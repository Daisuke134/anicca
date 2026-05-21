# Service Architecture

## Stack

| Component | Technology |
|-----------|-----------|
| iOS | Swift/SwiftUI (iOS 15+, Xcode 16+) |
| API | Node.js/Express (Railway) |
| DB | PostgreSQL/Prisma |
| Payments | RevenueCat ($9.99/mo, $49.99/yr) |
| Analytics | Mixpanel (project: 3970220) |
| E2E | Maestro |
| Agent | OpenClaw (Mac Mini) |

## Directory Structure

```
anicca-project/
├── aniccaios/          # iOS app
├── apps/api/           # Express API
├── apps/landing/       # Netlify landing page
├── .claude/            # CC config (rules/, skills/)
├── .specify/           # SDD specs
├── agent_docs/         # Agent reference docs
└── maestro/            # E2E tests
```

## Deploy

| Branch | Environment | Trigger |
|--------|------------|---------|
| main | Production (Railway) | Auto on push |
| dev | Staging (Railway) | Auto on push |
| release/x.x.x | App Store snapshot | Manual |

## MCP Project IDs

| Service | ID |
|---------|-----|
| Mixpanel | `3970220` (integer) |
| RevenueCat | `projbb7b9d1b` (string) |

## Execution Environment

| Item | Value |
|------|-------|
| Machine | Mac Mini (anicca-mac-mini-1) |
| Tailscale | 100.99.82.95 |
| Timezone | JST (Asia/Tokyo) |
| MacBook SSH | `ssh cbns03@100.108.140.123` |
