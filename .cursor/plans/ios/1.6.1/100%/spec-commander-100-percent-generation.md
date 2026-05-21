# Commander Agent 100% Nudge Generation 仕様書

## 概要

Commander Agentが必要なスロット数分のNudgeを確実に生成する。
**JSON Schema の `minItems/maxItems` を使用してLLMレベルで配列長を強制し、`finish_reason`検査と再試行ロジックで信頼性を担保する。**

---

## 問題（As-Is）

### 現象

| ユーザー | 結果 | 問題 |
|---------|------|------|
| User A | 0 nudges / 0 slots | Agentが何も生成しない |
| User B | 3 enabled / 6 slots | 必要数の半分しか生成しない |

### 根本原因

LLMは「プロンプトでのお願い」を無視できる。スキーマに長さ制約がないため、LLMは好きな数だけ生成して終わる。

```
[現状のフロー]
プロンプト「15件生成せよ」→ LLM「8件で十分かな」→ 8件返却 → 7件欠損
```

### 問題のコード

```javascript
// commander.js:48 - スキーマ定義
const AgentRawOutputSchema = z.object({
  rootCauseHypothesis: z.string(),
  overallStrategy: z.string(),
  frequencyReasoning: z.string(),
  appNudges: z.array(AppNudgeSchema),  // ❌ 長さ制約なし
  tiktokPosts: z.array(TiktokPostSchema).length(2),  // ✅ 2件強制
  xPosts: z.array(XPostSchema).length(2),  // ✅ 2件強制
});
```

---

## 解決策（To-Be）

### 核心: OpenAI Structured Outputs + 実行時検査 + 再試行

OpenAIの `strict: true` + `minItems/maxItems` を使用し、さらに`finish_reason`検査と再試行ロジックで信頼性を担保する。

```
[修正後のフロー]
JSON Schema「appNudges: minItems=15, maxItems=15」
  → LLM生成（max_tokens動的設定）
  → finish_reason検査（refusal/length/content_filterをチェック）
  → 正常: スキーマ検証 → 成功
  → length中断: max_tokens増加して再試行
  → 他の異常: 再試行 or フォールバック
```

### 重要な制限事項

OpenAI Structured Outputsは以下の場合にスキーマ準拠が保証されない:
1. **refusal**: 安全上の理由でモデルが拒否
2. **finish_reason=length**: max_tokensに達して中断
3. **content_filter**: コンテンツフィルターで中断

**したがって、「100%の信頼性」ではなく「高い信頼性 + エッジケース対応」として設計する。**

### 設計原則

| 責務 | 担当 | 変更可否 |
|------|------|---------|
| **時間スロット決定** | システム（scheduleMap + trimSlots） | Agent変更不可 |
| **配列長強制** | JSON Schema（minItems/maxItems） | システムが動的設定 |
| **異常検出** | finish_reason + refusal検査 | 必須 |
| **コンテンツ決定** | Commander Agent | 生成必須 |
| **ON/OFF決定** | Commander Agent | `enabled: true/false`で制御 |

---

## スキーマ定義（必須フィールド一覧）

### トップレベルスキーマ（AgentRawOutputSchema）

| フィールド | 型 | 必須/任意 | 説明 |
|-----------|------|---------|------|
| rootCauseHypothesis | string | 必須 | 根本原因仮説 |
| overallStrategy | string | 必須 | 全体戦略 |
| frequencyReasoning | string | 必須 | 頻度設定理由 |
| appNudges | array | 必須 | アプリNudge配列（長さ=slotCount） |
| tiktokPosts | array | 必須 | TikTok投稿配列（長さ=2） |
| xPosts | array | 必須 | X投稿配列（長さ=2） |

### AppNudgeSchema

| フィールド | 型 | 必須/任意 | 説明 |
|-----------|------|---------|------|
| slotIndex | number | 必須 | スロット番号（0以上の整数） |
| hook | string | 必須 | 通知タイトル |
| content | string | 必須 | 詳細内容 |
| tone | enum | 必須 | 'strict'/'gentle'/'empathetic'/'analytical'/'playful' |
| enabled | boolean | 必須 | 有効/無効フラグ |
| reasoning | string | 必須 | 生成理由 |

### TiktokPostSchema

| フィールド | 型 | 必須/任意 | 説明 |
|-----------|------|---------|------|
| slot | enum | 必須 | 'morning'/'evening' |
| caption | string | 必須 | キャプション（最大2200文字） |
| hashtags | array | 必須 | ハッシュタグ配列（最大5件） |
| tone | string | 必須 | トーン |
| reasoning | string | 必須 | 生成理由 |
| enabled | boolean | **必須** | 有効/無効フラグ **← 本仕様で追加**（レガシーデータはundefined=true扱い） |

### XPostSchema

| フィールド | 型 | 必須/任意 | 説明 |
|-----------|------|---------|------|
| slot | enum | 必須 | 'morning'/'evening' |
| text | string | 必須 | ツイートテキスト（最大280文字） |
| reasoning | string | 必須 | 生成理由 |
| enabled | boolean | **必須** | 有効/無効フラグ **← 本仕様で追加**（レガシーデータはundefined=true扱い） |

**レガシーデータ互換性**:
- **tiktokPosts/xPosts**: 本仕様以前のデータでは`enabled`フィールドが存在しない場合がある。下流処理では`enabled !== false`でフィルタすることで、レガシーデータ（undefined）を`enabled=true`として扱う。
- **appNudges**: 既存データにはすでに`enabled`フィールドが存在するため、レガシー救済は不要。新規生成でも`enabled`は必須。

---

## 下流利用箇所とバリデーション

### tiktokPosts の下流

| 利用箇所 | ファイル | 処理内容 | enabled参照 |
|---------|---------|---------|-------------|
| TikTok Agent GHA | `routes/admin/tiktok.js` | `/api/admin/tiktok/pending` でpending投稿取得 | **フィルタ追加（本仕様）** |
| notification_schedules保存 | `jobs/generateNudges.js` | `agentRawOutput`に格納 | なし（そのまま保存） |

**利用フィールド**: `caption`, `hashtags`, `tone`, `reasoning`, `slot`, `enabled`

### xPosts の下流

| 利用箇所 | ファイル | 処理内容 | enabled参照 |
|---------|---------|---------|-------------|
| X Agent GHA | `routes/admin/xposts.js` | `/api/admin/x/pending` でpending投稿取得 | **フィルタ追加（本仕様）** |
| notification_schedules保存 | `jobs/generateNudges.js` | `agentRawOutput`に格納 | なし（そのまま保存） |

**利用フィールド**: `text`, `reasoning`, `slot`, `enabled`

### フォールバック出力の契約

| フィールド | 件数 | enabled | 理由 |
|-----------|------|---------|------|
| appNudges | slotTable.length | **true** | アプリ通知は必ず配信 |
| tiktokPosts | 2 | **false** | スキーマ準拠だが投稿しない |
| xPosts | 2 | **false** | スキーマ準拠だが投稿しない |

**投稿抑止の仕組み**:
1. フォールバック時は `tiktokPosts[*].enabled = false`、`xPosts[*].enabled = false` を設定
2. `/api/admin/tiktok/pending` と `/api/admin/x/pending` で `enabled !== false` をフィルタ
   - `enabled=true` → 含まれる
   - `enabled=false` → 除外される
   - `enabled=undefined`（レガシー） → 含まれる（true扱い）
3. GHAは `enabled=false` のポストを取得しないため、投稿されない

---

## 実装変更

### 1. 動的スキーマ生成（OpenAI互換）

**ファイル**: `apps/api/src/agents/commander.js`

```javascript
/**
 * スロット数に応じた動的スキーマを生成
 * OpenAIのStrictモード互換を確保
 * @param {number} slotCount - 必要なNudge数
 */
function createAgentOutputSchema(slotCount) {
  return z.object({
    rootCauseHypothesis: z.string(),
    overallStrategy: z.string(),
    frequencyReasoning: z.string(),
    appNudges: z.array(AppNudgeSchema).min(slotCount).max(slotCount),  // ✅ 長さ強制
    tiktokPosts: z.array(TiktokPostSchema).length(2),
    xPosts: z.array(XPostSchema).length(2),
  });
}

// ✅ TiktokPostSchema にenabled追加（必須フィールド）
const TiktokPostSchema = z.object({
  slot: TiktokPostSlot,
  caption: z.string().max(2200),
  hashtags: z.array(z.string()).max(5),
  tone: z.string(),
  reasoning: z.string(),
  enabled: z.boolean(),  // ✅ 必須（OpenAI strict mode要件）
});

// ✅ XPostSchema にenabled追加（必須フィールド）
const XPostSchema = z.object({
  slot: XPostSlot,
  text: z.string().max(280),
  reasoning: z.string(),
  enabled: z.boolean(),  // ✅ 必須（OpenAI strict mode要件）
});

/**
 * ZodスキーマをOpenAI互換JSON Schemaに変換
 * OpenAIのサブセット制限に適合することを確認
 */
function toOpenAIJsonSchema(zodSchema, name) {
  const jsonSchema = zodToJsonSchema(zodSchema, { name });
  // additionalProperties: false を全オブジェクトに設定（OpenAI要件）
  return ensureAdditionalPropertiesFalse(jsonSchema);
}

/**
 * スロット数に基づくmax_tokensの推定
 * 1 Nudge ≈ 150 tokens、基本オーバーヘッド ≈ 500 tokens
 */
function estimateMaxTokens(slotCount, attempt = 0) {
  const baseTokens = 500;
  const tokensPerNudge = 150;
  const tiktokXTokens = 400;  // 2 TikTok + 2 X posts
  const buffer = 1.3 + (attempt * 0.2);  // 再試行ごとにバッファ増加
  
  return Math.ceil((baseTokens + (slotCount * tokensPerNudge) + tiktokXTokens) * buffer);
}
```

### 2. OpenAI API呼び出し + finish_reason検査 + max_tokens動的調整

**ファイル**: `apps/api/src/agents/commander.js`

```javascript
export async function runCommanderAgent({ 
  grounding, 
  model = 'gpt-4o-2024-08-06',
  slotCount,
  maxRetries = 2  // ✅ 再試行を維持
}) {
  const schema = createAgentOutputSchema(slotCount);
  const jsonSchema = toOpenAIJsonSchema(schema, 'commander_output');
  
  let lastError = null;
  
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      // ✅ 再試行ごとにmax_tokensを増加
      const maxTokens = estimateMaxTokens(slotCount, attempt);
      
      const response = await openai.chat.completions.create({
        model,
        messages: buildMessages(grounding),
        max_tokens: maxTokens,  // ✅ 動的設定
        response_format: {
          type: "json_schema",
          json_schema: {
            name: "commander_output",
            strict: true,
            schema: jsonSchema
          }
        }
      });
      
      const choice = response.choices[0];
      
      // ✅ finish_reason検査
      if (choice.finish_reason === 'length') {
        throw new Error(
          `Output truncated (finish_reason=length). ` +
          `max_tokens=${maxTokens} was insufficient. Will retry with higher limit.`
        );
      }
      
      if (choice.finish_reason === 'content_filter') {
        throw new Error(
          `Content filtered (finish_reason=content_filter). ` +
          `Generation was halted by content moderation.`
        );
      }
      
      if (choice.finish_reason !== 'stop') {
        throw new Error(
          `Unexpected finish_reason: ${choice.finish_reason}. Expected 'stop'.`
        );
      }
      
      // ✅ refusal検査
      if (choice.message.refusal) {
        throw new Error(`Model refused: ${choice.message.refusal}`);
      }
      
      // ✅ スキーマ検証（Structured Outputsでも必須）
      const content = JSON.parse(choice.message.content);
      const output = schema.parse(content);
      
      // ✅ 配列長の最終確認
      if (output.appNudges.length !== slotCount) {
        throw new Error(
          `Expected ${slotCount} nudges, got ${output.appNudges.length}`
        );
      }
      
      return output;
      
    } catch (error) {
      lastError = error;
      console.warn(`Commander attempt ${attempt + 1}/${maxRetries + 1} failed:`, error.message);
      
      if (attempt < maxRetries) {
        // 再試行前に待機（エクスポネンシャルバックオフ）
        await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, attempt)));
      }
    }
  }
  
  // 全再試行失敗 → エラーをthrow（呼び出し元でフォールバック処理）
  throw new Error(`Commander failed after ${maxRetries + 1} attempts: ${lastError?.message}`);
}
```

### 3. generateNudges.js でのフォールバック処理

**ファイル**: `apps/api/src/jobs/generateNudges.js`

```javascript
const { grounding, slotTable } = await collectAllGrounding(
  query, user.user_id, problems, preferredLanguage, appVersion
);

let agentOutput;
try {
  agentOutput = await runCommanderAgent({ 
    grounding,
    slotCount: slotTable.length
  });
} catch (error) {
  console.error('Commander failed, using rule-based fallback:', error.message);
  // ✅ フォールバック: ルールベースNudgeを使用
  agentOutput = generateRuleBasedFallback(slotTable, preferredLanguage);
}
```

### 4. ルールベースフォールバック（スキーマ完全準拠）

**ファイル**: `apps/api/src/agents/commander.js`

```javascript
/**
 * Commander失敗時のルールベースフォールバック
 * スキーマ完全準拠:
 * - appNudges: slotTable.length件、enabled=true
 * - tiktokPosts: 2件、enabled=false（投稿しない）
 * - xPosts: 2件、enabled=false（投稿しない）
 */
export function generateRuleBasedFallback(slotTable, preferredLanguage) {
  const isJa = preferredLanguage === 'ja';
  
  return {
    rootCauseHypothesis: 'Fallback mode - LLM generation failed',
    overallStrategy: 'Using rule-based content',
    frequencyReasoning: 'Maintaining scheduled frequency',
    
    // appNudges: スキーマ準拠（slotTable.length件、enabled=true）
    appNudges: slotTable.map((slot) => ({
      slotIndex: slot.slotIndex,
      hook: isJa ? '今日も前に進もう' : 'Keep moving forward',
      content: isJa ? '小さな一歩から始めよう。' : 'Start with a small step.',
      tone: 'gentle',
      enabled: true,  // ✅ アプリ通知は配信する
      reasoning: 'Rule-based fallback due to LLM failure',
    })),
    
    // tiktokPosts: スキーマ準拠（2件、enabled=false）
    tiktokPosts: [
      {
        slot: 'morning',
        caption: isJa ? '変わりたいなら今日から' : 'Change starts today',
        hashtags: ['#mindfulness', '#growth'],
        tone: 'gentle',
        reasoning: 'Fallback placeholder - not for posting',
        enabled: false,  // ✅ フォールバック時は投稿しない
      },
      {
        slot: 'evening',
        caption: isJa ? '自分を責めないで' : "Don't blame yourself",
        hashtags: ['#selfcare', '#mentalhealth'],
        tone: 'gentle',
        reasoning: 'Fallback placeholder - not for posting',
        enabled: false,
      },
    ],
    
    // xPosts: スキーマ準拠（2件、enabled=false）
    xPosts: [
      {
        slot: 'morning',
        text: isJa ? '今日も一歩前へ' : 'One step forward today',
        reasoning: 'Fallback placeholder - not for posting',
        enabled: false,  // ✅ フォールバック時は投稿しない
      },
      {
        slot: 'evening',
        text: isJa ? '深呼吸しよう' : 'Take a deep breath',
        reasoning: 'Fallback placeholder - not for posting',
        enabled: false,
      },
    ],
  };
}
```

### 5. 下流pendingエンドポイントにenabledフィルタ追加

**ファイル**: `apps/api/src/routes/admin/tiktok.js`

```javascript
// /api/admin/tiktok/pending
router.get('/pending', async (req, res) => {
  // ... existing code ...
  
  for (const tp of candidates) {
    if (slot && tp.slot !== slot) continue;
    // ✅ enabled=false をフィルタ（フォールバックポストを除外）
    if (tp.enabled === false) continue;
    
    tiktokPosts.push({
      caption: tp.caption,
      hashtags: tp.hashtags || [],
      tone: tp.tone,
      reasoning: tp.reasoning,
      slot: tp.slot,
      sourceUserId: s.userId,
      scheduleId: s.id,
    });
  }
  // ...
});
```

**ファイル**: `apps/api/src/routes/admin/xposts.js`

```javascript
// /api/admin/x/pending
router.get('/pending', async (req, res) => {
  // ... existing code ...
  
  for (const xp of candidates) {
    if (slot && xp.slot !== slot) continue;
    // ✅ enabled=false をフィルタ（フォールバックポストを除外）
    if (xp.enabled === false) continue;
    
    xPosts.push({
      text: xp.text,
      reasoning: xp.reasoning,
      slot: xp.slot,
      sourceUserId: s.userId,
      scheduleId: s.id,
    });
  }
  // ...
});
```

---

## OpenAI Structured Outputs の制限事項

### サポートされるJSON Schemaサブセット

| サポート | 非サポート |
|---------|-----------|
| type, properties, required | allOf, not, if/then/else |
| items, minItems, maxItems | oneOf（一部制限あり） |
| enum, const | patternProperties |
| additionalProperties: false | 複雑な$ref |

### 必須要件

1. **additionalProperties: false** を全オブジェクトに設定
2. **required** に全プロパティを列挙
3. スキーマの最大5000プロパティ、最大10階層

---

## テスト計画

### ユニットテスト

| テスト | 期待結果 |
|-------|---------|
| `createAgentOutputSchema(5)` のJSONスキーマにminItems=5, maxItems=5が含まれる | Pass |
| 生成されたJSONスキーマがOpenAIサブセット制限に適合 | Pass |
| finish_reason='length'でエラーをthrow | Pass |
| finish_reason='content_filter'でエラーをthrow | Pass |
| refusal検出でエラーをthrow | Pass |
| 3回失敗後にフォールバックが呼ばれる | Pass |
| `estimateMaxTokens(15, 0)` が適切な値を返す | Pass |
| `estimateMaxTokens(15, 2)` が attempt=0 より大きい値を返す | Pass |

### フォールバック検証テスト

| テスト | 期待結果 |
|-------|---------|
| フォールバック出力の `appNudges.length` が `slotTable.length` と一致 | Pass |
| フォールバック出力の `tiktokPosts.length` が 2 | Pass |
| フォールバック出力の `xPosts.length` が 2 | Pass |
| フォールバック出力が通常スキーマ `createAgentOutputSchema(N)` でparse可能 | Pass |
| フォールバックの `appNudges[*].enabled` が true | Pass |
| フォールバックの `tiktokPosts[*].enabled` が false | Pass |
| フォールバックの `xPosts[*].enabled` が false | Pass |
| フォールバックの `tiktokPosts[*].slot` が 'morning'/'evening' | Pass |
| フォールバックの `xPosts[*].slot` が 'morning'/'evening' | Pass |

### 下流フィルタテスト

**注意**: 新規生成データでは`enabled`は必須。レガシーデータ（本仕様以前）では`enabled`が未定義の場合があり、その場合は`enabled=true`として扱う。

| テスト | 期待結果 |
|-------|---------|
| `/api/admin/tiktok/pending` で enabled=false のポストが除外される | Pass |
| `/api/admin/x/pending` で enabled=false のポストが除外される | Pass |
| `/api/admin/tiktok/pending` で enabled=true のポストが含まれる | Pass |
| `/api/admin/x/pending` で enabled=true のポストが含まれる | Pass |
| **（レガシー救済）** `/api/admin/tiktok/pending` で enabled未定義のポストがenabled=true扱いで含まれる | Pass |
| **（レガシー救済）** `/api/admin/x/pending` で enabled未定義のポストがenabled=true扱いで含まれる | Pass |

### 統合テスト

| テスト | 期待結果 |
|-------|---------|
| 15スロットのユーザーでgenerateNudges実行 | 15件のnudge生成 or フォールバック |
| OpenAI APIモックでrefusal返却 | フォールバックに移行 |
| OpenAI APIモックでfinish_reason='length'返却 | max_tokens増加して再試行 |
| OpenAI APIモックでfinish_reason='content_filter'返却 | 再試行後フォールバック |
| フォールバック時にtiktok/pending が空を返す | Pass |
| フォールバック時にx/pending が空を返す | Pass |

### スキーマ適合テスト

```javascript
// OpenAI APIに実際にスキーマを送信して検証
it('schema is accepted by OpenAI', async () => {
  const schema = createAgentOutputSchema(5);
  const jsonSchema = toOpenAIJsonSchema(schema, 'test');
  
  const response = await openai.chat.completions.create({
    model: 'gpt-4o-2024-08-06',
    messages: [{ role: 'user', content: 'Generate test output' }],
    response_format: {
      type: 'json_schema',
      json_schema: { name: 'test', strict: true, schema: jsonSchema }
    },
    max_tokens: 10
  });
  
  expect(response.choices[0].finish_reason).toBeDefined();
});

// フォールバックがスキーマ準拠
it('fallback output conforms to schema', () => {
  const slotTable = [{ slotIndex: 0 }, { slotIndex: 1 }];
  const fallback = generateRuleBasedFallback(slotTable, 'en');
  const schema = createAgentOutputSchema(2);
  
  expect(() => schema.parse(fallback)).not.toThrow();
  expect(fallback.appNudges).toHaveLength(2);
  expect(fallback.tiktokPosts).toHaveLength(2);
  expect(fallback.xPosts).toHaveLength(2);
  expect(fallback.appNudges.every(n => n.enabled === true)).toBe(true);
  expect(fallback.tiktokPosts.every(p => p.enabled === false)).toBe(true);
  expect(fallback.xPosts.every(p => p.enabled === false)).toBe(true);
});
```

---

## 影響範囲

| ファイル | 変更内容 |
|---------|---------|
| `apps/api/src/agents/commander.js` | 動的スキーマ生成、finish_reason検査、max_tokens動的調整、再試行ロジック、enabled追加 |
| `apps/api/src/jobs/generateNudges.js` | フォールバック呼び出し追加 |
| `apps/api/src/routes/admin/tiktok.js` | enabled=falseフィルタ追加 |
| `apps/api/src/routes/admin/xposts.js` | enabled=falseフィルタ追加 |
| `apps/api/src/agents/__tests__/commander.test.js` | スキーマ検証テスト、finish_reasonテスト、フォールバックテスト追加 |
| `apps/api/src/routes/admin/__tests__/tiktok.test.js` | enabledフィルタテスト追加 |
| `apps/api/src/routes/admin/__tests__/xposts.test.js` | enabledフィルタテスト追加 |

---

## Before/After 比較

| 項目 | Before | After |
|------|--------|-------|
| 配列長制約 | なし（プロンプトのみ） | JSON Schema minItems/maxItems |
| 信頼性 | 40%以下 | 高い信頼性 + エッジケース対応 |
| finish_reason検査 | なし | 必須（refusal/length/content_filter検出） |
| max_tokens | 固定 or なし | 動的設定 + 再試行時増加 |
| 再試行 | maxRetries=2 | maxRetries=2 + エクスポネンシャルバックオフ |
| スキーマ検証 | なし | schema.parse必須 |
| フォールバック appNudges | enabled=false | enabled=true（アプリ通知は配信） |
| フォールバック tiktok/x | 空配列 | 2件ずつ、enabled=false（投稿しない） |
| tiktok/x pendingフィルタ | なし | enabled=falseを除外 |

---

## リスク

| リスク | 対策 |
|-------|------|
| OpenAIのサブセット制限でスキーマ拒否 | スキーマ適合テストで事前検証 |
| refusal/length/content_filter中断 | finish_reason検査 + max_tokens増加 + 再試行 + フォールバック |
| zod-to-json-schemaの非互換 | OpenAI SDKヘルパーまたは`openai-zod-to-json-schema`検討 |
| フォールバックの下流互換性 | スキーマ完全準拠 + enabled=falseフィルタで投稿防止 |

---

## デプロイ

1. Backend変更のみ（iOS変更なし）
2. dev → Staging テスト
3. main → Production デプロイ
4. Cronログで「0 nudges」が発生しないことを確認
5. フォールバック発生時にTikTok/X投稿が行われないことを確認

---

*Last updated: 2026-02-02*
