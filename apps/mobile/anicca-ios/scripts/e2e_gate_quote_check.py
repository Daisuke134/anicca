#!/usr/bin/env python3
"""Compare the living-home quote text between two Maestro hierarchy dumps.

Usage: e2e_gate_quote_check.py HIERARCHY_T0 HIERARCHY_T1

Maestro has no text-extraction assertion, so the "words change on
their own" gate check reads the accessibility hierarchy the runner
dumps at T0 and T1 (35s apart, app in foreground, deck dwell ~20s)
and compares the text carried by the element identified as
`quote-text`.

Prints a JSON verdict on stdout:
  {"status": "passed"|"failed", "t0": <text|null>, "t1": <text|null>,
   "detail": "..."}
Exit code is always 0; the caller (run-e2e-gate.sh) folds the verdict
into gate-result.json and decides the run's exit code. "Cannot
extract" is a FAILED verdict, never a silent pass: if we cannot prove
the words changed, the gate does not certify the build.
"""

import json
import re
import sys

QUOTE_ID = "quote-text"
# Attribute names Maestro / XCTest hierarchies use for visible text,
# in the order we trust them.
TEXT_ATTRS = ("accessibilityText", "text", "value", "label")


def _node_text(node):
    attrs = node.get("attributes") or {}
    for attr in TEXT_ATTRS:
        value = attrs.get(attr)
        if value and str(value).strip():
            return str(value).strip()
    return None


def _find_quote_text(node):
    """Depth-first: the quote-text node's own text, else its subtree's."""
    if not isinstance(node, dict):
        return None
    attrs = node.get("attributes") or {}
    if attrs.get("resource-id") == QUOTE_ID:
        text = _node_text(node)
        if text:
            return text
        for child in node.get("children") or []:
            text = _find_quote_text(child)
            if text:
                return text
        return None
    for child in node.get("children") or []:
        text = _find_quote_text(child)
        if text:
            return text
    return None


def extract_quote_text(hierarchy: str):
    """Return the visible text of the quote-text element, or None.

    `maestro hierarchy` on iOS emits a JSON tree
    ({"attributes": {"resource-id": ..., "accessibilityText": ...},
    "children": [...]}) — parse it as JSON. (The first version of
    this checker regex-searched for XML-style attr="value" pairs and
    could never match the JSON serialization; run 45682131989's T0
    dump contained the quote yet extraction failed.) The regex path
    below remains only as a fallback for non-JSON dumps.
    """
    if not hierarchy:
        return None
    try:
        tree = json.loads(hierarchy)
    except json.JSONDecodeError:
        tree = None
    if tree is not None:
        return _find_quote_text(tree)
    for span in hierarchy.split("<") if "<" in hierarchy \
            else hierarchy.splitlines():
        if QUOTE_ID not in span:
            continue
        for attr in TEXT_ATTRS:
            m = re.search(attr + r'="([^"]*)"', span)
            if m and m.group(1).strip():
                return m.group(1).strip()
        return None
    return None


def main() -> int:
    with open(sys.argv[1], encoding="utf-8", errors="replace") as f:
        h0 = f.read()
    with open(sys.argv[2], encoding="utf-8", errors="replace") as f:
        h1 = f.read()
    t0 = extract_quote_text(h0)
    t1 = extract_quote_text(h1)
    if t0 is None or t1 is None:
        verdict = {
            "status": "failed",
            "t0": t0,
            "t1": t1,
            "detail": "quote-text element text not extractable from hierarchy dump(s)",
        }
    elif t0 != t1:
        verdict = {
            "status": "passed",
            "t0": t0,
            "t1": t1,
            "detail": "quote text changed on its own during the 35s foreground wait",
        }
    else:
        verdict = {
            "status": "failed",
            "t0": t0,
            "t1": t1,
            "detail": "quote text identical after 35s in foreground — living home did not advance",
        }
    print(json.dumps(verdict, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
