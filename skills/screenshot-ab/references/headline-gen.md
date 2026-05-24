# ヘッドライン生成ループ

## Screen ロール定義

| # | ロール | 目的 | 例（EN） | 例（JA） |
|---|--------|------|---------|---------|
| 1 | Hero | コアバリュー。ストップ・ザ・スクロール | "Your Mind Deserves Better" | "あなたの心にもっと優しく" |
| 2 | 差別化 | 競合との違い | "Not Another Meditation App" | "瞑想アプリじゃない" |
| 3 | 人気機能 | 最も愛される機能 | "Nudges That Actually Work" | "本当に届くナッジ" |
| 4 | 社会的証明 | 結果/数字/レビュー | "87% Feel Better in 7 Days" | "7日で87%が変化を実感" |

## 採点基準（1-10）

| 基準 | 配点 | 内容 |
|------|------|------|
| Emotional Hook | 3 | 感情を動かすか。「ふーん」ではなく「え？」を引き出す |
| Specificity | 2 | 具体的か。「良いアプリ」ではなく「7日で変わる」 |
| Brevity | 2 | 短いか。最大8語（EN）/ 15文字（JA） |
| Curiosity Gap | 2 | 続きを見たくなるか。情報の隙間を作る |
| Locale Fit | 1 | その言語のネイティブとして自然か。翻訳調でないか |

**8/10+ で採用。7以下は却下。**

## 生成ループ

```
1. experiments.json の winning_patterns と losing_patterns を読む
2. anicca-app-context.md のペルソナ + 画面説明を読む
3. 各 Screen ロールに対して 10案生成（EN / JA 別々）
4. 各案を上記 5基準で自己採点
5. 8/10+ のみ残す
6. 各 Screen で最低 1案必要。不足なら再生成（max 3回）
7. 3回ループしても 8+ が出ない → Slack 警告して EXIT
```

## 出力フォーマット

```
## Iteration N

### EN Headlines
screen1: "HEADLINE" subtitle: "Subtitle text"
screen2: "HEADLINE" subtitle: "Subtitle text"
screen3: "HEADLINE" subtitle: "Subtitle text"
screen4: "HEADLINE" subtitle: "Subtitle text"

### JA Headlines
screen1: "ヘッドライン" subtitle: "サブテキスト"
screen2: "ヘッドライン" subtitle: "サブテキスト"
screen3: "ヘッドライン" subtitle: "サブテキスト"
screen4: "ヘッドライン" subtitle: "サブテキスト"

### スコアカード
| # | 基準 | s1 | s2 | s3 | s4 | 判定 |
|---|------|----|----|----|----|------|
| 1 | Emotional Hook | 9 | 8 | 8 | 7 | FAIL(s4) |
...

### 総合: PASS / FAIL → [次のアクション]
```

## EN / JA ルール

| ルール | 理由 |
|--------|------|
| **翻訳禁止** | EN→JA の直訳は不自然。各言語ネイティブのコピーライティング |
| **同じ Screen で同じメッセージ** | Screen 1 は両言語とも「コアバリュー」。表現は別 |
| **日本語は体言止め有効** | 「変わる、7日で。」のような倒置 + 体言止め |
| **英語は 2人称有効** | "You're not broken." "Your mind deserves..." |

## 勝ちパターン（experiments.json から参照）

- 感情的2人称（"Nobody talks about...", "You're not..."）→ 40x views
- 数字 + 結果（"87% in 7 days"）
- 否定形（"Not another...", "Stop trying to..."）

## 負けパターン（回避）

- 機能リスト（"Track, Measure, Improve"）
- 一般的な動詞（"Discover", "Explore", "Transform"）
- 長文（9語以上 / 16文字以上）
