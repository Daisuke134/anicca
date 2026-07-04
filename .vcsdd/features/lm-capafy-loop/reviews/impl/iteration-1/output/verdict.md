# VCSDD Adversary Verdict — lm-capafy-loop / loop.sh (iteration 1)

**Overall verdict: FAIL**

Reviewed file: `/Users/anicca/anicca/skills/self/lm-capafy-loop/loop.sh`
Reference model (named by the file's own header comment): `/Users/anicca/anicca/skills/self/founder-loop/founder-loop.sh`
Authoritative spec (located via grep, no manifest existed): `/Users/anicca/anicca-project/docs/superpowers/specs/2026-07-04-anicca-money-loop-lm-capafy-design.md`

## Execution disclosure (honesty rule)
No Bash tool was available in this session (only Read/Write/Edit/Grep/Glob), despite the task text saying "you have Bash". I did **not** execute loop.sh myself and did not simulate a broken Capafy token live. Evidence used instead:
1. The pre-existing `state/STATE.md` on disk (timestamped `2026-07-04T14:57:55Z`), which is real output from a prior live run: `heal_first: all revenue surfaces healthy`, `lm_active_paid_subs: 0`, `capafy_net_revenue_usd_3d: 0.0`, honest "NO realised..." status. This confirms the happy-path (all-healthy, zero-revenue) case behaves as intended.
2. Deterministic static code-trace of the bash+python logic for the failure paths below — the Python dict-default and bash string-comparison semantics involved are unambiguous and traceable by hand without executing the script.
3. Confirmed via grep (prefix only, not full secret) that `~/.openclaw/.env::STRIPE_SECRET_KEY` currently begins `sk_live`, so the observed STATE.md is genuine live-mode data.

## Dimension verdicts

| Dimension | Verdict | Findings |
|---|---|---|
| Spec Fidelity | **FAIL** | FIND-001, FIND-008 |
| Edge Case Coverage | **FAIL** | FIND-003, FIND-004 |
| Implementation Correctness | **FAIL** | FIND-002, FIND-003, FIND-009 |
| Structural Integrity | **FAIL** | FIND-005, FIND-006, FIND-007 |
| Verification Readiness | **FAIL** | FIND-004 |

## Is the harness spine trustworthy (never fabricates/masks a revenue number)?

**No — not under failure conditions.** Under the observed happy path (both surfaces genuinely healthy, genuinely zero revenue) it is honest. But by code-trace, it has a real, demonstrable masking bug (FIND-002): Capafy's `/agent/sales/trend` and Stripe's `/v1/subscriptions` both return well-formed JSON error bodies on failure (`{"code":401,...}` for Capafy — the same shape the script's own HEAL check parses the `code` field from at loop.sh:18 — and Stripe's standard `{"error":{...}}`). Neither shape has a top-level `data` key, so the Python `.get('data',[])` / `.get('data',{}).get('data',[])` chains silently default to empty and the script prints `"0.0"`/`"0"` — indistinguishable from a genuinely-verified zero. Because the HEAL check and the READ call are two separate curl invocations (for Capafy, against two *different* endpoints), a TOCTOU gap or an endpoint-specific outage lets `heal_first: all revenue surfaces healthy` coexist with a fabricated-looking zero. This directly contradicts the stated contract ("must NEVER fabricate a number... must fail SAFE (show NA / not silently 0-as-success)").

Two compounding issues:
- FIND-003: when the failure *does* surface as `NA` (curl timeout / non-JSON), the STATUS text still falls back to a hardcoded string that asserts **"not code"** — self-contradicting the NA field in the same file.
- FIND-001: even on the honest path, `lm_active_paid_subs` is a subscription **count**, not a dollar figure, so it cannot actually be checked against the spec's stated `$200/month` goal — a $0-coupon or test subscription would inflate it into a false "EARNING" signal.

## Blocking findings (file:line)

1. **FIND-001** (critical, spec_fidelity/requirement_mismatch) — `loop.sh:33-37,43,50`: LM_SUBS is a subscription count, not a $ revenue figure; cannot be validly compared to the spec's `$200/month` goal; $0/coupon/test subs inflate it.
2. **FIND-002** (critical, implementation_correctness/requirement_mismatch) — `loop.sh:17-19,24-25,29-37`: API error responses (valid JSON, wrong shape) silently default to `0`/`0.0` instead of `NA`, defeating the anti-fake contract; TOCTOU gap between HEAL (separate endpoint/call) and READ.
3. **FIND-003** (major, implementation_correctness/requirement_mismatch) — `loop.sh:40-44`: on genuine `NA`, STATUS defaults to a string that asserts "not code" — self-contradicts the NA value in the same file.
4. **FIND-004** (critical, verification_readiness+edge_case_coverage/test_coverage) — whole file vs `founder-loop/test-founder-loop.sh:1-63`: zero tests, zero test-seam env vars; every invocation hits live production credentials; the failure paths above are untestable without breaking production auth.
5. **FIND-005** (minor, structural_integrity/requirement_mismatch) — `loop.sh:42`: numeric guard `^[0-9.]+$` is too permissive (regression of a lesson already documented in the sibling script's own FIND-903).
6. **FIND-006** (major, structural_integrity/requirement_mismatch) — `loop.sh:9-10,50,54` vs `founder-loop.sh:19-21,45-46`: no prior-STATE read, no cumulative tracking; a 3-day Capafy window can't be reconciled against a monthly goal, and cadence gaps >3d permanently lose revenue visibility.
7. **FIND-007** (minor, structural_integrity/requirement_mismatch) — `loop.sh:40-44`: STATUS is winner-takes-all; HEAL-NEEDED silently discards a simultaneous EARNING signal from the narrative text.
8. **FIND-008** (major, spec_fidelity/spec_gap) — `loop.sh:15-25` vs design spec lines 45,119,130-131,135: spec's HEAL-FIRST requires cron-log-freshness check + auto-fix-or-escalation (the exact incident that let Capafy die silently for 6 weeks); loop.sh has neither, and the narrower as-built section 13 doesn't reconcile the drop.
9. **FIND-009** (major, implementation_correctness/security_surface) — `loop.sh:24,34`: no check that `STRIPE_SECRET_KEY` is `sk_live_` vs `sk_test_`; currently live in practice, but no code-level guard prevents test-mode data from being silently reported as real revenue.

## Actual script output referenced

From the existing on-disk `state/STATE.md` (real prior run, not fabricated by me):
```
# LM + Capafy money loop — STATE (GLVS, no-human, money → Dais bank)
goal: LM Stripe revenue + Capafy subscription revenue > Dais monthly spend (~$200). Done ONLY on real provider-reported revenue, NEVER 'published/posted'.
last_wake_utc: 2026-07-04T14:57:55Z
heal_first: all revenue surfaces healthy (Capafy auth ✓, LM /health 200, Stripe ✓)
lm_active_paid_subs: 0
capafy_net_revenue_usd_3d: 0.0
status: NO realised external revenue yet — bottleneck = DEMAND (users/sales), not code
next: if HEAL-NEEDED → fix that surface first; else pick the single highest-EV self-improve action (LM funnel / Capafy listing→winner / Reddit demand) and VERIFY a real revenue delta.
```
This confirms the honest-zero happy path works. It does **not** confirm the failure/masking paths above, which were found by static code-trace and remain unverified by live execution in this review (no Bash tool available to me this session).
