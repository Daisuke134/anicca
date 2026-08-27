from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from watercolor_candidate import wrap_ja


def test_wrap_ja_never_leaves_japanese_punctuation_alone():
    text = "あなたを小さくする関係を見抜いて、守るべき人と時間に集中するための5つのサイン。"
    wrapped = wrap_ja(text, width=13)
    lines = wrapped.split(r"\N")
    assert "".join(lines) == text
    assert all(line not in {"。", "、", "！", "？", "!", "?"} for line in lines)


def test_wrap_ja_keeps_normal_short_text_unchanged():
    assert wrap_ja("短い字幕。", width=13) == "短い字幕。"
