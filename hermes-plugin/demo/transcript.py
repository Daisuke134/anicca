"""Scripted Life Manager session. Prints a transcript; does not call the network."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import runtime  # noqa: E402

TODAY = date(2026, 11, 10)


class MemoryStore:
    def __init__(self):
        self.data = None

    def load(self):
        from engine import blank_state

        if self.data is None:
            self.data = blank_state()
        return self.data

    def save(self, data):
        self.data = data


def say(title, body):
    print(f"\n== {title}")
    print(body)


def main():
    store = MemoryStore()
    say(
        "user",
        "I commit to ship the essay tomorrow. I'll meditate every morning.",
    )
    context = runtime.ingest_user_message(
        store,
        "I commit to ship the essay tomorrow. I'll meditate every morning.",
        today=TODAY,
        session_id="demo",
    )
    say("pre_llm_call context", context)
    say(
        "tool life_manager_checkin (scheduled, unattended)",
        json.dumps(
            runtime.tool_checkin(store, today=TODAY, unattended=True, execution_id="demo-cron"),
            indent=2,
        ),
    )
    say(
        "user the next morning, after meditating",
        "I meditated.",
    )
    done = runtime.tool_complete(store, {"ref": "meditate every morning"}, today=date(2026, 11, 11))
    say("tool life_manager_complete", json.dumps(done, indent=2))
    again = runtime.tool_complete(store, {"ref": "meditate every morning"}, today=date(2026, 11, 12))
    say("next day complete", json.dumps(again["commitment"], indent=2))
    missed = runtime.tool_status(store, today=date(2026, 11, 14))
    habit = missed["habits"][0]
    say(
        "status after a missed day",
        f"{habit['text']}: streak {habit['streak']}, best {habit['best_streak']}, overdue {habit['overdue']}",
    )


if __name__ == "__main__":
    main()
