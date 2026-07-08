# Impl Review Findings — self-improve-real-ledger (Phase 3, iteration 2)

Reviewer: fresh-context VCSDD adversary (Opus). File write blocked by harness guard; persisted
verbatim by orchestrator. VERDICT: PASS, 0 blocking, 0 major, 5 minor, SAFE_TO_DEPLOY.

## F-1 (iter1 BLOCKING) — genuinely FIXED (independently re-derived)
promote_gate_run.py:243-245 now binds mean_backtest_net_usd=assessment["mean_oos_net_usd"]
(verified dollar-scale via evaluator.py:193). None-safety: compute_realized_gate short-circuits
realism_gap_blocks=False when None (promote_gate.py:226-230), other gates unaffected — matches
spec's conservative framing. 3 new regression tests (AST field-pinning, realistic-scale
field-sensitivity $0.30-vs-2.5, None-safety) verified falsifiable; RED→GREEN evidence genuine.

## Re-executed evidence (fresh)
worktree self-improve: 83 passed 1 failed (= EDGE-RL5b artifact, reason matches docs verbatim);
hl-trade 41+1skip; node 21/21; run_evolve.sh byte-identical to main (REQ-RL16).

## Anti-stub judgment (CRIT-004/REQ-RL17 second half) — performed
All three decide_promotion call sites (253 / 268-273 / 280-285) bind the SAME realized_gate local
computed ONCE at 243-245 via the real chain resolve_ledger_path → confirmed_net_series (real I/O)
→ last_promotion_ts (real git subprocess) → pure gate_math. No stub/literal anywhere.
F-5 bypass closure hand-traced: both import forms produce non-empty denylist matches.
DENYLIST_MODULES: 25 pre-existing entries byte-identical, 8 new appended (INV-RL3 holds).

## Structural/money-safety
Every new symbol ≥2 non-test references (no orphans). All "w"/"a" writes are run_dir artifacts;
zero earn-ledger writes; wallet-key strings only as declarative denylist entries; no spend-cap
references.

## Minor (5, non-blocking)
1. REQ-RL12 integration (matching repo/BASELINE_PATH pair) never exercised in-tests — deferred to
   PROP-RL-LIVE2 post-merge live tier. 2. MIN_REALIZED_ROWS boundary 5-vs-6 untested (single >=).
3. clock-skew window untested (safe by construction, row_count=0). 4. two time.time() calls ms
   apart (immaterial). 5. PROP-RL-MIR1 node -e cross-language check not executable (manual parity
   re-confirmed).
