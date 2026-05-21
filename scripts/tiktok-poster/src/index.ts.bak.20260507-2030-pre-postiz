import { Command } from 'commander';
import { resolve } from 'node:path';
import { loadTracker, saveTracker } from './tracker-io.js';
import { BlotatoClient } from './blotato-client.js';
import { generateCaption } from './caption.js';
import { resolveCardImagePath } from './path-security.js';
import { loadImageAsBase64Jpg } from './image-loader.js';
import type { Language, ReconcileResolution } from './types.js';

const TRACKER_PATH = resolve(
  import.meta.dirname ?? '.',
  '../../../assets/card-screenshots/posted_tracker.json',
);

const ASSETS_DIR = resolve(
  import.meta.dirname ?? '.',
  '../../../assets/card-screenshots',
);

function parseLanguage(value: string): Language {
  if (value !== 'en' && value !== 'ja') {
    console.error(`Invalid language: ${value}. Must be 'en' or 'ja'.`);
    process.exit(1);
  }
  return value;
}

function resolveAccountId(language: Language): string {
  const envKey = language === 'en' ? 'BLOTATO_ACCOUNT_ID_EN' : 'BLOTATO_ACCOUNT_ID_JA';
  const id = process.env[envKey];
  if (!id) {
    console.error(`${envKey} env var required.`);
    process.exit(1);
  }
  return id;
}

const program = new Command();

program
  .command('reserve')
  .requiredOption('--language <lang>', 'Language (en or ja)')
  .option('--dry-run', 'Dry run mode (skip real API for recovery)')
  .action(async (opts: { language: string; dryRun?: boolean }) => {
    const language = parseLanguage(opts.language);
    const dryRun = opts.dryRun ?? false;
    const runId = process.env.GITHUB_RUN_ID ?? `local-${Date.now()}`;

    const tracker = await loadTracker(TRACKER_PATH);

    // All cards exhausted → exit gracefully
    if (tracker.allCardsPosted(language)) {
      console.log(`::warning::All cards exhausted for ${language}. No card to reserve.`);
      process.exit(0);
    }

    // Recover stalled in_flights using blotato_post_id + status API
    const client = new BlotatoClient({
      dryRun,
      apiKey: process.env.BLOTATO_API_KEY,
    });
    await tracker.recoverStalledInFlights(language, (blotatoPostId) =>
      client.checkPostStatus(blotatoPostId),
    );

    // Persist recovery results before reserving
    await saveTracker(TRACKER_PATH, tracker);

    // All cards exhausted after recovery → exit gracefully
    if (tracker.allCardsPosted(language)) {
      console.log(`::warning::All cards exhausted for ${language} (after recovery). No card to reserve.`);
      process.exit(0);
    }

    const result = tracker.reserveNextCard(language, runId);
    await saveTracker(TRACKER_PATH, tracker);

    console.log(`Reserved: ${result.cardId} (${result.cardKey})`);
  });

program
  .command('post')
  .requiredOption('--language <lang>', 'Language (en or ja)')
  .option('--dry-run', 'Dry run mode')
  .action(async (opts: { language: string; dryRun?: boolean }) => {
    const language = parseLanguage(opts.language);
    const dryRun = opts.dryRun ?? false;
    const accountId = dryRun ? 'dry-run-account' : resolveAccountId(language);

    const tracker = await loadTracker(TRACKER_PATH);
    const data = tracker.getData();

    // Find all in_flight cards for this language (must be exactly 1)
    const inFlightCards: string[] = [];
    for (const cardId of Object.keys(data.cards)) {
      if (data.cards[cardId]?.[language]?.status === 'in_flight') {
        inFlightCards.push(cardId);
      }
    }

    if (inFlightCards.length === 0) {
      console.error(`No in_flight card found for ${language}. Run 'reserve' first.`);
      process.exit(1);
    }

    if (inFlightCards.length > 1) {
      console.error(
        `Multiple in_flight cards found for ${language}: ${inFlightCards.join(', ')}. ` +
        `This indicates tracker corruption. Use 'reconcile' to resolve.`,
      );
      process.exit(1);
    }

    const inFlightCardId = inFlightCards[0]!;
    const cardKey = `${inFlightCardId}_${language}`;
    const problemType = inFlightCardId.replace(/_\d+$/, '');
    const imagePath = resolveCardImagePath(ASSETS_DIR, inFlightCardId, language);
    const caption = generateCaption({ cardId: inFlightCardId, language, problemType });

    const client = new BlotatoClient({
      dryRun,
      apiKey: process.env.BLOTATO_API_KEY,
    });

    // Check if this in_flight already has a blotato_post_id (resume from polling)
    const existingBlotatoPostId = data.cards[inFlightCardId]?.[language]?.blotato_post_id;
    let blotatoPostIdSaved = !!existingBlotatoPostId;

    try {
      if (existingBlotatoPostId) {
        // Resume: blotato_post_id already saved — skip upload + post, go to status check
        console.log(`Resuming with existing blotato_post_id: ${existingBlotatoPostId}`);
        // For Blotato, polling is handled server-side. If we have a blotato_post_id,
        // the post was already submitted. Mark as posted.
        const freshTracker = await loadTracker(TRACKER_PATH);
        freshTracker.markAsPosted(inFlightCardId, language);
        await saveTracker(TRACKER_PATH, freshTracker);
        console.log(`Posted (resumed): ${cardKey}`);
      } else {
        // Phase 1: Upload image via GitHub raw URL
        const imageFileName = `${inFlightCardId}.png`;
        const rawUrl = `https://raw.githubusercontent.com/Daisuke134/anicca.ai/dev/assets/card-screenshots/${language}/${imageFileName}`;
        const mediaResult = await client.uploadMedia(rawUrl);

        // Phase 2: Post to TikTok via Blotato
        const postResult = await client.postPhoto(accountId, mediaResult.url, caption);

        // Persist blotato_post_id BEFORE considering it done (crash recovery)
        const trackerForId = await loadTracker(TRACKER_PATH);
        trackerForId.saveBlotatoPostId(inFlightCardId, language, postResult.postSubmissionId);
        await saveTracker(TRACKER_PATH, trackerForId);
        blotatoPostIdSaved = true;

        // Phase 3: Mark as posted (Blotato handles the actual TikTok upload asynchronously)
        const freshTracker = await loadTracker(TRACKER_PATH);
        freshTracker.markAsPosted(inFlightCardId, language);
        await saveTracker(TRACKER_PATH, freshTracker);
        console.log(`Posted: ${cardKey} → Blotato ID: ${postResult.postSubmissionId}`);
      }
    } catch (error) {
      console.error(`Post failed for ${cardKey}:`, error);

      if (blotatoPostIdSaved) {
        // blotato_post_id is persisted — keep in_flight so next run's
        // recoverStalledInFlights can check status via checkPostStatus.
        console.log(`Kept in_flight with blotato_post_id for recovery: ${cardKey}`);
      } else {
        // Failed before postPhoto completed — no blotato_post_id, safe to rollback
        const freshTracker = await loadTracker(TRACKER_PATH);
        freshTracker.rollbackInFlight(inFlightCardId, language);
        await saveTracker(TRACKER_PATH, freshTracker);
        console.log(`Rolled back (no blotato_post_id): ${cardKey}`);
      }
      process.exit(1);
    }
  });

program
  .command('reconcile')
  .requiredOption('--language <lang>', 'Language (en or ja)')
  .requiredOption('--card-id <id>', 'Card ID (e.g., staying_up_late_0)')
  .requiredOption('--resolution <res>', 'Resolution: "posted" or "unposted"')
  .option('--blotato-id <id>', 'Blotato post ID (optional, for posted resolution)')
  .action(async (opts: { language: string; cardId: string; resolution: string; blotatoId?: string }) => {
    const language = parseLanguage(opts.language);

    if (opts.resolution !== 'posted' && opts.resolution !== 'unposted') {
      console.error(`Invalid resolution: ${opts.resolution}. Must be 'posted' or 'unposted'.`);
      process.exit(1);
    }
    const resolution: ReconcileResolution = opts.resolution;

    const tracker = await loadTracker(TRACKER_PATH);
    tracker.resolveManualReconcile(opts.cardId, language, resolution, opts.blotatoId);
    await saveTracker(TRACKER_PATH, tracker);

    console.log(`Reconciled: ${opts.cardId}/${language} → ${resolution}${opts.blotatoId ? ` (Blotato ID: ${opts.blotatoId})` : ''}`);
  });

program.parse();
