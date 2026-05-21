import express from 'express';
import handler from '../../../api/billing/webhookRevenueCat.js';

const router = express.Router();
router.post('/', (req, res) => handler(req, res));
export default router;


