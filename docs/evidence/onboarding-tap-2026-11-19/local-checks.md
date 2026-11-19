# Local verification — 2026-11-19

- `python3 -m unittest discover -s apps/mobile/anicca-ios/scripts/tests -v`: 54 discovered, 52 passed, 2 skipped, zero failures/errors. Output: python-tests.txt.
- Skips: `PaywallNativeBuildTests.test_production_paywall_helper_compiles_and_passes_existing_truth_table` (Swift compiler absent), `SettingsSignOutTests.test_tap_waits_for_confirmation_cancel_is_inert_and_confirm_signs_out` (Swift runtime absent).
- `python3 apps/mobile/anicca-ios/scripts/tests/test_analytics_provider_contract.py`: PASS, output analytics-contract.txt. This standalone script is not executed by unittest discovery.
- `bash -n apps/mobile/anicca-ios/scripts/onboarding-ship-gate.sh apps/mobile/anicca-ios/scripts/release-ios.sh`: PASS (syntax only; gate was not invoked).
- PyYAML parsing of new workflow and adapted Maestro multi-document YAML: PASS.
- ElementTree scheme XML and json.loads UI-only xctestplan: PASS. All 12 MARKETING_VERSION settings are 1.10.1; all 12 CURRENT_PROJECT_VERSION settings are 836.
- `git diff --check` / staged diff check: PASS after final staging. No conflict markers/unmerged files.
- Ruby/Fastlane syntax execution unavailable: ruby is not installed.
- No native Swift/Xcode, app build, E2E, simulator, archive, upload, submission or workflow dispatch attempted. Shell test doubles in the Python suite are synthetic failure-contract tests, not native evidence.

## Independent read-only review

Reviewer: harness child `/root/review_port`, inherited model; no CLI model/effort override or invented model readback. Reviewed actual diffs against dddaeb10b with REVIEW.md; no file mutations.

Round 1: 2 findings, 1 blocking. Release gate inherited the unit-test plan with @testable unit targets despite Release testability disabled; fixed by the UI-only OnboardingTap plan, scheme registration and explicit -testPlan selection. StoreKit evidence description overstated real-product coverage; fixed to disclose local StoreKit fixture plus live SDK configuration. No native failure was claimed as observed.

Round 2: 0 new blocking findings; both original findings verified resolved, two stale Python contracts checked.

Round 3: 0 new blocking findings on the final retry/restore label-shape delta; actions and disabled state unchanged. The existing paywall Python test's text parser was then aligned to the loadingContent/legalLinks boundaries because explicit Button labels replaced the old initializer strings; it retains the eligibility refresh/load-event assertions. Final full Python suite passed after this adaptation.

## Baseline inconsistencies found by tests

- BuildDiagnosticsTests expected one combined build/unit log upload, although the baseline workflow runs two jobs. Fixed test checks each job's failure upload after its producer, retaining the proper log.
- Analytics standalone contract expected a direct lowercase event name in the flow; current flow calls trackOnboardingStepCompleted. Test now checks that call and event emission inside the existing helper.

These changes correct tests against existing code; production CI and analytics were not altered.
