"""gate_math.py — PURE deterministic core for the self-improve harness's scoring/gating logic.

Every function here is referentially transparent: same inputs -> same outputs, zero I/O, zero
side effects, zero imports of os/subprocess/pathlib/requests/urllib/socket. This is the module a
static AST/text import-scan test asserts is free of those imports (mirrors eval-driven-earning's
NFR-ED1 / test_eval_spine_no_io.py pattern — see verification-architecture.md "Pure Core" table).

Traces to behavioral-spec.md:
  - net_usd                  -> REQ-GR2, REQ-EV1
  - apply_score_cap          -> REQ-RH1
  - is_implausible_jump      -> REQ-RH2
  - marker_lines/diff_in_scope -> REQ-DL2
  - scan_denylisted_imports  -> REQ-DL4
  - checksums_match          -> REQ-DL3
  - stage_gate               -> REQ-RH4
  - beats_baseline           -> REQ-RH4, EDGE-2

Do NOT add any I/O import to this file. If a future change needs file/network/subprocess access,
it belongs in scope_guard.py / evaluator.py / promote.py (the effectful shell), never here.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Optional, Tuple

EVOLVE_START_RE = re.compile(r"^\s*#\s*EVOLVE-BLOCK-START\s*$")
EVOLVE_END_RE = re.compile(r"^\s*#\s*EVOLVE-BLOCK-END\s*$")


def net_usd(gross_usd: float, cost_usd: float) -> float:
    """gross - cost. Mirrors skills/_shared/lib/ledger.mjs::deriveLine's earn_usdc - cost_usdc
    exactly (REQ-GR2, REQ-EV1)."""
    return float(gross_usd) - float(cost_usd)


def apply_score_cap(raw_score: float, ceiling: float) -> float:
    """Reward capping (REQ-RH1, Lilian Weng / Amodei et al. defenses against reward hacking):
    never return a value above `ceiling`."""
    return min(float(raw_score), float(ceiling))


def is_implausible_jump(candidate_score: float, population_best: float, multiple: float = 3.0) -> bool:
    """True iff candidate_score > multiple * population_best, for population_best > 0 (REQ-RH2).
    When population_best <= 0 there is no meaningful positive multiple to jump over, so this
    specific trip-wire does not fire (other gates still apply independently)."""
    if population_best <= 0:
        return False
    return float(candidate_score) > float(multiple) * float(population_best)


@dataclass(frozen=True)
class DiffScopeResult:
    in_scope: bool
    out_of_scope_lines: list = field(default_factory=list)


def marker_lines(lines: list) -> Optional[Tuple[int, int]]:
    """Locate EVOLVE-BLOCK-START/END in an already-split (splitlines()) file. Returns 1-indexed
    (start_line, end_line) iff there is EXACTLY ONE well-formed START/END pair (start before end);
    returns None for zero, duplicated, or malformed marker structures (fail-closed callers treat
    None as a scope violation, never guess at a boundary)."""
    starts = [i + 1 for i, l in enumerate(lines) if EVOLVE_START_RE.match(l)]
    ends = [i + 1 for i, l in enumerate(lines) if EVOLVE_END_RE.match(l)]
    if len(starts) != 1 or len(ends) != 1 or ends[0] <= starts[0]:
        return None
    return starts[0], ends[0]


def diff_in_scope(candidate_code: str, baseline_code: str, evolve_block_range: Tuple[int, int]) -> DiffScopeResult:
    """Pure whole-file-text comparison of `candidate_code` against `baseline_code`, OUTSIDE the
    EVOLVE-BLOCK (REQ-DL2). `evolve_block_range` is the BASELINE's own (start, end) 1-indexed
    marker line numbers. The candidate's own EVOLVE-BLOCK markers are located independently (the
    block MAY legitimately grow or shrink in line count — an LLM edit that adds a line inside the
    block must not be misread as an edit to the code that immediately follows it), then everything
    strictly BEFORE the candidate's START and strictly AFTER the candidate's END is compared,
    line-for-line, against the equivalent baseline prefix/suffix. Any mismatch anywhere in the
    fixed region -> in_scope=False. A candidate with zero/duplicated/malformed markers is itself an
    out-of-scope violation (sentinel line number -1).

    Operates on the ACTUAL resulting file text (child_code, whichever way openevolve produced it
    — diff-apply or full-rewrite), never on openevolve's own diff/marker object (not trusted for
    this — see behavioral-spec.md "Scope of the strategy program")."""
    base_lines = baseline_code.splitlines()
    cand_lines = candidate_code.splitlines()
    b_start, b_end = evolve_block_range

    cand_markers = marker_lines(cand_lines)
    if cand_markers is None:
        return DiffScopeResult(in_scope=False, out_of_scope_lines=[-1])
    c_start, c_end = cand_markers

    base_prefix = base_lines[: b_start - 1]
    base_suffix = base_lines[b_end:]
    cand_prefix = cand_lines[: c_start - 1]
    cand_suffix = cand_lines[c_end:]

    out_of_scope: list = []

    max_prefix = max(len(base_prefix), len(cand_prefix))
    for i in range(max_prefix):
        b = base_prefix[i] if i < len(base_prefix) else None
        c = cand_prefix[i] if i < len(cand_prefix) else None
        if b != c:
            out_of_scope.append(i + 1)

    max_suffix = max(len(base_suffix), len(cand_suffix))
    for i in range(max_suffix):
        b = base_suffix[i] if i < len(base_suffix) else None
        c = cand_suffix[i] if i < len(cand_suffix) else None
        if b != c:
            out_of_scope.append(b_end + 1 + i)

    return DiffScopeResult(in_scope=(len(out_of_scope) == 0), out_of_scope_lines=out_of_scope)


def scan_denylisted_imports(code_text: str, denylist_modules: Iterable[str]) -> list:
    """Pure static-text scan (REQ-DL4): which denylisted entries appear as a substring of
    `code_text` (import statement, path, or bare identifier reference — deliberately broad/
    conservative, mirroring genome.mjs's defensive `stripForbidden` philosophy of catching a bad
    reference regardless of exactly how it is written). Returns the list of hits found (empty =
    clean)."""
    return [name for name in denylist_modules if name in code_text]


def checksums_match(before_hash: str, after_hash: str) -> bool:
    """Trivial equality (REQ-DL3). Hash computation itself is effectful (reads files) and lives in
    scope_guard.py; this predicate only compares two already-computed digests."""
    return before_hash == after_hash


def stage_gate(stage1_pass: bool, stage2_pass: bool, tripwire_clear: bool, adversary_verdict: str) -> bool:
    """Promotion gate (REQ-RH4): True iff ALL of stage1 PASS, stage2 PASS, trip-wire clear, AND
    adversary_verdict == "PASS". Any single False/non-PASS input blocks promotion regardless of
    the other three (PROP-SI-RH4's 16-combination truth table)."""
    return bool(stage1_pass) and bool(stage2_pass) and bool(tripwire_clear) and adversary_verdict == "PASS"


def beats_baseline(candidate_score: float, baseline_score: float) -> bool:
    """Strict candidate_score > max(baseline_score, 0), copied verbatim from
    evolve.mjs::evaluatePromotion's absolute-net-positive-floor logic (EDGE-2: a tie, or a
    baseline that is itself losing money, never counts as "beaten" by another non-positive
    score)."""
    return float(candidate_score) > max(float(baseline_score), 0.0)
