# Word screenshot sharing (#9414)

When enabled, “Share these words” appears directly below the displayed home words.
A tap freezes the words, theme and date; the system sheet receives a 1080×1920
image with アニッチャ / Anicca, all words (export whitespace reflowed), date and localized promise.
Caption includes https://aniccaai.com, #アニッチャ, #AniccaWords and @anicca.company.
An image-render failure shows a retryable alert, never a blank asset.
Existing legacy sharing remains available while the new feature is disabled.

## Enablement and ship gate

Default OFF: the app Info.plist key `AniccaScreenshotSharingEnabled` is absent.
Debug builds may opt in with `-aniccaScreenshotSharing` for verification.
Do not enable the release key until anicca-ops #520's production model-word
readback, the existing all-screen tap E2E, and Dais's TestFlight experience pass.
This PR does not ship or enable the feature. Muse owns E2E and analytics readback.

## Daily UGC ledger reconciliation

Events use the existing AnalyticsManager/Mixpanel pipeline:

| Event | Meaning |
| --- | --- |
| `screenshot_share_opened` | UIKit share sheet actually appeared (once per attempt) |
| `screenshot_share_completed` | UIKit completion returned completed=true and no error |

Both carry `share_id`, `share_day_jst` (yyyy-MM-dd, Asia/Tokyo, captured at tap),
`quote_id`, `delivery_id`, `source` (home/saved), and `asset_version=word-card-v1`.
AnalyticsManager also adds its event ID and timestamp. No words/answers are sent.
Count distinct share_id grouped by share_day_jst, filter source=home for the
home KPI. Enter opened and completed separately into the existing ugc-ledger.md;
never sum them. Completion uses the attempt day even if the sheet crosses midnight.
Cancellation produces opened only. A second attempt produces a new share_id.
Keep the legacy affirmation_shared event for existing dashboards; do not include it
again in this KPI. Completion is an OS share action (including Save Image), not
proof of a published social post. Missing analytics readback is unknown, not zero.

## Required device verification (not run on Linux)

1. Debug opt-in, authenticated model-generated words: CTA immediately below words.
2. Every theme, Japanese/English, longest 500-character text, newlines, large Dynamic
   Type: save exported image and visually verify all four components, no truncation.
3. Inspect caption in a text-capable destination; verify both tags and mention.
4. Cancel, complete, repeat; verify opened once and completion only on successful
   activity. Read back Mixpanel and reconcile distinct IDs with the daily ledger.
5. Leave sheet open through idle interval, midnight, background/foreground and a
   notification: asset remains frozen; deferred home updates resume after dismissal.
6. Run the existing all-screen E2E and TestFlight owner experience before enablement.

## Local evidence

Python integration regression checks: initially 2 failures, then 2 passes; review
added deferred-refresh and whitespace regressions (failed before fix, passed after fix).
Final focused checks: 4 pass; full script suite: 59 run / 56 pass / 2 skip / 1 pre-existing failure.
Independent review after both fixes: 0 findings.
XCTest content/gate/date/render tests added but not executed: swift/xcodebuild absent.
Existing Python suite has an unrelated stale version assertion in
`test_versions_are_consistent_across_targets` (expects 1.10.1, main is 1.11.0).
Localization parity has existing de/fr/es/pt-BR drift; all three new keys are
present in all six languages. This is a limitation, not a passing iOS build.
