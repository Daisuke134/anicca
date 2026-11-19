# 1.10.0 tap-fix port execution plan

Authority: Muse delegation 2026-11-19, LOCAL code only. Base dddaeb10b, current branch codex/tap-fix-1100-port. Do not push, merge, build, run native E2E or archive.

1. Verify source provenance and actual sun-icon/PrimaryButton implementation. Read original incident and compare adaptive route before porting.
2. Cherry-pick 0f0f0779d without committing; retain current 1.10.0 implementations, adapt hit regions and tests, drop removed screens. Observe Python structural RED then GREEN; no native RED/GREEN claims.
3. Fetch every ASC build and current public-version relation; pick next build above maximum, update version1.10.1 consistently, preserve sanitized receipt.
4. Run Python suite and focused shell/config validation, independent read-only review, resolve findings. Native verification remains needs_gh_actions.
5. Commit current branch, retain worktree; write anicca-ops report through gh api PUT and verify exact readback bytes. Report pending provenance/reproduce → E2E → archive → submit.
