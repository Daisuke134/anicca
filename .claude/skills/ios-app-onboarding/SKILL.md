---
name: ios-app-onboarding
description: "Activate this skill when designing, auditing, iterating, or reviewing iOS app onboarding flows and paywalls for maximum conversion. Covers the Vara Framework, Cravotta 3-Step Paywall, RevenueCat 2025 benchmarks (75,000 apps, $10B+), Superwall 4,500 A/B tests, Hook Model, Drawer strategy, and Apple 2026 compliance. Outputs EN and JA localized text. Applicable to all iOS apps."
---

# iOS App Onboarding & Paywall Optimization

## Purpose

Provide battle-tested best practices for iOS app onboarding and paywall design that maximize
trial starts, subscription conversion, and Day-1 retention. Based on:
- **RevenueCat 2025** — 75,000 apps, $10B+ revenue benchmarked
- **Superwall** — 1億 paywall views, 4,500 A/B tests
- **PaywallScreens.com** — 10,229+ real-world paywalls analyzed
- **Top apps** — Headspace (87 steps), Duolingo (77 steps), Clear 30 ($10K→$30K/mo in 8 weeks)
- **Steven Cravotta** — $40K MRR, 3-step paywall (CVR 2x)
- **Nir Eyal** — Hook Model (habit-forming products)

## When to Use

- Designing a new onboarding flow for any iOS app
- Auditing an existing onboarding for conversion improvements
- Iterating on paywall design, copy, or pricing layout
- Reviewing onboarding before App Store submission
- Creating factory apps that need profitable onboarding patterns

---

## Core Principles

| # | Principle | Data | Source |
|---|-----------|------|--------|
| 1 | **85% of users decide to pay in the first 5 minutes** | 85% | Superwall / Clear 30 |
| 2 | **80-90% of trials happen on Day 0** | Must show paywall during onboarding | RevenueCat 2025 |
| 3 | **Increasing paywall views from 40%→80% = linear revenue increase** | Before CVR optimization | Superwall Bootcamp |
| 4 | **Top 5% vs Bottom 25% = 400x revenue gap** | $8,888 vs $19 first-year | RevenueCat 2025 |
| 5 | **Trust is the highest-leverage variable** | - | Steven Cravotta |
| 6 | **Sell the outcome, not the product** | +50% CVR (program preview vs feature list) | Superwall / Clear 30 |
| 7 | **Transparency about pricing = +3% CV** | Tell users the app costs money during onboarding | Clear 30 |

### Value Equation (Superwall / Clear 30)

```
Dream Outcome × Likelihood of Achievement
─────────────────────────────────────────
    Time Delay + Effort + Sacrifice
```

Onboarding's job = Maximize Dream Outcome & Likelihood, minimize perceived Time/Effort/Sacrifice.

---

## Core Framework: The Three Pillars (Vara Framework)

| # | Pillar | Purpose | Implementation |
|---|--------|---------|----------------|
| 1 | **Personalize immediately** | Create investment/ownership feeling | Add 2-3 question slides early in the flow |
| 2 | **Slow them down on purpose** | Build perceived value layer by layer | Progress bar + value proposition slides between questions |
| 3 | **Max perceived value before paywall** | Achieve "I need this" conviction | Show personalized result summary right before paywall |

---

## Conversion Benchmarks (RevenueCat 2025, 75,000 apps)

### Download → Trial

| Category | Q1 (25th) | Median | Q3 (75th) | P90 (Top 10%) |
|----------|----------|--------|-----------|---------------|
| All | 2.6% | 6.2% | 12.4% | 20.3% |
| Health & Fitness | 3.5% | 7.8% | 14.2% | 24.1% |
| Business | 3.9% | 8.9% | 14.9% | 18.0% |

### Trial → Paid

| Trial Length | Median Conversion |
|-------------|-------------------|
| 17-32 days (long) | **45.7%** |
| 5-9 days (standard) | **26.8%** |
| Best apps | **60%+** |

### Hard vs Soft Paywall

| Metric | Hard Paywall | Freemium (Soft) |
|--------|-------------|-----------------|
| D35 Download→Paid | **12.11%** | 2.18% |
| Best for | Value clear upfront | Gradual engagement |

### Revenue Per Install

| Category | D60 Revenue/Install |
|----------|-------------------|
| Health & Fitness | $0.63 |
| AI Apps | $0.63+ |
| All (median) | $0.31 |

---

## Workflow

### Step 1: Audit Current Onboarding

| Check | Best Practice | Weight |
|-------|--------------|--------|
| Personalization questions exist | 2-3 questions before paywall | CRITICAL |
| Progress indicator | Bar on all slides (20% start = Endowed Progress) | HIGH |
| Value proposition slides | Social proof / stats between questions | HIGH |
| "Building your plan" moment | Loading animation before paywall | MEDIUM |
| Skip button exists | Apple guideline compliance | CRITICAL |
| Animations | Fade/slide transitions between slides | MEDIUM |
| Benefit-oriented copy | "What you get" not "What this does" | HIGH |
| Goal setting step | Commitment & consistency principle | HIGH |
| Personalized insight/result | Before paywall, based on answers | CRITICAL |
| Transparency about cost | Mention app is paid during onboarding | MEDIUM |

### Step 2: Audit Current Paywall

| Check | Best Practice | Weight |
|-------|--------------|--------|
| **Multi-step paywall (3 steps)** | Risk-Free Primer → Transparency Promise → Hard Close | CRITICAL |
| Step 1 shows NO price | "Try for free" only, lower heart rate | CRITICAL |
| Step 2 shows trial timeline + Day 5 reminder | Remove cancel anxiety (Blinkist: +23% CVR, -55% complaints) | CRITICAL |
| Trial reminder notification scheduled | Local push on Day 5 of trial | HIGH |
| Personalized headline (Step 3) | Based on onboarding answers | CRITICAL |
| Social proof above CTA | "⭐ 4.9 · X+ users" directly above button | HIGH |
| "No commitment. Cancel anytime." | Below CTA, every paywall | CRITICAL |
| Yearly plan has "BEST VALUE" badge | + "Save X%" + weekly breakdown | HIGH |
| CTA says "Continue" or "Start Free Trial" | NOT "Subscribe" or "Buy" | HIGH |
| Annual plan pre-selected | Anchor to annual plan | HIGH |
| Weekly price breakdown | $49.99/yr → "$0.96/week" | HIGH |
| Legal footer | Terms + Privacy + Cancel anytime | CRITICAL |
| Restore Purchases button | Apple requirement | CRITICAL |
| **NO Toggle Paywall** | Apple rejects since Jan 2026 (Guideline 3.1.2) | CRITICAL |
| Drawer offer (not Exit Offer modal) | On × press: slide-up with weekly reframe | MEDIUM |

### Step 3: Generate Improvement Recommendations

For each CRITICAL or HIGH item that fails audit, generate:

1. **What to change** — Exact element (component, text, style)
2. **Why** — Which best practice it violates and expected impact
3. **How** — Code-level or design-level patch (EN + JA text included)
4. **Expected impact** — Estimated CVR improvement range

### Step 4: Output Localized Text

All text recommendations MUST include both EN and JA versions:

| Key | EN | JA |
|-----|----|----|
| (i18n key) | English text | 日本語テキスト |

### Step 5: Apple Guidelines Compliance Check (2026)

| Rule | Check |
|------|-------|
| Paywall MUST be dismissible (skip/close button) | ⬜ |
| Actual prices displayed (from StoreKit/RevenueCat) | ⬜ |
| Free trial duration + auto-renewal clearly stated | ⬜ |
| Privacy Policy link on paywall | ⬜ |
| Terms of Use link on paywall | ⬜ |
| Restore Purchases button present and functional | ⬜ |
| `demoAccountRequired` set to `false` | ⬜ |
| **NO Toggle Paywall** (Guideline 3.1.2 — rejected since Jan 2026) | ⬜ |
| **NO aggressive Exit Offer modals** (Guideline 5.6 risk) | ⬜ |

---

## Recommended Onboarding Flow Template (8-12 slides)

```
PHASE 1: HOOK (Trust)
┌──────────┐   ┌──────────┐   ┌──────────┐
│ Welcome  │ → │ Struggles│ → │ Depth    │
│ Dream +  │   │ "What's  │   │ "How     │
│ Social   │   │ holding  │   │ often?"  │
│ Proof    │   │ you back"│   │ 1-tap    │
└──────────┘   └──────────┘   └──────────┘

PHASE 2: INVEST (Commitment)
┌──────────┐   ┌──────────┐
│ Goals    │ → │ Personal │
│ "Best    │   │ Insight  │
│ self?"   │   │ Stats +  │
│ Chips    │   │ Path     │
└──────────┘   └──────────┘

PHASE 3: VALUE DEMO
┌──────────┐   ┌──────────┐
│ Program  │ → │ Live     │
│ Preview  │   │ Demo     │
│ 7-day    │   │ Try the  │
│ journey  │   │ product  │
└──────────┘   └──────────┘

PHASE 4: PERMISSION
┌──────────┐
│ Notif    │
│ Permission│
│ Value-   │
│ framed   │
└──────────┘

PHASE 5: CONVERT (3-Step Paywall)
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│ Risk-Free│ → │ Trial    │ → │ Plan     │ ← │ Drawer   │
│ Primer   │   │ Timeline │   │ Selection│   │ Offer    │
│ No price │   │ Blinkist │   │ + CTA    │   │ (on ×)   │
└──────────┘   └──────────┘   └──────────┘   └──────────┘
```

Each slide MUST have:
- Progress indicator (bar, 20% start, hidden on paywall)
- Single clear CTA button
- Smooth animation transition (slide, 500ms ease-in-out)
- Haptic feedback on button tap

---

## Multi-Step Paywall (Cravotta Method — CVR 2x)

Source: Steven Cravotta (@StevenCravotta, Puff Count $40K MRR)
Core insight: "If your paywall is a single screen with a Buy button, you're losing 40% of potential revenue."
Result: Trial conversion rate doubles compared to single-screen paywall.

### 3-Step Trust Bridge

| Step | Screen | Purpose | Key Rule |
|------|--------|---------|----------|
| Step 1 | **Risk-Free Primer** | Lower heart rate | NO price shown. "Try for free" only. No × button |
| Step 2 | **Transparency Promise** | Remove cancel anxiety | Blinkist timeline: Today→Day 5→Day 7. +23% CVR, -55% complaints |
| Step 3 | **The Hard Close** | Convert in felt-safety state | Personalized headline + plans + social proof above CTA |

### Step 3: The Hard Close (Full Paywall)
```
┌────────────────────────────┐
│                       [X]  │
│       🎯 App Icon          │
│  "{Personalized Headline}" │
│                            │
│  ┌─FREE──┬──PREMIUM───┐   │  ← Comparison table
│  │ basic │ full access │   │
│  │ limit │ unlimited   │   │
│  │  ❌   │     ✅      │   │
│  └───────┴────────────┘   │
│                            │
│  [ Monthly    $X.XX/mo ]   │
│  [ Yearly ⭐ BEST VALUE ]  │  ← Pre-selected, Save%, weekly breakdown
│     "$0.XX/week"           │
│                            │
│  ⭐ 4.9 · X,000+ users    │  ← Social proof above CTA
│  [=== Start Free Trial ===]│  ← Primary CTA
│  No commitment. Cancel     │
│  anytime.                  │
│      "Maybe later"         │  ← Subtle
│    "Restore Purchases"     │
│  Terms • Privacy           │
└────────────────────────────┘
```

### Drawer Offer (on × press — NOT Exit Offer modal)

> **WARNING:** Exit Offer modals have iOS rejection risk (Apple Guideline 5.6). Use Drawer (slide-up) instead.

```
┌────────────────────────────┐
│  "Not ready for a year?"   │
│  "That's just $0.XX/week   │
│   — less than a coffee"    │
│                            │
│  [Start Free Trial]        │
│  "Maybe later"             │
└────────────────────────────┘
```

---

## Banned Patterns (Apple 2026)

| Pattern | Status | Guideline |
|---------|--------|-----------|
| **Toggle Paywall** | **BANNED on iOS** (Jan 2026) | 3.1.2 — "confusing, may prevent users from understanding" |
| **Exit Offer modals** | **RISKY on iOS** | 5.6 — rejection cases reported (RevenueCat 2026/03) |
| **× button delay > 5s** | **RISKY** | App Review flags this |
| **Hiding prices** | **BANNED** | 3.1.1 |
| **"Free" without trial context** | **BANNED** | Misleading |

> Toggle Paywall is still OK on **Google Play / Web**. Platform-specific paywall recommended.

---

## Hook Model (Nir Eyal — Habit Formation)

| Step | Content | App Implementation |
|------|---------|-------------------|
| 1. **Trigger** | External: notifications. Internal: emotions | Push notifications = External → Habit = Internal |
| 2. **Action** | Minimum effort to perform | 1-tap response to nudge |
| 3. **Variable Reward** | Unpredictable rewards → dopamine | Different nudge content each time |
| 4. **Investment** | User puts in time/data → generates next trigger | Profile, reflections, preference learning |

---

## Conversion Optimization Techniques

| Technique | How | Expected Impact | Source |
|-----------|-----|-----------------|--------|
| **Anchoring** | Show yearly first, monthly appears expensive | CVR +15-30% | Superwall |
| **Loss aversion** | "Free users miss 80% of content" | CVR +10-20% | Superwall |
| **Social proof above CTA** | "⭐ 4.9 · X,000+ users" directly above button | CVR +5-15% | Superwall |
| **Endowment/Sunk cost** | Questions → "your personalized plan" | CVR +20-40% | Superwall |
| **Free trial framing** | "Start Free Trial" vs "Subscribe" | CVR +30-50% | Superwall |
| **Weekly price breakdown** | $49.99/yr → "$0.96/week" | Perception shift | Superwall |
| **Program preview > Feature list** | 7-day journey timeline instead of bullet points | CVR +50% | Clear 30 |
| **"No commitment, cancel anytime"** | On every paywall, below CTA | Consistent CVR lift | Superwall |
| **Blinkist timeline paywall** | Today→Day 5 reminder→Day 7 charge | CVR +23%, complaints -55% | RevenueCat |
| **Transparency** | Tell users app costs money during onboarding | CVR +3% | Clear 30 |
| **Drawer strategy** | × press → slide-up weekly reframe → final offer | Recovery without modal risk | Superwall |

---

## Progress Bar Spec

| Attribute | Value |
|-----------|-------|
| Position | SafeArea top, 8px padding |
| Height | 4px |
| Corner radius | 2px |
| Color | Accent color |
| Background | Label 10% opacity |
| **Start value** | **20%** (Endowed Progress Effect) |
| Calculation | `0.2 + 0.8 × (currentStep / totalSteps)` |
| Animation | `.easeInOut(duration: 0.4)` |
| **Hidden on** | Paywall steps (Step 9-12) |

---

## Japanese Market Considerations

| Factor | Japan Tendency | Response |
|--------|---------------|----------|
| Price sensitivity | ¥1,500/mo feels high. Annual discount effective | Push annual + weekly breakdown |
| Trust priority | Review/word-of-mouth culture | Strong social proof |
| Politeness | Keigo/polite expressions preferred | All copy in 丁寧語 |
| Cancel anxiety | Stronger than US — fear of forgetting to cancel | Trial reminder especially emphasized |
| Privacy | Cautious about data collection | "Processed on device" messaging |

---

## Target Metrics

| Metric | Target | How to Measure |
|--------|--------|---------------|
| Onboarding completion rate | >70% | Analytics: slide-by-slide drop-off |
| Paywall view rate | >80% | Onboarding complete → paywall shown |
| Paywall CVR (soft) | >5% | Purchase / paywall views |
| Free trial start rate | >15% | Trial start / paywall views |
| Trial → Paid | >60% | Paid / trial starts |
| D1 retention | >40% | Next-day return rate |

---

## Reference Apps

| App | Steps | Pattern | Key Learning | Source |
|-----|-------|---------|-------------|--------|
| Headspace | 87 | Each step ultra-lightweight, actual meditation in onboarding | Wellness: "experience" > "explain" | UserOnboard |
| Duolingo | 77 | Value before signup — lesson before account | Minimize signup barrier | UserOnboard |
| Clear 30 | 7 | Goal→Social proof→Pain point→Solution | $10K→$30K/mo in 8 weeks | Superwall |
| Blinkist | 10-15 | Timeline paywall | CVR +23%, complaints -55% | RevenueCat |
| Balance | 15-20 | Long personalization → result → soft paywall | Meditation gold standard | PaywallScreens |
| RISE | 10-15 | Questions → loading → personalized paywall | "Building your plan" pattern | PaywallScreens |
| Fastic | 10+ | Long onboarding, 26M users, still high conversion | Length doesn't kill if personalized | PaywallScreens |
| Opal | 8-10 | Problem → solution → paywall | Problem-solution frame | PaywallScreens |

---

## References

For detailed research and app-specific implementation:
- `references/onboarding-paywall-best-practices.md` — Full research with sources and citations
- `.cursor/plans/ios/onboarding-paywall-best-practices.md` — Comprehensive BP with 17 sections
- `.cursor/plans/ios/spec-onboarding-improvement.md` — Anicca-specific implementation spec
