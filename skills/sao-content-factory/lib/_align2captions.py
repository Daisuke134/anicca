#!/usr/bin/env python3
"""Convert ElevenLabs character-level alignment → @remotion/captions Caption[].

Reads JSON on stdin:
  {
    "characters": ["H","e","l","l","o"," ","w","o","r","l","d"],
    "character_start_times_seconds": [...],
    "character_end_times_seconds": [...]
  }

Writes JSON on stdout: [{ text, startMs, endMs, timestampMs, confidence }]

A "word" is a maximal run of non-whitespace characters. Trailing space is
appended to text so renderer can show "Hello world" not "Helloworld".
"""
import json
import sys


def main():
    data = json.load(sys.stdin)
    chars = data.get("characters", [])
    starts = data.get("character_start_times_seconds", [])
    ends = data.get("character_end_times_seconds", [])
    if not chars or len(chars) != len(starts) != len(ends):
        json.dump([], sys.stdout)
        return

    captions = []
    cur = []
    cur_start_ms = None
    cur_end_ms = None
    for ch, s, e in zip(chars, starts, ends):
        if ch.strip() == "":
            # whitespace → close current word (if any)
            if cur:
                text = "".join(cur) + " "
                captions.append({
                    "text": text,
                    "startMs": cur_start_ms,
                    "endMs": cur_end_ms,
                    "timestampMs": (cur_start_ms + cur_end_ms) // 2,
                    "confidence": None,
                })
                cur = []
                cur_start_ms = None
                cur_end_ms = None
            continue
        if cur_start_ms is None:
            cur_start_ms = int(s * 1000)
        cur_end_ms = int(e * 1000)
        cur.append(ch)

    if cur:
        text = "".join(cur) + " "
        captions.append({
            "text": text,
            "startMs": cur_start_ms,
            "endMs": cur_end_ms,
            "timestampMs": (cur_start_ms + cur_end_ms) // 2,
            "confidence": None,
        })

    json.dump(captions, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
