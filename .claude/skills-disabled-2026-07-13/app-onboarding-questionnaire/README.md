# App Onboarding Questionnaire

A [Claude Code](https://claude.ai/code) skill that designs and builds high-converting questionnaire-style onboarding flows for your app — modelled on proven conversion patterns from top subscription apps like Mob, Headspace, Noom, and Duolingo.

## What It Does

Run `/app-onboarding-questionnaire` from your app project and the skill will:

1. **Analyse your codebase** to understand what your app does, who it's for, and what permissions it needs
2. **Define the user transformation** — the before/after story that drives your onboarding narrative
3. **Design a screen-by-screen blueprint** using a proven 14-screen psychological framework
4. **Draft all the copy** — headlines, questions, options, CTAs, social proof
5. **Build the onboarding flow** in your app's native framework (SwiftUI, React Native, Flutter, etc.)

No marketing expertise required. The skill handles the conversion psychology — you just answer questions about your app.

## The Framework

The onboarding follows a proven psychological sequence used by the highest-converting subscription apps:

| # | Screen | Purpose |
|---|--------|---------|
| 1 | Welcome | Hook — show the end state, create desire |
| 2 | Goal Question | "What are you trying to achieve?" — creates psychological investment |
| 3 | Pain Points | "What prevents you?" — surfaces frustrations, builds empathy |
| 4 | Social Proof | Testimonials matched to user personas |
| 5 | Tinder Cards | Swipe agree/disagree on pain statements — interactive self-identification |
| 6 | Personalised Solution | Mirror their pains back with stats showing how the app solves each one |
| 7 | Comparison Table | Life with vs without the app *(optional)* |
| 8 | Preferences | Functional personalisation that feeds the upcoming demo |
| 9 | Permission Priming | Benefit-framed pre-sell before system permission dialogs *(auto-detected)* |
| 10 | Processing Moment | "Building X just for you..." — anticipation builder |
| 11 | App Demo | User actually USES the core app mechanic — not a tour, a real interaction |
| 12 | Value Delivery | Tangible output from their demo + share/viral moment |
| 13 | Account Gate | Optional sign-in to unlock what they just created |
| 14 | Paywall | Hard paywall with trial, social proof, and pricing |

Not every app needs every screen — the skill adapts based on your app's complexity.

## What Makes This Different

Most onboarding generators stop at the questionnaire. This skill goes further:

- **App Demo Screen** — Builds a functional mini-version of your app's core interaction inside the onboarding. Users pick recipes, choose exercises, categorise transactions — whatever your core loop is. They DO something and get a tangible result back.
- **Viral Moment** — The demo output is designed to be shareable. This is where organic growth comes from.
- **Permission Priming** — Auto-detects permissions from your codebase (Info.plist, AndroidManifest, etc.) and creates benefit-framed priming screens that convert at 70-80%+ vs ~40% for cold system prompts.
- **Resumable** — Progress is saved to Claude Code's memory system. Come back tomorrow and pick up where you left off.

## Installation

### Option 1: Add to your Claude Code skills directory

```bash
cd ~/.claude/skills
git clone https://github.com/adamlyttleapps/claude-skill-app-onboarding-questoinnaire.git app-onboarding-questionnaire
```

### Option 2: Add as a dependency in your project's `.claude/settings.json`

```json
{
  "skills": [
    "github:adamlyttleapps/claude-skill-app-onboarding-questoinnaire"
  ]
}
```

## Usage

From your app's project directory in Claude Code:

```
/app-onboarding-questionnaire
```

The skill will analyse your codebase and walk you through each phase interactively.

## Reference

The framework is based on analysis of the [Mob](https://www.mob.co.uk/) recipe app's onboarding flow (19 screens), which is widely regarded as one of the best-converting onboarding experiences in the App Store.

## License

MIT
