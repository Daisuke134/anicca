# Q2 widget code implementation plan

Spec: `~/workspace/goals/anicca-revenue-growth-as-life-manager/hidden_files/widget-surface-gate-spec-2026-11-14.md` (read in full).

Scope: supplied `codex/widget-gate-fix`, base `claude/living-home-paywall-2026-11-15`; commit only. No ops files, paid APIs, production or ASC mutations.

- [x] Read checker and all fixtures. Reproduce reference FAIL 13/warn 1. Audit checkout: additional privacy failure (14/1).
- [x] Replace static configuration with AppIntent category/name/theme/refresh; add large. Reuse extension's existing AppIntent pattern and App Group.
- [x] Share one Foundation content store between app and extension. Select from current struggles using likes and recent presentation history, not calendar modulo. Default lock screen to generic words. Preserve fallback.
- [x] Add idempotent save intent on medium/large and import into existing LikedQuotesStore. Do not substitute app-opening share for W-3; leave sharing unverified pending supported native interaction/device proof.
- [x] Show localized guide after a feed save; persist random holdout before exposure. Query installed configurations on feed activation; record both installed and non-installed observations, failures as unknown, and widget taps via dedicated URL.
- [x] Build source-state JSON with file evidence, run the supplied checker unchanged, record exact residuals and Xcode/device/ASC requirements, review diff and commit.

Review focus: no-data/removed categories, duplicate saves, premium expiry, logout cleanup, preview rendering must not mutate reaction/presentation state. Checker is a source-state gate, never a build or runtime proof. Swift/Xcode unavailable here; do not claim native tests passed.

Procedure evidence: installed Superpowers 7.0.1 using-superpowers, systematic-debugging, test-driven-development, writing-plans, executing-plans, verification-before-completion read. Astra Advisor not exposed. User already specified worktree/base/execution/deliverable, so continue authorized work without a plan approval pause. No widget implementation sibling in loop registry (only distribution lanes): no precedent there; reuse iOS AppIntent and shared-store code instead. Boundary script failed on old canonical path; explicit user checkout instruction and spec rename supersede it. README absent from checker directory. Config readback: gpt-6-astra, medium, priority; no config changes or paid API calls.

Resume verification and exact residuals: [widget-verification.md](widget-verification.md). Checked items mean the source implementation/audit work is done, not W-3 share or W-6 store publication. iOS 16.6 retains a static compatibility path.
