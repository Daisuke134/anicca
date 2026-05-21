# Backend Best Practices Research

**調査日時**: 2026-01-26 20:22:22
**調査対象**: API Versioning, LLM Output Validation, Notification Scheduling, Cold Start, Feedback Loops

---

## 1. API Versioning and Backward Compatibility for Mobile Apps

### 調査結果

#### 核心原則
モバイルアプリは強制更新できないため、複数バージョンの API を同時にサポートする必要がある。

#### ベストプラクティス

| 手法 | 推奨度 | 説明 |
|------|--------|------|
| URI Versioning | ⭐⭐⭐ | `https://api.example.com/v1/users` - 最も明示的 |
| Header Versioning | ⭐⭐ | `X-API-Version: 1` - URI をクリーンに保つ |
| Query Parameters | ⭐ | `?version=1` - 見落としやすい |

#### 安全な変更 vs 破壊的変更

**安全な変更（Safe Changes）:**
- オプショナルパラメータの追加
- 新しいレスポンスフィールドの追加（クライアントは無視する）
- 新しいエンドポイントの追加
- 機能の非推奨化（事前通知付き）

**破壊的変更（Breaking Changes - 絶対禁止）:**
- パラメータ型の変更
- オプショナルパラメータを必須に変更
- エンドポイントの削除・リネーム
- レスポンス構造の変更

#### 長期サポート戦略

| ステップ | タイムライン | 実装 |
|---------|-------------|------|
| 新バージョンリリース | Day 0 | 旧バージョンと並行稼働 |
| 非推奨通知 | 6-12ヶ月前 | ドキュメント・ヘッダー・メールで通知 |
| 段階的移行 | 3-6ヶ月 | Feature Flag で 5% → 50% → 100% |
| 旧バージョン削除 | 95%+ 移行後 | ユーザーの 95% が新バージョンに移行してから |

#### テスト戦略
- 全バージョンに対するユニットテスト
- CI/CD で各バージョンのレスポンススキーマを検証
- 異なるアプリバージョンをシミュレートした自動テスト

### 情報源
- [API Versioning Best Practices for Backward Compatibility | Endgrate](https://endgrate.com/blog/api-versioning-best-practices-for-backward-compatibility)
- [API Versioning: Strategies & Best Practices - xMatters](https://www.xmatters.com/blog/api-versioning-strategies)
- [API Versioning Strategies: Best Practices Guide](https://daily.dev/blog/api-versioning-strategies-best-practices-guide)

---

## 2. LLM Output Validation in Production Systems

### 調査結果

#### バリデーション手法の比較

| 手法 | 信頼性 | 複雑度 | 推奨度 |
|------|--------|--------|--------|
| Prompting + Parsing | 低 | 低 | ❌ |
| JSON Mode | 中 | 低 | ⚠️ シンタックスのみ保証 |
| Structured Outputs | 高 | 中 | ✅ スキーマ強制 |
| Function/Tool Calling | 高 | 中 | ✅ スキーマベース |

#### エラーハンドリング戦略

**1. 不完全なレスポンス検出**
```javascript
if (response.finish_reason !== 'stop') {
  // context window 制限、content filtering、ネットワーク中断
  // → リトライまたはフォールバック
}
```

**2. スキーマバリデーション**
```typescript
import Ajv from 'ajv';
const ajv = new Ajv();
const validate = ajv.compile(schema);

if (!validate(llmOutput)) {
  // バリデーション失敗
  console.error(validate.errors);
  // → リトライまたはフォールバック
}
```

**3. リトライ vs フォールバック**

| シナリオ | 戦略 | 実装 |
|---------|------|------|
| 一時的エラー | リトライ | 指数バックオフで最大3回 |
| パース失敗 | LLM に修正依頼 | プロンプトで具体的エラーを指摘 |
| 繰り返し失敗 | フォールバック | 事前定義されたルールベースコンテンツ |
| 拒否（Refusal） | 代替ワークフロー | ユーザーにメッセージ表示 |

#### プロダクション実装パターン

**OpenAI Structured Outputs:**
```typescript
const completion = await openai.chat.completions.create({
  model: "gpt-4o",
  messages: [...],
  response_format: {
    type: "json_schema",
    json_schema: {
      name: "nudge_content",
      strict: true,
      schema: nudgeSchema
    }
  }
});
```

**モニタリング:**
- AI observability プラットフォームで生成トレースを追跡
- バリデーション成功率をメトリクス化
- プロンプトが期待通り動作しているか定期確認（モデル更新で壊れる可能性）

#### セキュリティ
ユーザー入力をスキーマに組み込む前に徹底的にサニタイズ（悪意ある exploitation 防止）

### 情報源
- [How To Ensure LLM Output Adheres to a JSON Schema | Modelmetry](https://modelmetry.com/blog/how-to-ensure-llm-output-adheres-to-a-json-schema)
- [How JSON Schema Works for LLM Data](https://latitude-blog.ghost.io/blog/how-json-schema-works-for-llm-data/)
- [The guide to structured outputs and function calling with LLMs](https://agenta.ai/blog/the-guide-to-structured-outputs-and-function-calling-with-llms)

---

## 3. Notification Scheduling Systems for Mobile Apps

### 調査結果

#### タイミング戦略

| 戦略 | 効果 | 実装優先度 |
|------|------|----------|
| タイムゾーン尊重 | 必須 | ⭐⭐⭐ |
| サイレンス期間 | ユーザー体験向上 | ⭐⭐⭐ |
| 個別最適化送信時刻 | CTR +50% | ⭐⭐⭐ |
| 行動ベーストリガー | 関連性向上 | ⭐⭐ |

#### 実装パターン

**1. タイムゾーン処理**
```typescript
// ❌ NG: グローバルな一斉送信
schedule.push({
  time: "2026-01-27T09:00:00Z",
  allUsers: true
});

// ✅ OK: ユーザーのローカル時刻で送信
schedule.push({
  localTime: "09:00",  // ユーザーのタイムゾーンで
  timezone: user.timezone
});
```

**2. サイレンス期間**
```typescript
const silenceHours = {
  start: "22:00",  // ユーザーのローカル時刻
  end: "07:00"
};

if (isWithinSilencePeriod(scheduledTime, silenceHours)) {
  // 次の許可された時間帯まで遅延
  scheduledTime = getNextAllowedTime(scheduledTime, silenceHours);
}
```

**3. 行動ベーストリガー**
固定スケジュールではなく、ユーザー行動に基づいてトリガー：
- カートに追加 → 1時間後にリマインド
- 7日間非アクティブ → エンゲージメント通知
- 習慣完了 → 称賛通知

**4. スケジュール変更の処理**

| シナリオ | 実装 |
|---------|------|
| 日中のスケジュール変更 | 次回の計算タイミングで反映（即座に再スケジュールしない） |
| ユーザー設定変更 | 即座に既存スケジュールをキャンセル・再計算 |
| サーバー駆動の更新 | `/api/mobile/nudge/schedule` で日次取得 |

#### 既存スケジューラとの統合

**Anicca の現状:**
- `ProblemNotificationScheduler` - ルールベース（問題タイプごとに固定時刻）
- `NotificationScheduler` - サーバー駆動（認可とサーバー Nudge）
- `LLMNudgeCache` - LLM 生成コンテンツのキャッシュ

**推奨統合パターン:**
```
Server API (/api/mobile/nudge/schedule)
    ↓ 日次取得
LLMNudgeCache にキャッシュ
    ↓
NotificationScheduler が読み込み
    ↓
iOS UNUserNotificationCenter に登録
    ↓
スケジュール済み通知の実行
```

### 情報源
- [iOS push notifications guide (2026) | Pushwoosh](https://www.pushwoosh.com/blog/ios-push-notifications/)
- [App Push Notification Best Practices for 2026 - Appbot](https://appbot.co/blog/app-push-notifications-2026-best-practices/)
- [14 Push Notification Best Practices for 2026 | Reteno](https://reteno.com/blog/push-notification-best-practices-ultimate-guide-for-2026)

---

## 4. Cold Start Problem for Personalization Systems

### 調査結果

#### 問題の定義

| タイプ | 説明 | 影響 |
|--------|------|------|
| User Cold Start | 新規ユーザーの嗜好情報なし | 不適切なレコメンド |
| Item Cold Start | 新規アイテムのインタラクションなし | アイテムが推薦されない |
| System Cold Start | システム立ち上げ時にデータなし | 両方の問題 |

#### ウォームアップ戦略（優先順位順）

**1. 初期質問票（必須）**
```typescript
// サインアップ時に問題を選択させる（Anicca の既存実装）
const onboardingQuestions = {
  step: "struggles",
  minSelections: 1,
  maxSelections: 13,
  problems: ProblemType[]
};

// ✅ Anicca はすでにこれを実装済み（StrugglesStepView）
```

**推奨バランス:**
- 質問数: 3-7 個（多すぎると離脱）
- Spotify の例: お気に入りアーティスト・ジャンルを選択

**2. コンテキストデータの活用**
```typescript
const contextualData = {
  timezone: user.timezone,  // ローカル時刻の推測
  locale: user.locale,      // 言語・文化的嗜好
  deviceType: "iOS"         // プラットフォーム
};
```

**3. ハイブリッドフィルタリング**
```
新規ユーザー:
  Content-based filtering（問題タイプのメタデータ）
      +
  Collaborative filtering（似たユーザーの行動）
```

**4. デフォルトレコメンド戦略**

| 期間 | 戦略 | 理由 |
|------|------|------|
| 0-3日 | 人気コンテンツ | データ不足 |
| 4-7日 | 問題タイプベース + 人気 | 初期嗜好 + 実証済み |
| 8-14日 | 個別化開始 | 十分なフィードバック |
| 15日+ | 完全個別化 | 行動パターン確立 |

**5. ホームページプロモーション**
新規アイテムを目立つ位置に配置して初期インタラクションを促進

#### Anicca への適用

**現状:**
- ✅ オンボーディングで問題選択（StrugglesStepView）
- ✅ 問題タイプベースの Nudge（ProblemNotificationScheduler）
- ⚠️ LLM 生成 Nudge の個別化はまだ初期段階

**推奨改善:**
```typescript
// Phase 1: 新規ユーザー（0-7日）
if (userDays <= 7) {
  return getPopularNudgesForProblemType(user.problemTypes);
}

// Phase 2: ウォームアップ期間（8-14日）
if (userDays <= 14) {
  return hybridRecommendation(
    contentBased: user.problemTypes,
    collaborative: similarUsers
  );
}

// Phase 3: 完全個別化（15日+）
return personalizedNudge(user.fullHistory);
```

### 情報源
- [What is the Cold Start Problem in Recommender Systems? | freeCodeCamp](https://www.freecodecamp.org/news/cold-start-problem-in-recommender-systems/)
- [Cold start (recommender systems) - Wikipedia](https://en.wikipedia.org/wiki/Cold_start_(recommender_systems))
- [How to solve the "cold start problem" in an ML recommendation system - GoPractice](https://gopractice.io/product/how-to-solve-the-cold-start-problem-in-an-ml-recommendation-system/)

---

## 5. Feedback Loop Design for ML Systems

### 調査結果

#### フィードバックループの構造

```
Product Deployment
    ↓
Feedback Collection (Explicit + Implicit)
    ↓
Model Iteration
    ↓
Product Deployment (繰り返し)
```

#### Explicit vs Implicit Feedback

| 特性 | Explicit Feedback | Implicit Feedback |
|------|------------------|------------------|
| **データ量** | < 1% のインタラクション | 100% のインタラクション |
| **信頼性** | 高（直接的な評価） | 中（推測が必要） |
| **ユーザー負担** | 高（能動的アクション） | なし（自動収集） |
| **即時性** | 遅い | 即座 |
| **推奨用途** | 評価データセット構築 | リアルタイム改善 |

#### Implicit Feedback のシグナル

**Anicca Nudge への適用:**

| シグナル | 意味 | 収集方法 |
|---------|------|----------|
| 👍 タップ | 明確な肯定 | Explicit |
| 👎 タップ | 明確な否定 | Explicit |
| 無視（通知を開かない） | 弱い否定 | Implicit（既存実装あり） |
| 通知を開いたが即座に閉じる | 関連性なし | Implicit（要実装） |
| 通知を開いて 5 秒以上表示 | 関心あり | Implicit（要実装） |
| フォローアップアクション | 強い肯定 | Implicit（行動変容） |

#### フィードバック収集の実装

**Explicit Feedback（既存）:**
```swift
// ✅ Anicca はすでに実装済み
func handleFeedback(isPositive: Bool) {
  // 👍 または 👎 を API に送信
}
```

**Implicit Feedback（推奨追加）:**
```swift
struct NudgeEngagement {
  let nudgeId: String
  let opened: Bool              // 通知をタップしたか
  let timeSpent: TimeInterval   // カード表示時間
  let dismissed: Bool           // 閉じたか
  let actionTaken: Bool         // ボタンをタップしたか

  var engagementScore: Double {
    // スコア計算ロジック
    if !opened { return 0.0 }
    if dismissed && timeSpent < 2 { return 0.2 }
    if timeSpent > 5 { return 0.7 }
    if actionTaken { return 1.0 }
    return 0.5
  }
}
```

#### Feedback Attribution（帰属）

**問題: どの変更が効果をもたらしたか？**

| 手法 | 実装 | 推奨度 |
|------|------|--------|
| A/B テスト | ユーザーを 2 グループに分割、片方のみ変更 | ⭐⭐⭐ |
| 段階的ロールアウト | 5% → 50% → 100% で効果測定 | ⭐⭐ |
| 前後比較 | 変更前後のメトリクス比較 | ⭐（相関≠因果） |

**実装例:**
```typescript
// Feature Flag でグループ分け
const variant = user.id % 100 < 50 ? 'control' : 'experiment';

if (variant === 'experiment') {
  // 新しいプロンプト・アルゴリズムを使用
  nudge = getLLMNudgeV2(user);
} else {
  // 既存実装
  nudge = getLLMNudgeV1(user);
}

// 両グループの engagement を比較
```

#### モデル改善の 4 つの経路

| 手法 | 速度 | コスト | 効果 | 用途 |
|------|------|--------|------|------|
| System Prompt 調整 | 即座 | 低 | 中 | 迅速な改善 |
| RAG | 数日 | 中 | 高 | 知識拡張 |
| Fine-tuning | 数週間 | 高 | 最高 | ドメイン特化 |
| Evaluation Dataset | 継続的 | 低 | - | 品質測定 |

**推奨フロー（Anicca）:**
```
Week 1-4: System Prompt 調整（フィードバックに基づいて）
    ↓
Week 5-8: Evaluation Dataset 構築（ユーザー評価から）
    ↓
Week 9+: Fine-tuning 検討（十分なデータ蓄積後）
```

### 情報源
- [LLM Feedback Loop | Nebuly](https://www.nebuly.com/blog/llm-feedback-loop)
- [Feedback Loops in LLMOps | Medium](https://medium.com/@t.sankar85/feedback-loops-in-llmops-the-catalyst-for-continuous-improvement-061fcad0bcd9)
- [Building Machine Learning Pipelines - Chapter 13: Feedback Loops | O'Reilly](https://www.oreilly.com/library/view/building-machine-learning/9781492053187/ch13.html)

---

## まとめ

全5トピックについて、2026年1月時点の最新ベストプラクティスを調査しました。

### 共通テーマ

1. **段階的移行** - いきなり変更せず、フラグ・A/Bテスト・段階的ロールアウトで検証
2. **後方互換性** - モバイルアプリは強制更新できない前提で設計
3. **フォールバック戦略** - AI・外部サービスは失敗する前提で代替案を用意
4. **データ駆動** - 推測ではなく実測データで判断（A/Bテスト、メトリクス）
5. **ユーザー体験優先** - 技術的完璧さよりユーザーの負担軽減

### 次のステップ

各トピックについて具体的な実装推奨を別セクションで提示します。
