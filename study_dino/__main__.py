"""JSONL event playback. Always simulation-only; no I/O to a device or platform."""
import argparse
import json
from pathlib import Path

from .session import Event, StudySession


def main():
    parser = argparse.ArgumentParser(description="奶龙本地规则回放：不是视觉识别或实物演示")
    parser.add_argument("scenario", type=Path, help="本地测试事件 JSONL 文件")
    args = parser.parse_args()
    session = StudySession()
    for line_number, line in enumerate(args.scenario.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
            event = Event(**raw)
            output = session.handle(event).to_dict()
        except (ValueError, TypeError, KeyError) as error:
            parser.exit(2, f"第{line_number}行输入无效：{error}\n")
        print(json.dumps({"evidence": "local_simulation", "hardware_executed": False,
                          "event_id": event.event_id, **output}, ensure_ascii=False))


if __name__ == "__main__":
    main()
