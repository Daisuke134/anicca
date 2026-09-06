"""The public-page readback waits as long as every other transient reader in this loop.

Four of the eight failures fixed on 2026-09-06 were one recoverable read ending a whole
wake, and each came from a reader whose retry was shorter than the loop's own standard --
five attempts three seconds apart, the shape `_read_official_catalog` carries with its
reasoning written beside it. `_observe_own_page` was the last reader of a rendering page
still on three attempts two seconds apart.

The short sleeps that remain are deliberate, and this file makes "deliberate" checkable:
each one must say beside it why it is short.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _source(name: str) -> str:
    return (SCRIPTS / f"{name}.py").read_text(encoding="utf-8")


def test_the_public_page_readback_uses_the_standard_window():
    source = _source("storefront_direct")
    block = source[source.index("_own_page_readback_valid(observed, service_id, expected_image_count)") - 400:]
    block = block[:600]
    assert "for attempt in range(5)" in block
    assert "if attempt < 4" in block
    assert "time.sleep(3)" in block


def test_the_nested_snapshot_retry_says_why_it_stays_short():
    # `_seller_snapshot_from_fresh_tab` wraps `_seller_snapshot_for`, which already waits the
    # full window. Widening it would nest one retry inside another.
    assert "nest one retry inside another" in _source("storefront_direct")


@pytest.mark.parametrize("name", ["storefront_direct", "storefront_draft"])
def test_the_standard_shape_is_present_in_both_files(name):
    source = _source(name)
    assert "for attempt in range(5)" in source
    assert "if attempt < 4" in source


@pytest.mark.parametrize("name", ["storefront_direct", "storefront_draft"])
def test_no_retry_sleeps_for_less_than_a_second(name):
    # A retry with no wait asks the same unfinished page again immediately. Sub-second waits
    # are the shape that produced today's failures in their most extreme form.
    assert not [v for v in re.findall(r"time\.sleep\(([0-9.]+)\)", _source(name)) if float(v) < 1]
