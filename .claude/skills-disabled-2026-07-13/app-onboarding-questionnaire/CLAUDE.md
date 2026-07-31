# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Claude Code skill (`app-onboarding-questionnaire`) that designs and builds high-converting questionnaire-style onboarding flows for any app. Modelled on proven conversion patterns from top subscription apps (Mob, Headspace, Noom, Duolingo). Invoked via `/app-onboarding-questionnaire` from within a user's app project.

## Skill Structure

- **SKILL.md** — The skill prompt. Defines a 5-phase workflow: App Discovery → User Transformation → Blueprint → Screen Content → Implementation. Uses memory to persist state across conversations.
- **CLAUDE.md** — This file. Development guidance for working on the skill itself.

## The Onboarding Framework

The skill implements a 13-screen archetype sequence based on the Mob recipe app's onboarding (the gold standard reference). The psychological sequence is:

1. **Hook** — Welcome + app preview showing the end state
2. **Goal elicitation** — "What are you trying to achieve?" (single-select, creates investment)
3. **Pain discovery** — "What prevents you?" (multi-select, surfaces frustrations)
4. **Social proof** — Testimonials matched to user personas
5. **Pain amplification** — Tinder-style agree/disagree cards (interactive self-identification)
6. **Personalised solution** — Mirror their pains back with stats showing how the app solves each one
7. **Comparison table** — Life with vs without the app (optional)
8. **Preference config** — Functional personalisation that feeds the upcoming demo
9. **Permission priming** — Auto-detected from codebase; benefit-framed pre-sell before system dialog (notifications, location, camera, etc.)
10. **Processing moment** — "Building X just for you..." (anticipation, even if instant)
11. **App demo** — User actually USES the core app mechanic (hardest screen — must be functional, not a tour)
12. **Value delivery** — Tangible output from their demo + share/viral moment
13. **Account gate** — Optional sign-in to unlock what they just created
14. **Paywall** — Hard paywall with trial, social proof, and pricing

Not every app needs every screen — the skill adapts based on complexity.

## Key Design Decisions

- **Platform-adaptive** — Works with SwiftUI, UIKit, React Native, Flutter, Jetpack Compose, or any framework. Reads the codebase to determine patterns.
- **The app demo is the differentiator** — Most onboarding skills just do questionnaires. This one requires building a functional mini-demo of the app's core interaction inside the onboarding flow. This is the hardest part and the most important.
- **Viral moment is intentional** — The demo must produce a shareable output. This is where organic growth comes from.
- **Memory-driven resume** — All phases save to Claude Code memory so users can resume across conversations.
- **Non-marketer friendly** — The skill asks simple questions and handles the conversion psychology. The user doesn't need marketing expertise.

## Conventions

- The skill runs from the user's app project directory, not from this skill directory.
- SKILL.md frontmatter must include `name`, `description`, and `user-invocable: true`.
- Always check memory for prior state before starting any phase.
- Copy should be conversational, not marketing-speak. "Would I say this to a friend?" test.
