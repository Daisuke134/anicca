import { query } from '../lib/db.js';

export const ENTITLEMENT_SOURCE = {
  REVENUECAT: 'revenuecat'
};

export async function fetchSubscriptionRow(userId) {
  const r = await query(
    'select * from user_subscriptions where user_id = $1 limit 1',
    [userId]
  );
  return r.rows[0] || null;
}

export async function ensureSubscriptionRow(userId) {
  const existing = await fetchSubscriptionRow(userId);
  if (existing) return existing;
  const r = await query(
    `insert into user_subscriptions (user_id, updated_at)
     values ($1, timezone('utc', now()))
     on conflict (user_id)
     do update set updated_at = excluded.updated_at
     returning *`,
    [userId]
  );
  return r.rows[0];
}

function normalizeStatus(provider, rawStatus) {
  if (provider === ENTITLEMENT_SOURCE.REVENUECAT) {
    switch (rawStatus) {
      case 'active':
      case 'renewal':
      case 'unlimited':
        return { plan: 'pro', status: rawStatus };
      case 'grace_period':
      case 'billing_issue':
        return { plan: 'grace', status: rawStatus };
      default:
        return { plan: 'free', status: rawStatus || 'expired' };
    }
  }
      return { plan: 'free', status: rawStatus || 'canceled' };
}

export async function getEntitlementState(userId) {
  const subscription = await fetchSubscriptionRow(userId);

  let statusInfo = normalizeStatus(
    subscription?.entitlement_source || ENTITLEMENT_SOURCE.REVENUECAT,
    subscription?.status
  );

  // RevenueCatのentitlement_payloadから直接isActiveを確認
  if (subscription?.entitlement_source === 'revenuecat') {
    let payload = subscription?.entitlement_payload;
    if (typeof payload === 'string') {
      try {
        payload = JSON.parse(payload);
      } catch (e) {
        payload = null;
      }
    }

    if (payload && typeof payload === 'object') {
      const isActive = payload.is_active === true;
      const expiresDate = payload.expires_date ? new Date(payload.expires_date) : null;
      const isExpired = expiresDate ? expiresDate <= new Date() : false;

      if (isActive && !isExpired) {
        statusInfo = {
          plan: 'pro',
          status: payload.period_type === 'trial' ? 'trialing' : 'active'
        };
      } else if (expiresDate && expiresDate > new Date()) {
        statusInfo = { plan: 'pro', status: 'grace_period' };
      } else {
        statusInfo = { plan: 'free', status: 'expired' };
      }
    } else if (
      subscription?.current_period_end &&
      new Date(subscription.current_period_end) > new Date() &&
      statusInfo.plan === 'free'
    ) {
      statusInfo = { ...statusInfo, plan: 'pro' };
    }
  }

  const currentPeriodEnd = subscription?.current_period_end || null;

  return {
    plan: statusInfo.plan,
    status: statusInfo.status,
    currentPeriodEnd
  };
}

export function normalizePlanForResponse(state) {
  return {
    plan: state.plan,
    status: state.status,
    current_period_end: state.currentPeriodEnd
  };
}
