# Welcome gate failure: test-side AX waiter interruption

## Evidence and root cause

Run `44509771791`, source `816090ac5bd3f7b4243751257e2f477e9707bb4c`, Release, Xcode 16.4 (16F6), iOS 26.2. Input: `~/workspace/tmp_cache/gate44509/dl/20261119T105453Z-3225/testFullOnboardingCenterTaps.{log,xcresult}`.

The text build log alone does **not** show an untappable button. Its 30-second wait is for existence; the subsequent compound predicate has a **10-second** deadline. The xcresult's Zstandard data attachments were decoded locally using the existing `tmp_cache/codex-tmp/extract-tap-evidence.py` approach (libzstd). The runner diagnostic attachment `data.0~x35CI4-CyCcWakeG6fuRRO8ZGyREUi5VhS0KUQQH3wlh2KwnKohaEKqe22MlmFNL3FPcuWn-Ddrr_v15D6ofqw==` supplies decisive evidence:

- 11:12:52.596: outer waiter starts, timeout 10s.
- 11:12:53.626–57.175: first element lookup.
- 11:12:59.535: **`Computed hit point {220.0, 878.0} (hittable)`**, inside `{{24, 850}, {392, 56}}`.
- Further value/placeholder AX requests and another lookup follow.
- 11:13:02.849–02.850: outer watchdog interrupts that lookup, returning **`Interrupted by waiter`**.
- 11:13:02.856: outer expectation reports timed out.

Selected original lines: [runner-excerpt.txt](evidence/tap-gate-welcome-2026-11-19/runner-excerpt.txt). The failure's element debug attachment contains only the query chain, not `enabled=false` or an obstructing view. The screen recording payload `data.0~PF1LKqNUrrlIbeNc7vG-GY2CbR9MkLP7WUsinxdDkiqGwSqd3zNbZad5LlZhjWN4K4ehAMhFhziicNQl3XWMqQ==` was inspected at 25s: welcome and Get Started are visibly present; no modal is visible. More decisively, the native hit-point result above is positive. No tap was sent before failure.

Thus this failure is the **test's outer deadline interrupting a compound remote AX evaluation**, not evidence of an app overlay or a disabled welcome button. The source also supplies no welcome loading/disabled condition (PrimaryButton defaults enabled). This does not establish that the founder's shipped-build hard-press report is resolved.

## Change and retained requirements

`OnboardingTapE2ETests.tap` now uses a block predicate capturing the element, with `object: nil`, so the expectation does not describe an XCUIElement as its polling subject. Typed checks explicitly require existence, enabled and hittable. Its budget is 30s, matching the existing existence budget and allowing the observed cold-simulator AX work to finish. This is a bounded readiness wait, never a tap retry.

Timeout explicitly returns without tapping, saves a screen attachment and reports the element description after polling. Exactly one normal `coordinate(...).tap()` remains. The welcome step explicitly asserts arrival at goal selection, in all three existing center/leading/trailing cases. No accessibility-action tap, app routing bypass, entitlement bypass, app change or workflow change.

## Verification and limitations

- Existing native RED: run 44509771791. It is the regression scenario; the same three complete-journey cases remain.
- Before change: Python structural suite 54 tests, 52 pass / 2 skip.
- After change: [Python output](evidence/tap-gate-welcome-2026-11-19/python-tests.txt), 54 tests, **52 pass / 2 skip**. An intermediate structural failure detected the forbidden substring `while ` in a new comment; the comment was reworded, with no weakening of the checker.
- `git diff --check`: pass.
- `bash apps/mobile/anicca-ios/scripts/onboarding-ship-gate.sh`: exit 69, macOS/Xcode/Simulator unavailable. Native compilation and post-fix E2E GREEN are **not verified**. Required next evidence: run all three cases on macOS against this commit, including paywall → feed → relaunch. No push/dispatch/ASC operation was performed.
- Self-review under REVIEW.md: 0 findings; checks retained, one tap, no app effects. Test-only risk tier. No independent reviewer or native execution claimed.

## Procedure and boundaries

Read `/home/hatch/.agents/skills/{using-superpowers,systematic-debugging,test-driven-development,verification-before-completion,finishing-a-development-branch}/SKILL.md`, `test-driven-development/writing-good-tests.md`, `using-superpowers/references/codex-tools.md`, REVIEW.md and docs/team README/RULES/OWNERSHIP/WORKFLOW/BOARD. Astra Advisor is not exposed; used the applicable Superpowers procedure and existing helpers, with no dependency added.

Worktree is `/home/hatch/workspace/anicca-wt-tap-fix-1100-port`, branch `codex/tap-fix-1100-port`, common Git directory `/home/hatch/workspace/life-manager/.git`, origin `https://github.com/Daisuke134/anicca.git`. Source guard returned exit 2 because its old canonical root `/home/hatch/Projects/life-manager-main` is absent. The explicit assignment overrides Life Manager origin/checkout and push rules; guard unchanged. Team docs' hard-paywall wording also disagrees with the implemented optional-purchase/free-feed flow; existing app behavior preserved. Commit locally and preserve this worktree; no merge or push.
