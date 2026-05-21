import { processRevenueCatEvent } from '../../services/revenuecat/webhookHandler.js';
import logger from '../../utils/logger.js';
import { BILLING_CONFIG } from '../../config/environment.js';
import crypto from 'crypto';
import { query } from '../../lib/db.js';

export default async function webhookRevenueCat(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // RevenueCat webhook認証: AuthorizationヘッダーまたはX-RevenueCat-Webhook-Signatureヘッダーを確認
    const authHeader = req.headers['authorization'];
    const signatureHeader = req.headers['x-revenuecat-webhook-signature'];
    
    let secret = null;
    if (authHeader && authHeader.startsWith('Bearer ')) {
      secret = authHeader.replace('Bearer ', '');
    } else if (signatureHeader) {
      secret = signatureHeader;
    }

    if (!secret) {
      logger.warn('RevenueCat webhook: Missing authorization header');
      return res.status(401).json({ error: 'Unauthorized' });
    }

    if (BILLING_CONFIG.REVENUECAT_WEBHOOK_SECRET && secret !== BILLING_CONFIG.REVENUECAT_WEBHOOK_SECRET) {
      logger.warn('RevenueCat webhook: Invalid webhook secret');
      return res.status(401).json({ error: 'Unauthorized' });
    }

    // express.raw()でBufferとして受け取っているので、JSONにパース
    let event;
    let rawBodyString = null;
    if (Buffer.isBuffer(req.body)) {
      const bodyString = req.body.toString('utf8');
      rawBodyString = bodyString;
      event = JSON.parse(bodyString);
    } else {
      event = req.body;
      try {
        rawBodyString = JSON.stringify(req.body);
      } catch {
        rawBodyString = null;
      }
    }

    if (!event || !event.event) {
      logger.warn('RevenueCat webhook: Invalid event payload', { body: event });
      return res.status(400).json({ error: 'Invalid payload' });
    }

    // Always persist an audit row. This is the SSOT for "webhook arrived".
    // event_id is a stable hash of the raw body to avoid relying on provider-specific ids.
    try {
      const eventId = crypto
        .createHash('sha256')
        .update(String(rawBodyString || ''))
        .digest('hex');
      const userId = event?.app_user_id ? String(event.app_user_id) : null;
      const type = String(event?.event || 'unknown');
      const payloadJson = (() => {
        try { return JSON.stringify(event); } catch { return null; }
      })();

      await query(
        `insert into subscription_events (event_id, user_id, type, provider, payload, created_at)
         values ($1, $2, $3, 'revenuecat', $4::jsonb, timezone('utc', now()))
         on conflict (event_id) do nothing`,
        [eventId, userId, type, payloadJson]
      );
    } catch (e) {
      logger.warn('[RevenueCat] Failed to insert subscription_events audit row', { error: e?.message || String(e) });
      // continue (do not fail webhook)
    }

    await processRevenueCatEvent(event);
    res.status(200).json({ received: true });
  } catch (error) {
    logger.error('RevenueCat webhook error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
}
