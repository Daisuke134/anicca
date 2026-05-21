import logger from '../../utils/logger.js';
import { BILLING_CONFIG } from '../../config/environment.js';
import { fetchCustomerEntitlements } from './api.js';
import { fetchSubscriptionRow, normalizePlanForResponse, getEntitlementState, ENTITLEMENT_SOURCE } from '../subscriptionStore.js';
import { query } from '../../lib/db.js';

const RC_EVENTS = new Set([
  'INITIAL_PURCHASE', 'RENEWAL', 'UNCANCELLATION',
  'BILLING_ISSUE', 'CANCELLATION', 'EXPIRATION', 'PRODUCT_CHANGE'
]);

function buildSubscriptionMetadata({ revenuecatAppUserId, deviceId } = {}) {
  const metadata = {};
  if (revenuecatAppUserId) metadata.revenuecat_app_user_id = String(revenuecatAppUserId);
  if (deviceId) metadata.device_id = String(deviceId);
  return metadata;
}

async function findProfileIdByRevenueCatAppUserId(revenuecatAppUserId) {
  const raw = String(revenuecatAppUserId || '').trim();
  if (!raw) return null;
  try {
    const r = await query(
      `select user_id
         from user_subscriptions
        where metadata->>'revenuecat_app_user_id' = $1
        order by updated_at desc
        limit 1`,
      [raw]
    );
    return r.rows?.[0]?.user_id ? String(r.rows[0].user_id) : null;
  } catch (e) {
    logger.warn('[RevenueCat] Failed to resolve profileId from user_subscriptions.metadata', { error: e?.message || String(e) });
    return null;
  }
}

export async function applyRevenueCatEntitlement(userId, entitlements, { revenuecatAppUserId, deviceId } = {}) {
  const metadata = buildSubscriptionMetadata({ revenuecatAppUserId, deviceId });
  const metadataJson = JSON.stringify(metadata || {});
  // 設定されたEntitlement IDを確実に指定 (entlb820c43ab7)
  const targetId = BILLING_CONFIG.REVENUECAT_ENTITLEMENT_ID;
  const entitlement = entitlements[targetId];
  
  // 指定IDのEntitlementがあり、かつ有効か？
  if (!entitlement || !entitlement.is_active) {
    logger.info('[RevenueCat] No active entitlement found for target ID', { 
      userId, 
      targetId,
      availableIds: Object.keys(entitlements),
      hasEntitlement: !!entitlement,
      isActive: entitlement?.is_active
    });
    
    // Freeプラン適用
    const payload = {
      user_id: userId,
      plan: 'free',
      status: 'free',
      current_period_end: null,
      entitlement_source: ENTITLEMENT_SOURCE.REVENUECAT,
      revenuecat_entitlement_id: targetId,
      revenuecat_original_transaction_id: null, // V2 APIでは取得不可
      entitlement_payload: entitlement ? JSON.stringify(entitlement) : null,
      metadata: metadataJson,
      updated_at: new Date().toISOString()
    };
    
    await query(
      `insert into user_subscriptions
       (user_id, plan, status, current_period_end, entitlement_source, revenuecat_entitlement_id, revenuecat_original_transaction_id, entitlement_payload, metadata, updated_at)
       values ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb, timezone('utc', now()))
       on conflict (user_id)
       do update set
         plan=excluded.plan,
         status=excluded.status,
         current_period_end=excluded.current_period_end,
         entitlement_source=excluded.entitlement_source,
         revenuecat_entitlement_id=excluded.revenuecat_entitlement_id,
         revenuecat_original_transaction_id=excluded.revenuecat_original_transaction_id,
         entitlement_payload=excluded.entitlement_payload,
         metadata = coalesce(user_subscriptions.metadata, '{}'::jsonb) || excluded.metadata,
         updated_at=excluded.updated_at`,
      [
        payload.user_id, payload.plan, payload.status, payload.current_period_end,
        payload.entitlement_source, payload.revenuecat_entitlement_id, payload.revenuecat_original_transaction_id, payload.entitlement_payload,
        payload.metadata
      ]
    );
    
    logger.info('[RevenueCat] Entitlement applied successfully (free)', { userId, plan: payload.plan });
    return;
  }
  
  // 有効なEntitlementが見つかった場合
  const expiresDate = entitlement.expires_at 
    ? new Date(entitlement.expires_at) // ミリ秒単位のタイムスタンプをDateに変換
    : null;
  
  const now = new Date();
  const isExpired = expiresDate != null && expiresDate <= now;
  const isActive = entitlement.is_active && !isExpired;
  
  // 注意: V2 APIのCustomerEntitlementにはperiod_typeが存在しないため、trial判定は不可
  // 必要に応じて別エンドポイント（subscriptions）から取得
  const status = isActive ? 'active' : 'expired';
  
  const payload = {
    user_id: userId,
    plan: isActive ? 'pro' : 'free',
    status,
    current_period_end: expiresDate ? expiresDate.toISOString() : null,
    entitlement_source: ENTITLEMENT_SOURCE.REVENUECAT,
    revenuecat_entitlement_id: targetId,
    revenuecat_original_transaction_id: null, // V2 APIでは取得不可（別エンドポイント必要）
    entitlement_payload: JSON.stringify(entitlement),
    metadata: metadataJson,
    updated_at: new Date().toISOString()
  };
  
  logger.info('[RevenueCat] Applying entitlement', { 
    userId, 
    plan: payload.plan, 
    status: payload.status,
    expiresDate: payload.current_period_end,
    isActive,
    isExpired,
    expiresAt: entitlement.expires_at
  });
  
  await query(
    `insert into user_subscriptions
     (user_id, plan, status, current_period_end, entitlement_source, revenuecat_entitlement_id, revenuecat_original_transaction_id, entitlement_payload, metadata, updated_at)
     values ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb, timezone('utc', now()))
     on conflict (user_id)
     do update set
       plan=excluded.plan,
       status=excluded.status,
       current_period_end=excluded.current_period_end,
       entitlement_source=excluded.entitlement_source,
       revenuecat_entitlement_id=excluded.revenuecat_entitlement_id,
       revenuecat_original_transaction_id=excluded.revenuecat_original_transaction_id,
       entitlement_payload=excluded.entitlement_payload,
       metadata = coalesce(user_subscriptions.metadata, '{}'::jsonb) || excluded.metadata,
       updated_at=excluded.updated_at`,
    [
      payload.user_id, payload.plan, payload.status, payload.current_period_end,
      payload.entitlement_source, payload.revenuecat_entitlement_id, payload.revenuecat_original_transaction_id, payload.entitlement_payload,
      payload.metadata
    ]
  );
  
  logger.info('[RevenueCat] Entitlement applied successfully', { userId, plan: payload.plan, status: payload.status });
}

export async function processRevenueCatEvent(event) {
  const type = event?.event;
  if (!RC_EVENTS.has(type)) return;
  const appUserId = event?.app_user_id;
  if (!appUserId) return;
  // Webhook payload only has RevenueCat app_user_id; map it to Anicca profileId(UUID) via user_subscriptions.metadata.
  // If mapping not found yet, fall back to appUserId (will not affect APNs sender until mapping exists).
  const mappedProfileId = await findProfileIdByRevenueCatAppUserId(appUserId);
  const userIdForStore = mappedProfileId || appUserId;
  const entitlements = await fetchCustomerEntitlements(appUserId);
  await applyRevenueCatEntitlement(userIdForStore, entitlements, { revenuecatAppUserId: appUserId });
  logger.info('RevenueCat entitlement updated', { appUserId, mappedProfileId, type });
}

export { normalizePlanForResponse, getEntitlementState };

