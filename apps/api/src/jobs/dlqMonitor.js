import { monitorDLQ } from '../services/dlqMonitor.js';
import { notifyDLQEntry } from '../services/slackNotifier.js';
import baseLogger from '../utils/logger.js';

const logger = baseLogger.withContext('DlqMonitorJob');

export async function runDlqMonitor() {
  const result = await monitorDLQ();

  if (result.archived > 0) {
    await notifyDLQEntry('dlq-monitor', 'archived_old_entries', result);
  }

  return result;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  runDlqMonitor()
    .then((result) => {
      logger.info('DLQ monitor completed', result);
      process.exit(0);
    })
    .catch((error) => {
      logger.error('DLQ monitor failed', error);
      process.exit(1);
    });
}

export default runDlqMonitor;
