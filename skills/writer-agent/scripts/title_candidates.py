#!/usr/bin/env python3
"""Persist every title candidate, chosen and rejected, with the rule that killed it.

Why this exists: on 2026-07-26 the loop shipped a measurement-report headline and
threw away three stronger ones. Finding the culprit took a human reading the
rejection reasons and then grepping the skill for the rule behind each. Both
halves of that are mechanical if the rejections are recorded properly, so this
script makes the recording a hard contract:

  * a rejection must cite the FILE AND LINE of the rule it applied, so blame
    lands on a specific line instead of on a vibe, and
  * a rejection must be stated in reader-side words, because "does not match the
    pattern" is the failure mode itself -- form-compliance standing in for
    reader effect is what inverted the ranking in the first place.

The stored pairs are also the training data: every rejected candidate is a free
counterfactual for the beat-rate gate (spec 47 section 19), so nothing is
thrown away.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

MIN_CANDIDATES = 5
MIN_REASON_CHARS = 10
CITED_RULE = re.compile(r"^[A-Za-z0-9_./-]+:[0-9]+$")

# Rejection reasons that describe the rulebook instead of the reader. These are
# refused outright -- the whole defect class is a form rule masquerading as a
# quality judgement.
FORM_REASONS = (
    "型でない",
    "型に合わ",
    "型に当てはま",
    "パターンに合致",
    "skill が禁止",
    "skillが禁止",
    "スキルが禁止",
    "規約違反",
    "does not match the pattern",
    "not one of the patterns",
    "skill prohibits",
    "skill forbids",
    "against the skill",
    "violates the rule",
)


class CandidateError(ValueError):
    """The candidate record does not satisfy the contract."""


def _check_rejection(index: int, entry: dict) -> None:
    title = str(entry.get("title", "")).strip()
    if not title:
        raise CandidateError(f"rejected[{index}] has no title")
    reason = str(entry.get("reason", "")).strip()
    if len(reason) < MIN_REASON_CHARS:
        raise CandidateError(
            f"rejected[{index}] ({title}): reason must say, in reader-side words, "
            f"why a stranger would not click -- got {reason!r}"
        )
    lowered = reason.casefold()
    for marker in FORM_REASONS:
        if marker.casefold() in lowered:
            raise CandidateError(
                f"rejected[{index}] ({title}): {marker!r} describes the rulebook, "
                "not the reader. Say what the reader would fail to get."
            )
    cited = str(entry.get("cited_rule", "")).strip()
    if not CITED_RULE.match(cited):
        raise CandidateError(
            f"rejected[{index}] ({title}): cited_rule must be <file>:<line> "
            f"pointing at the rule applied -- got {cited!r}"
        )


def validate(record: dict) -> dict:
    """Raise CandidateError unless the record can carry blame to a rule line."""
    chosen = record.get("chosen")
    if not isinstance(chosen, dict) or not str(chosen.get("title", "")).strip():
        raise CandidateError("chosen.title is required")
    if len(str(chosen.get("why", "")).strip()) < MIN_REASON_CHARS:
        raise CandidateError(
            "chosen.why must say why a stranger would click, in reader-side words"
        )
    rejected = record.get("rejected")
    if not isinstance(rejected, list):
        raise CandidateError("rejected must be a list")
    total = 1 + len(rejected)
    if total < MIN_CANDIDATES:
        raise CandidateError(
            f"{total} candidates recorded; at least {MIN_CANDIDATES} are required "
            "so the gate has counterfactuals to score"
        )
    for index, entry in enumerate(rejected):
        if not isinstance(entry, dict):
            raise CandidateError(f"rejected[{index}] must be an object")
        _check_rejection(index, entry)
    return record


def _load(source: str) -> dict:
    text = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise CandidateError(f"input is not JSON: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("record", "validate"))
    parser.add_argument("--json", default="-", help="candidate JSON file, or - for stdin")
    parser.add_argument("--run-dir", help="run directory to write into (record only)")
    parser.add_argument("--lang", default="ja")
    args = parser.parse_args(argv)

    try:
        record = validate(_load(args.json))
    except CandidateError as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 3

    if args.command == "validate":
        print(json.dumps({"ok": True, "candidates": 1 + len(record["rejected"])}))
        return 0

    if not args.run_dir:
        print("FATAL: record requires --run-dir", file=sys.stderr)
        return 2
    record["lang"] = args.lang
    # Under gates/, where every other run artifact lives (STEP 0.6) and where
    # score-latest-run.sh looks for it. Writing to the run-dir root instead
    # meant the ledger would be produced every morning and found by nobody --
    # the scorer would report "no run directory carries a ledger" and the whole
    # chain would no-op while looking healthy (caught 2026-07-27, before the
    # first run that would have written one).
    out = Path(args.run_dir) / "gates" / f"title-candidates-{args.lang}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "path": str(out), "candidates": 1 + len(record["rejected"])}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
