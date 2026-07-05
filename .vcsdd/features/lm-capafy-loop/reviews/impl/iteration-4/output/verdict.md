# VCSDD Adversary Verdict — lm-capafy-loop — iteration-4 (convergence gate)

**Overall verdict: PASS**

Fresh context, disk-only, traced `loop.sh` + `test-loop.sh` line-by-line against the three residual
findings from iteration-3 and re-walked every anti-fake invariant (INV-1..6) from scratch. No new
finding is being invented. Measurement spine converged.

---

## FIND-015 (was critical) — RESOLVED

**Claim to verify**: Capafy monthly must be the CURRENT/LATEST payout month, not `max(amount)` across
all history.

**Trace**:
- `loop.sh:40` — `latest=max(recs, key=lambda r: str(r.get('payoutMonth','')))` selects the record with
  the lexicographically-largest `payoutMonth` string (ISO `YYYY-MM` sorts chronologically as a string),
  i.e. the latest month, not the largest amount.
- `loop.sh:41` — `print(round(float(latest.get('amount',0) or 0),2))` reads the amount from **that**
  record only — the max-over-amounts bug from iteration-3 is gone.
- `test-loop.sh:16` — `PAYMULTI='{"code":0,"data":[{"amount":50.0,"payoutMonth":"2026-05"},{"amount":0.0,"payoutMonth":"2026-06"}]}'` — exactly the adversarial fixture demanded by the prior finding (old
  high $50, recent $0).
- `test-loop.sh:24` — Test G: `run "$ACC" "$PAYMULTI" "$T0" "$SUBS0" 0` asserts
  `'^capafy_monthly_payout_usd: 0.0'`. If the old max()-over-history bug were reintroduced this would
  read `50.0` and the regex would fail — this is a real regression guard, not a tautology.

**Verdict: RESOLVED.** The fix is structurally correct and the test would actually catch a regression
(it exercises exactly the two-record collapse scenario the finding described).

Residual (non-blocking, noted for the record only): `payoutMonth` defaults to `''` via
`.get('payoutMonth','')` if the field is ever absent on a record; an unlabeled record would sort as the
lowest possible key and could be skipped even if it were logically the newest. No evidence exists that
Capafy ever omits this field (every real/fixture record seen across all 4 iterations carries it), so this
is not being raised as a blocking finding — flagging only as a latent assumption for whoever owns this
skill next.

---

## FIND-016 — RESOLVED

**Claim to verify**: the `CAPAFY-LOOP-NEVER-RAN` branch (log file absent) needs a test; previously
`run()` always `touch`ed the log so it always existed.

**Trace**:
- `test-loop.sh:6-9` — `run()` signature comment now documents a 5th arg
  `<log_age_days | "none">`; `if [ "$age" = "none" ]; then LOG="$T/absent.log"; else touch "$LOG"; ...; fi`
  — when `"none"` is passed, `$LOG` points at a path inside the per-test tempdir that is **never
  created**.
- `test-loop.sh:25` — Test H: `run "$ACC" "$PAY0" "$T0" "$SUBS0" none` then
  `a "never-ran" "$O" 'CAPAFY-LOOP-NEVER-RAN'`.
- `loop.sh:73-76` — `if [ -f "$LP" ]; then ... else add_heal "CAPAFY-LOOP-NEVER-RAN → wire+fire daily_loop.sh"; fi` — the else branch is exactly what Test H exercises, since `LMCAP_LOGFILE` is wired
  straight through to `LP` (`loop.sh:15`) and the test's absent-file path is passed via that env var.

**Verdict: RESOLVED.** Both heal branches on `loop.sh:73-76` (STALE via Test E, NEVER-RAN via Test H) now
have independent, distinguishable-message test coverage; a future refactor that collapsed or
mis-wired either branch would break one of the two assertions.

---

## FIND-017 (was non-blocking) — Stripe shape confirmed to match; residual acknowledged, still non-blocking

**Trace**: `evidence/stripe-shape.txt` documents a live Stripe query (2026-07-04, `expand[]=data.items.data.price`) returning `items.data[0].price.unit_amount: 500` with `recurring.interval: month`.
`loop.sh:62-67` reads exactly `it.get('price')` → `pr.get('unit_amount')` (cents→dollars ÷100) →
halves for `interval=='year'` — matches the captured live shape field-for-field. The evidence file this
review was pointed at is a real, dated, non-fabricated capture (not just an unlogged claim as
iteration-3 flagged) — the artifact gap iteration-3 raised is now closed.

**Verdict: matches; non-blocking** (as scoped). Noted only that the live capture had 0 active subs at
capture time so the *summation loop* (`for s in ... for it in ...`) itself still hasn't been exercised
end-to-end against a real non-zero subscriber — but the failure mode if the shape assumption were ever
wrong remains fail-safe (`NA` via the broad `except Exception` at `loop.sh:70`), so per the review scope
this stays non-blocking.

---

## Anti-fake core — spot-traced, all hold

| Invariant | Where | Status |
|---|---|---|
| INV-1 error body → NA never 0 | `loop.sh:37` (Capafy payout `code!=0 or 'data' not in d`→`NA`), `loop.sh:49` (Capafy trend, same pattern), `loop.sh:60` (`'error' in d or object!='list'`→`NA` for Stripe) | Confirmed; Test A (`test-loop.sh:18`, Capafy 401→`capafy_monthly_payout_usd: NA`) and Test B (`test-loop.sh:19`, Stripe error→`lm_mrr_usd: NA` + `status: READ-FAILED`) both actually exercise this, not just static code |
| NA → READ-FAILED | `loop.sh:82-86` — `TOTAL` only computed if **both** `LM_MRR!=NA` and `CAP_MO!=NA`; else `STATUS="READ-FAILED..."` unless `HEAL` is non-empty (HEAL takes priority, which is correct fail-safe ordering) | Confirmed by Test B |
| Dollars not counts | `loop.sh:65` `(pr.get('unit_amount') or 0)/100.0` cents→dollars; year interval ÷12 (`loop.sh:66`); Test C (`SUB20` fixture, `unit_amount:2000`) asserts `lm_mrr_usd: 20.0` (not `2000`, not a subscriber-count) | Confirmed |
| sk_live guard | `loop.sh:25` — `case` on `STRIPE_SECRET_KEY`: `sk_live_*`→ok, empty→`STRIPE-KEY-MISSING`, anything else→`STRIPE-KEY-NOT-LIVE` | Confirmed. Test harness uses a literal `sk_live_test` (`test-loop.sh:10`) which matches the `sk_live_*` glob and so bypasses the HEAL — this is safe because in test mode `fetch()` never makes a network call regardless (`loop.sh:18`, fixture short-circuit before `curl`), so no real key material or live call is ever touched by the test suite |
| HEAL+READ no-TOCTOU | Every external surface (`cap_acct`, `cap_payout`, `cap_trend`, `lm_subs`) is fetched exactly once into a variable (`loop.sh:28,32,45,55`) and only that captured variable is parsed downstream — no re-fetch-and-recheck pattern anywhere | Confirmed, single read per surface |
| monthly-vs-3day separation | `loop.sh:82-83` — `TOTAL` sums only `LM_MRR + CAP_MO`; `CAP_3D` (`loop.sh:44-52`) is written to STATE.md as `capafy_3d_net_usd_leading` (`loop.sh:101`) but never enters the `TOTAL`/goal arithmetic | Confirmed — grepped every use of `CAP_3D` in the file; it appears only in the trend-computation block and the STATE.md echo line, never in the `SPEND`/`TOTAL` block |
| selfheal-request written on HEAL | `loop.sh:91` — `if [ -n "$HEAL" ]; then ... printf ... > "$REQ"; else rm -f "$REQ" ...; fi` | Confirmed by Test E (`REQEXISTS=yes` on STALE) and Test F (`REQEXISTS=no` when healthy) |
| test seam never touches prod log | `loop.sh:14-15` — `REQ`/`LP` both resolve via `LMCAP_REQ`/`LMCAP_LOGFILE` env overrides with prod paths only as `:-` fallback defaults; `test-loop.sh:6-10` always sets both to per-test-tempdir paths for every one of the 8 test invocations | Confirmed; grepped `test-loop.sh` for the literal prod path `daily_loop.log` — it appears nowhere, only as the (unused-in-tests) fallback default inside `loop.sh` itself |

One incidental, non-blocking observation: `loop.sh:22` reads the **real** production
`capafy-autopublish/vendor/capafy-publisher/config.json` to populate `CAP_TOK`, unconditionally, even
during test runs. This is a read-only `json.load` of a credential file (not a write, not the freshness
log, not something a test result depends on — during `LMCAP_TEST=1` the token is computed but never
actually placed on the wire, since `fetch()` short-circuits to the fixture file before any `curl` call).
It does not let a fake/masked number through and does not touch the artifact `LMCAP_LOGFILE`/`LMCAP_REQ`
seams are meant to protect, so it is not raised as a finding, only flagged for awareness.

---

## Dimensions

| Dimension | Verdict | Basis |
|---|---|---|
| Spec Fidelity | PASS | `docs/superpowers/specs/2026-07-04-anicca-money-loop-lm-capafy-design.md` §13 describes exactly this measurement spine (HEAL-FIRST, real-revenue-only READ, atomic STATE.md, no fabrication); `loop.sh` implements the monthly-vs-monthly comparison (§4/§11 INV-6) correctly now that FIND-015 is fixed |
| Edge Case Coverage | PASS | 8 tests (A–H) cover: Capafy error→NA, Stripe error→NA+READ-FAILED, real non-zero sub, true $0, stale log+selfheal-request, healthy+no-request, multi-record latest-not-max (FIND-015), missing-log-file (FIND-016) |
| Implementation Correctness | PASS | Latest-month selection, cents→dollars conversion, year→month normalization, broad fail-safe excepts, atomic `mv` state write all traced and correct |
| Structural Integrity | PASS | Single cohesive ~109-line script, each surface fetched once, clearly commented invariant blocks, no duplication, no dead branches |
| Verification Readiness | PASS | Every seam (`LMCAP_TEST`, `LMCAP_FIXTURE`, `LMCAP_DIR`, `LMCAP_LOGFILE`, `LMCAP_REQ`) is isolated from prod paths; the FIND-015/016 fixes are each backed by a test that would fail if the bug were reintroduced (not tautological assertions) |

---

## Convergence

FIND-015, FIND-016 both **RESOLVED** with regression-capable tests. FIND-017 **matches live evidence**
and remains non-blocking as scoped. No new blocking finding was found after re-walking INV-1 through
INV-6 and the seam isolation. **The measurement spine converged.**
