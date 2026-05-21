# iOS Onboarding Design Rules

Source: [Mau - Prayer Lock $25k/month](https://www.youtube.com/watch?v=mau_prayer_lock) — 8 rules for high-converting onboarding

## 8 Rules

| # | Rule | Detail |
|---|------|--------|
| 1 | **3-Act Structure** | Problem presentation -> App experience -> Paywall. "introduction -> climax -> conclusion" |
| 2 | **Questions = Self-Persuasion** | Ask questions not for data, but so users reflect on their own answers and convince themselves |
| 3 | **Answer Mirroring** | Mirror the user's answers back to them in subsequent screens to create personalization feeling |
| 4 | **Longer = Higher Conversion (if valuable)** | "the longer, the better it converts" — but every screen must provide value |
| 5 | **Let Users Experience Core Feature** | Don't just describe — let users actually USE the core feature during onboarding |
| 6 | **Review Modal After Core Experience** | Request App Store review RIGHT AFTER the user completes the core feature (peak satisfaction) |
| 7 | **Commitment Principle** | Users actively state they are committed BEFORE seeing the paywall |
| 8 | **10%+ DL-to-Trial Conversion** | Target at least 10% download-to-trial conversion rate |

## Implementation Pattern (SwiftUI)

```
OnboardingContainerView
  |-- Step 1: ProblemEmpathyView (Act 1: Problem)
  |     - Hook: "Do you struggle with X?"
  |     - Emotional connection
  |     - accessibilityIdentifier: "onboarding_get_started"
  |
  |-- Step 2: PersonalizationView (Act 1: Questions)
  |     - 2-3 questions for self-persuasion
  |     - Tap selections (not text input)
  |     - accessibilityIdentifier: "onboarding_continue"
  |
  |-- Step 3: CoreExperienceView (Act 2: Try It)
  |     - Let user USE the core feature
  |     - Brief, guided interaction
  |     - Review modal after completion (Rule 6)
  |
  |-- Step 4: CommitmentView (Act 2: Commit)
  |     - Mirror user's answers (Rule 3)
  |     - "Are you ready to commit?" (Rule 7)
  |
  |-- Step 5: PaywallView (Act 3: Soft Paywall)
  |     - Show plans (monthly + annual)
  |     - [Maybe Later] to dismiss (soft paywall)
  |     - accessibilityIdentifier: "paywall_plan_monthly", "paywall_plan_yearly", "paywall_maybe_later"
```

## Anti-Patterns

| Bad | Good |
|-----|------|
| Skip straight to paywall | 3-act structure with value delivery first |
| Ask questions without using answers | Mirror answers back in later screens |
| Describe features in text | Let users experience the core feature |
| Hard paywall (no skip) | Soft paywall with [Maybe Later] |
| Generic "Welcome to AppName" | Problem-focused hook that resonates |
| Request review on first launch | Request after core feature completion |

## Design Thinking for iOS Onboarding

Source: Adapted from [Anthropic frontend-design](frontend-design/SKILL.md)

Before designing, understand the context:
- **Purpose**: What problem does this onboarding solve? What's the user's emotional state?
- **Tone**: Warm and encouraging (health/wellness), Urgent and bold (productivity), Playful (entertainment)
- **Constraints**: iOS 15+ compatibility, VoiceOver, Dynamic Type, Dark Mode
- **Differentiation**: What's the one thing that makes this onboarding memorable?

Apply Apple HIG principles:
- Use SF Symbols, semantic colors, San Francisco font
- 44pt minimum touch targets
- Standard iOS navigation patterns
- Respect safe areas and Dynamic Island
