---
name: sao-content-factory
description: 毎日 07:05 JST。**その日の対象エージェントを1体だけ**選び、Firecrawl SEARCH でそのエージェントの【最新情報】を能動収集し、走るモデルが12ツイの深掘り X thread を書き、nano-banana で図解1枚を作り、JP/EN 2本を X (@aniccaxxx) に Postiz 下書きで投下する。1日1エージェント。動画なし・TikTok/IG/YT なし・X only。
---

# SAO Content Factory (firecrawl-SEARCH 駆動 / nano-banana 図 / JP+EN / X draft)

お前 = 走っているモデル。外部 LLM API は一切叩かない (HARD RULE #6)。
bash は deterministic 処理のみ (firecrawl, jq, curl, nano-banana CLI, postiz)。

> **2026-05-19 Dais 方針 (これが最新・上書き)**
> - **1日1エージェント深掘り**。1本のスレに Andon+Kelly+Polsia… を全部
>   詰め込むのは「情報過多で何も残らない」= 廃止。その日は **対象を1体だけ**
>   選び、そのエージェントだけを 12 ツイで濃く扱う (Anicca 接続は tweet 11 のみ)。
> - 旧「固定 entity を固定 source_blog で scrape」も **廃止** (毎週同じ紹介=
>   新情報ゼロ=読者離脱)。対象エージェントは **roster を日毎ローテ**するが、
>   中身は毎回 **Firecrawl SEARCH でそのエージェントの最新情報を能動探索**して書く
>   (固定文の使い回し禁止)。"どの1体か" はローテ、"中身" は常に fresh。
> - 動画は作らない (75秒 Remotion は slop 廃止)。TikTok/IG/YT に出さない。
>   **X only**、Postiz **type:"now"** (直接公開。Dais 2026-05-23)。
> - 画像 = nano-banana CLI (raw fal/flux 禁止)。JP と EN の2本を出す。

## STEP 1 — 今日の対象エージェントを1体選び、その最新情報だけ取る

### 1a. roster から今日の1体を決める (ローテ)

対象は **1日1体**。roster (随時追加可・新顔が出たら足す):

```
0 Andon Labs (Mona — Stockholm cafe)
1 Kelly (iamkelly — outbound AI)
2 Truth Terminal (memetic / crypto-native AI)
3 Light Anchor (signals AI)
4 Polsia (autonomous startup builder)
5 Anicca (Tokyo, 7 products — 自社。週1まで)
```

カーソル: `state/agent-cursor` (整数1行、無ければ 0)。
今日の index = `cursor mod (roster数)`。**ただし**:
- そのエージェントが直近3日で既出 (`state/processed-urls.jsonl` の
  `agent` フィールド) なら次の index へスキップ。
- どこかで「明らかに今ホットな1体」(大手メディア報道・新ラウンド・新数字)
  が firecrawl で見つかれば、その日はカーソル無視でそれを優先。
処理後 `state/agent-cursor` を `+1` して保存 (翌日は次の1体)。

### 1b. その1体の最新情報を Firecrawl SEARCH

選んだ 1 体について **そのエージェント名で** 検索し、
**直近 (7日以内目安) の新しい記事/発表/数字** を 1–3 本拾う。例 (対象=Andon):

```
firecrawl search "Andon Labs latest"
firecrawl search "Andon Labs Mona cafe revenue"
firecrawl search "Andon Labs news 2026"
```

道具: `firecrawl search "<query>"` → 候補 URL → `firecrawl scrape <url> markdown`
で本文取得。JS/Cloudflare で弱い時は agent-{{profile.lateness.stakeholders.channel}} / camofox-{{profile.lateness.stakeholders.channel}}(:9377)。

**重複排除 (必須)**: `state/processed-urls.jsonl` に既出 URL がある記事は捨てる。
今日使った URL は処理後 `{"url","date","agent","slug","en","jp"}` で append。
当日二重実行は `state/sao-<YYYY-MM-DD>.done` で防ぐ。
その1体の fresh 記事が皆無なら roster の次の1体にずらす
(それでも全滅なら、その1体の "現在地" を自分の最新知識で1本にまとめてよい。
固定文の使い回しは禁止 — X が重複拒否する)。

## STEP 2 — その1体を深掘りする 12ツイ X thread (お前が執筆)

**今日選んだ 1 体だけ** を濃く扱う。他のエージェントを並べて紹介しない
(名前が出るとしても比較の一言まで)。取った fresh 情報を核にした深掘り:
- tweet 1 = フック (🧵)。その1体の今日の新事実 + なぜ重要かを1行で。
- tweet 2–10 = **その1体の分解**: 何者か / 何をした(今週の数字・具体) /
  アーキテクチャ・運営方法 / 失敗・学び / なぜ今これが効くのか。各 ≤270字。
- tweet 11 = Anicca も同じ SAO カテゴリ、という接続 (1ツイのみ)。
- tweet 12 = CTA: aniccaai.com/fellows + github.com/Daisuke134/anicca。
書く前に `humanizer` (EN) を mental に通す。`$DRAFT_FILE_EN` に
JSON 配列 `[{"content":"..."}, ... 12個]` で保存。
同内容を `humanizer-ja` 視点で JP 12ツイに翻訳し `$DRAFT_FILE_JP` に保存。

## STEP 3 — nano-banana で図解を EN + JP 2枚 (両方・毎回)

Nano Banana 2 (CLI) は日本語を完璧に描く (2026-05-19 実証)。
**EN図と JP図を別々に生成する**(共有しない)。図も **その1体だけ** を主役に
した「ゼロ知識でも1枚で全部わかる」図 — そのエージェントの仕組み/今週の数字/
何をしたか を可視化 (SAO 全体の関係図ではない・箇条書きPowerPoint禁止・実ダイアグラム):

```bash
mkdir -p "$RUN_DIR"
# stall 対策: timeout 150s + 2回 retry。両方失敗で NO_FIG=1 → STEP4 は thread のみで進める。
cd ~/tools/nano-banana-2 && (set -a; . ~/.openclaw/.env; set +a; \
  for i in 1 2; do timeout 150 bun src/cli.ts "<EN infographic: ENGLISH title + 3-5 ENGLISH callouts + SAO relation map + aniccaai.com/fellows>" \
    -o sao_$(date +%Y%m%d)_en -s 2K -a 4:5 -d "$RUN_DIR" && break; \
    echo "[retry $i] nano-banana EN stalled, retrying"; done)
cd ~/tools/nano-banana-2 && (set -a; . ~/.openclaw/.env; set +a; \
  for i in 1 2; do timeout 150 bun src/cli.ts "縦4:5のクリーンなインフォグラフィック。日本語を正確に。<日本語タイトル + 3-5個の日本語ラベル吹き出し + SAO関係図 + aniccaai.com/fellows>。完璧に読める日本語、実ダイアグラム" \
    -o sao_$(date +%Y%m%d)_ja -s 2K -a 4:5 -d "$RUN_DIR" && break; \
    echo "[retry $i] nano-banana JP stalled, retrying"; done)

# fallback: 両方失敗なら NO_FIG=1 で STEP4 を画像無し thread のみで進める (fake せず明示)
EN_JPEG=$(ls "$RUN_DIR"/sao_*_en.jpeg 2>/dev/null | head -1)
JP_JPEG=$(ls "$RUN_DIR"/sao_*_ja.jpeg 2>/dev/null | head -1)
if [ -z "$EN_JPEG" ] && [ -z "$JP_JPEG" ]; then
  export NO_FIG=1
  echo "⚠ nano-banana 両方失敗 → NO_FIG=1: STEP4 は figure なしで thread のみ post draft (Slack に明示報告)"
fi
```
生成後 `Read` で **両方** 目視検証 (HARD RULE #8): EN 可読+正確 / JP
可読+正しい日本語 (文字化け/tofu なし)。NG はその言語だけ prompt 締めて再生成。
**NO_FIG=1 の時**: STEP4 で image upload を skip し thread だけ post draft → stdout/Slack に「⚠ figure 生成失敗・thread のみ draft」と明示 (fake/garbage 投稿しない・#14)。

## STEP 4 — X に JP/EN を Postiz 下書きで投下 (X only)

```bash
INT="cmm6d7m5703rwpr0yr5vtme3w"   # {{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}} X のみ
set -a; . ~/.openclaw/.env; set +a
upimg(){ /opt/homebrew/bin/postiz upload "$1" 2>&1 | sed -n '/^{/,$p'; }
ENJ=$(ls -t "$RUN_DIR"/sao_*_en.jpeg 2>/dev/null|head -1); JPJ=$(ls -t "$RUN_DIR"/sao_*_ja.jpeg 2>/dev/null|head -1)
EU=$(upimg "$ENJ"); EN_PATH=$(echo "$EU"|jq -r '.path//empty'); EN_ID=$(echo "$EU"|jq -r '.id//empty')
JU=$(upimg "$JPJ"); JP_PATH=$(echo "$JU"|jq -r '.path//empty'); JP_ID=$(echo "$JU"|jq -r '.id//empty')
post_draft(){  # $1 thread JSON, $2 ISO date, $3 img path, $4 img id
  jq -nc --arg i "$INT" --arg d "$2" --arg p "$3" --arg id "$4" --slurpfile tw "$1" \
   '{type:"now",date:$d,shortLink:false,tags:[],posts:[{integration:{id:$i},
     value:[ $tw[0]|to_entries[] | {content:.value.content,
       image:(if .key==0 then [{id:$id,path:$p}] else [] end)} ],
     settings:{__type:"x",who_can_reply_post:"everyone"}}]}' \
  | curl -sS -X POST https://api.postiz.com/public/v1/posts \
     -H "Authorization: $POSTIZ_API_KEY" -H "Content-Type: application/json" -d @-
}
NOW=$(date -u +%Y-%m-%dT%H:%M:%S.000Z)
LATER=$(date -u -v+5H +%Y-%m-%dT%H:%M:%S.000Z 2>/dev/null || date -u -d '+5 hours' +%Y-%m-%dT%H:%M:%S.000Z)
post_draft "$DRAFT_FILE_EN" "$NOW"   "$EN_PATH" "$EN_ID"   # EN thread + EN figure
post_draft "$DRAFT_FILE_JP" "$LATER" "$JP_PATH" "$JP_ID"   # JP thread + JP figure
```
`type:"now"` 禁止 / IG・TikTok・YT に出さない / publish gate なし
(draft は本質的に安全。Dais が Postiz で公開)。

## STEP 5 — 検証 + 後始末

- `postiz posts:list` で EN/JP 2 draft が `cmm6d7m5703rwpr0yr5vtme3w` に
  state=DRAFT で乗ったか、thread=12ツイ、tweet1 に図、を確認 (HARD RULE #8)。
  nano-banana jpeg を再度 `Read` して図が意図通りか確認。
- 使った URL を `state/processed-urls.jsonl` に append、
  `state/sao-<DATE>.done` を touch。
- 最終 stdout 1行 (cron 配送が #metrics へ):
  `✅ SAO drafted: EN=<postId> JP=<postId> fig=<file> src=<url>` /
  `❌ SAO FAILED: <理由>`

## やらないこと

- 外部 LLM API を叩かない (HARD RULE #6・お前がモデル)。
- **1スレに複数エージェントを詰め込まない** (1日1体・深掘り厳守)。
- 固定 source_blog / 固定文の使い回し (枯れる・X 重複拒否)。
  ※ "どの1体か" の roster ローテは OK、"中身" は毎回 fresh search。
- 動画生成 (ElevenLabs/Suno/Remotion)・TikTok/IG/YT 投稿・`type:"now"`。
- Slack に自分で投稿 (cron 配送がやる)。
- 旧 phases (02/03/03b/04 video, 00-run-daily) は使わない (legacy)。

## 環境変数 (`~/.openclaw/.env` から source)
`POSTIZ_API_KEY` (Postiz) / `GEMINI_API_KEY` (nano-banana) / `SLACK_*` (cron配送)
※ `RUN_DIR` = `~/.openclaw/skills/sao-content-factory/output/$(date +%Y-%m-%d)`、
  `DRAFT_FILE_EN`/`DRAFT_FILE_JP` = `$RUN_DIR/thread_{en,jp}.json` を自分で export。

## Spec 参照
`.cursor/plans/social-marketing-closed-loop-spec.md` (#46 — sao firecrawl-SEARCH rebuild)
