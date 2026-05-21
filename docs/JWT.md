# JWT認証実装状況と移行計画（AT+RT・Keychain・RT回転）

## JWT認証（Bearerトークン）について

### ベストプラクティスかどうか

はい、JWT認証（Bearerトークン）はベストプラクティスです。理由:

- **標準的（RFC 6750）**: OAuth 2.0の標準的な認証方式
- **ステートレスでスケーラブル**: サーバー側でセッション管理が不要
- **トークンに情報を含められる**: ユーザーID、権限、有効期限などを含められる
- **有効期限管理が容易**: トークン内に有効期限を含められる
- **セキュリティが高い**: 署名検証により改ざんを防げる

## 現在の実装状況

### 実装済み

1. **JWT検証ミドルウェア（`requireAuth.js`）**
   - Bearerトークンの検証が実装済み
   - HS256署名の検証に対応
   - ただし、モバイルAPIではほとんど未使用

2. **JWT発行機能（`jwt.js`）**
   - JWT署名機能が実装済み
   - `/api/auth/entitlement`で使用（Supabase用）

### 未実装・不完全

1. **ログイン時のJWT発行**
   - `/api/auth/apple`は内部UUIDを返すのみ
   - JWTトークンを発行していない

2. **モバイルAPIエンドポイント**
   - `/api/mobile/realtime` → `device-id` + `user-id`を使用
   - `/api/mobile/profile` → `device-id` + `user-id`を使用
   - `/api/mobile/entitlement` → `device-id` + `user-id`を使用
   - `/api/mobile/account` → Bearerトークンと`device-id`/`user-id`の両方をサポート（後方互換）

3. **iOSアプリ側**
   - JWTトークンを受け取っていない
   - すべてのAPIリクエストで`device-id`と`user-id`ヘッダーを使用
   - Bearerトークンを送信していない

4. **セキュリティ機能**
   - トークンブラックリスト未実装（ログアウト・アカウント削除時の無効化不可）
   - トークンリフレッシュ機能未実装

### 課金関連

- RevenueCat Webhook: 独自の認証方式（RevenueCatの署名検証）
- モバイルからの課金関連API: `device-id`/`user-id`を使用（JWT未使用）

## 現状のまとめ

| エンドポイント | 認証方式 | 状態 |
|---|---|---|
| `/api/auth/apple` | Apple IDトークン検証 | JWT発行なし |
| `/api/mobile/realtime` | `device-id` + `user-id` | JWT未使用 |
| `/api/mobile/profile` | `device-id` + `user-id` | JWT未使用 |
| `/api/mobile/entitlement` | `device-id` + `user-id` | JWT未使用 |
| `/api/mobile/account` | Bearerトークン or `device-id`/`user-id` | 両方サポート（後方互換） |
| 課金関連API | `device-id` + `user-id` | JWT未使用 |

**結論**: モバイルAPIはほぼ`device-id`/`user-id`ヘッダー方式で、JWT認証は未使用です。`account.js`のみBearerトークンをサポートしていますが、iOSアプリは使用していません。

## 実装方法

### 1. ログイン時にAT/RTを発行

`/api/auth/apple` は Apple ID トークン検証後に、15分有効の **Access Token (AT)** と 30日有効の **Refresh Token (RT)** を発行します。RTはDBにハッシュで保存し、回転・再利用検知に対応します。

**重要な修正点**:
- 環境変数の存在チェック
- JWT発行時のエラーハンドリング
- JWT ID（jti）を含めてブラックリスト対応

```javascript
// apps/api/src/routes/auth/apple.js
import { signJwtHs256 } from '../../utils/jwt.js';
import crypto from 'crypto';
import baseLogger from '../../utils/logger.js';

const logger = baseLogger.withContext('AppleAuth');

router.post('/', async (req, res) => {
  try {
    // ... 既存の検証処理 ...
    
    const verifiedUser = await verifyIdentityToken(identity_token, nonce, user_id);
    
    if (!verifiedUser) {
      logger.warn('Apple token verification failed');
      return res.status(401).json({ error: 'token_verification_failed' });
    }
    
    // JWTトークンを発行
    const jwtSecret = process.env.PROXY_AUTH_JWT_SECRET;
    if (!jwtSecret) {
      logger.error('PROXY_AUTH_JWT_SECRET is not configured');
      // JWT発行失敗時も認証は成功しているので、トークンなしで返す（後方互換）
      return res.json({
        userId: verifiedUser.userId,
        appleUserId: verifiedUser.appleUserId,
        displayName: verifiedUser.displayName,
        email: verifiedUser.email
        // token と expiresAt は省略（後方互換）
      });
    }
    
    const now = Math.floor(Date.now() / 1000);
    const exp = now + (15 * 60); // 15分
    const jti = crypto.randomUUID(); // JWT ID（ブラックリスト用）
    
    const payload = {
      sub: verifiedUser.userId, // 内部UUID
      jti: jti, // JWT ID（ブラックリスト用）
      apple_user_id: verifiedUser.appleUserId,
      email: verifiedUser.email,
      display_name: verifiedUser.displayName,
      iat: now,
      exp: exp
    };
    
    const token = signJwtHs256(payload, jwtSecret);
    const rt = crypto.randomBytes(32).toString('base64url');
    await upsertRefreshToken({ userId: verifiedUser.userId, token: rt, deviceId: req.get('device-id')||'unknown', ttlDays: 30, userAgent: req.get('user-agent') });
    return res.json({ userId: verifiedUser.userId, token, expiresAt: exp * 1000, refreshToken: rt });
  } catch (error) {
    logger.error('Apple auth error', error);
    return res.status(500).json({ error: 'internal_error' });
  }
});
```

### 2. iOSアプリ側でAT/RTを保存・使用

`AuthCoordinator.swift`と`UserCredentials`を修正して、JWTトークンを受け取り、保存します。

**重要な修正点**:
- 後方互換性のためのオプショナルフィールド
- トークン有効期限チェックのロジック修正

```swift
// aniccaios/aniccaios/Models/UserProfile.swift
struct UserCredentials: Codable {
    let userId: String
    let displayName: String
    let email: String?
    var jwtAccessToken: String? // オプショナル（後方互換）
    var accessTokenExpiresAt: Date? // オプショナル（後方互換）
    
    // 後方互換性のためのカスタムデコーディング
    enum CodingKeys: String, CodingKey {
        case userId, displayName, email, jwtToken, tokenExpiresAt
    }
    
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        userId = try container.decode(String.self, forKey: .userId)
        displayName = try container.decode(String.self, forKey: .displayName)
        email = try container.decodeIfPresent(String.self, forKey: .email)
        jwtToken = try container.decodeIfPresent(String.self, forKey: .jwtToken)
        tokenExpiresAt = try container.decodeIfPresent(Date.self, forKey: .tokenExpiresAt)
    }
}
```

```swift
// aniccaios/aniccaios/Authentication/AuthCoordinator.swift
// verifyWithBackend内の修正
if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
   let backendUserId = json["userId"] as? String {
    
    let jwtToken = json["token"] as? String
    let expiresAt: Date? = (json["expiresAt"] as? TimeInterval).map { Date(timeIntervalSince1970: $0 / 1000) }
    let rt = json["refreshToken"] as? String
    if let rt = rt { try? KeychainService.save(Data(rt.utf8), account: "rt") }
    let credentials = UserCredentials(
        userId: backendUserId,
        displayName: displayName,
        email: email,
        jwtAccessToken: jwtToken,
        accessTokenExpiresAt: expiresAt
    )
    
    await MainActor.run {
        AppState.shared.updateUserCredentials(credentials)
    }
    
    logger.info("Sign in successful for user: \(backendUserId, privacy: .public)")
} else {
    logger.error("Invalid backend response format")
    await MainActor.run {
        AppState.shared.setAuthStatus(.signedOut)
    }
}
```

### 3. ネットワークリクエストでBearerトークンを使用（期限前に自動更新）

すべてのAPIリクエストでBearerトークンを使用するように修正します。

**重要な修正点**:
- トークン有効期限チェックのロジック修正（`?? Date() > Date()`は常にtrueになる問題を修正）
- 共通ヘルパー関数の追加

```swift
// aniccaios/aniccaios/Services/NetworkSessionManager.swift
extension NetworkSessionManager {
    /// 認証ヘッダーを設定するヘルパー関数
    @MainActor
    func setAuthHeaders(for request: inout URLRequest) throws {
        guard case .signedIn(let credentials) = AppState.shared.authStatus else {
            throw AuthError.notAuthenticated
        }
        
        if let exp = credentials.accessTokenExpiresAt, exp.addingTimeInterval(-60) <= Date() {
            try await refreshIfNeeded()
        }
        if let at = credentials.jwtAccessToken {
            request.setValue("Bearer \(at)", forHTTPHeaderField: "Authorization")
        }
    }
}

enum AuthError: Error {
    case notAuthenticated
}
```

**使用例**:
```swift
// 各APIリクエストで使用
var request = URLRequest(url: url)
request.httpMethod = "GET"
try NetworkSessionManager.shared.setAuthHeaders(for: &request)
let (data, response) = try await NetworkSessionManager.shared.session.data(for: request)
```

### 4. モバイルAPIエンドポイントでJWT認証を優先

各エンドポイントでJWT認証を優先し、Bearerトークンがない場合のみ`device-id`/`user-id`をフォールバックします。

**共通ヘルパー関数の作成**:
```javascript
// apps/api/src/middleware/extractUserId.js（新規作成）
import requireAuth from './requireAuth.js';
import baseLogger from '../utils/logger.js';

const logger = baseLogger.withContext('ExtractUserId');

/**
 * Bearerトークンまたはdevice-id/user-idヘッダーからuserIdを抽出
 * @param {express.Request} req
 * @param {express.Response} res
 * @returns {Promise<string|null>} userId or null (エラー時はresで応答済み)
 */
export default async function extractUserId(req, res) {
  const authHeader = String(req.headers['authorization'] || '');
  
  // Bearerトークンを優先
  if (authHeader.startsWith('Bearer ')) {
    const auth = await requireAuth(req, res);
    if (!auth) return null; // エラーはrequireAuthで返される
    return auth.sub;
  }
  
  // 後方互換: device-id/user-idを使用
  const deviceId = (req.get('device-id') || '').toString().trim();
  const userId = (req.get('user-id') || '').toString().trim();
  
  if (!deviceId) {
    logger.warn('Missing device-id header');
    res.status(400).json({ error: 'device-id is required' });
    return null;
  }
  
  if (!userId) {
    logger.warn('Missing user-id header');
    res.status(401).json({ error: 'user-id is required' });
    return null;
  }
  
  return userId;
}
```

**各エンドポイントでの使用例**:
```javascript
// apps/api/src/routes/mobile/realtime.js
import extractUserId from '../../middleware/extractUserId.js';

router.get('/session', async (req, res) => {
  const userId = await extractUserId(req, res);
  if (!userId) return; // エラーはextractUserIdで返される
  
  try {
    // 以降の処理はuserIdを使用
    const entitlement = await getEntitlementState(userId);
    // ...
  } catch (error) {
    logger.error('Failed to issue client_secret', error);
    return res.status(500).json({ error: 'failed_to_issue_client_secret' });
  }
});
```

### 5. Refresh Tokenストアと回転・再利用検知

**データベーステーブルの作成**:
```sql
-- docs/migrations/009_token_blacklist.sql（新規作成）
CREATE TABLE IF NOT EXISTS token_blacklist (
  token_id VARCHAR(255) PRIMARY KEY,
  expires_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_token_blacklist_expires_at ON token_blacklist(expires_at);

-- 期限切れトークンを自動削除するクリーンアップジョブ（オプション）
-- または、定期的にクリーンアップを実行
```

**トークンブラックリストサービスの実装**:
```javascript
// apps/api/src/services/tokenBlacklist.js（新規作成）
import { pool } from '../../lib/db.js';

/**
 * トークンをブラックリストに追加
 * @param {string} tokenId - JWTのjti（JWT ID）またはトークンのハッシュ
 * @param {number} expiresAt - トークンの有効期限（Unix timestamp）
 */
export async function blacklistToken(tokenId, expiresAt) {
  const client = await pool.connect();
  try {
    await client.query(
      'INSERT INTO token_blacklist (token_id, expires_at) VALUES ($1, to_timestamp($2)) ON CONFLICT DO NOTHING',
      [tokenId, expiresAt]
    );
  } finally {
    client.release();
  }
}

/**
 * トークンがブラックリストに含まれているかチェック
 * @param {string} tokenId - JWTのjtiまたはトークンのハッシュ
 */
export async function isTokenBlacklisted(tokenId) {
  const client = await pool.connect();
  try {
    const result = await client.query(
      'SELECT 1 FROM token_blacklist WHERE token_id = $1 AND expires_at > NOW()',
      [tokenId]
    );
    return result.rows.length > 0;
  } finally {
    client.release();
  }
}
```

**requireAuthでブラックリストをチェック**:
```javascript
// apps/api/src/middleware/requireAuth.js
import crypto from 'crypto';
import { isTokenBlacklisted } from '../services/tokenBlacklist.js';

// ... 既存のコード ...

export default async function requireAuth(req, res) {
  try {
    const auth = req.headers['authorization'] || '';
    if (!auth.startsWith('Bearer ')) {
      res.status(401).json({ error: 'Missing Authorization bearer' });
      return null;
    }
    const token = auth.slice('Bearer '.length).trim();

    const memberSecret = process.env.PROXY_AUTH_JWT_SECRET;
    const guestSecret = process.env.PROXY_GUEST_JWT_SECRET;

    let decoded = tryVerify(token, memberSecret);
    let tokenType = 'member';

    if (!decoded) {
      decoded = tryVerify(token, guestSecret);
      tokenType = decoded ? 'guest' : null;
    }

    if (!decoded || !tokenType) {
      console.warn('JWT verification failed: no matching secret');
      res.status(401).json({ error: 'Invalid token' });
      return null;
    }
    
    // ブラックリストチェック
    const tokenId = decoded.jti || crypto.createHash('sha256').update(token).digest('hex');
    if (await isTokenBlacklisted(tokenId)) {
      res.status(401).json({ error: 'Token has been revoked' });
      return null;
    }

    const sub = decoded?.sub || decoded?.uid || decoded?.user_id || decoded?.email || null;
    if (!sub) {
      res.status(401).json({ error: 'Token missing subject' });
      return null;
    }

    // ... 既存の処理 ...
  } catch (e) {
    console.warn('JWT verification failed:', e?.message || String(e));
    res.status(401).json({ error: 'Invalid token' });
    return null;
  }
}
```

### 6. ログアウト時のトークン無効化（RT失効・全端末オプション）

ログアウト時にトークンをブラックリストに追加します。

```javascript
// apps/api/src/routes/auth/logout.js（新規作成）
import express from 'express';
import requireAuth from '../../middleware/requireAuth.js';
import { blacklistToken } from '../../services/tokenBlacklist.js';
import crypto from 'crypto';

const router = express.Router();

router.post('/', async (req, res) => {
  try {
    const auth = await requireAuth(req, res);
    if (!auth) return; // エラーはrequireAuthで返される
    
    // トークンをブラックリストに追加
    const token = req.headers['authorization']?.slice('Bearer '.length).trim();
    if (token) {
      const tokenId = auth.raw?.jti || crypto.createHash('sha256').update(token).digest('hex');
      if (auth.raw?.exp) {
        await blacklistToken(tokenId, auth.raw.exp);
      }
    }
    
    return res.status(200).json({ message: 'Logged out successfully' });
  } catch (error) {
    console.error('[Logout] Error:', error);
    return res.status(500).json({ error: 'internal_error' });
  }
});

export default router;
```

**ルーターの登録**:
```javascript
// apps/api/src/routes/auth/index.js
import logoutRouter from './logout.js';
// ...
router.use('/logout', logoutRouter);
```

### 7. アカウント削除時のトークン無効化

アカウント削除時にトークンをブラックリストに追加します。

```javascript
// apps/api/src/routes/mobile/account.js
// 修正後
import crypto from 'crypto';
import { blacklistToken } from '../../services/tokenBlacklist.js';

router.delete('/', async (req, res, next) => {
  try {
    const authHeader = String(req.headers['authorization'] || '');
    let userId = null;
    let tokenId = null;
    
    if (authHeader.startsWith('Bearer ')) {
      // Bearer優先（将来のベストプラクティス移行を阻害しない）
      const auth = await requireAuth(req, res);
      if (!auth) return;
      userId = auth.sub;
      
      // トークンをブラックリストに追加
      const token = authHeader.slice('Bearer '.length).trim();
      tokenId = auth.raw?.jti || crypto.createHash('sha256').update(token).digest('hex');
      if (auth.raw?.exp) {
        await blacklistToken(tokenId, auth.raw.exp);
      }
    } else {
      // モバイル規約ヘッダー（device-id + user-id）を許容（即効の401解消）
      const deviceId = (req.get('device-id') || '').toString().trim();
      userId = (req.get('user-id') || '').toString().trim();
      if (!deviceId) {
        return res.status(400).json({ error: 'device-id is required' });
      }
      if (!userId) {
        return res.status(401).json({ error: 'user-id is required' });
      }
    }
    
    // 既存のアカウント削除処理...
    // RevenueCatのSubscriber削除
    // データベースの削除
    
    return res.status(204).send();
  } catch (error) {
    console.error('[Account Deletion] Error:', error);
    next(error);
  }
});
```

### 8. iOS側でのログアウト処理

iOS側でログアウト時にサーバーに通知します。

```swift
// aniccaios/aniccaios/Authentication/AuthCoordinator.swift
func signOut() {
    // サーバーにログアウトを通知（JWTトークンがある場合）
    Task {
        if case .signedIn(let credentials) = AppState.shared.authStatus,
           let jwtToken = credentials.jwtToken {
            await notifyLogout(jwtToken: jwtToken)
        }
    }
    
    AppState.shared.clearUserCredentials()
    AppState.shared.resetState()
}

private func notifyLogout(jwtToken: String) async {
    let url = AppConfig.proxyBaseURL.appendingPathComponent("auth/logout")
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("Bearer \(jwtToken)", forHTTPHeaderField: "Authorization")
    
    do {
        _ = try await NetworkSessionManager.shared.session.data(for: request)
    } catch {
        // ログアウト通知の失敗は無視（ローカルでクリア済み）
        logger.debug("Logout notification failed: \(error.localizedDescription, privacy: .public)")
    }
}
```

## 実装の優先順位（更新済み）

1. **フェーズ1**: ログイン時にJWTトークンを発行
2. **フェーズ2**: iOSアプリでJWTトークンを保存・使用
3. **フェーズ3**: モバイルAPIエンドポイントでJWT認証を優先（後方互換を維持）
4. **フェーズ4**: RTストア（回転・再利用検知）
5. **フェーズ5**: ログアウト・アカウント削除時のRT無効化
6. **フェーズ6**: `device-id`/`user-id`方式を段階的に廃止

この順序で進めると、既存の動作を維持しながらJWT認証へ移行し、完全にセキュアな認証システムを構築できます。

## セキュリティ考慮事項

### 完全にセキュアにするための要件

1. **トークンブラックリスト**: ログアウト・アカウント削除時にトークンを無効化
2. **トークンの有効期限**: 30日間（必要に応じて短縮可能）
3. **JWT ID（jti）**: トークンごとに一意のIDを付与してブラックリスト管理
4. **環境変数の管理**: Railwayで`PROXY_AUTH_JWT_SECRET`を設定（既に設定済み）
5. **iOS側の安全な保存**: 現状はUserDefaults、将来的にはKeychainへの移行を検討

### 注意事項

- **後方互換性の維持**: 既存の`device-id`/`user-id`方式もサポートし続けることで、段階的な移行が可能
- **エラーハンドリング**: トークンが無効な場合や有効期限切れの場合の適切なエラーハンドリングが必要
- **トークンの有効期限**: 30日間の有効期限を設定（必要に応じて調整可能）
- **セキュリティ**: JWTシークレットは環境変数で管理し、本番環境では強力なシークレットを使用（Railwayで設定済み）
- **ブラックリストのクリーンアップ**: 期限切れトークンは定期的に削除することを推奨

## 実装チェックリスト

### バックエンド
- [ ] `/api/auth/apple`でJWTトークンを発行
- [ ] 環境変数`PROXY_AUTH_JWT_SECRET`の存在チェック
- [ ] JWT発行時のエラーハンドリング
- [ ] JWT ID（jti）を含める
- [ ] `extractUserId`ミドルウェアの作成
- [ ] 各モバイルAPIエンドポイントで`extractUserId`を使用
- [ ] トークンブラックリストテーブルの作成
- [ ] `tokenBlacklist.js`サービスの実装
- [ ] `requireAuth`でブラックリストチェック
- [ ] `/api/auth/logout`エンドポイントの作成
- [ ] アカウント削除時のトークン無効化

### iOSアプリ
- [ ] `UserCredentials`に`jwtToken`と`tokenExpiresAt`を追加（後方互換対応）
- [ ] `AuthCoordinator`でJWTトークンを受け取り保存
- [ ] `NetworkSessionManager`に`setAuthHeaders`ヘルパーを追加
- [ ] すべてのAPIリクエストで`setAuthHeaders`を使用
- [ ] トークン有効期限チェックのロジック修正
- [ ] ログアウト時にサーバーに通知

### テスト
- [ ] JWTトークンの発行テスト
- [ ] JWTトークンの検証テスト
- [ ] ブラックリスト機能のテスト
- [ ] ログアウト時のトークン無効化テスト
- [ ] アカウント削除時のトークン無効化テスト
- [ ] 後方互換性のテスト（device-id/user-id方式）
