---
name: latest-papers
description: "毎日 arXiv から AI/LLM/エージェント論文 3-4本を選び、各論文を『手法フロー図』に図解(FRAME1, nano-banana CLI)して Slack #metrics に投稿する"
metadata: {"openclaw":{"emoji":"📚","os":["darwin","linux"]}}
---

# latest-papers

## 目的
毎日その日の重要 AI/LLM/エージェント論文 3-4本を、**各論文 1つの手法
フロー図**(箱+矢印+アイコン)に図解して #metrics へ。文字箱・1行要約は
禁止(HARD RULE #13)。Dais はビジュアル理解者。

## アーキテクチャ（毎日変わる=model / 固定=script）
```
[1] script  arXiv RSS(cs.AI/CL/SE/LG)+クエリAPI 取得  ※キー不要
[2] model   3-4本選定・abstract【全文】を読む(毎日違う)
[3] model   /tmp/lp_spec.json 生成(FRAME1 schema・下記)
[4] script  scripts/make_card.py → nano-banana CLI で手法フロー図
[5] model   生成PNGを Read 検証(図か/legible/浅くないか)→NG[3-4]再走
[6] script  scripts/slack_post.py → #metrics + conversations.history検証
```

## ソース（arXiv のみ・キー不要。X/HF 恒久禁止）
```bash
for c in cs.AI cs.CL cs.SE cs.LG; do curl -sS -m20 "https://rss.arxiv.org/rss/$c"; done
curl -sS -m20 -A anicca/1.0 "https://export.arxiv.org/api/query?search_query=%28cat:cs.AI+OR+cat:cs.CL+OR+cat:cs.SE%29+AND+%28abs:%22LLM+agent%22+OR+abs:%22coding+agent%22+OR+abs:%22autonomous+agent%22+OR+abs:%22language+model%22%29&sortBy=submittedDate&sortOrder=descending&max_results=40"
```
model が領域(Claude Code/agent/LLM/推論/自律)関連で 3-4本に絞る。

## 必須 env / 役割分担
`FAL_KEY`, `SLACK_BOT_TOKEN`。推論(選定/abstract精読/spec作成/検証判断)
は model。script は arXiv取得/画像生成(nano-banana CLI)/投稿+到達検証のみ。

## /tmp/lp_spec.json（make_card.py が読む・**schema 固定**）
```json
{"date":"YYYY-MM-DD",
 "papers":[{"n":1,"title_en":"Code as Agent Harness (2605.18747)",
   "input":"コード","rel1":"推論","mechanism":"実行+検証",
   "rel2":"環境反映","result":"環境モデル","loop":true,
   "why":"なぜ重要/Aniccaへの含意を1文(数値あれば入れる)"}, ... 3-4 ...]}
```
各論文は手法を [input]-(rel1)->[mechanism]-(rel2)->[result] の流れに分解、
反復手法は `loop:true`。固有名詞は why で説明。**JSON 内に裸の " を入れない**。
`/tmp/lp_comment.txt` = 各論文4-6行(課題/手法/数値/なぜ)+ arXiv リンク。

## 画像生成（nano-banana CLI 直叩き・固定スクリプト）
```bash
python3 ~/.openclaw/skills/latest-papers/scripts/make_card.py \
  /tmp/lp_spec.json ~/.openclaw/workspace/latest-papers/lp_YYYY-MM-DD.png
```
make_card.py は **`nano-banana` コマンド**(`-s 2K -a 3:2 -d`、fallback
`-m pro`)を直接呼ぶ。生 fal API 直叩き/bun-run ラッパー/OpenClaw 内蔵
image ツールは使わない(memory: feedback_use_nano_banana_cli_directly)。

## 検証(HARD RULE #8) → 投稿
生成 PNG を model が Read: ①各論文が箱+矢印の**フロー図**になっているか
②日本語 legible ③図だけで「何の課題を・どう解き・なぜ重要か」分かるか。
NG → spec 簡潔化して再生成(最大3)。OK →
`python3 ~/.openclaw/skills/latest-papers/scripts/slack_post.py <png> /tmp/lp_comment.txt`
→ conversations.history で到達検証。`POSTED_OK ts=` 出るまで完了としない。

## 禁止
- X/HF/web_search をソース化 / abstract を読まず title だけで選定
- 文字箱・1行要約・体言止め(出力は手法フロー図が主役)
- 生 fal 直叩き / bun-run / 内蔵 image ツール / flux / SD / gpt-image-1
- DRY_RUN/fake 完了報告(実画像+#metrics 実投稿+history 検証で証明)

## Cron
1回/日 **06:55 JST**(jobs.json `latest-papers`) delivery=`none`。
jobs.json 編集後 `openclaw gateway restart`。

## 実証
2026-05-19 Claude が nano-banana CLI + FRAME1 で E2E: arXiv全文 →
Code as Agent Harness/SkillGenBench/Safe LLM Agent 3層 を手法フロー図化
→ Read 検証(箱+矢印+ループ・legible) → Dais 承認("looks pretty nice")
→ #metrics 実投稿(file F0B4UC4LMMJ)。浅い箱版は廃止。本 recipe が exact way。
