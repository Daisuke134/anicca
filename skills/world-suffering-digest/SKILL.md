---
name: world-suffering-digest
description: "毎朝『今 世界で人々が何に・どこで・どれだけ苦しんでいるか』を WorldMonitor の個別findings(main)+危機ニュース(sub)から実体化し、TOP3を因果フロー図に深掘り(FRAME3, nano-banana CLI)して Slack #metrics へ。Anicca が次に解きに行く苦しみの起点。(既存 suffering-detector=SAFE-T危機interrupt とは別物)"
metadata: {"openclaw":{"emoji":"🗺️","os":["darwin","linux"]}}
---

# world-suffering-digest

## 目的
Anicca は苦しみを終わらせる entity。毎朝「**今 世界で人々が実際に
何に・どこで・どれだけ苦しんでいるか**」を掴み、**TOP3を1件ずつ
因果フロー図(原因→現状→誰が/規模)+強度ゲージ**で深掘り。
※既存 `suffering-detector`(SAFE-T 危機 interrupt) とは別 skill・触らない。

## ★絶対の誤り（2026-05-19, Dais 激怒）
WorldMonitor の機能/ダッシュボードの**概要を要約しただけ**で
「人が何に苦しんでいるか」を書かなかった = 完全に誤り。findings を
1件ずつ実体(誰が/どこで/何人/何に)に展開。世界地図チョビ点も不可。

## ソース（main=WorldMonitor 個別findings / sub=危機ニュース）
| 役割 | ソース | 取り方 |
|------|--------|--------|
| MAIN | worldmonitor.app(地域別含む) | `scripts/fetch_worldmonitor.py` が個別 finding を**1件ずつ**抽出。概要要約は禁止 |
| SUB | 危機ニュース | model が上位 finding の語で `firecrawl scrape` し人数/規模を補強 |
キー不要・両方公開。

## アーキテクチャ（毎日=model / 固定=script）
```
[1] script  scripts/fetch_worldmonitor.py → 個別findings raw
[2] model   各 finding を実体化(何が/どこ/規模/人数)。SUB で数値補強
[3] model   OPIS(YLSS/DLES,心理的苦痛最広,強度重み)で TOP3 決定
[4] model   /tmp/sd_spec.json 生成(FRAME3 schema・下記)+ /tmp/sd_cmt.txt
[5] script  scripts/make_card.py → nano-banana CLI で TOP3深掘り図
[6] model   PNG を Read 検証(人が何に苦しむか+数値+図か)→NG[3-5]再走
[7] script  slack_post.py → #metrics + conversations.history検証
```

## 必須 env / 役割分担
`FAL_KEY`,`SLACK_BOT_TOKEN`(+firecrawl CLI)。推論(findings実体化/数値
補強/OPIS判定/TOP3決定/spec/検証)は model。script は WorldMonitor取得/
画像生成(nano-banana CLI)/投稿+到達検証のみ。

## /tmp/sd_spec.json（make_card.py が読む・**schema 固定**）
```json
{"date":"YYYY-MM-DD","top1_short":"アフガン 人道危機",
 "items":[{"rank":1,"place":"アフガニスタン","what":"人道危機",
   "level":"極度","cause":"政情不安+経済崩壊+支援縮小",
   "now":"食料・医療の供給途絶、冬の寒波と重複",
   "who_scale":"支援要 推定 数千万人規模",
   "source":"WorldMonitor: Afghanistan Instability Rising/CRITICAL"},
  ... 必ず3件・#1が最大 ...]}
```
各 item を [原因 cause]→[現状 now]→[誰が/規模 who_scale] の因果フロー
として書く。数値はでっち上げず SUB(危機ニュース)で取れた範囲を「推定」
明記で。**JSON 内に裸の " を入れない**。`/tmp/sd_cmt.txt`=各実数値+出典。

## 画像生成（nano-banana CLI 直叩き）
```bash
python3 ~/.openclaw/skills/world-suffering-digest/scripts/make_card.py \
  /tmp/sd_spec.json ~/.openclaw/workspace/world-suffering-digest/wsd_YYYY-MM-DD.png
```
make_card.py は **`nano-banana` コマンド**(`-s 2K -a 3:2 -d`、fallback
`-m pro`)を直接。生 fal/bun-run/内蔵 image は不可
(memory: feedback_use_nano_banana_cli_directly)。

## 検証(HARD RULE #8) → 投稿
PNG を model が Read: ①TOP3各々が **原因→現状→誰が/規模 の因果
フロー図**か ②強度ゲージあるか ③「人が何に苦しんでるか+場所+数値」
が出てるか(WorldMonitor概要要約に戻ってたら即作り直し) ④legible。
OK→ `~/.openclaw/skills/latest-papers/scripts/slack_post.py <png>
/tmp/sd_cmt.txt` → conversations.history で到達検証。

## 禁止
- WorldMonitor の機能/概要・要約を書く(★最大の誤り) / 世界地図チョビ点
- findings を実体(場所/人数/何に)に展開しない / 文字箱
- 生 fal/bun-run/内蔵 image / flux / SD / gpt-image-1
- 既存 `suffering-detector`(SAFE-T) skill/cron を触る
- DRY_RUN/fake 完了報告(実画像+#metrics 実投稿+history 検証で証明)

## Cron
1回/日 **07:30 JST**(jobs.json `world-suffering-digest-daily`)
delivery=`none`。jobs.json 編集後 `openclaw gateway restart`。

## 実証
2026-05-19 Claude が nano-banana CLI + FRAME3 で E2E: WorldMonitor
個別findings(Afghanistan/Gaza/Lebanon Instability) → 実体化 → OPIS で
TOP3 → 因果フロー図+強度ゲージ → Read 検証(地図でなく深掘り図・
legible) → Dais 承認。概要要約版は廃止。本 recipe が exact way。
