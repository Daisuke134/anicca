# X Tweeter Chinese Source Hourly Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore `@selawmqt` X Tweeter and add hourly source-grounded original posts from public Chinese content pages.

**Architecture:** Restore the last verified original-post wrapper and admission contract, then add one deterministic public-index collector that returns evidence rather than making editorial decisions. Reuse the existing model and browser-publishing pipeline, with a separate state ledger and launchd owner.

**Tech Stack:** Python 3.11, Bash, launchd TOML/plist generation, existing Codex Luna model boundary, existing Playwright X publisher.

**Spec:** `docs/superpowers/specs/2026-08-27-x-tweeter-chinese-hourly-design.md`

## Global Constraints

- Do not call or copy MediaCrawler in the commercial runtime.
- Do not modify X Reposter behavior or Affiliate distribution queues.
- Publish only to the verified `@selawmqt` identity through `affiliate/x-en`.
- One wake may create at most one X effect; unknown effects never retry.
- Every post includes the original Chinese source URL and durable evidence.

---

### Task 1: Restore the independent original owner

**Files:**
- Restore: `skills/x-tweeter/x-tweeter-cli.sh`
- Restore: `skills/x-tweeter/x-tweeter-healthcheck.sh`
- Restore: `skills/x-tweeter/scripts/original_contract.py`
- Restore: `loops/x-tweeter/loop.toml`
- Test: `skills/x-tweeter/tests/test_launchd_contract.py`
- Test: `skills/x-tweeter/tests/test_role_separation.py`

**Interfaces:**
- Consumes: existing `skills/x-repost/x-repost-cli.sh` original mode.
- Produces: an hourly launchd owner with separate state and Affiliate English identity.

- [ ] Write tests requiring minute-0 hourly cadence, `x:affiliate-en` identity, original-only mode, separate state, and disabled Affiliate queues.
- [ ] Run the tests and confirm they fail because the owner files are absent.
- [ ] Restore the minimal prior owner files and adjust only cadence and identity.
- [ ] Run the focused tests and confirm they pass.
- [ ] Commit and push the restored owner.

### Task 2: Add public Chinese source evidence

**Files:**
- Create: `skills/x-tweeter/scripts/chinese_source_collect.py`
- Modify: `skills/x-tweeter/scripts/original_contract.py`
- Test: `skills/x-tweeter/tests/test_chinese_source_collect.py`
- Test: `skills/x-tweeter/tests/test_original_contract.py`

**Interfaces:**
- Produces: `collect(search_html: str, query: str, observed_at: str) -> dict` with bounded candidates.
- Produces: admission fields `source_domain`, `source_language`, `evidence_translation`, and URL-dedupe protection.

- [ ] Write tests for seven allowed domains, redirect URL decoding, bounded dedupe, disallowed-domain rejection, URL duplicate rejection, and mandatory English translation.
- [ ] Run the tests and confirm they fail because the collector and fields are absent.
- [ ] Implement the smallest parser and extend the existing admission contract.
- [ ] Run focused and role-separation tests.
- [ ] Commit and push the source evidence slice.

### Task 3: Connect discovery to the original-post pass

**Files:**
- Modify: `skills/x-tweeter/x-tweeter-cli.sh`
- Create: `skills/x-tweeter/config/chinese-queries.txt`
- Test: `skills/x-tweeter/tests/test_entrypoint.py`

**Interfaces:**
- Consumes: bounded collector receipt and existing model boundary.
- Produces: source/draft/critic receipts consumed by `original_contract.py` and existing `x_post.py`.

- [ ] Write a failing entrypoint test requiring public-index collection before model selection, source URL preservation, and no MediaCrawler invocation.
- [ ] Run the test and confirm the missing discovery stage is the failure.
- [ ] Add the bounded discovery/model/admission stage while reusing existing publication and recovery code.
- [ ] Run all X Tweeter and relevant X Reposter tests.
- [ ] Commit and push the integrated pass.

### Task 4: Release and official readback

**Files:**
- Modify only generated release/plist state outside Git through existing repository commands.

**Interfaces:**
- Produces: immutable release, loaded launchd owners, official X permalink, and replay-zero evidence.

- [ ] Fetch, rebase onto current `origin/main`, and rerun focused tests.
- [ ] Merge the feature branch to main and push.
- [ ] Cut the canonical immutable release and regenerate/reload exact X Tweeter plists.
- [ ] Read back loaded ProgramArguments, cadence, identity, and current release SHA.
- [ ] Kickstart the real owner and wait for its terminal receipt.
- [ ] Verify the exact post on `@selawmqt`, then run a second wake and prove zero duplicate external effect.

