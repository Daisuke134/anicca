"""A font lookup must not throw away the most expensive work the loop does.

`fc-match` names a file that does not change between wakes. It was run on every hero render
with a ten-second timeout, and under load that timeout ended the whole wake -- after the
proposal had been generated, sealed and paid for. The answer is cached for the life of the
process, and the lookup is retried like every other transient in this loop.
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


@pytest.fixture(autouse=True)
def _no_cache(monkeypatch):
    monkeypatch.setattr(direct, "_HERO_FONT_PATH", None)
    monkeypatch.setattr(direct.time, "sleep", lambda seconds: None)


@pytest.fixture
def fc(monkeypatch, tmp_path):
    font = tmp_path / "HiraginoSans.ttc"
    font.write_bytes(b"font")
    calls = []

    def install(outcomes):
        queue = list(outcomes)

        def fake(argv, **kwargs):
            calls.append(argv)
            outcome = queue.pop(0) if queue else outcomes[-1]
            if isinstance(outcome, Exception):
                raise outcome
            return subprocess.CompletedProcess(argv, outcome[0], stdout=outcome[1], stderr="")

        monkeypatch.setattr(direct.subprocess, "run", fake)
    return install, calls, font


def test_a_timeout_that_clears_is_not_fatal(fc):
    install, calls, font = fc
    install([subprocess.TimeoutExpired("fc-match", 10), (0, str(font))])
    assert direct._hero_font_path() == font
    assert len(calls) == 2


def test_five_attempts_then_the_named_failure(fc):
    install, calls, _ = fc
    install([subprocess.TimeoutExpired("fc-match", 10)])
    with pytest.raises(RuntimeError, match="storefront_generated_image_font_missing"):
        direct._hero_font_path()
    assert len(calls) == 5


def test_the_answer_is_looked_up_once_per_process(fc):
    install, calls, font = fc
    install([(0, str(font))])
    assert direct._hero_font_path() == font
    assert direct._hero_font_path() == font
    assert direct._hero_font_path() == font
    assert len(calls) == 1, "a path that never changes must not be asked for every render"


def test_a_font_that_does_not_exist_is_still_a_failure(fc):
    install, _, _ = fc
    install([(0, "/nonexistent/Hiragino.ttc")])
    with pytest.raises(RuntimeError, match="storefront_generated_image_font_missing"):
        direct._hero_font_path()


def test_a_nonzero_exit_is_retried_then_named(fc):
    install, calls, font = fc
    install([(1, ""), (0, str(font))])
    assert direct._hero_font_path() == font
    assert len(calls) == 2


def test_the_renderer_no_longer_runs_fc_match_itself():
    source = (SCRIPTS / "storefront_direct.py").read_text(encoding="utf-8")
    block = source[source.index("def _render_generated_image_asset("):][:1400]
    assert "fc-match" not in block
    assert "_hero_font_path()" in block
