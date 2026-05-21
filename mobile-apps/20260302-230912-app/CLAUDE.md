# mobileapp-builder — CLAUDE.md
# Source: harrymunro/ralph-wiggum (https://github.com/harrymunro/ralph-wiggum/blob/main/CLAUDE.md)
# Source: Geoffrey Huntley (https://ghuntley.com/ralph/) — "use as little context as possible"
# Source: Anthropic harness (https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)

## Your Task

1. Read `prd.json` (same directory as this file)
2. Read `progress.txt` (check Codebase Patterns section FIRST)
3. Pick the **highest priority** user story where `passes: false`
4. Read `.claude/skills/mobileapp-builder/references/us-<NNN>-*.md` for this US
5. Read referenced skills (listed in the spec file)
6. Implement that single user story
7. Run verification checks listed in the spec
8. If checks pass, commit ALL changes: `feat: [US-ID] - [Title]`
9. Update prd.json: set `passes: true` + add notes
10. Append progress to `progress.txt`
11. Report via Slack (BOTH, curl FIRST):
    source ~/.config/mobileapp-builder/.env
    curl -s -X POST "$SLACK_WEBHOOK_AGENTS" -H 'Content-Type: application/json' -d '{"text":"🏭 <US-ID> 完了: <summary>"}'

## Special Slack Reports (US-001, US-007)

### US-001 完了時（アイデア報告）:
curl -s -X POST "$SLACK_WEBHOOK_AGENTS" -H 'Content-Type: application/json' -d '{"text":"📱 アイデア選定完了\nApp: <app_name>\n概要: <one_liner>\n理由: <why_this_trend>\nターゲット: <target_user>"}'

### US-007 完了時（TestFlightリンク報告）:
TESTFLIGHT_URL=$(asc testflight builds get-link --app <APP_ID> --build <BUILD_ID> 2>/dev/null || echo "N/A")
curl -s -X POST "$SLACK_WEBHOOK_AGENTS" -H 'Content-Type: application/json' -d '{"text":"🧪 TestFlight準備完了\nリンク: '"$TESTFLIGHT_URL"'\n↑タップしてテスト可能"}'

## CRITICAL Rules (違反 = リジェクト)

| # | Rule |
|---|------|
| 17 | **RevenueCat/Mixpanel API キーは Info.plist から読む**。`ProcessInfo.processInfo.environment` 禁止 |
| 18 | **screenshot-creator スキル使用禁止**。Koubou（`asc screenshots frame`）のみ |
| 19 | **オンボーディング最終画面はソフトペイウォール必須**。自前 SwiftUI PaywallView + Purchases.shared.purchase(package:)。RevenueCatUI 禁止。[Maybe Later] で閉じれる |
| 20 | **ATT 禁止**。AppTrackingTransparency / NSUserTrackingUsageDescription は使わない |
    openclaw system event --text "🏭 <US-ID> 完了" 2>/dev/null || true

## Progress Report Format
# Source: mischasigtermans/ralph (https://github.com/mischasigtermans/ralph)

APPEND to progress.txt (never replace):

```
## [Date] - [US-ID]: [Title]
- What was implemented
- Files changed
- **Learnings for future iterations:**
  - Patterns discovered
  - Gotchas encountered
---
```

## Mandatory Quality Gates (Backpressure)
# Source: harrymunro/ralph-wiggum CLAUDE.md
# Quote: "Quality gates are mandatory blockers, not suggestions"

Before marking ANY story as `passes: true`, you MUST verify:
1. All acceptance criteria met with EVIDENCE (not assertion)
2. All checks in the reference file pass
3. git commit clean

### Forbidden Shortcuts
# Source: harrymunro/ralph-wiggum CLAUDE.md

| Forbidden | Why |
|-----------|-----|
| Mock/Stub RevenueCat | Must use real SDK |
| Skip subscription pricing | MISSING_METADATA = rejection |
| Python/Pillow for screenshots | Only Koubou + asc-shots-pipeline skill |
| Skip greenlight checks | External gate will catch and reset |
| Set passes:true without evidence | validate.sh will auto-reset |

### Evidence Over Assertion
# Source: harrymunro/ralph-wiggum CLAUDE.md
# Quote: "Never claim something works without proving it"

| Bad (Assertion) | Good (Evidence) |
|-----------------|-----------------|
| "Subscriptions configured" | "asc subscriptions list → state=READY_TO_SUBMIT" |
| "Screenshots uploaded" | "find screenshots/framed -name '*.png' \| wc -l → 3" |
| "Build valid" | "asc builds list → processingState=VALID" |

Run the command. See the output. Report the evidence.

## Secrets
Before any signing/build:
```
source ~/.config/mobileapp-builder/.env
security unlock-keychain -p "$KEYCHAIN_PASSWORD" ~/Library/Keychains/login.keychain-db
```

## Stop Condition
# Source: harrymunro/ralph-wiggum + snarktank/ralph

After completing a story, check if ALL stories have `passes: true`.
If ALL complete: `<promise>COMPLETE</promise>`
If stories remain: end normally (next iteration picks up).

## CRITICAL RULES
- Read .claude/skills/mobileapp-builder/SKILL.md for all CRITICAL RULES
- ONE story per iteration (Source: ghuntley.com/ralph/ "one item per loop")
- Every source file change → git commit
- Every US start → Slack report
- Every US completion → update progress.txt + prd.json + git commit + Slack report
- DO NOT modify validate.sh (external quality gate, not your file)

## 3-Attempt Limit
# Source: harrymunro/ralph-wiggum CLAUDE.md
# https://raw.githubusercontent.com/harrymunro/ralph-wiggum/main/CLAUDE.md
# Quote: "If you cannot make a story pass quality gates after 3 attempts: STOP"

If you cannot make a story pass after 3 attempts:
1. STOP — do not continue iterating
2. Document what's failing in progress.txt
3. Skip to the next story
4. Never use forbidden shortcuts to force a pass

## Consolidate Patterns
# Source: harrymunro/ralph-wiggum CLAUDE.md
# Quote: "add reusable patterns to Codebase Patterns at TOP of progress.txt"

If you discover a reusable pattern, add it to `## Codebase Patterns`
at the TOP of progress.txt (create if it doesn't exist).
Only general, reusable patterns — not story-specific details.

## Human Intervention Pattern
When you need human action (ASC app creation, RC setup, App Privacy):

1. Write to progress.txt:
```
WAITING_FOR_HUMAN: <what you need>
<detailed instructions for Dais with copy-paste info>
```

2. Set passes: false for this US
3. End your response normally (next iteration will retry)

ralph.sh detects WAITING_FOR_HUMAN in progress.txt → posts to Slack.
Anicca (OpenClaw) receives Dais's reply → writes keys to .env / touches files.
Next iteration: you read .env / check files → continue.

### What to check per US:
- US-005 ASC creation: check progress.txt for APP_ID
- US-005 RC keys: check .env for RC_SECRET_KEY + RC_PUBLIC_KEY
- US-009 App Privacy: check .app-privacy-done file exists
