# Spec: 起動ハング & 通知ゼロ & API クラッシュ 修正

## 開発環境

| 項目 | 値 |
|------|-----|
| **ブランチ** | `feature/startup-notification-fix` |
| **ベースブランチ** | `dev` |
| **作業状態** | ✅ API修正済み（Anicca実施）/ ⏳ iOS修正残件あり |
| **対象バージョン** | 1.6.3 |
| **App Store 再提出** | **必須**（iOS コード変更のため） |

---

## 現在の状態（2026-03-01）

| 問題 | 状態 | 実施者 | 手法 |
|------|------|--------|------|
| 🔴 API クラッシュループ | ✅ **修正済み** | Anicca (Mac Mini) | `paymentMiddleware(..., false)` — `syncFacilitatorOnStart = false` |
| 🔴 通知ゼロ | ✅ **修正済み** | Anicca (Mac Mini) | API復旧により自動解消 |
| 🟡 iOS 起動 30秒ハング（潜在リスク） | ⏳ **未修正** | 未対応 | API 稼働中は表面化しないが、次に API が落ちたら再発 |

### Anicca の実際の修正内容

**コミット:** `1d7dab630 fix: disable x402 syncFacilitatorOnStart to prevent crash on invalid CDP key`

```javascript
// apps/api/src/routes/x402/index.js（Anicca の修正）
// 5番目の引数 false = syncFacilitatorOnStart を無効化
router.use(
  paymentMiddleware(routes, server, undefined, undefined, false)
);
```

**根本原因（Anicca の spec より）:** `paymentMiddleware` が内部で `httpServer.initialize()` を非同期呼び出し → `"Invalid key format"` で Promise reject → Unhandled Rejection → Node.js プロセス即死。`syncFacilitatorOnStart = false` で起動時初期化を無効化することでクラッシュを防止。

**注意:** Anicca の修正は **fail-open**（x402 失敗 → payment gate なしで動作継続）。本 spec が設計した fail-closed（503返却）とは異なる。現状動作しているため fail-closed への変更は別タスク。

---

## 1. 何が起きているか（原因）※参考：修正済み

### 症状（当時）

| 問題 | 症状 |
|------|------|
| 🔴 起動ハング | App Store版がずっとローディング画面のまま |
| 🔴 通知ゼロ | 昨日は大量に届いた通知が今日は1件もない |

### 原因は1つ: API サーバーがクラッシュループ中（修正済み）

Railway で確認済み: **API deployment status = CRASHED**（2026-02-28T13:58:48 UTC（22:58 JST）以降）

`paymentMiddleware` が内部で非同期に `httpServer.initialize()` を呼ぶ → `"Invalid key format"` で Unhandled Promise Rejection → プロセス即死 → Railway が再起動 → また死ぬ → ループ

**これによって2つの症状が発生していた:**

```
API が死んでいる
    ↓
┌───────────────────────────────────┬───────────────────────────────────┐
│ アプリ起動時に API を呼ぶ          │ 毎分の通知送信ジョブも              │
│ → 応答がない → 30秒待つ           │   API プロセスの中にある            │
│ → 「ローディング画面が30秒続く」   │ → API が死んでいる = ジョブも死亡   │
│                                   │ → 「通知が届かない」                │
└───────────────────────────────────┴───────────────────────────────────┘
```

---

## 2. 直った後の姿

| 状態 | 修正前（2026-02-28） | 現在（✅ API修正後） | iOS修正後（目標） |
|------|---------------------|---------------------|------------------|
| Railway API | CRASHED、クラッシュループ | ✅ SUCCESS、安定稼働 | 変わらず ✅ |
| 通知 | 1件も届かない | ✅ 正常送信中 | 変わらず ✅ |
| x402 ルート | 全部不可 | fail-open（payment gate なし）で動作 | 変わらず（別タスク） |
| アプリ起動（API 正常時） | ~10秒 | ✅ 高速（API が応答するため） | **≤ 8秒**（タイムアウト短縮後） |
| アプリ起動（API 不在時） | 30秒ハング | **依然 30秒ハング**（潜在リスク） | **≤ 10秒**（8s timeout後にメイン画面） |

---

## 3. 受け入れ条件

### ✅ 完了済み（API 修正）

| # | 条件 | 状態 |
|---|------|------|
| AC-1 | Railway API deployment status が SUCCESS | ✅ 完了 |
| AC-2 | デプロイ直後にプロセスが安定起動 | ✅ 完了 |
| AC-3 | `/health` が 200 を返す | ✅ 完了 |
| AC-5 | APNs 送信ジョブが15分以内に動き始める | ✅ 完了（通知届いている） |
| AC-8 | デプロイ後5分間で再起動が発生しない | ✅ 完了 |

### ⏳ 残件（iOS 修正）

| # | 条件 | 確認方法 | しきい値 |
|---|------|---------|---------|
| AC-4 | アプリ起動が API **不在時でも** 10秒以内に完了する | シミュレータで API なし状態でコールドスタート計測 | ≤ 10秒 |
| AC-9 | `bootstrapProfileFromServerIfAvailable` が 8秒でタイムアウトする | `test_bootstrapTimesOutIn8Seconds()` | Unit Test PASS |
| AC-10 | タイムアウト後に `isBootstrappingProfile` が `false` になる | `test_bootstrapFlagClearedAfterTimeout()` | Unit Test PASS |

---

## 4. As-Is / To-Be

### 修正1: x402 クラッシュ（API 側）— ✅ 完了済み（Anicca実施）

**実際の修正（As-Was → As-Is）:**

```javascript
// Before（クラッシュする）:
router.use(paymentMiddleware({ ... }, server));

// After（Anicca が修正済み）:
router.use(paymentMiddleware({ ... }, server, undefined, undefined, false));
//                                                                  ↑ syncFacilitatorOnStart = false
```

変更ファイル: `apps/api/src/routes/x402/index.js`（`dev` + `main` 両方に反映済み）

---

### 修正2: iOS 側の API タイムアウト短縮（iOS 側）— ⏳ 未実施

**なぜ必要か:**

API が正常な今は表面化しないが、次に API が落ちると再び30秒ハングが再発する。iOS のタイムアウト値をベストプラクティスに合わせることで、どのような API 状態でも UI が10秒以内に表示されることを保証する。

**ベストプラクティス根拠:**

ソース: [Apple Developer — Reducing your app's launch time](https://developer.apple.com/documentation/xcode/reducing-your-app-s-launch-time) / 核心の引用: 「Network latency should never block app launch. Use a short timeout and show cached or default data immediately.」

ソース: [Apple Developer — URLRequest.timeoutInterval](https://developer.apple.com/documentation/foundation/urlrequest/timeoutinterval) / 核心の引用: 「The default timeout interval is 60 seconds. Reduce it for launch-time requests that should fail fast.」

ソース: [Apple Developer — URLSessionConfiguration.httpMaximumConnectionsPerHost](https://developer.apple.com/documentation/foundation/urlsessionconfiguration/1407597-httpmaxicomconnectionsperhost) / 核心の引用: 「The default value is 6 on iOS. Setting it to 1 serializes all requests.」

**起動 SLO 定義:**

| 項目 | 値 |
|------|-----|
| 計測開始点 | アプリアイコンタップ（Cold start） |
| 計測終了点 | メイン画面（ContentView のメインコンテンツ）が表示される瞬間 |
| API 正常時の合格基準 | ≤ 8秒 |
| API 不在時の最大待機 | 8s（per-request timeout） + iOS URLSession オーバーヘッド（≤2s） = ≤ 10秒 |
| タイムアウト後 | `isBootstrappingProfile = false` に遷移し必ずメイン画面へ |

**As-Is:**

```swift
// NetworkSessionManager.swift:20（現状）
config.httpMaximumConnectionsPerHost = 1
// ↑ Apple デフォルト（iOS）は 6。1に設定すると全リクエストが直列化される
// 根拠なし。起動時の並列ウォームアップを阻害している

// NetworkSessionManager.swift:22（現状）
config.timeoutIntervalForRequest = 30.0
// ↑ グローバル timeout 30秒。API 不在時は起動が30秒ハングする

// AppState.swift:bootstrapProfileFromServerIfAvailable()
var request = URLRequest(url: AppConfig.profileSyncURL)
// ↑ per-request timeout 未設定 → セッション global 30秒が適用される
```

**To-Be:**

```swift
// NetworkSessionManager.swift:20（変更後）
config.httpMaximumConnectionsPerHost = 4
// ↑ Apple BP: 並列接続を許可。起動時ウォームアップリクエストを並列化

// NetworkSessionManager.swift:22（変更なし — 背景通信には30秒が適切）
config.timeoutIntervalForRequest = 30.0

// AppState.swift:bootstrapProfileFromServerIfAvailable()（変更後）
var request = URLRequest(url: AppConfig.profileSyncURL)
request.timeoutInterval = 8.0
// ↑ 起動専用の per-request timeout。8秒でタイムアウト → defer で isBootstrappingProfile = false
// グローバル設定を変えず、起動リクエストのみ短縮する（Apple BP）
```

**変更ファイル:**
- `aniccaios/aniccaios/Services/NetworkSessionManager.swift:20`（1行変更）
- `aniccaios/aniccaios/AppState.swift`（`bootstrapProfileFromServerIfAvailable` 内に1行追加）

---

## 5. テストマトリックス

### ✅ 完了済みテスト（API 修正確認済み）

| # | テスト | 状態 |
|---|--------|------|
| 1 | Railway status = SUCCESS | ✅ |
| 2 | x402 失敗ログ出力 + プロセス継続 | ✅ |
| 4 | `/health` が 200 | ✅ |
| 10 | 5分後も再起動なし | ✅ |
| 11 | APNs sender ログ出力 | ✅（通知届いている） |

### ⏳ 残件テスト（iOS 修正で実施）

| # | 何をテストするか | テスト名 / 確認方法 | 種別 | AC |
|---|----------------|-------------------|------|----|
| 8 | bootstrap が 8秒でタイムアウトする | `test_bootstrapTimesOutIn8Seconds()` | Unit | AC-9 |
| 9 | タイムアウト後に `isBootstrappingProfile` が false になる | `test_bootstrapFlagClearedAfterTimeout()` | Unit | AC-10 |
| 12 | API 不在でも実機起動が10秒以内に完了する | コールドスタート手動計測 ≤ 10秒 | Manual | AC-4 |

---

## 6. 境界（やらないこと）

| 項目 | 理由 |
|------|------|
| fail-closed（503返却）への変更 | Anicca が fail-open で修正済み。別タスク |
| x402 の鍵フォーマット問題の根本修正 | API が動いている。鍵修正は別タスク |
| `timeoutIntervalForRequest` の全体変更 | 背景通信に影響する。起動リクエストのみ per-request で短縮 |
| AppDelegate の Task リアーキテクチャ | 影響範囲が広い。タイムアウト短縮で十分 |
| 起動 SLO の反復統計計測（3回以上・p95/p99） | 緊急修正の受け入れに手動1回確認で十分 |

---

## 7. 実行手順

### ✅ Step 1-8 完了済み（API 修正 — Anicca実施）

| Step | 内容 | 状態 |
|------|------|------|
| 1 | `syncFacilitatorOnStart = false` を追加 | ✅ |
| 2 | dev にコミット & push | ✅ |
| 3 | main に push → Railway production デプロイ | ✅ |
| 4 | `/health` curl 200 確認 | ✅ |
| 5-8 | Railway log / APNs確認 | ✅ |

### ⏳ Step 9-11 残件（iOS 修正）

```
Step 9:  NetworkSessionManager.swift:20 を 1 → 4 に変更
Step 10: AppState.swift:bootstrapProfileFromServerIfAvailable() に request.timeoutInterval = 8.0 を追加
Step 11: cd aniccaios && fastlane test（test #8, #9 PASS）
Step 12: 実機/シミュレータで API を止めた状態でコールドスタート計測 ≤ 10秒（AC-4）
Step 13: dev に commit & push
Step 14: App Store に再提出（v1.6.3）
```

---

## E2E 判定

| 項目 | 値 |
|------|-----|
| UI 変更 | なし |
| 新画面 | なし |
| 結論 | Maestro E2E: **不要**（タイムアウト値変更のみ。Unit Test + 手動起動計測で確認） |

---

## ユーザー作業

**なし。** 全て Claude が実行する。

---

*作成: 2026-02-28*
*API修正完了（Anicca）: 2026-03-01 — `syncFacilitatorOnStart = false`*
*iOS修正残件: NetworkSessionManager + AppState タイムアウト短縮*

*Codex review iter 1-10: ok: true まで完了（詳細は旧spec版参照）*
*ベストプラクティス: [Apple Developer — Reducing your app's launch time](https://developer.apple.com/documentation/xcode/reducing-your-app-s-launch-time)*
