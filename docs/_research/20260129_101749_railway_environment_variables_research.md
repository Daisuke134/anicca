# Railway.app Environment Variables Best Practices Research

**調査日時**: 2026-01-29 10:17:49
**調査対象**: Railway.app環境変数のベストプラクティス、Node.js本番環境での環境変数検証戦略
**調査理由**: コンテナ起動時の環境変数未設定問題への対応方針決定

---

## 📊 調査結果サマリー

| 項目 | 推奨アプローチ |
|------|--------------|
| **必須環境変数が未設定の場合** | ✅ **Crash（process.exit(1)）** - Fail Fast原則 |
| **オプション環境変数が未設定の場合** | ✅ **Graceful Degradation（デフォルト値）** |
| **検証タイミング** | ✅ **アプリ起動時（最優先）** |
| **推奨ライブラリ** | ✅ Zod（TypeScript）/ Envalid / Joi |
| **RAILWAY_PUBLIC_DOMAIN** | ⚠️ **テンプレートデプロイ時に空になる既知の問題** |
| **内部通信** | ✅ **RAILWAY_PRIVATE_DOMAINを優先使用** |

---

## 1. Railway.app 環境変数ベストプラクティス

### 1.1 コア原則

| 原則 | 詳細 |
|------|------|
| **Private変数の優先使用** | サービス間通信には`RAILWAY_PRIVATE_DOMAIN`または`DATABASE_URL`を使用 |
| **Reference変数の活用** | 他サービスの変数を動的参照し、ハードコーディングを避ける |
| **Shared変数で重複削減** | プロジェクト・環境スコープの共有変数で管理を簡略化 |
| **Sealed変数で機密保護** | 機密データはSealed変数として、UI/API経由で値を非表示化 |
| **テンプレート構文** | `${{VARIABLE}}`構文で複雑な値を構築（例: `https://${{DOMAIN}}/${{PATH}}`） |

### 1.2 デプロイメントフロー

```
変数追加/更新/削除
    ↓
Staged Changes（レビュー待ち）
    ↓
Deploy実行
    ↓
コンテナ再起動
    ↓
新しい変数が利用可能
```

⚠️ **重要**: 変数変更は**手動デプロイが必須**。自動では反映されない。

### 1.3 .envファイルの自動検出

GitHubリポジトリ連携時、`.env`ファイルから環境変数を自動検出・提案する機能あり。ワンクリックでサービス変数に投入可能。

**ソース**:
- [Railway Best Practices](https://docs.railway.com/overview/best-practices)
- [Using Variables | Railway Docs](https://docs.railway.com/guides/variables)
- [Variables Reference | Railway Docs](https://docs.railway.com/reference/variables)

---

## 2. Node.js本番環境での環境変数検証戦略

### 2.1 業界コンセンサス: **Fail Fast原則**

> **「重要な環境変数が欠けている場合、アプリケーションは起動すべきではない」**

| 変数タイプ | 対応 | 理由 |
|-----------|------|------|
| **必須変数**（DATABASE_URL、API_KEY等） | ❌ **Crash & Exit** | データ漏洩・不正動作を防止 |
| **オプション変数**（ログレベル、Feature Flag等） | ✅ **デフォルト値で継続** | 運用の柔軟性 |

### 2.2 検証のベストプラクティス

#### ✅ すべきこと

```typescript
// ❌ ダメな例: 直接アクセス
const dbUrl = process.env.DATABASE_URL;

// ✅ 良い例: 起動時に検証
import { z } from 'zod';

const envSchema = z.object({
  DATABASE_URL: z.string().url(),
  PORT: z.coerce.number().default(3000),
  LOG_LEVEL: z.enum(['debug', 'info', 'warn', 'error']).default('info'),
  API_KEY: z.string().min(1),
});

// アプリ起動前に検証
const env = envSchema.parse(process.env);

// 失敗時は自動的にprocess.exit(1)相当のエラー
```

#### ❌ してはいけないこと

| アンチパターン | 問題 |
|--------------|------|
| `process.env.DATABASE_URL || 'default'` | 必須変数にデフォルト値を設定 |
| コード内で都度`process.env`アクセス | 検証タイミングが遅れる |
| 欠けている変数を無視 | ランタイムエラーで後から判明 |

### 2.3 推奨ライブラリ（2026年版）

| ライブラリ | 特徴 | 用途 |
|-----------|------|------|
| **Zod** | TypeScript型安全、スキーマ定義 | モダンTypeScriptプロジェクト |
| **Envalid** | シンプル、軽量、型推論 | 既存Node.jsプロジェクトへの導入 |
| **Joi** | 成熟、豊富なバリデーション | 複雑な検証ルールが必要な場合 |
| **env-schema** | Fastifyエコシステムに統合 | Fastify使用時 |

### 2.4 実装例（Zod）

```typescript
// config/env.ts
import { z } from 'zod';

const envSchema = z.object({
  // 必須: 未設定時はエラー
  DATABASE_URL: z.string().url('Invalid DATABASE_URL'),
  JWT_SECRET: z.string().min(32, 'JWT_SECRET must be at least 32 characters'),

  // 必須（型変換）
  PORT: z.coerce.number().int().positive().default(3000),

  // オプション: デフォルト値
  NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),
  LOG_LEVEL: z.enum(['debug', 'info', 'warn', 'error']).default('info'),

  // 条件付き: 本番環境では必須
  SENTRY_DSN: z.string().url().optional(),
});

// 起動時に検証（index.tsの最初の行）
export const env = envSchema.parse(process.env);

// 型推論が効く
type Env = z.infer<typeof envSchema>;
```

```typescript
// index.ts
import { env } from './config/env';

// この時点で全ての環境変数が検証済み
console.log(`Starting server on port ${env.PORT}`);
```

### 2.5 エラーハンドリング

```typescript
try {
  const env = envSchema.parse(process.env);
} catch (error) {
  if (error instanceof z.ZodError) {
    console.error('❌ Environment validation failed:');
    error.issues.forEach((issue) => {
      console.error(`  - ${issue.path.join('.')}: ${issue.message}`);
    });
    process.exit(1); // Crash Fast
  }
  throw error;
}
```

**出力例**:
```
❌ Environment validation failed:
  - DATABASE_URL: Required
  - JWT_SECRET: String must contain at least 32 character(s)
```

**ソース**:
- [How to Configure Node.js for Production with Environment Variables (2026-01-06)](https://oneuptime.com/blog/post/2026-01-06-nodejs-production-environment-variables/view)
- [Bulletproof Your Node.js Backend: Manage Environment Variables with Confidence](https://dev.to/vibhanshu909/bulletproof-your-nodejs-backend-manage-environment-variables-with-confidence-25j2)
- [Node.js Best Practices](https://github.com/goldbergyoni/nodebestpractices)

---

## 3. Crash vs Graceful Degradation: 判断基準

### 3.1 決定マトリックス

| 環境変数 | 未設定時の対応 | 理由 |
|---------|--------------|------|
| `DATABASE_URL` | ❌ **Crash** | DBなしでは動作不可 |
| `JWT_SECRET` | ❌ **Crash** | セキュリティリスク |
| `API_KEY`（外部サービス） | ❌ **Crash** | 機能が壊れる |
| `RAILWAY_PUBLIC_DOMAIN` | ⚠️ **条件付きCrash** | 外部公開必須なら必須 |
| `PORT` | ✅ **Default: 3000** | 標準的なデフォルト値 |
| `LOG_LEVEL` | ✅ **Default: info** | ログは補助機能 |
| `FEATURE_FLAG_XYZ` | ✅ **Default: false** | 段階的ロールアウト用 |

### 3.2 実装例

```typescript
const envSchema = z.object({
  // ❌ Crash対象
  DATABASE_URL: z.string().url(),
  JWT_SECRET: z.string().min(32),

  // ✅ Graceful Degradation
  PORT: z.coerce.number().default(3000),
  ENABLE_ANALYTICS: z.coerce.boolean().default(false),

  // ⚠️ 条件付きCrash（本番環境では必須）
  SENTRY_DSN: z.string().url().refine(
    (val) => process.env.NODE_ENV !== 'production' || val !== undefined,
    { message: 'SENTRY_DSN is required in production' }
  ).optional(),
});
```

**ソース**:
- [Node.js Environment Variables: Working with process.env (Configu)](https://configu.com/blog/node-js-environment-variables-working-with-process-env-and-dotenv/)
- [Checking for Environment Variables in a Node.js project](https://claytonerrington.com/blog/nodejs-environment-variable-checks/)

---

## 4. RAILWAY_PUBLIC_DOMAIN の扱い

### 4.1 変数の特性

| 項目 | 詳細 |
|------|------|
| **提供タイミング** | ビルド時 & ランタイムの両方 |
| **自動更新** | デプロイ・再デプロイ時に自動更新 |
| **スコープ** | サービス単位 |

### 4.2 既知の問題（⚠️ 重要）

**問題**: テンプレートからデプロイした場合、`RAILWAY_PUBLIC_DOMAIN`が**常に空**になる

**影響**:
- 初回デプロイ時にアプリが起動失敗する可能性
- ヘルスチェックが失敗する

**回避策**:
1. Public Networkingを一度削除
2. 再度有効化する
3. 変数が正しく設定される

**根本的な解決策**:
- `RAILWAY_PRIVATE_DOMAIN`を優先使用（内部通信用）
- 外部公開URLが必要な場合のみ`RAILWAY_PUBLIC_DOMAIN`を使用
- アプリ起動時に`RAILWAY_PUBLIC_DOMAIN`が空でもクラッシュしないようにする

### 4.3 推奨実装パターン

```typescript
const envSchema = z.object({
  // 内部通信用（常に利用可能）
  RAILWAY_PRIVATE_DOMAIN: z.string().optional(),

  // 外部公開用（オプション）
  RAILWAY_PUBLIC_DOMAIN: z.string().optional(),

  // フォールバック
  PUBLIC_URL: z.string().url().optional(),
});

const env = envSchema.parse(process.env);

// 優先順位: 明示的な設定 > RAILWAY_PUBLIC_DOMAIN > RAILWAY_PRIVATE_DOMAIN
export const publicUrl =
  env.PUBLIC_URL ||
  env.RAILWAY_PUBLIC_DOMAIN ||
  env.RAILWAY_PRIVATE_DOMAIN ||
  'http://localhost:3000';
```

### 4.4 デバッグ方法

```bash
# Railway CLIでデプロイ状態確認
railway status

# 環境変数を確認
railway variables

# ログで変数を確認
railway logs
```

**ソース**:
- [RAILWAY_PUBLIC_DOMAIN is always empty when deploying from a Template](https://station.railway.com/questions/railway-public-domain-is-always-empty-wh-ae6fd3af)
- [Public Domains | Railway Docs](https://docs.railway.com/reference/public-domains)
- [Public Networking | Railway Docs](https://docs.railway.com/guides/public-networking)

---

## 5. セキュリティ考慮事項

### 5.1 Sealed変数の使用

| 機密度 | 変数タイプ | 例 |
|-------|----------|-----|
| **高** | Sealed | JWT_SECRET, DATABASE_PASSWORD, API_KEY |
| **中** | 通常 | DATABASE_URL（URLに認証情報含む場合はSealed） |
| **低** | 通常 | PORT, LOG_LEVEL |

### 5.2 ログ出力時の注意

```typescript
// ❌ ダメ: 環境変数を直接ログ出力
console.log('Environment:', process.env);

// ✅ 良い: マスキング
const safeEnv = {
  DATABASE_URL: env.DATABASE_URL ? '***REDACTED***' : undefined,
  JWT_SECRET: '***REDACTED***',
  PORT: env.PORT,
};
console.log('Configuration:', safeEnv);
```

### 5.3 .envファイルの管理

| ファイル | 用途 | Git管理 |
|---------|------|---------|
| `.env` | ローカル開発 | ❌ `.gitignore` |
| `.env.example` | テンプレート | ✅ コミット |
| `.env.production` | 本番環境（非推奨） | ❌ 絶対NG |

**推奨フロー**:
```
ローカル: .env（git無視）
    ↓
Railway: Web UI or CLIで設定
    ↓
本番: Railway Variables（Sealed）
```

**ソース**:
- [Using Environment Variables in Node.js for App Configuration and Secrets](https://medium.com/dopplerhq/using-environment-variables-in-node-js-for-app-configuration-and-secrets-6fa1dd6c0fd7)

---

## 6. 実装推奨事項（Anicca API用）

### 6.1 即座に実装すべき対策

| 優先度 | 対策 | 期待効果 |
|--------|------|---------|
| **🔴 P0** | Zodで環境変数検証を追加 | 起動時エラーの早期検出 |
| **🔴 P0** | 必須変数が未設定時は`process.exit(1)` | デプロイ失敗の明確化 |
| **🟡 P1** | `RAILWAY_PUBLIC_DOMAIN`をオプション化 | テンプレートデプロイ対応 |
| **🟡 P1** | フォールバック順序の実装 | 起動時の柔軟性向上 |
| **🟢 P2** | 起動時にログで設定を出力（マスキング付き） | デバッグ効率化 |

### 6.2 実装例（apps/api/src/config/env.ts）

```typescript
import { z } from 'zod';

const envSchema = z.object({
  // 必須: Crash対象
  DATABASE_URL: z.string().url('DATABASE_URL must be a valid URL'),
  JWT_SECRET: z.string().min(32, 'JWT_SECRET must be at least 32 characters'),

  // 必須（型変換）
  PORT: z.coerce.number().int().positive().default(3000),

  // Railway変数（オプション: フォールバック対応）
  RAILWAY_PUBLIC_DOMAIN: z.string().optional(),
  RAILWAY_PRIVATE_DOMAIN: z.string().optional(),

  // オプション: Graceful Degradation
  NODE_ENV: z.enum(['development', 'staging', 'production']).default('development'),
  LOG_LEVEL: z.enum(['debug', 'info', 'warn', 'error']).default('info'),
});

function validateEnv() {
  try {
    const env = envSchema.parse(process.env);

    // 成功時: 安全な情報のみログ出力
    console.log('✅ Environment validation successful');
    console.log('   NODE_ENV:', env.NODE_ENV);
    console.log('   PORT:', env.PORT);
    console.log('   DATABASE_URL:', env.DATABASE_URL ? '***SET***' : '***MISSING***');
    console.log('   RAILWAY_PUBLIC_DOMAIN:', env.RAILWAY_PUBLIC_DOMAIN || '(not set)');

    return env;
  } catch (error) {
    if (error instanceof z.ZodError) {
      console.error('❌ Environment validation failed:');
      error.issues.forEach((issue) => {
        console.error(`   ${issue.path.join('.')}: ${issue.message}`);
      });
      process.exit(1); // Crash Fast
    }
    throw error;
  }
}

export const env = validateEnv();
export type Env = z.infer<typeof envSchema>;
```

```typescript
// apps/api/src/index.ts
import { env } from './config/env'; // 最初にインポート

const app = express();

// この時点で全ての環境変数が検証済み
const PORT = env.PORT;
const publicUrl = env.RAILWAY_PUBLIC_DOMAIN ||
                   env.RAILWAY_PRIVATE_DOMAIN ||
                   `http://localhost:${PORT}`;

console.log(`🚀 Server starting at ${publicUrl}`);

app.listen(PORT, () => {
  console.log(`✅ Server running on port ${PORT}`);
});
```

### 6.3 Railway設定の推奨

```toml
# railway.toml（オプション: Config as Code）
[deploy]
startCommand = "npm run start"
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3

[build]
builder = "NIXPACKS"
```

**ヘルスチェックエンドポイント**:
```typescript
// apps/api/src/routes/health.ts
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    env: env.NODE_ENV,
    // 機密情報は含めない
  });
});
```

---

## 7. テンプレートデプロイ時の対応フロー

### 7.1 初回デプロイ時（RAILWAY_PUBLIC_DOMAINが空の場合）

```
1. デプロイ実行
    ↓
2. コンテナ起動
    ↓
3. 環境変数検証
    ↓
4a. RAILWAY_PUBLIC_DOMAINが空 → ⚠️ 警告ログ出力（Crashしない）
4b. その他の必須変数が空 → ❌ Crash（process.exit(1)）
    ↓
5. アプリ起動
    ↓
6. Railway UIでPublic Networkingを削除→再追加
    ↓
7. 再デプロイ
    ↓
8. RAILWAY_PUBLIC_DOMAINが正しく設定される
```

### 7.2 実装例（条件付きCrash）

```typescript
const envSchema = z.object({
  RAILWAY_PUBLIC_DOMAIN: z.string().optional(),
  // ...
});

const env = envSchema.parse(process.env);

// テンプレートデプロイの既知の問題に対応
if (!env.RAILWAY_PUBLIC_DOMAIN) {
  console.warn('⚠️  RAILWAY_PUBLIC_DOMAIN is not set');
  console.warn('   This is expected on first deploy from template');
  console.warn('   Using fallback: RAILWAY_PRIVATE_DOMAIN or localhost');
}

// 必須の場合のみCrash
if (!env.RAILWAY_PUBLIC_DOMAIN && env.NODE_ENV === 'production') {
  console.error('❌ RAILWAY_PUBLIC_DOMAIN is required in production');
  process.exit(1);
}
```

---

## 8. まとめ: 最終推奨事項

### 8.1 実装チェックリスト

| # | タスク | 優先度 | 所要時間 |
|---|--------|--------|---------|
| 1 | Zodをインストール（`npm install zod`） | P0 | 1分 |
| 2 | `src/config/env.ts`を作成し、検証ロジックを実装 | P0 | 15分 |
| 3 | `index.ts`の最初で`env.ts`をインポート | P0 | 2分 |
| 4 | 必須変数リストを確認し、Zodスキーマに追加 | P0 | 10分 |
| 5 | `RAILWAY_PUBLIC_DOMAIN`をオプション化 | P1 | 5分 |
| 6 | ヘルスチェックエンドポイント追加 | P1 | 10分 |
| 7 | ログ出力のマスキング実装 | P2 | 5分 |
| 8 | `.env.example`ファイル作成 | P2 | 5分 |

**総所要時間**: 約1時間

### 8.2 ベストプラクティスまとめ

| 原則 | 実装方法 |
|------|---------|
| **Fail Fast** | 必須変数が未設定ならCrash（`process.exit(1)`） |
| **型安全** | Zodでスキーマ定義＆型推論 |
| **早期検証** | アプリ起動前に全変数を検証 |
| **明確なエラー** | Zodのエラーメッセージをそのままログ出力 |
| **柔軟性** | オプション変数にはデフォルト値 |
| **セキュリティ** | 機密情報はSealed変数＆ログマスキング |
| **Railway対応** | `RAILWAY_PRIVATE_DOMAIN`優先、`RAILWAY_PUBLIC_DOMAIN`はオプション |

---

## 📚 参考資料（全ソース）

### Railway公式ドキュメント
- [Best Practices | Railway Docs](https://docs.railway.com/overview/best-practices)
- [Using Variables | Railway Docs](https://docs.railway.com/guides/variables)
- [Variables Reference | Railway Docs](https://docs.railway.com/reference/variables)
- [Public Domains | Railway Docs](https://docs.railway.com/reference/public-domains)
- [Public Networking | Railway Docs](https://docs.railway.com/guides/public-networking)

### Node.js環境変数ベストプラクティス（2026年版）
- [How to Configure Node.js for Production with Environment Variables (2026-01-06)](https://oneuptime.com/blog/post/2026-01-06-nodejs-production-environment-variables/view)
- [Bulletproof Your Node.js Backend: Manage Environment Variables with Confidence](https://dev.to/vibhanshu909/bulletproof-your-nodejs-backend-manage-environment-variables-with-confidence-25j2)
- [Node.js Best Practices Repository](https://github.com/goldbergyoni/nodebestpractices)
- [Validating Environment Variables in Node.js | Medium](https://medium.com/@davidminaya04/validating-environment-variables-in-node-js-c1c917a45d66)

### ライブラリドキュメント
- [envalid - npm](https://www.npmjs.com/package/envalid)
- [Zod Official Documentation](https://zod.dev/)

### Railway既知の問題
- [RAILWAY_PUBLIC_DOMAIN is always empty when deploying from a Template](https://station.railway.com/questions/railway-public-domain-is-always-empty-wh-ae6fd3af)

---

**調査完了日時**: 2026-01-29
**次回レビュー推奨**: 環境変数追加時、Railway APIアップデート時
