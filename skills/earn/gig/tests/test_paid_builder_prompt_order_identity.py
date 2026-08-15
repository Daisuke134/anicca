#!/usr/bin/env python3
"""★What was ordered★ reaches the builder's instructions, not just its packet.

2026-08-07 23:36, order 91000001 (買い手A, offer:92000015). The builder was shown
題材『パズルクエストX』 and 納品はGoogleドキュメントで, and produced a general guide to
the game -- a subject and a file format are not a deliverable. Measured on that pass:

    grep -c 企画 ~/gig/evidence/gig-pass-1786113058-11812/PAID_WORK.prompt.txt  ->  0

The order's own name, 「ポケモン動画の企画・台本作成ができる方を募集します」, is the only place
企画 and 台本 exist anywhere on that order, and it reached nothing.

Two halves have to hold, and this file tests the second:

1. the compiler carries it        -- tests/test_project_context_compiler.py
2. ★the prompt cannot skim it★    -- here

These tests run the real bash out of ``gig_pass.sh`` rather than restating the clause, so a
clause that is written but never rendered cannot pass. The prompt argument is checked for
the variable itself for the same reason ``test_paid_builder_prompt_blocked_contract`` renders
rather than greps: a value computed and then not interpolated is the exact bug being fixed.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1]
GIG_PASS = SKILL / "gig_pass.sh"
MARKER = "You are the high-value paid-work builder."
TITLE = "ポケモン動画の企画・台本作成ができる方を募集します"


def _order_clause_block() -> str:
    """The real `order_clause=$( ... )` assignment, lifted verbatim from gig_pass.sh."""
    text = GIG_PASS.read_text(encoding="utf-8")
    match = re.search(
        r"^  local order_clause=\"\"\n(  order_clause=\$\(.*?^PYEOF\n\)\n)",
        text, re.S | re.M,
    )
    assert match, "the A9 order_clause block was not found in gig_pass.sh"
    # `local` is only legal inside a function; the assignment itself is what we exercise.
    return match.group(1).replace("  order_clause=$(", "order_clause=$(", 1)


def _render_clause(tmp_path: Path, order: dict | None) -> str:
    root = tmp_path / "project"
    if order is not None:
        context = root / "context" / "current.json"
        context.parent.mkdir(parents=True, exist_ok=True)
        context.write_text(
            json.dumps({"combined_context": {"order": order}}, ensure_ascii=False),
            encoding="utf-8",
        )
    script = (
        f'TOP_PROJECT_ROOT="{root}"\n'
        + _order_clause_block()
        + 'printf "%s" "$order_clause"\n'
    )
    done = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr
    return done.stdout


def test_the_prompt_interpolates_the_clause_before_everything_else(tmp_path):
    """Position is the point: first, in the imperative voice, ahead of the packet."""
    line = next(
        row for row in GIG_PASS.read_text(encoding="utf-8").splitlines() if MARKER in row
    )
    assert "$order_clause" in line, "order_clause is computed but never reaches the prompt"
    assert line.index("$order_clause") < line.index("$feedback_clause")
    assert line.index("$order_clause") < line.index("$builder_queue_json")


def test_the_order_name_is_quoted_in_the_builders_instructions(tmp_path):
    rendered = _render_clause(tmp_path, {"title": TITLE, "title_source": "order_label"})
    assert TITLE in rendered
    # The words the 2026-08-07 prompt did not contain, now present by construction.
    assert "企画" in rendered and "台本" in rendered


def test_the_order_name_is_tied_to_a_required_output_so_it_cannot_be_skimmed(tmp_path):
    """A value the model may read is not a fix; a sentence it must write is.

    The rest of this prompt makes rules unskippable by naming an exact file and exact keys.
    Same device here: before building, justify in acceptance evidence why the artifact is
    what the order name asked for -- or write BLOCKED instead.
    """
    rendered = _render_clause(tmp_path, {"title": TITLE, "title_source": "order_label"})
    assert "acceptance evidence に記録" in rendered
    assert "BLOCKED" in rendered
    assert "誤納品" in rendered


def test_a_subject_only_build_is_named_as_the_failure_it_was(tmp_path):
    rendered = _render_clause(tmp_path, {"title": TITLE, "title_source": "order_label"})
    assert "題材" in rendered
    assert "2026-08-07" in rendered


def test_an_order_naming_nothing_tells_the_builder_where_we_looked(tmp_path):
    """★Absence is visible, not silent.★ No title on record means nobody ever wrote down
    what to build, and the honest move is to refuse and ask -- not to guess from a 題材."""
    rendered = _render_clause(tmp_path, {
        "title": None, "title_source": "none",
        "looked_in": ["/workspace/gig/postings/request-91000001.json", "queue_item.title"],
    })
    assert "記録が存在しません" in rendered
    assert "request-91000001.json" in rendered
    assert "acceptance-blocked.json" in rendered
    assert "推測して作ってはいけません" in rendered


def test_a_missing_context_leaves_the_prompt_exactly_as_it_was(tmp_path):
    """The clause must never be able to fail the paid lane it is riding in."""
    assert _render_clause(tmp_path, None) == ""


def test_the_clause_stays_inside_a_sane_prompt_budget(tmp_path):
    """Measured on the real title; the whole point is that it is cheap enough to always send."""
    rendered = _render_clause(tmp_path, {"title": TITLE, "title_source": "order_label"})
    assert len(rendered.encode("utf-8")) <= 1200


if __name__ == "__main__":  # pragma: no cover - convenience
    raise SystemExit(pytest.main([__file__, "-p", "no:randomly", "-q"]))
