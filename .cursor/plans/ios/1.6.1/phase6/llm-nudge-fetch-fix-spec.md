# Phase 6: LLM Nudge Fetch Fix - 匿名ユーザー対応

## 概要

LLM生成NudgeのフェッチがiOS側で失敗する問題を修正する。
原因は匿名ユーザー（Apple Sign Inなし）が `.signedIn` 状態ではないため。

---

## 問題（As-Is）

### 症状

```
🔄 [LLM] Starting fetchTodaysLLMNudges...
🔄 [LLM] Not signed in, skipping fetch
❌ [LLM] Fetch failed: 操作を完了できませんでした。（aniccaios.LLMNudgeService.ServiceErrorエラー1）
```

- LLMキャッシュが空
- デバッグUIで「LLMキャッシュ確認」→「📦 LLMキャッシュ: 空」
- 「LLM再フェッチ」しても同じエラー

### 根本原因

**iOS側（LLMNudgeService.swift:19-22）:**
```swift
guard case .signedIn(let credentials) = await AppState.shared.authStatus else {
    logger.warning("🔄 [LLM] Not signed in, skipping fetch")
    throw ServiceError.notAuthenticated
}
```

- `.signedIn` 状態を必須としている
- 匿名ユーザーは `UserCredentials` を持たないため `.signedOut` 状態
- よってフェッチできない

### データ分析（2026-01-24時点）

```sql
SELECT COUNT(*) as total,
       COUNT(DISTINCT user_id) as unique_users,
       COUNT(DISTINCT device_id) as unique_devices
FROM mobile_profiles;

-- 結果: total=40, unique_users=24, unique_devices=40
```

```sql
SELECT COUNT(*) FROM mobile_profiles WHERE device_id = user_id;
-- 結果: 23（匿名ユーザー）
```

**結論**: 24人中23人が匿名ユーザー（device_id == user_id）。現行の `.signedIn` チェックでは96%のユーザーがLLM Nudgeを受け取れない。

---

## 解決策（To-Be）

### 方針

匿名ユーザーは `device_id == user_id` であるため、`device_id` を認証に使用する。

| コンポーネント | 変更 |
|---------------|------|
| iOS LLMNudgeService | `.signedIn` チェック削除、device_idベース認証 |
| iOS AppState | `.signedIn` チェック削除 |
| API | 変更なし（既にdevice-id対応） |
| Cron | 変更なし（user_idで保存、匿名はdevice_id==user_id） |

### フロー（修正後）

```
App Launch
    ↓
fetchTodaysLLMNudges() 呼び出し
    ↓
device_id を取得
    ↓
API呼び出し (device-id, user-id ヘッダー)
    ↓
nudge_events から取得（user_id == device_id で検索）
    ↓
LLMNudgeCacheに保存
    ↓
通知時刻に使用
```

---

## 受け入れ条件

1. [ ] 匿名ユーザーでも `/nudge/today` からLLM Nudgeを取得できる
2. [ ] 認証済みユーザー（Apple Sign In済み）も引き続き動作する
3. [ ] Xcodeログで `✅ [LLM] Fetched and cached X nudges` が表示される
4. [ ] デバッグUIで「LLMキャッシュ確認」→ キャッシュ内容が表示される
5. [ ] デバッグUIで「100% LLM表示テスト」→ LLM生成カードが表示される

---

## パッチ

### Patch 1: LLMNudgeService.swift

**ファイル**: `aniccaios/aniccaios/Services/LLMNudgeService.swift`

**変更内容**: `.signedIn` チェックを削除し、device_idベースの認証に変更

```swift
import Foundation
import OSLog

/// LLM生成NudgeのAPI呼び出しサービス
actor LLMNudgeService {
    static let shared = LLMNudgeService()

    private let logger = Logger(subsystem: "com.anicca.ios", category: "LLMNudgeService")
    private let session: URLSession
    private let decoder: JSONDecoder

    private init() {
        self.session = URLSession.shared
        self.decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
    }

    /// 今日生成されたNudgeを取得
    func fetchTodaysNudges() async throws -> [LLMGeneratedNudge] {
        // device_idを取得（匿名ユーザーはdevice_id == user_id）
        let deviceId = await AppState.shared.resolveDeviceId()

        let url = await MainActor.run { AppConfig.nudgeTodayURL }
        logger.info("🔄 [LLM] Requesting: \(url.absoluteString) with deviceId: \(deviceId)")

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(deviceId, forHTTPHeaderField: "device-id")

        // user-idヘッダーを設定
        // 認証済みユーザー: credentials.userId を使用
        // 匿名ユーザー: device_id を使用（device_id == user_id のため）
        var userId = deviceId
        if case .signedIn(let credentials) = await AppState.shared.authStatus {
            userId = credentials.userId
            if let jwt = credentials.jwtAccessToken {
                request.setValue("Bearer \(jwt)", forHTTPHeaderField: "Authorization")
            }
        }
        request.setValue(userId, forHTTPHeaderField: "user-id")

        do {
            let (data, response) = try await session.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                throw ServiceError.invalidResponse
            }

            guard (200..<300).contains(httpResponse.statusCode) else {
                logger.error("❌ [LLM] Failed: HTTP \(httpResponse.statusCode)")
                if let body = String(data: data, encoding: .utf8) {
                    logger.error("❌ [LLM] Response: \(body)")
                }
                throw ServiceError.httpError(httpResponse.statusCode)
            }

            let responseBody: NudgeTodayResponse
            do {
                responseBody = try decoder.decode(NudgeTodayResponse.self, from: data)
            } catch {
                logger.error("❌ [LLM] Decode error: \(error.localizedDescription)")
                throw error
            }
            logger.info("✅ [LLM] Decoded \(responseBody.nudges.count) nudges")
            return responseBody.nudges
        } catch {
            logger.error("❌ [LLM] Failed to fetch todays nudges: \(error.localizedDescription)")
            throw error
        }
    }

    enum ServiceError: Error {
        case invalidResponse
        case httpError(Int)
    }
}

/// APIレスポンス形式
private struct NudgeTodayResponse: Codable {
    let nudges: [LLMGeneratedNudge]
}
```

### Patch 2: AppState.swift

**ファイル**: `aniccaios/aniccaios/AppState.swift`

**変更内容**: init内の `.signedIn` チェックを削除

**Before (Line 134-139):**
```swift
// Phase 6: LLM生成Nudgeを取得（認証済みユーザーのみ）
Task {
    if case .signedIn = self.authStatus {
        await fetchTodaysLLMNudges()
    }
}
```

**After:**
```swift
// Phase 6: LLM生成Nudgeを取得（device_idベース、認証不要）
Task {
    await fetchTodaysLLMNudges()
}
```

---

## 追加: Railwayログ改善

### Patch 3: generateNudges.js（ログ安全化）

**ファイル**: `apps/api/src/jobs/generateNudges.js`

**変更内容**: 生成されたNudgeの内容をログに出力（環境変数で制御）

**Before (Line 342):**
```javascript
console.log(`✅ [GenerateNudges] Generated nudge for user ${user.user_id}, problem ${problem}`);
```

**After:**
```javascript
// デフォルト: プレビューのみ（機微情報保護 + ログ肥大化防止）
const hookPreview = (validated.hook || '').slice(0, 20);
const contentLen = (validated.content || '').length;
console.log(`✅ [GenerateNudges] User ${user.user_id}, ${problem}, tone=${validated.tone}, hook="${hookPreview}...", contentLen=${contentLen}`);

// 環境変数 LOG_NUDGE_CONTENT=true で全文表示（デバッグ時のみ）
if (process.env.LOG_NUDGE_CONTENT === 'true') {
  console.log(`📝 [GenerateNudges] hook="${validated.hook}"`);
  console.log(`📝 [GenerateNudges] content="${validated.content}"`);
}
```

---

## 追加: API 401エラー抑制

### Patch 4: nudge.js（401 → 空配列）

**ファイル**: `apps/api/src/routes/mobile/nudge.js`

**変更内容**: profileIdが見つからない場合、401ではなく空配列を返す（初回起動時のノイズ抑制）

**Before (Line 203-205):**
```javascript
const profileId = await resolveProfileId(userId);
if (!profileId) {
  return res.status(401).json({ error: { code: 'UNAUTHORIZED', message: 'Could not resolve profile_id' } });
}
```

**After:**
```javascript
const profileId = await resolveProfileId(userId);
if (!profileId) {
  // 匿名ユーザーの初回起動など、プロファイル未生成の場合は空配列を返す
  // 401を返すとiOS側でエラーログが出てノイズになる
  logger.info(`[NudgeToday] No profile found for userId: ${userId}, returning empty nudges`);
  return res.json({ nudges: [] });
}

---

## テストマトリックス

| # | テスト | 期待結果 | カバー |
|---|--------|---------|--------|
| 1 | 匿名ユーザーでアプリ起動 | LLM Nudgeがキャッシュされる | ✅ |
| 2 | デバッグUI「LLMキャッシュ確認」 | キャッシュ内容が表示される | ✅ |
| 3 | デバッグUI「100% LLM表示テスト」 | LLM生成カードが表示される | ✅ |
| 4 | デバッグUI「LLM再フェッチ」 | エラーなくフェッチ完了 | ✅ |
| 5 | Cronジョブ実行後 | Railwayログにプレビュー表示（全文は環境変数制御） | ✅ |
| 6 | プロファイル未生成ユーザー | 401ではなく空配列が返る | ✅ |
| 7 | LOG_NUDGE_CONTENT=true | Railwayログに全文表示 | ✅ |

---

## 境界（Boundaries）

### やること
- LLMNudgeService: device_idベース認証に変更
- AppState: .signedInチェック削除
- generateNudges.js: ログ安全化（環境変数制御）
- nudge.js: 401 → 空配列（ノイズ抑制）

### やらないこと
- Cronジョブの保存ロジック変更
- 複数デバイス対応（将来の課題）
- JWT失効フォールバック（全員匿名なので不要）

---

## 実行手順

```bash
# 1. ビルド確認
cd aniccaios && xcodebuild build -project aniccaios.xcodeproj -scheme aniccaios-staging -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=26.2' -quiet

# 2. テスト実行
cd aniccaios && xcodebuild test -project aniccaios.xcodeproj -scheme aniccaios-staging -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=26.2' -only-testing:aniccaiosTests | xcpretty

# 3. 実機デプロイ
cd aniccaios && fastlane build_for_device
```

---

## ローカライズ

変更なし（ログメッセージのみ、UIテキストなし）

---

## レビューチェックリスト

- [ ] 匿名ユーザー（96%）がLLM Nudgeを受け取れるようになる
- [ ] 認証済みユーザー（4%）の動作に影響がない
- [ ] device_id == user_id の前提が正しいことを確認した
- [ ] エラーハンドリングが適切
- [ ] ログに機微情報が含まれない（環境変数制御）
- [ ] プロファイル未生成時に401ではなく空配列を返す
- [ ] セキュリティ上の懸念がない（device_idは既にAPIで使用済み）

---

最終更新: 2026-01-24
