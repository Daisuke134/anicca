# Anicca soft paywall Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline for this delegated goal.

**Goal:** Real free affirmation experience, optional paid themes, recorded Maestro journey and official App Store submission.
**Architecture:** Reuse ContentRouter/Feed, ThemePicker, PaywallFlowContainer and RevenueCat entitlement; remove onboarding purchase barrier without new services.
**Tech Stack:** SwiftUI, XCTest, Maestro, existing GitHub macos-15 and Xcode Cloud, asc CLI.
**Spec:** anicca-ops files/anicca-soft-paywall-spec-2026-11-13.md v1.0.

## Global Constraints
- Version 1.9.14 reserved in Muse claim; 1.9.13 lane preserved.
- No price or RC exp529116692b mutation; no paid tool/new API payment.
- No mock offerings or static video substitutes as E2E evidence.
- User explicitly delegated specification decisions and uninterrupted execution. Use designated isolated Linux checkout; source-boundary FAIL (old fixed Mac path) recorded, guard unchanged.

## Review Focus
- Offline and resumed question-complete onboarding must reach free feed.
- Old hard offering must never hide close, including missing products.
- Dismiss must preserve old theme; purchase/restore must apply pending theme only after entitlement.
- Existing saved theme must survive migration/relaunch.
- E2E must use real configuration; missing secrets or runner capacity is blocked, never success.

### Task 1: Free entry and optional premium themes
**Files:** Onboarding/OnboardingFlowView.swift, PaywallPackageSelection.swift, OnboardingBibleViews.swift, Views/Feed/ThemeStore.swift, SettingsSheet.swift, PaywallVariantBView.swift, Resources/{en,ja,fr,de,pt-BR,es}.lproj/Localizable.strings; related native and wiring tests.
- [ ] Add tests for unconditional soft resolution/close, free theme policy, offline entry; run failure before implementation.
- [ ] Complete onboarding directly after questions and on resume; no entitlement request gating. Keep offering/package purchase policy.
- [ ] Use theme-picker pending selection + existing PaywallFlowContainer. Only sageMist/sandWave free, grandfather saved selection; dismiss does not select; entitled success selects.
- [ ] Show localized Free vs Premium benefits. Run focused Python wiring checks and CI Swift build/unit tests.

### Task 2: Real E2E recording
**Files:** maestro/v1.9.14/01-soft-paywall.yaml, existing iOS CI if necessary, scoped evidence directory.
- [ ] Reuse existing onboarding selectors, then feed swipe/save/themes/locked-theme/paywall/close/free-theme/relaunch.
- [ ] Run on actual simulator build with real RC configuration, capture recording and result. Commit real artifacts only after inspection.
- [ ] Inspect recording and verify commit/device/time/result metadata. Missing runner/RC is blocked with exact failure.

### Task 3: Release and official readback
**Files:** project version configuration, docs/team/BOARD.md; ops specification/progress/submission record.
- [ ] Fresh independent review per REVIEW.md, fix blocking findings, CI/checks; named PR and merge-when-green only.
- [ ] With tests/video green, reserve unused build, sign/upload via existing Xcode Cloud/fastlane route. Do not cancel unrelated in-flight review without coordination.
- [ ] Submit 1.9.14 and read official ID/state; update ops progress and fetch/read origin. Preserve PR worktree while open.
