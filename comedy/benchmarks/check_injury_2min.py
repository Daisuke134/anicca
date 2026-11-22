#!/usr/bin/env python3
"""Offline script gate: ensure the two-minute stage cut keeps v8's opening and reaches a joke immediately."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "sagi-injury-help-2min-live.md"
FIRST = "はい、救急指令センターです。火事ですか、救急ですか？"
SECOND = (
    "救急ですね。声で分かりました。右ひざがご実家に帰られています。"
    "病名は「急性ひざの里帰りスペシャル」です。帰りの切符はこちらで手配します。"
)
BANNED = (
    "住所を教えてください",
    "今どこにいますか",
    "窓の外には何が見えますか",
    "落ち着いてください",
    "深呼吸して",
    "吸って、吐いて",
)


def extract_dialogues(md: str) -> list[tuple[str, str]]:
    if "## 完全上演台本" not in md or "## アドリブ" not in md:
        raise ValueError("Missing canonical script section markers")
    body = md.split("## 完全上演台本", 1)[1].split("## アドリブ", 1)[0]
    head = re.compile(r"^\*\*(ダイス|チャッピー)(?:（[^\n]+?）)?\*\*\s*$", re.MULTILINE)
    match = list(head.finditer(body))
    dialogues = []
    for i, h in enumerate(match):
        spoken = body[h.end() : match[i + 1].start() if i + 1 < len(match) else len(body)]
        spoken = "\n".join(line for line in spoken.strip().splitlines() if not line.strip().startswith("（")).strip()
        if spoken:
            dialogues.append((h.group(1), spoken))
    return dialogues


def check(md: str) -> list[str]:
    issues = []
    dialogues = extract_dialogues(md)
    if len(dialogues) < 16:
        issues.append("Too few dialogue turns for interactive sketch")
    if not dialogues or dialogues[0][0] != "ダイス":
        issues.append("Dais is not first speaker")
    ai = [line for role, line in dialogues if role == "チャッピー"]
    if len(ai) < 6:
        issues.append("Too few AI turns")
    if len(ai) >= 1 and ai[0] != FIRST:
        issues.append("AI first line differs from v8")
    if len(ai) >= 2 and ai[1] != SECOND:
        issues.append("AI second line differs from v8")
    for i, line in enumerate(ai):
        if i > 0 and ("？" in line or "?" in line):
            issues.append(f"Extra question in AI turn {i+1}")
        if any(phrase in line for phrase in BANNED):
            issues.append(f"Banned stage advice/triage in AI turn {i+1}")
    speech = "".join(s for _, s in dialogues)
    for anchor in ("田中ピーポー太郎", "おもち34号", "右折田", "豆腐田", "会田", "結婚", "歌舞伎町", "たぶん治る総合病院"):
        if anchor not in speech:
            issues.append(f"Missing key world anchor: {anchor}")
    for i in range(1, len(dialogues)):
        if dialogues[i][0] == dialogues[i - 1][0]:
            issues.append(f"Broken human–AI alternation at line {i+1}")
    return issues


def main() -> int:
    text = SCRIPT.read_text(encoding="utf-8")
    problems = check(text)
    turns = extract_dialogues(text)
    chars = sum(len(line) for _, line in turns)
    print(f"script={SCRIPT} total_turns={len(turns)} spoken_characters={chars}")
    if problems:
        for issue in problems:
            print(f"FAIL: {issue}", file=sys.stderr)
        return 1
    print("PASS: opening, immediate v8 joke, question discipline, character anchors, dialogue alternation")
    print("NOTE: duration, audio routing, voice model compliance and audience laughter are NOT_MEASURED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
