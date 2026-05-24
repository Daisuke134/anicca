---
name: dais-x-feed-digest
description: "RSSHub(無料)で watchlist X を全文取得し、5テーマ各3ニュースを『別々のミニ図解付き infographic』(FRAME2, nano-banana CLI)にして毎朝 08:00 JST に Slack #metrics へ。⑥世界の苦しみは別skill world-suffering-digest に分離。"
metadata: {"openclaw":{"emoji":"📰","os":["darwin","linux"]}}
---

# dais-x-feed-digest

## 目的
ダイスが X をスクロールせず、5テーマの最新を **テーマ毎1枚・各テーマ
3ニュースを別々のミニ図解**で受け取る。文字箱・浅い要約・相関図への
混ぜ込みは禁止(HARD RULE #13、Dais 2026-05-19)。

## 5テーマ（⑥は world-suffering-digest に分離済）
①AIモデル/製品 launch ②AIエージェント/AI entity ③AIで稼ぐ
④アプリ growth ⑤Claude Code/AIコーディング

## アーキテクチャ（毎日=model / 固定=script）
```
[0] script  RSSHub 起動(冪等: colima+docker, TWITTER_AUTH_TOKEN=.env)
[1] script  scripts/fetch_rsshub.py → watchlist12人 本人投稿+RT【全文】
[2] model   5テーマに凝縮。各テーマ重ならない3ニュースを選ぶ
[3] model   /tmp/xf_spec.json 生成(FRAME2 schema・下記) + 各cmt
[4] script  scripts/make_cards.py → nano-banana CLI で5枚
[5] model   5枚を Read 検証(別ニュース図解か/数値入りか)→NG[3-4]再走
[6] script  slack_post.py ×5 → #metrics + conversations.history検証
```

## ソース（RSSHub のみ・grok/X API 不使用）
RSSHub Docker(:1200, Mac mini)。各 handle `/twitter/user/<h>` =
本人投稿+RT を **全文(`description`)** で。truncate される `title`
は使わない(HARD RULE #13)。watchlist=`watchlist.json` の `x_handles`。
起動 bootstrap:
```bash
colima status>/dev/null 2>&1 || colima start --cpu 2 --memory 4
docker ps --format '{{.Names}}'|grep -qx rsshub || { set -a;. ~/.openclaw/.env;set +a
 docker rm -f rsshub 2>/dev/null
 docker run -d --name rsshub -p 1200:1200 -e NODE_ENV=production \
  -e TWITTER_AUTH_TOKEN="$TWITTER_AUTH_TOKEN" diygod/rsshub:latest; sleep 12; }
curl -s -m8 http://localhost:1200/hackernews -o /dev/null -w '%{http_code}'  # 200=健全
```
token 切れたら Dais に再取得依頼(Chrome/Safari Cookies→x.com→auth_token)。

## 必須 env / 役割分担
`TWITTER_AUTH_TOKEN`,`FAL_KEY`,`SLACK_BOT_TOKEN`。推論(全文精読/テーマ
凝縮/3ニュース選定/spec作成/検証)は model。script は RSSHub取得/画像
生成(nano-banana CLI)/投稿+到達検証のみ。

## /tmp/xf_spec.json（make_cards.py が読む・**schema 固定**）
```json
{"date":"YYYY-MM-DD","themes":[
 {"n":1,"label":"① AIモデル/製品 launch","news":[
   {"headline":"Anthropic が Stainless を買収",
    "diagram":"before->after: 外部SDK基盤 → 内製化",
    "situation":"Stainless=全Anthropic SDKを生成してきた会社",
    "number":"対象=全Anthropic SDK/MCP基盤",
    "source":"@AnthropicAI /status/2056419620643541012"},
   {...},{...}]}, ... 1..5 ...]}
```
3ニュースは**重ならない別件**。各 `diagram` は箱/矢印/アイコンの
ミニ図(before→after / timeline / 2-box比較 / funnel)。`number` に
具体数値(例: PayPal 週74,000タスク)。固有名詞は situation で定義。
**JSON 内に裸の " を入れない**。`/tmp/xf_cmt_<n>.txt`=要点+元URL。

## 画像生成（nano-banana CLI 直叩き）
```bash
python3 ~/.openclaw/skills/dais-x-feed-digest/scripts/make_cards.py \
  /tmp/xf_spec.json ~/.openclaw/workspace/dais-x-feed-digest YYYY-MM-DD
```
make_cards.py は **`nano-banana` コマンド**(`-s 2K -a 3:2 -d`、fallback
`-m pro`)を直接。生 fal/bun-run/内蔵 image は不可
(memory: feedback_use_nano_banana_cli_directly)。

## 検証(HARD RULE #8) → 投稿
各5枚を model が Read: ①3ニュースが**独立モジュール+各ミニ図解**か
②混ざってない ③数値入り ④legible。NG→spec直し再生成。OK→
`slack_post.py <img> <cmt>` を5回 → conversations.history で5枚到達検証。

## 禁止
- grok/X API/x_search をソース化(RSSHub のみ＝Dais 決定)
- title だけ取る(全文 description 必須)
- 別ニュースを1相関図に混ぜる / 文字箱 / 浅い要約
- 生 fal/bun-run/内蔵 image / flux / SD / gpt-image-1
- クロス投稿(X/TikTok/IG)は当面しない(Slack のみ)
- DRY_RUN/fake 完了報告(実5枚+#metrics 実投稿+history 検証で証明)

## Cron
1回/日 **08:00 JST**(jobs.json `dais-x-feed-digest-daily`)
delivery=`none`。jobs.json 編集後 `openclaw gateway restart`。

## 実証
2026-05-19 Claude が nano-banana CLI + FRAME2 で ②AI entity を E2E:
RSSHub全文 → truth_terminal/Perplexity×Snowflake(PayPal週74,000)/
Perplexity安全基盤 を3独立ミニ図解 → Read 検証 → Dais 承認 →
#metrics 実投稿(file F0B4UC606CU)。旧「相関図混ぜ/文字箱/grok」は
廃止。本 recipe が exact way。
