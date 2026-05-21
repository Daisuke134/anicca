import express from 'express';
import requireInternalAuth from '../../middleware/requireInternalAuth.js';
import baseLogger from '../../utils/logger.js';
import { runRoundtableStandup } from '../../jobs/roundtableStandup.js';
import { runRoundtableWatercooler } from '../../jobs/roundtableWatercooler.js';
import { runMemoryExtraction } from '../../jobs/memoryExtractor.js';
import { runInitiativeGenerator } from '../../jobs/initiativeGenerator.js';

const router = express.Router();
const logger = baseLogger.withContext('AdminRoundtable');

router.use(requireInternalAuth);

router.post('/standup', async (req, res) => {
  try {
    const result = await runRoundtableStandup();
    return res.json({ success: true, result });
  } catch (error) {
    logger.error('standup failed', error);
    return res.status(500).json({ error: 'standup failed' });
  }
});

router.post('/watercooler', async (req, res) => {
  try {
    const result = await runRoundtableWatercooler();
    return res.json({ success: true, result });
  } catch (error) {
    logger.error('watercooler failed', error);
    return res.status(500).json({ error: 'watercooler failed' });
  }
});

router.post('/memory-extract', async (req, res) => {
  try {
    const result = await runMemoryExtraction();
    return res.json({ success: true, result });
  } catch (error) {
    logger.error('memory-extract failed', error);
    return res.status(500).json({ error: 'memory-extract failed' });
  }
});

router.post('/initiative-generate', async (req, res) => {
  try {
    const result = await runInitiativeGenerator();
    return res.json({ success: true, result });
  } catch (error) {
    logger.error('initiative-generate failed', error);
    return res.status(500).json({ error: 'initiative-generate failed' });
  }
});

export default router;
