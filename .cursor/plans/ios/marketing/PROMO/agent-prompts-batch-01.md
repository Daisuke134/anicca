
## 共通ルール（全エージェント共通）

### 必須参照ファイル
- **完成例**: `/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/creatives/video-01-3am-scrolling.md`
- **完成例**: `/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/creatives/video-02-three-day-habit.md`
- **Hook型カタログ**: `/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/hooks.md`
- **Klingベスプラ**: `/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/best-kilng-prompt.md`
- **Nano Bananaベスプラ**: `/Users/cbns03/Downloads/anicca-project/examples/awesome-nano-banana-pro-prompts/README.md`
- **Desmondのアドバイス**: `/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/desmond.md`

### 出力ファイル形式
- 保存先: `/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/creatives/`
- ファイル名: `video-XX-[slug].md` または `carousel-XX-[slug].md`
- 粒度: video-01, video-02と同じ詳細さ

### 音声発声ルール
- **Anicca → Aniicha** と表記して正しい発音に寄せる

### Hookルール（最重要・絶対遵守）
- **Hookは“型”から作る**（独自の思いつき禁止）。必ず以下を参照して作る:
  - `plan.md` の「Hook/サムネイルパターン（バイラル参考例）」
  - `hooks.md`（Fekriの勝ち筋フォーマット）
- **各コンテンツでHook案を最低5つ**（EN/JPそれぞれ）提示すること
- その5つの中に **POV型を最低1つ必ず含める**
- **冒頭0-3秒の中央キャプション＝Hook（＝サムネ文字）**として成立する短さにする（原則1行）
- Hookが長くなる場合は **2行目以降**に“状況説明”を置き、Hook自体は短く保つ
- **意味が一発で通る**文にする（曖昧語だけのHook禁止）

### Nano Bananaプロンプトルール
- シーン1は添付なしで生成（ベースキャラクター）
- シーン2以降は「Use the uploaded reference image for the character's face and appearance.」をプロンプト冒頭に追加
- アスペクト比: 9:16
- スタイル: Cinematic, realistic
- 「No text in the image.」を忘れずに

### Klingプロンプトルール
- 冒頭に「Static camera shot.」を入れる
- 最後に「The camera remains fixed.」を入れる
- 動きは最小限に（Minimal movement）
- 入力画像を明記

### Arcads.aiスクリプトルール
- 構成: HOOK (0-5秒) → PROBLEM (5-15秒) → SOLUTION (15-25秒) → RESULT (25-35秒) → CTA (35-40秒)
- 会話調で台本っぽくならないように
- 発音: Aniicha

---

## プロンプト1: 動画03「自己嫌悪のループ」

```
# タスク

Aniccaアプリのプロモーション動画03「自己嫌悪のループ」のMDファイルを作成してください。

## 参照

1. まず以下のファイルを読んで、同じ粒度・構成で作成すること:
   - `/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/creatives/video-01-3am-scrolling.md`
   - `/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/creatives/video-02-three-day-habit.md`

2. 動画の元ネタは以下のplan.mdの「動画03」セクション:
   - `/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/plan.md`

3. ベストプラクティス参照:
   - Kling: `/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/best-kilng-prompt.md`
   - Desmond: `/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/desmond.md`

## 動画03の概要（plan.mdより）

- **Hook（EN）**: "You're not broken. You're just stuck."
- **Hook（JP）**: 「あなたは壊れてない。ただハマってるだけ」
- **構成**:
  - 0-3秒: 「また失敗した」「どうせ自分なんて」のテキスト渦巻き
  - 3-15秒: AI生成の人物が頭を抱える（暗い色調）
  - 15-25秒: Aniccaのボイス「"ダメな人"じゃなくて"傷ついている人"なんだ」
  - 25-30秒: 光が差し込む + ロゴ
- **理由**: Aniccaの核フレーズを直接使用。自己嫌悪に苦しむ人に深く刺さる

## 出力

`/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/creatives/video-03-self-hatred-loop.md`

以下を含めること:
- 基本情報テーブル
- なぜこの動画が効果的か
- 秒数別構成
- Hookパターン（EN/JP各3つ）
- 各プラットフォーム用キャプション（TikTok/IG/YT/X/Threads × EN/JP）
- Nano Bananaプロンプト（全シーン、添付指定付き）
- Klingプロンプト（全シーン、入力画像指定付き）
- Arcads.aiスクリプト（EN/JP）
- 成功指標
- 投稿結果記録テンプレート

## 注意

- 音声発声時は「Aniicha」と表記
- Aniccaの核フレーズ「"ダメな人"じゃなくて"傷ついている人"なんだ」を活かす
- 暗い色調から光が差し込む変容を視覚的に表現
- 自己嫌悪に苦しむ人の感情に寄り添う
```

---

## プロンプト2: 動画04「朝起きれない問題」

```
# タスク

Aniccaアプリのプロモーション動画04「朝起きれない問題」のMDファイルを作成してください。

## 参照

1. まず以下のファイルを読んで、同じ粒度・構成で作成すること:
   - `/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/creatives/video-01-3am-scrolling.md`
   - `/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/creatives/video-02-three-day-habit.md`

2. 動画の元ネタは以下のplan.mdの「動画04」セクション:
   - `/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/plan.md`

3. ベストプラクティス参照:
   - Kling: `/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/best-kilng-prompt.md`
   - Desmond: `/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/desmond.md`

## 動画04の概要（plan.mdより）

- **Hook（EN）**: "If you can't wake up on time, stop scrolling."
- **Hook（JP）**: 「朝起きれない人、スクロール止めて」
- **構成**:
  - 0-3秒: アラーム10回スヌーズ → まだ寝てる
  - 3-15秒: 遅刻、慌てる、1日が台無し
  - 15-25秒: Anicca「起きよう。今日の君は起きられる」
  - 25-30秒: 7:00に自然に目覚める人 + ロゴ
- **理由**: 起床は最もわかりやすいユースケース

## 出力

`/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/creatives/video-04-cant-wake-up.md`

以下を含めること:
- 基本情報テーブル
- なぜこの動画が効果的か
- 秒数別構成
- Hookパターン（EN/JP各3つ）
- 各プラットフォーム用キャプション（TikTok/IG/YT/X/Threads × EN/JP）
- Nano Bananaプロンプト（全シーン、添付指定付き）
- Klingプロンプト（全シーン、入力画像指定付き）
- Arcads.aiスクリプト（EN/JP）
- 成功指標
- 投稿結果記録テンプレート

## 注意

- 音声発声時は「Aniicha」と表記
- スヌーズを押しまくる「あるある」を視覚的に表現
- 遅刻の慌ただしさと、自然に目覚める穏やかさのコントラスト
- 起床習慣はAniccaの主要ユースケース
```

---

## プロンプト3: 動画05「7日間チャレンジ結果」

```
# タスク

Aniccaアプリのプロモーション動画05「7日間チャレンジ結果」のMDファイルを作成してください。

## 参照

1. まず以下のファイルを読んで、同じ粒度・構成で作成すること:
   - `/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/creatives/video-01-3am-scrolling.md`
   - `/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/creatives/video-02-three-day-habit.md`

2. 動画の元ネタは以下のplan.mdの「動画05」セクション:
   - `/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/plan.md`

3. ベストプラクティス参照:
   - Kling: `/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/best-kilng-prompt.md`
   - Desmond: `/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/desmond.md`

## 動画05の概要（plan.mdより）

- **Hook（EN）**: "What 7 days with Anicca did to me"
- **Hook（JP）**: 「Aniccaを7日使ったらこうなった」
- **構成**:
  - 0-3秒: DAY 1 → DAY 7 のジャンプカット
  - 3-20秒: 各日のハイライト（AI生成画像スライド）
    - Day1: 懐疑的
    - Day3: 朝起きれた
    - Day5: 運動継続中
    - Day7: 自分で起きられた
  - 20-30秒: 「内なるAnicca」が育った + ロゴ
- **サムネ**: 「7 DAYS」+ 矢印 + 変容イメージ
- **理由**: 7日間チャレンジは高エンゲージメント。具体的な数字がクリック誘発

## 出力

`/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/creatives/video-05-7-day-challenge.md`

以下を含めること:
- 基本情報テーブル
- なぜこの動画が効果的か
- 秒数別構成（7日間のタイムラインを反映）
- Hookパターン（EN/JP各3つ）
- 各プラットフォーム用キャプション（TikTok/IG/YT/X/Threads × EN/JP）
- Nano Bananaプロンプト（全シーン、添付指定付き）
- Klingプロンプト（全シーン、入力画像指定付き）
- Arcads.aiスクリプト（EN/JP）
- 成功指標
- 投稿結果記録テンプレート

## 注意

- 音声発声時は「Aniicha」と表記
- Day 1 → Day 7 の変容を視覚的に表現
- 各日のハイライトを短く印象的に
- 「7日間チャレンジ」はTikTokで人気のフォーマット
```

---

## プロンプト4: カルーセル01「朝型になる5ステップ」

```
# タスク

Aniccaアプリのプロモーションカルーセル01「朝型になる5ステップ」のMDファイルを作成してください。

## 参照

1. まず以下のファイルを読んで、構成を理解すること:
   - `/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/creatives/video-01-3am-scrolling.md`
   - `/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/creatives/video-02-three-day-habit.md`

2. カルーセルの元ネタは以下のplan.mdの「カルーセル01」セクション:
   - `/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/plan.md`

3. Nano Bananaベストプラクティス参照:
   - `/Users/cbns03/Downloads/anicca-project/examples/awesome-nano-banana-pro-prompts/README.md`

## カルーセル01の概要（plan.mdより）

- **フォーマット**: 6枚のスライド画像（Instagram向け）
- **構成**:
  1. 表紙「朝型になりたい人へ」
  2. Step1: 寝る前1時間スマホ禁止
  3. Step2: 起床時刻を15分ずつ前倒し
  4. Step3: 朝一番に水を飲む
  5. Step4: 成功を記録する
  6. Step5: Aniccaに起こしてもらう → CTA
- **理由**: 「保存」されやすいリスト形式

## 出力

`/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/creatives/carousel-01-morning-person-5-steps.md`

以下を含めること:
- 基本情報テーブル
- なぜこのカルーセルが効果的か
- 各スライドの構成（テキスト + ビジュアル）
- 各プラットフォーム用キャプション（IG/Threads × EN/JP）
- Nano Bananaプロンプト（6枚分、一貫したデザインスタイル）
- 成功指標（保存数重視）
- 投稿結果記録テンプレート

## 注意

- カルーセルはNano Bananaのみ（Klingは不要）
- アスペクト比: 1:1（Instagram推奨）または 4:5
- 一貫したデザインスタイル（色、フォント、レイアウト）
- 各スライドにテキストオーバーレイ
- CTAは最後のスライドで明確に
```

---

## プロンプト5: カルーセル02「今夜やめるべき5つの習慣」

```
# タスク

Aniccaアプリのプロモーションカルーセル02「今夜やめるべき5つの習慣」のMDファイルを作成してください。

## 参照

1. まず以下のファイルを読んで、構成を理解すること:
   - `/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/creatives/video-01-3am-scrolling.md`
   - `/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/creatives/video-02-three-day-habit.md`

2. カルーセルの元ネタは以下のplan.mdの「カルーセル02」セクション:
   - `/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/plan.md`

3. Nano Bananaベストプラクティス参照:
   - `/Users/cbns03/Downloads/anicca-project/examples/awesome-nano-banana-pro-prompts/README.md`

## カルーセル02の概要（plan.mdより）

- **フォーマット**: 6枚のスライド（Instagram向け）
- **構成**:
  1. 表紙「睡眠を壊す5つの習慣」
  2. ベッドでスマホ
  3. カフェイン摂取
  4. 考え事をしながら寝る
  5. 不規則な就寝時刻
  6. 一人で戦おうとすること → Anicca紹介
- **理由**: ネガティブリストは注目されやすい

## 出力

`/Users/cbns03/Downloads/anicca-project/.cursor/plans/PROMO/creatives/carousel-02-5-habits-to-stop.md`

以下を含めること:
- 基本情報テーブル
- なぜこのカルーセルが効果的か
- 各スライドの構成（テキスト + ビジュアル）
- 各プラットフォーム用キャプション（IG/Threads × EN/JP）
- Nano Bananaプロンプト（6枚分、一貫したデザインスタイル）
- 成功指標（保存数重視）
- 投稿結果記録テンプレート

## 注意

- カルーセルはNano Bananaのみ（Klingは不要）
- アスペクト比: 1:1（Instagram推奨）または 4:5
- 一貫したデザインスタイル（色、フォント、レイアウト）
- 「❌」マークで視覚的に「やめるべき」を強調
- 最後のスライドで「✅ Aniccaがサポート」に転換
- ネガティブからポジティブへの流れを意識
```

---

## 使い方

1. 各プロンプトをコピー
2. 新しいCursorチャット（エージェントモード）を開く
3. プロンプトを貼り付けて実行
4. 5つ同時に並列実行可能

## 進捗管理

| # | タイプ | タイトル | エージェント | ステータス |
|---|--------|---------|-------------|-----------|
| 03 | 動画 | 自己嫌悪のループ | Agent A | 未着手 |
| 04 | 動画 | 朝起きれない問題 | Agent B | 未着手 |
| 05 | 動画 | 7日間チャレンジ | Agent C | 未着手 |
| C01 | カルーセル | 朝型になる5ステップ | Agent D | 未着手 |
| C02 | カルーセル | 今夜やめるべき5つの習慣 | Agent E | 未着手 |

