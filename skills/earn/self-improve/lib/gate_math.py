"""gate_math.py — PURE deterministic core for the self-improve harness's scoring/gating logic.

Every function here is referentially transparent: same inputs -> same outputs, zero I/O, zero
side effects, zero imports of os/subprocess/pathlib/requests/urllib/socket. This is the module a
static AST/text import-scan test asserts is free of those imports (mirrors eval-driven-earning's
NFR-ED1 / test_eval_spine_no_io.py pattern — see verification-architecture.md "Pure Core" table).

Traces to behavioral-spec.md:
  - net_usd                  -> REQ-GR2, REQ-EV1
  - risk_adjusted_score      -> REQ-EV1/RH1/RH5 (close-loop revision — see its own docstring)
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

# REQ-RL10/RL11 (self-improve-real-ledger): minimum confirmed rows inside the current operating
# window before the realized-ledger trend/realism checks fire at all (below this, a brand-new or
# quiet instance is judged on fixture performance alone — EDGE-RL1/EDGE-RL4). A documented,
# defensible-but-not-empirically-tuned minimum (>=3 rows per half-window split); see
# behavioral-spec.md's UNVERIFIED section for the tunable-constant disclosure.
MIN_REALIZED_ROWS_FOR_TREND = 6


def net_usd(gross_usd: float, cost_usd: float) -> float:
    """gross - cost. Mirrors skills/_shared/lib/ledger.mjs::deriveLine's earn_usdc - cost_usdc
    exactly (REQ-GR2, REQ-EV1)."""
    return float(gross_usd) - float(cost_usd)


def risk_adjusted_score(oos_scores: Iterable[float], eps: float = 1e-9) -> float:
    """Sharpe-like risk-adjusted fitness over a candidate's out-of-sample window scores (close-loop
    Gap 2 fix, replacing a raw-USD `combined_score` for stage2/promotion purposes): mean(oos) /
    max(population_stddev(oos), eps).

    Rationale (Marcos Lopez de Prado, "The Three Types of Backtests" — a strategy's backtest must
    be judged on risk-adjusted, not raw, return, precisely because raw return can be inflated by
    leverage/variance without any genuine edge; Sharpe ratio is the canonical risk-adjusted return
    measure this generalizes) + Lilian Weng, "Reward Hacking in Reinforcement Learning" (a fitness
    that rewards raw magnitude invites reward hacking via variance/leverage amplification rather
    than genuine improvement — exactly what happened to this feature's own real accepted candidate
    `233d923c`, see execution-notes-self-improve.md's "HONEST re-read" section: identical trade
    selection to baseline in every OOS window, stake merely scaled up, inter-window stddev ~5x the
    claimed mean improvement).

    Structural property this buys (proven EXACTLY, not just approximately — see
    test_risk_adjusted_fitness.py::test_risk_adjusted_score_is_invariant_to_uniform_positive_leverage
    and its end-to-end counterpart against the real fixture): for any candidate whose stake
    function is baseline's own decision multiplied by a POSITIVE CONSTANT k (a pure leverage
    change — same trades selected, same weights relative to each other, only overall size
    changed), every oos_scores[i] scales by the same k (net_usd is linear in stake when the
    selected-row set is unchanged), so mean(oos)*k / max(stddev(oos)*k, eps) is EXACTLY
    mean(oos)/max(stddev(oos), eps/k) — and whenever the real stddev clears the `eps` floor (true
    for every realistic dollar-figure backtest; `eps` only matters in the fully-degenerate
    zero-variance case below), that reduces to `mean(oos)*k / (stddev(oos)*k)` = the identical,
    k-independent ratio. Deliberately `max(stddev, eps)` rather than `stddev + eps`: adding a fixed
    eps to a POSITIVE stddev is NOT scale-invariant under multiplication by k (the additive eps
    shrinks in relative terms as k grows, so a leverage-only candidate would keep inching the
    ratio up — a genuine, if tiny, reward-hacking crack); `max(stddev, eps)` has no such term to
    shrink, so the invariance is exact rather than asymptotic. `eps` only ever activates in the
    fully-degenerate case (stddev == 0, i.e. every OOS window scored identically), which is exactly
    the artifact `COMBINED_SCORE_CEILING` (REQ-RH1) exists to cap. A genuine selection change (e.g.
    raising the edge/confidence bar to concentrate on rows where the fixture's real signal is
    strongest) changes WHICH trades are selected, which can genuinely raise the ratio — this is the
    only way `risk_adjusted_score` rewards a candidate. Population (not sample) stddev is used
    (divide by n, not n-1): the ≥3 window pairs (REQ-EV3) are the full outcome set being scored, not
    a sample estimating a larger population.

    Returns 0.0 for an empty `oos_scores` (consistent with FAIL_SENTINEL's fail-closed convention
    — REQ-EV6)."""
    scores = [float(s) for s in oos_scores]
    if not scores:
        return 0.0
    mean = sum(scores) / len(scores)
    variance = sum((s - mean) ** 2 for s in scores) / len(scores)
    stddev = variance ** 0.5
    return mean / max(stddev, eps)


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


def realized_window_split(
    rows: Iterable[Tuple[float, float]], window_start_ts: float, window_end_ts: float
) -> dict:
    """REQ-RL8: pure aggregation over already-filtered (ts, net_usdc) pairs (the caller's job, via
    ledger_reader.is_confirmed, is impure). Splits `[window_start_ts, window_end_ts)` at its
    temporal MIDPOINT into two halves. `row_count` = rows falling inside the window at all."""
    midpoint = (float(window_start_ts) + float(window_end_ts)) / 2.0
    first_half_net_usd = 0.0
    second_half_net_usd = 0.0
    row_count = 0
    for ts, net_usdc in rows:
        ts = float(ts)
        if ts < window_start_ts or ts >= window_end_ts:
            continue
        row_count += 1
        if ts < midpoint:
            first_half_net_usd += float(net_usdc)
        else:
            second_half_net_usd += float(net_usdc)
    return {
        "window_net_usd": first_half_net_usd + second_half_net_usd,
        "first_half_net_usd": first_half_net_usd,
        "second_half_net_usd": second_half_net_usd,
        "row_count": row_count,
    }


def is_worsening_trend(first_half_net_usd: float, second_half_net_usd: float) -> bool:
    """REQ-RL9: strictly `second_half_net_usd < first_half_net_usd`."""
    return float(second_half_net_usd) < float(first_half_net_usd)


def realized_trend_blocks(window_net_usd: float, worsening: bool, sufficient: bool) -> bool:
    """REQ-RL10: `sufficient AND window_net_usd < 0.0 AND worsening`. When `sufficient` is False
    (too few confirmed rows in the current operating window) this specific check never fires —
    independent of REQ-RL7's `resolved` gate, which is about identity/path resolution, not data
    volume."""
    return bool(sufficient) and float(window_net_usd) < 0.0 and bool(worsening)


def data_realism_gap(
    mean_backtest_net_usd: float,
    mean_realized_net_per_row: float,
    sufficient: bool,
    multiple: float = 3.0,
) -> bool:
    """REQ-RL11: True (contradiction — BLOCK) when `sufficient` is True AND either (a) the
    fixture backtest claims a real edge while the real, sufficiently-sampled track record shows
    none (`mean_realized_net_per_row <= 0.0 AND mean_backtest_net_usd > 0.0`), OR (b) the real
    per-trade edge is implausibly smaller than the fixture's claimed one (REUSE of
    `is_implausible_jump`, REQ-RH2, repurposed here as fixture-vs-reality rather than
    candidate-vs-population)."""
    if not sufficient:
        return False
    mean_backtest_net_usd = float(mean_backtest_net_usd)
    mean_realized_net_per_row = float(mean_realized_net_per_row)
    if mean_realized_net_per_row <= 0.0 and mean_backtest_net_usd > 0.0:
        return True
    if mean_realized_net_per_row > 0.0 and is_implausible_jump(
        mean_backtest_net_usd, mean_realized_net_per_row, multiple
    ):
        return True
    return False
