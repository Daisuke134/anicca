# Terra-high Editorial Escalation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give each article-language editorial gate one Terra-medium evaluation and, only after changed draft bytes following a FAIL, one Terra-high evaluation, with no third paid judge call.

**Architecture:** `scripts/editorial-gate.sh` already owns the current draft hash and prior hash-bound editorial receipt. It deterministically selects requested effort from that receipt, passes the effort through the existing sole model runner, and persists the requested effort in the next receipt. A prior high FAIL plus another changed draft exits before invoking any model; the caller must reroute instead of buying more reasoning.

**Tech Stack:** Bash, jq, Python standard library embedded JSON update, existing shell contract tests.

## Global Constraints

- First editorial evaluation for one language/run requests `medium`.
- The first changed draft after a hash-bound editorial FAIL requests `high`.
- A hash-bound high FAIL permits no third editorial model call for that language/run.
- Same-byte FAIL remains the existing exit `76` and makes no model call.
- New high-exhausted refusal uses exit `77` and makes no model call.
- This slice does not implement Sol, token/cost accounting, `block_freeze`, or active-six.

---

### Task 1: Hash-bound one-shot Terra-high editorial gate

**Files:**
- Modify: `skills/writer-agent/tests/editorial-revision-boundary.sh`
- Modify: `skills/writer-agent/scripts/editorial-gate.sh:57-125,217-231`
- Modify after verification: `docs/writer-agent/WRITER-AGENT-SSOT.md`

**Interfaces:**
- Consumes: prior `gates/editorial-<lang>.json` fields `verdict`, `article_sha256`, and new `requested_reasoning_effort`.
- Produces: model-runner environment `ARTICLE_MODEL_REASONING_EFFORT=medium|high`, receipt field `requested_reasoning_effort`, exit `77` after a high FAIL is already spent.

- [ ] **Step 1: Extend the existing boundary test and verify RED**

Make the fake model runner append `${ARTICLE_MODEL_REASONING_EFFORT:-unset}` for each call. Assert the first call is `medium`, the changed-draft call is `high`, both receipts carry their requested effort, and a third changed draft exits `77` without a third call. Run `bash skills/writer-agent/tests/editorial-revision-boundary.sh`; expected failure is `unset` instead of `medium` before production changes.

- [ ] **Step 2: Implement the minimal effort state machine**

Before the judge call, set `REQUESTED_REASONING_EFFORT=medium`. If the prior receipt is FAIL with different bytes and its effort is not `high`, select `high`. If its effort is `high`, log `BLOCK:high-escalation-exhausted`, emit an error, and exit `77`. Invoke only:

```bash
ARTICLE_MODEL_REASONING_EFFORT="$REQUESTED_REASONING_EFFORT" \
  "$MODEL_RUNNER" judge --prompt-file -
```

Persist `requested_reasoning_effort` beside the current article hash.

- [ ] **Step 3: Run focused GREEN and adjacent editorial contracts**

Run the revised boundary test plus `editorial-cta-contract.sh`, `editorial-citation-contract.sh`, and `quality-gate-persistent-control.sh`. All must pass.

- [ ] **Step 4: Run real non-publishing medium/high E2E**

Use a temporary run/article and the live gate with the real model runner. Capture a first FAIL receipt requesting medium, change the article bytes according to its fix, then prove the second receipt requests high. If the real first call passes, use the command-contract fake for the state transition and separately prove real model-runner accepts `ARTICLE_MODEL_REASONING_EFFORT=high`; never alter or publish a live article.

- [ ] **Step 5: Run full regression delta**

Run `bash tests/run-all.sh`. The new/changed Writer test must pass and the existing unrelated 32-file failure set must not grow.

- [ ] **Step 6: Promote, document, and push**

Commit/push the isolated runtime branch, promote that exact commit to the live checkout, rerun the focused contract on the live path, then update Writer SSOT with RED/GREEN/E2E/full-suite receipts. Send the changed SSOT through Telegram and commit/push both SSOT remotes.

