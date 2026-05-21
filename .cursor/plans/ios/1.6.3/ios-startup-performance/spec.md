# Spec: iOS 起動タイムアウト最適化（潜在リスク排除）

## 開発環境

| 項目 | 値 |
|------|-----|
| **ブランチ** | `feature/ios-startup-perf` |
| **ベースブランチ** | `dev` |
| **作業状態** | Spec作成 |
| **対象バージョン** | 1.6.3 |
| **App Store 再提出** | **必須**（iOS コード変更のため） |

---

## 1. 何が起きているか（原因）

### 潜在リスク

API クラッシュは `1d7dab630` で修正済み。しかし iOS 側に**残存リスク**がある。

API が再び遅延・不安定になった場合、今の iOS コードは**最大30秒、画面がローディングのままになる**。

### 根本原因

| ファイル | 問題のコード | 値 | リスク |
|---------|------------|-----|--------|
| `NetworkSessionManager.swift:22` | `config.timeoutIntervalForRequest = 30.0` | **30秒** | API 不安定時に 30 秒ハング |
| `NetworkSessionManager.swift:20` | `config.httpMaximumConnectionsPerHost = 1` | **1** | 起動時の並列リクエストが直列化 |
| `AppState.swift:450` | `URLRequest(url: ...)` — per-request timeout なし | **なし** | セッションの 30 秒が無条件に適用 |

### ベストプラクティス

ソース: [Apple Developer Documentation - Reducing your app's launch time](https://developer.apple.com/documentation/xcode/reducing-your-app-s-launch-time) / 核心の引用: 「Waiting for API responses before rendering the first screen is one of the most damaging launch-time mistakes, and network latency should never block app launch.」

ソース: [Apple Developer Documentation - httpMaximumConnectionsPerHost](https://developer.apple.com/documentation/foundation/urlsessionconfiguration/httpmaximumconnectionsperhost) / 核心の引用: iOS の HTTP/1.1 デフォルト値は **4**。1 に下げると接続が直列化する。

ソース: [APIYouWontHate - Taking a Timeout from Poor Performance](https://apisyouwonthate.com/blog/taking-a-timeout-from-poor-performance/) / 核心の引用: 「A timeout should be set on the client side to something that is reasonable for what you are trying to accomplish and have a failure or fallback loop.」

| 設定 | 現在値 | ベストプラクティス | 根拠 |
|------|-------|-----------------|------|
| `timeoutIntervalForRequest`（グローバル） | 30.0 秒 | **30.0 のまま**（バックグラウンド通信用） | 背景ジョブは時間がかかることがある |
| `bootstrapProfile` の per-request timeout | なし（30 秒が適用） | **8.0 秒**を明示指定 | Apple: 起動時 API は 8〜10 秒以内 |
| `httpMaximumConnectionsPerHost` | 1 | **4**（iOS デフォルト値） | Apple デフォルト。1 に下げる理由がない |

---

## 2. 直った後の姿

| 状態 | 今（修正前） | 修正後 |
|------|------------|-------|
| API が正常 | 0.5 秒で起動画面表示 ✅ | 0.5 秒で起動画面表示 ✅（変わらず） |
| API が遅延（2〜5 秒） | 2〜5 秒待つ | 2〜5 秒待つ（変わらず） |
| API がダウン or 8 秒超タイムアウト | **30 秒ハング** ❌ | **8 秒でタイムアウト → 即画面表示** ✅ |
| 起動時の並列リクエスト | 直列（1 接続ずつ） | 並列（最大 4 接続）→ わずかに速くなる |

**ユーザー体験の変化:**
- API が死んでいても、起動から **8 秒以内に必ずメイン画面が表示される**
- 「ローディングが30秒続く」は永遠に起きなくなる
- 通常時（API 正常）は体感変化なし

---

## 3. 受け入れ条件

| # | 条件 | 確認方法 | しきい値 |
|---|------|---------|---------|
| AC-1 | API がダウンしている状態でアプリを起動し、8〜10 秒以内にメイン画面が表示される | シミュレータで API URL を無効な URL に書き換えてビルド → 起動計測 | ≤ 10 秒 |
| AC-2 | 正常時の起動時間が劣化していない | 実機 Cold start 1 回計測 | ≤ 10 秒（変化なし） |
| AC-3 | `bootstrapProfile` タイムアウト後に `isBootstrappingProfile = false` になる | ユニットテスト | `isBootstrappingProfile == false` |

---

## 4. As-Is / To-Be

### 変更1: `NetworkSessionManager.swift`

**As-Is:**
```swift
config.httpMaximumConnectionsPerHost = 1      // 直列化
config.timeoutIntervalForRequest = 30.0        // セッションデフォルト
```

**To-Be:**
```swift
config.httpMaximumConnectionsPerHost = 4      // iOS デフォルト値に戻す
config.timeoutIntervalForRequest = 30.0        // バックグラウンド通信用 → 維持
```

### 変更2: `AppState.swift` — `bootstrapProfileFromServerIfAvailable()`

**As-Is:**
```swift
var request = URLRequest(url: AppConfig.profileSyncURL)
request.httpMethod = "GET"
// ← per-request timeout なし（セッションの 30 秒が適用される）
```

**To-Be:**
```swift
var request = URLRequest(url: AppConfig.profileSyncURL)
request.httpMethod = "GET"
request.timeoutInterval = 8.0   // 起動時 API: 8 秒で fail-fast
// ← セッション全体の 30 秒ではなく、このリクエストだけ 8 秒
```

**変更ファイル:**
- `aniccaios/aniccaios/Services/NetworkSessionManager.swift:20`
- `aniccaios/aniccaios/AppState.swift:450`（`bootstrapProfileFromServerIfAvailable` 内）

**変更行数: 2 行。**

---

## 5. テストマトリックス

| # | 何をテストするか | テスト名 | 種別 | AC |
|---|----------------|---------|------|----|
| 1 | bootstrap が 8 秒でタイムアウトする | `test_bootstrapTimesOutIn8Seconds()` | Unit | AC-1 |
| 2 | タイムアウト後に `isBootstrappingProfile` が false になる | `test_bootstrapFlagClearedAfterTimeout()` | Unit | AC-3 |
| 3 | API ダウン時に 10 秒以内にメイン画面が出る | シミュレータで無効 URL → 起動計測 | Manual | AC-1 |
| 4 | 正常時の起動速度が劣化しない | 実機 Cold start 計測 ≤ 10 秒 | Manual | AC-2 |

---

## 6. 境界

| やらないこと | 理由 |
|------------|------|
| AppDelegate の Task リアーキテクチャ（UI 表示後に API 呼ぶ） | 影響範囲大。1.6.4 以降で検討 |
| `waitsForConnectivity = false` の追加 | 現状 `waitsForConnectivity` はデフォルト false（変更不要） |
| バックグラウンド通信の timeout 変更 | 30 秒維持で問題なし |

---

## 7. 実行手順

```
Step 1: NetworkSessionManager.swift:20 を httpMaximumConnectionsPerHost = 4 に変更
Step 2: AppState.swift の bootstrapProfileFromServerIfAvailable() 内に request.timeoutInterval = 8.0 を追加
Step 3: fastlane test でユニットテスト (#1, #2) を実行
Step 4: シミュレータで AC-1 確認（API ダウン時に 10 秒以内に画面が出る）
Step 5: dev にコミット & push
Step 6: fastlane full_release でバージョンを上げて App Store 提出
```

---

## E2E 判定

| 項目 | 値 |
|------|-----|
| UI 変更 | なし |
| 新画面 | なし |
| 結論 | Maestro E2E: **不要**（起動タイムアウトはユニットテスト + 手動計測で確認） |

---

## ユーザー作業

**なし。** 全て Claude が実行する。

---

*作成: 2026-03-01*
*ソース: Apple Developer Documentation / APIYouWontHate / useyourloaf.com*
*変更2行: NetworkSessionManager.swift + AppState.swift*
