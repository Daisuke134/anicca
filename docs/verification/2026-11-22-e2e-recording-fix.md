# E2E recording code handoff

Branch: codex/e2e-recording-fix-20261122. No push or Actions dispatch.

The assigned checkout contains neither OnboardingWinnerE2ETests.swift nor its
reported line 98. The historical run failure cannot be reproduced on this Linux
host (no Swift/Xcode). This patch addresses a concrete stale-layout defect, not
an assertion that the reported run now passes.

FeedRootView passes measured geometry into VerticalPager pages. A hosting
controller retains that value, while synchronizeVisiblePage previously returned
without updating it whenever the index was unchanged. Initial zero geometry can
therefore persist into the visible home. Refresh the existing host's rootView on
same-index updates, retaining the host and existing interactive-swipe guards.
QuoteNavigationCoordinatorTests now checks zero-to-visible geometry at index 0.
Run that regression and the existing swipe/navigation tests in Xcode.

Recording handoff to Muse:
- The workflow skips maestro for PR/push and workflow_dispatch without
  run_maestro=true; default is false. A normal build is not recording evidence.
- The existing Maestro runner builds then launches through simctl/Maestro.
  Merely building a scheme does not activate its StoreKit launch configuration.
- For the required sign-in-free recording use xcodebuild test with scheme
  aniccaios and its Anicca.xctestplan (already references Anicca.storekit),
  selecting the onboarding/living-home UI test in the recording branch.
  Do not use the current raw Maestro launch as proof of StoreKit configuration.
- Verify actual nonempty quote-text, a subsequent different quote-text while
  idle, and the resulting video. Preserve xcresult and video even on failure.
- Port/restore the missing OnboardingWinnerE2ETests from the run's source before
  selecting it; it is not present in this assigned tree.

Skills read: using-superpowers, systematic-debugging, test-driven-development,
verification-before-completion under /home/hatch/.agents/skills. Swift regression
execution is deferred to Muse's macOS Actions run, as requested.

Local validation: git diff --check passed. Python unittest discovery under
apps/mobile/anicca-ios/scripts/tests ran 44 tests: 40 passed, 2 skipped, 2 failed
in test_paywall_selection_wiring against untouched onboarding/paywall source.
This is not a green full suite. No Swift tests or E2E were run locally.
