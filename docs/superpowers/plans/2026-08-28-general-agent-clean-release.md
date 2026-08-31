# GA-12B Clean General-Agent Release Plan

> **For agentic workers:** Use Superpowers task-by-task. Verify the staged public tree, then the pushed archive.

**Goal:** Make the public general-agent release reproducibly contain its manifest, reference-only secret contract, local/cloud instructions, root license, and third-party notices.

**Architecture:** Extend the existing standard-library clean-user test. Archive the Git index (equal to `HEAD` in CI), extract it into a temporary directory, and inspect only public files. Add one root notice for the four design references already named in the README; vendor no source.

**Files:**

- Modify: `runtime/loop/tests/test_clean_user_install.py`
- Add: `THIRD_PARTY_NOTICES.md`
- Modify: `docs/superpowers/specs/2026-08-01-dais-mr-bot-five-phase-execution-spec.md`

## Task 1: Reproducible public archive

- [x] Add a failing test that archives the staged tree and requires the manifest, all `_REF` example values to use `secret://`, local/cloud quick starts, `LICENSE`, and four notices.
- [x] Add the smallest root notice with project, license, source URL, and “design reference only; no vendored source” boundary.
- [x] Run the clean-user test, provider manifest test, changed-path PII/OSS scans, and `git diff --check`.
- [x] Commit/push, archive the pushed commit into a clean temporary directory, rerun acceptance there, and read back PR #3018.
- [x] Mark GA-12 DONE only if the pushed archive passes with no private checkout, credential, personal path, or provider-specific code.

Delivery: remote commit `f108b591d9744f203873cc3a07e594dfac0146fa`; `GA12_PUSHED_ARCHIVE=PASS`.
