"""F4 (docs/loop-engineering/26-gig-loop-asis-tobe-plan.md sec CC'/EW'): a recurring
failure class must produce a lesson entry that reaches the builder/planner prompts --
deterministically, no model call.

Covers:
  - threshold: a (step, reason) pair below `threshold` occurrences never surfaces
  - window: a pair entirely outside `window_days` never surfaces, even at high count
  - bounded output: only the top `top_n` pairs per step reach the markdown fragment
  - injection: the regenerated failure-lessons.md is a real domain_skills.py source,
    reachable through the exact same BY_STEP/fragment() path C3 pinned for coconala.md
    (test_domain_skills_b0_listing_fit_rule.py) -- not a new mechanism.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "failure_lessons.py"
DOMAIN_SKILLS_PATH = Path(__file__).resolve().parents[1] / "scripts" / "domain_skills.py"


def load_module(path: Path, name: str):
    scripts_dir = str(path.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_ledger(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_below_threshold_never_surfaces() -> None:
    m = load_module(MODULE_PATH, "failure_lessons")
    now = 1_000_000.0
    rows = [
        {"ts": now - i, "failed_step": "B2", "reason": "rare_reason"}
        for i in range(4)  # threshold default is 5; 4 must not qualify
    ]
    recurring = m.aggregate(rows, now=now, window_days=7, threshold=5)
    assert recurring == []


def test_at_threshold_surfaces_with_correct_count_and_last_seen() -> None:
    m = load_module(MODULE_PATH, "failure_lessons")
    now = 1_000_000.0
    rows = [
        {"ts": now - i * 60, "failed_step": "B2", "reason": "b2_parent_boundary_failed"}
        for i in range(5)
    ]
    recurring = m.aggregate(rows, now=now, window_days=7, threshold=5)
    assert len(recurring) == 1
    row = recurring[0]
    assert row["failed_step"] == "B2"
    assert row["reason"] == "b2_parent_boundary_failed"
    assert row["count"] == 5
    assert row["last_seen"] == int(now)  # the i=0 row, the most recent


def test_outside_window_does_not_count_even_at_high_volume() -> None:
    m = load_module(MODULE_PATH, "failure_lessons")
    now = 1_000_000.0
    eight_days_ago = now - 8 * 86400
    rows = [
        {"ts": eight_days_ago - i, "failed_step": "B2", "reason": "old_reason"}
        for i in range(50)
    ]
    recurring = m.aggregate(rows, now=now, window_days=7, threshold=5)
    assert recurring == []


def test_window_boundary_is_inclusive_of_exactly_now_minus_window() -> None:
    m = load_module(MODULE_PATH, "failure_lessons")
    now = 1_000_000.0
    cutoff = now - 7 * 86400
    rows = [{"ts": cutoff, "failed_step": "B0", "reason": "boundary"} for _ in range(5)]
    recurring = m.aggregate(rows, now=now, window_days=7, threshold=5)
    assert len(recurring) == 1
    assert recurring[0]["count"] == 5


def test_malformed_and_incomplete_rows_are_skipped_not_fatal(tmp_path) -> None:
    m = load_module(MODULE_PATH, "failure_lessons")
    ledger = tmp_path / "pass-failures.jsonl"
    ledger.write_text(
        "not json at all\n"
        + json.dumps({"ts": 1, "failed_step": "B2"}) + "\n"  # missing reason
        + json.dumps({"failed_step": "B2", "reason": "x"}) + "\n"  # missing ts
        + "\n",  # blank line
        encoding="utf-8",
    )
    rows = m.read_rows(ledger)
    assert len(rows) == 2  # the two well-formed-but-incomplete JSON objects
    recurring = m.aggregate(rows, now=1_000_000.0, window_days=7, threshold=1)
    assert recurring == []  # neither row has both ts and reason


def test_bounded_output_top_n_per_step() -> None:
    m = load_module(MODULE_PATH, "failure_lessons")
    now = 1_000_000.0
    rows = []
    # Six distinct recurring reasons under B2, each above threshold, counts 6..11 so
    # sort order is unambiguous.
    for n, reason in enumerate(
        ["r1", "r2", "r3", "r4", "r5", "r6"], start=1
    ):
        count = n + 5
        rows.extend(
            {"ts": now - i, "failed_step": "B2", "reason": reason} for i in range(count)
        )
    recurring = m.aggregate(rows, now=now, window_days=7, threshold=5)
    grouped = m.by_domain_step(recurring, top_n=5)
    assert len(grouped["B2"]) == 5
    # Highest counts kept: r6 (11) down through r2 (7); r1 (6) dropped.
    kept_reasons = {row["reason"] for row in grouped["B2"]}
    assert kept_reasons == {"r2", "r3", "r4", "r5", "r6"}
    assert "r1" not in kept_reasons


def test_unmapped_failed_step_is_counted_but_not_grouped() -> None:
    # QUEUE has no domain_skills.py call site at all (verified against BY_STEP below), so
    # a recurring QUEUE failure is real in failure-lessons.json but has nowhere to inject.
    m = load_module(MODULE_PATH, "failure_lessons")
    now = 1_000_000.0
    rows = [
        {"ts": now - i, "failed_step": "QUEUE", "reason": "live_queue_snapshot_failed"}
        for i in range(6)
    ]
    recurring = m.aggregate(rows, now=now, window_days=7, threshold=5)
    assert len(recurring) == 1  # still counted
    grouped = m.by_domain_step(recurring, top_n=5)
    assert grouped == {}  # but never grouped under an injectable step


def test_paid_queue_delivery_aliases_to_reply_not_a_new_step() -> None:
    # assess_paid_queue's browser-delivery agent is the only caller of
    # `domain_skills.py REPLY`; its record_failure calls are stamped PAID_QUEUE_DELIVERY.
    m = load_module(MODULE_PATH, "failure_lessons")
    now = 1_000_000.0
    rows = [
        {"ts": now - i, "failed_step": "PAID_QUEUE_DELIVERY", "reason": "formal_delivery_transaction_failed"}
        for i in range(6)
    ]
    recurring = m.aggregate(rows, now=now, window_days=7, threshold=5)
    grouped = m.by_domain_step(recurring, top_n=5)
    assert "PAID_QUEUE_DELIVERY" not in grouped
    assert "REPLY" in grouped
    assert grouped["REPLY"][0]["reason"] == "formal_delivery_transaction_failed"


def test_main_writes_bounded_json_and_markdown(tmp_path) -> None:
    m = load_module(MODULE_PATH, "failure_lessons")
    ledger = tmp_path / "pass-failures.jsonl"
    now = m.time.time()
    write_ledger(
        ledger,
        [
            {"ts": now - i, "failed_step": "B2", "reason": "b2_parent_boundary_failed"}
            for i in range(20)
        ],
    )
    out = tmp_path / "failure-lessons.json"
    md = tmp_path / "failure-lessons.md"
    rc = m.main(
        [
            "--ledger", str(ledger),
            "--out", str(out),
            "--markdown", str(md),
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["threshold"] == 5
    assert len(payload["recurring"]) == 1
    assert payload["recurring"][0]["count"] == 20
    body = md.read_text(encoding="utf-8")
    assert body.startswith("## B2")
    assert "b2_parent_boundary_failed" in body


def test_main_on_a_missing_ledger_writes_empty_output_not_an_error(tmp_path) -> None:
    m = load_module(MODULE_PATH, "failure_lessons")
    out = tmp_path / "failure-lessons.json"
    md = tmp_path / "failure-lessons.md"
    rc = m.main(
        [
            "--ledger", str(tmp_path / "does-not-exist.jsonl"),
            "--out", str(out),
            "--markdown", str(md),
        ]
    )
    assert rc == 0
    assert json.loads(out.read_text(encoding="utf-8"))["recurring"] == []
    assert md.read_text(encoding="utf-8") == ""


def test_injection_reaches_b2_prompt_via_domain_skills_fragment(tmp_path, monkeypatch) -> None:
    # Characterization test in the same shape as
    # test_domain_skills_b0_listing_fit_rule.py::test_b0_fragment_includes_the_...: prove
    # the real BY_STEP/fragment() path (no new mechanism) actually carries a regenerated
    # failure-lessons.md into a step's prompt fragment.
    ds = load_module(DOMAIN_SKILLS_PATH, "domain_skills_for_failure_lessons_test")
    fake_skill_dir = tmp_path / "domain-skills"
    fake_skill_dir.mkdir()
    monkeypatch.setattr(ds, "SKILL_DIR", fake_skill_dir)

    fl = load_module(MODULE_PATH, "failure_lessons_for_injection_test")
    ledger = tmp_path / "pass-failures.jsonl"
    now = fl.time.time()
    write_ledger(
        ledger,
        [
            {"ts": now - i, "failed_step": "B2", "reason": "b2_parent_boundary_failed"}
            for i in range(9)
        ],
    )
    rc = fl.main(
        [
            "--ledger", str(ledger),
            "--out", str(tmp_path / "failure-lessons.json"),
            "--markdown", str(fake_skill_dir / "failure-lessons.md"),
        ]
    )
    assert rc == 0

    fragment = ds.fragment("B2", limit=0)
    assert "b2_parent_boundary_failed" in fragment
    assert "[failure-lessons]" in fragment

    # A lane that cannot act on it (PROFILE has no B2 failures) must not carry B2's noise.
    profile_fragment = ds.fragment("PROFILE", limit=0)
    assert "b2_parent_boundary_failed" not in profile_fragment


def test_every_step_aliases_target_an_actual_by_step_key() -> None:
    # If STEP_ALIASES ever points at a BY_STEP key domain_skills.py does not define, the
    # generated section would exist in the markdown but fragment() would silently drop it
    # for that step (BY_STEP.get(step) governs what sections() is even asked for).
    ds = load_module(DOMAIN_SKILLS_PATH, "domain_skills_for_alias_check")
    fl = load_module(MODULE_PATH, "failure_lessons_for_alias_check")
    for target in set(fl.STEP_ALIASES.values()):
        assert target in ds.BY_STEP
        assert "failure-lessons" in ds.BY_STEP[target]
