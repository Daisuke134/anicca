import express from 'express';
import revenuecatWebhookRouter from './webhook/revenuecat.js';
import revenuecatSyncRouter from './revenuecat-sync.js';

const router = express.Router();

router.use('/webhook/revenuecat', revenuecatWebhookRouter);
router.use('/revenuecat/sync', revenuecatSyncRouter);

// Backward-compat: Stripe billing endpoints removed in 1.5.0, kept as 410 for old clients
router.post('/checkout-session', (_req, res) => res.status(410).json({ error: { code: 'GONE', message: 'Stripe billing removed in v1.5.0. Use RevenueCat.' } }));
router.post('/portal-session', (_req, res) => res.status(410).json({ error: { code: 'GONE', message: 'Stripe billing removed in v1.5.0. Use RevenueCat.' } }));

export default router;
