#!/usr/bin/env python3
"""Detect a feature that predicts what the loop CHOOSES but not what
actually WINS -- the signature of optimising a proxy instead of the goal.

Why this exists: spec 47 section 19-4a, second half. Section 1's problem #8
(a measurement-report headline shipped over three stronger candidates) had a
concrete shape: the selection rule liked "we tested N things, X% happened"
titles regardless of whether real readers did. That is Goodhart's Law
in miniature -- a proxy feature the SELECTION step rewards without the
JUDGE (standing in for the reader) rewarding it back. This script makes
that pattern mechanically detectable instead of something a human has to
notice by eye, by comparing two numbers per feature:
  chosen_rate = how much more often the feature appears in what we
                CHOSE than in what we REJECTED (a positive number means our
                selection step likes this feature)
  win_lift    = how much more the feature actually helps against real
                opponents (mean beat_rate with it minus without it)
A feature the loop keeps choosing (chosen_rate > 0) that does not actually
win (win_lift <= 0) is optimising a proxy, not the goal -- flag it.

Features are computed from title TEXT ALONE, no model calls, deliberately
"dumb" per the coordinator's spec so they stay inspectable:
  has_number, has_percent, is_negation, is_first_person, names_reader,
  is_measurement_report (has_number AND a comparison word).

Design choices made because the spec left them open (simplest option, noted
here rather than asked about):
  * English negation/first-person/reader-address markers (not, never, stop,
    no, I, my, me, you, your) are matched as WHOLE TOKENS via a simple
    regex word split, not bare substrings -- "no" or "I" as a substring
    would false-positive inside ordinary words ("technology", "chief").
    Japanese markers (ではない, 僕, 私, 俺, あなた, な人へ) are matched as
    plain substrings, same as harvest_corpus.py's CJK detection precedent
    -- there is no cheap word-boundary concept for unsegmented Japanese
    text, and these markers are distinctive enough not to need one.
  * is_measurement_report's comparison words (tested, benchmark, faster,
    shorter, longer, 比べ, 測) ARE matched as plain casefolded substrings --
    they are long/distinctive enough that the collision risk a bare "no"
    or "I" has does not apply, so the simpler check is used.
  * "clearly positive" chosen_rate is implemented as chosen_rate > 0 --
    the spec does not give a numeric threshold beyond the sign, and the
    sample-size floor is what actually protects against noise.
  * The sample-size floor applies to ALL FOUR relevant counts at once
    (n_chosen, n_rejected, n_with_feature, n_without_feature) -- both
    ratios (chosen_rate and win_lift) need both their sides above the
    floor before either number is trusted enough to flag anything on.

INPUT: every <run-dir>/gates/beat-rate-<lang>.json under a state root
(default skills/writer-agent/state/runs), scanned recursively -- same
input surface as rule_blame.py, computed independently (no shared module,
matching the sibling-script isolation already used by title_candidates.py /
harvest_corpus.py / beat_rate.py).

OUTPUT: one JSON object (all features, every number, every sample size)
plus a human-readable table, printed by `goodhart.py report`.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_MIN_SAMPLE = 5

_DIGIT_RE = re.compile(r"\d")
_WORD_RE = re.compile(r"[A-Za-z']+")

_NEGATION_JA = ("ではない", "じゃない")
_NEGATION_EN = {"not", "never", "stop", "no"}

_FIRST_PERSON_JA = ("僕", "私", "俺")
_FIRST_PERSON_EN = {"i", "my", "me"}

_NAMES_READER_JA = ("な人へ", "あなた")
_NAMES_READER_EN = {"you", "your"}

_MEASUREMENT_JA = ("比べ", "測")
_MEASUREMENT_EN = ("tested", "benchmark", "faster", "shorter", "longer")


def _english_tokens(title: str) -> set:
    return {word.lower() for word in _WORD_RE.findall(title or "")}


def has_number(title: str) -> int:
    return 1 if _DIGIT_RE.search(title or "") else 0


def has_percent(title: str) -> int:
    text = title or ""
    return 1 if ("%" in text or "パーセント" in text) else 0


def is_negation(title: str) -> int:
    text = title or ""
    if any(marker in text for marker in _NEGATION_JA):
        return 1
    return 1 if _english_tokens(text) & _NEGATION_EN else 0


def is_first_person(title: str) -> int:
    text = title or ""
    if any(marker in text for marker in _FIRST_PERSON_JA):
        return 1
    return 1 if _english_tokens(text) & _FIRST_PERSON_EN else 0


def names_reader(title: str) -> int:
    text = title or ""
    if any(marker in text for marker in _NAMES_READER_JA):
        return 1
    return 1 if _english_tokens(text) & _NAMES_READER_EN else 0


def is_measurement_report(title: str) -> int:
    text = title or ""
    if not has_number(text):
        return 0
    if any(marker in text for marker in _MEASUREMENT_JA):
        return 1
    lowered = text.casefold()
    return 1 if any(marker in lowered for marker in _MEASUREMENT_EN) else 0


FEATURE_FUNCS = {
    "has_number": has_number,
    "has_percent": has_percent,
    "is_negation": is_negation,
    "is_first_person": is_first_person,
    "names_reader": names_reader,
    "is_measurement_report": is_measurement_report,
}
FEATURE_NAMES = tuple(FEATURE_FUNCS.keys())


# ---------------------------------------------------------------------------
# Small pure functions -- these are what the contract test drives directly.
# ---------------------------------------------------------------------------

def compute_feature_stats(name: str, candidates: list[dict], min_sample: int) -> dict:
    """chosen_rate, win_lift, sample sizes, and status for one feature over
    a flat list of {"title", "role", "beat_rate"} candidates."""
    feature_fn = FEATURE_FUNCS[name]
    chosen = [c for c in candidates if c.get("role") == "chosen"]
    rejected = [c for c in candidates if c.get("role") == "rejected"]
    with_feature = [c for c in candidates if feature_fn(c.get("title", "")) == 1]
    without_feature = [c for c in candidates if feature_fn(c.get("title", "")) == 0]

    n_chosen, n_rejected = len(chosen), len(rejected)
    n_with, n_without = len(with_feature), len(without_feature)

    chosen_rate = None
    if n_chosen and n_rejected:
        p_chosen = sum(feature_fn(c.get("title", "")) for c in chosen) / n_chosen
        p_rejected = sum(feature_fn(c.get("title", "")) for c in rejected) / n_rejected
        chosen_rate = p_chosen - p_rejected

    win_lift = None
    if n_with and n_without:
        win_lift = (
            sum(c.get("beat_rate", 0.0) for c in with_feature) / n_with
            - sum(c.get("beat_rate", 0.0) for c in without_feature) / n_without
        )

    insufficient = min(n_chosen, n_rejected, n_with, n_without) < min_sample
    if insufficient or chosen_rate is None or win_lift is None:
        status = "insufficient_data"
    elif chosen_rate > 0 and win_lift <= 0:
        status = "flag"
    else:
        status = "ok"

    return {
        "feature": name,
        "chosen_rate": chosen_rate,
        "win_lift": win_lift,
        "n_chosen": n_chosen,
        "n_rejected": n_rejected,
        "n_with_feature": n_with,
        "n_without_feature": n_without,
        "status": status,
    }


def compute_all_features(candidates: list[dict], min_sample: int) -> list[dict]:
    return [compute_feature_stats(name, candidates, min_sample) for name in FEATURE_NAMES]


def format_report_table(rows: list[dict]) -> str:
    header = (
        f"{'feature':<22} {'chosen_rate':>12} {'win_lift':>10} "
        f"{'n_chosen':>9} {'n_rejected':>10} {'n_with':>7} {'n_without':>10}  status"
    )
    lines = [header]
    for row in rows:
        chosen_rate = "-" if row["chosen_rate"] is None else f"{row['chosen_rate']:+.3f}"
        win_lift = "-" if row["win_lift"] is None else f"{row['win_lift']:+.3f}"
        lines.append(
            f"{row['feature']:<22} {chosen_rate:>12} {win_lift:>10} "
            f"{row['n_chosen']:>9} {row['n_rejected']:>10} {row['n_with_feature']:>7} "
            f"{row['n_without_feature']:>10}  {row['status']}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Disk scanning (impure) -- everything above this line is what the contract
# test drives directly with in-memory fixtures.
# ---------------------------------------------------------------------------

def load_candidates_from_runs(state_root: Path) -> list[dict]:
    """Every {title, role, beat_rate} triple from every beat-rate-<lang>.json
    under state_root, across all runs and languages -- goodhart looks for a
    proxy signature in the aggregate, not per-run."""
    rows: list[dict] = []
    if not state_root.exists():
        return rows
    for path in sorted(state_root.glob("**/gates/beat-rate-*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for candidate in data.get("candidates", []):
            title = candidate.get("title")
            role = candidate.get("role")
            beat_rate = candidate.get("beat_rate")
            if title is None or role not in ("chosen", "rejected") or beat_rate is None:
                continue
            # A candidate whose pairs all came back inconclusive reports
            # beat_rate 0.0, which is a judge outage wearing the costume of a
            # loss (see beat_rate.py's scorable_pairs and spec 47 section
            # 21.42). Feeding those zeros into win_lift would let an outage
            # depress whatever features those titles happened to carry and
            # manufacture a proxy flag out of downtime. Older files predate
            # the field; absent means "not known to be unscored", which keeps
            # historical rows usable.
            if candidate.get("scorable_pairs") == 0:
                continue
            rows.append({"title": title, "role": role, "beat_rate": beat_rate})
    return rows


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _default_state_root() -> Path:
    return Path(__file__).resolve().parent.parent / "state" / "runs"


def cmd_report(args: argparse.Namespace) -> int:
    state_root = Path(args.state_root) if args.state_root else _default_state_root()
    candidates = load_candidates_from_runs(state_root)
    rows = compute_all_features(candidates, args.min_sample)
    print(json.dumps({"min_sample": args.min_sample, "sample_size": len(candidates), "features": rows}, ensure_ascii=False))
    print()
    print(format_report_table(rows))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_report = sub.add_parser("report", help="flag features that are chosen often but do not actually win")
    p_report.add_argument("--state-root", default=None)
    p_report.add_argument("--min-sample", type=int, default=DEFAULT_MIN_SAMPLE)

    args = parser.parse_args(argv)
    if args.command == "report":
        return cmd_report(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
