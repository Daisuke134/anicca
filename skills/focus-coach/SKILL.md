---
name: focus-coach
description: "Focus coach for AI agents — diagnose focus blockers using BJ Fogg's B=MAP model and prescribe tiny actions. Use when: user can't focus, productivity stuck, procrastinating, distracted, overwhelmed. Triggers: focus, concentrate, distracted, procrastinate, stuck, overwhelmed, can't start, motivation."
version: 1.0.0
author: Daisuke134
---

# focus-coach — x402 Focus Diagnosis + Tiny Action

Pay $0.01 USDC per request. Diagnoses why someone can't focus (Motivation, Ability, or Prompt missing) and returns a single tiny action based on BJ Fogg's Tiny Habits methodology.

## Prerequisite

```bash
npm install -g awal@2.0.3
awal auth login
```

## Usage

```bash
# Check endpoint details
npx awal@2.0.3 x402 details https://anicca-proxy-production.up.railway.app/api/x402/focus-coach

# Make a paid request
npx awal@2.0.3 x402 pay https://anicca-proxy-production.up.railway.app/api/x402/focus-coach \
  -X POST \
  -d '{"situation":"I need to write a report but keep checking my phone","energy_level":"low","time_available_minutes":10,"language":"en"}'
```

## Input Schema

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| situation | string (1-2000) | ✅ | — | What you're trying to do and what's blocking you |
| energy_level | "low" \| "medium" \| "high" | ❌ | "medium" | Current energy state |
| time_available_minutes | number (1-60) | ❌ | 5 | Minutes available for the tiny action |
| language | "en" \| "ja" | ❌ | "en" | Output language |

## Output Schema

```json
{
  "coach_id": "fcs_a1b2c3d4",
  "diagnosis": {
    "blocker": "ability",
    "explanation": "The task feels overwhelming because there is no clear first step."
  },
  "tiny_action": {
    "action": "Open the document and type one sentence.",
    "anchor": "After I sit down at my desk, I will open the document and type one sentence.",
    "celebration": "Say 'I started!' and do a small fist pump."
  },
  "follow_up": "After typing one sentence, set a 5-minute timer and keep going.",
  "safe_t_flag": false
}
```

## Chain with emotion-detector

```bash
# Step 1: Detect emotion
EMOTION=$(npx awal@2.0.3 x402 pay .../emotion-detector -X POST -d '{"text":"I feel so overwhelmed"}')
# Step 2: Use emotion context in focus-coach
npx awal@2.0.3 x402 pay .../focus-coach -X POST -d '{"situation":"Feeling overwhelmed, need to finish project","energy_level":"low"}'
```

## Pricing

- $0.01 USDC per request (Base network)
- Payment via x402 protocol (HTTP 402)
