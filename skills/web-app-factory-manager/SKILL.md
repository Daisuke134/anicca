---
name: web-app-factory-manager
description: Ralph Loop パターンで Web アプリを自律ビルド・Vercel デプロイする。Use when triggered by web-app-factory-daily cron at 15:00 JST, or told to "run web-app-factory", "trigger web app build", "start web factory".
---

# web-app-factory-manager v1

Ralph Loop (snarktank/ralph) + appfactory-builder + vercel-deploy で
Web アプリを自律的にビルドし Vercel にデプロイする。

ソース: snarktank/ralph (https://github.com/snarktank/ralph/blob/main/ralph.sh)
ソース: Anthropic harness (https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)

---

## STEP 1: web-apps/<name>/ を作成

```bash
APP_DIR=/Users/anicca/anicca-project/web-apps/$(date +%Y%m%d)-$(date +%H%M%S)-app
mkdir "$APP_DIR"   # no -p: fail if exists (fresh instance per run)
```

## STEP 2: prd.json + CLAUDE.md + ralph.sh をコピー

```bash
cp /Users/anicca/anicca-project/.claude/skills/web-app-factory/prd.json.template "$APP_DIR/prd.json"
cp /Users/anicca/anicca-project/.claude/skills/web-app-factory/CLAUDE.md.template "$APP_DIR/CLAUDE.md"
cp /Users/anicca/anicca-project/.claude/skills/web-app-factory/ralph.sh "$APP_DIR/ralph.sh"
chmod +x "$APP_DIR/ralph.sh"
touch "$APP_DIR/progress.txt"
```

## STEP 3: Slack に起動報告（MANDATORY — 最初にやること）

Slack #metrics ({{profile.channels.reportChannel}}) に起動報告を送る。**これが最初のアクション。フォルダ作成より前でも後でもいいが、必ず送る。**

```bash
openclaw message send --channel slack --target "{{profile.channels.reportChannel}}" --text "🏭 Web Factory 起動。APP_DIR=$APP_DIR — 今日の Web アプリを作ります"
```

## STEP 4: tmux 内で ralph.sh を起動

```
First kill any existing factory session (Source: stackoverflow.com/questions/3432536):
```bash
tmux kill-session -t web-factory 2>/dev/null || true
```

Then start:
```
exec pty:true background:true command:"tmux new-session -d -s web-factory -c '$APP_DIR' './ralph.sh 20'"
```
```

sessionId を記録する。

## STEP 5: 監視 + Slack 報告

process action:log で定期的にログを読む。
各イテレーション（🏭 Iteration N）の開始/終了を検出し、Slack #metrics に報告。
system event を受信したらそのまま Slack に転送。

報告タイミング:
- 各 iteration 開始/完了時
- US-004 実行中は 30分ごと
- エラー検出時は即座に

## STEP 6: Stripe Webhook 待ち

US-006 完了後、Slack に「🔑 Stripe Webhook 登録が必要です」が来る。
Dais が Slack で Webhook Secret を送ったら:

```bash
# Vercel に環境変数追加 + 再デプロイ
npx vercel env add STRIPE_WEBHOOK_SECRET production --token $VERCEL_TOKEN <<< "$WEBHOOK_SECRET"
npx vercel deploy --prod --token $VERCEL_TOKEN --yes
```

## STEP 7: 完了処理

ralph.sh 終了（COMPLETE 検出 or MAX_ITERATIONS）後:
1. 最終ログ確認
2. Slack に完了報告「🏭 Web Factory 完了。[AppName] を Vercel にデプロイしました」
3. git add + git commit + git push

---

| 項目 | 値 |
|------|-----|
| 実行環境 | Mac Mini |
| 起動方法 | exec pty:true background:true（ralph.sh を tmux で） |
| 作業ディレクトリ | /Users/anicca/anicca-project/web-apps/<date>-app |
| claude パス | /opt/homebrew/bin/claude |
| 監視方法 | process action:log/poll |
| 所要時間 | 3-8 時間 |
| Slack | #metrics ({{profile.channels.reportChannel}}) |
