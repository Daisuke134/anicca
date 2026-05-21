# x402 初期化クラッシュ修正 Spec

## 1. 概要（What & Why）

### What

API サーバー（Railway Production）が x402 payment middleware の非同期初期化エラーで**プロセスごと死んでいる**。サーバーが起動→クラッシュ→再起動を無限ループしており、**全 API エンドポイント（iOS アプリ含む）が完全に使えない状態**。

### Why

`@x402/express` の `paymentMiddleware` は内部で `httpServer.initialize()` を非同期で呼ぶ。この Promise が reject されると **unhandled rejection** となり Node.js プロセスが死ぬ。

現在 Railway の `CDP_API_KEY_SECRET` にはクライアントキー（短い文字列）が入っており、PEM 秘密鍵ではないため、facilitator への接続時に `UserInputValidationError: Invalid key format` が発生する。

### 根本原因の流れ

```
paymentMiddleware() 呼び出し
    ↓
内部で httpServer.initialize() を非同期実行（Promise 生成）
    ↓
initialize() → facilitator に接続 → CDP_API_KEY_SECRET で JWT 生成
    ↓
「Invalid key format」→ Promise reject
    ↓
この Promise は paymentMiddleware 呼び出し元の try-catch では捕まらない
（非同期で後から reject されるため）
    ↓
Unhandled Promise Rejection → Node.js プロセス死亡
```

### ソース

ソース: [x402 express パッケージ ソースコード](https://github.com/coinbase/x402/blob/main/typescript/packages/http/express/src/index.ts) / 核心の引用: `let initPromise: Promise<void> | null = syncFacilitatorOnStart ? httpServer.initialize() : null;`（84行目）

ソース: [x402 paymentMiddleware シグネチャ](https://github.com/coinbase/x402/blob/main/typescript/packages/http/express/src/index.ts#L321-L337) / 核心の引用: `export function paymentMiddleware(routes, server, paywallConfig?, paywall?, syncFacilitatorOnStart: boolean = true)`（第5引数で起動時初期化を制御）

## 2. 受け入れ条件

| # | 条件 | テスト可能な形式 |
|---|------|-----------------|
| AC-1 | `CDP_API_KEY_SECRET` が不正な値でも API サーバーが起動し続ける | Railway ログに `Anicca API Server running on port 8080` が出て、プロセスが死なない |
| AC-2 | x402 初期化失敗時、他の API エンドポイント（`/api/mobile/*` 等）は正常に動作する | `curl` で `/api/mobile/nudge/today` が 200 を返す |
| AC-3 | x402 初期化失敗時、emotion-detector / buddhist-counsel は**課金なし**で動作する | `curl -X POST /api/x402/emotion-detector` が 200 を返す |
| AC-4 | `CDP_API_KEY_SECRET` が正しい PEM 鍵の場合、x402 課金ゲートが正常に動作する | ログに `💰 x402 payment middleware active` が出て、未払いリクエストに 402 が返る |

## 3. As-Is / To-Be

### As-Is（現状）

**ファイル:** `apps/api/src/routes/x402/index.js`

```
paymentMiddleware(routes, server)
    ↓
第5引数 syncFacilitatorOnStart = true（デフォルト）
    ↓
内部で httpServer.initialize() が即座に実行
    ↓
鍵エラー → unhandled rejection → プロセス死亡
```

| 項目 | 現状 |
|------|------|
| `paymentMiddleware` の呼び出し | `paymentMiddleware(routes, server)` — 第5引数なし（デフォルト `true`） |
| 非同期エラーハンドリング | try-catch で囲んでいるが、`initialize()` の Promise reject は捕まらない |
| サーバー状態 | 起動→クラッシュ→再起動の無限ループ |

### To-Be（変更後）

```
paymentMiddleware(routes, server, undefined, undefined, false)
    ↓
第5引数 syncFacilitatorOnStart = false
    ↓
起動時に httpServer.initialize() を実行しない
    ↓
サーバーは正常に起動
    ↓
リクエスト時に初期化を試みる → 失敗しても Express エラーハンドラが捕まえる
```

| 項目 | 変更後 |
|------|--------|
| `paymentMiddleware` の呼び出し | `paymentMiddleware(routes, server, undefined, undefined, false)` |
| 非同期エラーハンドリング | 起動時の初期化自体をスキップ。リクエスト時の初期化エラーは Express ミドルウェアチェーン内で発生するため、既存の try-catch で捕まる |
| サーバー状態 | 正常に起動。x402 は初回リクエスト時に初期化を試み、失敗したらそのリクエストだけエラーを返す（サーバーは死なない） |

### 変更箇所

| ファイル | 変更内容 |
|---------|---------|
| `apps/api/src/routes/x402/index.js` 101行目 | `paymentMiddleware(routes, server)` → `paymentMiddleware(routes, server, undefined, undefined, false)` |

**変更は1行のみ。**

## 4. テストマトリックス

| # | To-Be | テスト名 | カバー |
|---|-------|----------|--------|
| 1 | 不正な鍵でもサーバーが起動し続ける | `test_server_starts_with_invalid_cdp_key` | OK |
| 2 | x402 失敗時に他の API が正常動作 | `test_other_endpoints_work_when_x402_fails` | OK |
| 3 | x402 失敗時に emotion-detector が課金なしで動作 | `test_emotion_detector_works_without_payment_gate` | OK |
| 4 | 正しい鍵の場合は課金ゲートが有効 | `test_payment_gate_active_with_valid_key` | OK |

**テスト方法:** Railway デプロイ後のログ確認 + `curl` による動作確認。ユニットテストはライブラリ内部の動作であり、x402 ライブラリの責務のためスコープ外。

## 5. 境界

### やること

| やること |
|---------|
| `paymentMiddleware` の第5引数を `false` に変更（1行） |

### やらないこと

| やらないこと | 理由 |
|-------------|------|
| `CDP_API_KEY_SECRET` の値を変更する | ユーザーが Coinbase ポータルで PEM 鍵を取得して Railway に貼る作業 |
| x402 ライブラリのコードを変更する | 外部依存。変更不可 |
| emotion-detector / buddhist-counsel のロジック変更 | 今回のスコープ外 |
| DB パスワードエラーの修正 | x402 クラッシュが原因の連鎖障害。x402 を直せば解消する |

### 触るファイル

| ファイル | 変更 |
|---------|------|
| `apps/api/src/routes/x402/index.js` | 1行変更 |

### 触らないファイル

| ファイル | 理由 |
|---------|------|
| `apps/api/src/server.js` | 変更不要 |
| `apps/api/src/routes/x402/buddhistCounsel.js` | スコープ外 |
| `apps/api/src/routes/x402/emotionDetector.js` | スコープ外 |
| iOS コード全般 | 無関係 |

## 6. 実行手順

```bash
# 1. コード変更（1行）
# apps/api/src/routes/x402/index.js の paymentMiddleware 呼び出しに第5引数 false を追加

# 2. コミット & push
git add -A && git commit -m "fix: disable x402 syncFacilitatorOnStart to prevent crash on invalid CDP key" && git push origin dev

# 3. main にマージ & push（Railway Production 自動デプロイ）
git checkout main && git merge dev && git push origin main && git checkout dev

# 4. デプロイ確認（2-3分後）
railway logs  # 「Anicca API Server running on port 8080」が出て死なないことを確認
```

## E2E判定

| 項目 | 値 |
|------|-----|
| UI変更 | なし |
| 新画面 | なし |
| 新ボタン/操作 | なし |
| 結論 | Maestro E2E シナリオ: **不要**（理由: バックエンド1行変更のみ、UI 変更なし） |

## ユーザー作業（実装後）

| # | タスク | 手順 | 目的 |
|---|--------|------|------|
| 1 | Coinbase ポータルで PEM 秘密鍵を取得 | https://portal.cdp.coinbase.com/projects/api-keys → Secret API Keys → Create API key → Secret をコピー | x402 課金ゲートを有効にする |
| 2 | Railway の `CDP_API_KEY_SECRET` を貼り替え | https://railway.com → API → Variables → `CDP_API_KEY_SECRET` を新しい PEM 鍵に更新 | 上記と同じ |
| 3 | ログ確認 | Railway ログに `💰 x402 payment middleware active` が出ることを確認 | 課金ゲートが正常に起動したことの確認 |
