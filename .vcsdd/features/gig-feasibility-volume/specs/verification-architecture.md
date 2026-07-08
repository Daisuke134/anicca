# gig-feasibility-volume — Verification Architecture (VCSDD, lean, Phase 1b)

- **Feature**: `gig-feasibility-volume`
- **Depends on**: `specs/behavioral-spec.md` (REQ-GFV-001..020)
- **Mode**: lean — fewer `required:true` proof obligations than strict; no human-approval gate at spec review.

## 1. Purity Boundary Map

### Pure Core (deterministic, no I/O, formally testable with plain pytest — Tier 1)

| Module / function | REQ | Notes |
|---|---|---|
| `funnel.py::summarize_gig_funnel(rows)` | REQ-GFV-007 (indirectly, unchanged), REQ-GFV-011 | EXISTING, unmodified — reused, not touched |
| `funnel.py::dedupe_latest_status(rows)` | REQ-GFV-012 | EXISTING, unmodified — reused for `listing_id` dedupe too (§2, PROP-005) |
| `funnel.py::summarize_gig_funnel_by_category(rows)` | REQ-GFV-011 | NEW — pure partition-then-bucket function, in-memory only, no file I/O |
| `passprep.py`'s `listings_due` computation (the boolean-decision sub-logic, factored so it is callable with an in-memory row list + `now` timestamp, not just via full-file I/O) | REQ-GFV-005 | The 7-day-window count + threshold compare is pure given `(listing_rows, now, listing_weekly_target)`; the *file read* that produces `listing_rows` is the effectful shell (§1.2) |
| `passprep.py`'s skip-floor logic (existing, `priority ⊆ skip → reset`) | REQ-GFV-008 | EXISTING, unmodified — non-regression pin only |
| `self-improve/gig/evaluator.py`'s new per-category scoring function | REQ-GFV-013 | Given a list of `gig-funnel.jsonl` row dicts (already parsed) → `{category: {reply_rate,win_rate,paid_jpy}}`, no I/O, no import of anything that posts/applies/dispatches |
| `funnel_report.py`'s `listings_live` count (the dedupe-by-`listing_id` + filter-`status=="live"` logic, factored to take an in-memory row list) | REQ-GFV-012 | Same "factor the pure compute out from the file read" pattern as `listings_due` above |
| `passprep.py`'s `cold_start` computation (the sum-and-compare sub-logic, factored so it is callable with an in-memory row list, not just via full-file I/O) | REQ-GFV-017 | Given `(earnings_rows, SETTLED_set)` → boolean; reuses `run.sh`'s existing `SETTLED`/`jnum()` conventions verbatim rather than redefining them (DRY — one status-set literal, not two) |

### Effectful Shell (I/O / browser / time — integration-tested, Tier 0)

| Module / action | REQ | Notes |
|---|---|---|
| `passprep.py`'s file reads/writes (`strategy.json`, `strategy.default.json`, NEW `~/gig/listings.jsonl` read) | REQ-GFV-001, 002, 005, 008, 009 | EXISTING atomic-write pattern (`tempfile.mkstemp` + `os.replace`) reused for any new write path |
| `funnel_report.py`'s file reads/writes (`applied.jsonl`, NEW `listings.jsonl` read, `gig-funnel.jsonl` append) | REQ-GFV-012 | EXISTING tolerant-parse `_read_jsonl` pattern reused for the new `listings.jsonl` read |
| `gig-cli.sh` STARTUP prompt: listing creation/maintenance on Coconala (CDP daily-driver) | REQ-GFV-006 | Genuinely effectful + judgment-laden (which category/tier/price); NOT unit-testable — verified by real listing URL existence (§3, integration tier) |
| `gig-cli.sh` STARTUP prompt: B2-APPLY volume screening + application submission | REQ-GFV-007, 010, 016 | Existing browser-driven flow, prompt-text change only (no new code module) |
| `gig-cli.sh` STARTUP prompt: B3-LEARN price/hook capture on `lessons.jsonl` | REQ-GFV-014 | Prompt-text change; write path reuses existing `lessons.jsonl` append convention |
| `weekly_compare.py::beats_previous_week` | REQ-GFV-015 | EXISTING, unmodified — receives new category-aggregated input, its own I/O/logic is out of scope |
| `passprep.py`'s `~/gig/earnings.jsonl` file read (feeds the pure `cold_start` compute above) | REQ-GFV-017 | Tolerant-parse pattern, same as every other ledger reader in this codebase |
| `gig-cli.sh` STARTUP prompt: B4-IMPROVE `agent-reach` web best-practice search + `strategy.json` diff application (`listing_playbook`/`proposal_playbook`/`price_defaults`/`proposal_templates`/`listing_categories` writes) | REQ-GFV-018, 019 | Genuinely effectful + judgment-laden (which finding to apply, how); NOT unit-testable — verified by real pass evidence (a concrete `strategy.json` diff attributable to a cited search finding) |
| `gig-cli.sh` STARTUP prompt: B1/B2 individualized message/proposal text generation (no unmodified template sends) | REQ-GFV-020 | Prompt-text + agent-judgment change; no new code module — verified by grep (clause presence) + real pass evidence (no verbatim-template sends observed) |

## 2. Proof Obligations

| ID | Description | REQ | Tier | Required | Tool |
|----|-------------|-----|------|----------|------|
| PROP-001 | `strategy.default.json` contains non-empty `feasibility_rules.ai_doable` and `feasibility_rules.ai_infeasible` strings; no regex/keyword array present anywhere in the scope-locked files that decides feasibility | REQ-GFV-001 | 0 | true | manual/static file inspection (grep for `re.compile`/regex literals touching feasibility in the diff) |
| PROP-002 | Given a `strategy.json` fixture with N pre-existing keys and no `feasibility_rules`, running `passprep.py`'s fill-forward leaves all N original keys' values unchanged (except `pass_count`/`updated_ts`) and adds `feasibility_rules` | REQ-GFV-002 | 1 | true | pytest, fixture-based |
| PROP-003 | `passprep.py` exits 0 and prints valid JSON to stdout for: (a) missing `strategy.json`, (b) corrupt `strategy.json`, (c) missing `strategy.default.json` + corrupt `strategy.json`, (d) unreadable `listings.jsonl` | REQ-GFV-002, 005 | 1 | true | pytest, exercises all 4 fallback branches (extends existing crash-safety tests) |
| PROP-004 | `strategy.default.json.skip_categories` contains zero 占い/霊感/スピリチュアル entries; `strategy.default.json.listing_categories` contains exactly one 占い-style entry | REQ-GFV-003 | 0 | true | static file inspection / simple python assert script |
| PROP-005 | `strategy.default.json.listing_categories` has ≥8 entries; every entry's `price_jpy_initial` falls in [0.5, 0.7] × `price_jpy_target` | REQ-GFV-004 | 1 | true | pytest, iterates seed file entries |
| PROP-006 | `listings_due` pure function: 0 rows in trailing 7 days → true; `listing_weekly_target` rows in trailing 7 days → false; boundary (`target-1` rows) → true | REQ-GFV-005 | 1 | true | pytest, table-driven fixture (3+ cases incl. boundary) |
| PROP-007 | `passprep.py`'s stdout JSON includes `listings_due` as a boolean on every successful and every fallback run | REQ-GFV-005 | 1 | true | pytest, asserts key presence + type across all branches from PROP-003 |
| PROP-008 | (Behavioral, not unit-testable) A pass with `listings_due:true` that successfully creates a listing produces exactly one new `listings.jsonl` row with a dereferenceable `url`; a pass with `listings_due:false` produces zero new rows | REQ-GFV-006 | 0 | false (lean: documented, verified once via real E2E pass, not gated every sprint) | manual E2E: real CloakBrowser listing-creation pass + `curl`/browser-open the resulting URL |
| PROP-009 | Given a fixture set of requests (feasible/non-saturated/non-skip/non-applied count = M, `max_apply_per_pass` = K): the STARTUP prompt's instructed behavior applies to `min(M, K)` requests, never fewer than `min(M,K)` when M ≥ 1 | REQ-GFV-007 | 0 | false (lean: prompt-text behavior, verified via real pass evidence — applied-rate trend in `gig-funnel.jsonl` over N passes post-ship, not a unit test) | E2E evidence review (compare applied-rate before/after over ≥10 real passes) |
| PROP-010 | Existing skip-floor fixture (all `priority_categories` ⊆ `skip_categories`) still resets `skip_categories` to `[]` after this feature's `passprep.py` changes | REQ-GFV-008 | 1 | true | pytest, existing-behavior regression pin |
| PROP-011 | `strategy.default.json.apply_skip_thresholds.max_applicants == 30`; running `passprep.py` against a LIVE-shaped fixture with `max_applicants:12` leaves it at 12 | REQ-GFV-009 | 1 | true | pytest, two fixtures (fresh-bootstrap vs live-fixture) |
| PROP-012 | `summarize_gig_funnel_by_category`: sum of `applied` across all returned categories == `summarize_gig_funnel`'s `applied` for the same input rows (partition-invariance); a row with no `category` lands in `"uncategorized"`; empty input → `{}` | REQ-GFV-011 | 1 | true | pytest, property-style (generate random row sets, assert invariant) + explicit edge fixtures |
| PROP-013 | `summarize_gig_funnel_by_category` does not duplicate `_WON_STATUSES`/`_PAID_STATUSES` — grep-verifiable single definition site reused by both functions | REQ-GFV-011 | 0 | true | static inspection (grep count == 1 for each set literal) |
| PROP-014 | A `gig-funnel.jsonl` row written post-ship contains the original top-level keys (`ts,pass_id,applied,replied,won,paid`) unchanged in type/meaning, PLUS `by_category` (dict) and `listings_live` (int) | REQ-GFV-012 | 1 | true | pytest, schema-shape assertion on `funnel_report.run()`'s return value |
| PROP-015 | `git diff` against `~/anicca/skills/self/cadence-contracts.json` is empty after this feature's implementation phase | REQ-GFV-012 | 0 | true | `git diff --stat` check in the impl-review gate (Phase 3), not a unit test |
| PROP-016 | `evaluator.py::evaluate_stage1`'s existing signature/return-shape/behavior is unchanged (regression) on a fixture ledger identical to one used before this feature | REQ-GFV-013 | 1 | true | pytest, before/after golden-output comparison |
| PROP-017 | The new per-category evaluator function contains no import of any post/apply/dispatch/live-session module (grep-verifiable, mirrors the existing sandbox-boundary comment in `evaluator.py`) | REQ-GFV-013 | 0 | true | static inspection |
| PROP-018 | A `by_category`-less `gig-funnel.jsonl` row (old-schema) fed into the per-category evaluator contributes zero to every category tally without raising | REQ-GFV-013 | 1 | true | pytest, mixed-schema fixture |
| PROP-019 | (Behavioral) A new `outcome:"accepted"` `lessons.jsonl` row for a request with a known `applied.jsonl` price carries a numeric `price_jpy` | REQ-GFV-014 | 0 | false (lean: verified via real pass evidence once a real win occurs post-ship, not blocking sprint completion) | evidence review on next real `outcome:accepted` event |
| PROP-020 | `weekly_compare.py::beats_previous_week`'s call signature is byte-identical pre/post this feature (no signature-breaking change) | REQ-GFV-015 | 0 | true | static diff inspection |
| PROP-021 | `gig-cli.sh` STARTUP prompt text (grep-verifiable) contains the never-refuse clause language | REQ-GFV-016 | 0 | true | static inspection (grep for the clause substring in the STARTUP var) |
| PROP-022 | `cold_start` pure function: 0 SETTLED-status/evidence/positive-jpy rows (or absent file) → true; exactly one qualifying row with `jpy=1` → false; a row with `jpy` as `"¥40,000"`-style string parses via the reused `jnum()` convention → contributes 40000, not 0/crash; a SETTLED row with empty `evidence` does NOT count (matches `run.sh`'s own exclusion) | REQ-GFV-017 | 1 | true | pytest, table-driven fixture (4+ cases incl. the string-parse and empty-evidence edge cases) |
| PROP-023 | `passprep.py`'s stdout JSON includes `cold_start` as a boolean on every successful and every fallback run (mirrors PROP-007's pattern for `listings_due`) | REQ-GFV-017 | 1 | true | pytest, asserts key presence + type across all branches |
| PROP-024 | `gig-cli.sh` STARTUP prompt text (grep-verifiable) requires an `agent-reach` (or equivalent web-search) call inside B4, unconditionally whenever `do_improve:true`, with `cold_start` referenced ONLY as an emphasis/depth modulator (never as a skip condition for this half) | REQ-GFV-018 | 0 | true | static inspection (grep for `agent-reach` + `do_improve` + `cold_start` co-occurring in the B4 clause of the STARTUP var, and absence of any `if cold_start: skip search`-shaped conditional) |
| PROP-025 | `gig-cli.sh` STARTUP prompt text (grep-verifiable) requires the per-category funnel-metrics double-down review inside B4, unconditionally whenever `do_improve:true` (not gated on `cold_start` at all — always runs, cold-start or not) | REQ-GFV-018 | 0 | true | static inspection |
| PROP-026 | `strategy.default.json.listing_playbook` and `.proposal_playbook` are non-empty and contain the spot-check phrases (松竹梅, モニター価格/モニター, 30分, 5段/5 for proposal structure, 80%) traceable to the design doc's BP research | REQ-GFV-019 | 0 | true | static inspection / simple python assert script |
| PROP-027 | `passprep.py`'s fill-forward mechanism (widened per REQ-GFV-019) adds `listing_playbook`/`proposal_playbook` to a live `strategy.json` fixture lacking them, without altering any other existing key — same invariant as PROP-002, extended to 2 more keys | REQ-GFV-019 | 1 | true | pytest, extends the PROP-002 fixture with the 2 new keys |
| PROP-028 | `gig-cli.sh` STARTUP prompt text (grep-verifiable) contains the individualization requirement ("no unmodified template send") for both B1 replies and B2 proposals | REQ-GFV-020 | 0 | true | static inspection |

## 3. Verification Strategy

- **Tier 0** (no formal proof needed — static inspection / existence checks): PROP-001, 004, 008 (partially — E2E), 013, 015, 017, 019 (evidence, not gate), 020, 021, 024, 025, 026, 028, 029, 030. These are either grep-verifiable text/schema facts or one-off real-pass evidence reviews that don't block sprint completion in lean mode.
- **Tier 1** (property/example-based tests, pytest): PROP-002, 003, 005, 006, 007, 009 (partially — fixture-level prompt-instruction-following can be example-tested if a passprep-equivalent decision table is extracted; the actual browser application count is Tier 0/E2E), 010, 011, 012, 014, 016, 018, 022, 023, 027. All of these operate on pure functions or deterministic file-I/O helpers already following the codebase's existing tolerant-parse / atomic-write / crash-safety conventions — no new formal-methods tooling (Kani/hypothesis) is warranted at this feature's scale; standard `pytest` fixtures suffice, matching how `funnel.py`/`passprep.py` are already verified elsewhere in this repo (no existing `.kani`/`hypothesis` usage found in this skill directory).
- **Tier 2/3**: not applicable — no cryptographic, concurrency, or safety-critical property in this feature warrants lightweight or strong formal proof. (This mirrors the existing verification depth of `funnel.py`/`passprep.py`/`evaluator.py`, none of which use Tier 2/3 tooling today.)

## 4. Lean-mode required-obligation summary

`required:true` count = 25 (PROP-001,002,003,004,005,006,007,010,011,012,013,014,015,016,017,018,020,021,022,023,024,025,026,027,028 — see table for the authoritative per-row `Required` column, this list is derivable from it). `required:false` (evidence-only, non-blocking) = PROP-008, 009, 019 (3 total, 28 PROPs overall) — these are genuinely behavioral/browser-dependent and are verified via real pass evidence post-ship rather than gating Phase 2 sprint completion, consistent with lean mode's "fewer required:true, no strict human-approval gate" behavior documented in the `vcsdd-spec` skill.

## 5. Traceability

Every REQ-GFV-001..020 in `behavioral-spec.md` maps to ≥1 PROP-XXX above (REQ-GFV-006→PROP-008; REQ-GFV-007→PROP-009; REQ-GFV-014→PROP-019; REQ-GFV-015→PROP-020; REQ-GFV-017→PROP-022/023; REQ-GFV-018→PROP-024/025; REQ-GFV-019→PROP-026/027; REQ-GFV-020→PROP-028; every other REQ maps to a Tier-0/Tier-1 PROP as listed). No REQ is left without a verification method; no PROP references a REQ that does not exist in `behavioral-spec.md`.
