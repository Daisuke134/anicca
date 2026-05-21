# TikTok「〜って思った瞬間」画像生成ログ

## モデル

| 項目 | 値 |
|------|-----|
| モデル | **Gemini 3 Pro Image** (`gemini-3-pro-image-preview`) |
| 通称 | Nano Banana Pro |
| スキル | `resciencelab/opc-skills@nanobanana` |
| アスペクト比 | 9:16（TikTok縦型） |
| テキスト | なし（画像のみ） |

## 生成コマンド（共通）

```bash
export GEMINI_API_KEY=<your-key>
python3 .agents/skills/nanobanana/scripts/generate.py "<PROMPT>" -r 9:16 -o <output.png> -v
```

---

## 01_irritation.png — イラつき

**感情フック:** 「あーこいつ、イラつく。」って思った瞬間

```
Dark moody anime watercolor oil painting, extreme close-up side profile of young Japanese woman age 17-19, face filling entire frame from edge to edge, frustrated irritated expression with furrowed brows and clenched jaw, dark grey-blue watercolor wash background, mix of watercolor transparency and oil paint texture, warm skin tones with pink lips, dark hair in messy bun with loose strands, slightly stylized anime features with detailed expressive eyes, school uniform collar barely visible at bottom, dramatic moody atmosphere, dim lighting from the side casting shadows, emotional intense portrait
```

---

## 02_jealousy.png — 嫉妬

**感情フック:** 「なんでこいつなんかが」って思った瞬間

```
Anime oil painting illustration, extreme close-up of a young Japanese schoolgirl face, three-quarter view looking down with resentful jealous eyes, dark stormy sky in background, slightly stylized large expressive eyes, visible oil paint brushstrokes on skin, warm natural skin tone with subtle blush, dark black hair with bangs falling over face, navy blue school uniform sailor collar, melancholic dark moody atmosphere, dramatic lighting from above, emotional portrait, soft anime proportions but with painterly texture
```

---

## 03_selfhate.png — 自己嫌悪

**感情フック:** 「自分が嫌いになった」って思った瞬間

```
Semi-realistic anime oil painting, extreme close-up portrait filling entire frame, young Japanese woman age 18-20, eyes closed with single tear running down cheek, feeling of self-hatred and defeat, cool blue-grey color palette, thick visible oil paint brushstrokes, natural warm skin tones contrasting with cold background, wearing dark hoodie, long dark hair framing face, deeply emotional and melancholic atmosphere, painterly texture like classical oil painting but with anime influence, dramatic soft lighting
```

---

## 04_leftbehind.png — 取り残され

**感情フック:** 「自分だけ取り残されてる」って思った瞬間

```
Dark moody anime watercolor painting, extreme close-up of young Japanese woman age 17-18, looking upward with empty hollow eyes full of loneliness, face fills 90 percent of frame, DARK background with deep brown and black watercolor washes, soft watercolor brushstrokes, warm skin tones contrasting with dark surroundings, long messy dark hair, slightly stylized anime eyes large and expressive, watercolor bleeding effects at edges, melancholic lonely dark atmosphere like a rainy evening, dim dramatic lighting on face only, emotional raw portrait
```

---

## 05_comparison.png — 比較・羨望

**感情フック:** 「比べちゃダメなのに比べちゃう」って思った瞬間

```
Dark moody anime watercolor painting, extreme close-up of young Japanese woman age 17-18 face in three-quarter view, looking sideways with bitter envious expression pursed lips, face takes up 85 percent of vertical frame, dark purple-grey watercolor wash background, watercolor brushstrokes with ink outlines, warm natural skin tones with subtle blush on cheeks, dark hair pulled back with messy loose strands falling over face, slightly stylized anime eyes with detailed irises, wearing navy school uniform with white sailor collar line visible at bottom, dark moody atmosphere, dramatic lighting from one side, emotionally intense and resentful expression
```

---

## 06_regret.png — 深夜後悔

**感情フック:** 「また同じこと繰り返してる」って思った瞬間

```
Semi-realistic anime oil painting, extreme close-up of young Japanese woman age 18 face illuminated by blue smartphone screen light in complete darkness, looking at phone with regretful sad frustrated expression, tear-stained cheeks, face takes up most of frame, warm skin tones lit by cold blue phone glow, dark hair falling around face, wearing pajama or casual top, late night alone in bedroom atmosphere, oil painting brushstroke texture, deeply emotional and raw mood, phone visible at bottom of frame, dramatic blue lighting contrast
```

---

## 参考元

TikTok「飛脚」アカウントの「〜って思った瞬間」シリーズ（水彩/油絵アニメタッチ、顔クローズアップ、バイラル投稿）
