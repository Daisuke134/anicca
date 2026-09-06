"""No new possibly-unbound local in the Apply wrapper.

2026-09-06: a rename left `denied_source_id` assigned only inside `if source_failure is not None:`
while a later branch read it on every phase. The ordinary case -- no source failure at all -- then
raised UnboundLocalError two seconds into every wake, which was worse than the bug being fixed. The
unit tests all passed, because they covered the two helpers and not the control flow between them.

CPython already does this analysis. It emits `LOAD_FAST_CHECK` only where the compiler cannot prove
a local is bound at the read, so the interpreter's own opinion is a free and exact guard -- no
linter, no dependency. Pinning the set means an existing one stays visible while a new one fails.

Run: python3 -m pytest skills/earn/gig/tests/test_apply_no_new_unbound_locals.py
"""

import dis
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "application_direct.py"

# Pre-existing, measured 2026-09-06 and deliberately not fixed here: each needs its own reading of
# whether the unbound path is reachable, and that is a separate change from the one that added this
# guard. The point of the pin is that this list may shrink, never grow by accident.
KNOWN_POSSIBLY_UNBOUND = {
    "main": {
        "continuing_after_source_failure",
        "must_stop",
        "next_cursor",
        "next_cursor_path",
    },
}


def _possibly_unbound() -> dict[str, set[str]]:
    code = compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec")

    def walk(block):
        yield block
        for const in block.co_consts:
            if hasattr(const, "co_code"):
                yield from walk(const)

    found: dict[str, set[str]] = {}
    for block in walk(code):
        names = {i.argval for i in dis.get_instructions(block) if i.opname == "LOAD_FAST_CHECK"}
        if names:
            found[block.co_name] = names
    return found


def test_no_local_is_read_on_a_path_where_it_may_be_unbound():
    found = _possibly_unbound()
    new = {
        name: sorted(names - KNOWN_POSSIBLY_UNBOUND.get(name, set()))
        for name, names in found.items()
        if names - KNOWN_POSSIBLY_UNBOUND.get(name, set())
    }
    assert not new, (
        f"new possibly-unbound locals: {new}. A name a later branch always reads must be bound on "
        f"every path, not only inside the branch that produces it."
    )


def test_the_denied_source_binding_that_broke_production_stays_fixed():
    assert "denied_source_id" not in _possibly_unbound().get("main", set())


def test_the_known_list_shrinks_but_is_never_stale():
    """A name that gets fixed must leave the pin, or the guard slowly stops meaning anything."""
    found = _possibly_unbound()
    stale = {
        name: sorted(names - found.get(name, set()))
        for name, names in KNOWN_POSSIBLY_UNBOUND.items()
        if names - found.get(name, set())
    }
    assert not stale, f"these are fixed now and should be removed from KNOWN_POSSIBLY_UNBOUND: {stale}"
