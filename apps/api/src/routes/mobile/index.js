import express from 'express';
import profileRouter from './profile.js';
import entitlementRouter from './entitlement.js';
import accountRouter from './account.js';
import nudgeRouter from './nudge.js';
import preReminderRouter from './preReminder.js';
import pushRouter from './push.js';

const router = express.Router();

router.use('/profile', profileRouter);
router.use('/entitlement', entitlementRouter);
router.use('/account', accountRouter);
router.use('/nudge', nudgeRouter);
router.use('/nudge', preReminderRouter);  // /mobile/nudge/pre-reminder
router.use('/push', pushRouter);

// 410 Gone stubs for deprecated endpoints (v1.6.0)
// These endpoints were removed but never called by iOS app.
// Keeping 410 stubs for backward compatibility and monitoring.
const deprecatedHandler = (req, res) => {
  res.status(410).json({
    error: {
      code: 'ENDPOINT_DEPRECATED',
      message: 'This endpoint has been removed in v1.6.0'
    }
  });
};
router.all('/behavior', deprecatedHandler);
router.all('/behavior/*', deprecatedHandler);
router.all('/feeling', deprecatedHandler);
router.all('/feeling/*', deprecatedHandler);
router.all('/daily_metrics', deprecatedHandler);
router.all('/daily_metrics/*', deprecatedHandler);
router.all('/sensors', deprecatedHandler);
router.all('/sensors/*', deprecatedHandler);
router.all('/user-type', deprecatedHandler);
router.all('/user-type/*', deprecatedHandler);
router.all('/realtime', deprecatedHandler);
router.all('/realtime/*', deprecatedHandler);

export default router;
