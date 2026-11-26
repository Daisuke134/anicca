# Living Home screenshot sharing implementation plan

Goal: implement #9414 using the existing QuoteCardView, ImageRenderer and ShareSheet.
Spec: https://github.com/Daisuke134/anicca/issues/9414 (including comments).
Architecture: snapshot the visible words/theme/date at tap, render an outbound branded card,
and correlate presentation/completion through one share ID. Keep legacy sharing while rollout is off.
Tech stack: SwiftUI/UIKit, existing Mixpanel, XCTest and Python wiring checks.

- [x] Add tests for branded content, rollout default, daily correlation and image rendering.
- [x] Add the localized immediate CTA, immutable share payload, renderer and sheet callbacks.
- [x] Pause home auto-advance during sharing; preserve existing completion learning.
- [ ] Run available checks, independent review, commit/push and PR against main.

Review focus: 500-character/newline words, midnight, cancel/error, repeat shares,
and home auto-advance/background refresh during an active sheet.

Release gate: anicca-ops #520 is OPEN. AniccaScreenshotSharingEnabled defaults false.
Enable only after #520 authoritative readback, all-screen tap E2E, analytics readback,
and Dais's TestFlight experience. No release or rollout is performed here.

Environment: Linux, no swift or xcodebuild. Native XCTest/E2E cannot run here.
Source-boundary script requires an unavailable old Life Manager path; assignment overrides it.
Initial clean branch was an unrelated snapshot e2994a582: preserved as
archive/9414-original-e2994a582, then based assigned branch on origin/main 21603ce3e.
Astra Advisor is unavailable in this harness; use Superpowers native execution and review.
Skills read: using-superpowers, brainstorming (questions explicitly opted out), writing-plans,
test-driven-development, executing-plans, verification-before-completion.

Verification: 4 Python wiring regressions pass (each introduced with failing check).
Full iOS Python script suite: 59 run, 56 passed, 2 skipped (Swift unavailable),
1 pre-existing stale marketing-version assertion failed. Six locale key deltas
verified to contain exactly the 3 added keys. git diff --check passes.
xcodebuild -showdestinations: command not found. Native tests remain unverified.
Independent read-only review: 2 blocking findings (deferred refresh, excessive
newlines), both fixed; follow-up review 0 findings. No production effects.
Ruling: preserve existing unrelated failed checks and report them in the PR;
user explicitly requested commit/push/PR, not repair unrelated release assertions.
Finishing skill read; selected action is the user's explicit push + PR instruction.
