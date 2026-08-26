# Coconala Installer Dispatch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make root `./install.sh coconala` enter the package-owned Coconala installer without executing the generic self-funded installer.

**Architecture:** Add a native shell dispatch before generic installer initialization. The existing no-argument path remains byte-for-byte behaviorally unchanged. A focused Node test executes the real shell scripts in an isolated HOME and proves dispatch, generic-effect zero, and unknown-product failure.

**Tech Stack:** Bash, Node `node:test`, existing `skills/earn/gig/install.sh`.

## Global Constraints

- Coconala remains the only onboarding implementation in this slice.
- No new dependency, controller, daemon, database, or abstraction.
- Root no-argument installer behavior remains unchanged.
- Dispatch occurs before generic dependency checks, runtime directory creation, or launchd mutation.
- Production code target: 15 LOC or less in one existing file; test target: 45 LOC or less.

---

### Task 1: Root Coconala dispatch

**Files:**
- Modify: `install.sh`
- Create: `test/install-coconala-dispatch.test.mjs`
- Modify: `skills/earn/gig/TODO.md`

**Interfaces:**
- Consumes: root argv where `$1` is absent, `coconala`, or an unsupported product token.
- Produces: `exec bash "$REPO_ROOT/skills/earn/gig/install.sh" "${@:2}"` for `coconala`; existing generic flow for no argument; exit 2 for unsupported product token.

- [x] **Step 1: Write the failing dispatch test**

Create a Node test that runs `bash install.sh coconala --help` under an empty temporary HOME, asserts exit 0 and the Gig onboarding CLI help marker, and asserts the generic runtime root was not created. Add a second assertion that `bash install.sh unknown-product` exits 2 without creating the runtime root.

- [x] **Step 2: Run the test to verify RED**

Run: `node --test test/install-coconala-dispatch.test.mjs`

Expected: FAIL because root `install.sh` ignores `coconala` and creates/runs the generic installer path.

- [x] **Step 3: Implement the minimal shell dispatch**

Immediately after `REPO_ROOT` is resolved and before generic environment/default initialization, branch on argument count. `coconala` execs the existing package installer with the remaining arguments. Any other non-option product token prints a concise supported-command error and exits 2. No argument continues into the existing generic body.

- [x] **Step 4: Run focused and compatibility tests**

Run:

```bash
node --test test/install-coconala-dispatch.test.mjs test/install-isolation.test.mjs
```

Expected: all tests PASS; dispatch test proves generic runtime effect zero and isolation test proves the legacy no-argument install remains unchanged.

- [x] **Step 5: Update state and publish**

Mark atomic Coconala item 1 complete in `skills/earn/gig/TODO.md`, record test counts and exact behavior, run `git diff --check`, commit, fetch/rebase, push main, and read back remote main.
