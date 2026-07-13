#!/usr/bin/env python3
"""
ASO candidate linter for Anicca.

Usage:
    python3 lint.py <candidates.json> <baseline-en-US.json>

Exit 0 if all candidates pass lint, 1 otherwise. Prints a JSON report to stdout.
"""
import json
import sys
from typing import Any

LIMITS = {"name": 30, "subtitle": 30, "keywords": 100, "promotional_text": 170}
BANNED_WORDS = {"#1", "best app", "top app"}  # avoid Apple 2.3.7 flags; "free" is allowed because we sell a trial
BRAND_REQUIRED = "anicca"
TITLE_EDIT_DISTANCE_MAX = 5

LOCALES = ["en-US", "ja", "de-DE", "es-ES", "fr-FR", "pt-BR"]


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + (ca != cb))
        prev = curr
    return prev[-1]


def lint_locale(locale: str, candidate: dict[str, Any], baseline_name: str) -> list[str]:
    errors: list[str] = []
    for field, limit in LIMITS.items():
        v = candidate.get(field, "")
        if len(v) > limit:
            errors.append(f"{locale} {field} length {len(v)} > {limit}")
    name = candidate.get("name", "")
    if BRAND_REQUIRED not in name.lower():
        errors.append(f"{locale} title missing 'anicca'")
    if levenshtein(name, baseline_name) > TITLE_EDIT_DISTANCE_MAX:
        errors.append(f"{locale} title edit distance {levenshtein(name, baseline_name)} > {TITLE_EDIT_DISTANCE_MAX}")
    blob = " ".join([candidate.get(k, "") for k in LIMITS]).lower()
    for w in BANNED_WORDS:
        if w in blob:
            errors.append(f"{locale} contains banned phrase '{w}'")
    return errors


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: lint.py <candidates.json> <baseline-en-US.json>", file=sys.stderr)
        return 2
    candidates = json.load(open(sys.argv[1]))
    baseline = json.load(open(sys.argv[2]))

    report = {"results": []}
    overall_pass = True
    for idx, cand in enumerate(candidates.get("candidates", [])):
        cand_errors: dict[str, list[str]] = {}
        for locale in LOCALES:
            loc_cand = cand["locales"].get(locale)
            if not loc_cand:
                cand_errors[locale] = [f"{locale} missing"]
                continue
            base_name = baseline.get(locale, {}).get("name", "") if isinstance(baseline, dict) and locale in baseline else baseline.get("name", "") if isinstance(baseline, dict) else ""
            errors = lint_locale(locale, loc_cand, base_name)
            if errors:
                cand_errors[locale] = errors
        report["results"].append({"candidate_index": idx, "errors": cand_errors})
        if any(cand_errors.values()):
            overall_pass = False

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
