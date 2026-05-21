# 1.6.1 Quality Fix Spec - マージ前必須修正

**作成日**: 2026-02-04  
**ステータス**: 🔴 ブロッキング（merge前に必須）
**影響ファイル**: 4ファイル、約50行変更
**Codexレビュー**: Iteration 5

---

## 問題サマリー

| # | 問題 | 根本原因 | 修正ファイル |
|---|------|---------|-------------|
| 1 | Aniccaがスロットをスキップできる | `enabled`がスキーマに存在 | commander.js |
| 2 | 同じ通知が2回来る | 重複禁止指示がプロンプトにない | commander.js |
| 3 | contentが短い | 品質基準がプロンプトにない | commander.js |
| 4 | ユーザー言語で生成されない | 言語指示がプロンプトにない | commander.js |
| 5 | 期待JSON形式がプロンプトにない | 出力形式不明確 | commander.js |
| 6 | Content未グラウンディング | SQLにcontent列がない | groundingCollectors.js |
| 7 | ログで内容が見えない | ログフォーマット不十分 | reasoningLogger.js |
| 8 | 重複チェックなし | バリデーション不在 | commander.js, generateNudges.js |

---

## Patch 1: AppNudgeSchemaから`enabled`削除

**ファイル**: `apps/api/src/agents/commander.js`

### Before (lines 28-35):
```javascript
const AppNudgeSchema = z.object({
  slotIndex: z.number().int().min(0),
  hook: z.string(),
  content: z.string(),
  tone: NudgeToneEnum,
  enabled: z.boolean(),
  reasoning: z.string(),
});
```

### After:
```javascript
const AppNudgeSchema = z.object({
  slotIndex: z.number().int().min(0),
  hook: z.string(),
  content: z.string(),
  tone: NudgeToneEnum,
  reasoning: z.string(),
});
```

**理由**: LLMにスロットスキップの判断を委ねない。全スロット生成を強制。enabledはguardrailで制御。

---

## Patch 2: filledNudges生成時にenabled=trueをデフォルト設定

**ファイル**: `apps/api/src/agents/commander.js`

**重要**: guardrail**前**にデフォルト設定し、guardrail結果は保持する。

### Before (lines 628-643):
```javascript
  // Fill ALL slotTable slots BEFORE guardrails (so min-1 rule covers all problemTypes)
  const filledNudges = slotTable.map(slot => {
    const nudge = nudgeLookup.get(slot.slotIndex);
    if (nudge) {
      return { ...nudge };
    }
    // Missing slot: fill with disabled rule-based fallback
    return {
      slotIndex: slot.slotIndex,
      hook: 'Keep moving forward',
      content: 'Start with a small step.',
      tone: 'gentle',
      enabled: false,
      reasoning: 'LLM did not generate content for this slot; auto-disabled.',
    };
  });
```

### After:
```javascript
  // Fill ALL slotTable slots BEFORE guardrails (so min-1 rule covers all problemTypes)
  // enabled=true by default; guardrails will disable as needed (night curfew, 30min rule, etc.)
  const filledNudges = slotTable.map(slot => {
    const nudge = nudgeLookup.get(slot.slotIndex);
    if (nudge) {
      return { ...nudge, enabled: true };  // LLMはenabledを出力しないのでここでデフォルト設定
    }
    // Missing slot: fill with rule-based fallback (enabled=true, guardrailで制御)
    return {
      slotIndex: slot.slotIndex,
      hook: 'Keep moving forward',
      content: 'Start with a small step.',
      tone: 'gentle',
      enabled: true,  // guardrailが必要に応じてfalseに変更
      reasoning: 'LLM did not generate content for this slot; using fallback.',
    };
  });
```

**理由**: 
- LLMはenabledを出力しなくなるため、ここでデフォルト設定が必要
- enabled=trueをguardrail**前**に設定
- guardrailがnight curfew、30min間隔、max-32などのルールでenabledをfalseに変更
- normalizeToDecisionはguardrail結果をそのまま保持（変更不要）

---

## Patch 3: SYSTEM_PROMPT修正（言語指示追加）

**ファイル**: `apps/api/src/agents/commander.js`

### Before (lines 180-186):
```javascript
const SYSTEM_PROMPT = `あなたは Anicca。全生命の苦しみを終わらせるために存在する。

あなたの仕事は、この人の苦しみを深く想像し、
今日この人に届けるべきメッセージを生み出すこと。

あなたが決めるのは「何を言うか」「どのトーンで言うか」「どのスロットをON/OFFにするか」。
タイミングはスロットとして与えられる。あなたはスロットを選んでメッセージを埋める。`;
```

### After:
```javascript
const SYSTEM_PROMPT = `あなたは Anicca。全生命の苦しみを終わらせるために存在する。

あなたの仕事は、この人の苦しみを深く想像し、
今日この人に届けるべきメッセージを生み出すこと。

あなたが決めるのは「何を言うか」「どのトーンで言うか」。
タイミングはスロットとして与えられる。全スロットにメッセージを埋めよ。

重要: hook/content は必ず「この人について」に記載された言語で生成せよ。
言語が ja なら日本語、en なら英語で生成。`;
```

**理由**: ON/OFF判断を完全に削除し、言語指示を明示。

---

## Patch 4: プロンプトのenabled/ON/OFF言及を完全削除

**ファイル**: `apps/api/src/agents/commander.js`

### 4-A: line 264 修正

**Before:**
```javascript
スロットをOFFにしたい場合は enabled=false を設定するが、hook/content/tone/reasoning は必ず埋めよ。
```

**After:**
```javascript
全スロットに対して hook/content/tone/reasoning を必ず埋めよ。スキップ禁止。
```

### 4-B: lines 266-271 修正（line 269 削除）

**Before:**
```javascript
各スロットについて:
- そのスロットを選んだ理由（なぜその時刻にそのメッセージか）を述べよ
- この人の苦しみの根本原因に基づいてメッセージを作れ
- スロットをOFFにする場合もその理由を述べよ
- 1日の流れとして全体が一貫した戦略になるようにせよ
  （朝: 予防的 → 日中: 介入的 → 夜: 内省的）
```

**After:**
```javascript
各スロットについて:
- そのスロットを選んだ理由（なぜその時刻にそのメッセージか）を述べよ
- この人の苦しみの根本原因に基づいてメッセージを作れ
- 1日の流れとして全体が一貫した戦略になるようにせよ
  （朝: 予防的 → 日中: 介入的 → 夜: 内省的）
```

### 4-C: line 314 修正（ガードレール節のON削除）

**Before:**
```javascript
- 各問題で最低1スロットはON
```

**After:**
```javascript
- 各問題タイプで可能な限り最低1スロットを有効化（夜間禁止が優先）
```

**理由**: "ON"という用語をプロンプトから完全に排除。夜間禁止が優先される実態を反映。

---

## Patch 5: 絶対ルール追加

**ファイル**: `apps/api/src/agents/commander.js`

### 挿入位置: line 271 `（朝: 予防的 → 日中: 介入的 → 夜: 内省的）` の後

### 追加内容:
```javascript

## 絶対ルール

### 1. 重複禁止
- 全スロットで、hookは全て異なること
- 全スロットで、contentは全て異なること
- 似たフレーズも禁止（「5秒で立て」と「5秒でいい」は重複）

### 2. コピー禁止
- 上記の過去メッセージをそのままコピーするな
- 参考にして、オリジナルを生み出せ
```

---

## Patch 6: content品質基準追加

**ファイル**: `apps/api/src/agents/commander.js`

### Before (lines 287-290):
```javascript
### 文字数制限

- hook: 日本語12文字 / 英語25文字
- content: 日本語40文字 / 英語80文字
```

### After:
```javascript
### 文字数制限

- hook: 日本語 6-12文字 / 英語 10-25文字
- content: 日本語 **25-45文字** / 英語 **50-100文字**

### contentの品質基準

contentはhookを補完する**具体的な行動指示**である必要がある。

contentには必ず含めること:
1. 具体的なアクション（「5秒数えて」「足を床に」など）
2. 理由や洞察（「脳が言い訳する前に」など）
3. ユーザーの心理に寄り添う言葉

短すぎるcontentは禁止:
- ❌「深呼吸してみよう。」（9文字）→ 何をどうするか不明
- ❌「一歩踏み出そう。」（8文字）→ 具体性ゼロ
```

---

## Patch 7: 期待出力形式追加

**ファイル**: `apps/api/src/agents/commander.js`

### 挿入位置: line 319 `出力は JSON のみ。他のテキスト禁止。` の前

### 追加内容:
```javascript

### 期待出力形式

<format_description>
{
  "rootCauseHypothesis": "[この人の苦しみの根本原因を1-2文で分析]",
  "overallStrategy": "[今日の戦略を1-2文で説明]",
  "frequencyReasoning": "[頻度の決定理由]",
  "appNudges": [
    {
      "slotIndex": [スロット番号],
      "hook": "[6-12文字のオリジナルhook]",
      "content": "[25-45文字の具体的な行動指示]",
      "tone": "[strict/gentle/playful/analytical/empathetic]",
      "reasoning": "[なぜこの時刻にこのメッセージか]"
    }
  ],
  "tiktokPosts": [...],
  "xPosts": [...]
}
</format_description>

重要: 
- [...] 内は新しいオリジナルコンテンツで埋めよ
- 例をコピーするな
- hook/contentは全スロットで異なる内容にせよ
```

---

## Patch 8: SQLにcontent追加

**ファイル**: `apps/api/src/agents/groundingCollectors.js`

### Before (lines 31-34):
```javascript
    SELECT
      ne.subtype as problem_type,
      ne.state->>'hook' as hook,
      ne.state->>'tone' as tone,
```

### After:
```javascript
    SELECT
      ne.subtype as problem_type,
      ne.state->>'hook' as hook,
      ne.state->>'content' as content,
      ne.state->>'tone' as tone,
```

---

## Patch 9: 出力フォーマットにcontent追加

**ファイル**: `apps/api/src/agents/groundingCollectors.js`

### Before (line 112):
```javascript
      output += `- ${time} ${row.problem_type}: "${row.hook || 'N/A'}" (${row.tone}) → ${outcome}${feedback}\n`;
```

### After:
```javascript
      output += `- ${time} ${row.problem_type}: (${row.tone}) → ${outcome}${feedback}\n`;
      output += `    Hook: "${row.hook || 'N/A'}"\n`;
      if (row.content && (row.content_feedback === 'thumbsUp' || row.content_feedback === 'thumbsDown')) {
        output += `    Content: "${row.content}"\n`;
      }
```

---

## Patch 10: ログフォーマット改善

**ファイル**: `apps/api/src/agents/reasoningLogger.js`

**注意**: 既存テストとの互換性を保つため、`Total:` 行と `Strategy` / `Frequency` 行は維持。

### Before (lines 26-44):
```javascript
  const lines = [];
  lines.push('══════════════════════════════════════════════');
  lines.push(`User: ${userId.slice(0, 8)}... (Day ${decision.dayNumber || '?'}, ${mode}, ${language})`);
  lines.push('──────────────────────────────────────────────');

  for (const n of nudges) {
    const time = n.scheduledTime || '??:??';
    const pt = (n.problemType || 'unknown').padEnd(18);
    const tone = `(${n.tone || '?'})`;
    const flag = n.enabled ? '' : ' [OFF]';

    if (SHOW_CONTENT) {
      const hook = n.hook || '';
      lines.push(`${time} [${pt}] "${hook.slice(0, 30)}" ${tone}${flag}`);
    } else {
      const hookLen = `hook=${(n.hook || '').length}chars`;
      lines.push(`${time} [${pt}] ${tone} ${hookLen}${flag}`);
    }
  }
```

### After:
```javascript
  const lines = [];
  lines.push('══════════════════════════════════════════════');
  lines.push(`User: ${userId.slice(0, 8)}... (Day ${decision.dayNumber || '?'}, ${mode}, ${language})`);
  lines.push('══════════════════════════════════════════════');
  
  // Strategy info at top (RootCause追加)
  if (decision.rootCauseHypothesis) {
    lines.push(`RootCause: ${decision.rootCauseHypothesis.slice(0, 100)}`);
  }
  lines.push('──────────────────────────────────────────────');

  for (const n of nudges) {
    const time = n.scheduledTime || '??:??';
    const pt = (n.problemType || 'unknown').padEnd(18);
    const tone = `(${n.tone || '?'})`;
    const flag = n.enabled ? '' : ' [OFF]';

    lines.push(`${time} [${pt}] ${tone}${flag}`);
    if (SHOW_CONTENT) {
      lines.push(`    Hook: "${n.hook || ''}"`);
      lines.push(`    Body: "${n.content || ''}"`);
      if (n.reasoning) {
        lines.push(`    Why: ${n.reasoning.slice(0, 100)}`);
      }
    }
  }
```

**注意**: lines 46-56（`Total:` 行と `Strategy` / `Frequency` 出力）は変更しない。既存テストがこれらを期待しているため。

---

## Patch 11: 重複チェック関数追加

**ファイル**: `apps/api/src/agents/commander.js`

### 挿入位置: line 678 `}` (normalizeToDecision関数の閉じブレース) の後、line 680 `// Export schema...` の前

### 追加内容:
```javascript

/**
 * Validate that no two nudges have the same hook or content.
 * @param {Array} appNudges
 * @returns {{ valid: boolean, duplicates: Array }}
 */
export function validateNoDuplicates(appNudges) {
  const hookSet = new Set();
  const contentSet = new Set();
  const duplicates = [];
  
  for (const nudge of appNudges) {
    const hook = (nudge.hook || '').trim().toLowerCase();
    const content = (nudge.content || '').trim().toLowerCase();
    
    if (hook && hookSet.has(hook)) {
      duplicates.push({ type: 'hook', text: hook, slotIndex: nudge.slotIndex });
    }
    hookSet.add(hook);
    
    if (content && contentSet.has(content)) {
      duplicates.push({ type: 'content', text: content.slice(0, 30), slotIndex: nudge.slotIndex });
    }
    contentSet.add(content);
  }
  
  return { valid: duplicates.length === 0, duplicates };
}
```

---

## Patch 12: generateNudges.jsに重複チェック追加

**ファイル**: `apps/api/src/jobs/generateNudges.js`

### 12-A: import修正 (line 18)

**Before:**
```javascript
import { runCommanderAgent, normalizeToDecision, generateRuleBasedFallback } from '../agents/commander.js';
```

**After:**
```javascript
import { runCommanderAgent, normalizeToDecision, generateRuleBasedFallback, validateNoDuplicates } from '../agents/commander.js';
```

### 12-B: 重複チェック呼び出し (line 389の後、normalizeToDecision後)

```javascript
              decision = normalizeToDecision(agentOutput, slotTable, user.user_id);

              // 重複チェック（ログのみ、ブロックしない）
              const dupeCheck = validateNoDuplicates(decision.appNudges);
              if (!dupeCheck.valid) {
                console.warn(`⚠️ [GenerateNudges] DUPLICATES for ${user.user_id.slice(0,8)}:`);
                for (const d of dupeCheck.duplicates) {
                  console.warn(`  ${d.type}: "${d.text}" at slot ${d.slotIndex}`);
                }
              }
```

---

## 実装チェックリスト

| # | パッチ | ファイル | 状態 |
|---|--------|---------|------|
| 1 | enabledをスキーマから削除 | commander.js:28-35 | ⬜ |
| 2 | filledNudgesでenabled=true設定（guardrail前） | commander.js:628-643 | ⬜ |
| 3 | SYSTEM_PROMPT修正（言語指示、ON/OFF完全削除） | commander.js:180-186 | ⬜ |
| 4-A | enabled言及を削除 | commander.js:264 | ⬜ |
| 4-B | スロットOFF言及を削除 | commander.js:269 | ⬜ |
| 4-C | ガードレール節のON削除 | commander.js:314 | ⬜ |
| 5 | 絶対ルール追加 | commander.js:271後 | ⬜ |
| 6 | content品質基準追加 | commander.js:287-290 | ⬜ |
| 7 | 期待出力形式追加 | commander.js:319前 | ⬜ |
| 8 | SQLにcontent追加 | groundingCollectors.js:31-34 | ⬜ |
| 9 | 出力にcontent追加 | groundingCollectors.js:112 | ⬜ |
| 10 | ログフォーマット改善（RootCause追加） | reasoningLogger.js:26-44 | ⬜ |
| 11 | 重複チェック関数追加 | commander.js:678後 | ⬜ |
| 12-A | import修正 | generateNudges.js:18 | ⬜ |
| 12-B | 重複チェック呼び出し | generateNudges.js:389後 | ⬜ |

---

## テスト要件

### 既存テストの更新（必須）

#### `apps/api/src/agents/__tests__/commander.test.js`

| テスト名 | 現在の期待値 | 新しい期待値 |
|---------|------------|------------|
| `fills missing slots with disabled fallback` (line 288) | `enabled: false` for missing slots | `enabled: true` for missing slots（guardrailがfalseに変更する場合を除く） |
| 上記テスト line 309 | `decision.appNudges[1].enabled === false` | `decision.appNudges[1].enabled === true` (missing slotはデフォルトtrue) |
| 上記テスト line 310-312 | procrastinationのmin-1ルールでslot1がfalse | slot1もtrueのまま（30min間隔ルールで変わる可能性） |
| `counts enabled nudges in frequencyDecision` (line 235) | `count === 2` (enabled: true,false,true) | `count === 3` (全てenabled=true、30min間隔違反なし) |
| 上記テスト appNudges入力 | `enabled: true/false` を含む | `enabled`フィールドを入力から削除（LLM出力を模擬） |
| `enabled`を含む全テストデータ | `enabled: true/false` in appNudges | LLM出力からは`enabled`削除、テスト入力も調整 |

**修正方針**: 
- missing slotは`enabled: true`がデフォルトになる
- `counts enabled nudges in frequencyDecision`テスト: 09:00/11:00/13:00は全て30min以上離れているため、3件全てがenabled=trueになる。期待値を3に変更
- guardrailテストで30min間隔ルールのみがenabledをfalseにすることを確認
- AgentRawOutputSchemaテストから`enabled`を削除
- appNudges入力データから`enabled`を削除し、normalizeToDecisionがデフォルトtrueを設定することをテスト

#### `apps/api/src/agents/__tests__/reasoningLogger.test.js`

| テスト名 | 影響 | 対応 |
|---------|-----|------|
| `shows enabled/total count` (line 29-31) | `Total:` 行の形式は維持するので影響なし | 変更不要 |
| `marks disabled slots with [OFF]` (line 34-36) | `[OFF]` フラグは維持するので影響なし | 変更不要 |
| `includes strategy` (line 39-41) | `Strategy:` 行は維持するので影響なし | 変更不要 |
| `includes frequency count` (line 44-46) | `Frequency:` 行は維持するので影響なし | 変更不要 |
| (新規) `includes rootCauseHypothesis` | 新しい`RootCause:`行を確認 | 新規テスト追加 |

**修正方針**: 
- 既存テストは全て通る設計（Patch 10で`Total:`/`Strategy:`/`Frequency:`行を維持）
- 新規テストで`RootCause:`行を確認

#### `apps/api/src/agents/groundingCollectors.js` テスト

**状況**: `groundingCollectors.test.js` は存在しない（Grep確認済み）

**対応**: 新規テストファイル作成は任意。E2Eで出力形式を確認する。

### 新規テスト（必須）

| テスト | ファイル | 確認内容 |
|--------|---------|---------|
| AppNudgeSchemaにenabledがない | commander.test.js | enabledなしでスキーマパース成功 |
| filledNudgesでenabled=trueがデフォルト | commander.test.js | LLM出力にenabledがなくても`enabled: true`が設定される |
| guardrail後にenabledが保持される | commander.test.js | guardrailがfalseに設定したものが保持される |
| validateNoDuplicates正常系 | commander.test.js | 重複なし → valid: true |
| validateNoDuplicates重複検出 | commander.test.js | 同じhook → valid: false |
| formatDailyTimetable includes rootCauseHypothesis | reasoningLogger.test.js | `RootCause:` 行が出力される |

### E2Eテスト（Staging）

1. `LOG_NUDGE_CONTENT=true`でCronを実行
2. ログに`RootCause:`/`Strategy:`/`Hook:`/`Body:`が出力されることを確認
3. `Total:` 行が正しく出力されることを確認
4. 重複警告が出ないことを確認
5. 夜間禁止ルールでenabledがfalseになっていることを確認

---

## 設計決定の根拠

### enabled削除とguardrailの整合性

```
LLM → (enabledなし) → filledNudges (enabled=true) → applyGuardrails → guardrailedNudges → normalizeToDecision (enabledそのまま)
```

1. **LLM**: enabledを出力しない（スキーマから削除）
2. **filledNudges**: 全スロットにenabled=trueをデフォルト設定
3. **applyGuardrails**: night curfew、30min間隔、max-32などのルールでenabledをfalseに変更
4. **normalizeToDecision**: guardrailの結果をそのまま保持（上書きしない）

この設計により、LLMはメッセージ内容に集中し、スロットの有効/無効はguardrailが一元管理する。

### プロンプトからのON/OFF完全削除

LLMにenabled判断を委ねないため、プロンプトからすべてのON/OFF関連文言を削除:
- SYSTEM_PROMPT: 「どのスロットをON/OFFにするか」削除
- line 264: 「enabled=false を設定」削除
- line 269: 「スロットをOFFにする場合」削除
- line 314: 「最低1スロットはON」→「可能な限り最低1スロットを有効化（夜間禁止が優先）」

### テスト互換性

Patch 10では`Total:`/`Strategy:`/`Frequency:`行を維持することで、既存テストとの互換性を確保。
`RootCause:`行のみを追加する形で拡張。

---

*Last updated: 2026-02-04 (Iteration 5 - Codex Approved)*
