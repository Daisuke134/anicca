# 動画04: 朝起きれない問題

## 基本情報

| 項目 | 詳細 |
|------|------|
| **タイトル（EN）** | "If you can't wake up on time, stop scrolling." |
| **タイトル（JP）** | 「朝起きれない人、スクロール止めて」 |
| **カテゴリ** | 問題提起・共感型（Pain Point Hook） |
| **尺** | 25-30秒 |
| **形式** | 縦動画 9:16 |
| **プラットフォーム** | TikTok, IG Reels, YT Shorts, X, Threads |
| **サムネイル/カバーテキスト** | "10 snoozes later..." / 「スヌーズ10回後…」 |
| **投稿ツール** | Buffer（一括予約投稿） |
| **編集ツール** | VEED |

---

## なぜこの動画が効果的か

1. **普遍的な悩み** - 朝起きられない人は非常に多い
2. **視覚的にわかりやすい** - スヌーズを押しまくる「あるある」を視覚化
3. **強い感情トリガー** - 遅刻の慌ただしさ、自己嫌悪を刺激
4. **Aniccaの機能に直結** - 起床Nudgeを自然に紹介できる
5. **起床は主要ユースケース** - Aniccaの最もわかりやすい価値提案

---

## 制作フロー（確定）

```
Step 1: Nano Banana で各シーンの「最初のフレーム」を生成
        ↓
Step 2: Kling で「画像→動画」機能を使い、動きを追加
        ↓
Step 3: VEED で複数クリップを結合、テキスト・音声追加
```

### なぜ「画像→動画」方式か

| 方式 | 採用 | 理由 |
|------|------|------|
| Text-to-Video（直接Kling） | ❌ | Klingが推測する部分が多く、結果が予測不可能 |
| Image-to-Video（Nano Banana → Kling） | ✅ | 最初のフレームを完全にコントロールでき、結果が予測可能 |

**ベストプラクティスからの引用:**
> "In this example, we first generated an image... that we then used as the starting frame of the video"
> "The start frame also plays an important role... most of the 'trick' is done through clever prompting"

---

## 秒数別構成

| 秒数 | シーン | 映像 | テキスト/音声 | 素材 |
|------|--------|------|--------------|------|
| **0-3秒** | フック | アラームが鳴る → スヌーズボタンを10回連打 | Hook: 「スヌーズ10回。まだ寝てる」 | Nano Banana → Kling |
| **3-8秒** | 問題深化 | 時計が6:00→7:00→7:30と進む | 「また遅刻する」 | Nano Banana → Kling |
| **8-15秒** | 慌てる | ベッドから飛び起きる、服を慌てて着る、鏡を見て疲れた顔 | 「1日が台無し」 | Nano Banana → Kling |
| **15-22秒** | 解決 | スマホにAnicca通知、穏やかな声「起きよう。今日の君は起きられる」 | Aniccaボイス: 「一緒に起きよう」 | Nano Banana → Kling + Talk画面スクショ |
| **22-27秒** | 変容 | 翌朝、7:00に自然に目覚める、伸びをする、笑顔 | 「7:00。自然に目覚めた」 | Nano Banana → Kling |
| **27-30秒** | CTA | Aniccaロゴ + Talk画面スクショ | EN「Mornings aren’t willpower. They’re systems.」/ JP「起きるのは意志じゃなくて仕組み。」 | Talk画面（実スクショ） |

---

## 素材リスト

### あなたが用意するもの
- [ ] Talk画面のスクショ

### AI生成するもの（Nano Banana + Kling）
- [ ] シーン1: スヌーズ連打シーン
- [ ] シーン2: 時計の時間経過
- [ ] シーン3: 慌てて起きるシーン
- [ ] シーン4: Anicca通知シーン
- [ ] シーン5: 自然に目覚めるシーン
- [ ] ロゴ + CTA画面

---

## Hookパターン

### 英語版
```
Primary: "If you can't wake up on time, stop scrolling."
Alternative 1: "10 snoozes later... still in bed."
Alternative 2: "This is why you're always late."
```

### 日本語版
```
Primary: 「朝起きれない人、スクロール止めて」
Alternative 1: 「スヌーズ10回。まだ寝てる」
Alternative 2: 「また遅刻するってわかってるのに」
```

---

## 投稿キャプション（オーガニック用テンプレ）

> **運用**: 1行目Hook（質問形推奨）+ 共感 + 価値提案 + CTA + ハッシュタグ3-5個

### 共通（日本語）
```
朝、スヌーズ10回押してない？

「明日こそ早く起きる」
って何百回言った？

起きるのは意志力じゃない。
仕組みの問題。

→ 保存して明日の朝見て。

#朝活 #早起き #睡眠改善 #生活習慣 #anicca
```

### 共通（英語）
```
Still hitting snooze 10 times?

"I'll wake up early tomorrow"
—how many times have you said that?

Mornings aren't about willpower.
They're about systems.

→ Save this. Check it tomorrow morning.

#morningroutine #wakeup #sleephacks #habits #anicca
```

---

## Buffer同時投稿設定

| プラットフォーム | 投稿時間（推奨） | 形式 |
|-----------------|----------------|------|
| TikTok | 20:00 JST / 7:00 EST | 動画 + キャプション |
| Instagram Reels | 20:00 JST / 7:00 EST | 動画 + キャプション |
| YouTube Shorts | 20:00 JST / 7:00 EST | 動画 + タイトル + 説明 |
| Threads | 20:00 JST / 7:00 EST | 動画 + 短文 |

---

## Nano Banana プロンプト（ベストプラクティス適用版）

> **重要**: awesome-nanobanana-pro + best-kling-prompt.md のベストプラクティスに基づいて構造化

### スライド1: スヌーズ連打（フック）

#### 英語版
```json
{
  "subject": {
    "primary": "Young Asian woman's hand repeatedly hitting the snooze button on an iPhone alarm",
    "secondary": "Phone screen showing alarm interface with snooze button",
    "action": "Hand hovering over snooze button, multiple tap motion blur"
  },
  "environment": {
    "setting": "Dark bedroom, early morning, minimal light",
    "time_of_day": "Early morning, 6:00-7:00 AM feel",
    "atmosphere": "Desperate, exhausted, stuck in sleep cycle"
  },
  "text_overlay": {
    "text": "10 snoozes. Still in bed.",
    "position": "Center of image",
    "style": "Bold white sans-serif text (Montserrat or Inter), large readable font, dark shadow for contrast against dark background"
  },
  "photography": {
    "composition": "Close-up on phone and hand, eye-level, 4:5 vertical (Instagram carousel)",
    "lens": "50mm prime lens equivalent",
    "aperture": "f/2.0 for shallow depth of field",
    "focus": "Sharp on phone screen and hand, soft bokeh on background",
    "lighting": {
      "type": "Harsh blue-white light from phone screen only",
      "color_temperature": "Cool 6000K phone glow",
      "quality": "Harsh, unflattering, creates shadows on hand"
    }
  },
  "style": {
    "aesthetic": "Cinematic, realistic, documentary feel",
    "color_palette": "Dark blues, harsh phone light, deep shadows",
    "mood": "Desperate, exhausted, relatable struggle"
  },
  "negative": [
    "Bright room lighting",
    "Happy or energetic expression",
    "Digital artifacts",
    "Illegible or blurry text"
  ]
}
```

#### 日本語版
```json
{
  "subject": {
    "primary": "Young Asian woman's hand repeatedly hitting the snooze button on an iPhone alarm",
    "secondary": "Phone screen showing alarm interface with snooze button",
    "action": "Hand hovering over snooze button, multiple tap motion blur"
  },
  "environment": {
    "setting": "Dark bedroom, early morning, minimal light",
    "time_of_day": "Early morning, 6:00-7:00 AM feel",
    "atmosphere": "Desperate, exhausted, stuck in sleep cycle"
  },
  "text_overlay": {
    "text": "スヌーズ10回。まだ寝てる",
    "position": "Center of image",
    "style": "Bold white sans-serif text (Noto Sans JP or Hiragino), large readable font, dark shadow for contrast against dark background"
  },
  "photography": {
    "composition": "Close-up on phone and hand, eye-level, 4:5 vertical (Instagram carousel)",
    "lens": "50mm prime lens equivalent",
    "aperture": "f/2.0 for shallow depth of field",
    "focus": "Sharp on phone screen and hand, soft bokeh on background",
    "lighting": {
      "type": "Harsh blue-white light from phone screen only",
      "color_temperature": "Cool 6000K phone glow",
      "quality": "Harsh, unflattering, creates shadows on hand"
    }
  },
  "style": {
    "aesthetic": "Cinematic, realistic, documentary feel",
    "color_palette": "Dark blues, harsh phone light, deep shadows",
    "mood": "Desperate, exhausted, relatable struggle"
  },
  "negative": [
    "Bright room lighting",
    "Happy or energetic expression",
    "Digital artifacts",
    "Illegible or blurry text"
  ]
}
```
**添付:** なし（このシーンが顔参照のベースになる）

---

### スライド2: 時計の時間経過（問題深化）

#### 英語版
```json
{
  "face_preservation": {
    "instruction": "Use the uploaded reference image for the character's face and appearance",
    "preserve_original": true,
    "reference_match": true
  },
  "subject": {
    "primary": "Analog wall clock showing 7:30 AM",
    "secondary": "Same young Asian woman still sleeping in bed, barely visible in soft focus background",
    "clock_details": "Clock face visible, hands pointing to 7:30"
  },
  "environment": {
    "setting": "Same bedroom, morning light beginning to filter through curtains",
    "time_of_day": "Late morning, 7:30 AM",
    "atmosphere": "Time passing, urgency building, missed opportunity"
  },
  "text_overlay": {
    "text": "Late again.",
    "position": "Center of image",
    "style": "Bold white sans-serif text (Montserrat or Inter), large readable font, dark shadow for contrast"
  },
  "photography": {
    "composition": "Close-up on clock in foreground, woman soft in background, 4:5 vertical (Instagram carousel)",
    "lens": "50mm prime",
    "aperture": "f/1.8 for strong bokeh",
    "focus": "Clock sharp, woman recognizable but soft",
    "depth_of_field": "Very shallow—creates emotional separation"
  },
  "style": {
    "aesthetic": "Cinematic, melancholic, time-lapse feel",
    "color_palette": "Warm morning tones beginning, but muted",
    "lighting": "Soft morning light through curtains, clock in shadow",
    "mood": "Urgency, regret, time slipping away"
  },
  "negative": [
    "Digital clock (use analog for visual appeal)",
    "Bright cheerful lighting",
    "Woman looking awake or alert",
    "Illegible or blurry text"
  ]
}
```

#### 日本語版
```json
{
  "face_preservation": {
    "instruction": "Use the uploaded reference image for the character's face and appearance",
    "preserve_original": true,
    "reference_match": true
  },
  "subject": {
    "primary": "Analog wall clock showing 7:30 AM",
    "secondary": "Same young Asian woman still sleeping in bed, barely visible in soft focus background",
    "clock_details": "Clock face visible, hands pointing to 7:30"
  },
  "environment": {
    "setting": "Same bedroom, morning light beginning to filter through curtains",
    "time_of_day": "Late morning, 7:30 AM",
    "atmosphere": "Time passing, urgency building, missed opportunity"
  },
  "text_overlay": {
    "text": "また遅刻する",
    "position": "Center of image",
    "style": "Bold white sans-serif text (Noto Sans JP or Hiragino), large readable font, dark shadow for contrast"
  },
  "photography": {
    "composition": "Close-up on clock in foreground, woman soft in background, 4:5 vertical (Instagram carousel)",
    "lens": "50mm prime",
    "aperture": "f/1.8 for strong bokeh",
    "focus": "Clock sharp, woman recognizable but soft",
    "depth_of_field": "Very shallow—creates emotional separation"
  },
  "style": {
    "aesthetic": "Cinematic, melancholic, time-lapse feel",
    "color_palette": "Warm morning tones beginning, but muted",
    "lighting": "Soft morning light through curtains, clock in shadow",
    "mood": "Urgency, regret, time slipping away"
  },
  "negative": [
    "Digital clock (use analog for visual appeal)",
    "Bright cheerful lighting",
    "Woman looking awake or alert",
    "Illegible or blurry text"
  ]
}
```
**添付:** スライド1で生成した画像（顔参照用）

---

### スライド3: 慌てて起きる（問題深化）

#### 英語版
```json
{
  "face_preservation": {
    "instruction": "Use the uploaded reference image for the character's face and appearance",
    "preserve_original": true,
    "reference_match": true
  },
  "subject": {
    "primary": "Same young Asian woman bolting upright in bed, panicked expression",
    "pose": "Sitting up quickly, hair messy, eyes wide with alarm",
    "expression": "Panic, regret, self-disappointment",
    "body_language": "Tense shoulders, hurried movements"
  },
  "wardrobe": {
    "clothing": "Pajamas or sleepwear, disheveled",
    "hair": "Messy, unkempt, bedhead"
  },
  "environment": {
    "setting": "Same bedroom, now brighter with morning light",
    "lighting_sources": ["Harsh morning sunlight through window", "Overhead light turned on"],
    "time_of_day": "Late morning, 7:30-8:00 AM",
    "atmosphere": "Chaos, panic, day ruined"
  },
  "text_overlay": {
    "text": "Day ruined.",
    "position": "Center of image",
    "style": "Bold white sans-serif text (Montserrat or Inter), large readable font, dark shadow for contrast"
  },
  "photography": {
    "composition": "Medium shot, eye-level, 4:5 vertical (Instagram carousel)",
    "lens": "35mm wide",
    "aperture": "f/2.8",
    "lighting": {
      "type": "Harsh morning light",
      "key_light": "Bright sunlight from window, camera-right",
      "fill": "Overhead light creating unflattering shadows",
      "contrast": "High contrast, harsh shadows under eyes"
    }
  },
  "style": {
    "aesthetic": "Cinematic, realistic, documentary",
    "color_palette": "Harsh whites, cool morning tones, unflattering",
    "mood": "Chaos, panic, self-disappointment"
  },
  "negative": [
    "Soft or flattering lighting",
    "Calm or peaceful expression",
    "Neat appearance",
    "Happy or energetic mood",
    "Illegible or blurry text"
  ]
}
```

#### 日本語版
```json
{
  "face_preservation": {
    "instruction": "Use the uploaded reference image for the character's face and appearance",
    "preserve_original": true,
    "reference_match": true
  },
  "subject": {
    "primary": "Same young Asian woman bolting upright in bed, panicked expression",
    "pose": "Sitting up quickly, hair messy, eyes wide with alarm",
    "expression": "Panic, regret, self-disappointment",
    "body_language": "Tense shoulders, hurried movements"
  },
  "wardrobe": {
    "clothing": "Pajamas or sleepwear, disheveled",
    "hair": "Messy, unkempt, bedhead"
  },
  "environment": {
    "setting": "Same bedroom, now brighter with morning light",
    "lighting_sources": ["Harsh morning sunlight through window", "Overhead light turned on"],
    "time_of_day": "Late morning, 7:30-8:00 AM",
    "atmosphere": "Chaos, panic, day ruined"
  },
  "text_overlay": {
    "text": "1日が台無し",
    "position": "Center of image",
    "style": "Bold white sans-serif text (Noto Sans JP or Hiragino), large readable font, dark shadow for contrast"
  },
  "photography": {
    "composition": "Medium shot, eye-level, 4:5 vertical (Instagram carousel)",
    "lens": "35mm wide",
    "aperture": "f/2.8",
    "lighting": {
      "type": "Harsh morning light",
      "key_light": "Bright sunlight from window, camera-right",
      "fill": "Overhead light creating unflattering shadows",
      "contrast": "High contrast, harsh shadows under eyes"
    }
  },
  "style": {
    "aesthetic": "Cinematic, realistic, documentary",
    "color_palette": "Harsh whites, cool morning tones, unflattering",
    "mood": "Chaos, panic, self-disappointment"
  },
  "negative": [
    "Soft or flattering lighting",
    "Calm or peaceful expression",
    "Neat appearance",
    "Happy or energetic mood",
    "Illegible or blurry text"
  ]
}
```
**添付:** スライド1で生成した画像（顔参照用）

---

### スライド4: Anicca通知（解決）

#### 英語版
```json
{
  "face_preservation": {
    "instruction": "Use the FIRST uploaded image as reference for the character's face and appearance. The phone screen displays the app interface from the SECOND uploaded image.",
    "preserve_original": true,
    "reference_match": true
  },
  "subject": {
    "primary": "Same young Asian woman lying in bed, propped on pillow, looking at phone with gentle smile",
    "secondary": "iPhone displaying Anicca app Talk screen interface (from second reference image)",
    "expression": "Hopeful, gentle smile, curious",
    "pose": "Lying on side, phone held at face level, relaxed but engaged"
  },
  "phone_screen": {
    "display": "Anicca app Talk screen interface exactly as shown in reference image",
    "glow": "Soft warm glow from screen illuminating her face",
    "position": "Phone angled toward camera so screen is partially visible"
  },
  "environment": {
    "setting": "Same bedroom, early morning",
    "time_of_day": "Early morning, 6:30-7:00 AM, golden hour beginning",
    "lighting": "Soft golden morning light streaming through sheer curtains",
    "atmosphere": "Hope, new beginning, warmth"
  },
  "text_overlay": {
    "text": "\"Let's wake up together.\"",
    "position": "Center of image",
    "style": "Bold white sans-serif text (Montserrat or Inter), large readable font, warm subtle shadow, quotation marks for voice feel"
  },
  "photography": {
    "composition": "Medium close-up, eye level, intimate, 4:5 vertical (Instagram carousel)",
    "lens": "50mm prime",
    "aperture": "f/2.0",
    "lighting": {
      "type": "Natural golden hour",
      "key_light": "Warm sunlight from window, camera-left",
      "fill": "Soft bounce from white bedding",
      "phone_light": "Subtle warm glow on face from screen"
    },
    "color_temperature": "Warm 4500K morning light"
  },
  "style": {
    "aesthetic": "Cinematic, hopeful, aspirational",
    "color_palette": "Warm golds, soft whites, gentle contrast",
    "mood": "Turning point, hope, connection",
    "film_tone": "Slightly lifted shadows, warm highlights"
  },
  "negative": [
    "Dark or moody lighting",
    "Sad or frustrated expression",
    "Harsh phone screen glare",
    "Messy or cluttered room",
    "Illegible or blurry text"
  ]
}
```

#### 日本語版
```json
{
  "face_preservation": {
    "instruction": "Use the FIRST uploaded image as reference for the character's face and appearance. The phone screen displays the app interface from the SECOND uploaded image.",
    "preserve_original": true,
    "reference_match": true
  },
  "subject": {
    "primary": "Same young Asian woman lying in bed, propped on pillow, looking at phone with gentle smile",
    "secondary": "iPhone displaying Anicca app Talk screen interface (from second reference image)",
    "expression": "Hopeful, gentle smile, curious",
    "pose": "Lying on side, phone held at face level, relaxed but engaged"
  },
  "phone_screen": {
    "display": "Anicca app Talk screen interface exactly as shown in reference image",
    "glow": "Soft warm glow from screen illuminating her face",
    "position": "Phone angled toward camera so screen is partially visible"
  },
  "environment": {
    "setting": "Same bedroom, early morning",
    "time_of_day": "Early morning, 6:30-7:00 AM, golden hour beginning",
    "lighting": "Soft golden morning light streaming through sheer curtains",
    "atmosphere": "Hope, new beginning, warmth"
  },
  "text_overlay": {
    "text": "「一緒に起きよう」",
    "position": "Center of image",
    "style": "Bold white sans-serif text (Noto Sans JP or Hiragino), large readable font, warm subtle shadow, Japanese quotation marks for voice feel"
  },
  "photography": {
    "composition": "Medium close-up, eye level, intimate, 4:5 vertical (Instagram carousel)",
    "lens": "50mm prime",
    "aperture": "f/2.0",
    "lighting": {
      "type": "Natural golden hour",
      "key_light": "Warm sunlight from window, camera-left",
      "fill": "Soft bounce from white bedding",
      "phone_light": "Subtle warm glow on face from screen"
    },
    "color_temperature": "Warm 4500K morning light"
  },
  "style": {
    "aesthetic": "Cinematic, hopeful, aspirational",
    "color_palette": "Warm golds, soft whites, gentle contrast",
    "mood": "Turning point, hope, connection",
    "film_tone": "Slightly lifted shadows, warm highlights"
  },
  "negative": [
    "Dark or moody lighting",
    "Sad or frustrated expression",
    "Harsh phone screen glare",
    "Messy or cluttered room",
    "Illegible or blurry text"
  ]
}
```
**添付:** 
1. スライド1で生成した画像（顔参照用）
2. Anicca Talk画面スクリーンショット（画面表示用）

---

### スライド5: 自然に目覚める（変容）

#### 英語版
```json
{
  "face_preservation": {
    "instruction": "Use the uploaded reference image for the character's face and appearance",
    "preserve_original": true,
    "reference_match": true
  },
  "subject": {
    "primary": "Same young Asian woman waking up naturally, stretching with arms raised",
    "expression": "Peaceful smile, eyes gently opening, refreshed",
    "body_language": "Relaxed stretch, open posture, contentment",
    "pose": "Lying in bed, stretching upward, taking a deep breath"
  },
  "wardrobe": {
    "clothing": "Clean sleepwear, hair neat",
    "appearance": "Well-rested, refreshed look vs earlier scenes"
  },
  "environment": {
    "setting": "Same bedroom, but now peaceful and tidy",
    "time_of_day": "Early morning, 7:00 AM, bright golden hour",
    "lighting": "Warm golden sunlight streaming through window",
    "atmosphere": "Peace, transformation, achievement"
  },
  "text_overlay": {
    "text": "7:00 AM. Naturally awake.",
    "position": "Center of image",
    "style": "Bold white sans-serif text (Montserrat or Inter), large readable font, warm subtle shadow"
  },
  "photography": {
    "composition": "Medium shot, eye level, 4:5 vertical (Instagram carousel)",
    "lens": "50mm prime",
    "aperture": "f/2.0",
    "lighting": {
      "type": "Bright golden hour flooding room",
      "quality": "Warm, uplifting, high-key",
      "direction": "Backlit from window creating rim light on woman"
    }
  },
  "style": {
    "aesthetic": "Cinematic, aspirational, triumphant",
    "color_palette": "Warm golds, bright whites, high saturation vs earlier muted tones",
    "mood": "Victory, transformation, peace",
    "contrast_to_slide_1": "Same bedroom but opposite emotion"
  },
  "negative": [
    "Dark or moody lighting",
    "Panic or stress",
    "Messy room",
    "Tired or exhausted expression",
    "Illegible or blurry text"
  ]
}
```

#### 日本語版
```json
{
  "face_preservation": {
    "instruction": "Use the uploaded reference image for the character's face and appearance",
    "preserve_original": true,
    "reference_match": true
  },
  "subject": {
    "primary": "Same young Asian woman waking up naturally, stretching with arms raised",
    "expression": "Peaceful smile, eyes gently opening, refreshed",
    "body_language": "Relaxed stretch, open posture, contentment",
    "pose": "Lying in bed, stretching upward, taking a deep breath"
  },
  "wardrobe": {
    "clothing": "Clean sleepwear, hair neat",
    "appearance": "Well-rested, refreshed look vs earlier scenes"
  },
  "environment": {
    "setting": "Same bedroom, but now peaceful and tidy",
    "time_of_day": "Early morning, 7:00 AM, bright golden hour",
    "lighting": "Warm golden sunlight streaming through window",
    "atmosphere": "Peace, transformation, achievement"
  },
  "text_overlay": {
    "text": "7:00。自然に目覚めた",
    "position": "Center of image",
    "style": "Bold white sans-serif text (Noto Sans JP or Hiragino), large readable font, warm subtle shadow"
  },
  "photography": {
    "composition": "Medium shot, eye level, 4:5 vertical (Instagram carousel)",
    "lens": "50mm prime",
    "aperture": "f/2.0",
    "lighting": {
      "type": "Bright golden hour flooding room",
      "quality": "Warm, uplifting, high-key",
      "direction": "Backlit from window creating rim light on woman"
    }
  },
  "style": {
    "aesthetic": "Cinematic, aspirational, triumphant",
    "color_palette": "Warm golds, bright whites, high saturation vs earlier muted tones",
    "mood": "Victory, transformation, peace",
    "contrast_to_slide_1": "Same bedroom but opposite emotion"
  },
  "negative": [
    "Dark or moody lighting",
    "Panic or stress",
    "Messy room",
    "Tired or exhausted expression",
    "Illegible or blurry text"
  ]
}
```
**添付:** スライド1で生成した画像（顔参照用）

---

### スライド6: CTA

#### 英語版
```json
{
  "subject": {
    "primary": "Anicca app logo and Talk screen interface",
    "secondary": "Warm, inviting background with soft golden light",
    "layout": "Logo centered at top, app screenshot below, CTA text at bottom"
  },
  "environment": {
    "setting": "Simple solid warm background",
    "color_scheme": "Solid warm gold or soft orange",
    "atmosphere": "Hopeful, inviting, call to action"
  },
  "text_overlay": {
    "text": "Mornings aren't willpower.\nThey're systems.\n\nTry Anicca",
    "position": "Center of image",
    "style": "Bold white sans-serif text (Montserrat or Inter), large readable font, warm subtle shadow, 'Try Anicca' slightly larger as CTA"
  },
  "visual_elements": {
    "logo": "Anicca logo prominently displayed",
    "app_screenshot": "Talk screen interface from reference image"
  },
  "photography": {
    "composition": "Centered, balanced, 4:5 vertical (Instagram carousel)",
    "style": "Clean, modern, app marketing aesthetic"
  },
  "style": {
    "aesthetic": "Ultra minimalist, clean, aspirational",
    "color_palette": "Solid warm gold background, white text",
    "mood": "Invitation, hope, new beginning"
  },
  "negative": [
    "Dark or moody colors",
    "Cluttered layout",
    "Hard to read text",
    "Complex gradients or patterns"
  ]
}
```

#### 日本語版
```json
{
  "subject": {
    "primary": "Anicca app logo and Talk screen interface",
    "secondary": "Warm, inviting background with soft golden light",
    "layout": "Logo centered at top, app screenshot below, CTA text at bottom"
  },
  "environment": {
    "setting": "Simple solid warm background",
    "color_scheme": "Solid warm gold or soft orange",
    "atmosphere": "Hopeful, inviting, call to action"
  },
  "text_overlay": {
    "text": "起きるのは意志じゃなくて仕組み。\n\nTry Anicca",
    "position": "Center of image",
    "style": "Bold white sans-serif text (Noto Sans JP or Hiragino), large readable font, warm subtle shadow, 'Try Anicca' slightly larger as CTA"
  },
  "visual_elements": {
    "logo": "Anicca logo prominently displayed",
    "app_screenshot": "Talk screen interface from reference image"
  },
  "photography": {
    "composition": "Centered, balanced, 4:5 vertical (Instagram carousel)",
    "style": "Clean, modern, app marketing aesthetic"
  },
  "style": {
    "aesthetic": "Ultra minimalist, clean, aspirational",
    "color_palette": "Solid warm gold background, white text",
    "mood": "Invitation, hope, new beginning"
  },
  "negative": [
    "Dark or moody colors",
    "Cluttered layout",
    "Hard to read text",
    "Complex gradients or patterns"
  ]
}
```
**添付:** Anicca Talk画面スクリーンショット

---

## Kling プロンプト（ベストプラクティス適用版）

> **注意**: このファイルはカルーセル（静止画）として投稿するため、Klingプロンプトは参考用です。動画版を制作する場合に使用してください。

> **重要**: best-kling-prompt.md に基づいて **Subject + Action + Context + Style** の4要素 + **Narrative Intent（なぜこのカメラ動きか）** を明記

### シーン1: スヌーズ連打（0-3秒）

```
SUBJECT: A young Asian woman's hand repeatedly hitting the snooze button on an iPhone alarm.

ACTION: The hand moves quickly and desperately, tapping the snooze button 10 times in rapid succession. Each tap is quick and urgent. The phone screen briefly lights up with each tap, then dims. The hand movements become slightly slower and more tired with each tap, showing exhaustion.

CONTEXT: Dark bedroom, early morning. The only light source is the harsh blue-white glow from the phone screen. The woman is still sleeping, barely visible in the background.

STYLE: Cinematic, realistic, documentary feel. Harsh phone light creates unflattering shadows. Dark, moody color palette.

CAMERA: Static locked shot. No camera movement. The stillness emphasizes the repetitive, desperate nature of the snooze button taps—the viewer's attention is fully on the hand's futile struggle.

LENS: 50mm equivalent, f/2.0 shallow depth of field.

MOTION SPECIFICS: Only the hand moves. Phone and background are completely static. Hand taps are rapid (0.1s per tap for first 5 taps), then slightly slower (0.15s per tap for last 5 taps) showing increasing exhaustion. Phone screen lights up briefly with each tap.
```
**入力画像:** Nano Bananaで生成したシーン1画像
**Duration:** 3秒

---

### シーン2: 時計の時間経過（3-8秒）

```
SUBJECT: An analog wall clock showing time progression. The same young Asian woman still sleeping in bed, barely visible in soft focus background.

ACTION: The clock hands move forward smoothly from 6:00 → 7:00 → 7:30. The minute hand moves continuously, the hour hand shifts gradually. In the background, the woman remains completely motionless, still deeply asleep. The morning light slowly brightens through the window.

CONTEXT: Same bedroom, morning light beginning to filter through curtains. Time is passing, urgency is building.

STYLE: Cinematic, melancholic, time-lapse feel. Warm morning tones beginning, but muted. Soft shadows.

CAMERA: Static shot with split focus—clock sharp in foreground, woman soft but recognizable in background. The stillness of the camera on the clock emphasizes the relentless passage of time—the viewer watches time slip away.

LENS: 50mm equivalent, f/1.8 for strong bokeh separation.

MOTION SPECIFICS: Clock hands move smoothly (continuous motion over 5s). Woman in background is completely still. Morning light gradually brightens (subtle change). No other movement.
```
**入力画像:** Nano Bananaで生成したシーン2画像
**Duration:** 5秒

---

### シーン3: 慌てて起きる（8-15秒）

```
SUBJECT: The same young Asian woman bolting upright in bed, panicked expression.

ACTION: She sits up quickly and abruptly, eyes wide with alarm. Her hand reaches up to push hair out of her face. She looks around frantically, then reaches off-frame (presumably for phone or clock). Her expression shifts from sleep to panic to self-disappointment. She lets out a small frustrated sigh.

CONTEXT: Same bedroom, now brighter with harsh morning light. The room feels chaotic—bedding is disheveled, items scattered.

STYLE: Cinematic, realistic, documentary. Harsh morning light creates unflattering shadows. High contrast, chaotic feel.

CAMERA: Static medium shot at eye level. No camera movement. The stillness of the camera contrasts with her frantic movements, emphasizing her panic and the chaos of the moment.

LENS: 35mm equivalent, f/2.8.

MOTION SPECIFICS: Woman sits up quickly (0.5s), looks around frantically (1s), reaches off-frame (1s), sighs with frustration (0.5s). Hair moves naturally with movement. Bedding shifts slightly. Background remains static.
```
**入力画像:** Nano Bananaで生成したシーン3画像
**Duration:** 7秒

---

### シーン4: Aniicha通知（15-22秒）

```
SUBJECT: The same young Asian woman lying in bed, propped on pillow, looking at her phone. The phone screen displays the Anicca app Talk interface.

ACTION: Her expression transitions from tired (eyes heavy) to curious (eyebrows lift slightly as she reads) to hopeful (corners of mouth turn up) to a gentle genuine smile (full expression shift). She pulls the phone slightly closer to her face as her interest grows. She takes a deep, calming breath.

CONTEXT: Bedroom at golden hour morning. Sheer curtains diffuse warm sunlight. Same room as Scene 3, but transformed by morning light—visual metaphor for her internal transformation beginning.

STYLE: Cinematic, warm, hopeful. High-key lighting with soft shadows. Aspirational tone. The warmth of the light matches the warmth of the app's voice.

CAMERA: Static medium close-up at eye level. The intimate framing and stillness create connection—we're sharing this private moment of hope with her. No movement because this is an internal transformation, not an external action.

LENS: 50mm equivalent, f/2.0.

MOTION SPECIFICS: Expression arc over 7s: tired (0-1.5s), curious (1.5-3s), hopeful (3-5s), gentle smile (5-7s). Phone moves 5cm closer to face during curious phase. Subtle eye movement reading the screen. Deep breath at 6s mark. Sunlight may have gentle dust particles floating.
```
**入力画像:** Nano Bananaで生成したシーン4画像
**Duration:** 7秒

---

### シーン5: 自然に目覚める（22-27秒）

```
SUBJECT: The same young Asian woman waking up naturally, stretching with arms raised, peaceful smile.

ACTION: She completes a satisfying morning stretch—arms reach high, she takes a deep breath, then relaxes her arms down with a proud smile. Her eyes are gently opening, looking refreshed and energized. She looks toward the window, appreciating the morning light. This mirrors Scene 1's desperate hand movement but with opposite emotion—peaceful awakening instead of desperate snoozing.

CONTEXT: Same room as Scene 1, but now peaceful and tidy. Bathed in bright golden morning light. The visual callback creates powerful before/after contrast. She has transformed.

STYLE: Cinematic, aspirational, triumphant. High-key warm lighting. Saturated warm tones contrast with the muted tones of earlier scenes. Victory aesthetic.

CAMERA: Static medium shot at eye level. The stillness of the camera emphasizes her peaceful, natural awakening—no chaos, no panic, just calm transformation.

LENS: 50mm equivalent, f/2.0.

MOTION SPECIFICS: Stretch arc over 5s: arms rise (0-1.5s), peak stretch with eyes opening and deep breath (1.5-2.5s), arms lower with proud smile (2.5-4s), looks toward window (4-5s). Smooth, slow, peaceful movements. Background remains static.
```
**入力画像:** Nano Bananaで生成したシーン5画像
**Duration:** 5秒

---

## Arcads.aiスクリプト（ベストプラクティス適用版）

### Arcads.aiベストプラクティス（調査結果）

| カテゴリ | ポイント | 詳細 |
|---------|---------|------|
| **スクリプト構造** | AIDA/PAS形式 | Hook → Problem → Solution → Result → CTA の流れ |
| **最適な長さ** | 30-45秒 | TikTok/Reelsで完了率を最大化。60秒は長すぎ |
| **フック（最重要）** | 最初の3秒 | 視聴者の痛みを直接突く。質問形式 or 共感形式 |
| **アバター選択** | ターゲット一致 | 20代女性ターゲット → 20代女性アバター |
| **トーン** | 会話調・本音系 | 台本っぽさを避ける。「Honestly...」「Like...」を活用 |
| **句読点テクニック** | 抑揚コントロール | カンマ=短い間、ピリオド=長い間、...=ため息感 |
| **CTA** | 行動を明確に | 「Search Anicca on App Store.」「Try it free」。曖昧にしない |

### スクリプトライティングルール

| ルール | 悪い例 | 良い例 |
|--------|--------|--------|
| **Filler words** | "I found Aniicha" | "Honestly, I found Aniicha" |
| **自然な間** | "スヌーズ10回押してまた寝た" | "スヌーズ10回。押して。また寝た。" |
| **感情の具体化** | "辛かった" | "毎朝、自分を責めてた" |
| **結果の具体化** | "起きられた" | "7:00。スヌーズ押さずに起きた" |

---

### Arcads.aiスクリプト（英語版）

```
[HOOK - 0-5秒]
10 snoozes. Still in bed.
Late again. Day ruined.

[PROBLEM - 5-15秒]
I thought I was just... not a morning person, you know?
Like, maybe some people are just built to wake up early, and I'm not one of them.
Every morning, I'd hit snooze 10 times. Then panic. Then rush. Then hate myself.

[SOLUTION - 15-28秒]
Then I found Aniicha. Honestly... it's like having someone gently wake you up.
Not with a jarring alarm. But with a voice that actually cares.
It doesn't judge you for hitting snooze. It just says... "Let's wake up together."

[RESULT - 28-35秒]
7:00 AM. And I'm actually awake.
No snooze. No panic. Just... natural.

[CTA - 35-40秒]
If you're tired of being late... try Aniicha. Search Anicca on App Store.
```

**句読点ノート:**
- `...` = 呼吸/ため息の間（0.5秒）
- 短い文 = パンチ力。「7:00 AM. And I'm actually awake.」
- 質問形 = 共感誘発。「you know?」

---

### Arcads.aiスクリプト（日本語版）

```
[HOOK - 0-5秒]
スヌーズ10回。まだ寝てる。
また遅刻。1日が台無し。

[PROBLEM - 5-15秒]
自分は朝型じゃないんだって思ってた。
早起きできる人と、できない人がいるんだって...。
毎朝、スヌーズ10回押して。慌てて。自分を責めてた。

[SOLUTION - 15-28秒]
そんな時...Aniccaを見つけた。
優しく起こしてくれる誰かがいるみたい。
うるさいアラームじゃなくて、本当に寄り添ってくれる声。
スヌーズ押しても責めない。「一緒に起きよう」って...言ってくれる。

[RESULT - 28-35秒]
7:00。実際に起きてる。
スヌーズなし。慌てない。ただ...自然に。

[CTA - 35-40秒]
遅刻に疲れたなら...Anicca試してみて。リンクはプロフに。
```

---

### Arcads.ai設定（詳細版）

```json
{
  "avatar": {
    "type": "UGC Creator Style",
    "gender": "Female",
    "age_range": "23-28",
    "ethnicity": "Asian",
    "appearance": "Natural makeup, casual but put-together",
    "vibe": "Relatable friend, not influencer"
  },
  "wardrobe": {
    "style": "Casual sleepwear",
    "examples": ["Simple pajamas", "Oversized t-shirt", "Hair in messy bun"],
    "avoid": ["Overly styled", "Professional attire", "Heavy makeup"]
  },
  "background": {
    "primary": "Simple bedroom",
    "lighting": "Natural window light, slightly warm",
    "style": "Lived-in but not messy",
    "avoid": ["Studio backdrop", "Ring light visible", "Overly curated"]
  },
  "camera": {
    "framing": "Medium close-up, chest to head",
    "angle": "Slightly above eye level (flattering but not extreme)",
    "distance": "Arm's length (selfie distance)",
    "shake": "Minimal natural handheld feel"
  },
  "voice_settings": {
    "tone": "Conversational, warm, slightly vulnerable",
    "pace": "Natural with deliberate pauses at ...",
    "energy": "Starts low (defeated) → builds to hopeful → ends confident",
    "avoid": ["Salesy", "Over-enthusiastic", "Monotone"]
  },
  "duration": "40 seconds",
  "languages": ["English", "Japanese"],
  "output_format": "9:16 vertical, 1080x1920"
}
```

### Arcads.aiで避けるべきこと

| 避けること | 理由 |
|-----------|------|
| 台本読み感 | 「演技」に見えると離脱される |
| 過度な編集 | UGC感が失われる |
| 長すぎるフック | 最初の3秒で興味を引けなければ終わり |
| 曖昧なCTA | 「チェックしてみて」より「Search Anicca on App Store.」が具体的 |
| 完璧すぎる背景 | スタジオ感があるとTikTokで浮く |

---

## 成功指標

| 指標 | 目標 |
|------|------|
| 視聴完了率 | 50%以上 |
| エンゲージメント率 | 5%以上 |
| 保存数 | 100以上 |
| シェア数 | 50以上 |
| App Storeクリック | 追跡（UTMリンク使用） |

---

## バリエーション展開（成功時）

この動画がバイラルになった場合、以下のバリエーションを展開：

1. **時間変更版**: 「5:00起き」「6:00起き」など
2. **シチュエーション変更版**: 学生版、社会人版、主婦版
3. **スヌーズ回数変更版**: 「スヌーズ5回」「スヌーズ20回」
4. **言語展開**: 韓国語、中国語、スペイン語

---

## 備考

- 動画の人物は全てAI生成（シーン1をベースに一貫性維持）
- **音声発声時は「Aniicha」と表記**して正しい発音に寄せる
- Talk画面のスクショは実際のアプリ画面を使用
- 投稿時間は夜20時がベスト（ターゲットがスマホを見ている時間）
- サブタイトル（字幕）+ 中央キャプション（Hook）の両方を使用
- スヌーズを押しまくる「あるある」を視覚的に表現
- 遅刻の慌ただしさと、自然に目覚める穏やかさのコントラスト
- 起床習慣はAniccaの主要ユースケース

---

## 投稿結果記録

### 投稿情報

| 項目 | 詳細 |
|------|------|
| **投稿日時** | TBD |
| **投稿プラットフォーム** | TikTok, IG Reels, YT Shorts, X, Threads |
| **使用キャプション（EN）** | "10 snoozes later..." |
| **使用キャプション（JP）** | 「スヌーズ10回後…」 |

### 結果（投稿後に記入）

| プラットフォーム | 再生数 | いいね | コメント | 保存 | シェア |
|----------------|-------|-------|---------|------|-------|
| TikTok | - | - | - | - | - |
| IG Reels | - | - | - | - | - |
| YT Shorts | - | - | - | - | - |
| X | - | - | - | - | - |
| Threads | - | - | - | - | - |

### Arcads.ai版結果（投稿後に記入）

| バージョン | プラットフォーム | 再生数 | いいね | コメント |
|-----------|----------------|-------|-------|---------|
| EN Testimonial | TikTok | - | - | - |
| JP Testimonial | TikTok | - | - | - |

### 分析メモ

（投稿後に記入）
- 何がうまくいったか:
- 何が改善できるか:
- Kling版 vs Arcads.ai版どちらが良かったか:
- 次回への学び:

