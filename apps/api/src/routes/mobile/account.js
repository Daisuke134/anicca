import express from 'express';
import requireAuth from '../../middleware/requireAuth.js';
import { deleteSubscriber } from '../../services/revenuecat/api.js';
import { pool } from '../../lib/db.js';
import { revokeAllRefreshTokensForUser } from '../../services/auth/refreshService.js';

const router = express.Router();

// Guideline 5.1.1(v)対応: アカウント削除
router.delete('/', async (req, res, next) => {
  try {
    const authHeader = String(req.headers['authorization'] || '');
    let userId = null;
    
    if (authHeader.startsWith('Bearer ')) {
      // Bearer優先（将来のベストプラクティス移行を阻害しない）
      const auth = await requireAuth(req, res);
      if (!auth) return;
      userId = auth.sub;
    } else {
      // モバイル規約ヘッダー（device-id + user-id）を許容（即効の401解消）
      const deviceId = (req.get('device-id') || '').toString().trim();
      userId = (req.get('user-id') || '').toString().trim();
      if (!deviceId) {
        return res.status(400).json({ error: { code: 'INVALID_REQUEST', message: 'device-id is required' } });
      }
      if (!userId) {
        return res.status(401).json({ error: { code: 'UNAUTHORIZED', message: 'user-id is required' } });
      }
    }
    
    // すべてのリフレッシュトークンを失効
    try {
      await revokeAllRefreshTokensForUser(userId);
    } catch (e) {
      console.error('[Account Deletion] Failed to revoke refresh tokens for user', userId, e);
    }

    // RevenueCatのSubscriber削除（App User ID）
    try {
      await deleteSubscriber(userId);
    } catch (error) {
      // RevenueCat削除失敗はログに記録するが、処理は続行
      console.error(`[Account Deletion] Failed to delete RevenueCat subscriber for user ${userId}:`, error);
    }
    
    // アプリDBの削除（pg Poolでトランザクション）
    const client = await pool.connect();
    try {
      await client.query('BEGIN');
      // 関連データを削除（外部キー制約の順序に注意）
      await client.query('DELETE FROM user_subscriptions WHERE user_id = $1', [userId]);
      await client.query('DELETE FROM mobile_profiles WHERE user_id = $1', [userId]);
      // テーブル存在チェックの上で安全に削除
      const tableExists = async (name) => {
        const { rows } = await client.query('SELECT to_regclass($1) as reg', [`public.${name}`]);
        return Boolean(rows?.[0]?.reg);
      };
      if (await tableExists('tokens')) {
        await client.query('DELETE FROM tokens WHERE user_id = $1', [userId]);
      }
      // レガシーテーブルが残存している場合の安全な削除
      if (await tableExists('usage_sessions')) {
        await client.query('DELETE FROM usage_sessions WHERE user_id = $1', [userId]);
      }
      if (await tableExists('mobile_voip_tokens')) {
        await client.query('DELETE FROM mobile_voip_tokens WHERE user_id = $1', [userId]);
      }
      
      // profilesテーブルの削除: userIdがUUID形式かどうかを確認
      // UUID形式の場合は直接削除、そうでない場合はapple_user_idで検索
      const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
      if (uuidRegex.test(userId)) {
        // UUID形式の場合
        await client.query('DELETE FROM profiles WHERE id = $1::uuid', [userId]);
      } else {
        // Apple User IDの場合（metadataから検索）
        await client.query(`DELETE FROM profiles WHERE metadata->>'apple_user_id' = $1`, [userId]);
      }
      
      // user_settingsはON DELETE CASCADEで自動削除される
      await client.query('COMMIT');
    } catch (e) {
      await client.query('ROLLBACK');
      throw e;
    } finally {
      client.release();
    }
    
    return res.status(204).send();
  } catch (error) {
    console.error('[Account Deletion] Error:', error);
    next(error);
  }
});

export default router;

