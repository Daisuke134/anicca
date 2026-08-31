# Codex Account Failover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every shared Mr.bot Codex execution start with account 1 and retry account 2 only for pre-effect machine-readable quota/auth failure.

**Architecture:** Expand each configured Codex candidate into account-scoped candidates inside the canonical runner. Each account gets its own automation home and auth source; existing provider fallback order remains unchanged after account 2. Do not add account 3, a daemon, a database, or per-loop routing.

**Tech Stack:** Python 3 standard library, JSON configuration, `unittest`

**Spec:** `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md` §10.0.1

## Global Constraints

- Account 1 is `~/.codex/auth.json`; account 2 is `~/.codex-acct2/auth.json`.
- Fallback to the next account only for pre-effect `transient_quota` or `transient_auth`.
- Invalid output, task/browser failure, unknown effect, or any observed effect fails closed.
- Account credentials, IDs, and auth bodies never enter logs, evidence, specs, or committed files.
- Preserve existing timeout/unavailable provider fallback after the Codex account chain.

---

### Task 1: Shared account-scoped Codex candidates

**Files:**
- Modify: `runtime/agent-runner/agent_runner.py`
- Modify: `runtime/agent-runner/config.json`
- Test: `runtime/agent-runner/tests/test_codex_account_failover.py`

**Interfaces:**
- Consumes: provider `accounts` entries with `alias`, `automation_home`, and `auth_file`.
- Produces: account-scoped effective candidates and attempt evidence containing only the account alias.

- [ ] **Step 1: Write failing account isolation and ordering tests**

Assert the canonical config order is account 1 then account 2, and that each effective candidate resolves only its own automation home/auth target.

- [ ] **Step 2: Run RED**

Run: `python3 -m unittest runtime.agent-runner.tests.test_codex_account_failover -v`

Expected: FAIL because account expansion and account-scoped environment resolution do not exist.

- [ ] **Step 3: Implement minimal account expansion**

Expand Codex candidates from `providers.codex.accounts` in order. Merge only the selected account's alias, automation home, and auth file into a copied provider config.

- [ ] **Step 4: Write failing fallback gate tests**

Use a fake Codex executable that records the account-specific `CODEX_HOME`: account 1 quota/auth before effect invokes account 2 exactly once; invalid output/task failure does not; account 1 and 2 quota then reaches only the existing next provider.

- [ ] **Step 5: Implement minimal fallback gate**

Continue within the same provider only for `transient_quota` or `transient_auth` and no effect evidence. Preserve the existing cross-provider transient fallback contract after the account chain.

- [ ] **Step 6: Run GREEN and focused regression**

Run: `python3 -m unittest runtime.agent-runner.tests.test_codex_account_failover -v`

Run: `python3 -m unittest discover -s runtime/agent-runner/tests -p 'test_*.py'`

Expected: all PASS, no credential contents in output.

- [ ] **Step 7: Commit**

Commit only the three task files and this plan.
