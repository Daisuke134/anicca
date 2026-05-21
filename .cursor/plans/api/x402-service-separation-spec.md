# Spec: x402 サービス分離（Strangler Fig パターン）

## 開発環境

| 項目 | 値 |
|------|-----|
| **ブランチ** | `dev` |
| **ベースブランチ** | `dev` |
| **作業状態** | GATE 2 実装完了（全49テスト GREEN、Railway サービス作成済み、デプロイ待ち） |
| **対象** | API + iOS |

---

## 1. 概要（What & Why）

### What

x402 エージェント向け API（全8エンドポイント）を既存 API サーバーから分離し、Railway 上に独立サービスとしてデプロイする。加えて、iOS アプリの API タイムアウトを短縮し、サーバー障害時にアプリが固まらないようにする。

**重要な前提:** x402 エンドポイントは**外部AIエージェント専用の有料API**。iOS Anicca アプリは `/api/mobile/*` を使用し、x402 は一切呼ばない。したがって、x402 ルートの URL 変更（`/api/x402/*` → 新ドメイン直下）にクライアント互換期間は不要。Facade/redirect も不要。

### Why

2026-02-28 に x402 の CDP 鍵エラーが API サーバー全体をクラッシュさせた。**お金を払っているユーザーへの通知が丸1日止まった。** x402 と iOS 通知は無関係なのに、同じプロセスにいるせいで巻き添えで死んだ。**二度と起こしてはいけない。**

### ベストプラクティス根拠

| # | ソース | URL | 核心の引用 |
|---|--------|-----|-----------|
| BP-1 | AWS Prescriptive Guidance - Strangler Fig | https://docs.aws.amazon.com/prescriptive-guidance/latest/modernization-decomposing-monoliths/strangler-fig.html | 「incrementally transform a monolithic application into microservices by replacing a particular functionality with a new service」 |
| BP-2 | Microsoft Azure - Strangler Fig Pattern | https://learn.microsoft.com/en-us/azure/architecture/patterns/strangler-fig | 「A facade (proxy) intercepts requests that go to the back-end legacy system. The facade routes these requests either to the legacy application or to the new services.」 |
| BP-3 | microservices.io - Strangler Application | https://microservices.io/patterns/refactoring/strangler-application.html | 「gradually replace specific pieces of functionality with new applications and services」 |
| BP-4 | Railway Monorepo Guide | https://docs.railway.com/guides/deploying-a-monorepo | 「Setting this means that Railway will only pull down files from that directory when creating new deployments.」 |
| BP-5 | Railway Blog - Deploying Monorepos | https://blog.railway.com/p/deploying-monorepos | 「Isolated monorepo components are 100% contained in the folder they reside in」 |
| BP-6 | Express.js - Health Checks and Graceful Shutdown | https://expressjs.com/en/advanced/healthcheck-graceful-shutdown.html | 「Once the application gets this signal, it should stop accepting new requests, finish all the ongoing requests, clean up the resources it used, including database connections and file locks then exit.」 |
| BP-7 | Prisma - Working With Data in Large Teams | https://www.prisma.io/blog/working-with-data-in-large-teams | 「Version every schema change in Git. Review schema changes through pull requests.」 |
| BP-8 | Render - Connecting Multiple Services to Shared DB | https://render.com/articles/connecting-multiple-services-to-a-shared-database | 「Total Service Pools <= Database Connection Limit - Reserved Connections (approx. 3)」 |

---

## 2. 受け入れ条件

| # | 条件 | 確認方法 |
|---|------|---------|
| AC-1 | x402-agents サービスが Railway で独立して動作する | `curl https://<x402-agents-domain>/health` → 200 |
| AC-2 | 全8エンドポイントが x402 課金ゲート付きで動作する | 各 `curl -X POST /<endpoint>` が 402（未払い）を返す |
| AC-3 | 既存 API から x402 ルートが完全に削除されている | `curl -X POST https://anicca-proxy-production.up.railway.app/api/x402/emotion-detector` → 404 |
| AC-4 | 既存 API の `/health` が 200 を返す | `curl https://anicca-proxy-production.up.railway.app/health` → 200 |
| AC-5 | 通知送信ジョブが正常動作する | Railway ログで `problemNudgeApnsSender` が出力される |
| AC-6 | x402-agents がクラッシュしても既存 API に影響なし | x402-agents を停止 → 既存 API の `/health` が 200 |
| AC-7 | iOS アプリが API 不在でも 10秒以内にメイン画面表示 | 実機 Cold start 計測 <= 10秒 |
| AC-8 | x402-agents のログに payment middleware active ログが出る | Railway ログ確認 |
| AC-9 | x402-agents が SIGTERM で graceful shutdown する | Railway ログで shutdown + Prisma disconnected 確認 |
| AC-10 | 既存 API の package.json から x402 依存が消えている | `grep @x402 apps/api/package.json` → 0件 |
| AC-11 | x402-agents に rate limiting（30 req/min）が適用されている | 31回連続リクエスト → 429 Too Many Requests |
| AC-12 | x402-agents の既存テストが移動後も GREEN | `cd apps/x402-agents && npm test` → all pass |
| AC-13 | x402 初期化失敗時に全ルートが 503 を返す（fail-closed） | CDP 鍵を無効化 → 各エンドポイントに POST → 503 |
| AC-14 | 必須環境変数欠落時にプロセスが起動失敗する | `X402_WALLET_ADDRESS` 未設定 → process.exit(1) |
| AC-15 | DB 接続断時に 503 を返す | DB URL を無効化 → `/health` → 503 |

---

## 3. As-Is / To-Be

### 修正1: x402 を独立サービスに分離（API 側）

**As-Is:**

```
apps/api/
├── src/
│   ├── routes/
│   │   ├── x402/                    ← API サーバーの中にいる
│   │   │   ├── index.js             ← paymentMiddleware + 8ルート定義
│   │   │   ├── emotionDetector.js
│   │   │   ├── buddhistCounsel.js
│   │   │   ├── contextCompressor.js
│   │   │   ├── decisionClarifier.js
│   │   │   ├── focusCoach.js
│   │   │   ├── habitDesigner.js
│   │   │   ├── intentRouter.js
│   │   │   ├── promptSanitizer.js   ← NOTE: network がハードコード 'eip155:8453'（他7ルートは変数）
│   │   │   └── __tests__/
│   │   ├── index.js                 ← x402Router をマウント（L34, L70-71）+ rate limit 30 req/min（L70）
│   │   └── ...
│   ├── services/
│   │   └── buddhistCounselService.js  ← x402 専用サービス（唯一の外部サービス依存）
│   └── server.js
└── package.json                     ← x402 依存パッケージも含む
```

**現在の x402 ルーター構造（apps/api/src/routes/x402/index.js）:**

- x402ResourceServer + ExactEvmScheme + HTTPFacilitatorClient で手動初期化
- `server.initialize()` を try-catch で囲み、失敗しても続行
- paymentMiddleware に全8ルートの課金設定を一括登録
- 各ルートファイルは express.Router() + zod + OpenAI + prisma を使用
- buddhistCounsel.js のみ `buddhistCounselService.js` を import
- 他7ルートは外部サービス依存なし（OpenAI + prisma のみ）
- **prompt-sanitizer のみ** network を `'eip155:8453'` にハードコード（他7ルートは `network` 変数使用）→ **そのまま移植する（ハードコード維持）。** Mainnet 固定は意図的設計（prompt-sanitizer は Base Mainnet 専用）

**To-Be:**

```
apps/api/                              ← 既存 API（x402 を完全削除）
├── src/
│   ├── routes/
│   │   ├── index.js                  ← x402Router のマウント削除（L34, L70-71）
│   │   └── ...（x402/ ディレクトリ削除）
│   ├── services/                     ← buddhistCounselService.js 削除
│   └── server.js
└── package.json                      ← @x402/*, @coinbase/x402, ethers を削除

apps/x402-agents/                      ← 新サービス（完全独立）
├── src/
│   ├── routes/
│   │   ├── emotionDetector.js        ← apps/api から移動（import パス修正）
│   │   ├── buddhistCounsel.js        ← apps/api から移動（import パス修正）
│   │   ├── contextCompressor.js      ← apps/api から移動（import パス修正）
│   │   ├── decisionClarifier.js      ← apps/api から移動（import パス修正）
│   │   ├── focusCoach.js             ← apps/api から移動（import パス修正）
│   │   ├── habitDesigner.js          ← apps/api から移動（import パス修正）
│   │   ├── intentRouter.js           ← apps/api から移動（import パス修正）
│   │   ├── promptSanitizer.js        ← apps/api から移動（import パス修正、network ハードコード維持）
│   │   └── __tests__/               ← apps/api から移動（import パス修正）
│   ├── services/
│   │   └── buddhistCounselService.js  ← apps/api から移動
│   ├── lib/
│   │   └── prisma.js                 ← DB 接続（同じ PostgreSQL、connection_limit=5）
│   └── server.js                     ← 新規（Express + x402 + rate limit + CORS + /health + graceful shutdown）
├── prisma/
│   └── schema.prisma                 ← 既存 API と同じスキーマ（コピー）
├── package.json                      ← x402 依存 + openai + prisma + zod + express
├── railway.toml                      ← Railway 設定ファイル
└── vitest.config.js                  ← テスト設定（既存テスト移植用）
```

### x402-agents/src/server.js 設計

ソース: [Express.js - Health Checks and Graceful Shutdown](https://expressjs.com/en/advanced/healthcheck-graceful-shutdown.html) / 核心の引用: 「it should stop accepting new requests, finish all the ongoing requests, clean up the resources it used, including database connections and file locks then exit.」

```
server.js の責務:
─────────────────────────────
0. 必須環境変数チェック: X402_WALLET_ADDRESS, OPENAI_API_KEY, DATABASE_URL
   → 欠落時は console.error + process.exit(1)
1. Express app 作成
2. app.set('trust proxy', 1) — Railway リバースプロキシ配下で正しいクライアントIP取得
3. CORS 設定（origin: '*', credentials: false, methods: ['GET','POST'], allowedHeaders: ['Content-Type','Authorization','X-Payment-*']）
   理由: x402 は payment が認証。ブラウザ Cookie は使わない
4. Rate limiting: express-rate-limit 30 req/min（既存 API と同じ設定を移植）
   keyGenerator: req.ip（trust proxy により正しい IP）
5. /health エンドポイント（DB 接続確認付き: prisma.$queryRaw`SELECT 1` → 200 / 503）
6. x402 手動初期化: x402ResourceServer + ExactEvmScheme + HTTPFacilitatorClient
   → server.initialize() を try-catch で囲む
   → 【fail-closed】初期化失敗時は isX402Ready = false フラグを設定
   → paymentMiddleware の前にガードミドルウェア: !isX402Ready → 503 "Service Unavailable"
7. paymentMiddleware で全8ルートの課金設定を一括登録（isX402Ready = true の場合のみ有効）
8. 各ルートをマウント（/emotion-detector, /buddhist-counsel, 等）
9. SIGTERM ハンドラ（graceful shutdown）
   → server.close() → prisma.$disconnect() → process.exit(0)
10. ポート: process.env.PORT || 3001
```

### Railway 設定

| 項目 | Service 1: API（既存） | Service 2: x402-agents（新規） |
|------|----------------------|------------------------------|
| Root Directory | `apps/api/` | `apps/x402-agents/` |
| Watch Paths | `apps/api/**` | `apps/x402-agents/**` |
| Start Command | `prisma migrate deploy && prisma generate && node src/server.js` | `npx prisma generate && node src/server.js` |
| 環境変数（削除） | `CDP_API_KEY_ID`, `CDP_API_KEY_SECRET` を削除 | — |
| 環境変数（設定） | 既存のまま | 下記テーブル |
| ドメイン | `anicca-proxy-production.up.railway.app` | Railway 自動生成 |

**x402-agents 環境変数:**

| 変数名 | 値 | 用途 |
|--------|-----|------|
| `CDP_API_KEY_ID` | 既存と同じ | x402 CDP 認証 |
| `CDP_API_KEY_SECRET` | 既存 PEM 秘密鍵 | x402 CDP 認証 |
| `X402_WALLET_ADDRESS` | 既存と同じ | x402 支払い先 |
| `X402_NETWORK` | `eip155:8453` | Base Mainnet |
| `OPENAI_API_KEY` | 既存と同じ | GPT-4o 呼び出し |
| `DATABASE_URL` | 既存と同じ PostgreSQL URL（`?connection_limit=5` 付き） | agentAuditLog 書き込み |
| `PORT` | Railway 自動設定 | Express ポート |

### railway.toml（x402-agents）

ソース: [Railway Docs - Monorepo](https://docs.railway.com/guides/monorepo) / 核心の引用: 「The Railway Config File does not follow the Root Directory path. You have to specify the absolute path.」

```toml
[build]
builder = "nixpacks"
watchPatterns = ["apps/x402-agents/**"]

[deploy]
startCommand = "npx prisma generate && node src/server.js"
healthcheckPath = "/health"
healthcheckTimeout = 10
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

### DB 接続管理（共有 PostgreSQL）

ソース: [Render - Connecting Multiple Services to Shared DB](https://render.com/articles/connecting-multiple-services-to-a-shared-database) / 核心の引用: 「Total Service Pools <= Database Connection Limit - Reserved Connections (approx. 3)」

```
接続プール設計
─────────────────────────────
Railway PostgreSQL 接続上限: 100（8GB 未満インスタンス）
  → API サービス: connection_limit=10（Prisma デフォルト）
  → x402-agents: connection_limit=5（トラフィック少）
  → 合計: 15 / 100 = 余裕あり
```

```
マイグレーション管理
─────────────────────────────
所有者: apps/api/ が唯一のマイグレーション管理者
x402-agents: マイグレーション実行しない（npx prisma generate のみ）
理由: 2サービスが migrate deploy を競合実行すると壊れる
```

```
schema.prisma 同期
─────────────────────────────
現時点: apps/api/prisma/schema.prisma からコピーで運用
将来: CI で diff 検知を検討（スコープ外）
マイグレーション追加時: apps/api で migrate → x402-agents の schema.prisma を手動コピー
```

### x402-agents の package.json 依存関係

```
既存 API から移動する依存:
─────────────────────────────
@coinbase/x402        → x402-agents へ（移動）
@x402/evm             → x402-agents へ（移動）
@x402/express         → x402-agents へ（移動）
@x402/extensions      → x402-agents へ（移動）
ethers                → x402-agents へ（移動）

新規追加（既存 API にはなかったもの）:
─────────────────────────────
@x402/core            → dependencies に明示追加（@x402/express の peer dep だが npm 挙動差を防ぐため明示）

既存 API から削除:
─────────────────────────────
@coinbase/x402, @x402/evm, @x402/express, @x402/extensions, ethers

x402-agents の dependencies（完全リスト）:
─────────────────────────────
express, cors, express-rate-limit, zod,
openai, @prisma/client, prisma,
@coinbase/x402, @x402/core, @x402/evm, @x402/express, @x402/extensions, ethers,
dotenv

x402-agents の devDependencies:
─────────────────────────────
vitest, vitest-mock-extended, supertest

実装時の検証: npm ls @x402/core で依存解決を確認する
```

### 修正2: iOS 側の API タイムアウト短縮

**As-Is:**

| ファイル | 現状 |
|---------|------|
| `NetworkSessionManager.swift:19` | `config.httpMaximumConnectionsPerHost = 1` |
| `NetworkSessionManager.swift:20` | `config.timeoutIntervalForRequest = 30.0` |
| `NetworkSessionManager.swift:21` | `config.timeoutIntervalForResource = 30.0` |

**To-Be:**

| ファイル | 変更後 | 理由 |
|---------|--------|------|
| `NetworkSessionManager.swift:19` | `config.httpMaximumConnectionsPerHost = 4` | 並列リクエスト許可 |
| `NetworkSessionManager.swift:20` | `config.timeoutIntervalForRequest = 8.0` | 障害時の早期フォールバック |
| `NetworkSessionManager.swift:21` | `config.timeoutIntervalForResource = 30.0` | リソース全体は据え置き |

---

## 4. テストマトリックス

| # | To-Be | テスト名 | カバー |
|---|-------|----------|--------|
| 1 | x402-agents が独立して起動する | `curl /health` on x402-agents → 200 | OK |
| 2 | 全8エンドポイントが x402 課金ゲート付きで動く | 各 `curl -X POST /<endpoint>` → 402 | OK |
| 3 | 既存 API から x402 ルートが消えている | `curl /api/x402/emotion-detector` → 404 | OK |
| 4 | 既存 API の `/health` が 200 | `curl /health` → 200 | OK |
| 5 | 通知送信ジョブが動作する | Railway ログで `problemNudgeApnsSender` 確認 | OK |
| 6 | x402-agents 停止時に既存 API に影響なし | x402-agents 停止 → API `/health` 200 | OK |
| 7 | iOS タイムアウトが 8秒に短縮されている | `test_requestTimeoutIs8Seconds()` | OK |
| 8 | iOS 接続数が 4 に増加している | `test_maxConnectionsPerHostIs4()` | OK |
| 9 | 実機起動が 10秒以内 | 実機 Cold start 計測 <= 10秒 | OK |
| 10 | x402-agents が SIGTERM で graceful shutdown | Railway ログ確認 | OK |
| 11 | 既存 API の package.json から x402 依存が消えている | `grep @x402 apps/api/package.json` → 0件 | OK |
| 12 | x402-agents に rate limiting が動作する | 31回連続リクエスト → 429 | OK |
| 13 | 既存テストが移動後も GREEN | `cd apps/x402-agents && npm test` → all pass | OK |
| 14 | prompt-sanitizer の network がハードコード維持 | テストで network = 'eip155:8453' を検証 | OK |
| 15 | @x402/core が正しく解決される | `npm ls @x402/core` → resolved | OK |
| 16 | x402 初期化失敗時に全ルートが 503（fail-closed） | CDP 鍵無効化 → POST → 503 | OK |
| 17 | 必須環境変数欠落時にプロセス起動失敗 | `X402_WALLET_ADDRESS` 未設定 → exit(1) | OK |
| 18 | /health が DB 接続を検証する | DB URL 無効化 → `/health` → 503 | OK |
| 19 | trust proxy でクライアント IP が正しく取得される | X-Forwarded-For ヘッダ付きリクエスト → 正しい IP でレート制限 | OK |

---

## 5. 境界

### やること

| やること |
|---------|
| `apps/x402-agents/` を新規作成（Express + x402 + rate limit + CORS + Prisma + 8ルート + graceful shutdown） |
| `apps/x402-agents/railway.toml` を作成（healthcheck + restart policy + watchPatterns） |
| `apps/x402-agents/src/routes/__tests__/` を作成（既存テスト移動） |
| `apps/api/src/routes/x402/` を削除（全8ルート + index.js） |
| `apps/api/src/routes/x402/__tests__/` を削除 |
| `apps/api/src/services/buddhistCounselService.js` を削除 |
| `apps/api/src/routes/index.js` から x402Router のマウントを削除（L34, L70-71） |
| `apps/api/package.json` から x402 関連依存を削除 |
| Railway に新サービス「x402-agents」を追加（**コード push 前に作成**） |
| 新サービスに環境変数を設定 |
| 既存 API から CDP 関連の環境変数を削除 |
| iOS の `NetworkSessionManager` を修正（接続数 + タイムアウト） |

### やらないこと

| やらないこと | 理由 |
|-------------|------|
| DB スキーマ変更 | 同じ PostgreSQL を共有。agentAuditLog テーブルは既存 |
| Prisma migration | x402-agents は `prisma generate` のみ。migration は既存 API 側が所有 |
| x402 のビジネスロジック変更 | 移動するだけ。ロジックは変えない |
| 各ルートファイルのロジック変更 | 移動するだけ（import パスのみ修正） |
| prompt-sanitizer の network ハードコード修正 | 意図的設計（Base Mainnet 専用）。そのまま移植 |
| PgBouncer 導入 | 現時点で接続数は余裕あり（15/100） |
| API Gateway / Facade | x402-agents は独立ドメイン。プロキシ不要 |
| x402 初期化ロジックの変更 | 既存の手動初期化 + try-catch パターンをそのまま移植 |
| schema.prisma 同期の自動化 | 現時点ではコピーで運用。将来 CI で diff 検知を検討 |
| `/api/x402/*` の Facade/redirect 期間 | x402 は外部AIエージェント専用API。iOS アプリは呼ばない。クライアント互換不要 |

### 触るファイル

| ファイル | 変更 |
|---------|------|
| `apps/x402-agents/` 全体 | 新規作成 |
| `apps/api/src/routes/x402/` | 削除（全9ファイル: index.js + 8ルート） |
| `apps/api/src/routes/x402/__tests__/` | 削除（x402-agents に移動） |
| `apps/api/src/services/buddhistCounselService.js` | 削除 |
| `apps/api/src/routes/index.js` | x402Router のマウント削除（L34, L70-71） |
| `apps/api/package.json` | x402 関連依存の削除 |
| `aniccaios/aniccaios/Services/NetworkSessionManager.swift` | 2行変更 |

### 触らないファイル

| ファイル | 理由 |
|---------|------|
| `apps/api/src/server.js` | 変更不要 |
| `apps/api/prisma/` | 変更不要（schema は x402-agents にコピーするだけ） |
| iOS の他のファイル | スコープ外 |

---

## 6. 実行手順

```
Step 1:  Railway に新サービス「x402-agents」を作成（コード push 前に作成してダウンタイム防止）
         - railway service create x402-agents
         - Root Directory: apps/x402-agents/
         - 環境変数設定（railway variables --set）
         ※ コードがまだないためデプロイは起きない

Step 2:  apps/x402-agents/ を作成
         - package.json（全依存 + devDependencies）
         - prisma/schema.prisma（apps/api/prisma/ からコピー）
         - src/lib/prisma.js（connection_limit=5 付き）
         - src/services/buddhistCounselService.js（apps/api から移動）
         - src/routes/ 全8ファイル（apps/api から移動、import パス修正）
         - src/routes/__tests__/（apps/api から移動、import パス修正）
         - src/server.js（Express + CORS + rate limit + x402 初期化 + paymentMiddleware + 8ルートマウント + /health + graceful shutdown）
         - railway.toml（healthcheck + restart policy + watchPatterns）
         - vitest.config.js

Step 3:  npm ls @x402/core で依存解決を確認

Step 4:  cd apps/x402-agents && npm test（移動後のテストが GREEN）

Step 5:  apps/api から x402 を完全削除
         - src/routes/x402/ ディレクトリ削除（__tests__/ 含む）
         - src/services/buddhistCounselService.js 削除
         - src/routes/index.js から x402Router のマウント削除
         - package.json から @coinbase/x402, @x402/evm, @x402/express, @x402/extensions, ethers を削除

Step 6:  dev に commit & push
         → 両サービスが同時にデプロイされる（Railway auto-deploy）

Step 7:  既存 API の環境変数から CDP_API_KEY_ID, CDP_API_KEY_SECRET を削除

Step 8:  両サービスのデプロイ確認
         - x402-agents: /health → 200, payment middleware active ログ確認, 31回 → 429
         - 既存 API: /health → 200, /api/x402/* → 404

Step 9:  iOS の NetworkSessionManager を修正（接続数 + タイムアウト）

Step 10: fastlane test

Step 11: main に push → Production デプロイ

Step 12: 動作確認（AC-1 〜 AC-15）
```

---

## E2E 判定

| 項目 | 値 |
|------|-----|
| UI 変更 | なし |
| 新画面 | なし |
| 新ボタン/操作 | なし |
| 結論 | Maestro E2E: **不要**（バックエンド分離 + タイムアウト変更のみ。curl + 実機起動計測で確認） |

---

## ユーザー作業

**なし。** 全て Claude が実行する。Railway 環境変数の設定も CLI で行う。

---

*作成: 2026-02-28*
*v2: 2026-02-28（ベストプラクティス深掘り: 10ソース引用追加）*
*v3: 2026-03-05（コード現状反映: 全8ルート対応、x402初期化ロジック修正、iOS設定値修正）*
*v4: 2026-03-05（レビュー反映: rate limit + CORS追加、@x402/core明示的依存、prompt-sanitizer networkハードコード決定、デプロイ順序修正、テスト移動追記、watchPatterns追加、schema同期方針追記）*
*v5: 2026-03-05（Codex レビュー反映: fail-closed設計、trust proxy追加、必須env チェック、health DBチェック、CORS詳細化、クライアント互換不要の根拠明記）*
*根拠: Strangler Fig Pattern (AWS/Azure/microservices.io) + Railway Monorepo Guide + Express.js Graceful Shutdown + Prisma Multi-Service BP*
