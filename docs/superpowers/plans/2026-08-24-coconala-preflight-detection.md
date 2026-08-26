# Coconala Preflight Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give `./install.sh coconala preflight` one side-effect-free, machine-readable check of the Mac architecture, supported Python, Codex CLI/auth state, CloakBrowser binary, and disk headroom.

**Architecture:** Keep checks in the existing package shell installer and reuse native commands plus the existing CloakBrowser path contract. `preflight` performs no installs and no login; later atomic items consume its exact failed checks to install dependencies and invoke `codex login`.

**Tech Stack:** Bash, Node `node:test`, macOS native commands, Codex CLI `login status`.

## Global Constraints

- Production changes stay in `skills/earn/gig/install.sh`, target 60 LOC or less.
- One focused test file, target 90 LOC or less.
- No filesystem writes, browser launch, login, package install, launchd change, or marketplace effect.
- JSON output contains check names and booleans only; no auth contents or personal paths.
- Supported baseline remains Darwin arm64, Python 3.13+, CloakBrowser Chromium, 512 MiB free disk, and authenticated Codex CLI.

---

### Task 1: Side-effect-free preflight detection

**Files:**
- Modify: `skills/earn/gig/install.sh`
- Create: `test/install-coconala-preflight.test.mjs`
- Modify: `skills/earn/gig/TODO.md`

**Interfaces:**
- Consumes: `skills/earn/gig/install.sh preflight` and current machine state.
- Produces: one JSON object with `status`, `darwin`, `arm64`, `python`, `codex_cli`, `codex_authenticated`, `cloakbrowser`, and `disk_headroom`; exit 0 only when every check is true, otherwise exit 2.

- [x] **Step 1: Write RED tests against the real shell**

Use a temporary PATH with deterministic `uname`, `python3`, `codex`, and `df` executables plus a temporary executable CloakBrowser binary. Assert the all-ready fixture exits 0 with every boolean true. Remove the browser binary and assert exit 2, `cloakbrowser=false`, and no HOME/runtime files were created.

- [x] **Step 2: Verify RED**

Run: `node --test test/install-coconala-preflight.test.mjs`

Expected: FAIL because the current package installer treats `preflight` as missing onboarding arguments.

- [x] **Step 3: Implement minimal checks**

Add a `preflight` branch before the existing Python exec. Use fixed-format command exit status for platform, Python, Codex, browser glob, and disk checks; emit one JSON line and exit 0/2. Preserve all other argv forwarding unchanged.

- [x] **Step 4: Verify focused and dispatch compatibility**

Run:

```bash
node --test test/install-coconala-preflight.test.mjs test/install-coconala-dispatch.test.mjs test/install-isolation.test.mjs
```

Expected: all tests PASS.

- [x] **Step 5: Record, review, and publish**

Update atomic item 2a and this plan, run `bash -n`, `git diff --check`, commit, fetch/rebase, push main, read back remote, and obtain fresh read-only adversarial verification.
