# 動画03: 自己嫌悪のループ

## 基本情報

| 項目 | 詳細 |
|------|------|
| **タイトル（EN）** | "POV: you failed again… and you hate yourself for it." |
| **タイトル（JP）** | 「あるある：また自分を責めてる夜」 |
| **カテゴリ** | 問題提起・共感型（Pain Point Hook） |
| **尺** | 25-30秒 |
| **形式** | 縦動画 9:16 |
| **プラットフォーム** | TikTok, IG Reels, YT Shorts, X, Threads |
| **サムネイル/カバーテキスト** | "POV: you failed again…" / 「あるある：また自分を責めてる夜」 |
| **投稿ツール** | Buffer（一括予約投稿） |
| **編集ツール** | VEED |

---

## なぜこの動画が効果的か

1. **深い感情トリガー** - 自己嫌悪に苦しむ人に直接刺さる
2. **Aniccaの核フレーズ** - 「"ダメな人"じゃなくて"傷ついている人"なんだ」を直接使用
3. **視覚的な変容** - 暗闇から光が差し込むメタファーで希望を表現
4. **普遍的な悩み** - 「また失敗した」「どうせ自分なんて」は多くの人が経験
5. **シェアされやすい** - 感情的なピークで共感を呼び、リポストされる

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
| **0-3秒** | フック | 暗い背景、抽象的な感情の渦 | 中央キャプション: EN「POV: you failed again…」/ JP「あるある：また自分を責めてる夜」 | Nano Banana → Kling + VEED中央キャプション |
| **3-15秒** | 問題深化 | AI生成の人物が暗い部屋で頭を抱える。暗い色調、低いコントラスト | 効果音（呼吸、ため息） | Nano Banana → Kling + 効果音 |
| **15-25秒** | 転換点 | 少しずつ光が差し込む。人物の肩が少し上がる | 中央キャプション: EN「Not broken. Hurt.」/ JP「壊れてない。傷ついてるだけ。」 | Nano Banana → Kling + VEED中央キャプション |
| **25-30秒** | 変容・CTA | 光が部屋を満たし、人物が顔を上げる | 中央キャプション: EN「Try Anicca」/ JP「Aniccaを試してみて」+ Aniccaロゴ（VEEDで後入れ） | Nano Banana → Kling + VEEDロゴ合成 |

---

## 素材リスト

### あなたが用意するもの
- [ ] Aniccaロゴ（透明背景PNG、VEEDで最後に合成）
- [ ] 音楽: Pixabay – "Inspiring Cinematic Ambient" (Lexin_Music) - `https://pixabay.com/music/beautiful-plays-inspiring-cinematic-ambient-116199/`
- [ ] 効果音: 呼吸、ため息、光が差し込む音（必要に応じて）

### AI生成するもの（Nano Banana + Kling）
- [ ] **Character Reference画像（最重要）**: 人物の顔基準画像（バストアップ、無表情、シンプル背景、No text）を最初に生成
- [ ] シーン1: 暗い背景（抽象、人物なし）
- [ ] シーン2: 頭を抱える人物（Character Reference参照）
- [ ] シーン3: 光が差し込む瞬間（Character Reference参照）
- [ ] シーン4: 顔を上げる人物（Character Reference参照）

### 編集で追加するもの（VEED）
- [ ] 中央キャプション3回（シーン1/Hook、シーン3/転換、シーン4/CTA）
- [ ] Aniccaロゴ（シーン4の最後1.5-2秒）
- [ ] 音楽（全体）
- [ ] 効果音（必要箇所）

---

## Hookパターン（タイトル兼サムネ = 0-3秒中央キャプション）

### 英語版（確定）
```
Primary: "POV: you failed again… and you hate yourself for it."
```
**理由**: ユーザーが気に入っているPOV型。0.5秒で意味が通る。

### 日本語版（確定）
```
Primary: 「あるある：また自分を責めてる夜」
```
**理由**: POV直訳を避け、日本で通る共感ラベル（「あるある」）を使用。自己嫌悪ループが一瞬で伝わる。

### 中央キャプション配置（3回のみ）
- **シーン1（0-3秒）**: Hook（上記）
- **シーン3（15-25秒）**: EN「Not broken. Hurt.」/ JP「壊れてない。傷ついてるだけ。」
- **シーン4（25-30秒）**: EN「Try Anicca」/ JP「Aniccaを試してみて」

---

## YouTubeタイトル + 共通キャプション

### YouTubeタイトル
- **英語**: `POV: You failed again… and you hate yourself for it.`
- **日本語**: `あるある：また自分を責めてる夜`

### 共通キャプション（全プラットフォーム共通）
- **英語**: `You're not broken — you're hurt.`
- **日本語**: `壊れてるんじゃない。傷ついてるだけ。`

---

## Buffer同時投稿設定

| プラットフォーム | 投稿時間（推奨） | 形式 |
|----------------|----------------|------|
| TikTok | 20:00 JST / 7:00 EST | 動画 + キャプション |
| Instagram Reels | 20:00 JST / 7:00 EST | 動画 + キャプション |
| YouTube Shorts | 20:00 JST / 7:00 EST | 動画 + タイトル + 説明 |
| Threads | 20:00 JST / 7:00 EST | 動画 + 短文 |

---

## Nano Banana プロンプト（ベストプラクティス適用版）

> **重要**: awesome-nanobanana-pro + best-kling-prompt.md のベストプラクティスに基づいて構造化

### Character Reference画像（最初に生成）

**目的**: シーン2-4で人物の一貫性を保つための基準画像

```json
{
  "subject": {
    "primary": "Young white woman in her mid-20s, neutral expression",
    "pose": "Bust-up, facing camera slightly off-center",
    "expression": "Neutral, calm, no strong emotion",
    "body_language": "Relaxed, natural"
  },
  "wardrobe": {
    "clothing": "Simple gray t-shirt",
    "hair": "Down, natural, slightly messy"
  },
  "environment": {
    "setting": "Simple neutral background, soft blur",
    "lighting": "Even, soft natural light",
    "atmosphere": "Clean, minimal, reference-friendly"
  },
  "photography": {
    "composition": "Bust-up, centered, 9:16 vertical",
    "lens": "85mm portrait lens equivalent",
    "aperture": "f/2.0",
    "focus": "Sharp on face, soft background"
  },
  "style": {
    "aesthetic": "Realistic, clean, reference-quality",
    "color_palette": "Neutral, natural skin tones",
    "mood": "Neutral, versatile for multiple scenes"
  },
  "negative": [
    "Text overlays or watermarks",
    "Strong emotions or expressions",
    "Complex backgrounds",
    "Distracting elements"
  ]
}
```
**添付:** なし（最初に生成する基準画像）

**使用方法**: この画像を生成後、シーン2-4のプロンプトで「Use the uploaded reference image for the character's face and appearance」として参照する。

### シーン1: 暗い背景（フック）0-3秒

```json
{
  "subject": {
    "primary": "Dark, abstract background with swirling negative thoughts",
    "description": "Deep dark space, almost black, with subtle texture suggesting emotional turmoil"
  },
  "environment": {
    "setting": "Abstract void, no physical space",
    "time_of_day": "Timeless darkness",
    "atmosphere": "Heavy, oppressive, emotional weight"
  },
  "photography": {
    "composition": "Full frame, 9:16 vertical",
    "lens": "Wide angle, 24mm equivalent",
    "aperture": "f/2.8",
    "focus": "Everything in soft focus, dreamlike",
    "lighting": {
      "type": "Minimal, almost no light",
      "color_temperature": "Cool, desaturated",
      "quality": "Deep shadows, no highlights"
    }
  },
  "style": {
    "aesthetic": "Cinematic, abstract, emotional",
    "color_palette": "Deep blacks, muted grays, almost monochrome",
    "mood": "Heavy, oppressive, self-critical"
  },
  "negative": [
    "Text overlays or watermarks",
    "Bright colors",
    "Visible objects or people",
    "Harsh lighting"
  ]
}
```
**添付:** なし（抽象背景のみ。人物参照には使わない）

**重要**: シーン1は抽象背景のため、人物の一貫性を保つために**別途Character Reference画像を生成**すること。

---

### シーン2: 頭を抱える人物（問題深化）3-15秒

```json
{
  "face_preservation": {
    "instruction": "Use the uploaded reference image for the character's face and appearance",
    "preserve_original": true,
    "reference_match": true
  },
  "subject": {
    "primary": "Young white woman in her mid-20s sitting on edge of bed, head buried in hands",
    "pose": "Elbows on knees, face completely hidden in palms, shoulders slumped forward",
    "expression": "Deep emotional pain, self-hatred, exhaustion",
    "body_language": "Defeated, collapsed posture, tension in shoulders and neck"
  },
  "wardrobe": {
    "clothing": "Simple gray t-shirt, dark sweatpants",
    "hair": "Down, slightly messy, covering part of face"
  },
  "environment": {
    "setting": "Minimal bedroom at night, almost no furniture visible",
    "lighting_sources": ["Single dim lamp with very low warm orange glow", "No overhead lights", "Deep shadows"],
    "time_of_day": "Late night, 11PM-2AM feel",
    "atmosphere": "Isolation, despair, emotional rock bottom"
  },
  "photography": {
    "composition": "Medium shot, slightly below eye level for vulnerability, 9:16 vertical",
    "lens": "85mm portrait lens equivalent",
    "aperture": "f/2.0",
    "lighting": {
      "type": "Low-key dramatic lighting, very dark",
      "key_light": "Minimal warm lamp from camera-right, creating subtle rim light",
      "fill": "Almost none—deep shadows dominate",
      "contrast": "Very high contrast, chiaroscuro effect, mostly shadows"
    }
  },
  "style": {
    "aesthetic": "Cinematic, emotional, dramatic, dark",
    "color_palette": "Deep blues, warm orange lamp glow (very subtle), deep shadows, desaturated",
    "film_reference": "Wong Kar-wai moody interiors, but darker",
    "mood": "Heavy, introspective, emotional nadir, self-critical"
  },
  "negative": [
    "Bright lighting",
    "Happy or neutral expression",
    "Multiple light sources",
    "Visible phone or technology",
    "Colorful elements"
  ]
}
```
**添付:** Character Reference画像（別途生成した人物基準画像）

**重要**: シーン1は抽象背景のため、人物参照には使えない。必ず別途Character Reference画像を作成し、シーン2-4で参照すること。

---

### シーン3: 光が差し込む瞬間（転換点）15-25秒

```json
{
  "face_preservation": {
    "instruction": "Use the uploaded reference image for the character's face and appearance",
    "preserve_original": true,
    "reference_match": true
  },
  "subject": {
    "primary": "Same young white woman, still sitting on bed, but now a subtle change",
    "pose": "Slightly less collapsed, shoulders beginning to lift",
    "expression": "Transitioning from despair to curiosity, eyes still closed but face less tense",
    "body_language": "Beginning to respond to light, subtle shift in posture"
  },
  "environment": {
    "setting": "Same bedroom, but now golden light begins to stream through window",
    "lighting_sources": ["Warm golden morning light streaming through window (camera-left)", "Dim lamp still on but overpowered by new light"],
    "time_of_day": "Dawn breaking, 5-6AM feel",
    "atmosphere": "Hope beginning, transformation starting, light overcoming darkness"
  },
  "photography": {
    "composition": "Medium shot, same angle as Scene 2, 9:16 vertical",
    "lens": "85mm portrait lens equivalent",
    "aperture": "f/2.0",
    "lighting": {
      "type": "Transitional lighting—dark to light",
      "key_light": "Warm golden sunlight from window, camera-left",
      "fill": "Soft bounce from walls, shadows lifting",
      "contrast": "Medium contrast, shadows still present but lightening"
    },
    "color_temperature": "Warm 4000K morning light mixing with cool shadows"
  },
  "style": {
    "aesthetic": "Cinematic, hopeful transition, dramatic lighting change",
    "color_palette": "Warm golds beginning to mix with deep blues, shadows lifting",
    "mood": "Transformation beginning, hope emerging, light overcoming darkness",
    "film_tone": "Shadows lifting, warm highlights increasing"
  },
  "negative": [
    "Completely bright lighting",
    "Happy expression (too early)",
    "No shadows",
    "Harsh contrast"
  ]
}
```
**添付:** Character Reference画像（シーン2と同じ参照画像を使用）

---

### シーン4: 顔を上げる人物（変容・CTA）25-30秒

```json
{
  "face_preservation": {
    "instruction": "Use the uploaded reference image for the character's face and appearance",
    "preserve_original": true,
    "reference_match": true
  },
  "subject": {
    "primary": "Same young white woman, now lifting her head from hands",
    "pose": "Sitting upright, hands lowering from face, shoulders back",
    "expression": "Gentle, peaceful acceptance, eyes opening slowly, slight soft smile",
    "body_language": "Open posture, relaxed, transformed, at peace"
  },
  "wardrobe": {
    "clothing": "Same simple gray t-shirt, but now bathed in warm light",
    "hair": "Same style, but now catching golden light"
  },
  "environment": {
    "setting": "Same bedroom, now filled with warm golden morning light",
    "lighting_sources": ["Bright warm golden sunlight flooding room through window", "Lamp off or barely visible"],
    "time_of_day": "Early morning, 6-7AM, golden hour",
    "atmosphere": "Peace, acceptance, transformation complete, hope restored"
  },
  "photography": {
    "composition": "Medium shot, eye level, intimate, 9:16 vertical",
    "lens": "85mm portrait lens equivalent",
    "aperture": "f/2.0",
    "lighting": {
      "type": "High-key warm lighting",
      "key_light": "Warm golden sunlight from window, camera-left",
      "fill": "Soft bounce from white walls, minimal shadows",
      "contrast": "Low to medium contrast, soft shadows"
    },
    "color_temperature": "Warm 4500K morning light"
  },
  "style": {
    "aesthetic": "Cinematic, hopeful, aspirational, warm",
    "color_palette": "Warm golds, soft whites, gentle contrast",
    "mood": "Transformation complete, peace, self-compassion, hope",
    "film_tone": "Lifted shadows, warm highlights, aspirational"
  },
  "negative": [
    "Dark or moody lighting",
    "Sad or defeated expression",
    "Deep shadows",
    "Cool color tones"
  ]
}
```
**添付:** Character Reference画像（シーン2と同じ参照画像を使用）

**重要**: シーン4の最後1.5-2秒にAniccaロゴをVEEDで合成（Nano Bananaプロンプトには含めない）。

---

## Kling プロンプト（ベストプラクティス適用版）

> **重要**: best-kling-prompt.md に基づいて **Subject + Action + Context + Style** の4要素 + **Narrative Intent（なぜこのカメラ動きか）** を明記

### シーン1: 暗い背景（0-3秒）

```
Static camera shot.

SUBJECT: Abstract dark void with swirling emotional texture.

ACTION: Subtle, slow movement of dark shadows and textures, like thoughts swirling in darkness. The darkness itself seems to pulse slightly, breathing with emotional weight.

CONTEXT: No physical space, just abstract emotional void. Deep black background with minimal texture suggesting turmoil.

STYLE: Cinematic, abstract, emotional, almost monochrome. Deep shadows with no highlights.

CAMERA: Static locked shot. No camera movement. The stillness emphasizes the weight of the emotional darkness—the viewer feels trapped in this space, mirroring the feeling of being stuck in self-hatred.

LENS: Wide angle, 24mm equivalent, f/2.8.

MOTION SPECIFICS: Only subtle texture movement in the darkness (very slow, 0.5s pulse). Everything else is completely static. The minimal movement creates unease—something is wrong, but nothing is happening.

The camera remains fixed.
```
**入力画像:** Nano Bananaで生成したシーン1画像
**Duration:** 3秒

---

### シーン2: 頭を抱える人物（3-15秒）

```
Static camera shot.

SUBJECT: A young white woman sitting on edge of bed, head buried in hands, elbows on knees.

ACTION: She takes a deep, shuddering breath. Her shoulders rise slightly, then drop heavily with the exhale—a gesture of defeat. Her fingers press slightly harder against her temples. Her body remains collapsed. The dim lamp light flickers once, barely perceptibly, as if mirroring her emotional state.

CONTEXT: Dark bedroom at night. Single dim warm lamp creates dramatic shadows. This is her emotional lowest point—the crisis moment before change. Deep shadows dominate the frame.

STYLE: Cinematic, high-contrast, low-key dramatic lighting. Wong Kar-wai moody interiors influence. Deep shadows, minimal warm rim light.

CAMERA: Static medium shot, slightly below eye level. The lower angle gives her vulnerability—we're looking up at her despair rather than down at it, creating empathy rather than judgment. No camera movement—stillness reflects her feeling of being stuck in the self-hatred loop.

LENS: 85mm portrait equivalent, f/2.0.

MOTION SPECIFICS: Breathing is the primary motion—slow inhale (2s) with rising shoulders, slow exhale (3s) with dropping shoulders. Fingers press temples at exhale peak (at 5s mark). Lamp flickers subtly at 8s mark. No other movement. The minimal movement emphasizes her stuckness—she's trapped in this moment.

The camera remains fixed.
```
**入力画像:** Nano Bananaで生成したシーン2画像
**Duration:** 12秒

---

### シーン3: 光が差し込む瞬間（15-25秒）

```
Static camera shot.

SUBJECT: The same young white woman sitting on bed, still with head in hands, but now golden morning light begins to stream through the window.

ACTION: The golden light slowly fills the room, starting from the window and gradually illuminating the space. Her shoulders begin to lift slightly—a subtle response to the light. Her fingers relax slightly on her temples. The light touches her hair and shoulders, creating a warm rim light. Her breathing becomes calmer, slower.

CONTEXT: Same bedroom, but now dawn is breaking. The golden morning light contrasts with the previous darkness. This is the moment of transformation beginning—light overcoming darkness, both literally and metaphorically.

STYLE: Cinematic, transitional lighting, dramatic but hopeful. The warm golden light represents hope and self-compassion entering her life.

CAMERA: Static medium shot, same angle as Scene 2. The camera remains fixed to emphasize that the transformation is happening within her, not through external camera movement. The stillness allows the viewer to witness the light's gradual transformation of the space.

LENS: 85mm portrait equivalent, f/2.0.

MOTION SPECIFICS: Light gradually fills the room over 10s (slow, deliberate). Her shoulders lift slightly (at 3s mark). Fingers relax (at 5s mark). Breathing calms (throughout). The light movement is the primary action—it's the agent of change, not her physical movement yet.

The camera remains fixed.
```
**入力画像:** Nano Bananaで生成したシーン3画像
**Duration:** 10秒

---

### シーン4: 顔を上げる人物（25-30秒）

```
Static camera shot.

SUBJECT: The same young white woman, now lifting her head from her hands, face turning toward the warm golden light.

ACTION: She slowly lifts her head from her hands, her face turning toward the window where the light streams in. Her eyes open slowly, squinting slightly at first, then opening fully. A gentle, peaceful expression forms—not a big smile, but acceptance and peace. Her hands lower to her lap. She takes a calm, deep breath. Her shoulders relax completely.

CONTEXT: Same bedroom, now filled with warm golden morning light. The transformation is complete—from darkness to light, from self-hatred to self-compassion. The room feels peaceful, hopeful.

STYLE: Cinematic, hopeful, aspirational, warm. High-key lighting with soft shadows. The warmth of the light matches the warmth of self-compassion.

CAMERA: Static medium shot at eye level. The intimate framing and stillness create connection—we're sharing this private moment of transformation with her. No movement because this is an internal transformation becoming visible, not an external action.

LENS: 85mm portrait equivalent, f/2.0.

MOTION SPECIFICS: Head lifts slowly (0-2s), face turns toward light (2-3s), eyes open (3-4s), gentle expression forms (4-5s). Hands lower to lap (throughout). Calm breath (at 3s mark). The movement is slow, deliberate, peaceful—mirroring the internal shift from self-criticism to self-compassion.

The camera remains fixed.
```
**入力画像:** Nano Bananaで生成したシーン4画像
**Duration:** 5秒

---

## Arcads.ai スクリプト（ベストプラクティス適用版）

### Arcads.aiベストプラクティス（調査結果）

| カテゴリ | ポイント | 詳細 |
|---------|---------|------|
| **スクリプト構造** | AIDA/PAS形式 | Hook → Problem → Solution → Result → CTA の流れ |
| **最適な長さ** | 30-45秒 | TikTok/Reelsで完了率を最大化。60秒は長すぎ |
| **フック（最重要）** | 最初の3秒 | 視聴者の痛みを直接突く。質問形式 or 共感形式 |
| **アバター選択** | ターゲット一致 | 20代女性ターゲット → 20代女性アバター |
| **トーン** | 会話調・本音系 | 台本っぽさを避ける。「Honestly...」「Like...」を活用 |
| **句読点テクニック** | 抑揚コントロール | カンマ=短い間、ピリオド=長い間、...=ため息感 |
| **CTA** | 行動を明確に | 「Link in bio」「Try it free」。曖昧にしない |

### スクリプトライティングルール

| ルール | 悪い例 | 良い例 |
|--------|--------|--------|
| **Filler words** | "I found Aniicha" | "Honestly, I found Aniicha" |
| **自然な間** | "自分を責めてた毎日が続いた" | "自分を責めてた。毎日。それが続いた。" |
| **感情の具体化** | "辛かった" | "毎晩、自分を殴りすぎてた" |
| **結果の具体化** | "楽になった" | "今、自分を許せるようになった" |

---

### Arcads.aiスクリプト（英語版）

```
[HOOK - 0-5秒]
You're not broken. You're just stuck.

Every time you fail, you tell yourself: "I'm broken. I'll never change."

[PROBLEM - 5-15秒]
I used to do this... every single day.
Gym? Failed after 3 days. "I'm just not disciplined enough."
Meditation? Gave up. "I'm broken."
Journaling? Stopped. "I'm just... broken."

Every failure was proof that I was fundamentally broken.

[SOLUTION - 15-28秒]
Then I found Aniicha. And honestly... it changed everything.
Because Aniicha told me something I'd never heard before.

"You're not a broken person. You're a hurt person."

Not broken. Just hurt. And hurt people... can heal.

[RESULT - 28-35秒]
Now? I'm not perfect. But I'm not broken either.
I'm healing. And that's enough.

[CTA - 35-40秒]
If you're stuck in the self-hatred loop... try Aniicha. Link in bio.
```

**句読点ノート:**
- `...` = 呼吸/ため息の間（0.5秒）
- 短い文 = パンチ力。「Not broken. Just hurt.」
- 質問形 = 共感誘発。「I'm broken, right?」

---

### Arcads.aiスクリプト（日本語版）

```
[HOOK - 0-5秒]
あなたは壊れてない。ただハマってるだけ。

失敗するたびに「自分は壊れてる」って言ってた。

[PROBLEM - 5-15秒]
毎日、そうやって自分を責めてた。
筋トレ？3日でやめた。「根性がない」
瞑想？続かなかった。「自分は壊れてる」
日記？書かなくなった。「...壊れてる」

毎回の失敗が、自分が壊れてる証拠だと思ってた。

[SOLUTION - 15-28秒]
そんな時...Aniccaを見つけた。
そして、聞いたことのない言葉を聞いた。

「"ダメな人"じゃなくて"傷ついている人"なんだ」

壊れてない。ただ、傷ついてるだけ。傷ついた人は...治せる。

[RESULT - 28-35秒]
今？完璧じゃない。でも、壊れてるわけでもない。
治ってる。それでいい。

[CTA - 35-40秒]
自己嫌悪のループから抜け出したいなら...Anicca試してみて。リンクはプロフに。
```

---

### Arcads.ai設定（詳細版）

```json
{
  "avatar": {
    "type": "UGC Creator Style",
    "gender": "Female",
    "age_range": "23-28",
    "ethnicity": "White",
    "appearance": "Natural makeup, casual but put-together",
    "vibe": "Relatable friend, not influencer, vulnerable but strong"
  },
  "wardrobe": {
    "style": "Casual, comfortable",
    "examples": ["Simple gray t-shirt", "Dark sweatpants", "Hair down"],
    "avoid": ["Overly styled", "Professional attire", "Heavy makeup"]
  },
  "background": {
    "primary": "Simple bedroom, minimal",
    "lighting": "Natural window light transitioning from dark to warm",
    "style": "Lived-in but not messy",
    "avoid": ["Studio backdrop", "Ring light visible", "Overly curated"]
  },
  "camera": {
    "framing": "Medium close-up, chest to head",
    "angle": "Slightly below eye level (vulnerability)",
    "distance": "Arm's length (selfie distance)",
    "shake": "Minimal natural handheld feel"
  },
  "voice_settings": {
    "tone": "Conversational, vulnerable, compassionate",
    "pace": "Natural with deliberate pauses at ...",
    "energy": "Starts low (defeated) → builds to hopeful → ends peaceful",
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
| 曖昧なCTA | 「チェックしてみて」より「Link in bio」が具体的 |
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

1. **フレーズ変更版**: 「壊れてない」以外のAnicca核フレーズを使用
2. **シチュエーション変更版**: 仕事での失敗、人間関係での失敗など
3. **ターゲット変更版**: 学生版、社会人版、主婦版
4. **言語展開**: 韓国語、中国語、スペイン語

---

## 備考

### 制作上の重要事項
- **Character Reference画像**: シーン1は抽象背景のため、人物の一貫性を保つために**別途Character Reference画像を最初に生成**すること（バストアップ、無表情、シンプル背景、No text）
- 動画の人物は全てAI生成（Character Reference画像をベースに一貫性維持）
- **音声発声時は「Aniicha」と表記**して正しい発音に寄せる[[memory:12208368]]
- 暗い色調から光が差し込む変容を視覚的に表現
- 自己嫌悪に苦しむ人の感情に寄り添う

### 音声・音楽・テキスト
- **ナレーション**: 無し（効果音 + BGM中心）
- **字幕（サブタイトル）**: 無し（ナレーション無しのため不要）
- **中央キャプション**: 3回のみ（シーン1/Hook、シーン3/転換、シーン4/CTA）をVEEDで後入れ
- **音楽**: Pixabay – "Inspiring Cinematic Ambient" (Lexin_Music) - 商用利用可（Pixabay Content License）
- **アプリ画面/ロゴ**: シーン4の最後1.5-2秒にAniccaロゴをVEEDで合成（Nano Bananaプロンプトには含めない）

### 投稿・運用
- 投稿時間は夜20時がベスト（ターゲットがスマホを見ている時間）
- Arcads.ai版は同時制作してA/Bテスト（ただし今回はKling版を優先）

---

## 投稿結果記録

### 投稿情報

| 項目 | 詳細 |
|------|------|
| **投稿日時** | TBD |
| **投稿プラットフォーム** | TikTok, IG Reels, YT Shorts, X, Threads |
| **使用キャプション（EN）** | "POV: you failed again…" |
| **使用キャプション（JP）** | 「あるある：また自分を責めてる夜」 |

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

