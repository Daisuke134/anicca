# Larry Bible 完全準拠 — パッチスペック

**Status:** v2 — batch-generator/cross-post 除外
**Date:** 2026-04-03
**Author:** Claude Code + ダイス

---

## 0. モデルパラメータ

| 項目 | 値 |
|------|-----|
| 正しいモデル名 | `anthropic/claude-sonnet-4-6` |
| 引用元 | 稼働中の slideshow-en-1 cron の `payload.model` 値 |

---

## 1. 罪テーブル（Bible vs 実態）

| # | Bible（聖書） | 今やってること | 🔴 罪 |
|---|-------------|--------------|------|
| 1 | daily-report 毎朝実行（EN 07:00, JA 06:30） | `larry-daily-report-en/ja` = disabled + sonnet-4-5 | フィードバックループ死亡 |
| 2 | strategy-updater 毎朝 05:00 | `larry-strategy-updater` = disabled + sonnet-4-5 | フック更新なし。同じフックを延々回してる |
| 3 | ReelFarm LOOP A（7日メトリクス→フック淘汰） | `reelfarm-metrics-loop` = disabled | ReelFarm フック自動改善停止 |
| 4 | 投稿時間 07:30/16:30/21:00 | EN: 09:30/15:30/18:30, JA: 09:00/15:00/18:00 | ゴールデンタイムを逃してる |
| 5 | config.json = SELF_ONLY + UPLOAD | config = PUBLIC_TO_EVERYONE + DIRECT_POST | config が Bible に反してる |
| 6 | 背景画像: clean | 全6 slideshow が darkAcademia 固定 | ダイスが clean に変えたい |
| 7 | slide 6 = CTA アプリ画像（Motto/Myself スタイル） | slide 6 も darkAcademia + テキストオーバーレイ | CTA が弱い |

**除外:**
- batch-generator（毎回 cron 内でリアルタイム生成する運用でOK）
- cross-post YouTube Shorts（不要）
- ReelFarm LOOP B（後日対応）

---

## 2. 全パッチ

### Patch 1: larry-daily-report-en/ja 有効化 + モデル更新

**ファイル:** `/Users/anicca/.openclaw/cron/jobs.json`

```bash
python3 -c "
import json; d=json.load(open('/Users/anicca/.openclaw/cron/jobs.json'))
for j in d['jobs']:
    if j.get('name') in ['larry-daily-report-en','larry-daily-report-ja']:
        j['enabled']=True; j['payload']['model']='anthropic/claude-sonnet-4-6'
        print(f'{j[\"name\"]}: ON + sonnet-4-6')
json.dump(d, open('/Users/anicca/.openclaw/cron/jobs.json','w'), indent=2, ensure_ascii=False)"
```

### Patch 2: larry-strategy-updater 有効化 + モデル更新

**ファイル:** `/Users/anicca/.openclaw/cron/jobs.json`

```bash
python3 -c "
import json; d=json.load(open('/Users/anicca/.openclaw/cron/jobs.json'))
for j in d['jobs']:
    if j.get('name')=='larry-strategy-updater':
        j['enabled']=True; j['payload']['model']='anthropic/claude-sonnet-4-6'
        print('strategy-updater: ON + sonnet-4-6')
json.dump(d, open('/Users/anicca/.openclaw/cron/jobs.json','w'), indent=2, ensure_ascii=False)"
```

### Patch 3: ReelFarm LOOP A 有効化

**ファイル:** `/Users/anicca/anicca-project/openclaw-skills/jobs.json`

LOOP A は `timeframe=7` で直近7日分を見る。毎日回しても7日ウィンドウで分析。style 変更は週1回のみ（スキルに明記）。

```bash
python3 -c "
import json; d=json.load(open('/Users/anicca/anicca-project/openclaw-skills/jobs.json'))
for j in d['jobs']:
    if j.get('id')=='reelfarm-metrics-loop':
        j['enabled']=True; print('reelfarm-metrics-loop: ON')
json.dump(d, open('/Users/anicca/anicca-project/openclaw-skills/jobs.json','w'), indent=2, ensure_ascii=False)"
```

### Patch 4: 投稿時間を Bible 準拠に変更

**ファイル:** `/Users/anicca/.openclaw/cron/jobs.json`

| cron | 今 | 変更後 |
|------|-----|--------|
| slideshow-ja-1 | 0 9 (09:00) | 0 7 (07:00) |
| slideshow-en-1 | 30 9 (09:30) | 30 7 (07:30) |
| slideshow-ja-2 | 0 15 (15:00) | 0 16 (16:00) |
| slideshow-en-2 | 30 15 (15:30) | 30 16 (16:30) |
| slideshow-ja-3 | 0 18 (18:00) | 0 21 (21:00) |
| slideshow-en-3 | 30 18 (18:30) | 30 21 (21:30) |

```bash
python3 -c "
import json; d=json.load(open('/Users/anicca/.openclaw/cron/jobs.json'))
m={'slideshow-ja-1':'0 7 * * *','slideshow-en-1':'30 7 * * *','slideshow-ja-2':'0 16 * * *','slideshow-en-2':'30 16 * * *','slideshow-ja-3':'0 21 * * *','slideshow-en-3':'30 21 * * *'}
for j in d['jobs']:
    n=j.get('name','')
    if n in m: old=j['schedule']['expr']; j['schedule']['expr']=m[n]; print(f'{n}: {old} → {m[n]}')
json.dump(d, open('/Users/anicca/.openclaw/cron/jobs.json','w'), indent=2, ensure_ascii=False)"
```

### Patch 5: config.json を Bible 準拠に修正

**ファイル:** `/Users/anicca/.openclaw/workspace/tiktok-marketing/config.json`

```bash
python3 -c "
import json; f='/Users/anicca/.openclaw/workspace/tiktok-marketing/config.json'; d=json.load(open(f))
d['posting']['privacyLevel']='SELF_ONLY'; d['posting']['contentPostingMethod']='UPLOAD'; d['posting']['autoAddMusic']='no'
json.dump(d, open(f,'w'), indent=2, ensure_ascii=False); print('DONE: SELF_ONLY + UPLOAD + no music')"
```

### Patch 6: 背景 darkAcademia → clean

**ファイル:** `/Users/anicca/.openclaw/cron/jobs.json`（6つの slideshow cron）

```bash
python3 -c "
import json; d=json.load(open('/Users/anicca/.openclaw/cron/jobs.json'))
for j in d['jobs']:
    if j.get('name','').startswith('slideshow-') and j.get('enabled'):
        j['payload']['message']=j['payload']['message'].replace('darkAcademia','clean')
        print(f'{j[\"name\"]}: darkAcademia → clean')
json.dump(d, open('/Users/anicca/.openclaw/cron/jobs.json','w'), indent=2, ensure_ascii=False)"
```

### Patch 7: CTA slide（slide 6）追加 — CTA画像生成後に実行

**ファイル:** `/Users/anicca/.openclaw/cron/jobs.json`（6つの slideshow cron）

```bash
python3 -c "
import json; d=json.load(open('/Users/anicca/.openclaw/cron/jobs.json'))
cta='''

### CTA Slide (Slide 6) — MANDATORY
Do NOT generate or overlay text on slide 6. Use the pre-made CTA image:
- en: cp ~/.openclaw/workspace/tiktok-marketing/assets/cta/anicca-cta-en.png to slide6.png
- ja: cp ~/.openclaw/workspace/tiktok-marketing/assets/cta/anicca-cta-ja.png to slide6.png
Skip ALL text overlay for slide 6.'''
for j in d['jobs']:
    if j.get('name','').startswith('slideshow-') and j.get('enabled') and 'CTA Slide' not in j['payload']['message']:
        j['payload']['message']+=cta; print(f'{j[\"name\"]}: CTA added')
json.dump(d, open('/Users/anicca/.openclaw/cron/jobs.json','w'), indent=2, ensure_ascii=False)"
```

---

## 3. 適用後の必須コマンド

```bash
openclaw gateway restart
```

---

## 4. CTA 画像生成手順

### Step 1: nanobanana インストール
```bash
clawhub install resciencelab/opc-skills@nanobanana
```

### Step 2: 背景画像生成（手+iPhone、画面は白）
```bash
export GEMINI_API_KEY=<key>

# Anicca（暖かい雰囲気）
python3 .agents/skills/nanobanana/scripts/generate.py \
  "Realistic photo from above, a young person's relaxed hand naturally holding an iPhone 15 Pro showing a plain white screen. Soft warm natural lighting from the left, slightly blurred cozy bedroom background with warm beige tones. Casual grip, slightly tilted toward camera. Shot from above at slight angle. Warm inviting peaceful atmosphere. No text, no watermarks, no logos." \
  -r 9:16 -o /tmp/anicca-cta-base.png -v

# Honne（ダークモード雰囲気）
python3 .agents/skills/nanobanana/scripts/generate.py \
  "Realistic photo from above, a young person's relaxed hand naturally holding an iPhone 15 Pro Space Black showing a plain dark screen. Soft moody lighting, slightly blurred aesthetic dark room background. Casual grip, slightly tilted toward camera. Shot from above at slight angle. Calm moody atmosphere. No text, no watermarks, no logos." \
  -r 9:16 -o /tmp/honne-cta-base.png -v
```

### Step 3: スクショを iPhone 画面に合成 + テキスト追加
```bash
mkdir -p ~/.openclaw/workspace/tiktok-marketing/assets/cta/

# Anicca EN
ffmpeg -y -i /tmp/anicca-cta-base.png \
  -i /Users/anicca/anicca-project/assets/card-screenshots/en/self_loathing_0.png \
  -filter_complex "[1:v]scale=280:600[screen];[0:v][screen]overlay=(W-280)/2:(H-600)/2-50[merged];[merged]drawtext=text='Anicca':fontfile=$HOME/Library/Fonts/TikTokSansDisplayBold.ttf:fontsize=72:fontcolor=white:borderw=3:bordercolor=black:x=(w-text_w)/2:y=h*0.08,drawtext=text='words that heal':fontfile=$HOME/Library/Fonts/TikTokSansDisplayBold.ttf:fontsize=36:fontcolor=white:borderw=2:bordercolor=black:x=(w-text_w)/2:y=h*0.14" \
  ~/.openclaw/workspace/tiktok-marketing/assets/cta/anicca-cta-en.png

# Anicca JA
ffmpeg -y -i /tmp/anicca-cta-base.png \
  -i /Users/anicca/anicca-project/assets/card-screenshots/ja/self_loathing_0.png \
  -filter_complex "[1:v]scale=280:600[screen];[0:v][screen]overlay=(W-280)/2:(H-600)/2-50[merged];[merged]drawtext=text='アニッチャ':fontfile=/System/Library/Fonts/ヒラギノ角ゴシック\ W7.ttc:fontsize=72:fontcolor=white:borderw=3:bordercolor=black:x=(w-text_w)/2:y=h*0.08,drawtext=text='心に響く言葉をいつもそばに':fontfile=/System/Library/Fonts/ヒラギノ角ゴシック\ W7.ttc:fontsize=32:fontcolor=white:borderw=2:bordercolor=black:x=(w-text_w)/2:y=h*0.14" \
  ~/.openclaw/workspace/tiktok-marketing/assets/cta/anicca-cta-ja.png
```

Honne 版は Honne のスクショパスが分かり次第、同じ手順で作る。

---

最終更新: 2026-04-03 v2
