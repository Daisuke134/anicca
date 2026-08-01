# Capafy P1 Immediate Publish Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task by task and `test-driven-development` for every behavior change.

**Goal:** Remove synthetic Instagram warmup and elapsed-day waiting from Capafy, then autonomously start and verify one original Reel immediately after a browser-owned account session is verified.

**Architecture:** The deterministic lifecycle grants a single `publish_probe` capability from verified browser ownership. The creative agent produces original product education, the browser adapter proves a newly observed Reel URL and re-verifies the owner handle after sharing, P0 alone reports the verified URLs, and any challenge retires the account and immediately wakes replacement. The daily schedule remains a fallback cadence, while account creation and explicit kickstart can wake it immediately.

**Tech Stack:** Bash controllers and LaunchAgents, Python 3 lifecycle/outcome/browser adapters, pytest and shell integration tests, CloakBrowser CDP, Telegram P0 handoff.

---

## Task 1: Replace warmup-derived lifecycle semantics

**Files:**

- Modify: `skills/earn/capafy-marketing/tests/test_capafy_ig_lifecycle.py`
- Modify: `skills/earn/capafy-marketing/scripts/capafy_ig_lifecycle.py`

**RED:** Rewrite lifecycle tests so a verified active browser-owned account immediately derives `status=publish_probe_ready` and `capability=publish_probe`, regardless of account age or any legacy warmup file. Preserve a verified Reel only for the same handle, deriving `reach_observing`; derive `commercial_ready` only when that Reel and verified reach both exist. Require `record-reel` to store `first_publish_probe_verified`.

Run:

```bash
pytest -q skills/earn/capafy-marketing/tests/test_capafy_ig_lifecycle.py
```

Expected RED: old `warmup_0_of_2`, `warmup_only`, and `noncommercial_post` outputs fail the new assertions.

**GREEN:** Remove warmup action/date parsing, remove the `--warmup` CLI input, use capabilities `none`, `publish_probe`, and `commercial_post`, and preserve incident/reel/reach evidence only for the same handle. Keep legacy registry status `warming` readable during migration, but never interpret it as a wait gate.

Commit after the focused test passes.

## Task 2: Make account creation hand off directly to publishing

**Files:**

- Modify: `skills/earn/capafy-marketing/tests/test_capafy_ig_account_manager.sh`
- Modify: `skills/earn/capafy-marketing/tests/test_capafy_outcome.py`
- Modify: `skills/earn/capafy-marketing/capafy-ig-account-manager.sh`
- Modify: `skills/earn/capafy-marketing/scripts/capafy_outcome.py`
- Modify: `skills/earn/capafy-marketing/capafy-marketing-handoff.sh`

**RED:** Require an independently verified new account to persist `publish_probe_ready`, render natural language that says the first original Reel starts now, contain no warmup count/day language, and kickstart `ai.anicca.capafy-ig-marketing-daily` exactly once after the account-created terminal is delivered. Sender retry must remain idempotent and must not reprovision.

Run:

```bash
pytest -q skills/earn/capafy-marketing/tests/test_capafy_outcome.py
bash skills/earn/capafy-marketing/tests/test_capafy_ig_account_manager.sh
```

**GREEN:** Remove warmup fields and progress/waiting outcome contracts, persist the immediate capability, and wake the content owner after successful account handoff. Preserve the existing replacement and exactly-once Telegram boundaries.

Commit after both focused suites pass.

## Task 3: Publish immediately and verify the post-write owner session

**Files:**

- Modify: `skills/earn/capafy-marketing/tests/test_capafy_reel_poster.py`
- Modify: `skills/earn/capafy-marketing/tests/test_capafy_marketing_controller.sh`
- Modify: `skills/earn/capafy-marketing/scripts/capafy_reel_poster.py`
- Modify: `skills/earn/capafy-marketing/capafy-ig-marketing-daily.sh`
- Modify: `skills/earn/capafy-marketing/scripts/capafy_outcome.py`

**RED:** Require `publish_probe` for the first live post. A successful adapter result must contain exactly one newly observed Reel URL and `owner_session_verified=true`, obtained by reading the active handle again after sharing. The controller must start creative work immediately for a verified account without warmup evidence, reject hard commercial intent, refuse any poster result lacking post-write ownership proof, and record/report only after both proofs exist.

Run:

```bash
pytest -q skills/earn/capafy-marketing/tests/test_capafy_reel_poster.py
bash skills/earn/capafy-marketing/tests/test_capafy_marketing_controller.sh
```

**GREEN:** Remove the warmup file and waiting branch from the daily controller, pass `publish_probe`, add post-write handle verification to the poster, carry the proof into the terminal envelope, and render it in the natural-language published message. Challenge handling remains contain-retire-replace.

Commit after both focused suites pass.

## Task 4: Remove the obsolete scheduler and truthful-health residue

**Files:**

- Delete: `skills/earn/capafy-marketing/warm_jitter.sh`
- Delete: `skills/earn/capafy-marketing/tests/test_capafy_ig_warmup.sh`
- Delete: `skills/earn/capafy-marketing/launchd/ai.anicca.capafy-marketing-warmup.plist`
- Modify: `skills/earn/capafy-marketing/tests/test_capafy_p1_launchd.py`
- Modify: `skills/self/tests/test_capafy_ig_account_state.sh`
- Modify: `skills/earn/capafy-marketing/tests/test_capafy_goal_monitor_report.py`
- Modify: `skills/earn/capafy-marketing/capafy-goal-monitor.sh`

**RED:** Require exactly the manager and daily Marketer jobs, assert that no source warmup job/script exists, and require the goal report to describe lifecycle/session/post health rather than `warmup day`, `warmup loaded`, or `already_live`.

Run:

```bash
pytest -q skills/earn/capafy-marketing/tests/test_capafy_p1_launchd.py skills/earn/capafy-marketing/tests/test_capafy_goal_monitor_report.py
bash skills/self/tests/test_capafy_ig_account_state.sh
```

**GREEN:** Delete the warmup job path and migrate goal-monitor fields to the verified lifecycle vocabulary. Keep historical warmup data on disk as inert evidence; do not execute or count it.

Commit after the focused suites pass.

## Task 5: Regression, runtime migration, and immediate production proof

**Files:**

- Modify after each verified result: `docs/superpowers/specs/2026-08-01-capafy-self-improving-revenue-loop-design.md`

Run all focused and contract suites:

```bash
pytest -q \
  skills/earn/capafy-marketing/tests/test_capafy_ig_lifecycle.py \
  skills/earn/capafy-marketing/tests/test_capafy_reel_poster.py \
  skills/earn/capafy-marketing/tests/test_capafy_ig_session_verify.py \
  skills/earn/capafy-marketing/tests/test_capafy_outcome.py \
  skills/earn/capafy-marketing/tests/test_capafy_p1_launchd.py \
  skills/earn/capafy-marketing/tests/test_capafy_goal_monitor_report.py
bash skills/earn/capafy-marketing/tests/test_capafy_ig_account_manager.sh
bash skills/earn/capafy-marketing/tests/test_capafy_marketing_controller.sh
bash skills/earn/capafy-marketing/tests/test_capafy_marketing_outcome.sh
bash skills/self/tests/test_capafy_ig_account_state.sh
bash -n skills/earn/capafy-marketing/capafy-ig-account-manager.sh \
  skills/earn/capafy-marketing/capafy-ig-marketing-daily.sh \
  skills/earn/capafy-marketing/capafy-goal-monitor.sh \
  skills/earn/capafy-marketing/capafy-marketing-handoff.sh
git diff --check
```

Integrate the verified commits into the production branch without overwriting unrelated dirty work. Keep the already-unloaded installed warmup plist only as a timestamped disabled backup or remove that exact file recoverably; verify the label is absent from `launchctl`. Reload the manager/daily plists if their source contract changed, derive the live lifecycle snapshot, and kickstart `ai.anicca.capafy-ig-marketing-daily` immediately.

Production acceptance requires all of:

1. a real new `https://www.instagram.com/reel/.../` URL;
2. the Capafy skill URL and attributed campaign URL in the same terminal envelope;
3. `owner_session_verified=true` after the share;
4. exactly one Telegram delivery for that envelope;
5. lifecycle state `first_publish_probe_verified` or `reach_observing` for `@capafy.skills8m4q2z`;
6. no loaded Capafy warmup job and no synthetic engagement execution;
7. no fabricated claim if Instagram, the content agent, or the Capafy listing blocks completion.

After each verified task, append the test evidence and commit hash to the living spec before continuing.
