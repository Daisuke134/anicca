# Paid External Wait Resume Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Execute inline in this worktree; do not dispatch subagents. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve a current, evidence-bound paid remote owner result that is waiting on an external provider as a nonterminal Paid checkpoint instead of reporting `remote_builder` failure.

**Architecture:** Keep semantic judgment in the paid owner. Deterministic code validates only identity, freshness, hashes, incomplete business outcome, and official receipt shape, then reuses the existing `remote_progress -> pending` path. No provider-specific branch, scheduler, dependency, or customer-facing send is added.

**Tech Stack:** Python 3.14, pytest, existing `paid_direct.py`, existing `paid_remote_result.py`.

## Global Constraints

- Paid only; do not change Reply/Negotiate, Apply, Storefront, or their launchd jobs.
- The existing `ai.anicca.hf-gig-paid-direct` launchd job remains the only production executor.
- Codex does not send to Coconala or perform the buyer's paid work.
- Model-authored `blocked` never authorizes completion, delivery, or a customer message.
- Customer data and state remain under one project root; secrets remain resolver-only.
- Completion still requires the full semantic effect/output, official provider and Coconala readback, buyer acceptance or transaction completion, and replay-zero.

## Evidence and adopted rule

- Production project `18183618` contains a schema-valid owner result with `status=blocked`, current semantic and requirements hashes, a JAIC completion-page receipt, and Gmail thread readback; `paid_direct.py` converts it to `failed_step=remote_builder` solely because the owner status is not `ok`.
- Temporal message passing, AWS Step Functions callback tokens, and Azure Durable Functions external events all expose durable waiting as a workflow state rather than a failed activity. Current network isolation prevents refreshing those official pages, so they are background rationale only; the code decision is grounded in the local production receipt and existing `remote_progress -> pending` contract.
- Official references: `https://docs.temporal.io/develop/python/message-passing`, `https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html`, `https://learn.microsoft.com/en-us/azure/azure-functions/durable/durable-functions-external-events`.

---

### Task 1: Treat verified external wait as nonterminal Paid progress

**Files:**
- Modify: `skills/earn/gig/scripts/paid_remote_result.py`
- Modify: `skills/earn/gig/scripts/paid_direct.py`
- Create: `skills/earn/gig/tests/test_paid_remote_wait.py`

**Interfaces:**
- Consumes: current `paid-work-decision.json`, `live-buyer-reply.json`, owner runner status, `paid-remote-intent.json`, `paid-remote-result.json`, and `paid-remote-progress.jsonl`.
- Produces: `paid_remote_result.validate_wait(root, feedback, digest, pass_start) -> dict`; `_run_remote_repair()` raises the existing `Failure("remote_progress")` only after that validation succeeds, causing `_prepare_one()` to emit `status=pending`, `failed=0`, `effect=0`, `readback=1`.

- [x] **Step 1: Write the failing contract tests**

Create `test_paid_remote_wait.py` with a minimal project fixture. Assert:

```python
def test_current_blocked_remote_result_is_a_valid_wait(tmp_path):
    root, feedback, digest = blocked_project(tmp_path)
    result = paid_remote_result.validate_wait(root, feedback, digest, pass_start=0)
    assert result["status"] == "blocked"
    assert result["business_outcome"]["required_effect_satisfied"] is False

def test_completed_or_unbound_result_cannot_be_a_wait(tmp_path):
    root, feedback, digest = blocked_project(tmp_path)
    mutate_result(root, status="ok")
    with pytest.raises(ValueError, match="not an external wait"):
        paid_remote_result.validate_wait(root, feedback, digest, pass_start=0)

def test_paid_direct_maps_only_validated_blocked_owner_to_remote_progress(tmp_path, monkeypatch):
    paid = load_paid_direct()
    seen = []
    monkeypatch.setattr(paid.paid_remote_result, "validate_wait", lambda *args: seen.append(args) or {"status": "blocked"})
    assert paid._remote_owner_checkpoint("blocked", tmp_path, "a" * 64, "b" * 64, 0) == "pending"
    assert len(seen) == 1
```

- [x] **Step 2: Run RED and confirm the missing interface is the failure**

Run:

```bash
python3 -m pytest skills/earn/gig/tests/test_paid_remote_wait.py -q
```

Expected: FAIL because `validate_wait` and `_remote_owner_checkpoint` do not exist.

- [x] **Step 3: Implement the minimum deterministic wait validator**

In `paid_remote_result.py`, validate the current feedback and requirements digest, intent/result target and desired/observed digest, `status=blocked`, `authenticated=true`, a nonempty blocker, both semantic business outcome flags false, nonempty `remaining_work`, and at least one official receipt. Reject stale results and any completed/mismatched state. Do not validate or send `customer_message` as a completion effect.

In `paid_direct.py`, add `_remote_owner_checkpoint(...)`. Return `"pending"` only when owner status is `blocked` and `validate_wait` succeeds; keep `ok` unchanged and reject every other status. In `_run_remote_repair()`, convert `"pending"` to the existing `Failure("remote_progress")` after semantic binding and required files are checked.

- [x] **Step 4: Run GREEN and focused regressions**

Run:

```bash
python3 -m pytest skills/earn/gig/tests/test_paid_remote_wait.py skills/earn/gig/tests/test_paid_disk_preflight.py -q
python3 -m py_compile skills/earn/gig/scripts/paid_direct.py skills/earn/gig/scripts/paid_remote_result.py
```

Expected: all tests pass and compilation exits 0.

- [x] **Step 5: Prove the production-shaped fixture is pending, not failed**

Run a read-only copy of project `18183618` through the focused prepare path with the current owner result. Expected output:

```json
{"status":"pending","failed":0,"effect":0,"readback":1,"_paid_prepare_status":"pending"}
```

No Coconala or JAIC mutation is permitted in this check.

- [x] **Step 6: Run the Paid regression gate**

Run the complete tests currently present under `skills/earn/gig/tests`, record the six known baseline failures and existing post-208-test hang separately, and require no new failure attributable to this slice. The two focused files and `py_compile` must be fully green.

- [x] **Step 7: Commit the slice**

```bash
git add skills/earn/gig/scripts/paid_direct.py skills/earn/gig/scripts/paid_remote_result.py skills/earn/gig/tests/test_paid_remote_wait.py docs/superpowers/plans/paid-external-wait-resume.md
git commit -m "fix(gig): preserve paid external waits"
```

- [x] **Step 8: Release and production verification**

Promote the immutable Mr.bot release with the existing release tool, verify `current` points to the committed tree, and observe the existing `ai.anicca.hf-gig-paid-direct` job's natural wake. If an explicit trigger is required, it may run only through `bin/launchctl-safe`. For `18183618`, require `pending`, `failed=0`, official JAIC/Gmail readback, no duplicate qualification submission, and no Coconala send. A later substantive JAIC response must resume the same project owner and continue toward booking rather than create a new project.

Production evidence: immutable release `e79ea8915070021530806d9851b3afe20b989c9f` becomes `current` through the existing release watcher. Two natural Paid wakes both produce `18183618 status=pending`, `failed=0`, `effect=0`, `readback=1`; the qualification effect key remains one row and the Coconala effect child remains absent. The project stays active because JAIC has not supplied a substantive eligibility response or booking path. File-by-file regression result is 57 files green, two pre-existing failure files, and one pre-existing timeout file; focused Paid tests are 14/14 green.
