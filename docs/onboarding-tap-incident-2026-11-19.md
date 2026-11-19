# Onboarding tap candidate — port to 1.10.0, 2026-11-19

**LOCAL code prepared; root cause unconfirmed. No iOS reproduction, build, E2E, archive or submission was attempted in this port. Those steps are `needs_gh_actions`.**

Founder symptom: ordinary taps on the sun-icon welcome screen sometimes fail; hard/long presses advance. This is a reported symptom, not an observation in this VM.

## Source and ASC provenance

Assigned canonical origin: `https://github.com/Daisuke134/anicca.git`. Worktree: `/home/hatch/workspace/anicca-wt-tap-fix-1100-port`; branch `codex/tap-fix-1100-port`. Initial clean HEAD and origin/main both `dddaeb10b131d79e1e38abba35f5b3a9a9844b35`; shared Git store `/home/hatch/workspace/life-manager/.git`. Applied `git cherry-pick --no-commit 0f0f0779d` and resolved against this base. No push or merge.

Canonical source check passed before editing: WelcomeStepView has `sun.max` and calls PrimaryButton; PrimaryButton pads/sizes its HStack label, has no contentShape, draws background outside Button, and uses PressScaleButtonStyle. That style scales `configuration.label` and does not install a long-press recognizer. Missing explicit label geometry is a candidate mechanism; it does not prove pressure sensitivity or the root cause.

Base settings are **1.10.0 / 831**, whereas the live ASC version is **1.10.0 / 834, READY_FOR_SALE**. The exact archive-to-source mapping remains unverified. ASC returned all **202** builds with pagination exhausted; highest existing is **835**, VALID, ID `4d62115c-0d2a-4953-bf56-946b4e614f1e`. Therefore all 12 marketing/build settings become **1.10.1 / 836**. 832 is void; 836 is not reserved and must be rechecked before archive. [Sanitized official readback](evidence/onboarding-tap-2026-11-19/asc-build-number.json).

## What was ported and adapted

- Kept the shared PrimaryButton label shape after sizing, preserving flexible minHeight, loading/disabled logic, design and haptics. All current primary onboarding CTAs inherit it, including Welcome and Notifications; no old bespoke CTA was restored.
- Kept AppBackground input/accessibility exclusion on the current LinearGradient, preserving dark/light colors and opacity.
- Applied the same shape to current goal, adaptive question, pain, frequency, reminder, icon and theme rows; first-affirmation save, secondary skip/later actions, and paywall purchase/plan/retry/restore labels. Existing 44pt paywall-close label shape is the sibling pattern. No timing/retry/gesture workaround or dependency was introduced.
- Dropped obsolete ProcessingStepView and PersonalizedInsightStepView changes: these files are deleted in 1.10.0. Did not restore old GoalStepView, PreferredNudgeTimesView or ComparisonTableStepView. Retained the current routing and profile logic unchanged.
- Ported Xcode target registration, result verifier, ship-gate script, Fastlane/release-script hooks and CI workflow. Rewrote the three full-flow coordinate tests for the adaptive route, covering all five deep-dive modules across three cases plus prior-helpfulness present/absent. Updated supplementary Maestro flow to current IDs. Lowercase `-uiTesting` suppresses the rating prompt and supplies the existing stable test device ID; it does not skip RevenueCat. Uppercase `UITESTING` is excluded because it disables RevenueCat. This test-mode difference must be considered in physical-device reproduction.
- Retained seven localized release-note drafts. They are not proof of a fixed incident and must not ship before the native gate passes.
- Corrected a pre-existing Python test that expected combined build/unit log upload, although the existing workflow has separate jobs. Now it checks each job's producer, failure condition and log artifact; production CI behavior is unchanged. The standalone analytics contract also expected a direct event token in the flow, while current code delegates to trackOnboardingStepCompleted; its check now follows the existing helper and verifies event emission there. No production analytics behavior changed.

## Verification and limits

[Structural RED](evidence/onboarding-tap-2026-11-19/structural-red.txt) demonstrates absent shape/background exclusion, target registration and release settings before the port, plus the stale nine-step test. It is not native symptom reproduction. [Final Python results](evidence/onboarding-tap-2026-11-19/python-tests.txt) cover the existing script test suite and the result verifier. Shell/Python checks and review are recorded in the ops report.

The inherited Python suite uses isolated tool doubles to test log and recording failures. These are not actual xcodebuild, Swift, Maestro or simulator runs. Swift-dependent tests are skipped on this VM. Native touch behavior and Swift compilation remain unverified.

## Procedure and documentation mismatches

Read `/home/hatch/.agents/skills/{using-superpowers,systematic-debugging,test-driven-development,ios-design,requesting-code-review,verification-before-completion,finishing-a-development-branch}/SKILL.md`, test-driven-development/writing-good-tests.md, REVIEW.md and team docs. `canonical_source_check` skill was not found in installed skill locations; performed the delegation's explicit source checks directly. Astra Advisor is unavailable. Reused existing native components and test infrastructure.

`bash scripts/verify-source-boundary.sh` exits 2 because `/home/hatch/Projects/life-manager-main` is absent and local instructions name life-manager. User's assignment override authorizes this anicca checkout/current branch; no guard was weakened. The old incident/gate docs described 1.9.6, nine steps and build832; this report replaces those claims for this port. Team docs prescribe a hard paywall and push; current code has a soft paywall, and this assignment prohibits push. OnboardingBibleViews describes a routed rating pre-prompt, but current OnboardingFlowView instead requests StoreKit review after planReveal; the obsolete view is not restored.

[Remaining native sequence and release gate](e2e-ship-gate-2026-11-19.md). The branch/worktree is retained for the integration owner. Code completion is not incident resolution.
