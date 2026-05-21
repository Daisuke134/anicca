# OpenAI Realtime API 新機能実装計画（2025年8月）

## 🚀 新機能概要

OpenAIがRealtime APIに追加した革新的な機能により、Aniccaの能力が飛躍的に向上します。

## 📚 新機能詳細

### 1. **プロンプトストレージ機能（Reusable Prompts）**

#### 機能説明
OpenAI側のサーバーにプロンプト（指示文）を事前保存し、IDで呼び出す機能。

#### 現在の問題点
```javascript
// main-voice-simple.ts（873-973行）
// 毎回900行以上の巨大プロンプトを送信
const enhancedCommand = `
  【重要】ユーザーについての情報や好みに合わせて...
  // 900行の固定プロンプト（通信量が膨大）
`;
```

#### 新機能での実装
```javascript
// OpenAI側に事前登録
const prompts = {
  "anicca_morning_v1": {
    instructions: "朝会専用の詳細指示",
    tools: ["stripe_mcp", "github_mcp"],
    variables: { userName: "{{user}}" }
  },
  "anicca_meditation_v1": {
    instructions: "瞑想ガイド専用指示"
  }
};

// 使用時はIDを指定するだけ
await agent.updatePrompt({ 
  promptId: 'anicca_morning_v1',
  variables: { user: 'cbns03' }
});
```

#### ユーザー体験の変化
- **Before**: アプリ起動時に長い待機時間、応答が遅い
- **After**: 即座に応答開始、通信量90%削減、料金削減

---

### 2. **Out-of-band（帯域外）応答**

#### 機能説明
メイン会話と独立して並列で動く「もう一つの頭脳」。会話履歴を汚染せずにバックグラウンド処理が可能。

#### 実装例
```javascript
// メイン会話
ユーザー: 「今日の予定を教えて」
Anicca: 「10時にミーティングがあります」

// 同時にOut-of-bandで3つの分析を実行（裏側）
const [emotion, urgency, context] = await Promise.all([
  response.create({
    conversation: "none",  // 会話履歴に残さない
    metadata: { type: "emotion_analysis" },
    instructions: "ユーザーの疲労度を分析"
  }),
  response.create({
    conversation: "none",
    instructions: "緊急タスクをチェック"
  }),
  response.create({
    conversation: "none",
    instructions: "関連情報を事前収集"
  })
]);

// 分析結果を次の応答に反映
if (emotion.fatigue > 0.8) {
  // 疲れているなら優しいトーンに自動切替
  session.update({ voice: "shimmer", speed: 0.9 });
}
```

#### 活用ユースケース
1. **自動モード切替**: 時間帯や状況に応じて自動的にモード変更
2. **先読み情報収集**: ユーザーが質問する前に関連情報を準備
3. **異常検知**: バックグラウンドでSlackやGitHubを監視
4. **学習と改善**: 会話後に分析して次回に活かす

#### ユーザー体験の変化
- **Before**: 「分析中...」と待たされる、単一タスクのみ
- **After**: 待ち時間ゼロ、複数の処理が同時進行、より賢い応答

---

### 3. **Image Input（画像入力）機能**

#### 機能説明
画像をAIが「見て理解」できるマルチモーダル対応。

#### 従来との違い
```javascript
// Before（Playwright MCPのみ）
await playwrightMCP.screenshot();
// → 画像は撮れるが内容は理解できない

// After（Image Input対応）
await session.sendMessage({
  content: [
    { type: "input_image", image: screenshotBase64 },
    { type: "input_text", text: "エラーを診断して" }
  ]
});
// → AIが画像を見て内容を理解・説明できる
```

#### Aniccaでの活用例
```javascript
// エラー診断機能
ユーザー: 「エラー出てる、見て」
Anicca: （自動でスクショ撮影）
       「VSCodeの87行目でTypeErrorが発生していますね。
        変数userが未定義です。constで宣言を追加しましょう」

// コードレビュー
ユーザー: 「このコード大丈夫？」
Anicca: （画面解析）
       「async/awaitが抜けています。
        これだとPromiseが解決されずにメモリリークの可能性があります」

// UIフィードバック
ユーザー: 「デザインどう？」
Anicca: 「ボタンの配置は良いですが、
        背景とのコントラストが2.5:1で、WCAG基準の4.5:1を満たしていません」
```

#### ユーザー体験の変化
- **Before**: エラー内容を口頭で説明する必要がある
- **After**: 「見て」と言うだけで画面を理解して診断

---

### 4. **Remote MCP Server Support**

#### 機能説明
外部MCPサーバーと直接接続し、ツールを自動実行。

#### 実装例
```javascript
// mainAgent.tsに追加
tools: [
  {
    type: "mcp",
    server_url: "https://mcp.stripe.com",
    authorization: stripeApiKey,
    require_approval: "never"
  },
  {
    type: "mcp",
    server_url: "https://mcp.github.com",
    authorization: githubToken
  }
]
```

#### 朝会タスクでの活用
```javascript
async function morningBriefing() {
  // 全て音声だけで完結
  const report = await Promise.all([
    stripeMCP.getRevenue(),      // 売上確認
    githubMCP.getIssues(),        // Issue確認
    calendarMCP.getTodayEvents()  // 予定確認
  ]);
  
  return `
    おはようございます！
    昨日の売上：${report[0].amount}円
    緊急Issue：${report[1].critical.length}件
    今日の予定：${report[2].events.join(', ')}
  `;
}
```

#### ユーザー体験の変化
- **Before**: 各サービスを手動で確認
- **After**: 「朝会始めて」の一言で全情報を音声レポート

---

### 5. **カスタムコンテキスト機能**

#### 機能説明
会話履歴から必要な部分だけを選択的に参照。

#### 実装例
```javascript
// 会話を自動分類
class ContextManager {
  private contexts = {
    work: ["item_id_1", "item_id_2"],      // 仕事関連
    personal: ["item_id_3"],               // 個人的
    schedule: ["item_id_4", "item_id_5"]   // スケジュール
  };
  
  // 仕事の話をするときは仕事コンテキストのみ参照
  async respondAboutWork(question) {
    return response.create({
      input: [
        ...this.contexts.work.map(id => ({
          type: "item_reference",
          id
        })),
        { type: "message", content: question }
      ]
    });
  }
}
```

#### ユーザー体験の変化
- **Before**: 長時間使うと関係ない会話が混ざって精度低下
- **After**: 文脈を完璧に理解、雑談を挟んでも本題に戻れる

---

### 6. **SIP Support（電話システム統合）**

#### 機能説明
電話システムと直接接続。Aniccaが電話応対可能に。

#### 活用例
```javascript
// Twilioと連携
const sipConfig = {
  type: "sip",
  endpoint: "sip:support@company.com"
};

// 電話受付
着信 → Anicca: 「お電話ありがとうございます」
発信者: 「注文状況を確認したい」
Anicca: （データベース検索）「注文番号をお願いします」
```

---

## 🎯 実装優先順位とロードマップ

### Phase 1（1週間で実装）
**プロンプトストレージ実装**
- 定期タスク用プロンプトの最適化
- 通信量削減、応答速度向上
- 実装ファイル: `mainAgent.ts`, `main-voice-simple.ts`

### Phase 2（2週間で実装）
**Remote MCP統合**
- Stripe売上確認の自動化
- GitHub Issue管理の効率化
- 朝会タスクの完全自動化

### Phase 3（1ヶ月で実装）
**カスタムコンテキスト管理**
- 会話の自動分類システム
- 長時間使用時の精度維持
- コンテキスト別応答の実装

### Phase 4（将来実装検討）
**Image Input活用**
- エラー診断アシスタント
- コードレビュー支援
- UI/UXフィードバック

**Out-of-band応答**
- バックグラウンド監視
- 並列情報収集
- 自動学習システム

---

## 💡 期待される効果

1. **パフォーマンス向上**
   - 通信量90%削減
   - 応答速度3倍向上
   - API料金50%削減

2. **ユーザー体験の革新**
   - 待ち時間ゼロ
   - より賢い応答
   - 完全ハンズフリー操作

3. **新しい可能性**
   - 画面を見て診断
   - 電話応対
   - 24時間監視

---

## 📝 実装時の注意点

1. **SDKバージョン**
   - `@openai/agents`の最新版を使用
   - Realtime API対応版であることを確認

2. **後方互換性**
   - 既存機能を壊さないよう段階的に実装

3. **テスト**
   - 各機能を個別にテスト
   - 統合テストも実施

---

作成日: 2025年8月30日
作成者: Anicca開発チーム

