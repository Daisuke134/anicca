"""`prepare_draft` and `readback_published_draft` must agree on what is retryable.

Both open a draft page and compare a snapshot to the contract. `readback_published_draft`
already retried `storefront_draft_readback_mismatch`; `prepare_draft` did not, so the same
error on the same page ended the wake in one function and was absorbed in the other. The
contract named the right draft in every observed case -- the snapshot's url/action simply
still named the page the tab was on a moment before.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

SOURCE = (Path(__file__).resolve().parents[1] / "scripts" / "storefront_draft.py").read_text(
    encoding="utf-8")

TRANSIENTS = (
    "storefront_draft_category_option_missing",
    "storefront_draft_readback_mismatch",
)


def _bodies() -> dict[str, str]:
    """The source of each function, sliced at the next top-level `def`."""
    out = {}
    for name in ("prepare_draft", "readback_published_draft"):
        start = SOURCE.index(f"def {name}(")
        rest = SOURCE[start + 1:]
        end = rest.find("\ndef ")
        out[name] = rest[:end if end != -1 else len(rest)]
    return out


def test_both_functions_were_found():
    bodies = _bodies()
    assert len(bodies) == 2
    assert all(len(body) > 500 for body in bodies.values())


@pytest.mark.parametrize("name", ["prepare_draft", "readback_published_draft"])
@pytest.mark.parametrize("transient", TRANSIENTS)
def test_each_function_retries_both_transients(name, transient):
    body = _bodies()[name]
    assert "retryable" in body, f"{name} has no retryable set at all"
    assert transient in body, (
        f"{name} does not treat {transient} as retryable; the same error on the same page "
        "must not end the wake in one function and be absorbed in the other.")


@pytest.mark.parametrize("name", ["prepare_draft", "readback_published_draft"])
def test_nothing_else_was_quietly_made_retryable(name):
    body = _bodies()[name]
    retried = set(re.findall(r'startswith\("(storefront_[a-z_]+)"\)', body))
    assert retried == set(TRANSIENTS), retried
