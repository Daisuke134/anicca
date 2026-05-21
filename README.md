# Anicca - Proactive iOS Agent for Behavior Change

## Overview
Anicca is a proactive iOS agent that helps people break harmful patterns and build better habits.
It delivers timely nudges through notifications and a focused one-screen experience instead of waiting for prompts.

## Release Status
- App Store approved: **1.3.0 (Phase 6)**
- Next submission: **1.4.0**

## Core Experience (iOS)
1. Onboarding: welcome -> value -> struggles -> notifications -> ATT -> completion
2. Users select 13 Problem Types
3. Scheduled notifications deliver short hooks
4. Tapping opens a Nudge Card with 1-2 choices and feedback
5. LLM-generated nudges (Phase 6) are fetched daily and mixed with rule-based content

### Problem Types
staying_up_late, cant_wake_up, self_loathing, rumination,
procrastination, anxiety, lying, bad_mouthing, porn_addiction,
alcohol_dependency, anger, obsessive, loneliness

## Architecture
- iOS app: `aniccaios/` (Swift / SwiftUI)
- Backend API: `apps/api/` (Node.js / Express, Railway)
- E2E tests: `maestro/`

## Key Backend Endpoints (mobile)
- /api/mobile/profile
- /api/mobile/entitlement
- /api/mobile/nudge (trigger / feedback / today)
- /api/mobile/behavior
- /api/mobile/feeling
- /api/mobile/daily_metrics
- /api/mobile/sensors

## Roadmap
Source of truth: `.cursor/plans/ios/proactive/roadmap.md`

## Landing Page
https://aniccaai.com
