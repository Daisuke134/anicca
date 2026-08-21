# Agent Economy Public Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the agent-economy control boundary as a safe, read-first Life Manager skill.

**Architecture:** `SKILL.md` documents the existing money-truth and treasury modules; `run.sh` invokes only receipt reconciliation and emits one JSON summary. The skill is declared dormant in `skills/registry.json` so installation syncs it without adding a new autonomous money action to every loop menu.

**Tech Stack:** POSIX shell, Node.js ESM, registry-driven installer.

**Spec:** `docs/superpowers/specs/2026-08-21-agent-economy-design.md`

## Global Constraints

- Calling the meta skill does not sign, broadcast, trade, post, or buy compute.
- No private key variable is read or passed by the wrapper.
- External revenue remains zero unless receipt reconciliation proves it.
- The registry status stays `dormant` until the release-backed loop has a verified production witness.

---

### Task 1: Add the public skill contract and registry declaration

**Files:**
- Create: `skills/agent-economy/SKILL.md`
- Create: `skills/agent-economy/run.sh`
- Modify: `skills/registry.json`
- Test: `test/agent-economy-skill.test.mjs`

**Interfaces:**
- Consumes: `$ANICCA_HOME`, optional `$EARN_LEDGER`, and the existing receipt reconciler.
- Produces: one JSON money-truth summary; no transaction side effect.

- [ ] **Step 1: Write the contract test**

  Read `SKILL.md` and `run.sh` from disk and assert the frontmatter name, receipt sidecar, TaskMarket/OpenRouter guidance, reconciler invocation, `ANICCA_HOME` requirement, and absence of private-key variable names.

- [ ] **Step 2: Run the contract test and observe the RED result**

  Run: `node --test test/agent-economy-skill.test.mjs`
  Expected: FAIL with `ENOENT` because the public skill files do not yet exist.

- [ ] **Step 3: Add the frontmatter, read-first rules, wrapper, and dormant registry entry**

  Create `SKILL.md` with the read-first contract, create an executable `run.sh` that invokes only `reconcile-receipts.mjs`, and add the `agent-economy` registry row with `status:"dormant"`, `risk:"safe"`, and `entrypoint:"run.sh"`.

- [ ] **Step 4: Run the contract and integration checks**

  Run: `node --test test/agent-economy-skill.test.mjs`, `node -e "JSON.parse(require('fs').readFileSync('skills/registry.json','utf8'))"`, `bash -n skills/agent-economy/run.sh`, `npm run test:install`, `npm run test:oss`, and `git diff --check`.
  Expected: the contract, registry parse, install isolation, and OSS self-contained suites pass.

- [ ] **Step 5: Commit and push**

  Run: `git add skills/agent-economy/SKILL.md skills/agent-economy/run.sh skills/registry.json test/agent-economy-skill.test.mjs docs/superpowers/plans/2026-08-21-agent-economy-skill.md && git commit -m "feat: publish agent economy control skill" && git push`
