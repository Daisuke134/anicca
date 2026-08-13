# Lancers First Verified Application Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `5585496` の `submission_uncertain` を再送せず案件単位に隔離し、既存 Lancers loop が別の適格案件を発見・応募して、公式 proposal ID と `ApplicationReceipt` 1件まで閉じる。

**Architecture:** 既存 pending state を quarantine の正本として再利用する。`run_loop()` の pending reconciliation が `submission_uncertain` のときだけ discovery へ継続し、既存 `_filter_claimed_rows()` が claim 済み `5585496` を応募候補から除外する。同じ planner decision に公開ICP証拠と保守的原価見積を持たせ、submit直前に70% marginを整数演算で検証する。新DB、新サービス、新しい transaction abstraction は作らない。

**Tech Stack:** Python 3 stdlib、既存 Lancers `application_loop.py` / `application_tick.py`、既存 JSON state、既存 marketplace SQLite ledger、launchd。

## Global Constraints

- 外部 submit は既存 `ai.anicca.lancers-revenue-application` launchd loop だけが行う。テストや実装 subagent は submit しない。
- project `5585496` を blind resubmit しない。既存 pending entry と claim marker を削除・書換えしない。
- verified は Lancers 公式 proposal ID readback 後だけ。`ApplicationReceipt` は新規 provider proposal ID に対して正確に1件だけ appendする。
- G1 中は negotiation、fulfillment、finance、商品変更、新DB、common kernel、multi-account、他 marketplace を作らない。
- 本 slice の production logic は2ファイル、目標差分80 LOC以下。回帰testはHOL正常系1本＋金額過大評価を防ぐ1本だけ。
- 実装後の fresh adversarial review は1回だけ。Critical / Important だけを blocking とし、追加review roundは行わない。
- 現在の deployed source は canonical repo 外にある。G1ではversioned patchと検証証拠をrepoに残し、runtime全体の移管はG1完了後の別sliceにする。

## File Map and Size

| File | Responsibility | Change size |
|---|---|---:|
| `/Users/operator/.local/lib/anicca/lancers/skills/earn/lancers/scripts/application_loop.py` | deployed loopのHOL根因修正 | modify 8–15 LOC |
| `/Users/operator/.local/lib/anicca/lancers/skills/gig-work/schemas/application_decisions.schema.json` | ICP証拠・予測原価のplanner contract | modify 35–50 LOC |
| `apps/lancers-revenue/tests/test_application_loop_hol.py` | HOL隔離とmargin gateの最小回帰test | create 110–140 LOC |
| `ops/lancers/patches/0001-first-qualified-application.patch` | deployed 2ファイル差分のversioned SSOT | create 80–120 LOC |

Production 2 files、repo artifact 2 files。新規依存なし。runtime全体のcopyはこのsliceでは行わない。

---

### Task 1: Reproduce the HOL block with one regression test

**Files:**
- Create: `apps/lancers-revenue/tests/test_application_loop_hol.py`
- Read: `/Users/operator/.local/lib/anicca/lancers/skills/earn/lancers/scripts/application_loop.py:195-323`

**Interfaces:**
- Consumes: `application_loop.run_loop(...)`、`ApplicationLoopResult`、inject済み `discoverer` / `planner` / `submitter`。
- Produces: `test_uncertain_pending_is_quarantined_without_blocking_new_verified_application()`。

- [ ] **Step 1: Snapshot the real immutable baseline**

Run:

```bash
sha256sum /Users/operator/.local/lib/anicca/lancers/skills/earn/lancers/scripts/application_loop.py
jq '{fingerprints: (.fingerprints | length), pending: [.pending[] | {project_id, proposal_id}]}' /Users/operator/.local/state/anicca/lancers/application.json
sqlite3 'file:/Users/operator/.local/state/anicca/lancers/marketplace-ledger.sqlite3?immutable=1' "SELECT event_type, COUNT(*) FROM ledger_events GROUP BY event_type ORDER BY event_type;"
```

Expected: pending は `project_id=5585496`, `proposal_id=null` の1件。ledgerには `application_verified=11`、5585496のverified receiptなし。

- [ ] **Step 2: Add the failing stdlib regression test**

The test must:

```python
def test_uncertain_pending_is_quarantined_without_blocking_new_verified_application():
    # Import the deployed module by absolute path.
    # Stub read_pending_descriptor() to return project 5585496 terms.
    # Stub _reconcile_pending() to return submission_uncertain for 5585496.
    # Stub state_has_claim() as True only for 5585496.
    # Discover exactly [5585496, 6000001].
    # Planner receives only 6000001 and returns one eligible tailored decision.
    # Submitter records calls and returns application_verified with proposal ID 9000001.
    # Assert discoverer called once.
    # Assert submitter project IDs == ["6000001"] and never include "5585496".
    # Assert result verified_count == 1 and verified_project_ids == ["6000001"].
    # Assert result verified_provider_proposal_ids == ["9000001"].
    # Assert result unresolved_project_id == "5585496".
```

Use `unittest.mock.patch.object` and `tempfile.TemporaryDirectory`; do not read or mutate the live state from the test. Supply a complete normalized public opportunity row for each project and a timezone-aware fixed clock. At this stage the planner decision uses the current exact fields: `request_id`, `eligibility`, `reason_codes`, `proposal_text`, `price_jpy`, `deliver_date`。Task 3で同じfixtureを新しいqualification contractへ更新する。

- [ ] **Step 3: Run RED and prove the cause**

Run:

```bash
/opt/homebrew/bin/python3 -m unittest -v apps/lancers-revenue/tests/test_application_loop_hol.py
```

Expected: FAIL because `discoverer` is never called or the verified new project is absent; current `run_loop()` returns immediately after `_reconcile_pending()`.

- [ ] **Step 4: Commit only the RED test**

```bash
git add apps/lancers-revenue/tests/test_application_loop_hol.py
git commit -m "test(lancers): reproduce pending application HOL block"
git push origin docs/lancers-20k-mrr-design
```

---

### Task 2: Continue discovery after an uncertain pending readback

**Files:**
- Modify: `/Users/operator/.local/lib/anicca/lancers/skills/earn/lancers/scripts/application_loop.py:290-335`
- Test: `apps/lancers-revenue/tests/test_application_loop_hol.py`

**Interfaces:**
- Consumes: existing `_reconcile_pending()`, `_filter_claimed_rows()`, `_batch_summary()` and `ApplicationLoopResult.unresolved_project_id`.
- Produces: `run_loop()` behavior where pre-existing `submission_uncertain` is reported but does not block discovery; all other pending outcomes retain their current return behavior.

- [ ] **Step 1: Implement the minimum branch at the root cause**

At the start of `run_loop()`, keep the pending result separately. Preserve current immediate return for verified, terminal, state-invalid, and other non-`submission_uncertain` outcomes. Only `submission_uncertain` falls through:

```python
    quarantined_project_id = None
    if pending is not None:
        pending_result = _reconcile_pending(pending, Path(state_path))
        if pending_result.error != "submission_uncertain":
            if output_stream is not None:
                _emit(pending_result, output_stream)
            return pending_result.to_dict()
        quarantined_project_id = pending_result.unresolved_project_id or pending_result.project_id
```

Immediately before final emit/return, merge the old quarantine only when the new batch did not create its own unresolved project:

```python
    if quarantined_project_id is not None and result.unresolved_project_id is None:
        result = replace(result, unresolved_project_id=quarantined_project_id)
```

Do not change `_reconcile_pending()`, `_filter_claimed_rows()`, transaction state, ledger code, or pending JSON.

- [ ] **Step 2: Run GREEN**

```bash
/opt/homebrew/bin/python3 -m unittest -v apps/lancers-revenue/tests/test_application_loop_hol.py
```

Expected at this point: HOL test passes; margin regression still fails until Task 3.

- [ ] **Step 3: Run a read-only real-state check with external actions disabled**

Invoke `run_loop()` from a short Python process with the real state path but injected discoverer/planner/submitter. The injected submitter must only record its call and return a verified fake result; it must never load a browser or provider code.

Expected assertions:

```text
5585496 still present in pending state
discoverer called exactly once
submitter never called for 5585496
unresolved_project_id remains 5585496
live ledger row count unchanged
```

- [ ] **Step 4: Preserve the deployed baseline for the combined versioned patch**

Keep the immutable pre-change copies inside a `mktemp -d` directory until Task 3 creates one combined patch. Do not write backup files beside the deployed runtime or under state directories.

- [ ] **Step 5: Commit and push the isolated HOL test state**

```bash
git add apps/lancers-revenue/tests/test_application_loop_hol.py
git commit -m "fix(lancers): isolate uncertain application from discovery"
git push origin docs/lancers-20k-mrr-design
```

---

### Task 3: Enforce public ICP evidence and 70% projected margin

**Files:**
- Modify: `/Users/operator/.local/lib/anicca/lancers/skills/earn/lancers/scripts/application_loop.py:20-170`
- Modify: `/Users/operator/.local/lib/anicca/lancers/skills/gig-work/schemas/application_decisions.schema.json`
- Create: `ops/lancers/patches/0001-first-qualified-application.patch`
- Test: `apps/lancers-revenue/tests/test_application_loop_hol.py`

**Interfaces:**
- Consumes: normalized public `title` / `description` / `category`, planner `price_jpy`, and qualification cost fields.
- Produces: eligible decision accepted only with exact public evidence and `projected_net_gross_margin >= 70%`; `test_rejects_eligible_decision_below_seventy_percent_margin()`。

- [ ] **Step 1: Extend the existing decision object, not a new service**

Add required `qualification` to each decision. It is `null` for ineligible and this exact object for eligible:

```json
{
  "small_b2b_evidence": "4–240 character exact excerpt from title/description/category",
  "sns_staff_evidence": "4–240 character exact excerpt proving 0–1 staff or approved proxy",
  "expected_platform_fee_jpy": 19600,
  "expected_ai_cost_jpy": 2000,
  "expected_subcontractor_cost_jpy": 0,
  "expected_revision_refund_allowance_jpy": 7000,
  "cost_source_version": "lancers-g1-conservative-v1"
}
```

The conservative v1 rule requires `expected_platform_fee_jpy >= ceil(price_jpy * 20 / 100)`. This is a safety allowance, not a claim about the current provider fee. All other costs are non-negative integers and must reflect this proposal's bounded scope. Founding proposal price is at least ¥98,000 and remains within the observed budget.

- [ ] **Step 2: Validate evidence and margin before submit**

Extend `DECISION_FIELDS` and `_validate()` only. For eligible decisions require both evidence strings to occur verbatim in the concatenated public title/description/category. Reject hallucinated or missing excerpts. Use integer arithmetic:

```python
costs = platform_fee + ai_cost + subcontractor_cost + revision_refund_allowance
if 10 * (price_jpy - costs) < 7 * price_jpy:
    raise ValueError
```

Require `price_jpy >= 98_000`, the conservative fee floor, exact `cost_source_version`, and all four costs. Do not add floating point, configuration service, database columns, or ML ranking.

- [ ] **Step 3: Tighten the planner instruction**

Update `PLANNER_RULES` so eligible requires Japanese small B2B evidence plus one of these public SNS staffing facts: dedicated staff absent, representative/small team handles SNS concurrently, or first SNS hire. Require the proposal to state buyer problem, first-30-day deliverables, channel/count/revision cap, price/due date, recurring scope, and exactly one clarification question. Pure unknown is ineligible.

- [ ] **Step 4: Run the two-test GREEN gate**

Update the Task 1 eligible fixture with the new `qualification` object. Add the second test with a ¥98,000 proposal whose total expected costs are ¥29,401; assert `planner_failed` and zero submit calls.

```bash
/opt/homebrew/bin/python3 -m unittest -v apps/lancers-revenue/tests/test_application_loop_hol.py
```

Expected: 2 PASS. One proves HOL isolation/no resend; one proves a 69.99%-or-lower projected margin never reaches submit.

- [ ] **Step 5: Create and verify the combined versioned patch**

Create `ops/lancers/patches/0001-first-qualified-application.patch` from the preserved baselines. It contains only unified diffs for:

```text
skills/earn/lancers/scripts/application_loop.py
skills/gig-work/schemas/application_decisions.schema.json
```

Verify `patch --dry-run -p1` against a temporary copy of the unmodified deployed tree. Then run `git diff --check`; scan the patch for home paths, state payloads, cookies, email, tokens, and proposal content.

- [ ] **Step 6: Commit and push qualification GREEN**

```bash
git add apps/lancers-revenue/tests/test_application_loop_hol.py ops/lancers/patches/0001-first-qualified-application.patch
git commit -m "feat(lancers): require profitable B2B application evidence"
git push origin docs/lancers-20k-mrr-design
```

---

### Task 4: One fresh adversarial verification

**Files:**
- Read only: deployed source, test, versioned patch, live state, immutable ledger, launchd plist.

**Interfaces:**
- Consumes: Task 3 commit and primary evidence.
- Produces: one verdict `SHIP`, `FIX_FIRST`, or `RETHINK`; no second review round.

- [ ] **Step 1: Dispatch one fresh GPT/Sol adversarial verifier**

The verifier must independently try to disprove:

```text
1. 5585496 cannot be resubmitted by the new path.
2. submission_uncertain no longer prevents discovery.
3. a new unresolved submit is not overwritten by the old unresolved ID.
4. verified still requires official proposal ID readback in production.
5. ApplicationReceipt uniqueness remains owned by the existing transaction/ledger path.
6. public ICP evidence cannot be fabricated outside the observed row.
7. a proposal below 70% projected margin cannot reach submit.
8. the patch contains no state, secret, or unrelated change.
```

Critical / Important findings block deployment. Minor findings are recorded. Because review is capped at one, a blocking verdict returns the implementation to systematic debugging; do not dispatch another reviewer.

---

### Task 5: Trigger the real loop and prove one verified application

**Files:**
- Modify only through the existing loop: `/Users/operator/.local/state/anicca/lancers/application.json`, planner evidence, marketplace ledger, provider state.
- Read: launchd plist and application logs.

**Interfaces:**
- Consumes: adversarial `SHIP`, passing regression test, clean git branch, installed deployed patch.
- Produces: one real new provider proposal ID, exactly one new `application_verified` ledger event, unchanged 5585496 pending quarantine.

- [ ] **Step 1: Capture before-state evidence**

Record without printing secrets:

```text
application_verified count and external IDs
5585496 pending entry hash
application.json SHA-256
latest application stdout line
```

- [ ] **Step 2: Trigger the existing launchd loop**

Declare the external submit, then run the real configured loop rather than a custom executor:

```bash
launchctl kickstart -k gui/$(id -u)/ai.anicca.lancers-revenue-application
```

Watch the existing stdout/stderr and state for a bounded 30-minute window. Do not kickstart again while a tick is active. Do not delete or edit `5585496` pending state.

- [ ] **Step 3: Verify the official external effect**

Acceptance requires all of:

```text
new project_id != 5585496
public evidence proves Japanese small B2B and SNS staff 0–1 or an approved proxy
recorded cost source and integer calculation prove projected margin >= 70%
new provider_proposal_id is non-null and read back from Lancers
exactly one new application_verified ledger event for that provider ID
no second event for the same provider ID
5585496 pending entry hash unchanged
no submit intent/effect for 5585496 during the tick
result.unresolved_project_id == 5585496
```

If no suitable project is observed, report `no_eligible_project` truthfully and let the normal 30-minute loop retry; do not weaken filters or fabricate success. If the new submit becomes uncertain, preserve both provider evidence and state, do not retry blindly, and return to systematic debugging rather than claiming G1.

- [ ] **Step 4: Close G1 only after evidence passes**

Run the regression test again, `git diff --check`, `git status --short`, and confirm branch remote SHA. Update the design/task state with the verified provider ID and receipt evidence, commit, and push. Do not begin truthful reporting or profitable-acquisition automation until G1 is closed.

## Deferred after G1

- Move the complete deployed Lancers runtime and its dependencies into the canonical life-manager repository, then make launchd execute the canonical checkout. This is a separate migration slice because copying a partial dependency graph would create a false source of truth.
- Add ranking, per-tick/day quotas, and 70%/90% capacity control to complete G3. G1 already enforces its required public ICP evidence and 70% margin floor.
- Implement truthful storefront/application reporting (G2), negotiation/contract (G4), fulfillment (G5), and payment/net MRR (G6/G7) in that order.
