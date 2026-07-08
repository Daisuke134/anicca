# gig-feasibility-volume — Behavioral Spec (VCSDD, lean)

- **Feature**: `gig-feasibility-volume`
- **Date**: 2026-07-08
- **Author**: VCSDD builder (fresh-context Phase 1a/1b, per Dais/team-lead directive)
- **Mode**: lean · **Language**: python (passprep.py / funnel.py / funnel_report.py / evaluator.py) + bash prompt text (gig-cli.sh STARTUP)
- **Design source**: `docs/superpowers/specs/2026-07-08-gig-feasibility-volume-listing-design.md`
- **Scope lock (from design §「スコープ / 触るファイル」, WIDENED per spec-review iteration-1 MAJOR-1 finding)**: `~/profitable-claude/skills/human-funded/gig/{gig-cli.sh, strategy.default.json, passprep.py, funnel.py, funnel_report.py}` + `~/anicca/skills/self/self-improve/gig/evaluator.py` + `~/gig/strategy.json` + new `~/gig/listings.jsonl` ledger + `~/anicca/skills/self/cadence-contracts.json`'s `gig` entry ONLY (no other loop's entry) + `~/anicca/skills/self/cadence-evidence.py`'s `gig` branch ONLY (`clip`/`affiliate`/`video`/`bounty`/`founder-loop`/`pm-earner` branches untouched). No other loop, no other repo. The design doc's original scope line did not anticipate that `gig`'s `row-exists` cadence check was structurally always-true (fresh-context adversary finding, this iteration); closing that gap requires touching these two additional files — see §REQ-GFV-023.

## 0. Reality check (verified this session, Read/grep, 2026-07-08)

| Fact | Source |
|---|---|
| `~/gig/strategy.json` (live, pass_count=217) already has 13 `priority_categories` / 19 `skip_categories`, `apply_skip_thresholds:{max_applicants:12,min_contracted_to_skip:1,min_budget_jpy:3000}`, `category_performance`, `recommended_focus`, `deprioritize`, `recent_lessons` — all self-improve-written, NOT to be reset by this feature | `~/gig/strategy.json` (Read) |
| `占い/霊感/スピリチュアル` is currently in `skip_categories` verbatim: `"霊感/スピリチュアル/占い (requires psychic abilities)"` | `~/gig/strategy.json` skip_categories[10] |
| `~/gig/applied.jsonl` (267 rows) — `status:"applied"` rows: 91; only 13/91 carry a `category` field; 68/91 carry `price_jpy` | measured via Python scan this session (corrected in spec-review iteration-1 minor-3 — an earlier draft misreported this as 78/91) |
| `passprep.py` (SKILL_DIR-relative `strategy.default.json`) already bootstraps missing/corrupt `strategy.json`, enforces skip-floor (FIND-005: if `priority_categories` ⊆ `skip_categories` → reset skip to `[]`), increments `pass_count`, computes `do_improve = pass_count % improve_cadence_passes == 0`, prints one JSON line, exits 0 even on exception (fallback JSON to stdout, error to stderr) | `passprep.py:102-148` |
| `funnel.py::summarize_gig_funnel(rows)` is a pure function: buckets rows by `status` into `{applied,replied,won,paid}` (cumulative — a row's status is the *furthest* stage reached); `_WON_STATUSES={受注,成約}`, `_PAID_STATUSES={検収完了,支払}`; unrecognized/housekeeping status rows are ignored, never crash | `funnel.py:10-33` |
| `funnel.py::dedupe_latest_status(rows)` keeps the LAST row per `requestId` (file order = chronological), passes rows without `requestId` through unchanged | `funnel.py:36-56` |
| `funnel_report.py` reads `~/gig/applied.jsonl`, dedupes, summarizes, appends ONE `{ts,pass_id,applied,replied,won,paid}` line to `~/gig/gig-funnel.jsonl` EVERY pass UNCONDITIONALLY (`gig-cli.sh`'s FUNNEL REPORT step runs outside the `do_improve` branch, every single pass regardless of whether B1/B2 did anything this pass) — so `cadence-contracts.json`'s `gig` entry (`kind:row-exists`, source=`gig-funnel.jsonl`) reads a `ts` for every calendar day the hourly cron merely RAN, not a day real 出品/応募/顧客返信 activity happened; this row-exists check is therefore structurally always-true and does not implement the design doc's §6 cadence bar (spec-review iteration-1 MAJOR-1 finding). §REQ-GFV-021/022/023 below fix this by rewiring the `gig` entry to `kind:increment` on a new monotonic `activity_total` field | `funnel_report.py:38-46`, `~/anicca/skills/self/cadence-contracts.json`, `~/anicca/skills/self/cadence-evidence.py` (verified this session: `gig-funnel.jsonl`'s latest row shows `applied:93` after 217 unconditional passes, and `cadence.py`'s `row-exists` semantics — `today_jst_date in evidence["event_dates"]` — read directly off that always-appended `ts`) |
| `~/anicca/skills/self/self-improve/gig/evaluator.py::evaluate_stage1` already branches on funnel-shaped rows (`applied`/`won` keys present) vs generic ledger rows, computing `reply_rate + win_rate + paid_jpy` — falls back to `ledger_metrics.evaluate_stage1_generic` otherwise | `evaluator.py:20-35` |
| `gig-cli.sh` STARTUP prompt already runs STEP 0 passprep → PRE-STEP peer-lesson read → B1 NURTURE → B2 APPLY (up to `max_apply_per_pass`, screened by `priority_categories`/`skip_categories`/AI-doable judgment) → B3 LEARN → EARNED CHECK → (if `do_improve`) B4 IMPROVE + B5 SHARE → FUNNEL REPORT → mail report → touch `.last-pass` | `gig-cli.sh:21` (STARTUP var) |
| `~/gig/lessons.jsonl` rows already carry `{ts,requestId,category,outcome,reason,lesson}` (no `price_jpy`, no explicit "hook/切り口" field) | measured this session, tail -3 |
| `~/gig/listings.jsonl` does not exist yet — no listing model in current implementation | `ls ~/gig/` (absent) |
| Real applied-rate is 0.42/pass over 217 passes (91/217) against `max_apply_per_pass=5` — design's diagnosis: over-conservative screening + Coconala's public-request model requires SMS phone verification (structural, not fixable by this feature) | design doc §As-is |
| `run.sh` already defines the canonical "settled real yen" filter: `SETTLED={"検収","支払","検収完了","completed","paid"}` applied to `~/gig/earnings.jsonl` rows with a non-empty `evidence` and `jpy>0` (via its `jnum()` tolerant-parse helper), summed for the honest `jpy_earned` status line | `run.sh:42-44` |
| Design doc (2026-07-08, confirmed final) adds, after the original 7 To-be items, an **初期 best-practice playbook** (cold-start seed for both listing and proposal models, sourced from 2026-07-08 BP research, explicitly NOT locked — the loop re-searches and updates it every `do_improve` pass) and a **品質・自然さ** section requiring per-request individualized replies/proposals (定型テンプレの一斉送信をしない — each reply/proposal is written fresh against that request's own keywords/concerns/tone). The design doc contains NO section on platform-ToS compliance, AI-use disclosure, or an independent "human-style" pass on AI-generated deliverables — an earlier draft of this spec fabricated such a section (citing a non-existent "⚠️ Coconala ToS 制約" doc heading); per Dais's explicit 2026-07-08 instruction that content is deleted from this spec (§REQ-GFV-020 below covers ONLY the design doc's actual 品質・自然さ individualization requirement) | design doc §「初期 best-practice playbook」, §「品質・自然さ」 |
| Team-lead directive (2026-07-08, this session): self-improve (B4) must run BOTH a web best-practice search (via the `agent-reach` skill) AND a funnel-metrics double-down review EVERY `do_improve` pass — never purely one or the other; cold-start (zero settled revenue to date) weights the search half heavier while still reading metrics (even an empty ledger); once ≥1 real yen has ever settled, emphasis becomes roughly balanced between search and metrics — but neither half is ever skipped at any point | team-lead message, this session |

## 1. Judgment vs determinism boundary (BUILD AGENTS RIGHT — binding on every REQ below)

Per `~/.claude/rules/building-effective-ai-agents.md`: judgment (which category to list, which request to apply to, price, proposal wording, listing tier) stays with the agent via natural-language prompt criteria in `gig-cli.sh` STARTUP and `strategy.json` text fields. Determinism is reserved for: bootstrap/repair of `strategy.json` (`passprep.py`), skip-floor enforcement, cadence counters (`pass_count`, `do_improve`, new `listings_due`), funnel arithmetic (`funnel.py`), evidence-ledger existence checks (listing/proposal URL presence), and weekly score aggregation (`evaluator.py`). No REQ below introduces a regex/keyword classifier for feasibility or category judgment; feasibility criteria are natural-language text that the agent reads and applies, exactly like the existing `priority_categories`/`skip_categories` judgment already does.

## 2. Requirements

### REQ-GFV-001: `strategy.json` carries an explicit feasibility-basis field
**EARS**: THE SYSTEM SHALL persist a `feasibility_rules` object in `strategy.json` (bootstrapped into `strategy.default.json` as the seed) containing two natural-language text fields — `ai_doable` (criteria: completable via browser + computer alone — writing, code, design drafts, documents, chat/messaging) and `ai_infeasible` (criteria: phone-call handling, phone/SMS-required login, SMS-authenticated ad-account operation, physical on-site presence, national/professional license required, voice recording, face-on-camera appearance, physical/manual craft production) — as prose for agent judgment, not as a regex or keyword list consumed by code.
**Edge Cases**:
- `strategy.json` missing or corrupt on disk: `passprep.py`'s existing bootstrap-from-`strategy.default.json` path (FIND-002) restores `feasibility_rules` along with every other seeded key — no new bootstrap code path is required beyond adding the key to `strategy.default.json`.
- An operator/self-improve pass overwrites `strategy.json` without a `feasibility_rules` key (e.g. an older self-improve write predates this feature): `passprep.py` MUST NOT crash; §REQ-GFV-002 defines the fill-forward behavior.
**Acceptance Criteria**:
- `strategy.default.json` (bootstrap seed) contains a non-empty `feasibility_rules.ai_doable` and `feasibility_rules.ai_infeasible` string.
- No file under the scope-locked set contains a regex/keyword array whose match result *decides* feasibility (natural-language text only).

### REQ-GFV-002: `passprep.py` fills forward a missing `feasibility_rules` key without discarding the rest of a live `strategy.json`
**EARS**: WHEN `passprep.py` loads an existing, valid `strategy.json` that lacks a `feasibility_rules` key THE SYSTEM SHALL merge in the default `feasibility_rules` object from `strategy.default.json` (or the hardcoded `FALLBACK` if `strategy.default.json` is itself unreadable) while leaving every other existing key (`category_performance`, `recommended_focus`, `deprioritize`, `recent_lessons`, `apply_skip_thresholds`, etc.) untouched, then write the merged object back atomically.
**Edge Cases**:
- `strategy.default.json` itself unreadable at fill-forward time: use the hardcoded `FALLBACK`'s `feasibility_rules` (added alongside `FALLBACK`'s other seeded keys) — never crash, never emit invalid JSON.
- `strategy.json` already has a non-empty `feasibility_rules`: no-op (idempotent), existing operator/self-improve edits to that text are preserved verbatim (self-improve may itself refine the wording — that stays agent judgment, this REQ only guarantees the key exists).
**Acceptance Criteria**:
- Loading a `strategy.json` fixture with N pre-existing keys (e.g. a fixture matching the LIVE file's real 22-key shape, per §0 Reality check — corrected in spec-review iteration-1 minor-2, an earlier draft's illustrative "20/21" example was confusingly close to but not equal to the real count) and no `feasibility_rules` results in N+1 keys after `passprep.py` runs, with the original N byte-for-byte unchanged except `pass_count`/`updated_ts` (existing increment behavior).
- `passprep.py` exit code remains 0 in every case (matches existing crash-safety contract at `passprep.py:137-148`).

### REQ-GFV-003: 占い(fortune-telling/text-reading) category is reclassified out of `skip_categories`
**EARS**: THE SYSTEM SHALL NOT list any variant of `霊感/スピリチュアル/占い` (or its live-strategy wording) inside `skip_categories` in `strategy.default.json`; THE SYSTEM SHALL instead carry it as a low-to-mid priority `listing_categories` entry (§REQ-GFV-004) with the rationale "AI-completable text-reading content, saturated market, repeat-purchase culture" recorded in that entry's `notes` field.
**Edge Cases**:
- The LIVE `~/gig/strategy.json` (pass_count=217) still has the old `霊感/スピリチュアル/占い (requires psychic abilities)` skip-entry from before this feature: this REQ governs the bootstrap seed (`strategy.default.json`) and the STARTUP-prompt guidance text (§REQ-GFV-016); it does NOT silently rewrite the live file's `skip_categories` array out from under the running self-improve loop (that would erase 217-pass-accumulated judgment on unrelated skip entries). The next self-improve pass (B4, agent judgment, guided by the updated STARTUP-prompt text) removes the stale 占い skip-entry itself, or an operator applies the same one-line removal directly to `~/gig/strategy.json` as a manual data-migration step outside code — either path is acceptable; this REQ's acceptance criterion is scoped to the seed file plus the prompt guidance, not a forced live-file mutation.
**Acceptance Criteria**:
- `strategy.default.json`'s `skip_categories` array contains zero entries matching `占い`/`霊感`/`スピリチュアル`.
- `strategy.default.json`'s new `listing_categories` array contains exactly one entry whose `category` field matches `占い`/`霊感`/`スピリチュアル`-style text-reading content.

### REQ-GFV-004: `strategy.json` carries a `listing_categories` array for the listing (出品) model
**EARS**: THE SYSTEM SHALL persist a `listing_categories` array in `strategy.json` (seeded in `strategy.default.json`), each entry shaped `{category, tier, price_jpy_initial, price_jpy_target, review_threshold_min, review_threshold_max, notes}`, covering at minimum: SEO記事/LP文章, ネーミング/キャッチコピー, Excel/VBA自動化, EC商品説明文, プレゼン/パワポ, 文字起こし×要約, 翻訳, FAQ生成, and 占い/text-reading (§REQ-GFV-003).
**Edge Cases**:
- A category appears in both `priority_categories` (proposal model) and `listing_categories` (listing model): both membership are valid simultaneously — the same skill can be pursued via public-request proposal AND via a standing listing; no REQ requires mutual exclusivity.
- `review_threshold_min`/`review_threshold_max` absent on an entry (partial data from an earlier hand-edit): the agent (B-listing step, §REQ-GFV-006) treats a missing threshold as "not yet eligible for price increase," never crashes, never divides by zero (no code path performs arithmetic on these fields — they are read as judgment inputs only).
**Acceptance Criteria**:
- `strategy.default.json.listing_categories` has ≥8 entries covering the design doc's named categories.
- Each entry's `price_jpy_initial` is 50–70% of `price_jpy_target` (design doc's "初期は相場の50〜70%").

### REQ-GFV-005: `passprep.py` computes a deterministic weekly listing-cadence signal
**EARS**: WHEN `passprep.py` runs THE SYSTEM SHALL read `~/gig/listings.jsonl` (creating it as an empty file if absent) and compute `listings_due` (boolean) = true WHEN the count of listing-ledger rows with `ts` within the trailing 7 days is below a configurable `listing_weekly_target` (seeded default: 2, i.e. "週1〜2枠"), else false; `listings_due` is included in `passprep.py`'s printed JSON alongside the existing `pass_count`/`do_improve`/`max_apply_per_pass`/`priority_categories`/`skip_categories` fields.
**Edge Cases**:
- `~/gig/listings.jsonl` absent or empty: `listings_due = true` (bootstrap case — zero listings created yet, always due).
- `~/gig/listings.jsonl` contains malformed JSON lines: skip unparseable lines (same tolerant-parse pattern as `funnel_report.py::_read_jsonl`), never crash.
- `listing_weekly_target` missing from `strategy.json`: fall back to seeded default 2.
**Acceptance Criteria**:
- A `listings.jsonl` fixture with 0 rows in the last 7 days → `listings_due:true` in `passprep.py`'s stdout JSON.
- A fixture with 2 rows in the last 7 days (target=2) → `listings_due:false`.
- `passprep.py`'s existing crash-safety contract (exit 0, valid fallback JSON on any exception) is preserved; a missing/unreadable `listings.jsonl` degrades to `listings_due:true` via the same fallback path, never a stack trace to stdout.

### REQ-GFV-006: `gig-cli.sh` STARTUP prompt adds a listing-maintenance step gated on `listings_due`
**EARS**: WHEN STEP 0 (`passprep.py`) reports `listings_due:true` THE SYSTEM SHALL instruct the agent to create or refresh 1–2 listings this pass, choosing category/tier/price from `listing_categories` (agent judgment — which category, which tier, what price within the seeded initial/target range) via the Coconala listing-creation UI (CDP daily-driver), then append `{ts,listing_id,category,tier,price_jpy,url,status:"live"}` to `~/gig/listings.jsonl`.
**Edge Cases**:
- `listings_due:false`: the agent skips the listing step entirely this pass (no forced no-op row written) — cadence is enforced by §REQ-GFV-005's 7-day window, not by a per-pass write.
- Listing creation UI fails (network error, CAPTCHA, form validation): the agent logs the attempt and reports a `note` explaining the failure in the pass summary; it does NOT append a `status:"live"` row for a listing that was not actually confirmed live (no-fake-success, matches repo-wide No dry run rule).
- An existing listing needs a price increase (per `review_threshold_min`/`review_threshold_max` reached, §REQ-GFV-004): the agent updates the listing on Coconala and appends a NEW `~/gig/listings.jsonl` row with the same `listing_id`, updated `price_jpy`, `status:"live"` (append-only ledger, same pattern as `applied.jsonl`'s multi-row-per-requestId design).
**Acceptance Criteria**:
- A pass where `listings_due:true` and the agent successfully creates a listing produces exactly one new `~/gig/listings.jsonl` row with a real, dereferenceable Coconala listing URL in `url`.
- A pass where `listings_due:false` produces zero new `~/gig/listings.jsonl` rows.

### REQ-GFV-007: proposal-model volume — apply to every feasible, non-saturated viable request up to the per-pass cap
**EARS**: WHILE screening public requests for B2-APPLY THE SYSTEM SHALL apply to every request that passes ALL of (a) feasibility (§REQ-GFV-001 `ai_doable` criteria, agent judgment), (b) category membership in `priority_categories` and NOT in `skip_categories`, (c) not already in `APPLIED_IDS`, (d) applicant count below the live `apply_skip_thresholds.max_applicants` — up to `max_apply_per_pass` total new applications this pass; THE SYSTEM SHALL NOT stop at fewer than the viable count solely out of conservative self-limiting when viable, non-saturated, feasible requests remain and the per-pass cap has not been reached.
**Edge Cases**:
- Fewer than `max_apply_per_pass` viable requests exist this pass: apply to all of them (never pad with infeasible/skip-category requests to hit the cap).
- `apply_skip_thresholds.max_applicants` is a live, self-improve-tuned value (currently 12 in production, evidence-based from Friday-evening saturation observations, `strategy.json.time_of_week_patterns`): this REQ does NOT override that live-tuned value; §REQ-GFV-009 governs only the seeded bootstrap default.
**Acceptance Criteria**:
- Given a fixture pass with 4 feasible/non-saturated/non-skip/non-applied requests and `max_apply_per_pass=5`, the prompt's instructed behavior is to apply to all 4 (not artificially limit to 1).
- Given 8 such requests and `max_apply_per_pass=5`, apply to exactly 5 (the cap, not more).

### REQ-GFV-008: skip_categories skip-floor is preserved unchanged
**EARS**: THE SYSTEM SHALL continue to enforce the existing skip-floor behavior (FIND-005, `passprep.py:106-113`) unmodified: IF every `priority_categories` entry is also present in `skip_categories` THEN THE SYSTEM SHALL reset `skip_categories` to `[]` before computing `do_improve`/`listings_due` for that pass.
**Edge Cases**: none beyond the existing, already-tested behavior — this REQ is a non-regression pin, not new logic.
**Acceptance Criteria**: existing skip-floor unit-test-equivalent fixture (all priority categories also in skip) still resets `skip_categories` to `[]` after this feature's changes to `passprep.py`.

### REQ-GFV-009: bootstrap-seed saturation threshold aligns with the design's volume-maximization intent
**EARS**: THE SYSTEM SHALL set `strategy.default.json`'s seeded `apply_skip_thresholds.max_applicants` default to 30 (the design doc's stated "応募30+の飽和案件はskip" line) for NEW installs / from-scratch bootstraps only; THE SYSTEM SHALL NOT overwrite an already-live, self-improve-tuned `apply_skip_thresholds.max_applicants` value in `~/gig/strategy.json` (currently 12, evidence-tuned) as part of this feature's bootstrap/fill-forward logic.
**Edge Cases**:
- A fresh `~/gig` (no `strategy.json`) bootstraps from `strategy.default.json`: gets `max_applicants:30`.
- The live, already-running `strategy.json` (pass_count=217, `max_applicants:12`): unaffected by this REQ; future self-improve (B4) passes remain free to raise or lower it based on evidence, per existing agent-judgment behavior — this REQ only sets the from-scratch default higher to avoid a new install starting overly conservative.
**Acceptance Criteria**: `strategy.default.json.apply_skip_thresholds.max_applicants == 30`; a `passprep.py` run against the LIVE `~/gig/strategy.json` fixture (which already has `apply_skip_thresholds.max_applicants:12`) leaves that value at 12 after the run.

### REQ-GFV-010: applied-status rows carry a `category` field
**EARS**: WHEN B2-APPLY writes an `{status:"applied", ...}` row to `~/gig/applied.jsonl` THE SYSTEM SHALL include a `category` field whose value is one of the matched `priority_categories` (or `listing_categories`, if the application arose from a listing inquiry) entries used for that match.
**Edge Cases**:
- Historical rows (91 existing `applied` rows, only 13 with `category`) are NOT retroactively rewritten — this REQ governs new rows going forward only (append-only ledger, no backfill).
- A request matches no exact `priority_categories` string (edge taxonomy mismatch): the agent records its best-fit judgment string rather than omitting the field; `category` is never silently dropped for a NEW row after this feature ships.
**Acceptance Criteria**: 100% of NEW `status:"applied"` rows written after this feature ships carry a non-empty `category` field (measurable via `funnel_report.py`'s consumption in §REQ-GFV-011/012 — an uncategorized new row falls into the `"uncategorized"` bucket, which is the acceptance signal that a row is missing `category`, not a crash).

### REQ-GFV-011: `funnel.py` gains a pure per-category summarizer
**EARS**: THE SYSTEM SHALL add `summarize_gig_funnel_by_category(rows)` to `funnel.py` as a pure function (same signature/purity contract as `summarize_gig_funnel`) that first partitions deduped rows by `row.get("category") or "uncategorized"`, then applies the EXISTING `summarize_gig_funnel` status-bucketing logic independently within each partition, returning `{category_name: {applied,replied,won,paid}, ...}`.
**Edge Cases**:
- A row lacking `category`: bucketed under `"uncategorized"` (never dropped, never crashes — same never-drop convention as `dedupe_latest_status`'s `passthrough` for rows lacking `requestId`).
- Empty input (`rows=None` or `[]`): returns `{}`.
**Acceptance Criteria**:
- `summarize_gig_funnel_by_category` reuses `summarize_gig_funnel`'s internal bucketing (no duplicated status-vocabulary logic — `_WON_STATUSES`/`_PAID_STATUSES` defined exactly once).
- Sum of `applied` across all categories returned by the per-category function equals the `applied` value `summarize_gig_funnel` returns for the same input rows (invariant: partitioning by category never changes the total).

### REQ-GFV-012: `funnel_report.py` writes an additive, backward-compatible `gig-funnel.jsonl` row
**EARS**: WHEN `funnel_report.py` runs THE SYSTEM SHALL append a `gig-funnel.jsonl` row that (a) keeps the EXISTING top-level shape `{ts,pass_id,applied,replied,won,paid}` unchanged (so the existing `cadence-contracts.json` `row-exists` consumer and `evaluator.py`'s existing funnel-shape detection keep working unmodified) AND (b) adds a new `by_category` key = the output of `summarize_gig_funnel_by_category` (§REQ-GFV-011) AND (c) adds a new `listings_live` key = a deterministic count, read from `~/gig/listings.jsonl`, of the latest-status-per-`listing_id` rows whose `status == "live"` (same dedupe-latest-by-id pattern as `dedupe_latest_status`, applied to `listing_id` instead of `requestId`).
**Edge Cases**:
- `~/gig/listings.jsonl` absent: `listings_live: 0` (no crash — matches `_read_jsonl`'s existing absent-file tolerance).
- A consumer reading only the pre-existing top-level keys is unaffected by THIS REQ's schema addition — this is a strictly additive schema change, never a field removal or rename. (§REQ-GFV-023 separately changes the `cadence-contracts.json` `gig` entry's `kind` from `row-exists` to `increment` to fix the always-true cadence bug spec-review iteration-1 MAJOR-1 found — that is a consumer-BEHAVIOR change governed by REQ-GFV-023, not a schema change, and not this REQ's concern.)
**Acceptance Criteria**:
- A `gig-funnel.jsonl` row written after this feature ships validates against BOTH the old consumer's expectations (top-level `applied/replied/won/paid` present) and contains `by_category` (dict) and `listings_live` (int) keys.

### REQ-GFV-013: weekly evaluator scores per-category performance
**EARS**: THE SYSTEM SHALL extend `~/anicca/skills/self/self-improve/gig/evaluator.py` with a read-only, deterministic function that, given the `by_category` blocks accumulated across `gig-funnel.jsonl` rows in a trailing 7-day window, computes per-category `{reply_rate, win_rate, paid_jpy}` and returns them sorted by `paid_jpy` descending, for the agent's B4-IMPROVE step to read (agent judgment: which categories to shift listing/proposal allocation toward, per existing `recommended_focus`/`deprioritize` write pattern already in `strategy.json`).
**Edge Cases**:
- `by_category` absent on older `gig-funnel.jsonl` rows written before this feature (backward-compat rows without the new key): treated as contributing zero to every category's tally for that row — never crashes on a mixed-schema ledger (old rows without `by_category` alongside new rows with it).
- Existing `evaluate_stage1`'s whole-pass scoring (`_funnel_score`) is UNCHANGED — the new per-category function is additive, not a replacement.
**Acceptance Criteria**:
- `evaluator.py` still exports `evaluate_stage1` with its existing signature and return shape (non-regression).
- The new per-category function never imports or calls anything that posts/applies/dispatches/drives a live web session (same sandbox-boundary comment already present at the top of `evaluator.py`).

### REQ-GFV-014: lessons ledger captures price and hook on wins
**EARS**: WHEN B3-LEARN records an `outcome:"accepted"` row to `~/gig/lessons.jsonl` for a request that has a corresponding `applied.jsonl` row THE SYSTEM SHALL additionally include `price_jpy` (copied from the matching `applied.jsonl` row) and a `hook` field (free-text, agent-authored: what proposal angle/differentiator won the contract) alongside the existing `{ts,requestId,category,outcome,reason,lesson}` shape.
**Edge Cases**:
- No matching `applied.jsonl` row found (data gap): `price_jpy` omitted rather than fabricated (never invent a price).
- Existing 267 historical `lessons.jsonl` rows are not backfilled — forward-only, same append-only convention as §REQ-GFV-010.
**Acceptance Criteria**: a new `outcome:"accepted"` row written after this feature ships, for a request with a known `applied.jsonl` price, carries a numeric `price_jpy` field.

### REQ-GFV-015: weekly paid_jpy trend is machine-judged
**EARS**: THE SYSTEM SHALL compute "this week's total `paid_jpy` (summed across `by_category` in `gig-funnel.jsonl` rows in the trailing 7 days) > last week's total" as a deterministic boolean, reusing the existing `beats_previous_week` comparator already referenced by `gig-cli.sh`'s STARTUP prompt (`.../lib/weekly_compare.py`), fed by the new category-aggregated `paid_jpy` sums from §REQ-GFV-012/013 rather than requiring a separate ledger.
**Edge Cases**: fewer than 14 days of `gig-funnel.jsonl` history exist yet (feature just shipped): `beats_previous_week`'s existing handling of an insufficient-history window (whatever it already does today) is unchanged by this feature — this REQ does not modify `weekly_compare.py` itself, only ensures the data it's fed is now category-capable.
**Acceptance Criteria**: `weekly_compare.py`'s existing call signature and behavior are unmodified; this REQ is satisfied by §REQ-GFV-012's additive schema alone.

### REQ-GFV-016: STARTUP prompt states an explicit never-refuse clause
**EARS**: THE SYSTEM SHALL include, in `gig-cli.sh`'s STARTUP prompt text, an explicit instruction that a feasible (per §REQ-GFV-001 `ai_doable`) and legal, non-scam public request or listing inquiry is never declined or deprioritized merely out of conservative screening; THE SYSTEM SHALL state that the only valid grounds to skip are (a) `ai_infeasible` per §REQ-GFV-001, or (b) illegality/scam/ToS-violation risk (matching the existing skip_categories entries already reasoned this way, e.g. the スキャルピングBOT/決済自動化 entry).
**Edge Cases**: a request is borderline (partially feasible, e.g. mostly-remote work with one small physical-mail step): agent judgment stays with the agent — this REQ does not enumerate every borderline case; it only forbids using non-`ai_infeasible`, non-illegal reasons (e.g. "this is more competitive than I'd like," "I'm not confident I'll win") as skip grounds.
**Acceptance Criteria**: `gig-cli.sh`'s STARTUP prompt text contains the never-refuse clause; `strategy.json`'s `skip_categories` semantics (already narrative, evidence-cited per-entry) are unaffected — no new skip entry may be added without a feasibility or legality/ToS rationale in its own text (existing convention, already followed by every current skip_categories entry's parenthetical reason).

### REQ-GFV-017: `passprep.py` computes a deterministic `cold_start` signal from settled revenue
**EARS**: WHEN `passprep.py` runs THE SYSTEM SHALL read `~/gig/earnings.jsonl` (tolerant parse — same skip-unparseable-lines convention as every other ledger reader in this codebase, e.g. `funnel_report.py::_read_jsonl`), sum the `jpy` field across rows whose `status` is in the EXISTING `SETTLED` set (`{検収,支払,検収完了,completed,paid}`, reusing `run.sh:42`'s exact definition rather than redefining it) AND that carry a non-empty `evidence` field AND `jpy>0` (reusing `run.sh:29-31`'s `jnum()` tolerant-numeric-parse convention), and set `cold_start` (boolean) = true WHEN that cumulative sum is 0, else false; `cold_start` is included in `passprep.py`'s printed JSON alongside `pass_count`/`do_improve`/`listings_due`/`max_apply_per_pass`/`priority_categories`/`skip_categories`.
**Edge Cases**:
- `~/gig/earnings.jsonl` absent or empty: `cold_start:true` (zero settled revenue by definition).
- A row has `jpy` as a string with commas/¥/円 (matches `run.sh`'s `jnum()` handling of `"¥40,000"`-style values): parsed correctly via the same tolerant-numeric convention, not a hardcoded regex judgment (it is arithmetic parsing of a fixed numeric format, not case-judgment — matches the "genuine parsing of a machine format" exception already carved out in `~/.claude/rules/building-effective-ai-agents.md`).
- Malformed JSON lines in `earnings.jsonl`: skipped, never crash (same tolerant-parse convention).
- Once `cold_start` flips to false (any real settled yen ever recorded), it MUST NOT flip back to true on a later pass even if a subsequent week has zero NEW earnings — the signal is cumulative-to-date, not a trailing window (design intent: "cold-start" describes the loop's overall maturity, not a weekly dip).
**Acceptance Criteria**:
- A fixture `earnings.jsonl` with 0 SETTLED-status rows (or absent file) → `cold_start:true`.
- A fixture with exactly one SETTLED row, `jpy:1`, non-empty `evidence` → `cold_start:false`.
- A fixture with one SETTLED row but empty `evidence` (matches `run.sh`'s own exclusion condition) → does not count toward the sum → `cold_start:true` if it's the only row.
- `passprep.py`'s existing crash-safety contract (exit 0, valid fallback JSON) is preserved for every new failure mode this REQ introduces (unreadable `earnings.jsonl`, permission error, etc.) — degrades to `cold_start:true` via the same fallback path used by `listings_due` (§REQ-GFV-005).

### REQ-GFV-018: B4 IMPROVE STEP always performs BOTH a web best-practice search AND a funnel-metrics double-down review, every `do_improve` pass
**EARS**: WHEN STEP 0 (`passprep.py`) reports `do_improve:true` THE SYSTEM SHALL instruct the agent's B4 IMPROVE STEP to perform BOTH of the following, every single such pass, never only one: (a) a real web search via the `agent-reach` skill for current Coconala best-practices on what listings sell and what proposals win (e.g. title/thumbnail conventions, pricing-tier structure, proposal response-speed norms), then apply at least one concrete diff to `strategy.json` (`listing_playbook`/`proposal_playbook` text, `price_defaults`, `proposal_templates`, or `listing_categories` tier/price fields) informed by a specific finding from that search; (b) a funnel-metrics double-down review reading the per-category `{reply_rate,win_rate,paid_jpy}` breakdown already produced by REQ-GFV-013's evaluator extension, and — WHEN any category shows ≥1 reply or ≥1 win in its available history — raising that category's priority/listing cadence in `strategy.json` (reusing the existing `recommended_focus`/`deprioritize` write pattern already present in the live `strategy.json`, per §0 Reality check). WHEN `cold_start` (from STEP 0, §REQ-GFV-017) is true THE SYSTEM SHALL weight the search half heavier (broader query set, more sources, more time this pass) while still performing the metrics review in full (reading the ledger even when it is empty or all-zero — a confirmation read, not a skipped step). WHEN `cold_start` is false THE SYSTEM SHALL treat both halves as roughly balanced in weight.
**Edge Cases**:
- `do_improve:false` this pass: B4 (both halves) is skipped entirely this pass, per the EXISTING cadence gate (`improve_cadence_passes`, unmodified) — this REQ only governs what happens INSIDE a `do_improve:true` pass, it does not change when those passes occur.
- The web search (agent-reach) returns nothing new/actionable this pass (saturated search space, no new BP found): the agent records that null result honestly (e.g. in `recent_lessons` or a search-log note) rather than fabricating a diff — search still happened (satisfies "never skip"), it simply found nothing this time.
- The metrics review finds zero categories with any reply/win yet (true cold-start state, consistent with `cold_start:true`): no double-down action is taken this pass (nothing to double down on) but the review itself still occurred and is reported.
- `agent-reach` skill itself errors/unavailable this pass: the agent falls back to the existing PRE-STEP `gh issue list ... gig-lesson` peer-lesson read (already wired, `gig-cli.sh:21`) as the search substitute for that pass, logs a warning, and continues — matches the existing "gh failure must never abort the pass" convention already in the STARTUP prompt.
**Acceptance Criteria**:
- `gig-cli.sh`'s STARTUP prompt text (grep-verifiable) requires an `agent-reach` (or equivalent web-search) call inside B4, unconditionally on every `do_improve:true` pass.
- `gig-cli.sh`'s STARTUP prompt text (grep-verifiable) requires the per-category metrics review inside B4, unconditionally on every `do_improve:true` pass (not gated on `cold_start`).
- The prompt text references `cold_start` only to modulate the SEARCH half's depth/emphasis, never to skip either half.

### REQ-GFV-019: `strategy.json` seeds an initial, self-improve-mutable best-practice playbook
**EARS**: THE SYSTEM SHALL persist `listing_playbook` and `proposal_playbook` text fields in `strategy.json` (seeded in `strategy.default.json`), capturing the design doc's 2026-07-08 cold-start best-practice research as natural-language guidance for agent judgment — `listing_playbook` covering: benefit-based (not task-based) titles, thumbnail text-overlay conventions, 3-tier pricing (松竹梅) + paid options, monitor/introductory pricing for the first reviews, and a daily-login + weekly-update cadence; `proposal_playbook` covering: application-speed priority (respond within the platform's early-exposure window after a request posts), a 5-part proposal structure (empathy → capability → trust-building → price/timeline/scope breakdown → soft close), zero-track-record pricing at ~80% of market rate, and a DM/quote-inquiry SLA of a 30-minute first response → hearing → 3-tier presentation → time-boxed closing. THE SYSTEM SHALL treat these fields as a MUTABLE cold-start seed, not a locked constant — §REQ-GFV-018's B4 search half is EXPECTED to overwrite/refine this text over time as the agent finds newer best-practices.
**Edge Cases**:
- The LIVE `~/gig/strategy.json` (pass_count=217) does not yet have `listing_playbook`/`proposal_playbook`: filled forward on the next `passprep.py` run via the SAME merge-missing-key mechanism as §REQ-GFV-002 (widened to cover this REQ's new keys too — one fill-forward mechanism, not a duplicate one per new key).
- Self-improve (B4) rewrites `listing_playbook`/`proposal_playbook` to something that contradicts the original seed: valid and expected — this REQ's acceptance criterion is about the SEED file (`strategy.default.json`) content, not about pinning the live file's value forever.
**Acceptance Criteria**:
- `strategy.default.json.listing_playbook` and `.proposal_playbook` are non-empty strings (or structured text objects) whose content is traceable to the design doc's §「初期 best-practice playbook」 (spot-checkable key phrases: 松竹梅, モニター価格, 30分, 5段, 80%).
- `passprep.py`'s fill-forward mechanism (§REQ-GFV-002, widened) adds both keys to a live `strategy.json` fixture that lacks them, without altering any other existing key.

### REQ-GFV-020: Message and proposal individualization — no unmodified template sends
**EARS**: THE SYSTEM SHALL NOT send a `proposal_templates` (or any other canned) string unmodified, with zero request-specific content, as a B1-NURTURE reply or a B2-APPLY proposal; every message reply and every proposal text THE SYSTEM SHALL individualize to the specific request/talk-room's stated keywords, concerns, and tone (agent judgment reads the actual request/message text and reacts to it — sending an unmodified `proposal_templates` string verbatim, with zero request-specific content woven in, is a violation of this REQ, not merely poor quality — matches the design doc's §品質・自然さ「定型テンプレの一斉送信をしない」rule).
**Edge Cases**:
- `proposal_templates` in `strategy.json` remain useful as a STARTING skeleton/category-appropriate tone reference (this REQ does not require deleting them) — the violation is sending them UNCHANGED with zero request-specific adaptation, not using them as a base to adapt from.
- A request's stated content is very short/generic (little to individualize against): the agent still references at least one concrete detail from the actual posting (e.g. budget, deadline, deliverable format) rather than sending a fully generic string.
**Acceptance Criteria**:
- `gig-cli.sh`'s STARTUP prompt text (grep-verifiable) contains the individualization requirement ("no unmodified template send") for both B1 replies and B2 proposals.

### REQ-GFV-021: `funnel_report.py` computes a monotonic `listings_total` counter (distinct listings ever created)
**EARS**: WHEN `funnel_report.py` runs THE SYSTEM SHALL compute `listings_total` = the count of DISTINCT `listing_id` values that have EVER appeared in `~/gig/listings.jsonl`, regardless of current `status` (a delisted or price-updated listing's `listing_id` still counts once toward this total — unlike `listings_live` (§REQ-GFV-012), which reflects only CURRENTLY-live listings and can decrease, `listings_total` is monotonic non-decreasing over calendar time since it counts distinct IDs ever seen in an append-only ledger), and include it as a new top-level key in the `gig-funnel.jsonl` row alongside the existing top-level keys and §REQ-GFV-012's `by_category`/`listings_live` keys.
**Edge Cases**:
- `~/gig/listings.jsonl` absent or empty: `listings_total: 0` (no crash, matches `_read_jsonl`'s existing absent-file tolerance).
- A row missing `listing_id`: excluded from the distinct-count (never crashes, never counted as a phantom listing).
**Acceptance Criteria**:
- A `listings.jsonl` fixture with 4 rows spanning 3 distinct `listing_id` values (one `listing_id` appearing twice, e.g. a §REQ-GFV-006 price-update row) → `listings_total == 3`.
- A `listings.jsonl` fixture where one `listing_id`'s latest row has `status` other than `"live"` (delisted) → that `listing_id` still counts toward `listings_total` (distinguishing it from `listings_live`, which would exclude it).

### REQ-GFV-022: `funnel_report.py` computes a monotonic `activity_total` counter for cadence purposes
**EARS**: WHEN `funnel_report.py` runs THE SYSTEM SHALL compute `activity_total` = `applied + replied + listings_total` (§REQ-GFV-011's/the existing `summarize_gig_funnel`'s cumulative `applied`/`replied` buckets — both monotonic non-decreasing over the append-only `applied.jsonl` history, per §0 Reality check's description of `funnel.py`'s cumulative bucketing — PLUS §REQ-GFV-021's monotonic `listings_total`) and include it as a new top-level key in the `gig-funnel.jsonl` row. By construction `activity_total` is monotonic non-decreasing across the loop's full history: it can fail to increase on a given calendar day ONLY WHEN (a) zero NEW requests reached the `applied` stage for the first time that day, AND (b) zero requests received their FIRST tracked reply that day, AND (c) zero new distinct listing was EVER created that day — i.e. a day with genuinely zero 出品/応募/顧客返信 activity, exactly the design doc §6 cadence bar's three named trigger conditions. This field exists specifically to feed §REQ-GFV-023's cadence-contract fix.
**Edge Cases**:
- A day where an existing listing is delisted or price-updated (no NEW distinct `listing_id`) and no other activity occurs: `activity_total` does not increase that day — correctly reads as "no new activity," matching the design doc's literal wording (delisting/price-tuning is not one of the three named trigger conditions).
- A day where an already-applied-or-replied request advances further (e.g. to 受注/検収完了) with zero NEW applies/replies/listings that day: `won`/`paid` do NOT feed `activity_total` by design — those are downstream OUTCOMES, not new outbound actions the design doc's cadence bar asks about; a day with only a conversion event and zero new applies/replies/listings correctly reads as "no active engagement today."
**Acceptance Criteria**:
- Given two `gig-funnel.jsonl`-shaped fixture snapshots (day1 end-of-day cumulative `applied+replied+listings_total` sum vs day2's), where day2's sum exceeds day1's, `activity_total` strictly increases.
- Where day2's sum equals day1's (zero new applies/replies/listings that day), `activity_total` is unchanged from day1's value.

### REQ-GFV-023: `cadence-contracts.json`'s `gig` entry is rewired from `row-exists` to `increment`, closing the always-true gap
**EARS**: THE SYSTEM SHALL change `~/anicca/skills/self/cadence-contracts.json`'s `gig` entry from `{"kind":"row-exists","cadence":"1/day","unit":"reel","boundary_tz":"Asia/Tokyo","source":"~/gig/gig-funnel.jsonl (REQ-LV-015)"}` to `{"kind":"increment","field":"activity_total","boundary_tz":"Asia/Tokyo","source":"~/gig/gig-funnel.jsonl (REQ-GFV-022 activity_total = cumulative applied+replied+listings_total)"}`, reusing the EXACT `increment`-kind semantics `cadence.py::cadence_met` already implements for the `bounty` entry (`evidence["today_value"] > evidence["previous_value"]`) — THE SYSTEM SHALL NOT modify `cadence.py` itself (its `increment` branch is generic and unchanged). THE SYSTEM SHALL correspondingly move the `"gig"` member OUT of `cadence-evidence.py`'s shared `("clip","affiliate","video","gig")` row-exists tuple (in both `gather_evidence()` and `evidence_by_date_for_streak()`) and INTO a new day-latest-value lookup function, `_gig_today_and_previous_activity_total(today_jst_date)` — a copy+tweak of the EXISTING `_bounty_today_and_previous_checked` function (same "keep the LATEST value seen for each JST day, then today vs most-recent-prior-day" logic), reading `activity_total` off `~/gig/gig-funnel.jsonl` rows instead of `checked` off `bounty-funnel.jsonl` rows.
**Edge Cases**:
- `clip`/`affiliate`/`video` remain unmodified `row-exists` loops in the shared tuple (their ledgers are genuinely written only on real per-pass action, unlike gig's `funnel_report.py`, which runs unconditionally every pass) — this REQ touches ONLY the `gig` entry/branch; the other 3 members of that tuple, and the `bounty`/`founder-loop`/`pm-earner` branches, are byte-for-byte unchanged.
- A `gig-funnel.jsonl` row written BEFORE this feature ships (no `activity_total` key): `_gig_today_and_previous_activity_total` treats a missing key as `0` for that row (same `.get(..., 0)`-tolerant convention `_bounty_today_and_previous_checked` already uses for `checked`), never crashing on mixed-schema history.
- The existing `GIG_FUNNEL_PATH` environment-variable override (already read by `_gig_funnel_path()` in `cadence-evidence.py`) continues to work unchanged for the new lookup function — no new override seam is introduced, the existing one is reused.
**Acceptance Criteria**:
- `~/anicca/skills/self/cadence-contracts.json`'s `gig` entry, post-change, has `kind == "increment"` and `field == "activity_total"`; every other entry (`clip`,`affiliate`,`video`,`bounty`,`founder-loop`,`pm-earner`) is byte-for-byte unchanged (verifiable via `git diff` showing edits confined to the `gig` object).
- A `gig-funnel.jsonl` fixture with two rows on the SAME JST day, both from passes with zero real applies/replies/listings that day (`activity_total` unchanged from the previous day's end value) → `cadence_met()` returns `False` for that day (the row-exists false-positive this REQ fixes).
- A fixture where a genuine new application landed that day (`activity_total` increased vs the prior day) → `cadence_met()` returns `True`.

### REQ-GFV-024: `gig-cli.sh` STARTUP prompt's two broken path references are corrected
**EARS**: THE SYSTEM SHALL replace, within `gig-cli.sh`'s STARTUP prompt string, BOTH occurrences of the non-existent path prefix `~/anicca/skills/human-funded/gig/` with the real path `~/profitable-claude/skills/human-funded/gig/` — specifically (a) the STEP 0 passprep invocation, `python3 ~/anicca/skills/human-funded/gig/passprep.py` → `python3 ~/profitable-claude/skills/human-funded/gig/passprep.py`, and (b) the APPLY_RUNBOOK read, `~/anicca/skills/human-funded/gig/scripts/coconala/APPLY_RUNBOOK.md` → `~/profitable-claude/skills/human-funded/gig/scripts/coconala/APPLY_RUNBOOK.md` (spec-review iteration-1 MAJOR-3 finding: `~/anicca/skills/human-funded/` does not exist on disk at all; the agent has been silently self-correcting this every pass, which is not a guarantee).
**Edge Cases**:
- This feature ALSO edits `gig-cli.sh`'s STARTUP for §REQ-GFV-006/016/018/020/023 — both path fixes MUST land in the SAME STARTUP-string edit pass, not deferred to a separate change, since any edit to STARTUP already requires touching this file.
- No other path reference in STARTUP uses the broken `~/anicca/skills/human-funded/gig/` prefix (e.g. `~/anicca/skills/self/self-improve/gig/evaluator.py` and `~/anicca/skills/self/self-improve/lib/weekly_compare.py` are correct as-is, verified this session — they live under `~/anicca/skills/self/`, a real directory, not `~/anicca/skills/human-funded/`) — this REQ's replacement is scoped to exactly the two broken occurrences, not a blanket `~/anicca/` → `~/profitable-claude/` substitution.
**Acceptance Criteria**:
- `grep -c "~/anicca/skills/human-funded/gig/" gig-cli.sh` == 0 after this feature ships.
- `gig-cli.sh` contains both corrected path strings (`~/profitable-claude/skills/human-funded/gig/passprep.py` and `.../scripts/coconala/APPLY_RUNBOOK.md`) at least once each.

## 3. Non-functional constraints

- **Crash-safety**: every REQ touching `passprep.py` preserves its existing exit-0/fallback-JSON contract (`passprep.py:137-148`). No new code path may cause `passprep.py` to exit non-zero or print invalid JSON to stdout.
- **Purity**: `funnel.py` additions (§REQ-GFV-011) take ONLY the rows already collected for the pass as input — zero new browser/network access, matching the existing module docstring's purity claim.
- **Append-only ledgers**: `~/gig/listings.jsonl`, `~/gig/applied.jsonl`, `~/gig/lessons.jsonl`, `~/gig/gig-funnel.jsonl` are all append-only; no REQ in this spec rewrites or deletes historical rows.
- **No regex/keyword judgment**: no REQ introduces a regex or fixed keyword list that DECIDES feasibility, category fit, or skip/apply outcome — all such decisions remain natural-language agent judgment fed by the `strategy.json` text fields this spec adds/extends (§1).
- **Backward compatibility**: `gig-funnel.jsonl`'s schema changes (§REQ-GFV-012/021/022) and `evaluator.py`'s extension (§REQ-GFV-013) are additive-only (new keys, no removals/renames); `evaluator.py::evaluate_stage1` and `weekly_compare.py` require no modification to keep working. The ONE deliberate, in-scope exception is `cadence-contracts.json`'s `gig` entry (§REQ-GFV-023), whose `kind` is intentionally changed from `row-exists` to `increment` to fix the always-true cadence bug spec-review iteration-1 MAJOR-1 found; `clip`/`affiliate`/`video`/`bounty`/`founder-loop`/`pm-earner` entries and `cadence-evidence.py` branches are untouched.
- **Self-improve is never one-armed**: §REQ-GFV-018 is a binding non-functional invariant, not just a per-pass behavior — no future revision of the B4 IMPROVE STEP may reduce it to search-only or metrics-only; both halves run every `do_improve:true` pass for the lifetime of this loop, with only the RELATIVE EMPHASIS (not presence) modulated by `cold_start`.
- **Message individualization**: §REQ-GFV-020's no-unmodified-template-send constraint (design doc §品質・自然さ) is a conversion-rate/account-health requirement, not merely a style preference — it bounds every REQ in this spec that touches outbound messages/proposals (REQ-GFV-006, 007, 010, 016).

## 4. Edge case catalog (consolidated)

### Input Edge Cases
- Empty `~/gig/listings.jsonl` / absent file → treated as 0 listings (§REQ-GFV-005, §REQ-GFV-012).
- Malformed JSON lines in any ledger → skipped, never crash (existing tolerant-parse convention, reused everywhere).
- Missing `category` field on an applied row → falls into `"uncategorized"` bucket, never dropped (§REQ-GFV-010/011).
- `earnings.jsonl` row with `jpy` as a comma/¥-formatted string → parsed via existing `jnum()`-equivalent convention, never a crash or a silent zero (§REQ-GFV-017).

### State Edge Cases
- First-time run, no `strategy.json` yet → full bootstrap from `strategy.default.json` including new `feasibility_rules`/`listing_categories`/`apply_skip_thresholds.max_applicants:30`/`listing_playbook`/`proposal_playbook` (§REQ-GFV-001/004/009/019).
- Live `strategy.json` mid-flight (pass_count=217) missing only the NEW keys → fill-forward merge, existing keys untouched (§REQ-GFV-002, widened by §REQ-GFV-019).
- Mixed-schema `gig-funnel.jsonl` (old rows without `by_category` alongside new rows with it) → old rows contribute zero to category tallies, never crash (§REQ-GFV-013).
- `cold_start` flips false→true is never valid (monotonic once real revenue has ever settled) — a pass reading a temporarily-empty trailing window must not re-derive `cold_start` from a windowed view; it is always a cumulative-to-date sum (§REQ-GFV-017).

### Error Edge Cases
- Listing-creation browser flow fails mid-pass → no fake `status:"live"` row written; failure noted in pass summary (§REQ-GFV-006, ties to repo-wide No dry run rule).
- `strategy.default.json` itself corrupt/missing at fill-forward time → hardcoded `FALLBACK` used, still valid JSON, still exit 0 (§REQ-GFV-002, extends existing `passprep.py:96-99` last-resort path).
- `agent-reach` (or equivalent web-search path) errors/unavailable during B4 → falls back to the existing peer-lesson `gh issue list` read for that pass, never aborts the pass (§REQ-GFV-018).
- A B1/B2 message is about to be sent as an unmodified template string with zero request-specific content → this REQ (§REQ-GFV-020) forbids it; the agent must individualize before sending, not skip the reply.
- A day where an existing listing is delisted/price-updated and no other activity occurs → `activity_total` does not increase that day, correctly reading as no-activity per the design doc's literal 出品/応募/顧客返信 wording (§REQ-GFV-022).
- A `gig-funnel.jsonl` row written BEFORE this feature ships (no `activity_total` key) → treated as `0` by `cadence-evidence.py`'s new day-lookup function, never crashing on mixed-schema history (§REQ-GFV-023).
- `gig-cli.sh`'s broken `~/anicca/skills/human-funded/gig/` path references are fixed in the SAME STARTUP-string edit pass as this feature's other prompt-text changes, not deferred (§REQ-GFV-024).

## 5. Non-goals (explicitly out of scope for this feature)

- Modifying any Cadence Contract entry OTHER than `gig`'s — the `clip`/`affiliate`/`video`/`bounty`/`founder-loop`/`pm-earner` entries in `cadence-contracts.json`, and their corresponding branches in `cadence-evidence.py`, are untouched. `gig`'s entry IS modified by this feature (§REQ-GFV-023) — this REVERSES an earlier draft's Non-goal, which incorrectly claimed the `gig` entry needed no edit; spec-review iteration-1 MAJOR-1 found the original `row-exists` check structurally always-true (a real bug, not a style preference), so fixing it is now in-scope.
- Generalizing feasibility-gate/listing-model/funnel-evaluator/search-driven-self-improve patterns to other loops (clip/video/affiliate/article) — design doc §7 names this as a follow-on, tracked separately (task #20 in the team's TODO list), not part of this feature's REQ set. This feature establishes the pattern IN gig only.
- Rewriting the LIVE `~/gig/strategy.json`'s existing self-improve-tuned fields (`apply_skip_thresholds.max_applicants:12`, `category_performance`, `recommended_focus`, `deprioritize`) — only the bootstrap SEED (`strategy.default.json`) and STARTUP-prompt guidance text change; the live file's self-improve-accumulated judgment is preserved (§REQ-GFV-003, §REQ-GFV-009).
- A dedicated `listings.py` module or CLI — listing creation stays a browser-driven agent action inside `gig-cli.sh`'s STARTUP prompt (§REQ-GFV-006), consistent with the existing B1/B2 pattern (no new deterministic script performs the listing itself, only the cadence gate around it is deterministic).
- A dedicated `bp_search.py` module — the web best-practice search (§REQ-GFV-018) stays an agent-driven `agent-reach` skill call inside the STARTUP prompt, not a new deterministic script; only `cold_start` (the emphasis signal) is computed deterministically.
- Any AI-use disclosure requirement or independent "human-style" pass on AI-generated deliverables — not part of the confirmed design doc; explicitly excluded from this feature per Dais's 2026-07-08 instruction (an earlier draft of this spec incorrectly introduced such a requirement citing a non-existent design-doc section; that content has been removed — see §0 Reality check).
