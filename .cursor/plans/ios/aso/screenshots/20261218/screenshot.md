まず将来版の仕様を確認してから、スクリーンショット構成を提案します。

[1 tool called]

仕様を確認しました。将来版のスクリーンショット構成を提案します。

---

# 将来版（Proactive AI Agent）スクリーンショット構成

## デザインコンセプト：禅・わびさび

**現状の問題**：紫のグロー、派手すぎる、どこにでもあるAIアプリ感

**目指すデザイン**：

| 要素 | 禅・わびさびアプローチ |
|------|----------------------|
| **背景色** | `#1A1918`（墨色）または `#F5F3ED`（生成り） |
| **アクセント** | `#C9B382`（渋い金）- 控えめに使用 |
| **テキスト** | `#E5E4E2`（オフホワイト）力強いサンセリフ |
| **グロー** | **なし**。または非常に控えめな白いにじみ |
| **余白** | 多め。呼吸できる空間 |
| **写真・イラスト** | 使わない。タイポグラフィとUIのみ |
| **全体のトーン** | 厳しくも温かい。禅師のような存在感 |

---

## 6枚のスクリーンショット構成

### 1枚目：ヒーローショット（問題提起）

| 項目 | 内容 |
|------|------|
| **Headline** | **End the Loop.** |
| **Subheadline** | Same thoughts. Same habits. Same results. Time to break free. |
| **添付スクリーン** | なし（タイポグラフィのみ） |
| **背景** | 墨色 `#1A1918` にかすかな和紙テクスチャ |
| **意図** | ペインポイント（反芻・悪習慣のループ）に刺す |

---

### 2枚目：問題選択（StrugglesStepView）

| 項目 | 内容 |
|------|------|
| **Headline** | **Tell Us Your Struggles** |
| **Subheadline** | 13 battles. We'll fight them with you. |
| **添付スクリーン** | StrugglesStepView（13個の問題チップ選択画面） |
| **背景** | 墨色 + 画面 |
| **意図** | パーソナライズ感。「自分のための」感 |

---

### 3枚目：Nudge Card（コア機能）

| 項目 | 内容 |
|------|------|
| **Headline** | **Words That Hit Hard** |
| **Subheadline** | Delivered at the moment you need them most. |
| **添付スクリーン** | NudgeCardView（例：「その『あと5分だけ』で、何年失ってきた？」） |
| **背景** | 墨色 + 画面 |
| **意図** | 刺さる言葉で行動が変わることを示す |

---

### 4枚目：My Pathタブ

| 項目 | 内容 |
|------|------|
| **Headline** | **Your Path. Your Progress.** |
| **Subheadline** | Track the battles you chose. See how far you've come. |
| **添付スクリーン** | MyPathTabView（選択した問題リスト + Deep Diveボタン） |
| **背景** | 墨色 + 画面 |
| **意図** | 継続性・進捗可視化 |

---

### 5枚目：Deep Dive質問

| 項目 | 内容 |
|------|------|
| **Headline** | **AI That Understands You** |
| **Subheadline** | Deep questions. Deeper understanding. Better nudges. |
| **添付スクリーン** | DeepDiveSheetView（質問画面） |
| **背景** | 墨色 + 画面 |
| **意図** | AIが深く理解→パーソナライズされた介入 |

---

### 6枚目：CTA（締め）

| 項目 | 内容 |
|------|------|
| **Headline** | **Break Free.** |
| **Subheadline** | Your AI ally is ready. Are you? |
| **添付スクリーン** | なし（タイポグラフィのみ）または禅円相（円）のシンボル |
| **背景** | 墨色 + かすかな円相 |
| **意図** | 行動喚起。シンプルに締める |

---

## 統一デザインシステム（Nano Banana用プロンプト共通部分）

```
DESIGN SYSTEM (apply to all screenshots):
- Background: Deep charcoal #1A1918 with subtle washi paper texture
- Phone frame: iPhone 15 Pro, Space Black, no glow effects
- Headline font: Bold sans-serif (SF Pro Display Bold or similar), size 72pt, color #E5E4E2
- Subheadline font: Regular sans-serif, size 28pt, color #A0A09E
- Accent: Muted gold #C9B382 for subtle highlights only
- Layout: Generous whitespace, phone centered or slightly offset
- Tone: Zen, wabi-sabi, powerful simplicity. Like a stern but caring mentor.
- NO gradients, NO purple, NO glossy effects, NO illustrations
```

---

## 現行版との違い

| 項目 | 現行版 | 将来版（Proactive Agent） |
|------|--------|--------------------------|
| **1枚目** | AI Speaks First（音声） | End the Loop（問題提起） |
| **コア機能** | Voice Session | Nudge Card |
| **タブ** | Habits | My Path |
| **色味** | 紫グロー ❌ | 墨色・禅 ✅ |
| **トーン** | テック感 | 仏教的・禅師感 |

---

**この構成でMDファイルに保存してよければ、保存します。**

修正点やフィードバックがあれば教えてください。