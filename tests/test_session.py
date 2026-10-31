import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from study_dino.session import Event, Phase, Policy, StudySession

ROOT = Path(__file__).resolve().parents[1]


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.session = StudySession()
        self.clock = -1
        self.index = 0

    def send(self, kind, at=None, **data):
        self.clock = self.clock + 1 if at is None else at
        self.index += 1
        return self.session.handle(Event(f"event-{self.index}", self.clock, kind, data))

    def start(self, mode="voice"):
        return self.send("start", task="复习数学", mode=mode,
                         vibration_consent=mode != "voice", water_consent=mode == "splash")

    def ready(self):
        return self.send("device", online=True, vibration_ready=True, water_ready=True)

    def candidate(self, posture="absent"):
        self.send("observe", posture=posture, confidence=.95)
        return self.send("observe", at=self.clock + 5, posture=posture, confidence=.95)

    def feedback(self):
        self.candidate()
        return self.send("checkin", answer="distracted")

    def test_start_records_task(self):
        self.assertEqual(self.start().status, "started")
        self.assertEqual(self.session.task, "复习数学")
        self.assertEqual(self.session.phase, Phase.FOCUS)

    def test_no_task_cannot_start(self):
        with self.assertRaises(ValueError):
            self.send("start", task=" ")
        self.assertEqual(self.session.phase, Phase.IDLE)

    def test_water_needs_separate_consent(self):
        with self.assertRaises(ValueError):
            self.send("start", task="读书", mode="splash", vibration_consent=True)

    def test_vibration_needs_consent(self):
        with self.assertRaises(ValueError):
            self.send("start", task="读书", mode="vibrate")

    def test_string_false_is_not_consent(self):
        with self.assertRaises(ValueError):
            self.send("start", task="读书", mode="splash",
                      vibration_consent=True, water_consent="false")

    def test_cannot_replace_active_session(self):
        self.start()
        self.assertEqual(self.send("start", task="另一任务").status, "blocked")
        self.assertEqual(self.session.task, "复习数学")

    def test_aligned_is_not_attention_inference(self):
        self.start()
        result = self.send("observe", posture="aligned", confidence=.99)
        self.assertEqual(result.status, "aligned")
        self.assertFalse(result.intents)

    def test_three_candidate_categories_are_distinct(self):
        self.start()
        for posture in ("aligned", "deviated", "absent"):
            result = self.send("observe", posture=posture, confidence=.95)
            self.assertNotEqual(result.status, "unknown")

    def test_short_absence_does_not_prompt(self):
        self.start()
        result = self.send("observe", posture="absent", confidence=.95)
        self.assertEqual(result.status, "observing")
        self.assertFalse(result.intents)

    def test_sustained_absence_asks_not_sprays(self):
        self.start("splash")
        self.ready()
        result = self.candidate()
        self.assertEqual(result.status, "checkin_requested")
        self.assertEqual(result.intents[0]["kind"], "ask_checkin")
        self.assertFalse(self.session.pending_request)

    def test_sustained_deviation_asks(self):
        self.start()
        self.assertEqual(self.candidate("deviated").status, "checkin_requested")

    def test_changing_class_restarts_duration(self):
        self.start()
        self.send("observe", posture="absent", confidence=.95)
        result = self.send("observe", at=20, posture="deviated", confidence=.95)
        self.assertEqual(result.status, "observing")

    def test_unknown_cancels_candidate(self):
        self.start()
        self.candidate()
        self.send("observe", posture="unknown", confidence=.99)
        self.assertEqual(self.send("checkin", answer="distracted").status, "ignored")

    def test_low_confidence_is_unknown(self):
        self.start()
        result = self.send("observe", posture="absent", confidence=.2)
        self.assertEqual(result.status, "unknown")
        self.assertFalse(result.intents)

    def test_invalid_confidence_rejected(self):
        self.start()
        for value in (True, -1, 1.1, float("nan"), "high"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.send("observe", posture="absent", confidence=value)

    def test_legitimate_explanation_never_actuates(self):
        self.start("splash")
        self.ready()
        self.candidate()
        result = self.send("checkin", answer="legitimate")
        self.assertEqual(result.status, "explained")
        self.assertFalse(result.intents)

    def test_voice_mode_does_not_request_actuators(self):
        self.start()
        self.ready()
        result = self.feedback()
        self.assertEqual(result.status, "voice_reminder")
        self.assertFalse(result.intents)

    def test_offline_blocks_feedback(self):
        self.start("splash")
        result = self.feedback()
        self.assertEqual(result.status, "blocked")
        self.assertFalse(result.intents)

    def test_water_not_ready_blocks_combined_action(self):
        self.start("splash")
        self.send("device", online=True, vibration_ready=True)
        self.assertEqual(self.feedback().status, "blocked")

    def test_vibrate_mode_only_requests_vibration(self):
        self.start("vibrate")
        self.ready()
        result = self.feedback()
        self.assertEqual(result.intents[0]["outputs"], ["vibrate"])

    def test_splash_mode_requests_both_but_not_execution(self):
        self.start("splash")
        self.ready()
        result = self.feedback()
        self.assertEqual(result.status, "feedback_requested")
        self.assertEqual(result.intents[0]["outputs"], ["vibrate", "splash"])
        self.assertIn("不是执行成功", result.message)

    def test_answer_without_checkin_cannot_actuate(self):
        self.start("splash")
        self.ready()
        self.assertEqual(self.send("checkin", answer="distracted").status, "ignored")

    def test_waiting_for_answer_does_not_repeat_prompt(self):
        self.start()
        self.candidate()
        result = self.send("observe", posture="absent", confidence=.95)
        self.assertEqual(result.status, "awaiting_checkin")
        self.assertFalse(result.intents)

    def test_cooldown_prevents_prompt_spam(self):
        self.start()
        self.candidate()
        self.send("checkin", answer="legitimate")
        self.assertEqual(self.send("observe", posture="absent", confidence=.95).status, "cooldown")

    def test_pause_requests_stop_and_disarms(self):
        self.start("splash")
        self.ready()
        result = self.send("pause")
        self.assertEqual(result.phase, "paused")
        self.assertEqual(result.intents[0]["kind"], "stop_all")
        self.assertFalse(self.session.water_ready)

    def test_break_workflow_and_explicit_resume(self):
        self.start("splash")
        self.ready()
        self.send("break")
        result = self.send("observe", posture="absent", confidence=.99)
        self.assertEqual(result.status, "ignored")
        self.assertEqual(self.send("resume").status, "resumed")
        self.assertFalse(self.session.water_ready)

    def test_break_as_explanation(self):
        self.start()
        self.candidate()
        self.assertEqual(self.send("checkin", answer="break").phase, "break")

    def test_revoke_removes_both_permissions(self):
        self.start("splash")
        self.ready()
        self.send("revoke")
        self.send("resume")
        self.ready()
        self.assertEqual(self.feedback().status, "blocked")

    def test_emergency_stop_cannot_resume(self):
        self.start()
        self.send("device", online=True, emergency_stop=True, water_ready=True)
        self.assertEqual(self.send("resume").status, "blocked")
        self.assertEqual(self.session.phase, Phase.PAUSED)

    def test_cannot_resume_without_started_session(self):
        self.send("break")
        self.assertEqual(self.send("resume").status, "ignored")
        self.assertEqual(self.session.phase, Phase.IDLE)

    def test_duplicate_id_is_not_reexecuted(self):
        event = Event("start-once", 0, "start", {"task": "读书"})
        self.session.handle(event)
        self.assertEqual(self.session.handle(event).status, "duplicate_ignored")

    def test_old_event_time_rejected(self):
        self.start()
        with self.assertRaises(ValueError):
            self.send("observe", at=-1, posture="aligned", confidence=.95)
        self.send("observe", at=10, posture="aligned", confidence=.95)
        with self.assertRaises(ValueError):
            self.send("observe", at=9, posture="aligned", confidence=.95)

    def test_timeout_does_not_retry(self):
        self.start("splash")
        self.ready()
        result = self.feedback()
        request = result.intents[0]["request_id"]
        timed_out = self.send("timeout", request_id=request)
        self.assertEqual(timed_out.status, "unknown")
        self.assertFalse(timed_out.intents)
        self.assertEqual(self.session.pending_request, request)
        self.assertFalse(self.session.water_ready)

    def test_unknown_receipt_is_not_success(self):
        self.assertEqual(self.send("receipt", request_id=None, state="output_finished").status,
                         "receipt_ignored")

    def test_output_receipt_is_not_physical_proof(self):
        self.start("splash")
        self.ready()
        result = self.feedback()
        receipt = self.send("receipt", request_id=result.intents[0]["request_id"], state="output_finished")
        self.assertEqual(receipt.status, "device_reported")
        self.assertIn("不等于", receipt.message)
        self.assertIsNone(self.session.pending_request)

    def test_failed_receipt_disarms(self):
        self.start("splash")
        self.ready()
        result = self.feedback()
        self.send("receipt", request_id=result.intents[0]["request_id"], state="failed")
        self.assertFalse(self.session.water_ready)

    def test_ended_session_does_not_observe(self):
        self.start()
        self.send("end")
        self.assertEqual(self.send("observe", posture="absent", confidence=.99).status, "ignored")

    def test_event_contract_rejects_invalid_boundary_data(self):
        for args in ((1, 0, "start", {}), ("id", True, "start", {}), ("id", 0, "start", None)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                Event(*args)

    def test_invalid_policy_rejected(self):
        for kwargs in ({"sustained_seconds": -1}, {"cooldown_seconds": float("inf")},
                       {"minimum_confidence": 2}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                Policy(**kwargs)


class PlaybackTests(unittest.TestCase):
    def test_example_is_explicitly_simulated(self):
        result = subprocess.run([sys.executable, "-m", "study_dino", "examples/session-preview.jsonl"],
                                cwd=ROOT, capture_output=True, encoding="utf-8", check=True)
        rows = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(rows), 11)
        self.assertTrue(all(row["evidence"] == "local_simulation" for row in rows))
        self.assertTrue(all(row["hardware_executed"] is False for row in rows))
        self.assertTrue(any(row["status"] == "feedback_requested" for row in rows))
        self.assertTrue(any(row["phase"] == "break" for row in rows))

    def test_invalid_event_is_reported_without_traceback(self):
        with tempfile.TemporaryDirectory() as folder:
            scenario = Path(folder) / "invalid.jsonl"
            scenario.write_text('{"event_id":"bad","at":0,"kind":"invented"}\n', encoding="utf-8")
            result = subprocess.run([sys.executable, "-m", "study_dino", str(scenario)], cwd=ROOT,
                                    capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 2)
        self.assertIn("第1行", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
