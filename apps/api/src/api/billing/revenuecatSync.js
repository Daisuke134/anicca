import { fetchCustomerEntitlements } from '../../services/revenuecat/api.js';
import { applyRevenueCatEntitlement } from '../../services/revenuecat/webhookHandler.js';
import { getEntitlementState, normalizePlanForResponse } from '../../services/subscriptionStore.js';
import { ensureDeviceProfileId, resolveProfileId } from '../../services/mobile/userIdResolver.js';

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });
  // user-id header is RevenueCat "app_user_id" (anonymous id is OK).
  const appUserId = (req.auth?.sub || (req.get('user-id') || '').toString().trim());
  if (!appUserId) return res.status(401).json({ error: 'user-id required' });

  // We must write subscriptions keyed by profiles.id(UUID) because APNs sender calls getEntitlementState(profileId).
  // Resolve profileId from auth.sub (if present) or device-id.
  const deviceId = (req.get('device-id') || '').toString().trim();
  let profileId = null;
  try {
    if (req.auth?.sub) profileId = await resolveProfileId(req.auth.sub);
  } catch {
    profileId = null;
  }
  if (!profileId && deviceId) {
    profileId = await ensureDeviceProfileId(deviceId);
  }
  if (!profileId) return res.status(401).json({ error: 'device-id required' });
  
  try {
    const entitlements = await fetchCustomerEntitlements(appUserId);
    await applyRevenueCatEntitlement(profileId, entitlements, { revenuecatAppUserId: appUserId, deviceId });
    // 同期後に再度取得して確実に反映
    const state = await getEntitlementState(profileId);
    return res.json({ entitlement: normalizePlanForResponse(state) });
  } catch (error) {
    // エラー時も現在の状態を返す（フォールバック）
    const state = await getEntitlementState(profileId);
    return res.json({ entitlement: normalizePlanForResponse(state) });
  }
}

