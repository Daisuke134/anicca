#!/usr/bin/env python3
"""The daily Life Manager marketing loop: pick tomorrow's creative, speak it, render it.

What this replaces: the previous runtime bolted one fixed call recording onto every video, so the
voice was Dais talking to his own assistant and the subject could never change. Here the voice is
narration synthesised from the creative bank, and the bank rotates, so each day is a different piece.

The loop deliberately owns only two decisions — which creative runs and what the voice says — and
hands the actual rendering to MoneyPrinterTurbo rather than reimplementing a renderer.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

LANGUAGES = ("en", "ja")
VOICES = {"en": "en-US-AndrewNeural", "ja": "ja-JP-KeitaNeural"}


def load_bank(path: Path) -> list[dict]:
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def read_ledger(path: Path) -> list[dict]:
    """Run history, oldest first. A missing or partly written ledger is not fatal to the loop."""
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError:
        return []
    rows = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def next_creative(bank: list[dict], ledger: list[dict]) -> dict | None:
    """The creative after the one that ran most recently, wrapping at the end of the bank.

    Only the newest ledger entry matters: the loop moves forward one step per day, so an older entry
    naming a later creative must not drag the rotation backwards. An unknown id restarts the cycle
    rather than stalling the loop.
    """
    if not bank:
        return None
    ids = [row.get("id") for row in bank]
    last = None
    for row in reversed(ledger):
        candidate = row.get("creative_id")
        if candidate in ids:
            last = candidate
            break
    if last is None:
        return bank[0]
    return bank[(ids.index(last) + 1) % len(bank)]


def _beats(creative: dict, language: str) -> tuple[str, str, str]:
    suffix = "" if language == "ja" else f"_{language}"
    fields = [f"pain{suffix}", f"moment{suffix}", f"punchline{suffix}"]
    missing = [name for name in fields if not str(creative.get(name, "")).strip()]
    if missing:
        raise ValueError(f"creative {creative.get('id')!r} is missing {missing} for language {language!r}")
    return tuple(str(creative[name]).strip() for name in fields)  # type: ignore[return-value]


def narration_script(creative: dict, language: str) -> str:
    """Turn the three bank beats into prose a voice can read.

    The shape is always the same promise: name the problem the viewer already has, show the exact
    moment Life Manager takes it over, then say what is different afterwards.
    """
    if language not in LANGUAGES:
        raise ValueError(f"unsupported narration language {language!r}")
    pain, moment, punchline = _beats(creative, language)
    if language == "en":
        return (
            f"Here is something you already do: {pain}. "
            f"Nobody hands you that time back, and no reminder app has ever solved it. "
            f"Life Manager does the part you were doing by hand — {moment}. "
            f"So the day starts differently: {punchline}."
        )
    return (
        f"{pain}。"
        f"その時間は誰も返してくれないし、通知アプリでは解決しない。"
        f"Life Manager が、あなたが手でやっていた部分を引き取る。{moment}。"
        f"だから一日はこう始まる。{punchline}。"
    )


def render_argv(*, script: str, materials: list[Path], task_id: str, voice: str) -> list[str]:
    """The MoneyPrinterTurbo invocation.

    `--video-script` carries our own narration, so no language model sits in the daily path, and
    `--video-source local` keeps the loop independent of any stock-footage API key.
    """
    if not materials:
        raise ValueError("a render needs at least one material")
    return [
        "--video-script", script,
        "--video-source", "local",
        "--video-materials", ",".join(str(path) for path in materials),
        "--video-aspect", "9:16",
        "--video-count", "1",
        "--video-concat-mode", "sequential",
        "--voice-name", voice,
        "--subtitle-enabled",
        "--subtitle-position", "bottom",
        "--font-size", "60",
        "--stroke-width", "2",
        "--task-id", task_id,
    ]


def main() -> int:
    import argparse
    import uuid

    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Plan today's Life Manager marketing render.")
    parser.add_argument("--bank", type=Path, default=here / "creative-bank.jsonl")
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path(os.environ.get("LM_DAILY_RUN_LEDGER", "~/.life-manager/state/daily-run-ledger.jsonl")).expanduser(),
    )
    parser.add_argument("--language", choices=LANGUAGES, default="en")
    args = parser.parse_args()

    creative = next_creative(load_bank(args.bank), read_ledger(args.ledger))
    if creative is None:
        print(json.dumps({"error": "empty creative bank"}))
        return 1
    language = args.language
    print(json.dumps({
        "creative_id": creative["id"],
        "language": language,
        "voice": VOICES[language],
        "script": narration_script(creative, language),
        "task_id": str(uuid.uuid4()),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
