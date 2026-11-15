# Issue #96 widget surface gate — resume verification

## Result and remaining work

The interrupted changes are retained and completed as a source candidate on
`codex/widget-gate-fix`; commit only, no push, merge, deployment or ASC changes.
The actual extension deployment target remains iOS 16.6. iOS 17+ gets per-widget
AppIntent category/name/theme/refresh, Premium theme/refresh enforcement, and
idempotent save. iOS 16.6 keeps a static daily widget with the same kind, all four
families, reaction-aware selection and generic lock-screen text. Settings guidance
now states the iOS 17 requirement in all six locales.

Unmodified checker: `~/workspace/tools/widget-check/widget_check.py`.
Each run exits 1 because genuine residual failures remain:

| Source fixture | FAIL | WARN | Breakdown |
| --- | ---: | ---: | --- |
| `widget-source-state-before.json` | 14 | 1 | W-1:1, W-2:4, W-3:1, W-4:1, W-5:1, W-6:1, W-7:5 |
| `widget-source-state-after.json` (iOS 17+) | 2 | 1 | W-3: share absent; W-6: store screenshot absent |
| `widget-source-state-ios16.json` (iOS 16.6) | 6 | 1 | W-2:4 (static configuration), W-3:1, W-6:1 |

All warnings are W-6: store claims have not been checked against a shipped build.
Run each with `python3 ~/workspace/tools/widget-check/widget_check.py <fixture>`.
These JSON files are explicit source audits, not automatic source extraction or
runtime proof. Measurement booleans indicate implemented instrumentation only.
No adoption, retention lift, receipt or shipped-surface claim is made.

W-3 remains open: there is no verified way here to present a native share sheet
inside this widget without opening the app. An app-opening link or inert
ShareLink was not counted as compliant. Apple documents interactive widgets using
[Button and Toggle with App Intents](https://developer.apple.com/documentation/widgetkit/adding-interactivity-to-widgets-and-live-activities).
W-6 requires actual widget screenshots and shipped-build/ASC readback; none was
fabricated. These two gates are not completed by this commit.

## Interrupted-write audit

Inspected the entire git diff and all untracked candidate files. Original tracked
files: AniccaWidget.swift, WidgetShared.swift, project.pbxproj, AppState.swift,
all six Localizable.strings files, AnalyticsManager.swift, LikedQuotesStore.swift,
NudgeWidgetDataStore.swift, FeedRootView.swift, QuoteCardView.swift,
aniccaiosApp.swift and docs/team/BOARD.md. Original untracked files:
WidgetConfiguration.swift, WidgetExperience.swift, WidgetContentStore.swift,
widget-q2-plan.md and widget-source-state-before.json.

No empty, NUL-containing, truncated or syntactically corrupt file was found.
The reduction in WidgetShared.swift is intentional removal of the old duplicated
NudgeWidgetDataStore, now replaced by a Foundation store compiled into both targets.
Swift files parse with tree-sitter-swift; project.pbxproj and all six strings files
parse with openstep-parser. The latter does not support whole-line `//` comments
in strings; removing only those comments for parsing resolves the same initial
parser error in both HEAD and candidate (not file corruption). JSON parses with
Python. Per-file byte counts, hashes and check types are in widget-file-audit.json.
Neither parser performs Swift type checking or Apple SDK availability validation.

## Existing test suite

Command: `python3 -m unittest discover -s apps/mobile/anicca-ios/scripts/tests -v`.
Before resume edits: 44 run, 40 passed, 2 failed, 2 skipped.
After edits: 44 run, 40 passed, 2 failed, 2 skipped.
Both failures match `/tmp/q2-widget-tests.log` from the interrupted run:

- `test_free_onboarding_completes_without_a_network_or_purchase_gate`
- `test_primary_offer_and_alternatives_do_not_have_competing_scroll_regions`

Both belong to `test_paywall_selection_wiring.PaywallSelectionWiringTests`;
those tests and their production targets are unchanged. Skips require Swift.
Final local log: `/tmp/widget-resume-final-tests.log`. `git diff --check` passes.
No native widget/content-store behavior test or iOS build was executable here;
Swift and Xcode are absent. Before shipment, build against the 16.6 target and
exercise iOS 16.6/17+ add/edit/save, app import/unlike, Premium expiry, empty data,
preview non-mutation, account clearing, guide/holdout and analytics reception.

## Procedure and review

Read installed Superpowers 7.0.1 using-superpowers, systematic-debugging,
test-driven-development (and writing-good-tests), verification-before-completion,
and requesting-code-review. Their root is
`/home/hatch/.codex/plugins/cache/openai-curated-remote/superpowers/7.0.1/skills`.
Native RED/GREEN could not be run without Swift/Xcode; no claim of TDD completion.
Astra Advisor is not exposed. Existing App Group, AppIntent and localization paths
were reused without adding application dependencies.

A fresh read-only reviewer inspected the full diff and reported one blocker:
WidgetBundleBuilder does not support `else`. Fixed with explicit returns and `WidgetBundleBuilder.buildBlock` in ordinary
availability branches (Swift opaque-result availability), preserving one widget
kind per OS. An intermediate `#unavailable` builder branch was rejected in review
because it lacks the builder limited-availability marker.
Final focused re-review: 0 findings, 0 blocking; native build still unverified.
See Apple's [buildOptional contract](https://developer.apple.com/documentation/swiftui/widgetbundlebuilder/buildoptional(_:)).

Documentation conflicts: AGENTS.md and source-boundary.sh still require the old
Life Manager origin/path; team WORKFLOW asks for pull/push. The explicit assignment
overrides those rules for this canonical Anicca worktree and says commit without
push. Boundary script was run and returned exit 2 for its stale expected path.
The spec's historical 13 FAIL fixture omits the personalized lock-screen privacy
failure found in this checkout, so the actual before fixture has 14 FAIL.
Current branch and origin were verified; no other checkout/runtime was modified.
