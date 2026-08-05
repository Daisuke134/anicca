# Terra-medium Writer Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Writer's real Codex process boundary use `gpt-5.6-terra` with `medium` reasoning by default instead of `gpt-5.6-luna` with `xhigh`, with a regression receipt and one real provider invocation.

**Architecture:** Keep `runtime/model-runner.sh` as the only provider process boundary. Test its observable command contract through a fake Codex executable that captures arguments and stdin; do not add model routing, Sol escalation, publication changes, or accounting in this slice. Update the runtime README and Writer SSOT only after the executable contract is GREEN.

**Tech Stack:** Bash, Python standard library test harness, Codex CLI, Git worktree.

## Global Constraints

- Default Codex model is exactly `gpt-5.6-terra`.
- Default reasoning effort is exactly `medium`.
- This slice does not implement `Terra high`, Sol triggers, cost accounting, `block_freeze`, or active-six publication.
- No public article is created by verification.
- The pre-change repository baseline is `336/368 passed`; its 32 failures are outside Writer and must not increase.
- The implementation worktree is `/Users/anicca/profitable-claude/.worktrees/writer-terra-medium` on `fix/writer-terra-medium`.

---

### Task 1: Default Writer Codex model contract

**Files:**
- Create: `skills/writer-agent/tests/test_model_runner_contract.py`
- Modify: `skills/writer-agent/runtime/model-runner.sh:240-249`
- Modify: `skills/writer-agent/runtime/README.md:16-25`
- Modify after verification: `docs/writer-agent/WRITER-AGENT-SSOT.md` in the Anicca SSOT repository

**Interfaces:**
- Consumes: `model-runner.sh judge --prompt-file <path>` and existing `ARTICLE_CODEX_BIN`, `ARTICLE_PROVIDER`, `ARTICLE_MODEL_ROOT`, `ARTICLE_MODEL_STATE_ROOT`, `ARTICLE_MODEL_LOG`, and `ARTICLE_PROVIDER_HEALTH` environment boundaries.
- Produces: a Codex invocation containing `--model gpt-5.6-terra` and `model_reasoning_effort="medium"`, with the input prompt preserved on stdin.

- [ ] **Step 1: Write the failing command-contract test**

Create a standard-library unittest that installs a temporary executable named `codex`. The executable writes every argument as one JSON array plus stdin bytes to capture files and exits zero. Invoke the real runner in `judge` mode with an isolated model root/state/log/health path and assert:

```python
self.assertEqual(args[args.index("--model") + 1], "gpt-5.6-terra")
self.assertIn('model_reasoning_effort="medium"', args)
self.assertEqual(captured_stdin, "Return exactly TERRAMEDIUM")
```

- [ ] **Step 2: Run RED and preserve the expected failure**

Run:

```bash
python3 skills/writer-agent/tests/test_model_runner_contract.py
```

Expected: FAIL because the actual captured model is `gpt-5.6-luna` and the effort is `xhigh`.

- [ ] **Step 3: Make the minimal production change**

Change only the two defaults in the Codex command:

```bash
--model gpt-5.6-terra
-c "model_reasoning_effort=\"${ARTICLE_MODEL_REASONING_EFFORT:-medium}\""
```

- [ ] **Step 4: Run the focused GREEN test**

Run:

```bash
python3 skills/writer-agent/tests/test_model_runner_contract.py
```

Expected: one test passes with zero failures.

- [ ] **Step 5: Update the runtime contract documentation**

Replace the README's `gpt-5.6-luna`/`xhigh` statement with `gpt-5.6-terra`/`medium`. State explicitly that later high-effort and Sol routing are not implemented by this slice.

- [ ] **Step 6: Run a real provider E2E without publication side effects**

Use `ARTICLE_PROVIDER=codex`, isolated state/log/health paths, and `judge` mode with the prompt `Return exactly TERRAMEDIUM`. Verify exit zero, output contains `TERRAMEDIUM`, and the log records `provider=codex mode=judge status=success`. This call must not use agent mode or publish anything.

- [ ] **Step 7: Run scoped and repository regression verification**

Run the focused unittest again, `bash -n skills/writer-agent/runtime/model-runner.sh`, and `bash tests/run-all.sh`. The full suite must have no more than the same 32 pre-existing non-Writer failures and the new Writer test must pass inside the suite.

- [ ] **Step 8: Update receipts and commit/push each repository**

Record RED, GREEN, real-provider E2E, test counts, runtime commit, and remaining next slice in the Writer SSOT. Commit/push `fix/writer-terra-medium` in the runtime repository, then commit/push the current Writer SSOT branch in the Anicca repository. Send the changed SSOT artifact to Telegram with hashes and known defects.

