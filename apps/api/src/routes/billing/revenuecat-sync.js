import express from 'express';
import handler from '../../api/billing/revenuecatSync.js';

const router = express.Router();
router.post('/', handler);
export default router;


