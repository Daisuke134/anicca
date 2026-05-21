import express from 'express';
import { rotateAndIssue } from '../../services/auth/refreshService.js';

const router = express.Router();

router.post('/', async (req, res) => {
  try {
    const { refresh_token } = req.body || {};
    if (!refresh_token) {
      return res.status(400).json({ error: 'refresh_token_required' });
    }
    const result = await rotateAndIssue(
      refresh_token,
      (req.get('device-id') || 'unknown').toString(),
      req.get('user-agent') || null
    );
    if (result.error) {
      return res.status(result.status || 401).json({ error: result.error });
    }
    return res.json(result);
  } catch (e) {
    return res.status(500).json({ error: 'internal_error' });
  }
});

export default router;












