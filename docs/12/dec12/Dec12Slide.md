---
marp: true
header: ' '
footer: ' '
---

<style>
/* Google Fontsから日本語フォントを読み込み */
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');

/* --- 色やフォントの基本設定 --- */
:root {
  --color-background: #ffffff;
  --color-foreground: #1a1a1a;
  --color-heading: #000000;
  --color-accent: #2563eb;
  --color-hr: #000000;
  --font-default: 'Noto Sans JP', 'Hiragino Kaku Gothic ProN', 'Meiryo', sans-serif;
}

/* --- スライド全体のスタイル --- */
section {
  background: #ffffff;
  color: var(--color-foreground);
  font-family: var(--font-default);
  font-weight: 400;
  box-sizing: border-box;
  border-bottom: 4px solid var(--color-hr);
  position: relative;
  line-height: 1.8;
  font-size: 24px;
  padding: 56px;
}
section:last-of-type {
  border-bottom: none;
}

/* --- 見出しのスタイル --- */
h1, h2, h3, h4, h5, h6 {
  font-weight: 700;
  color: var(--color-heading);
  margin: 0;
  padding: 0;
}

/* タイトルページ(h1)のスタイル */
h1 {
  font-size: 48px;
  line-height: 1.4;
  text-align: left;
  color: #000000;
}

/* 通常スライドのタイトル(##) */
h2 {
  position: absolute;
  top: 40px;
  left: 56px;
  right: 56px;
  font-size: 36px;
  padding-top: 0;
  padding-bottom: 16px;
  color: #000000;
}

/* h2の疑似要素(::after)を使って、短い線を実装 */
h2::after {
  content: '';
  position: absolute;
  left: 0;
  bottom: 8px;
  width: 60px;
  height: 3px;
  background: #000000;
}

/* h2と後続コンテンツの間のスペースを確保 */
h2 + * {
  margin-top: 100px;
}

/* サブ見出し */
h3 {
  color: #333333;
  font-size: 26px;
  margin-top: 28px;
  margin-bottom: 12px;
}

/* --- リストのスタイル --- */
ul, ol {
  padding-left: 32px;
}
li {
  margin-bottom: 12px;
}

/* フッター */
footer {
  font-size: 0;
  color: transparent;
  position: absolute;
  left: 56px;
  right: 56px;
  bottom: 40px;
  height: 4px;
  background: #000000;
}

/* ヘッダー */
header {
  font-size: 0;
  color: transparent;
  position: absolute;
  top: 40px;
  left: calc(100% - 180px - 56px);
  width: 180px;
  height: 50px;
}

/* --- 特別なクラス --- */
section.lead {
  border-bottom: 4px solid var(--color-hr);
  display: flex;
  flex-direction: column;
  justify-content: center;
}

section.lead footer,
section.lead header {
  display: none;
}

section.lead h1 {
  margin-bottom: 24px;
  font-size: 52px;
}
section.lead p {
  font-size: 24px;
  color: var(--color-foreground);
}

/* ハイライトテキスト */
strong {
  color: #000000;
  font-weight: 700;
}

/* コードブロック風 */
code {
  background: #f3f4f6;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.9em;
  color: #000000;
}

/* 引用 */
blockquote {
  border-left: 4px solid #000000;
  padding-left: 20px;
  margin-left: 0;
  font-style: italic;
  color: #333333;
}

/* テーブル */
table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
}
th {
  background: #f3f4f6;
  color: #000000;
  padding: 12px;
  text-align: left;
  border: 1px solid #d1d5db;
}
td {
  padding: 12px;
  border: 1px solid #d1d5db;
  color: #000000;
  background: #ffffff;
}

/* 数字強調 */
.big-number {
  font-size: 64px;
  font-weight: 700;
  color: #000000;
}
</style>

<!-- ===== タイトルスライド ===== -->
<!-- _class: lead -->

# 個人開発における収益化への道のり

**12/14 発表**

---

## 今日お話しすること

### 概要

- 今年ずっとアプリ開発に取り組み、やっと収益化できた
  - アイディアから約2年 / 毎日開発を開始して約8ヶ月
- **$27 MRR**（月間経常収益） → 約4,000円
- 結論：**収益化に時間をかけ過ぎた。。**
- これまでの道のりを振り返り、収益化までの過程と反省を共有したい

---

## 作っているもの：Anicca

### 課題：主体性の欠如

**We are Bound by our lack of agency.**

- いつまで経っても習慣を形成できない
- 全てが3日坊主に
- 依存をやめられない
- 理想の自分になれない

---

## 対象ユーザー

### 従来のアプリでは続かない人

- 何を続けようとしても、継続できない状態が何年も続く
- 自分を信じられず、自己嫌悪に
- 苦しくて仕方ない

### なぜ従来のアプリでは不十分？

- 従来のアプリは、ユーザーに**主体性があることが前提**
- ユーザーが記録・投稿しないといけない
- 受動的にサポートするのではなく、**能動的にリードする存在**が必要

---

## 解決策：行動介入音声AI Anicca

### 機能

- 身につけたい習慣を行いたい時間を設定
- 毎日その時間にAniccaがその行動を促す（アラーム）
- 現在の行動に基づいて、リアルタイムで声掛け
  - フロントカメラ・スクリーン・アクティビティ
- 行動の詳細な可視化・記憶

### プラットフォーム

- iOS / Desktop アプリを提供中
- 有料版：月額1,500円・年間15,000円

---

## 現在の成果（12月）

<div style="display: flex; justify-content: space-around; align-items: center; margin-top: 60px;">
  <div style="text-align: center;">
    <div class="big-number">411</div>
    <div style="font-size: 24px; color: #333;">全ユーザー</div>
  </div>
  <div style="text-align: center;">
    <div class="big-number">$27</div>
    <div style="font-size: 24px; color: #333;">MRR（月間経常収益）<br>約4,000円</div>
  </div>
</div>

---

## アプリ開発に至った経緯

### 大学1年

- Peter Thielの「Zero to One」の動画を見て起業に興味
- ゼロから何かを作り出す
- 知り合いと習慣化アプリの開発を開始 → 怠惰で自然消滅
- 習慣化アプリの会社で1年間インターン（みんちゃレ）
  - → 自分はこのアプリでは習慣化できず、、

---

## アプリ開発に至った経緯

### 大学4年

- パブロフ型ニューロフィードバック論文を簡易的な脳波計で再現
- 注意散漫のフィードバックアプリを作成しGitHubで公開
  - **初めての個人開発**
- GPT4のおかげで「何かを作る」という経験ができた
- これが自信になり**大学院進学を決意**
- 脳波データを何時間も収集し、モデルを訓練 → 検出精度がイマイチで挫折

---

## アプリ開発に至った経緯

### 大学院

- 散漫状態の検出が難しく、モチベーション低下
- ニューロモジュレーションでマインドフルネスを促進 → 技術的問題で挫折

> **AIではどうか？**

---

## 開発履歴タイムライン

### 2024年1月〜7月
商用脳波計（Muse2）による注意散漫フィードバック
→ 検出できず＋対象ユーザーが少なすぎる

### 2024年12月〜2025年5月
Webカメラによる注意散漫フィードバック
→ 検出精度が不十分

### 2025年5月〜
画面状態を実況するAI（Google AI Studio）
→ 大西くんのフィードバックで改善

### 2025年6月〜現在
監視AI → 音声AIアシスタント → **介入型音声AI（Anicca）**

---

## $27 MRRまでにやったこと

### 基本戦略

- 家族・友達に使ってもらい、高速改善
- Aniccaの進捗をSNSに11月から継続投稿
  - X, TikTok, YouTube, Instagram
- とにかく、**フィードバック→改善の高速ループ**を続けた


---

## 使ったツール：開発

### Cursor一択（Maxプラン 200ドル）

- Claude Code ＜ Codex CLI ＜ **Cursor**
- Composer1が最高（早い・賢い）
- 小さめのタスク → Composer1
- 大きめのタスク → GPT5 Highで計画 → Composer1で実装

---

## 使ったツール：デザイン・マーケティング

### デザインツール

- **Mobbin / Figma**: UIデザインの改善
- **Sleek**: App Storeプレビュー画像作成
- **Superwall**: 課金誘導画面（ペイウォール）の改善

### マーケティング

- **Buffer**: SNSへの一括投稿ツール
- **VEED**: 動画編集AI
- **SideShift**: インフルエンサーへの依頼ツール、UGCコンテンツ作成

---

## 振り返りと反省

### 1年間考え続けたこと

> 「人間の行動変容に必要なコンテキストは何で、どう使えばいいか？」

**入力**: 基本プロファイル / スクリーン情報 / Gmail・Notion（MCP）
**出力**: 聴覚（声）/ 視覚（通知）/ 触覚（振動）

→ **最小限の介入で、最大限の行動変容を実現したい**

---

## 振り返りと反省

### 反省点

1. **大西くんのフィードバックを素直に反映し続けたらどうだったか？**
   - 画面行動を可視化するAI。人間行動の可視化・理解を極めてから、介入でも良かったかも
   - 自分のアイディアに籠り続けた反省。もっとユーザーと対話するべきだった

2. **収益化まで時間をかけすぎた**
   - アイディアから6ヶ月、全体だとほぼ2年
   - 顧客と対話して改善を繰り返し、早期の収益化を狙うべきだった

---

## 振り返りと反省

### 反省点（続き）

3. **必要ない機能に時間をかけすぎた**
   - Webアプリ
   - 音声駆動のオンボーディング
   - マルチエージェント
   - MCP連携

> **Make something people want.**

---

## 展望

### 今月のゴール

**MRR $100**（約15,000円）

### やること

- SNSの投稿を続ける
- **3,000再生の動画を作る**
- **能動性をAniccaに搭載する**

---

## 展望

### 長期ゴール

**10k MRR**（月収150万円）

- 起伏あれど、これ1本で生きていけそう
- ユーザーからのフィードバックの反映を最優先
- Aniccaに「人間行動」を根本的に理解させる

---

## Q&A

### 質疑応答

ご質問があればどうぞ！

---

## ありがとうございました

**Anicca - 行動変容のための音声AI**

- iOS / Desktop で利用可能
- 月額1,500円 / 年間15,000円

