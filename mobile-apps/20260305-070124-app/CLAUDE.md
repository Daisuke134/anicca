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
| 17 | **Mixpanel 禁止**。アナリティクス SDK は一切入れない。Greenlight が tracking SDK 検出 = CRITICAL |
| 18 | **screenshot-creator スキル使用禁止**。Koubou（`asc screenshots frame`）のみ |
| 19 | **全ての `asc` コマンドに `export ASC_BYPASS_KEYCHAIN=true` を設定すること**。未設定だとハングする |
| 20 | **オンボーディング最終画面はソフトペイウォール必須**。自前 SwiftUI PaywallView + Purchases.shared.purchase(package:)。RevenueCatUI 禁止。[Maybe Later] で閉じれる |
| 20b | **ATT 禁止**。AppTrackingTransparency / NSUserTrackingUsageDescription は使わない。スクショに ATT ダイアログが写り込む |
| 21 | **1 iteration = 1 US（厳守）**。2つ以上のUSを1イテレーションで実行したら即座に停止。次のイテレーションで続行。500ターン超過も即停止 |
| 22 | **PATH 設定（全イテレーション冒頭で実行）**: `export PATH="/Users/anicca/Library/Python/3.9/bin:$PATH"` と `export ASC_BYPASS_KEYCHAIN=true` |

## ASC CLI 正しいコマンド（skill 準拠）

| タスク | 正しいコマンド | スキル |
|--------|---------------|--------|
| スクショ capture | `asc screenshots capture --bundle-id ... --udid ... --output-dir ... --output json` | asc-shots-pipeline |
| スクショ upload | `asc screenshots upload --version-localization LOC_ID --path DIR --device-type IPHONE_67` | asc-shots-pipeline |
| Review screenshot | `asc subscriptions review-screenshots create --subscription-id ID --file PATH` | — |
| ビルド最新取得 | `asc builds list --app APP_ID --sort -uploadedDate --limit 1` | asc-build-lifecycle |
| ビルドをグループ追加 | `asc builds add-groups --build BUILD_ID --group GROUP_ID` | asc-testflight-orchestration |
| テスター追加 | `asc testflight beta-testers add --app APP_ID --email ... --group ...` | asc-testflight-orchestration |
| テスター招待 | `asc testflight beta-testers invite --app APP_ID --email ...` | asc-testflight-orchestration |
| Version ID 取得 | `asc versions list --app APP_ID` | asc-id-resolver |
| Loc ID 取得 | `asc app-store-version-localizations list --version-id VER_ID` | asc-id-resolver |
| App Privacy | `asc web privacy apply` + `publish`（自動、セッション切れ時のみ WAITING_FOR_HUMAN） | us-009-submit |
| RC Public Key | `curl -s "$RC_BASE/projects/$PID/apps/$AID/public_api_keys" -H "$AUTH" \| jq -r '.items[0].key'`（自動） | us-005b-monetization |
| 審査提出 | `asc review submissions-create --app APP_ID` → `items-add` → `submissions-submit` | asc-submission-health |

**❌ 存在しないフラグ（使うな）:** `--locale`, `--file`(screenshots upload), `--display-type`

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
2. Document what's failing in progress.txt with "BLOCKED: <reason>"
3. **DO NOT SKIP to the next story** — wait for the issue to be resolved
4. Never use forbidden shortcuts to force a pass

**CRITICAL:** 前の US が完了していないまま次の US に進むと、モックコードや不完全な実装になる。
US は順序依存。US-005a（インフラ）→ US-005b（マネタイズ）→ US-006（実装）の順。
BLOCKED 状態で iteration を終了し、次の iteration で再試行を待つ。

## Consolidate Patterns
# Source: harrymunro/ralph-wiggum CLAUDE.md
# Quote: "add reusable patterns to Codebase Patterns at TOP of progress.txt"

If you discover a reusable pattern, add it to `## Codebase Patterns`
at the TOP of progress.txt (create if it doesn't exist).
Only general, reusable patterns — not story-specific details.


## US別詳細手順
各USの実行時は必ず対応する `references/us-XXX.md` を読むこと。
この CLAUDE.md には詳細を書かない。references が常に正本。

## WAITING_FOR_HUMAN
progress.txt に `WAITING_FOR_HUMAN: <what you need>` を書いて passes: false にする。
ralph.sh が検知して Slack に通知する。
次のイテレーションで .env を確認して再開する。
