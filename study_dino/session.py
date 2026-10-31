"""Deterministic session rules for local preview, not a posture classifier.

All outputs are intents. This module cannot open a camera, microphone, serial
port, network connection, or actuator. The final device adapter must enforce its
own validated electrical limits and emergency stop.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import math


class Phase(str, Enum):
    IDLE = "idle"
    FOCUS = "focus"
    BREAK = "break"
    PAUSED = "paused"
    ENDED = "ended"


class Posture(str, Enum):
    ALIGNED = "aligned"
    DEVIATED = "deviated"
    ABSENT = "absent"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Policy:
    # Preview examples, not calibrated model thresholds or actuator durations.
    sustained_seconds: float = 5.0
    cooldown_seconds: float = 30.0
    minimum_confidence: float = 0.8

    def __post_init__(self):
        if not all(math.isfinite(x) and x >= 0 for x in
                   (self.sustained_seconds, self.cooldown_seconds)):
            raise ValueError("Policy times must be finite and nonnegative")
        if not 0 <= self.minimum_confidence <= 1:
            raise ValueError("Confidence threshold must be between 0 and 1")


@dataclass(frozen=True)
class Event:
    event_id: str
    at: float
    kind: str
    data: dict = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.event_id, str) or not self.event_id:
            raise ValueError("Event ID must be nonempty text")
        if isinstance(self.at, bool) or not isinstance(self.at, (int, float)) or not math.isfinite(self.at) or self.at < 0:
            raise ValueError("Event time must be finite and nonnegative")
        if not isinstance(self.data, dict):
            raise ValueError("Event data must be an object")


@dataclass(frozen=True)
class Outcome:
    status: str
    phase: str
    message: str
    intents: tuple[dict, ...] = ()

    def to_dict(self):
        return asdict(self)


def flag(data: dict, name: str, default: bool = False) -> bool:
    value = data.get(name, default)
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a boolean")
    return value


class StudySession:
    def __init__(self, policy: Policy | None = None):
        self.policy = policy or Policy()
        self.phase = Phase.IDLE
        self.task = ""
        self.mode = "voice"
        self.vibration_consent = False
        self.water_consent = False
        self.online = False
        self.vibration_ready = False
        self.water_ready = False
        self.emergency_stop = False
        self.candidate: Posture | None = None
        self.candidate_since = 0.0
        self.awaiting_checkin = False
        self.last_prompt_at = -math.inf
        self.pending_request: str | None = None
        self.last_time = -math.inf
        self.seen: set[str] = set()

    def result(self, status, message, *intents):
        return Outcome(status, self.phase.value, message, tuple(intents))

    def reset_observation(self):
        self.candidate = None
        self.awaiting_checkin = False

    def stop(self, event: Event, phase: Phase, reason: str):
        if self.phase not in (Phase.IDLE, Phase.ENDED):
            self.phase = phase
        self.reset_observation()
        self.vibration_ready = self.water_ready = False
        # This is a stop REQUEST, not proof a device has stopped.
        return self.result("stop_requested", reason,
                           {"request_id": f"stop:{event.event_id}", "kind": "stop_all"})

    def handle(self, event: Event) -> Outcome:
        if event.event_id in self.seen:
            return self.result("duplicate_ignored", "重复事件，未再次提出动作。")
        if event.at < self.last_time:
            raise ValueError("Events must use nondecreasing session time")
        handlers = {
            "start": self.start, "observe": self.observe,
            "checkin": self.checkin, "device": self.device,
            "pause": lambda e: self.stop(e, Phase.PAUSED, "监督已暂停，设备停止请求待确认。"),
            "break": lambda e: self.stop(e, Phase.BREAK, "进入休息，设备停止请求待确认。"),
            "end": lambda e: self.stop(e, Phase.ENDED, "本轮结束，设备停止请求待确认。"),
            "resume": self.resume, "revoke": self.revoke,
            "receipt": self.receipt, "timeout": self.timeout,
        }
        if event.kind not in handlers:
            raise ValueError(f"Unknown event kind: {event.kind}")
        outcome = handlers[event.kind](event)
        self.seen.add(event.event_id)
        self.last_time = event.at
        return outcome

    def start(self, event):
        if self.phase not in (Phase.IDLE, Phase.ENDED):
            return self.result("blocked", "已有会话；先结束，或明确恢复当前会话。")
        if self.pending_request:
            return self.result("blocked", "上一动作结果未知，不能开始新的执行链。")
        task = event.data.get("task", "")
        if not isinstance(task, str):
            raise ValueError("Task must be text")
        task = task.strip()
        mode = event.data.get("mode", "voice")
        vibration = flag(event.data, "vibration_consent")
        water = flag(event.data, "water_consent")
        if not task or mode not in ("voice", "vibrate", "splash"):
            raise ValueError("Start requires a task and a valid mode")
        if mode in ("vibrate", "splash") and not vibration:
            raise ValueError("Vibration mode needs explicit consent")
        if mode == "splash" and not water:
            raise ValueError("Splash mode needs separate water consent")
        self.task, self.mode = task, mode
        self.vibration_consent, self.water_consent = vibration, water
        self.phase = Phase.FOCUS
        self.last_prompt_at = -math.inf
        self.reset_observation()
        return self.result("started", "学习约定已记录；是否执行实物动作还需设备与安全状态确认。")

    def observe(self, event):
        posture = Posture(event.data["posture"])
        confidence = event.data.get("confidence", 0.0)
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            raise ValueError("Confidence must be a number between 0 and 1")
        if self.phase != Phase.FOCUS:
            return self.result("ignored", "当前不是监督状态，不触发提醒或动作。")
        if posture == Posture.UNKNOWN or confidence < self.policy.minimum_confidence:
            self.reset_observation()
            return self.result("unknown", "无法判断，保持不动作。")
        if posture == Posture.ALIGNED:
            self.reset_observation()
            return self.result("aligned", "回到约定的可见状态；这不证明内在专注。")
        if self.awaiting_checkin:
            return self.result("awaiting_checkin", "等待解释，不追加动作。")
        if event.at - self.last_prompt_at < self.policy.cooldown_seconds:
            return self.result("cooldown", "提醒冷却中。")
        if self.candidate != posture:
            self.candidate, self.candidate_since = posture, event.at
        if event.at - self.candidate_since < self.policy.sustained_seconds:
            return self.result("observing", "记录候选行为，尚未达到持续条件。")
        self.awaiting_checkin = True
        self.last_prompt_at = event.at
        question = ("刚才离开学习区，是在拿书，还是想休息一下？"
                    if posture == Posture.ABSENT else "奶龙申请查岗：要调整一下姿势，还是先休息？")
        return self.result("checkin_requested", question,
                           {"request_id": f"ask:{event.event_id}", "kind": "ask_checkin"})

    def checkin(self, event):
        answer = event.data["answer"]
        if answer not in ("legitimate", "distracted", "break"):
            raise ValueError("Unsupported check-in answer")
        if self.phase != Phase.FOCUS or not self.awaiting_checkin:
            return self.result("ignored", "没有等待中的查岗，不能凭这条输入触发动作。")
        self.reset_observation()
        if answer == "break":
            return self.stop(event, Phase.BREAK, "休息可以，停止请求待设备确认。")
        if answer == "legitimate":
            return self.result("explained", "收到，合理解释不当成摸鱼。")
        if self.mode == "voice":
            return self.result("voice_reminder", "奶龙叫你回来啦；本轮只语音，不提执行器动作。")
        reasons = []
        if not self.online:
            reasons.append("设备离线")
        if self.emergency_stop:
            reasons.append("硬停用")
        if not self.vibration_consent or not self.vibration_ready:
            reasons.append("震动未同意或未完成安全准备")
        if self.mode == "splash" and (not self.water_consent or not self.water_ready):
            reasons.append("喷水未同意或未完成安全准备")
        if self.pending_request:
            reasons.append("上一动作未确认")
        if reasons:
            return self.result("blocked", "；".join(reasons) + "，不提出物理动作。")
        self.pending_request = f"feedback:{event.event_id}"
        kinds = ["vibrate"] + (["splash"] if self.mode == "splash" else [])
        return self.result("feedback_requested", "仅提出有限动作意图，等待设备结果；不是执行成功。",
                           {"request_id": self.pending_request, "kind": "feedback", "outputs": kinds})

    def device(self, event):
        online = flag(event.data, "online")
        emergency = flag(event.data, "emergency_stop")
        vibration = flag(event.data, "vibration_ready")
        water = flag(event.data, "water_ready")
        self.online, self.emergency_stop = online, emergency
        self.vibration_ready = online and not emergency and vibration
        self.water_ready = online and not emergency and water
        if emergency:
            return self.stop(event, Phase.PAUSED, "硬停用有效，停止请求待确认；不允许后续反馈。")
        if not online and self.pending_request:
            return self.result("unknown", "设备离线，上一动作结果未知，不能自动重试。")
        return self.result("device_status", "设备状态已记录；本地回放中的状态不是实物证据。")

    def resume(self, event):
        if self.phase not in (Phase.BREAK, Phase.PAUSED):
            return self.result("ignored", "当前不需要恢复。")
        if self.emergency_stop:
            return self.result("blocked", "硬停用仍有效，不能恢复。")
        self.phase = Phase.FOCUS
        self.reset_observation()
        return self.result("resumed", "恢复监督；设备安全准备不会因恢复会话自动重置为已完成。")

    def revoke(self, event):
        self.vibration_consent = self.water_consent = False
        return self.stop(event, Phase.PAUSED, "动作同意已撤销，停止请求待确认。")

    def receipt(self, event):
        if self.pending_request is None or event.data["request_id"] != self.pending_request:
            return self.result("receipt_ignored", "无对应待确认动作，不能以该回执改变成功状态。")
        state = event.data["state"]
        if state not in ("output_finished", "failed"):
            raise ValueError("Receipt must report output_finished or failed")
        self.pending_request = None
        if state == "failed":
            self.vibration_ready = self.water_ready = False
        return self.result("device_reported", f"设备报告 {state}；不等于已观测实际出水或震动。")

    def timeout(self, event):
        if self.pending_request is None or event.data["request_id"] != self.pending_request:
            return self.result("ignored", "没有对应待确认动作。")
        self.vibration_ready = self.water_ready = False
        return self.result("unknown", "动作结果超时未知，不自动重发；需要核对设备实际状态。")
