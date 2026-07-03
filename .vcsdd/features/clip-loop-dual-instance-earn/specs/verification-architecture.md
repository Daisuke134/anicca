# Verification Architecture — clip-loop-dual-instance-earn (Phase 1b)

## Purity boundary map

| Layer | Purity | Location |
|---|---|---|
| Path resolution (`_instance_paths.sh`) | **PURE** — deterministic function of env vars (`ANICCA_INSTANCE`, `EARN_LEDGER`, `HOME`), no I/O, no side effects | `~/anicca/skills/earn/clip/_instance_paths.sh` |
| Queue/posted/ledger read-write | IMPURE (filesystem I/O) | `producer.sh`, `run.sh`, `monitor.sh` |
| Account/browser interaction | IMPURE (network + CDP) | `run.sh` → `ig-reels-poster/scripts/post_reel.py` |
| Wallet keygen (out of scope for THIS feature, tracked for the follow-on provisioning feature) | IMPURE (crypto RNG) | future `clip-loop-clawrouter-provision` |

The purity boundary is exactly `_instance_paths.sh`: everything downstream of it (producer/run/monitor)
is impure I/O that CONSUMES the resolved paths but never re-derives them independently — this is the
seam that isolation correctness (REQ-001..004) is provable at.

## Proof obligations

| ID | Requirement | Tier | Required (lean) | Verification method |
|---|---|---|---|---|
| PROP-001 | REQ-001 (default paths unchanged) | 1 (unit) | true | `tests/test_instance_paths.sh` case 1: source with `ANICCA_INSTANCE` unset, assert exact string equality against the 4 pre-feature hardcoded paths |
| PROP-002 | REQ-002 (suffixed paths distinct) | 1 (unit) | true | same test, case 2: source with `ANICCA_INSTANCE=clawrouter`, assert suffix present AND assert inequality vs. default |
| PROP-003 | REQ-003 (EARN_LEDGER override wins) | 1 (unit) | true | same test, case 3: both vars set, assert `CLIP_LEDGER` equals the override verbatim |
| PROP-004 | REQ-004 (N-instance distinctness) | 2 (integration) | true | script that resolves paths for a list of instance names (`""`, `myclaude`, `clawrouter`, `clawrouter-2`) and asserts all 4×N path sets are pairwise disjoint (set-based check, not eyeballing) |
| PROP-005 | REQ-005 (no model-specific branching, WORKER layer only: `producer.sh`/`run.sh`/`monitor.sh`/`_instance_paths.sh` — `clip-cli.sh` and any other per-instance LAUNCHER are explicitly out of scope, see REQ-005's carve-out) | 1 (static grep, heuristic) + 3 (manual read, authoritative) | true | ★ REVISED after iteration-3 finding: a single-line regex (even one requiring `if`/`elif`/`case` on the same line) is UNSOUND against idiomatic multi-line shell `case "$X" in / claude) ... ;; esac` blocks, and also false-triggers on the plain English word "case" inside comments (e.g. "case 1: ..."). A perfectly sound static check is not achievable with grep on shell source. Two-tier check instead: (a) **heuristic pre-check** — `grep -inE '\b(if|elif|case)\b' producer.sh run.sh monitor.sh _instance_paths.sh \| grep -iE "claude\|sonnet\|clawrouter\|anthropic\|blockrun"` as a fast smell-test, not proof; (b) **authoritative check** — the Phase 3 fresh-context adversary manually reads all four WORKER files in full (each is under 100 lines, a fully tractable manual read) and confirms zero conditionals of any shape (single- or multi-line `if`/`case`) branch on model/provider identity. (b) is what actually gates Phase 3 PASS; (a) only flags obvious cases early. |
| PROP-006 | REQ-006 (wallet/account zero-overlap, checkable) | 2 (integration, deferred to follow-on feature) | false (lean, deferred) | out of scope for this feature's Phase 2/3 — the follow-on provisioning feature must implement + prove an actual distinctness checker before creating a second live wallet |
| PROP-007 | REQ-007 (no-human account provisioning) | 0 (already proven, cite prior evidence) | false | already E2E-proven 2026-06-29 (`reference_ig_account_create_skill_daily_driver.md`, live @aiclipsvault) — concrete reference check: `grep -n "post_reel.py\|cdp_incognito.py\|ig-account-create" ~/anicca/skills/earn/clip/{run.sh,producer.sh}` must show ONLY calls into the already-proven `ig-account-create`/`ig-reels-poster` skills, zero calls into any new/unproven signup path |
| PROP-008 | REQ-008 (empty-state safety, no cross-instance fallback, BOTH run.sh AND monitor.sh) | 2 (integration) | true | (a) run `run.sh` with `ANICCA_INSTANCE=clawrouter-e2e-probe` (no queue/accounts files yet) in `EARN_MODE=discover`; assert stdout reports `nothing to post` AND assert it did NOT touch the real myclaude queue (mtime/content diff before/after). (b) run `monitor.sh` with the SAME `ANICCA_INSTANCE=clawrouter-e2e-probe`; assert it reports the probe instance's (empty) ledger/accounts state and does NOT print any myclaude ledger line or myclaude account handle — this sub-check is the one PROP-005's grep cannot catch (grep proves no model-name branching, not that monitor.sh sources `_instance_paths.sh` at all), so it is REQUIRED, not optional, and blocks Phase 3 PASS if `monitor.sh` has not yet been updated to source `_instance_paths.sh`. |

## Verification tiers legend
- Tier 0: cite existing evidence, no new work.
- Tier 1: unit test, deterministic, no external I/O.
- Tier 2: integration test, real filesystem/process side effect, no mocks (HARD RULE 0.24).
- Tier 3: formal proof / security audit (not needed for this feature — no crypto/financial logic lives in
  the isolation layer itself; PROP-006's wallet-distinctness proof is Tier 3 and correctly deferred to the
  follow-on feature that actually generates a second wallet).

## Gate

Phase 3 (adversarial review) must confirm PROP-001..005 and PROP-008 all PASS via fresh-context, disk-only
review, with explicit re-verification of PROP-005 (grep for model-specific branching) since that is the
requirement most likely to silently regress as the scripts evolve.
