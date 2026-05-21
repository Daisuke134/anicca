# Phase 11: Wisdom抽出・適用

> **バージョン**: 1.7.0
>
> **最終更新**: 2026-01-26
>
> **前提**: 1.6.0（シミュレーション基盤）完了後
>
> **状態**: 詳細化完了

---

## 1. 目標

**シミュレーション結果と実データからWisdomを抽出し、Nudge生成に適用する**

| 目標 | 詳細 |
|------|------|
| 校正ループ | シミュ予測 vs 実データを比較し、乖離があればペルソナを自動更新 |
| Wisdom抽出 | LLMで自然言語のWisdomを自動抽出 |
| Wisdom適用 | Nudge生成時にWisdomを参照して最適化 |

---

## 2. スコープ

### 2.1 前提（1.6.0で完了済み）

| 機能 | 状態 |
|------|------|
| DBスキーマ（wisdom, persona_update_history含む） | ✅ 完了 |
| ペルソナ生成（5-8個） | ✅ 完了 |
| EDSLシミュレーション | ✅ 完了 |
| TikTokデータ自動収集 | ✅ 完了 |
| Appフィードバック集計 | ✅ 完了 |

### 2.2 1.7.0でやること

| 機能 | 詳細 |
|------|------|
| 校正サービス | シミュ予測 vs 実データの比較、乖離検出 |
| ペルソナ自動更新 | LLMでペルソナを更新、履歴保存 |
| Wisdom抽出 | LLMで自然言語のWisdomを抽出 |
| Wisdom適用 | Nudge生成時にWisdomを参照 |
| 週次Cronジョブ | 校正・Wisdom抽出の自動実行 |

### 2.3 やらないこと（Out of Scope）

| 機能 | 理由 |
|------|------|
| Wisdomの手動編集UI | システムは完全自動。介入不要の設計思想 |
| Contextual Bandit実装 | セクション4で却下。LLM Wisdomのみ |
| マルチ言語Nudge生成 | 1.7.0では日本語固定。多言語は将来バージョン |
| A/Bテスト運用機能 | シミュレーション基盤で代替済み |
| リアルタイム校正 | 週次で十分。リアルタイムはオーバーエンジニアリング |
| Wisdom削除機能 | 自動UPSERTで上書き。手動削除は不要 |
| ダッシュボードUI | オプション（タスク#6）。1.7.0必須ではない |

---

## 3. ユーザーGUI作業

### 3.1 実装前（不要）

**1.6.0で全て完了済み。追加のGUI作業なし。**

### 3.2 実装中（不要）

**全て自動化。手動作業なし。**

### 3.3 運用時（オプション）

| 作業 | 頻度 | 詳細 |
|------|------|------|
| Wisdom確認 | 週1（任意） | DBでWisdom内容を確認 |
| ペルソナ更新履歴確認 | 週1（任意） | 自動更新が適切か確認 |

**注意：これらは確認のみ。介入は不要。システムは完全自動で動作。**

### 3.4 ローカライズ戦略

| 項目 | 1.7.0での対応 |
|------|--------------|
| **Nudge生成言語** | 日本語固定（プロンプト内で指定） |
| **Wisdom保存言語** | 日本語固定 |
| **多言語対応** | 1.7.0ではスコープ外（Out of Scope参照） |

**将来の多言語対応時:**
- `wisdom` テーブルに `locale` カラムを追加
- ユーザーの言語設定に基づいてWisdomを取得
- LLMプロンプトに言語指定を追加

### 3.5 Maestro E2Eテスト

**UI変更なしのため、Maestroテストは不要。**

| 理由 | 説明 |
|------|------|
| 画面追加なし | 全てバックエンド処理 |
| ボタン追加なし | ユーザー操作の変更なし |
| 既存フローへの影響なし | Nudge表示UIは既存のまま |

**テスト戦略:** Unit + Integration テストで十分。

---

## 4. なぜContextual Banditを使わないか

| 観点 | Contextual Bandit | LLM Wisdom（採用） |
|------|-------------------|-------------------|
| 出力 | 確率分布（説明不可） | 自然言語（説明可能） |
| 般化能力 | 見たことない状況に弱い | 抽象化されているから適用可能 |
| デバッグ | 困難（ブラックボックス） | 「このルールが間違い」と特定可能 |
| 哲学 | 統計的最適化 | ブッダ的な観察→抽象化→適用 |
| 理解可能性 | ❌ 開発者も理解困難 | ✅ 人間が読める |

**決定：全てLLM Wisdomで行く。Contextual Banditは使わない。**

---

## 5. アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    1.7.0 WISDOM SYSTEM                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ WEEKLY CALIBRATION (毎週日曜00:00 UTC)                          │   │
│  │                                                                  │   │
│  │  For each persona:                                              │   │
│  │    1. シミュ予測を取得（simulation_runs）                       │   │
│  │    2. 実データを取得（tiktok_ad_metrics + nudge_feedback）      │   │
│  │    3. 乖離計算: |predicted - actual| / predicted               │   │
│  │    4. IF 乖離 > 20%:                                            │   │
│  │       → LLMでペルソナ更新                                       │   │
│  │       → persona_update_historyに記録                            │   │
│  └──────────────────────────────┬──────────────────────────────────┘   │
│                                 ↓                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ WEEKLY WISDOM EXTRACTION (毎週日曜01:00 UTC)                    │   │
│  │                                                                  │   │
│  │  For each persona:                                              │   │
│  │    1. 過去7日のデータ取得                                       │   │
│  │       - simulation_runs                                        │   │
│  │       - tiktok_ad_metrics                                      │   │
│  │       - nudge_feedback                                         │   │
│  │    2. LLMでWisdom抽出                                           │   │
│  │       → 自然言語の原則（tone, timing, content, hook）          │   │
│  │    3. wisdomテーブルにUPSERT                                    │   │
│  └──────────────────────────────┬──────────────────────────────────┘   │
│                                 ↓                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ NUDGE GENERATION (リアルタイム)                                 │   │
│  │                                                                  │   │
│  │  1. ユーザーのProblemType → ペルソナ特定                        │   │
│  │  2. そのペルソナのWisdomを取得                                  │   │
│  │  3. LLMにWisdomをcontextとして渡す                              │   │
│  │  4. Wisdom適用済みNudgeを生成                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 5.1 DBスキーマ詳細

### wisdom テーブル

| カラム | 型 | 必須 | 説明 |
|--------|-----|------|------|
| `id` | uuid | ✅ | PK, default: gen_random_uuid() |
| `persona_id` | uuid | ✅ | FK → simulated_personas.id |
| `category` | text | ✅ | 'tone' \| 'timing' \| 'content' \| 'hook' |
| `principle` | text | ✅ | Wisdomの原則（自然言語） |
| `confidence` | numeric(3,2) | ✅ | 0.00〜1.00 |
| `evidence_summary` | text | | エビデンス要約 |
| `evidence_count` | integer | | エビデンス数 |
| `created_at` | timestamptz | ✅ | default: now() |
| `updated_at` | timestamptz | ✅ | default: now() |

**制約:**
- UNIQUE: `(persona_id, category, principle)` ← UPSERT用
- INDEX: `persona_id`, `confidence DESC`

### persona_update_history テーブル

| カラム | 型 | 必須 | 説明 |
|--------|-----|------|------|
| `id` | uuid | ✅ | PK, default: gen_random_uuid() |
| `persona_id` | uuid | ✅ | FK → simulated_personas.id |
| `before_profile` | jsonb | ✅ | 更新前のpsychological_profile |
| `after_profile` | jsonb | ✅ | 更新後のpsychological_profile |
| `reason` | text | ✅ | LLMによる分析結果 |
| `divergence_data` | jsonb | ✅ | { divergence: number, realData: object } |
| `triggered_by` | text | ✅ | 'weekly_calibration' \| 'manual' |
| `created_at` | timestamptz | ✅ | default: now() |

**制約:**
- INDEX: `persona_id`, `created_at DESC`

### 関連テーブル（1.6.0で作成済み、参照用）

| テーブル | 主要カラム | 用途 |
|----------|-----------|------|
| `simulated_personas` | id, name, problem_types[], psychological_profile, behavior_hypotheses | ペルソナ定義 |
| `simulation_runs` | id, persona_id, nudge_config, predictions, created_at | シミュ結果 |
| `tiktok_ad_metrics` | id, date, impressions, clicks, ctr, spend | TikTok実績 |
| `ad_persona_mapping` | ad_id, persona_id | 広告↔ペルソナ紐付け |
| `nudge_feedback` | id, nudge_id, action, created_at | Appフィードバック |

---

## 6. 校正サービス

### 6.1 校正ロジック

```typescript
// apps/api/src/services/calibrationService.ts

class CalibrationService {
  private DIVERGENCE_THRESHOLD = 0.20; // 20%

  async runWeeklyCalibration(): Promise<void> {
    const personas = await this.getActivePersonas();

    for (const persona of personas) {
      // 1. シミュ予測を取得
      const simPredictions = await this.getSimulationPredictions(persona.id);

      // 2. 実データを取得
      const realData = await this.getRealData(persona.id);

      // 3. 乖離を計算
      const divergence = this.calculateDivergence(simPredictions, realData);

      console.log(`[CALIBRATION] ${persona.name}: divergence = ${divergence}`);

      // 4. 乖離が閾値を超えたらペルソナ更新
      if (divergence > this.DIVERGENCE_THRESHOLD) {
        await this.updatePersonaWithLLM(persona, divergence, realData);
      }
    }
  }

  private async getSimulationPredictions(personaId: string) {
    const { data } = await supabase
      .from('simulation_runs')
      .select('nudge_config, predictions')
      .eq('persona_id', personaId)
      .gte('created_at', this.getOneWeekAgo());

    return data;
  }

  private async getRealData(personaId: string) {
    // TikTokデータ
    const { data: tiktokData } = await supabase
      .from('tiktok_ad_metrics')
      .select('*, ad_persona_mapping!inner(persona_id)')
      .eq('ad_persona_mapping.persona_id', personaId)
      .gte('date', this.getOneWeekAgo());

    // Appフィードバック
    const { data: appData } = await supabase
      .from('nudge_feedback')
      .select('*')
      .gte('created_at', this.getOneWeekAgo());

    return { tiktok: tiktokData, app: appData };
  }

  private calculateDivergence(simPredictions, realData): number {
    // シミュ予測の「タップする」率
    const simTapRate = this.calculateSimTapRate(simPredictions);

    // 実際のタップ率（TikTok CTR + App tap率の加重平均）
    const realTapRate = this.calculateRealTapRate(realData);

    // 乖離率
    if (simTapRate === 0) return 0;
    return Math.abs(simTapRate - realTapRate) / simTapRate;
  }

  private async updatePersonaWithLLM(persona, divergence, realData): Promise<void> {
    const prompt = `
あなたはAniccaのペルソナ校正システムです。

=== 現在のペルソナ ===
名前: ${persona.name}
ProblemTypes: ${persona.problem_types.join(', ')}
心理プロファイル:
${JSON.stringify(persona.psychological_profile, null, 2)}

行動仮説:
${JSON.stringify(persona.behavior_hypotheses, null, 2)}

=== 乖離データ ===
乖離率: ${(divergence * 100).toFixed(1)}%

=== 実際のユーザー反応 ===
TikTok:
${JSON.stringify(realData.tiktok?.slice(0, 10), null, 2)}

App:
${JSON.stringify(realData.app?.slice(0, 10), null, 2)}

=== タスク ===
このペルソナの心理プロファイルと行動仮説を更新してください。

出力形式（JSON）:
{
  "analysis": "何が間違っていたかの分析",
  "updated_psychological_profile": { ... },
  "updated_behavior_hypotheses": { ... }
}
`;

    const response = await openai.chat.completions.create({
      model: 'gpt-4o',
      messages: [{ role: 'user', content: prompt }],
      response_format: { type: 'json_object' }
    });

    const result = JSON.parse(response.choices[0].message.content);

    // ペルソナ更新
    await supabase
      .from('simulated_personas')
      .update({
        psychological_profile: result.updated_psychological_profile,
        behavior_hypotheses: result.updated_behavior_hypotheses,
        updated_at: new Date().toISOString()
      })
      .eq('id', persona.id);

    // 履歴保存
    await supabase.from('persona_update_history').insert({
      persona_id: persona.id,
      before_profile: persona.psychological_profile,
      after_profile: result.updated_psychological_profile,
      reason: result.analysis,
      divergence_data: { divergence, realData },
      triggered_by: 'weekly_calibration'
    });

    console.log(`[CALIBRATION] Updated persona: ${persona.name}`);
  }
}
```

---

## 7. Wisdom抽出サービス

### 7.1 Wisdom抽出ロジック

```typescript
// apps/api/src/services/wisdomExtractor.ts

class WisdomExtractor {
  async runWeeklyExtraction(): Promise<void> {
    const personas = await this.getActivePersonas();

    for (const persona of personas) {
      // 1. 過去7日のデータを取得
      const simResults = await this.getSimulationResults(persona.id);
      const realResults = await this.getRealResults(persona.id);

      // 2. LLMでWisdom抽出
      const wisdoms = await this.extractWisdomWithLLM(persona, simResults, realResults);

      // 3. DBに保存
      await this.saveWisdoms(persona.id, wisdoms);

      console.log(`[WISDOM] Extracted ${wisdoms.length} wisdoms for ${persona.name}`);
    }
  }

  private async extractWisdomWithLLM(persona, simResults, realResults): Promise<Wisdom[]> {
    const prompt = `
あなたはAniccaのWisdom抽出システムです。
ブッダのように、観察から一般化可能な原則を抽出してください。

=== ペルソナ ===
名前: ${persona.name}
ProblemTypes: ${persona.problem_types.join(', ')}

=== シミュレーション結果（過去7日）===
${JSON.stringify(simResults?.slice(0, 20), null, 2)}

=== 実データ（過去7日）===
TikTok:
${JSON.stringify(realResults.tiktok?.slice(0, 10), null, 2)}

App:
${JSON.stringify(realResults.app?.slice(0, 10), null, 2)}

=== タスク ===
このペルソナに効くNudgeの原則を抽出してください。

ルール:
1. 具体例ではなく、抽象的な原則として出力
2. カテゴリ（tone, timing, content, hook）ごとに整理
3. 信頼度（0.00-1.00）を付ける
4. その原則を支持するエビデンスを要約

JSON形式で出力:
{
  "wisdom": [
    {
      "category": "tone",
      "principle": "責めない。彼らは既に自分を責めている。",
      "confidence": 0.85,
      "evidence": "gentleトーンのtap率が23%高い"
    }
  ]
}
`;

    const response = await openai.chat.completions.create({
      model: 'gpt-4o',
      messages: [{ role: 'user', content: prompt }],
      response_format: { type: 'json_object' }
    });

    const result = JSON.parse(response.choices[0].message.content);
    return result.wisdom || [];
  }

  private async saveWisdoms(personaId: string, wisdoms: Wisdom[]): Promise<void> {
    for (const w of wisdoms) {
      // UPSERT: 同じ原則があれば更新、なければ挿入
      const { error } = await supabase
        .from('wisdom')
        .upsert({
          persona_id: personaId,
          category: w.category,
          principle: w.principle,
          confidence: w.confidence,
          evidence_summary: w.evidence,
          evidence_count: 1,
          updated_at: new Date().toISOString()
        }, {
          onConflict: 'persona_id,category,principle'
        });

      if (error) {
        console.error(`[WISDOM] Failed to save: ${error.message}`);
      }
    }
  }
}
```

---

## 8. Wisdom適用（Nudge生成）

### 8.1 NudgeGenerator更新

```typescript
// apps/api/src/services/nudgeGenerator.ts

class NudgeGenerator {
  async generateNudge(userId: string): Promise<Nudge> {
    // 1. ユーザー情報取得
    const user = await this.getUser(userId);

    // 2. ProblemTypeからペルソナを特定
    const persona = await this.matchPersona(user.problem_types);

    // 3. そのペルソナのWisdomを取得
    const wisdoms = await this.getWisdoms(persona.id);

    // 4. LLMにNudge生成を依頼（Wisdomをcontextとして渡す）
    const nudge = await this.generateWithWisdom(user, persona, wisdoms);

    return nudge;
  }

  private async matchPersona(userProblemTypes: string[]): Promise<SimulatedPersona> {
    // 最も近いペルソナを見つける（Jaccard類似度）
    const { data: personas } = await supabase
      .from('simulated_personas')
      .select('*');

    let bestMatch = personas[0];
    let bestScore = 0;

    for (const persona of personas) {
      const intersection = userProblemTypes.filter(t =>
        persona.problem_types.includes(t)
      ).length;
      const union = new Set([...userProblemTypes, ...persona.problem_types]).size;
      const score = intersection / union;

      if (score > bestScore) {
        bestScore = score;
        bestMatch = persona;
      }
    }

    return bestMatch;
  }

  private async getWisdoms(personaId: string): Promise<Wisdom[]> {
    const { data } = await supabase
      .from('wisdom')
      .select('*')
      .eq('persona_id', personaId)
      .gte('confidence', 0.5) // 信頼度50%以上のみ
      .order('confidence', { ascending: false });

    return data || [];
  }

  private async generateWithWisdom(user, persona, wisdoms): Promise<Nudge> {
    const wisdomContext = wisdoms.map(w =>
      `[${w.category}] ${w.principle} (信頼度: ${w.confidence})`
    ).join('\n');

    const prompt = `
あなたはAniccaです。以下のWisdomに基づいてNudgeを生成してください。

=== ユーザー情報 ===
ProblemTypes: ${user.problem_types.join(', ')}
現在時刻: ${new Date().toLocaleTimeString('ja-JP')}

=== マッチしたペルソナ ===
${persona.name}

=== Wisdom ===
${wisdomContext || '（まだWisdomがありません。デフォルトで生成してください）'}

=== タスク ===
このユーザーに送るNudgeを生成してください。
Wisdomの原則に従って、hook、content、toneを決定してください。

重要:
- Wisdomがある場合は必ず従う
- 責めない、小さいステップ、失敗を前提にする
- 「簡単に変われる」系のメッセージは禁止

JSON形式で出力:
{
  "hook": "通知タイトル（40文字以内）",
  "content": "本文（200文字以内）",
  "tone": "gentle/neutral/strict",
  "applied_wisdoms": ["適用したWisdomのprincipleを列挙"]
}
`;

    const response = await openai.chat.completions.create({
      model: 'gpt-4o',
      messages: [{ role: 'user', content: prompt }],
      response_format: { type: 'json_object' }
    });

    return JSON.parse(response.choices[0].message.content);
  }
}
```

---

## 8.2 後方互換性

### 既存動作の保証

| 状況 | 動作 | 保証 |
|------|------|------|
| Wisdomが0件 | 従来のプロンプトでNudge生成（Wisdomなし） | ✅ 完全互換 |
| ペルソナマッチなし | デフォルトペルソナにフォールバック | ✅ 完全互換 |
| Cronジョブ無効時 | Nudge生成は影響なし（Wisdom空で動作） | ✅ 完全互換 |

### フォールバック実装

```typescript
// generateWithWisdom() 内
const wisdomContext = wisdoms.length > 0
  ? wisdoms.map(w => `[${w.category}] ${w.principle} (信頼度: ${w.confidence})`).join('\n')
  : '（Wisdomなし。デフォルトで生成してください）';

// wisdoms が空でも applied_wisdoms: [] を返す
return {
  hook: result.hook,
  content: result.content,
  tone: result.tone,
  applied_wisdoms: wisdoms.length > 0 ? result.applied_wisdoms : []
};
```

### 移行戦略

1. **Phase 1（デプロイ直後）**: Wisdomは0件。既存動作と同一。
2. **Phase 2（初回Cron後）**: Wisdomが生成開始。自動適用。
3. **Phase 3（定常運用）**: 週次でWisdomが更新・改善。

**破壊的変更なし。** 既存のNudge生成APIは署名変更なし。

---

## 9. 週次Cronジョブ

```typescript
// apps/api/src/jobs/scheduled.ts

import cron from 'node-cron';

// 毎週日曜00:00 UTCに校正
cron.schedule('0 0 * * 0', async () => {
  console.log('[CRON] weekly_calibration started');

  try {
    const calibrator = new CalibrationService();
    await calibrator.runWeeklyCalibration();

    console.log('[CRON] weekly_calibration completed');
  } catch (error) {
    console.error('[CRON] weekly_calibration failed:', error);
    await notifySlack(`weekly_calibration failed: ${error.message}`);
  }
});

// 毎週日曜01:00 UTCにWisdom抽出
cron.schedule('0 1 * * 0', async () => {
  console.log('[CRON] weekly_wisdom_extraction started');

  try {
    const extractor = new WisdomExtractor();
    await extractor.runWeeklyExtraction();

    console.log('[CRON] weekly_wisdom_extraction completed');
  } catch (error) {
    console.error('[CRON] weekly_wisdom_extraction failed:', error);
    await notifySlack(`weekly_wisdom_extraction failed: ${error.message}`);
  }
});
```

---

## 10. タスクリスト

| # | タスク | ファイル | 優先度 |
|---|--------|----------|--------|
| 1 | CalibrationService実装 | `apps/api/src/services/calibrationService.ts` | 高 |
| 2 | WisdomExtractor実装 | `apps/api/src/services/wisdomExtractor.ts` | 高 |
| 3 | NudgeGenerator更新（Wisdom適用） | `apps/api/src/services/nudgeGenerator.ts` | 高 |
| 4 | ペルソナマッチング実装 | 同上 | 中 |
| 5 | 週次Cronジョブ追加 | `apps/api/src/jobs/scheduled.ts` | 中 |
| 6 | Wisdomダッシュボード（オプション） | 管理画面 | 低 |

---

## 10.1 Runbook（運用手順）

### 環境変数

| 変数名 | 必須 | 説明 |
|--------|------|------|
| `OPENAI_API_KEY` | ✅ | LLM呼び出し用 |
| `SUPABASE_URL` | ✅ | DB接続 |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | DB接続（サービスロール） |
| `SLACK_WEBHOOK_URL` | ✅ | エラー通知用 |
| `WISDOM_CONFIDENCE_THRESHOLD` | | default: 0.5 |
| `CALIBRATION_DIVERGENCE_THRESHOLD` | | default: 0.2 |

### デプロイ手順

```bash
# 1. DBマイグレーション（1.6.0で実行済みなら不要）
cd apps/api && pnpm db:migrate

# 2. 環境変数確認
railway variables

# 3. デプロイ
git push origin dev  # Staging自動デプロイ

# 4. Stagingで動作確認後
git checkout main && git merge dev && git push origin main  # Production
```

### 初回実行（手動）

デプロイ直後はCronが週末を待つため、手動で初回実行を推奨。

```bash
# Railway CLI経由で実行
railway run --environment staging "pnpm run job:calibration"
railway run --environment staging "pnpm run job:wisdom"
```

**package.json に追加:**
```json
{
  "scripts": {
    "job:calibration": "tsx src/jobs/runCalibration.ts",
    "job:wisdom": "tsx src/jobs/runWisdomExtraction.ts"
  }
}
```

### 失敗時の復旧

| 症状 | 原因 | 対応 |
|------|------|------|
| Slack通知「calibration failed」 | LLM/DBエラー | ログ確認 → 手動再実行 |
| Slack通知「wisdom failed」 | LLM/DBエラー | ログ確認 → 手動再実行 |
| Wisdomが生成されない | ペルソナ0件 | `simulated_personas` テーブル確認 |
| 乖離が常に0 | シミュ/実データなし | 各テーブルにデータがあるか確認 |

### 監視指標

| 指標 | 正常値 | アラート条件 |
|------|--------|-------------|
| `wisdom.count` | ≥ 1 per persona | 0件が1週間続く |
| `persona_update_history.count` (週) | 0〜2 | 5件以上（頻繁すぎる更新） |
| `calibration_job.duration` | < 5分 | > 10分 |
| `wisdom_job.duration` | < 10分 | > 20分 |

---

## 11. 受け入れ条件

| # | 条件 | 検証方法（自動テスト可能） |
|---|------|---------------------------|
| 1 | 週次校正が自動実行される | `persona_update_history` に `triggered_by='weekly_calibration'` のレコードが存在する |
| 2 | 乖離 > 20% でペルソナが更新される | `divergence > 0.2` の場合、`persona_update_history` に記録が作成され、`simulated_personas.psychological_profile` が変更される |
| 3 | 乖離 ≤ 20% でペルソナは更新されない | `divergence <= 0.2` の場合、`persona_update_history` に記録が作成されない |
| 4 | Wisdomが自動抽出される | `wisdom` テーブルに `persona_id` ごとに1件以上のレコードが存在する |
| 5 | Wisdom UPSERTが動作する | 同じ `(persona_id, category, principle)` の2回目呼び出しでINSERTではなくUPDATEが発生する |
| 6 | Nudge生成時にWisdomが参照される | `generateNudge()` の返却値に `applied_wisdoms` 配列が含まれる（空配列も可） |
| 7 | Wisdom空の場合フォールバック | `wisdom` が0件のペルソナでも `generateNudge()` が正常動作し、`applied_wisdoms: []` を返す |
| 8 | confidence < 0.5 は除外 | `getWisdoms()` が `confidence >= 0.5` のみを返す |
| 9 | エラー時にSlack通知が送信される | `notifySlack()` が `weekly_calibration failed` または `weekly_wisdom_extraction failed` のメッセージで呼び出される |
| 10 | simTapRate = 0 でも乖離計算が安全 | `calculateDivergence()` が `simTapRate = 0` の場合に `0` を返す（ゼロ除算エラーなし） |

---

## 12. テストマトリックス

### 正常系

| # | 機能 | テスト名 | 種別 | 受入条件# |
|---|------|----------|------|----------|
| 1 | 乖離計算 | `test_calibration_calculatesDivergence` | Unit | - |
| 2 | ペルソナ更新（乖離>20%） | `test_calibration_updatesPersonaWhenDivergent` | Integration | 2 |
| 3 | ペルソナ非更新（乖離≤20%） | `test_calibration_skipsWhenNotDivergent` | Integration | 3 |
| 4 | Wisdom抽出 | `test_wisdomExtractor_extractsPatterns` | Integration | 4 |
| 5 | Wisdom UPSERT | `test_wisdomExtractor_upsertsExistingWisdom` | Integration | 5 |
| 6 | ペルソナマッチング | `test_nudgeGenerator_matchesPersona` | Unit | - |
| 7 | Wisdom適用 | `test_nudgeGenerator_appliesWisdom` | Integration | 6 |
| 8 | 週次Cron校正 | `test_weeklyCron_calibrationExecutes` | Integration | 1 |
| 9 | 週次CronWisdom | `test_weeklyCron_wisdomExecutes` | Integration | 4 |

### 境界・異常系

| # | 機能 | テスト名 | 種別 | 受入条件# |
|---|------|----------|------|----------|
| 10 | simTapRate=0 | `test_calibration_handleZeroSimTapRate` | Unit | 10 |
| 11 | Wisdom空 | `test_nudgeGenerator_fallbackWhenNoWisdom` | Integration | 7 |
| 12 | confidence閾値 | `test_nudgeGenerator_filtersLowConfidence` | Unit | 8 |
| 13 | Cron失敗通知 | `test_weeklyCron_notifiesSlackOnFailure` | Integration | 9 |
| 14 | LLMエラー | `test_wisdomExtractor_handlesLLMError` | Integration | - |
| 15 | DBエラー | `test_calibration_handlesDBError` | Integration | - |
| 16 | ペルソナ0件 | `test_calibration_handlesNoPersonas` | Unit | - |
| 17 | 実データ0件 | `test_calibration_handlesNoRealData` | Unit | - |

### カバレッジ確認

| 受入条件# | テスト# | カバー |
|----------|--------|--------|
| 1 | 8 | ✅ |
| 2 | 2 | ✅ |
| 3 | 3 | ✅ |
| 4 | 4, 9 | ✅ |
| 5 | 5 | ✅ |
| 6 | 7 | ✅ |
| 7 | 11 | ✅ |
| 8 | 12 | ✅ |
| 9 | 13 | ✅ |
| 10 | 10 | ✅ |

---

## 13. 参考

| 種別 | リンク |
|------|--------|
| EY AI Simulation | https://www.ey.com/en_gl/insights/wealth-asset-management/how-ai-simulation-accelerates-growth-in-wealth-and-asset-management |
| Stanford GenAgents | https://github.com/joonspk-research/genagents |

---

*このSpecは詳細化完了。1.6.0完了後に実装開始可能。*
