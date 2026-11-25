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


def extract_quote_text(hierarchy: str):
    """Return the visible text of the quote-text element, or None.

    Tolerant of both serializations Maestro emits (XML-ish attribute
    lists and indented node lines): find the node mentioning the id,
    then read a text-ish attribute from that same node span.
    """
    if not hierarchy:
        return None
    # Node spans: split on '<' for XML-ish dumps; if the dump is an
    # indented text tree, each line is a node.
    if "<" in hierarchy:
        spans = hierarchy.split("<")
    else:
        spans = hierarchy.splitlines()
    for span in spans:
        if QUOTE_ID not in span:
            continue
        for attr in TEXT_ATTRS:
            m = re.search(attr + r'="([^"]*)"', span)
            if m and m.group(1).strip():
                return m.group(1).strip()
        # Node found but carries no text attribute in this span; on
        # iOS the text may sit in a child node — keep looking at the
        # following spans until the next sibling with an id appears.
        idx = spans.index(span)
        for nxt in spans[idx + 1 : idx + 4]:
            if 'id="' in nxt or "accessibilityIdentifier" in nxt:
                break
            for attr in TEXT_ATTRS:
                m = re.search(attr + r'="([^"]*)"', nxt)
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
