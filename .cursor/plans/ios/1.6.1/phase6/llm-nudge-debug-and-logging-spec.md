# Phase 6: LLM Nudge 完全実装仕様書

## 概要

LLM生成Nudgeに**3つの重大な問題**がある。全て修正が必要。

---

## 問題一覧

### 問題1: user_id ミスマッチ（致命的バグ）

**場所**: `apps/api/src/jobs/generateNudges.js:264`

**現状**:
```javascript
// Line 196: device_id を profile_id として取得
mp.device_id as profile_id,

// Line 264: device_id で保存（間違い）
user.profile_id,  // ← これは device_id！
```

**結果**:
- Cron保存: `user_id = device_id`
- API検索: `user_id = credentials.userId`
- **別の値 → 結果0件 → キャッシュ空 → isAIGenerated常にfalse**

**修正**: `user.profile_id` → `user.user_id`

---

### 問題2: プロンプトにユーザーデータが含まれていない（仕様未実装）

**場所**: `apps/api/src/jobs/generateNudges.js:143-175`

**現状のプロンプト**:
```
## Problem Type
${problemName}

## Tone Definitions
...
```

**Specで定めたプロンプト（phase6-llm-generation-spec.md）**:
```
## User Profile
- Preferred tone: {preferred_tone} (based on past thumbs_up patterns)
- Avoided tone: {avoided_tone} (based on past thumbs_down patterns)

## What Worked (Top 3)
{successful_nudges}

## What Failed (Top 3)
{failed_nudges}
```

**結果**: パーソナライズが全く機能していない。全ユーザーに同じ品質のNudgeが生成される。

**修正**:
1. `getUserFeedback()` 関数を追加（nudge_outcomes テーブルからフィードバック取得）
2. `buildPrompt()` を修正してフィードバックをプロンプトに含める

---

### 問題3: iOS側のデバッグ手段がない

**現状**:
- LLMフェッチのログが不十分
- キャッシュ状態を確認するUIがない
- 100%LLMを強制表示するボタンがない

**結果**: 問題の原因特定が困難。

**修正**: デバッグログとデバッグボタンを追加

---

## あるべきプロンプト（完全版）

```javascript
function buildPrompt(problem, preferredLanguage = 'en', feedback = null) {
  const isJapanese = preferredLanguage === 'ja';
  const limits = CHAR_LIMITS[preferredLanguage] || CHAR_LIMITS.en;

  // ... problemNames, toneDefinitions は既存のまま ...

  // ユーザーフィードバックセクション
  let feedbackSection = '';
  if (feedback) {
    if (feedback.preferredTone || feedback.avoidedTone) {
      feedbackSection += `\n## User Profile\n`;
      if (feedback.preferredTone) {
        feedbackSection += `- Preferred tone: ${feedback.preferredTone} (based on past positive feedback)\n`;
      }
      if (feedback.avoidedTone) {
        feedbackSection += `- Avoided tone: ${feedback.avoidedTone} (based on past negative feedback)\n`;
      }
    }

    if (feedback.successful && feedback.successful.length > 0) {
      feedbackSection += `\n## What Worked (Top ${feedback.successful.length})\n`;
      feedbackSection += feedback.successful.join('\n') + '\n';
    }

    if (feedback.failed && feedback.failed.length > 0) {
      feedbackSection += `\n## What Failed (Top ${feedback.failed.length})\n`;
      feedbackSection += feedback.failed.join('\n') + '\n';
    }
  }

  return `You are Anicca, an AI that reduces human suffering through perfectly-timed nudges.

## Your Mission
Generate notification hooks and one-screen content that will make this specific person take action. The notification alone should be powerful enough to change behavior - they shouldn't even need to tap.

## Problem Type
${problemName}
${feedbackSection}

## Tone Definitions
${toneDefinitions}

## Output Requirements

### Hook (Notification)
- Maximum ${limits.hook} characters (CRITICAL - must fit in notification preview)
- Action-oriented
- Uses the tone that works for this person
- Powerful enough that they might change behavior without tapping

### Content (One-Screen)
- Maximum ${limits.content} characters
- Specific action or insight
- Directly related to the hook
- Provides value even if they only glance at it

## Output Format (JSON)

${exampleOutput}

## Critical Rules
1. NEVER exceed character limits. Hook ≤ ${limits.hook}, Content ≤ ${limits.content}.
2. Output a SINGLE JSON object, not an array.
3. If past approaches failed, try something different.
4. The hook is more important than the content. Focus there first.
${languageInstruction}`;
}
```

---

## パッチ

### Patch 1: generateNudges.js - user_id修正 + getUserFeedback追加 + buildPrompt修正

```diff
--- a/apps/api/src/jobs/generateNudges.js
+++ b/apps/api/src/jobs/generateNudges.js
@@ -63,6 +63,62 @@ function getScheduledHourForProblem(problem) {
   return scheduleMap[problem] || 9;
 }

+// ユーザーの過去フィードバックを取得
+async function getUserFeedback(userId, problem) {
+  // 過去30日のフィードバックを取得
+  const result = await query(`
+    SELECT
+      ne.state->>'hook' as hook,
+      ne.state->>'content' as content,
+      ne.state->>'tone' as tone,
+      no.reward,
+      no.signals->>'outcome' as outcome,
+      no.signals->>'thumbsUp' as thumbs_up,
+      no.signals->>'thumbsDown' as thumbs_down
+    FROM nudge_events ne
+    LEFT JOIN nudge_outcomes no ON no.nudge_event_id = ne.id
+    WHERE ne.user_id = $1::uuid
+      AND ne.subtype = $2
+      AND ne.domain = 'problem_nudge'
+      AND ne.created_at >= NOW() - INTERVAL '30 days'
+    ORDER BY ne.created_at DESC
+    LIMIT 50
+  `, [userId, problem]);
+
+  const rows = result.rows;
+  if (rows.length === 0) return null;
+
+  // 成功例（reward=1 または thumbsUp）
+  const successful = rows
+    .filter(r => r.reward === 1 || r.thumbs_up === 'true')
+    .slice(0, 3)
+    .map(r => `- "${r.hook}" → "${r.content}" (tone: ${r.tone})`);
+
+  // 失敗例（reward=0 または thumbsDown または outcome=ignored）
+  const failed = rows
+    .filter(r => r.reward === 0 || r.thumbs_down === 'true' || r.outcome === 'ignored')
+    .slice(0, 3)
+    .map(r => `- "${r.hook}" → "${r.content}" (tone: ${r.tone})`);
+
+  // 好まれるトーン（成功例から抽出）
+  const successfulTones = rows
+    .filter(r => r.reward === 1 || r.thumbs_up === 'true')
+    .map(r => r.tone)
+    .filter(Boolean);
+  const preferredTone = successfulTones.length > 0
+    ? [...new Set(successfulTones)].join(', ')
+    : null;
+
+  // 避けるべきトーン（失敗例から抽出）
+  const failedTones = rows
+    .filter(r => r.reward === 0 || r.thumbs_down === 'true')
+    .map(r => r.tone)
+    .filter(Boolean);
+  const avoidedTone = failedTones.length > 0
+    ? [...new Set(failedTones)].join(', ')
+    : null;
+
+  return { successful, failed, preferredTone, avoidedTone };
+}
+
 // 言語別の文字数制限
 const CHAR_LIMITS = {
   ja: { hook: 12, content: 40 },
@@ -71,7 +127,7 @@ const CHAR_LIMITS = {
 };

 // プロンプトを構築
-function buildPrompt(problem, preferredLanguage = 'en') {
+function buildPrompt(problem, preferredLanguage = 'en', feedback = null) {
   const isJapanese = preferredLanguage === 'ja';
   const limits = CHAR_LIMITS[preferredLanguage] || CHAR_LIMITS.en;

@@ -139,6 +195,26 @@ function buildPrompt(problem, preferredLanguage = 'en') {
     ? '3. Use Japanese. Natural, conversational, not robotic.'
     : '3. Use English. Natural, conversational, not robotic.';

+  // ユーザーフィードバックセクション
+  let feedbackSection = '';
+  if (feedback) {
+    if (feedback.preferredTone || feedback.avoidedTone) {
+      feedbackSection += `\n## User Profile\n`;
+      if (feedback.preferredTone) feedbackSection += `- Preferred tone: ${feedback.preferredTone} (based on past positive feedback)\n`;
+      if (feedback.avoidedTone) feedbackSection += `- Avoided tone: ${feedback.avoidedTone} (based on past negative feedback)\n`;
+    }
+
+    if (feedback.successful && feedback.successful.length > 0) {
+      feedbackSection += `\n## What Worked (Top ${feedback.successful.length})\n`;
+      feedbackSection += feedback.successful.join('\n') + '\n';
+    }
+
+    if (feedback.failed && feedback.failed.length > 0) {
+      feedbackSection += `\n## What Failed (Top ${feedback.failed.length})\n`;
+      feedbackSection += feedback.failed.join('\n') + '\n';
+    }
+  }
+
   return `You are Anicca, an AI that reduces human suffering through perfectly-timed nudges.

 ## Your Mission
@@ -146,6 +222,7 @@ Generate notification hooks and one-screen content that will make this specific

 ## Problem Type
 ${problemName}
+${feedbackSection}

 ## Tone Definitions
 ${toneDefinitions}
@@ -171,6 +248,8 @@ ${exampleOutput}
 ## Critical Rules
 1. NEVER exceed character limits. Hook ≤ ${limits.hook}, Content ≤ ${limits.content}.
 2. Output a SINGLE JSON object, not an array.
+3. If past approaches failed, try something different.
+4. The hook is more important than the content. Focus there first.
 ${languageInstruction}`;
 }

@@ -217,7 +296,13 @@ async function runGenerateNudges() {
     const limits = CHAR_LIMITS[preferredLanguage] || CHAR_LIMITS.en;

     for (const problem of problems) {
-      const prompt = buildPrompt(problem, preferredLanguage);
+      // ユーザーの過去フィードバックを取得
+      const feedback = await getUserFeedback(user.user_id, problem);
+      if (feedback) {
+        console.log(`📊 [GenerateNudges] User ${user.user_id} feedback for ${problem}: ${feedback.successful?.length || 0} success, ${feedback.failed?.length || 0} failed`);
+      }
+
+      const prompt = buildPrompt(problem, preferredLanguage, feedback);

       try {
         const response = await fetch('https://api.openai.com/v1/chat/completions', {
@@ -261,7 +346,7 @@ async function runGenerateNudges() {
            VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6::jsonb, $7, $8, $9, timezone('utc', now()))`,
           [
             nudgeId,
-            user.profile_id,
+            user.user_id,  // 修正: device_id ではなく user_id を使用
             'problem_nudge',
             problem,
             'llm_generation',
```

---

### Patch 2: LLMNudgeCache.swift - デバッグメソッド追加

```diff
--- a/aniccaios/aniccaios/Services/LLMNudgeCache.swift
+++ b/aniccaios/aniccaios/Services/LLMNudgeCache.swift
@@ -1,4 +1,5 @@
 import Foundation
+import OSLog

 /// LLM生成Nudgeのキャッシュ（@MainActorでスレッド安全性を保証）
 @MainActor
@@ -6,6 +7,8 @@ final class LLMNudgeCache {
     static let shared = LLMNudgeCache()

     private var cache: [String: LLMGeneratedNudge] = [:]
+
+    private let logger = Logger(subsystem: "com.anicca.ios", category: "LLMNudgeCache")

     private init() {}

@@ -18,10 +21,43 @@ final class LLMNudgeCache {
     func setNudges(_ nudges: [LLMGeneratedNudge]) {
         for nudge in nudges {
             let key = "\(nudge.problemType.rawValue)_\(nudge.scheduledHour)"
             cache[key] = nudge
         }
+        let summary = nudges.map { "\($0.problemType.rawValue)@\($0.scheduledHour)" }.joined(separator: ", ")
+        logger.info("📦 [LLMCache] Set \(nudges.count) nudges: \(summary)")
     }

     func clear() {
         cache = [:]
+        logger.info("📦 [LLMCache] Cleared")
+    }
+
+    // MARK: - Debug Methods
+
+    var count: Int {
+        cache.count
+    }
+
+    func getAllEntries() -> [(key: String, nudge: LLMGeneratedNudge)] {
+        cache.map { (key: $0.key, nudge: $0.value) }
+    }
+
+    func debugSummary() -> String {
+        if cache.isEmpty { return "📦 LLMキャッシュ: 空" }
+        let entries = cache.map { "\($0.value.problemType.rawValue)@\($0.value.scheduledHour): \"\($0.value.hook)\"" }
+        return "📦 LLMキャッシュ (\(cache.count)件):\n" + entries.joined(separator: "\n")
+    }
+
+    func getFirstNudge() -> LLMGeneratedNudge? {
+        cache.values.first
     }
 }
```

---

### Patch 3: AppState.swift - 詳細ログ追加

```diff
--- a/aniccaios/aniccaios/AppState.swift
+++ b/aniccaios/aniccaios/AppState.swift
@@ -142,14 +142,16 @@ final class AppState: ObservableObject {
     // MARK: - Phase 6: LLM生成Nudge

     func fetchTodaysLLMNudges() async {
+        logger.info("🔄 [LLM] Starting fetchTodaysLLMNudges...")
         do {
             let nudges = try await LLMNudgeService.shared.fetchTodaysNudges()
             await MainActor.run {
                 LLMNudgeCache.shared.setNudges(nudges)
             }
-            logger.info("Fetched \(nudges.count) LLM-generated nudges")
+            logger.info("✅ [LLM] Fetched and cached \(nudges.count) nudges")
         } catch {
-            logger.error("Failed to fetch todays LLM nudges: \(error.localizedDescription)")
+            logger.error("❌ [LLM] Fetch failed: \(error.localizedDescription)")
         }
     }
```

---

### Patch 4: LLMNudgeService.swift - 詳細ログ + デコードエラー詳細

```diff
--- a/aniccaios/aniccaios/Services/LLMNudgeService.swift
+++ b/aniccaios/aniccaios/Services/LLMNudgeService.swift
@@ -18,10 +18,12 @@ actor LLMNudgeService {
     func fetchTodaysNudges() async throws -> [LLMGeneratedNudge] {
         guard case .signedIn(let credentials) = await AppState.shared.authStatus else {
+            logger.warning("🔄 [LLM] Not signed in, skipping fetch")
             throw ServiceError.notAuthenticated
         }

         let url = await MainActor.run { AppConfig.nudgeTodayURL }
+        logger.info("🔄 [LLM] Requesting: \(url.absoluteString)")
         var request = URLRequest(url: url)
         request.httpMethod = "GET"
         // ... 既存のコード ...

             guard (200..<300).contains(httpResponse.statusCode) else {
                 logger.error("Failed to fetch nudges: HTTP \(httpResponse.statusCode)")
+                if let body = String(data: data, encoding: .utf8) {
+                    logger.error("🔄 [LLM] Response body: \(body)")
+                }
                 throw ServiceError.httpError(httpResponse.statusCode)
             }

-            let responseBody = try decoder.decode(NudgeTodayResponse.self, from: data)
+            let responseBody: NudgeTodayResponse
+            do {
+                responseBody = try decoder.decode(NudgeTodayResponse.self, from: data)
+            } catch let decodingError {
+                logger.error("❌ [LLM] Decoding error: \(String(describing: decodingError))")
+                throw decodingError
+            }
+            logger.info("🔄 [LLM] Decoded \(responseBody.nudges.count) nudges from response")
             return responseBody.nudges
```

---

### Patch 5: ProfileView.swift - デバッグボタン追加

**場所**: `#if DEBUG` セクション内、recordingSection の最後（行687付近）

```diff
--- a/aniccaios/aniccaios/Views/Profile/ProfileView.swift
+++ b/aniccaios/aniccaios/Views/Profile/ProfileView.swift
@@ -26,6 +26,10 @@ struct ProfileView: View {
     #if DEBUG
     @State private var debugAlarmTime = Date()
+    // Phase 6: LLMデバッグ用
+    @State private var showLLMCacheAlert = false
+    @State private var llmCacheAlertMessage = ""
+    @State private var showNoLLMAlert = false
     #endif

     // recordingSection 内の最後に追加:

+                    Divider()
+
+                    // MARK: - Phase 6 LLM Debug
+                    Text("🤖 Phase 6: LLM Nudge")
+                        .font(.subheadline.weight(.bold))
+                        .frame(maxWidth: .infinity, alignment: .leading)
+                        .padding(.top, 8)
+
+                    Button("📦 LLMキャッシュ確認") {
+                        let summary = LLMNudgeCache.shared.debugSummary()
+                        llmCacheAlertMessage = summary
+                        showLLMCacheAlert = true
+                    }
+                    .frame(maxWidth: .infinity, alignment: .leading)
+
+                    Divider()
+
+                    Button("🤖 LLM専用テスト（100%LLM）") {
+                        Task {
+                            if let llmNudge = await MainActor.run({
+                                LLMNudgeCache.shared.getFirstNudge()
+                            }) {
+                                let content = NudgeContent.content(from: llmNudge)
+                                await MainActor.run {
+                                    appState.showNudgeCard(content)
+                                }
+                            } else {
+                                await MainActor.run {
+                                    showNoLLMAlert = true
+                                }
+                            }
+                        }
+                    }
+                    .frame(maxWidth: .infinity, alignment: .leading)
+
+                    Divider()
+
+                    Button("🔄 LLM再フェッチ") {
+                        Task {
+                            await AppState.shared.fetchTodaysLLMNudges()
+                            let count = await MainActor.run { LLMNudgeCache.shared.count }
+                            llmCacheAlertMessage = "フェッチ完了: \(count)件"
+                            showLLMCacheAlert = true
+                        }
+                    }
+                    .frame(maxWidth: .infinity, alignment: .leading)

+            // アラート追加
+            .alert("LLMキャッシュ状態", isPresented: $showLLMCacheAlert) {
+                Button("OK", role: .cancel) { }
+            } message: {
+                Text(llmCacheAlertMessage)
+            }
+            .alert("LLMデータなし", isPresented: $showNoLLMAlert) {
+                Button("OK", role: .cancel) { }
+            } message: {
+                Text("LLMNudgeCacheにデータがありません。\n\n考えられる原因:\n1. Cronジョブが実行されていない\n2. API呼び出しが失敗している\n3. DBにデータがない\n\nXcodeログで「[LLM]」を検索してください。")
+            }
```

---

## DEBUG vs PRODUCTION

| 環境 | デバッグボタン | 🤖マーク | ユーザーへの影響 |
|------|--------------|---------|----------------|
| **PRODUCTION** | ❌ 非表示 | ❌ 非表示 | 何も見えない。LLMか既存か区別不可能。 |
| **DEBUG** | ✅ 表示 | ❌ 非表示 | 開発者のみ確認可能 |

---

## テストマトリックス

| # | 問題 | テスト内容 | 期待結果 |
|---|------|----------|---------|
| 1 | user_id修正 | Cron実行後、API `/nudge/today` 呼び出し | nudges配列に1件以上返る |
| 2 | パーソナライズ | フィードバックありユーザーでCron実行 | ログに「📊 feedback: X success, Y failed」 |
| 3 | パーソナライズ | フィードバックなしユーザーでCron実行 | 従来通り問題タイプのみでLLM呼び出し |
| 4 | iOSキャッシュ | アプリ起動後「📦」ボタン | キャッシュ内容表示 |
| 5 | iOS 100%LLM | 「🤖」ボタン（データあり） | NudgeCard表示 |
| 6 | iOS 100%LLM | 「🤖」ボタン（データなし） | アラート表示 |
| 7 | iOS再フェッチ | 「🔄」ボタン | API再呼び出し、件数表示 |

---

## 確認手順

### 1. DB確認（Supabase SQL Editor）

```sql
-- 今日生成されたLLM Nudge
SELECT
  id,
  user_id,
  subtype as problem_type,
  state->>'hook' as hook,
  state->>'tone' as tone,
  created_at
FROM nudge_events
WHERE domain = 'problem_nudge'
  AND decision_point = 'llm_generation'
  AND created_at >= NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC
LIMIT 20;

-- ユーザーの過去フィードバック確認
SELECT
  ne.state->>'hook' as hook,
  ne.state->>'tone' as tone,
  no.reward,
  no.signals->>'outcome' as outcome
FROM nudge_events ne
LEFT JOIN nudge_outcomes no ON no.nudge_event_id = ne.id
WHERE ne.user_id = 'YOUR_USER_ID'::uuid
  AND ne.domain = 'problem_nudge'
ORDER BY ne.created_at DESC
LIMIT 20;
```

### 2. iOS デバッグ

1. アプリ起動
2. Xcodeログで「[LLM]」を検索
3. Profile → 「📦 LLMキャッシュ確認」タップ
4. Profile → 「🤖 LLM専用テスト」タップ

---

## 実行手順

1. **Patch 1** を `generateNudges.js` に適用（user_id修正 + getUserFeedback + buildPrompt修正）
2. **Patch 2-5** をiOS側に適用
3. `git push origin dev` でRailwayにデプロイ
4. Cronが実行されるのを待つ（5:00 JST）または手動実行
5. iOSアプリでデバッグボタンを使って確認

---

## レビューチェックリスト

- [ ] **問題1**: `user.profile_id` → `user.user_id` に修正されているか
- [ ] **問題2**: `getUserFeedback()` 関数が追加されているか
- [ ] **問題2**: `buildPrompt()` に `feedback` 引数が追加されているか
- [ ] **問題2**: プロンプトに `User Profile`, `What Worked`, `What Failed` セクションが含まれるか
- [ ] **問題3**: iOS側にデバッグログが追加されているか
- [ ] **問題3**: デバッグボタンが `#if DEBUG` で保護されているか
- [ ] **PRODUCTION** で余計なUIが表示されないか
