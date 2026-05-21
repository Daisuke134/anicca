# mobileapp-builder — CLAUDE.md
# Source: harrymunro/ralph-wiggum (https://github.com/harrymunro/ralph-wiggum/blob/main/CLAUDE.md)
# Source: Geoffrey Huntley (https://ghuntley.com/ralph/) — "use as little context as possible"
# Source: Anthropic harness (https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)

## Step 0: PATH Setup (MANDATORY — EVERY bash command)

Source: Claude Code Docs — https://docs.anthropic.com/en/docs/claude-code/overview
> "Each command runs in a new shell session. Environment variables set in one command are not automatically available in the next."

**Every single `Bash` tool call MUST start with this line. No exceptions:**

```bash
export PATH="/opt/homebrew/bin:/Users/anicca/Library/Python/3.9/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
```

Without this, `asc`, `fastlane`, `xcrun`, `simctl`, `axe`, `jq`, `ls`, `tail`, `grep` and all other commands will fail with `command not found`.
This is NOT optional. This is NOT a suggestion. Prepend it to EVERY command.

## Your Task

APP_DIR = このファイル (CLAUDE.md) が置かれているディレクトリのフルパス。

1. Read `$APP_DIR/prd.json`
2. Read `$APP_DIR/progress.txt` (check Codebase Patterns section FIRST)
3. Pick the **highest priority** user story where `passes: false`
4. Read `.claude/skills/mobileapp-builder/references/us-<NNN>-*.md` for this US
5. Read referenced skills (listed in the spec file)
6. Implement that single user story
7. Run verification checks listed in the spec
8. If checks pass, commit ALL changes: `feat: [US-ID] - [Title]`
9. Update `$APP_DIR/prd.json`: set `passes: true` + add notes
10. Append progress to `$APP_DIR/progress.txt`
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
| 19 | **`ASC_BYPASS_KEYCHAIN=true` は絶対禁止。** iris session は US-005a Step 4.9 で管理する。`security unlock-keychain` + `unset ASC_BYPASS_KEYCHAIN` を使うこと |
| 20 | **オンボーディング最終画面はソフトペイウォール必須**。自前 SwiftUI PaywallView + Purchases.shared.purchase(package:)。RevenueCatUI 禁止。[Maybe Later] で閉じれる |
| 20b | **ATT 禁止**。AppTrackingTransparency / NSUserTrackingUsageDescription は使わない。スクショに ATT ダイアログが写り込む |
| 21 | **1 iteration = 1 US（HARD STOP）**。1つのUSを `passes: true` にしたら、**その瞬間に作業を終了**する。次のUSに手を出すな。progress.txt を更新して終了。ralph.sh が次の iteration を起動する。これは提案ではなく**絶対ルール**。違反するとトークンが無駄になる（validate.sh は1USしか検証しない）。500ターン超過も即停止 |
| 22 | **PATH 設定のみ（全イテレーション冒頭で実行）**: `export PATH="/opt/homebrew/bin:/Users/anicca/Library/Python/3.9/bin:/usr/local/bin:/usr/bin:/bin:$PATH"` |
| 24 | **スクショは 6.9" (IPHONE_69) のみ。1320x2868 が正しいサイズ。** 6.5"/6.1"/5.5" は不要（Apple が 6.9" から自動スケール）。6.7" で再キャプチャしようとするな。Source: https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications/ |
| 23 | **AI API / 外部 API コスト禁止** — OpenAI, Anthropic, Gemini, Apple FoundationModels（iOS 26+ = ユーザー基盤小）一切禁止。アプリは完全自己完結。ローカル・静的コンテンツのみ。バックエンド不要。理由: 月収 $29 vs API コスト $300+ |
| 23 | **AI API / AI モデル / 外部 AI サービス完全禁止**。OpenAI, Anthropic, Google Generative AI, Apple FoundationModels 一切不可。月額収益 $29 vs API コスト $300+。FoundationModels は iOS 26+ のみでユーザーベース皆無。オンデバイスロジック or 静的キュレーションコンテンツで代替 |
| 25 | **progress.txt 管理**: Codebase Patterns + 現在 US の記録のみ保持。完了 US の詳細は `logs/us-XXX-summary.md` に移動。10KB 以下維持。Source: Anthropic harnesses — context 膨張防止 |
| 26 | **WAITING_FOR_HUMAN 最小化**: iris session は keychain（auto モード）で管理。`ASC_WEB_SESSION_CACHE_BACKEND=file` は絶対に設定するな（keychain を読まなくなる）。Check 6 の前に `security unlock-keychain` 必須。RC SK鍵のみ WAITING_FOR_HUMAN 使用可。Source: session_cache.go L103-118 |

## ASC CLI 正しいコマンド（skill 準拠）

| タスク | 正しいコマンド | スキル |
|--------|---------------|--------|
| スクショ capture | `asc screenshots capture --bundle-id ... --udid ... --output-dir ... --output json` | asc-shots-pipeline |
| スクショ upload | `asc screenshots upload --version-localization LOC_ID --path DIR --device-type IPHONE_69` | asc-shots-pipeline |
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
- Every US completion → update `$APP_DIR/progress.txt` + `$APP_DIR/prd.json` + git commit + Slack report
- DO NOT modify validate.sh or ralph.sh (external quality gates, not your files)
- DO NOT modify `.claude/skills/mobileapp-builder/prd.json` (テンプレート。`$APP_DIR/prd.json` のみ編集可)
- DO NOT modify `.claude/skills/mobileapp-builder/SKILL.md` or `.claude/skills/mobileapp-builder/CLAUDE.md` (テンプレート)

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

### ASC CLI スキル（補助参照 — 必要に応じて読む）
- US-008a screenshots: `.agents/skills/asc-shots-pipeline/SKILL.md` (screenshot pipeline patterns)
- US-008b metadata: `.agents/skills/asc-metadata-sync/SKILL.md` (metadata sync patterns)
- US-008e release: `.agents/skills/asc-release-flow/SKILL.md` (release flow)
- CLI usage: `.agents/skills/asc-cli-usage/SKILL.md` (flags/output/auth guidance)

| US-010 | Build Report | logs/ トークン集計 → build-report.json → Slack + X 投稿 | us-010-report |

## WAITING_FOR_HUMAN
progress.txt に `WAITING_FOR_HUMAN: <what you need>` を書いて passes: false にする。
ralph.sh が検知して Slack に通知する。
次のイテレーションで .env を確認して再開する。

## US-008 連続実行ルール（CRITICAL）
US-008a を開始したら、US-008e まで連続で完了させること。
途中で他の US（US-004b, US-004-R, US-005a 等）に移動してはならない。
prd.json の priority 順を無視して、US-008a → 008b → 008c → 008d → 008e の順に実行する。
理由: US-008a-d で取得した VERSION_ID, BUILD_ID, LOC_ID 等の環境変数が
有効な間に全ステップを完了しないと、途中で別の US に飛ばされてセッションが切れる。
