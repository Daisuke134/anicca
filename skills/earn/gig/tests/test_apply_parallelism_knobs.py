"""Apply parallelism is serial by default, and provable rather than arguable.

Two parallelism changes landed on 2026-09-02 -- `claim and parallelize apply planning` and
`run apply effects on bounded workers` -- and Coconala's last application is from that same day.
Since then every listing fails the offer-form read observing a **fully rendered** top page
(`title='ココナラ - プロが集まる日本最大級のスキルマーケット'`). That is the shape of reading a page a
sibling worker navigated, not of a redirect, a session failure, or a markup change: a redirect
would land somewhere related, an expired session lands on login, and the lane reads
`応募・スカウト管理` normally in the same pass.

Serial is how the lane worked when it last applied. The env var restores concurrency without
cutting a release, so the hypothesis can be tested both ways in production.

Run: python3 -m pytest skills/earn/gig/tests/test_apply_parallelism_knobs.py
"""

import importlib
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import application_parent  # noqa: E402

KNOBS = (
    ("GIG_PLANNER_PARALLEL_WORKERS", "PLANNER_PARALLEL_WORKERS"),
    ("GIG_APPLICATION_EFFECT_WORKERS", "APPLICATION_EFFECT_WORKERS"),
)


def _reload(monkeypatch, **env):
    for name, _ in KNOBS:
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    return importlib.reload(application_parent)


@pytest.mark.parametrize("env_name,attr", KNOBS)
def test_serial_by_default(monkeypatch, env_name, attr):
    assert getattr(_reload(monkeypatch), attr) == 1


@pytest.mark.parametrize("env_name,attr", KNOBS)
def test_concurrency_can_be_restored_without_a_release(monkeypatch, env_name, attr):
    assert getattr(_reload(monkeypatch, **{env_name: "3"}), attr) == 3


@pytest.mark.parametrize("env_name,attr", KNOBS)
def test_a_nonsense_value_falls_back_to_serial(monkeypatch, env_name, attr):
    assert getattr(_reload(monkeypatch, **{env_name: "banana"}), attr) == 1
    assert getattr(_reload(monkeypatch, **{env_name: "0"}), attr) == 1
    assert getattr(_reload(monkeypatch, **{env_name: "-2"}), attr) == 1


def test_the_module_still_imports_clean(monkeypatch):
    module = _reload(monkeypatch)
    assert module.PLANNER_REQUESTS_PER_CONTEXT == 10
