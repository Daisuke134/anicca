# Phase 6 補足: Nudge テキスト改善 & デバッグ強化 仕様書

> 作成日: 2026-01-24
> ステータス: Draft

---

## 概要

Phase 6 LLM生成の実装後、以下の問題が発見された:
1. デバッグボタンが1種類のみ → テスト効率が悪い
2. 固定バリアントのテキストが長すぎる → 通知が切れる
3. LLM Prompt の言語がハードコード → 英語ユーザーに日本語が出る
4. ビルド時にログ確認していない → LLM取得成功/失敗がわからない

---

## 問題 1: ランダム問題タイプテストボタン

### As-Is

`ProfileView.swift` のデバッグセクション:

```swift
Button("📱 1枚画面テスト（夜更かし）") {
    let content = NudgeContent.contentForToday(for: .stayingUpLate)
    appState.showNudgeCard(content)
}
```

**問題**: staying_up_late しかテストできない。全問題タイプを順番にテストするのは面倒。

### To-Be

ユーザーが選択した問題からランダムに選んでテストするボタンを追加:

```swift
Button("🎲 ランダム問題でテスト") {
    // ユーザーが選択した問題タイプからランダムに選択
    let userProblems = appState.selectedProblems
    guard !userProblems.isEmpty else {
        // fallback: 全問題からランダム
        let randomProblem = ProblemType.allCases.randomElement()!
        let content = NudgeContent.contentForToday(for: randomProblem)
        appState.showNudgeCard(content)
        return
    }
    let randomProblem = userProblems.randomElement()!
    let content = NudgeContent.contentForToday(for: randomProblem)
    appState.showNudgeCard(content)
}
.accessibilityIdentifier("debug-nudge-test-random")
```

### パッチ

```diff
--- a/aniccaios/aniccaios/Views/Profile/ProfileView.swift
+++ b/aniccaios/aniccaios/Views/Profile/ProfileView.swift
@@ -634,6 +634,22 @@ struct ProfileView: View {

                     Divider()

+                    Button("🎲 ランダム問題でテスト") {
+                        let userProblems = appState.selectedProblems
+                        let randomProblem: ProblemType
+                        if userProblems.isEmpty {
+                            randomProblem = ProblemType.allCases.randomElement()!
+                        } else {
+                            randomProblem = userProblems.randomElement()!
+                        }
+                        let content = NudgeContent.contentForToday(for: randomProblem)
+                        appState.showNudgeCard(content)
+                    }
+                    .accessibilityIdentifier("debug-nudge-test-random")
+                    .frame(maxWidth: .infinity, alignment: .leading)
+
+                    Divider()
+
                     Button("📱 1枚画面テスト（夜更かし）") {
                         let content = NudgeContent.contentForToday(for: .stayingUpLate)
                         appState.showNudgeCard(content)
```

---

## 問題 2: 固定バリアントのテキストが長すぎる

### As-Is

**日本語 (ja.lproj/Localizable.strings)**:

| キー | 現在のテキスト | 文字数 |
|------|---------------|--------|
| `nudge_staying_up_late_notification_2` | その「あと5分だけ」で、何年失ってきた？ | 20 |
| `nudge_staying_up_late_notification_4` | 深夜0時を過ぎました。今すぐ休んでください。 | 22 |
| `nudge_staying_up_late_notification_5` | 深夜1時です。起きている1分が明日を蝕みます。 | 23 |
| `nudge_self_loathing_notification_4` | 自己批判は成長させない。自己慈悲が成長させる。 | 23 |
| `nudge_loneliness_notification_3` | 孤独は穏やかになれる。寂しさは永遠じゃない。 | 22 |
| ...等 多数 | | |

**問題**: 日本語通知は約12文字以内でないと切れる。15文字超のバリアントが多数。

**英語 (en.lproj/Localizable.strings)**:

| キー | 現在のテキスト | 文字数 |
|------|---------------|--------|
| `nudge_staying_up_late_notification_2` | How many years have you lost to 'just 5 more minutes'? | 54 |
| `nudge_self_loathing_notification_5` | Would you say this to a friend? Then don't say it to yourself. | 62 |
| `nudge_loneliness_notification_3` | Solitude can be peaceful. Loneliness doesn't have to be permanent. | 66 |
| ...等 多数 | | |

**問題**: 英語通知は約25文字以内でないと切れる。30文字超のバリアントが多数。

### To-Be

**新しい文字数制限**:
- 日本語: **12文字以内**
- 英語: **25文字以内**

**日本語バリアントの修正例**:

| キー | 現在 (長い) | 修正後 (短い) |
|------|-------------|---------------|
| `nudge_staying_up_late_notification_2` | その「あと5分だけ」で、何年失ってきた？ | 「あと5分」で何年失った？ |
| `nudge_staying_up_late_notification_4` | 深夜0時を過ぎました。今すぐ休んでください。 | 深夜0時。今すぐ休め。 |
| `nudge_staying_up_late_notification_5` | 深夜1時です。起きている1分が明日を蝕みます。 | 深夜1時。明日に響く。 |
| `nudge_self_loathing_notification_4` | 自己批判は成長させない。自己慈悲が成長させる。 | 批判より慈悲を。 |
| `nudge_porn_addiction_notification_8` | この弱さの瞬間はあなたを定義しない。 | これで終わりじゃない。 |

**英語バリアントの修正例**:

| キー | 現在 (長い) | 修正後 (短い) |
|------|-------------|---------------|
| `nudge_staying_up_late_notification_2` | How many years have you lost to 'just 5 more minutes'? | "5 more minutes"? Again? |
| `nudge_self_loathing_notification_5` | Would you say this to a friend? Then don't say it to yourself. | Say it to a friend? No? |
| `nudge_loneliness_notification_3` | Solitude can be peaceful. Loneliness doesn't have to be permanent. | Loneliness is temporary. |

### パッチ（日本語の一部）

```diff
--- a/aniccaios/aniccaios/Resources/ja.lproj/Localizable.strings
+++ b/aniccaios/aniccaios/Resources/ja.lproj/Localizable.strings
@@ -1,10 +1,10 @@
 // Nudge - staying_up_late (通知テキスト: 12文字以内)
 "nudge_staying_up_late_notification_1" = "スクロールより、呼吸。";
-"nudge_staying_up_late_notification_2" = "その「あと5分だけ」で、何年失ってきた？";
+"nudge_staying_up_late_notification_2" = "「あと5分」で何年失った？";
 "nudge_staying_up_late_notification_3" = "明日の自分、泣くよ。";
-"nudge_staying_up_late_notification_4" = "深夜0時を過ぎました。今すぐ休んでください。";
-"nudge_staying_up_late_notification_5" = "深夜1時です。起きている1分が明日を蝕みます。";
+"nudge_staying_up_late_notification_4" = "深夜0時。今すぐ休め。";
+"nudge_staying_up_late_notification_5" = "深夜1時。明日に響く。";
 "nudge_staying_up_late_notification_6" = "スマホを置いて。今すぐ。";
-"nudge_staying_up_late_notification_7" = "未来の自分が見てる。何が見える？";
+"nudge_staying_up_late_notification_7" = "未来の自分が見てる。";
 "nudge_staying_up_late_notification_8" = "睡眠は贅沢じゃない。薬だ。";
 "nudge_staying_up_late_notification_9" = "画面は待てる。夢は待てない。";
-"nudge_staying_up_late_notification_10" = "睡眠1時間 = 明日の判断力向上。";
+"nudge_staying_up_late_notification_10" = "1時間の睡眠で判断力UP。";
```

### 全バリアント修正リスト

別ファイル `.cursor/plans/ios/phase6/notification-text-shortening.md` に詳細リストを作成すること。

---

## 問題 3: LLM Prompt の言語がハードコード

### As-Is

`apps/api/src/jobs/generateNudges.js`:

```javascript
## Critical Rules
1. NEVER exceed character limits. Hook ≤ 25, Content ≤ 80.
2. Output a SINGLE JSON object, not an array.
3. Use Japanese. Natural, conversational, not robotic.
```

**問題**: `Use Japanese` がハードコードされている。英語ユーザーにも日本語で生成される。

### To-Be

ユーザーの `preferredLanguage` を DB から取得し、Prompt に動的に挿入:

```javascript
// ユーザーの言語設定を取得
const userLanguage = user.profile?.preferredLanguage || 'en';
const isJapanese = userLanguage === 'ja';

// 言語に応じた文字数制限
const hookLimit = isJapanese ? 12 : 25;
const contentLimit = isJapanese ? 40 : 80;

// Prompt の言語指示を動的に設定
const languageInstruction = isJapanese
  ? 'Use Japanese. Natural, conversational, not robotic.'
  : 'Use English. Natural, conversational, not robotic.';

const prompt = `...
## Critical Rules
1. NEVER exceed character limits. Hook ≤ ${hookLimit}, Content ≤ ${contentLimit}.
2. Output a SINGLE JSON object, not an array.
3. ${languageInstruction}
...`;
```

### パッチ

```diff
--- a/apps/api/src/jobs/generateNudges.js
+++ b/apps/api/src/jobs/generateNudges.js
@@ -66,7 +66,8 @@ function getScheduledHourForProblem(problem) {
 }

 // プロンプトを構築
-function buildPrompt(problem) {
+function buildPrompt(problem, preferredLanguage = 'ja') {
+  const isJapanese = preferredLanguage === 'ja';
   const problemNames = {
     staying_up_late: '夜更かし',
     cant_wake_up: '朝起きられない',
@@ -82,6 +83,19 @@ function buildPrompt(problem) {
     loneliness: '孤独'
   };

+  const problemNamesEn = {
+    staying_up_late: 'Staying up late',
+    cant_wake_up: "Can't wake up",
+    self_loathing: 'Self-loathing',
+    rumination: 'Rumination',
+    procrastination: 'Procrastination',
+    anxiety: 'Anxiety',
+    lying: 'Lying',
+    bad_mouthing: 'Bad-mouthing',
+    porn_addiction: 'Porn addiction',
+    alcohol_dependency: 'Alcohol dependency',
+    anger: 'Anger',
+    obsessive: 'Obsessive thoughts',
+    loneliness: 'Loneliness'
+  };
+
-  const problemName = problemNames[problem] || problem;
+  const problemName = isJapanese
+    ? (problemNames[problem] || problem)
+    : (problemNamesEn[problem] || problem);
+
+  const hookLimit = isJapanese ? 12 : 25;
+  const contentLimit = isJapanese ? 40 : 80;
+  const languageInstruction = isJapanese
+    ? 'Use Japanese. Natural, conversational, not robotic.'
+    : 'Use English. Natural, conversational, not robotic.';

   return `You are Anicca, an AI that reduces human suffering through perfectly-timed nudges.

@@ -102,13 +116,13 @@ function buildPrompt(problem) {
 ## Output Requirements

 ### Hook (Notification)
-- Maximum 25 characters (CRITICAL - must fit in notification preview)
+- Maximum ${hookLimit} characters (CRITICAL - must fit in notification preview)
 - Action-oriented
 - Powerful enough that they might change behavior without tapping

 ### Content (One-Screen)
-- Maximum 80 characters
+- Maximum ${contentLimit} characters
 - Specific action or insight
 - Directly related to the hook
 - Provides value even if they only glance at it
@@ -122,7 +136,7 @@ function buildPrompt(problem) {
 }

 ## Critical Rules
-1. NEVER exceed character limits. Hook ≤ 25, Content ≤ 80.
+1. NEVER exceed character limits. Hook ≤ ${hookLimit}, Content ≤ ${contentLimit}.
 2. Output a SINGLE JSON object, not an array.
-3. Use Japanese. Natural, conversational, not robotic.`;
+3. ${languageInstruction}`;
 }
```

また、`runGenerateNudges` 関数で `preferredLanguage` を取得して渡す:

```diff
@@ -146,7 +160,8 @@ async function runGenerateNudges() {
   const usersResult = await query(`
     SELECT DISTINCT
       mp.device_id as profile_id,
       mp.user_id,
-      COALESCE(mp.profile->'struggles', mp.profile->'problems', '[]'::jsonb) as problems
+      COALESCE(mp.profile->'struggles', mp.profile->'problems', '[]'::jsonb) as problems,
+      COALESCE(mp.profile->>'preferredLanguage', 'en') as preferred_language
     FROM mobile_profiles mp
     WHERE (
       (mp.profile->'struggles' IS NOT NULL AND jsonb_array_length(mp.profile->'struggles') > 0)
@@ -167,7 +182,8 @@ async function runGenerateNudges() {
   for (const user of users) {
     const problems = user.problems || [];
+    const preferredLanguage = user.preferred_language || 'en';

     for (const problem of problems) {
-      const prompt = buildPrompt(problem);
+      const prompt = buildPrompt(problem, preferredLanguage);
```

---

## 問題 4: ビルド時のログ確認

### As-Is

ビルド＆インストール後、すぐにテスト → LLM取得成功/失敗がわからない。

### To-Be

**運用ルール**: ビルド後、以下のログを確認してから実機テストを行う。

**確認方法 1: Xcode Console**
1. Xcode で実機を選択
2. Product → Run (または接続中のデバイスを選択)
3. Console に以下のログが出るか確認:

```
[LLMNudgeService] Fetching today's nudges...
[LLMNudgeService] Fetched 5 LLM nudges for today
```

または失敗時:
```
[LLMNudgeService] Failed to fetch nudges: ...
```

**確認方法 2: Console.app**
1. macOS の Console.app を開く
2. デバイス名でフィルタ
3. プロセス `aniccaios` でフィルタ
4. 上記のログを探す

**エージェントのルール**:
ビルド＆インストール後、ユーザーに「ログを確認してください」と伝えるか、Console.app でログを取得して報告する。

---

## To-Be チェックリスト

| # | 変更内容 | ファイル | 完了 |
|---|----------|---------|------|
| 1 | ランダム問題テストボタン追加 | `ProfileView.swift` | [ ] |
| 2-1 | 日本語通知テキスト短縮（16個以上） | `ja.lproj/Localizable.strings` | [ ] |
| 2-2 | 英語通知テキスト短縮（40個以上） | `en.lproj/Localizable.strings` | [ ] |
| 3-1 | LLM Prompt に言語動的挿入 | `generateNudges.js` | [ ] |
| 3-2 | DBから preferredLanguage 取得 | `generateNudges.js` | [ ] |
| 3-3 | 日本語/英語で異なる文字数制限 | `generateNudges.js` | [ ] |
| 4 | ビルド後ログ確認の運用ルール文書化 | `CLAUDE.md` | [ ] |

---

## テストマトリックス

| # | 変更 | テスト方法 | 期待結果 |
|---|------|----------|---------|
| 1 | ランダムボタン | タップして複数回確認 | 異なる問題タイプのNudgeCardが表示される |
| 2 | 短縮テキスト | 通知をプッシュして確認 | テキストが「…」で切れない |
| 3 | 言語動的挿入 | 英語設定で cron 実行 | 英語のNudgeが生成される |
| 4 | ログ確認 | ビルド後Console確認 | LLM取得ログが表示される |

---

## 優先順位

1. **問題 3（言語）** ← 英語ユーザーに日本語が出るのは致命的
2. **問題 2（テキスト短縮）** ← 通知が切れるのはUX悪い
3. **問題 1（ランダムボタン）** ← テスト効率化
4. **問題 4（ログ確認）** ← 運用改善

---

## 実行手順

### 問題 1 修正後

```bash
cd aniccaios && xcodebuild build \
  -project aniccaios.xcodeproj \
  -scheme aniccaios-staging \
  -configuration Debug \
  -destination 'generic/platform=iOS' \
  -derivedDataPath ./build/DerivedData \
  CODE_SIGN_IDENTITY="Apple Development" \
  DEVELOPMENT_TEAM=S5U8UH3JLJ

ios-deploy --bundle ./build/DerivedData/Build/Products/Debug-iphoneos/aniccaios.app --justlaunch
```

### 問題 3 修正後

```bash
# Railway staging にデプロイ
cd apps/api && railway up --environment staging

# cron を手動実行して確認
# Railway Dashboard → Nudge Cron → Trigger
```

---

## 関連ファイル

- `aniccaios/aniccaios/Views/Profile/ProfileView.swift`
- `aniccaios/aniccaios/Resources/ja.lproj/Localizable.strings`
- `aniccaios/aniccaios/Resources/en.lproj/Localizable.strings`
- `apps/api/src/jobs/generateNudges.js`
- `CLAUDE.md`

---

最終更新: 2026-01-24

