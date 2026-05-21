# mobileapp-builder

> An AI agent skill that autonomously builds and ships a Swift/SwiftUI iOS app to the App Store — from a spec.md file.

## What This Does

Give it a `spec.md` file and it does everything:

1. **Trend research** — X, TikTok, App Store rankings to find what to build
2. **SDD spec generation** — auto-generates spec.md, plan.md, tasks.md
3. **Xcode scaffold** — creates Swift/SwiftUI project with RevenueCat, Mixpanel
4. **SwiftUI implementation** — builds all screens autonomously via `ralph-autonomous-dev`
5. **Landing + Privacy pages** — deploys to Netlify automatically
6. **ASC setup** — creates app, sets privacy URL, categories, age rating
7. **IAP pricing** — 175-territory pricing via Purchasing Power Parity
8. **IAP localization** — EN + JA subscription display names
9. **IAP review screenshots** — Maestro → native resolution → JPEG upload
10. **App assets** — icon (SnapAI) + App Store screenshots (Pencil MCP)
11. **Build & upload** — Fastlane archive + TestFlight upload
12. **Preflight gate** — Greenlight + URL check + IAP validate + screenshot count
13. **Submit** — `asc submit create --confirm` → `WAITING_FOR_REVIEW` ✅

## Output

`WAITING_FOR_REVIEW` on App Store Connect.

## Prerequisites

Run the checker to see what's missing:
```bash
bash ~/.claude/skills/mobileapp-builder/scripts/check-prerequisites.sh
```

For the complete step-by-step setup → **[SETUP.md](./SETUP.md)**

**Summary of what you need:**

### OpenClaw (Cron Trigger)

| Key | Purpose | Required |
|-----|---------|----------|
| OpenClaw subscription | Gateway runtime | ✅ |
| LLM API key (Anthropic/OpenAI) | OpenClaw model | ✅ |

### Builder (CC Side)

| Key | Purpose | Required |
|-----|---------|----------|
| Claude Code subscription (Max) | CC execution | ✅ |
| `ASC_KEY_ID` + `ASC_ISSUER_ID` + `ASC_KEY_PATH` | App Store Connect API | ✅ |
| `APPLE_ID` + `APPLE_ID_PASSWORD` | 2FA (web privacy, app create) | ✅ |
| `RC_API_KEY` + `RC_SECRET_KEY` | RevenueCat | ✅ |
| `SLACK_WEBHOOK_AGENTS` | Slack notifications | Optional |
| `FIRECRAWL_API_KEY` | Privacy policy generation | Optional |
| `X_BEARER_TOKEN` | Trend research (X) | Optional |
| `APIFY_API_TOKEN` | Trend research (TikTok) | Optional |

### CLI Tools

`claude`, `asc`, `xcrun`, `xcodebuild`, `jq`, `python3`, `curl`, `git`

### Subagents

| File | Purpose |
|------|---------|
| `.claude/agents/code-quality-reviewer.md` | Code/spec review via Agent tool |

## Installation

```bash
# Install via npx skills (if using skill.sh)
npx skills add Daisuke134/mobileapp-builder -g -y

# Or copy SKILL.md to your .claude/skills/mobileapp-builder/ directory
```

## Usage

1. Complete setup: follow **[SETUP.md](./SETUP.md)** and verify with `check-prerequisites.sh`
2. In Claude Code, say: **"Build an iOS app about [your idea]"**
3. The agent handles everything. You approve 3 times:
   - **STOP 1**: Review the generated spec.md in Slack → approve or request changes
   - **STOP 2**: Test the TestFlight build → approve or request fixes
   - **STOP 3**: Set App Privacy in ASC Web (2 min) → say "done" → auto-submit

## Key Lessons Learned (Real-World Submissions)

| Lesson | Detail |
|--------|--------|
| App Privacy = auto via asc web privacy | `/v1/apps/{id}/appDataUsages` returns 404. Set in ASC Web before submitting |
| ISSUER_ID source | Always read from Fastfile `API_ISSUER_ID`, not ASC dashboard "Key ID" |
| Icon timing | Place icon BEFORE build. If added after, bump `CURRENT_PROJECT_VERSION` |
| IAP screenshot size | Use native simulator resolution (1320×2868). Never resize with `-z` flag |
| `asc submit create` | Use `--confirm` flag. `PATCH reviewSubmissions.state` returns 409 |
| Availability before pricing | Set `asc subscriptions availability set` BEFORE pricing. Reverse order = 500 errors |
| Privacy URL locale | Use `ja` not `ja-JP`. ASC API rejects `ja-JP` |

## Structure

```
mobileapp-builder/
├── SKILL.md              ← Main skill (14 phases, 22 critical rules, 3 human stops)
├── SETUP.md              ← Complete setup guide (accounts, env vars, CLIs, MCPs)
├── references/
│   ├── iap-bible.md      ← IAP pricing detailed guide
│   ├── spec-template.md  ← spec.md format template
│   └── submission-checklist.md ← Preflight gate checklist
└── scripts/
    ├── add_prices.py     ← 175-territory IAP pricing script
    └── check-prerequisites.sh  ← Auto-check all prerequisites
```

## Philosophy

Build fast. Ship fast. One spec.md → App Store in one agent session.

No manual Xcode. No manual ASC. Fully autonomous. App Privacy auto via asc web privacy.

---

Built by [Daisuke Narita](https://twitter.com/daisuke_narita_) while building [Anicca](https://aniccaai.com) — a proactive behavior change agent.

MIT License
