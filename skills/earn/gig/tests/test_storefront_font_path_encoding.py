"""The font this loop renders with has a Japanese name; the environment must not decide that.

`fc-match -f %{file} "Hiragino Sans"` answers
`/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc`. Read with `text=True`, Python decodes it
with the locale's encoding, and the storefront plist sets no LANG -- so under launchd the
name came back mangled and named a file that does not exist, while the identical command in
a shell answered correctly in 0.2 seconds. The wake reported
`storefront_generated_image_font_missing` for a font that was installed the whole time.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import storefront_direct as direct  # noqa: E402

SOURCE = (SCRIPTS / "storefront_direct.py").read_text(encoding="utf-8")
LOOKUP = SOURCE[SOURCE.index("def _hero_font_path"):][:1600]
JAPANESE_NAME = "ヒラギノ角ゴシック W4.ttc"


def test_the_lookup_names_its_encoding_rather_than_inheriting_one():
    assert 'encoding="utf-8"' in LOOKUP


def test_the_lookup_no_longer_lets_the_locale_decide():
    # Comments are allowed to name the old behaviour; the code must not use it.
    code = [line for line in LOOKUP.splitlines() if not line.lstrip().startswith("#")]
    assert not [line for line in code if "text=True" in line]


def test_a_japanese_font_path_survives_the_lookup(monkeypatch, tmp_path):
    font = tmp_path / JAPANESE_NAME
    font.write_bytes(b"font")
    monkeypatch.setattr(direct, "_HERO_FONT_PATH", None)
    monkeypatch.setattr(direct.subprocess, "run", lambda argv, **kw: subprocess.CompletedProcess(
        argv, 0, stdout=str(font) + "\n", stderr=""))
    assert direct._hero_font_path() == font


def test_the_real_font_name_round_trips_through_utf8():
    # The exact failure: these bytes are not decodable as ASCII, which is what launchd gave.
    raw = JAPANESE_NAME.encode("utf-8")
    assert raw.decode("utf-8") == JAPANESE_NAME
    with pytest.raises(UnicodeDecodeError):
        raw.decode("ascii")


def test_a_decode_failure_is_not_silently_turned_into_a_wrong_path():
    # errors="strict" so a mangled answer raises instead of naming a file that cannot exist.
    assert 'errors="strict"' in LOOKUP
