// Node.js 20+ native fetch (no node-fetch needed)
import { BILLING_CONFIG } from '../../config/environment.js';
import logger from '../../utils/logger.js';

// V2 APIを使用（PROJECT_ID必須）
const BASE_URL = 'https://api.revenuecat.com/v2';
const PROJECT_ID = BILLING_CONFIG.REVENUECAT_PROJECT_ID;

function parseActiveEntitlements(json) {
  // 専用エンドポイントのレスポンス形式: { object: "list", items: [...] }
  // CustomerEntitlementスキーマ: { object: "customer.active_entitlement", entitlement_id: string, expires_at: integer (ms) }
  if (json?.object === 'list' && Array.isArray(json.items)) {
    const result = {};
    const now = Date.now(); // ミリ秒単位の現在時刻
    
    logger.debug('[RevenueCat] Parsing active entitlements', { 
      itemsCount: json.items.length,
      firstItem: json.items[0] // デバッグ用
    });
    
    for (const item of json.items) {
      // entitlement_id が必須
      if (!item.entitlement_id) {
        logger.warn('[RevenueCat] Invalid entitlement item: missing entitlement_id', { item });
        continue;
      }
      
      // object フィールドのチェック（存在する場合のみ）
      if (item.object && item.object !== 'customer.active_entitlement') {
        logger.warn('[RevenueCat] Unexpected object type', { 
          expected: 'customer.active_entitlement',
          actual: item.object,
          entitlement_id: item.entitlement_id
        });
        // 警告のみで続行
      }
      
      const entitlementId = item.entitlement_id;
      const expiresAt = item.expires_at; // ミリ秒単位のタイムスタンプ（nullable）
      
      // 専用エンドポイントは「アクティブな」エンタイトルメントのみを返すため、
      // expires_at が現在時刻より後であることを確認（念のため）
      const isActive = expiresAt == null || expiresAt > now;
      
      result[entitlementId] = {
        entitlement_id: entitlementId,
        is_active: isActive,
        expires_at: expiresAt,
        expires_date: expiresAt ? new Date(expiresAt).toISOString() : null,
      };
    }
    
    logger.info('[RevenueCat] Parsed active entitlements', { 
      count: Object.keys(result).length,
      entitlementIds: Object.keys(result)
    });
    return result;
  }
  
  logger.warn('[RevenueCat] Unexpected response format', { 
    object: json?.object,
    hasItems: !!json?.items,
    itemsCount: json?.items?.length ?? 0
  });
  return {};
}

export async function fetchCustomerEntitlements(appUserId) {
  const key = BILLING_CONFIG.REVENUECAT_REST_API_KEY;
  const projectId = BILLING_CONFIG.REVENUECAT_PROJECT_ID;
  
  if (!key || !projectId) {
    logger.error('[RevenueCat] Missing API Key or Project ID', { 
      hasKey: !!key, 
      hasProjectId: !!projectId 
    });
    return {};
  }
  
  // 修正: 専用の active_entitlements エンドポイントを使用
  // GET /v2/projects/{project_id}/customers/{customer_id}/active_entitlements
  const url = `${BASE_URL}/projects/${projectId}/customers/${encodeURIComponent(appUserId)}/active_entitlements`;
  
  logger.info('[RevenueCat] Fetching active entitlements (V2)', { appUserId, url });
  
  try {
    const resp = await fetch(url, {
      headers: {
        Authorization: `Bearer ${key}`,
        Accept: 'application/json'
      }
    });
    
    if (!resp.ok) {
      const txt = await resp.text().catch(() => '');
      logger.warn('[RevenueCat] API error', { 
        status: resp.status, 
        appUserId, 
        error: txt 
      });
      // 404/403は未購読として扱う（エラーをthrowしない）
      if (resp.status === 403 || resp.status === 404) {
        return {};
      }
      throw new Error(`RevenueCat API error: ${resp.status} ${txt}`);
    }
    
    const json = await resp.json();
    logger.debug('[RevenueCat] API response (V2 active_entitlements)', { 
      appUserId, 
      object: json.object,
      itemsCount: json.items?.length ?? 0
    });
    
    // 専用エンドポイントのレスポンス形式: { object: "list", items: [...] }
    return parseActiveEntitlements(json);
    
  } catch (err) {
    logger.error('[RevenueCat] Network/Parse error', { 
      error: err.message, 
      appUserId 
    });
    return {};
  }
}

// Guideline 5.1.1(v)対応: アカウント削除時にRevenueCatのSubscriberを削除
export async function deleteSubscriber(appUserId) {
  const key = BILLING_CONFIG.REVENUECAT_REST_API_KEY;
  const projectId = BILLING_CONFIG.REVENUECAT_PROJECT_ID;
  
  if (!key || !projectId) {
    logger.error('[RevenueCat] Missing API Key or Project ID for subscriber deletion', { 
      hasKey: !!key, 
      hasProjectId: !!projectId 
    });
    throw new Error('Missing RevenueCat configuration');
  }
  
  // DELETE /v2/projects/{project_id}/customers/{customer_id}
  const url = `${BASE_URL}/projects/${projectId}/customers/${encodeURIComponent(appUserId)}`;
  
  logger.info('[RevenueCat] Deleting subscriber', { appUserId, url });
  
  try {
    const resp = await fetch(url, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${key}`,
        Accept: 'application/json'
      }
    });
    
    if (!resp.ok) {
      const txt = await resp.text().catch(() => '');
      // 404は既に削除済みとして扱う（エラーをthrowしない）
      if (resp.status === 404) {
        logger.info('[RevenueCat] Subscriber already deleted', { appUserId });
        return;
      }
      logger.warn('[RevenueCat] Failed to delete subscriber', { 
        status: resp.status, 
        appUserId, 
        error: txt 
      });
      throw new Error(`RevenueCat API error: ${resp.status} ${txt}`);
    }
    
    logger.info('[RevenueCat] Subscriber deleted successfully', { appUserId });
  } catch (err) {
    logger.error('[RevenueCat] Error deleting subscriber', { 
      error: err.message, 
      appUserId 
    });
    throw err;
  }
}


