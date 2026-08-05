# Terra-high Editorial Escalation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give each `(language,current_article_sha256)` editorial key one
bounded evaluation under the existing medium/high policy. A newly authorized
reroute hash receives one bounded evaluation; the same language/hash remains
exhausted and cannot purchase a third call.

**Architecture:** `scripts/editorial-gate.sh` owns the language, current draft
hash, and prior hash-bound editorial receipt. It deterministically selects the
requested effort from the receipt, passes it through the existing sole model
runner, and persists the effort and key in the next receipt. A prior high FAIL
for the same language/hash exits before invoking any model; an authorized new
reroute hash gets its one bounded evaluation instead of inheriting stale
exhaustion.

**Tech Stack:** Bash, jq, Python standard library embedded JSON update, existing shell contract tests.

## Global Constraints

- First editorial evaluation for a language/current-hash key requests `medium`.
- The first authorized changed draft after a hash-bound editorial FAIL may
  request `high` under the existing policy.
- A hash-bound high FAIL permits no further editorial model call for that same
  language/current-hash key.
- Same-byte FAIL remains the existing exit `76` and makes no model call.
- Same-key high-exhausted refusal uses exit `77` and makes no model call; a
  newly authorized reroute hash is a new key and receives one bounded call.
- This slice does not implement Sol, token/cost accounting, `block_freeze`, or active-six.

---

### Task 1: Hash-bound one-shot Terra-high editorial gate

**Files:**
- Modify: `skills/writer-agent/tests/editorial-revision-boundary.sh`
- Modify: `skills/writer-agent/scripts/editorial-gate.sh:57-125,217-231`
- Modify after verification: `docs/writer-agent/WRITER-AGENT-SSOT.md`

**Interfaces:**
- Consumes: prior `gates/editorial-<lang>.json` fields `verdict`,
  `article_sha256`, `language`, reroute authorization, and new
  `requested_reasoning_effort`.
- Produces: model-runner environment `ARTICLE_MODEL_REASONING_EFFORT=medium|high`,
  receipt fields for `(language,current_article_sha256)`, and exit `77` only
  after a high FAIL is already spent for that exact key.

- [x] **Step 1: Extend the existing boundary test and verify RED**

Make the fake model runner append `${ARTICLE_MODEL_REASONING_EFFORT:-unset}` for each call. Assert the first call is `medium`, the authorized changed-draft call is `high`, a same-key replay exits `77` without another call, and a newly authorized reroute hash gets exactly one bounded call. Run `bash skills/writer-agent/tests/editorial-revision-boundary.sh`; expected failure is `unset` instead of `medium` before production changes.

- [x] **Step 2: Implement the minimal effort state machine**

Before the judge call, derive a key from language and current article hash.
Set `REQUESTED_REASONING_EFFORT=medium` for a new key. If the prior receipt for
the same run/language has different authorized bytes and its effort is not
`high`, select `high`; if the prior receipt for the exact current key is a high
FAIL, log `BLOCK:high-escalation-exhausted`, emit an error, and exit `77`.
Invoke only:

```bash
ARTICLE_MODEL_REASONING_EFFORT="$REQUESTED_REASONING_EFFORT" \
  "$MODEL_RUNNER" judge --prompt-file -
```

Persist `requested_reasoning_effort` beside the current article hash.

- [x] **Step 3: Run focused GREEN and adjacent editorial contracts**

Run the revised boundary test plus `editorial-cta-contract.sh`, `editorial-citation-contract.sh`, and `quality-gate-persistent-control.sh`. All must pass.

- [x] **Step 4: Run real non-publishing medium/high E2E**

Use a temporary run/article and the live gate with the real model runner. Capture a first FAIL receipt requesting medium, change the article bytes according to its fix, then prove the second receipt requests high. If the real first call passes, use the command-contract fake for the state transition and separately prove real model-runner accepts `ARTICLE_MODEL_REASONING_EFFORT=high`; never alter or publish a live article.

- [x] **Step 5: Run full regression delta**

Run `bash tests/run-all.sh`. The new/changed Writer test must pass and the existing unrelated 32-file failure set must not grow.

- [x] **Step 6: Promote, document, and push**

Commit/push the isolated runtime branch, promote that exact commit to the live checkout, rerun the focused contract on the live path, then update Writer SSOT with RED/GREEN/E2E/full-suite receipts. Send the changed SSOT through Telegram and commit/push both SSOT remotes.
