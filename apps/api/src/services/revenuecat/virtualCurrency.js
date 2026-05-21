import { fetch } from 'undici';
import baseLogger from '../../utils/logger.js';

const logger = baseLogger.withContext('RCVirtualCurrency');
const PROJECT_ID = process.env.REVENUECAT_PROJECT_ID;
const API_KEY = process.env.REVENUECAT_REST_API_KEY;
export const VC_CURRENCY_CODE = process.env.REVENUECAT_VC_CODE || 'CREDIT';

function rcHeaders() {
  if (!PROJECT_ID || !API_KEY) {
    throw new Error('RevenueCat configuration missing');
  }
  return {
    Authorization: `Bearer ${API_KEY}`,
    'Content-Type': 'application/json'
  };
}

async function ensureCustomerExists(appUserId) {
  const url = `https://api.revenuecat.com/v2/projects/${PROJECT_ID}/customers`;
  const body = JSON.stringify({ id: appUserId });
  const res = await fetch(url, {
    method: 'POST',
    headers: rcHeaders(),
    body
  });

  if (res.status === 409) {
    return true;
  }
  if (!res.ok) {
    const detail = await res.text().catch(() => '');
    throw new Error(`RC create customer failed: ${res.status} ${detail}`);
  }
  return true;
}

/**
 * Get virtual currency balance for a user
 * @param {string} appUserId - RevenueCat app user ID
 * @param {string} currency - Currency code (defaults to VC_CURRENCY_CODE)
 * @returns {Promise<number>} Balance in minutes
 */
export async function getBalance(appUserId, currency = VC_CURRENCY_CODE) {
  const uid = encodeURIComponent(appUserId);
  const url = `https://api.revenuecat.com/v2/projects/${PROJECT_ID}/customers/${uid}/virtual_currencies`;
  
  const res = await fetch(url, { headers: rcHeaders() });
  
  if (!res.ok) {
    throw new Error(`RC balance failed: ${res.status}`);
  }
  
  const data = await res.json();
  const item = (data.items || []).find((i) => i.currency_code === currency);
  return Number(item?.balance ?? 0);
}

/**
 * Adjust virtual currency (internal helper)
 * @param {Object} params
 * @param {string} params.appUserId
 * @param {number} params.minutes - Positive for grant, negative for debit
 * @param {string} params.currency
 */
async function adjustMinutes({ appUserId, minutes, currency = VC_CURRENCY_CODE }, retryOnMissingCustomer = true) {
  const uid = encodeURIComponent(appUserId);
  const url = `https://api.revenuecat.com/v2/projects/${PROJECT_ID}/customers/${uid}/virtual_currencies/transactions`;
  
  const body = JSON.stringify({
    adjustments: {
      [currency]: minutes
    }
  });
  
  const res = await fetch(url, {
    method: 'POST',
    headers: rcHeaders(),
    body
  });
  
  if (!res.ok) {
    if (res.status === 404 && retryOnMissingCustomer) {
      await ensureCustomerExists(appUserId);
      return adjustMinutes({ appUserId, minutes, currency }, false);
    }
    const detail = await res.text().catch(() => '');
    throw new Error(`RC adjust failed: ${res.status} ${detail}`);
  }
  
  return true;
}

/**
 * Grant minutes (add credits)
 * @param {Object} params
 * @param {string} params.appUserId
 * @param {number} params.minutes
 * @param {string} params.currency
 * @param {Object} [params.context]
 */
export async function grantMinutes({ appUserId, minutes, currency, context }) {
  if (minutes <= 0) return true;
  
  logger.info('RC grant', {
    appUserId,
    minutes,
    currency: currency || VC_CURRENCY_CODE,
    context
  });
  
  return adjustMinutes({
    appUserId,
    minutes,
    currency: currency || VC_CURRENCY_CODE
  });
}

/**
 * Debit minutes (spend credits)
 * @param {Object} params
 * @param {string} params.appUserId
 * @param {number} params.minutes
 * @param {string} params.currency
 * @param {Object} [params.context]
 */
export async function debitMinutes({ appUserId, minutes, currency, context }) {
  if (minutes <= 0) return true;
  
  logger.info('RC debit', {
    appUserId,
    minutes,
    currency: currency || VC_CURRENCY_CODE,
    context
  });
  
  return adjustMinutes({
    appUserId,
    minutes: -Math.abs(minutes),
    currency: currency || VC_CURRENCY_CODE
  });
}

