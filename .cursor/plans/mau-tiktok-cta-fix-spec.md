# mau-tiktok パイプライン完全仕様 v7

**Status:** IN PROGRESS
**Date:** 2026-03-26
**Branch:** dev

---

## 概要

バイラル YouTube Shorts の最初3秒をフックとして使い、先延ばし防止 CTA 動画を結合して TikTok/YouTube/Instagram に自動投稿するパイプライン。

**原則:** Prayer Lock (mau-model.mov) を完全コピー。オリジナルゼロ。

```
最終投稿動画 (9秒):
┌──────────┐  ┌──────────────────┐
│ HOOK (3s) │ +│  CTA CLIP (6s)    │
│ バズ動画   │  │  Prayer Lock式    │
│ yt-dlp取得 │  │  Remotionレンダリング│
└──────────┘  └──────────────────┘
```

---

## 確定事項

| 項目 | 確定値 |
|------|--------|
| TikTok EN | `anicca.en7` (ID: `cmmtt62wq01lqn50yehk1f6dy`) |
| TikTok JA | `aniccajp6` (ID: `cmmytdj1101w1p30ytx8lj0fw`) |
| YouTube EN | `@anicca-ai` (ID: `cmmzukbkw04ulp30yfvijrwio`) |
| YouTube JA | JA専用 (ID: `cmn1oukj9012nnq0yqhouc3ib`) |
| Instagram EN | `anicca.ai` (ID: `cmmzzg2es0539p30ycb94ayx0`) |
| Instagram JA | `anicca.jp` (ID: `cmmzujxpa04ujp30yxqpg1vci`) |
| Cron | **4回/日** (08:00 / 08:15 / 17:00 / 17:15 JST) |
| 動画数 | **1本/cron** → 同じ1本を全プラットフォームに投稿 |
| CTA構造 | Prayer Lock式 2フェーズ（質問→VALUE PROP）、白帯400px + カード1520px |
| CTA尺 | **6秒**（Phase A 2s + Phase B 4s） |
| BGM | phonk/ロックイン系（`bgm_phonk_trimmed.mp3` 約4.9秒、ループ再生） |
| CTA再利用 | CTA動画は1回作ったら全動画で再利用。毎回作らない |

---

## Cron スケジュール（4回/日、既存cronと重複回避）

```
08:00  mau-tiktok-ja    ← TT aniccajp6 + IG anicca.jp + YT cmn1oukj9(JA)
08:15  mau-tiktok-en    ← TT anicca.en7 + IG anicca.ai + YT @anicca-ai
      --- 45分空き ---
09:00  slideshow-ja-1   ← (既存) TT anicca.jp2 + IG anicca.jp
09:30  slideshow-en-1   ← (既存) TT anicca.en + IG anicca.ai
12:00  reelclaw-ja-1    ← (既存) TT anicca.jp2 + IG anicca.jp + YT cmn1oukj9
12:30  reelclaw-en-1    ← (既存) TT anicca.en + IG anicca.ai + YT @anicca-ai
15:00  slideshow-ja-2   ← (既存) TT anicca.jp2 + IG anicca.jp
15:30  slideshow-en-2   ← (既存) TT anicca.en + IG anicca.ai
17:00  mau-tiktok-ja    ← TT aniccajp6 + IG anicca.jp + YT cmn1oukj9(JA)
17:15  mau-tiktok-en    ← TT anicca.en7 + IG anicca.ai + YT @anicca-ai
18:00  slideshow-ja-3   ← (既存) TT anicca.jp2 + IG anicca.jp
18:30  slideshow-en-3   ← (既存) TT anicca.en + IG anicca.ai
21:00  reelclaw-ja-2    ← (既存) TT anicca.jp2 + IG anicca.jp + YT cmn1oukj9
21:30  reelclaw-en-2    ← (既存) TT anicca.en + IG anicca.ai + YT @anicca-ai
```

### 投稿マトリクス

| Cron | 時間 | 動画 | TikTok | YouTube | Instagram | 投稿数 |
|------|------|------|--------|---------|-----------|--------|
| mau-ja morning | 08:00 | 1本 | aniccajp6 | cmn1oukj9(JA) | anicca.jp | 3 |
| mau-en morning | 08:15 | 1本 | anicca.en7 | @anicca-ai | anicca.ai | 3 |
| mau-ja evening | 17:00 | 1本 | aniccajp6 | cmn1oukj9(JA) | anicca.jp | 3 |
| mau-en evening | 17:15 | 1本 | anicca.en7 | @anicca-ai | anicca.ai | 3 |
| **日計** | | **4本** | | | | **12投稿/日** |

---

## フック取得

### クリエイター（確定）

| 言語 | クリエイター | URL | カテゴリ |
|------|-----------|-----|---------|
| EN | ZackD Films | `https://www.youtube.com/@ZackDFilms/shorts` | brainrot-comedy |
| JA | seeyou | `https://www.youtube.com/@seeyou_seeyou2/shorts` | brainrot-animation |

### スクレイプフロー

```
scrape-hooks.js --lang en --count 1
  → creators.json の EN クリエイター URL
  → yt-dlp で最新 Shorts をリスト
  → used_hooks.json にないものを1本 DL
  → hooks/raw/en/{creator}_{videoId}.mp4
  → used_hooks.json に追加
```

毎 cron で新しい1本。1日4本（EN 2 + JA 2）。

---

## CTA動画 v7 仕様（確定 — 白帯400px + カード1520px）

### 参考元: Prayer Lock YouTube Shorts フレーム分析

```
Prayer Lock 実物 (2本DL分析、1080x1920、各11.4s):

0-3s     バズフック（バイラルアニメ映像 + 字幕テキスト）
3-5.5s   背景画像フル画面 + 上部にテキスト直載せ
         "did you pray today bro??"
         フォント: ~80px、Bold、黒、テキスト幅=画面の78%
5.5-11s  背景画像フル画面 + 上部にテキスト直載せ
         "block your phone until you
          pray with 'prayer lock'
          (it's on the app store)"
         フォント: ~80px、Bold、黒、全行同じサイズ・同じ色
```

### Anicca CTA v7 確定レイアウト (6s = 180 frames @ 30fps)

**Option A のフォント（80px Bold Arial/ヒラギノ W8） + 白帯400px = 最終形。2本（EN + JA）のみ。**

```
白帯(400px) + カード(1520px) — 確定レイアウト
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ┌─────────────────────────────────────┐ ← y=0
  │██████████ 白帯 400px █████████████│
  │                                     │
  │  テキスト 80px Bold 黒              │
  │  Phase A: 1行 → y=160 (中央)       │
  │  Phase B: 3行 → y=60, y=150, y=240 │
  │                                     │
  ├─────────────────────────────────────┤ ← y=400
  │                                     │
  │  procrastination カード画像           │
  │  （1080x1520 エリアに scale+crop）    │
  │                                     │
  │                                     │
  └─────────────────────────────────────┘ ← y=1920
```

### フォント設定（確定 — 全Phase・全行で統一）

| 項目 | EN | JA |
|------|-----|-----|
| フォントファイル | `/System/Library/Fonts/Supplemental/Arial Bold.ttf` | `/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc` |
| サイズ | **80px** | **80px** |
| 色 | **黒 #000000** | **黒 #000000** |
| 揃え | 中央 `x=(w-tw)/2` | 中央 `x=(w-tw)/2` |

**全行同じサイズ・同じ色。ストアラインも同じ。グレー禁止。小さいフォント禁止。**
**EN は Arial Bold.ttf（standalone .ttf）。Helvetica.ttc は fontindex 非対応のため使わない。**

### CTA テキスト配置（確定 — 白帯400px内）

```
EN:
  Phase A (0-2s):  白帯400px 中央に1行
    y=160: "still procrastinating??"          80px bold black

  Phase B (2-6s):  白帯400px 内に3行
    y=60:  "stop procrastinating"             80px bold black
    y=150: "with 'anicca'"                    80px bold black
    y=240: "(it's on the app store)"          80px bold black
                                              ↑ アポストロフィはダブルクォートで囲んで回避

JA:
  Phase A (0-2s):  白帯400px 中央に1行
    y=160: "まだ先延ばし？"                     80px bold black

  Phase B (2-6s):  白帯400px 内に3行
    y=60:  "アニッチャが"                       80px bold black
    y=150: "先延ばしを通知してくれる"             80px bold black
    y=240: "(App Storeで公開中)"               80px bold black
```

### アポストロフィ バグ修正

**問題:** `'` は ffmpeg filtergraph のクォート開始文字。`it's` の `'` が後続パラメータをテキスト化する
**修正:** `textfile=` パラメータで外部ファイルから読み込み、filtergraph エスケープを完全回避

```bash
# ' を含むテキスト行は textfile で読み込む（MUST）
echo -n "with 'anicca'" > /tmp/cta_line3.txt
echo -n "(it's on the app store)" > /tmp/cta_line4.txt
# drawtext=textfile=/tmp/cta_line3.txt:fontsize=80:...
# drawtext=textfile=/tmp/cta_line4.txt:fontsize=80:...
```

### CTA アセット

| アセット | パス | サイズ |
|---------|------|--------|
| EN カード画像 | `/Users/anicca/anicca-project/assets/card-screenshots/en/procrastination_1.png` | 780x1688 |
| JA カード画像 | `/Users/anicca/Desktop/mau-tiktok-preview/new-ja/procrastination-jp.png` | 1179x2556 |
| BGM (トリム済) | `/Users/anicca/Desktop/mau-tiktok-preview/bgm_phonk_trimmed.mp3` | 4.94秒 |

### CTA 再利用用 JSON（v7 確定値）

```json
{
  "font": {
    "en": {
      "file": "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
      "name": "Arial Bold"
    },
    "ja": {
      "file": "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc",
      "name": "Hiragino Kaku Gothic Std W8"
    },
    "size": 80,
    "color": "black",
    "align": "center"
  },
  "layout": {
    "whiteBand": { "height": 400, "color": "white" },
    "cardArea": { "y": 400, "height": 1520 },
    "canvas": { "width": 1080, "height": 1920 }
  },
  "text": {
    "en": {
      "phaseA": { "lines": ["still procrastinating??"], "yPositions": [160] },
      "phaseB": { "lines": ["stop procrastinating", "with 'anicca'", "(it's on the app store)"], "yPositions": [60, 150, 240] }
    },
    "ja": {
      "phaseA": { "lines": ["まだ先延ばし？"], "yPositions": [160] },
      "phaseB": { "lines": ["アニッチャが", "先延ばしを通知してくれる", "(App Storeで公開中)"], "yPositions": [60, 150, 240] }
    }
  },
  "duration": { "phaseA": 2, "phaseB": 4, "total": 6, "fps": 30, "totalFrames": 180 },
  "bgm": "bgm_phonk_trimmed.mp3"
}
```

### 出力ファイル（確定 — 2本のみ）

| ファイル | 言語 |
|---------|------|
| `cta_en_final.mp4` | EN |
| `cta_ja_final.mp4` | JA |

### Remotion BP チェック (MUST)

| ルール | 対応 |
|--------|------|
| `useCurrentFrame()` のみ | MUST — CSS animation/transition 禁止 |
| `extrapolateRight: "clamp"` 全interpolate | MUST |
| `staticFile()` for assets | MUST |
| `<Img>` for images | MUST — native `<img>` 禁止 |
| `<Audio>` from `@remotion/media` | MUST — volume callback でフェード |
| `<Sequence>` + `premountFor` | MUST — Phase B 要素に適用 |
| `<Series>` for Phase A→B | MUST — overlap なし |
| Font: `@remotion/google-fonts` | MUST — Inter Bold (EN), Noto Sans JP Bold (JA)、subset指定 |
| No `<Video>` | MUST — 静止画 + テキスト + オーディオのみ |

### Green Zone テキスト配置

| プラットフォーム | 上部NG | 下部NG |
|---------------|--------|--------|
| TikTok | 上100px | 下280px |
| YouTube Shorts | 上80px | 下200px |
| Instagram Reels | 上60px | 下260px |
| **安全領域** | **上100px以下** | **下280px以上** |

白帯テキストは y=60〜240px（安全領域内、白帯が背景なので視認性も完璧）。

---

## パイプライン 4ステップ

### STEP 1: scrape-hooks.js

```bash
node scripts/scrape-hooks.js --lang en --count 1
node scripts/scrape-hooks.js --lang ja --count 1
```

- creators.json のクリエイター URL → yt-dlp で最新 Shorts 1本 DL
- used_hooks.json で重複防止
- 出力: `hooks/raw/{lang}/{creator}_{videoId}.mp4`

### STEP 2: trim-and-stitch.js

```bash
node scripts/trim-and-stitch.js --lang en --count 1
node scripts/trim-and-stitch.js --lang ja --count 1
```

1. フック動画を3秒にトリム (ffmpeg -t 3, 1080x1920, re-encode)
2. CTA動画と結合 (ffmpeg filter_complex concat, **-c copy 禁止 → re-encode 必須**、タイムスタンプずれ防止)
3. フック音声は3秒で終了、CTA部分は phonk BGM が流れる
4. 出力: `output/{lang}/mau_{lang}_{timestamp}.mp4` (9秒 = hook 3s + CTA 6s)

```bash
# MUST: filter_complex concat で re-encode（-c copy だと尺が11sになる）
ffmpeg -i hook_trimmed.mp4 -i cta_final.mp4 \
  -filter_complex "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]" \
  -map "[outv]" -map "[outa]" \
  -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p \
  -c:a aac -b:a 192k output.mp4
```

### STEP 3: post-to-postiz.js

```bash
node scripts/post-to-postiz.js --lang en
node scripts/post-to-postiz.js --lang ja
```

- output/{lang}/ の最新1本を Postiz API で投稿
- EN: 3プラットフォーム (TikTok + YouTube + Instagram)
- JA: 3プラットフォーム (TikTok + YouTube + Instagram)
- Postiz API: `Authorization: ${POSTIZ_API_KEY}` (Bearer prefix不要)
- Rate Limit: 30 req/hour → 1 cron で upload 1 + create 1 = 2 req

### STEP 4: cleanup

- used_hooks.json に URL 追加
- post-log.json に投稿記録
- output/ のファイルはオプションで削除（再投稿防止）

---

## Postiz API

| 項目 | 値 |
|------|-----|
| CLI | `/opt/homebrew/bin/postiz` v2.0.12 |
| API Key | `~/.config/mobileapp-builder/.env` → `POSTIZ_API_KEY` |
| Rate Limit | 30 req/hour |
| 認証 | `Authorization: ${POSTIZ_API_KEY}` (Bearer prefix不要) |
| 1回のcron消費 | upload 1 + create 3 = 4 req (各プラットフォーム別) |

### Postiz 投稿ルール（reelclaw 実績から — MUST）

**各プラットフォーム別リクエスト必須。1リクエストに複数プラットフォーム混ぜるな。**

```javascript
// TikTok MUST パラメータ
{
  privacy_level: "PUBLIC_TO_EVERYONE",
  content_posting_method: "DIRECT_POST",
  video_made_with_ai: false,
  autoAddMusic: "no",        // "yes" = BGM二重
  duet: true, stitch: true, comment: true,
  brand_content_toggle: false, brand_organic_toggle: false
}

// Instagram MUST パラメータ
{
  __type: "instagram-standalone",  // "instagram" だと失敗
  post_type: "reel",
  type: "now",
  tags: []                         // 空配列必須
}

// YouTube MUST パラメータ
{
  __type: "youtube",
  selfDeclaredMadeForKids: "no",
  privacy: "public",
  type: "now"
}
```

### 投稿先 Integration ID

| Lang | Platform | Account | Integration ID |
|------|----------|---------|----------------|
| EN | TikTok | anicca.en7 | `cmmtt62wq01lqn50yehk1f6dy` |
| EN | Instagram | anicca.ai | `cmmzzg2es0539p30ycb94ayx0` |
| EN | YouTube | @anicca-ai | `cmmzukbkw04ulp30yfvijrwio` |
| JA | TikTok | aniccajp6 | `cmmytdj1101w1p30ytx8lj0fw` |
| JA | Instagram | anicca.jp | `cmmzujxpa04ujp30yxqpg1vci` |
| JA | YouTube | JA専用 | `cmn1oukj9012nnq0yqhouc3ib` |

---

## スキル構造

```
~/.openclaw/skills/mau-tiktok/           ← OSS配布用
├── SKILL.md
├── scripts/
│   ├── scrape-hooks.js                   ← STEP 1
│   ├── trim-and-stitch.js                ← STEP 2
│   └── post-to-postiz.js                ← STEP 3
├── templates/
│   └── cta-video/                        ← Remotionプロジェクト
│       ├── src/Root.tsx
│       ├── src/compositions/CtaVideo.tsx
│       ├── public/
│       │   ├── anicca-icon.png
│       │   ├── procrastination_1_en.png
│       │   ├── procrastination-jp.png
│       │   └── bgm_phonk_final.mp3
│       └── package.json
├── config/
│   ├── creators-example.json
│   └── cta-props.json
└── references/
    ├── posting-targets.md
    └── creator-selection.md

~/.openclaw/workspace/mau-tiktok/         ← ランタイム（gitignore）
├── creators.json                         ← 実際のクリエイター設定
├── used_hooks.json                       ← 使用済みURL
├── post-log.json                         ← 投稿記録
├── config.json                           ← Postiz設定
├── cta/
│   ├── en/cta_en_final.mp4              ← v7 確定版
│   ├── ja/cta_ja_final.mp4              ← v7 確定版
│   └── *.norm.mp4                        ← 正規化済み
├── hooks/
│   ├── raw/{lang}/                       ← yt-dlp DL先
│   └── trimmed/{lang}/                   ← 3秒トリム済み
└── output/
    ├── en/mau_en_{ts}.mp4               ← 最終動画
    └── ja/mau_ja_{ts}.mp4
```

---

## creators.json（確定）

```json
{
  "creators": [
    { "name": "ZackD Films", "url": "https://www.youtube.com/@ZackDFilms/shorts", "lang": "en", "category": "brainrot-comedy" },
    { "name": "seeyou", "url": "https://www.youtube.com/@seeyou_seeyou2/shorts", "lang": "ja", "category": "brainrot-animation" }
  ]
}
```

**JA クリエイター: seeyou 確定済み。**

---

## 出力ルール

- **絶対に上書きしない。** バージョン付き
- CTA動画: `cta_{lang}_final.mp4`（v7確定版）
- stitched出力: `output/{lang}/mau_{lang}_{timestamp}.mp4`
- CTA動画は1回作ったら全動画で再利用（毎回レンダリングしない）

---

## To-Do

| # | タスク | 状態 |
|---|--------|------|
| 1 | BGM最終カット + トリム | ✅ 完了 |
| 2 | JA クリエイター確定（seeyou） | ✅ 完了 |
| 3 | Prayer Lock Shorts 分析 → CTA 構造確定 | ✅ 完了 |
| 4 | CTA v4-v6 試作（8本）→ ダイスレビュー | ✅ 完了 |
| 5 | CTA v7 確定（白帯400px + Arial Bold 80px + textfile apostrophe fix） | ✅ 完了 |
| 6 | CTA v7 最終動画（cta_en_final.mp4 + cta_ja_final.mp4） | ✅ 完了 |
| 7 | サンプル hook+CTA 結合 → EN/JA 完成品 (sample_full_en/ja.mp4) | ✅ 完了 |
| 8 | **ダイスが完成品を承認** | ✅ 完了 |
| 9 | creators.json 更新（ZackD + seeyou のみ） | ✅ 完了 |
| 10 | config.json 更新（YT JA + cron times + 1動画） | ✅ 完了 |
| 11 | CTA v7 ファイルをworkspaceにコピー | ✅ 完了 |
| 12 | scrape-hooks.js 修正（lang別ディレクトリ + count=1） | ✅ 完了 |
| 13 | trim-and-stitch.js リライト（filter_complex + v7 CTA） | ✅ 完了 |
| 14 | post-to-postiz.js 新規作成（reelclawテンプレート） | ✅ 完了 |
| 15 | SKILL.md v7 リライト | ✅ 完了 |
| 16 | jobs.json に4 cron + 1テストcron追加 | ✅ 完了 |
| 17 | `openclaw gateway restart` → テスト cron 実行 → 確認 | 🔜 次 |

---

## ffmpeg Gotcha（スキル実装時 MUST）

| # | 問題 | 修正 |
|---|------|------|
| 1 | `'` が filtergraph クォート開始文字と衝突 | `textfile=` でファイルから読み込み |
| 2 | Helvetica.ttc の `fontindex` 非対応 | Arial Bold.ttf (standalone .ttf) を使う |
| 3 | `-f concat -c copy` でタイムスタンプずれ (9s→11s) | `filter_complex concat` で re-encode |
| 4 | BGM 4.9s < CTA 6s で `-shortest` 切れ | `-stream_loop -1 -i bgm -t 6` |
| 5 | EN fontfile パスにスペース | `Arial\ Bold.ttf` でエスケープ |
| 6 | scrape-hooks.js が lang 別ディレクトリ未対応 | `hooks/raw/{lang}/` に保存するよう修正 |
| 7 | trim-and-stitch.js が古い CTA パス参照 | `cta_{lang}_final.mp4` に変更 |
| 8 | IG post_type が "post"（静止画用） | mau は動画 → `post_type: "reel"` に変更 |
| 9 | Postiz Auth header | Bearer なし。`Authorization: ${KEY}` で OK（reelclaw 実績） |
| 10 | YouTube privacy フィールド名 | `type: "public"` を使う（`privacy` ではない。reelclaw 実績） |

## Sonnet cron 実行ルール

| ルール | 理由 |
|--------|------|
| スクリプト3本を順に実行するだけ | Sonnet に判断させない。ロジックは全部スクリプト内 |
| SKILL.md に「NEVER modify scripts」明記 | Sonnet がスクリプトを書き換えるのを防止 |
| integration ID は config.json から読む | cron メッセージにハードコードしない |
| POSTIZ_API_KEY は .env から直接読む | Sonnet に環境変数を渡す必要なし |
| 各プラットフォーム別 API call | 1リクエストに混ぜると全失敗（reelclaw 実績） |
