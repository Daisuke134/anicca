import { cleanOldLowRelevancePosts } from '../services/hookPostTtlCleaner.js';
import { notifyPostSuccess, notifyDLQEntry } from '../services/slackNotifier.js';
import baseLogger from '../utils/logger.js';

const logger = baseLogger.withContext('HookPostTtlCleanerJob');

export async function runHookPostTtlCleaner() {
  const result = await cleanOldLowRelevancePosts();

  if (result.skipped) {
    logger.info('hook post TTL cleaner skipped', result.reason);
    return result;
  }

  if (result.failed > 0) {
    await notifyDLQEntry('hookpost-ttl-cleaner', `failed=${result.failed}`, result);
  }

  if (result.archived > 0 || result.deleted > 0) {
    await notifyPostSuccess('hookpost-ttl-cleaner', `archived:${result.archived}`, 5);
  }

  return result;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  runHookPostTtlCleaner()
    .then((result) => {
      logger.info('hook post TTL cleaner completed', result);
      process.exit(0);
    })
    .catch((error) => {
      logger.error('hook post TTL cleaner failed', error);
      process.exit(1);
    });
}

export default runHookPostTtlCleaner;
