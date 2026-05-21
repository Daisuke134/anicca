import express from 'express';
import requireInternalAuth from '../../middleware/requireInternalAuth.js';

const router = express.Router();

// POST /api/admin/trigger-nudges — manually trigger generateNudges cron job
router.post('/', requireInternalAuth, async (req, res) => {
  // Safety: disable LLM nudge generation triggers unless explicitly enabled.
  // This prevents accidental OpenAI token spend and aligns with "APNs + rule-based" direction.
  if (process.env.NUDGE_GENERATION_ENABLED !== 'true') {
    return res.status(410).json({ error: 'Nudge generation trigger is disabled' });
  }
  try {
    // Dynamic import to avoid circular deps and keep cron standalone
    const { runGenerateNudges } = await import('../../jobs/generateNudges.js');

    // Run in background, respond immediately
    res.json({ status: 'started', message: 'generateNudges triggered' });

    await runGenerateNudges();
    console.log('✅ [TriggerNudges] Manual trigger completed');
  } catch (error) {
    console.error('❌ [TriggerNudges] Manual trigger failed:', error.message);
    if (!res.headersSent) {
      res.status(500).json({ error: error.message });
    }
  }
});

export default router;
