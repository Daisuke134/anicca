# Product Requirements Document: BreathStory

**Date:** 2026-03-04
**Version:** 1.0.0
**Status:** Approved

---

## App Identity

| Field | Value |
|-------|-------|
| **app_name** | BreathStory |
| **bundle_id** | com.anicca.breathstory |
| **display_name** | BreathStory — Guided Breathing Stories |
| **subtitle** | Calm your stress with short audio tales |
| **category** | Health & Fitness |
| **platform** | iOS 15+ |
| **minimum_os** | iOS 15.0 |

---

## Subscription Pricing

| Product ID | Type | Price | Duration | Trial |
|-----------|------|-------|----------|-------|
| `com.anicca.breathstory.monthly` | Auto-Renewable Subscription | **$7.99/month** | 1 month | 7 days |
| `com.anicca.breathstory.annual` | Auto-Renewable Subscription | **$49.99/year** | 1 year | 7 days |

- Subscription Group: `BreathStory Premium`
- Free tier: 3 stories (Forest, Ocean, City Rain)
- Paywall placement: Soft paywall triggered on Story 4 access
- [Maybe Later] MUST always be visible — this is a CRITICAL rule

Source: [RevenueCat State of Subscription Apps 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) — median Health & Fitness price $7.99–$9.99/month

---

## App Store Metadata

### English (en-US)

**Name:** BreathStory — Guided Breathing Stories

**Subtitle:** Calm your stress with short audio tales

**Description:**
```
BreathStory transforms breathing exercises into immersive audio adventures.

Pick a world — a misty forest, a rolling ocean, a rainy city café — and let a narrator guide you through a calming story that naturally synchronizes your breathing.

No more boring "inhale 4, exhale 6" routines. Just press play, close your eyes, and breathe.

WHAT MAKES BREATHSTORY DIFFERENT:
• Narrative-guided breathing: stories naturally pace your inhale/exhale cycles
• 5 immersive worlds: Forest Path, Ocean Drift, Rain in the City, Starfield, Mountain Summit
• Offline playback: works without internet, perfect for planes and commutes
• No external APIs: all audio powered by Apple's built-in technology

FREE FEATURES:
• 3 full breathing stories
• Breathing animation ring
• Session streak tracker

BREATHSTORY PREMIUM:
• Unlimited story library
• All 5 launch stories + new stories added weekly
• 7-day free trial, cancel anytime

```

**Keywords (en-US):** breathing,breathwork,stress relief,calm,anxiety,relaxation,guided,stories,sleep,meditation

**Support URL:** https://anicca.ai/support
**Marketing URL:** https://anicca.ai
**Privacy Policy URL:** https://anicca.ai/privacy

### Japanese (ja)

**Name:** BreathStory — 呼吸ガイドストーリー

**Subtitle:** 短い音声ストーリーでストレス解消

**Keywords (ja):** 呼吸,リラックス,ストレス解消,瞑想,安眠,マインドフルネス,ガイド付き,睡眠,不安解消,呼吸法

---

## Screens

| # | Screen | Description |
|---|--------|-------------|
| 1 | HomeView | Story library grid with lock indicators |
| 2 | PlayerView | Breathing animation + AVSpeechSynthesizer narration |
| 3 | PaywallView | Soft paywall — custom SwiftUI, [Maybe Later] always visible |
| 4 | SettingsView | Restore purchase, streak count |
| 5 | OnboardingView | 3-step intro: problem → solution → CTA |

---

## Technical Constraints

| Constraint | Value |
|-----------|-------|
| Analytics SDK | NONE (Mixpanel prohibited) |
| Paywall SDK | Custom SwiftUI ONLY (RevenueCatUI prohibited) |
| ATT | NONE (AppTrackingTransparency prohibited) |
| Backend | NONE (offline-first MVP) |
| TTS | AVSpeechSynthesizer (built-in, free, offline) |
| Audio | AVPlayer (local .mp3 bundled in app) |
| Storage | UserDefaults only (streak, purchase state) |

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| 1 | app_name = BreathStory, bundle_id = com.anicca.breathstory |
| 2 | Monthly = $7.99, Annual = $49.99, 7-day trial |
| 3 | No Mixpanel, no RevenueCatUI, no ATT |
| 4 | Soft paywall with [Maybe Later] visible |
| 5 | 5 stories at launch (3 free, 2 premium) |
