import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';
import type { TrackerData } from './types.js';
import { Tracker } from './tracker.js';
import { generateCardOrder } from './card-order.js';

const CARD_ID_PATTERN = /^[a-z_]+_\d+$/;

/** Ensure card_order is populated. Migrates empty/missing card_order. */
function ensureCardOrder(data: TrackerData): TrackerData {
  if (!data.card_order || data.card_order.length === 0) {
    return { ...data, card_order: generateCardOrder() };
  }
  return data;
}

/** Validate tracker data integrity: card_order IDs and card entries */
function validateTrackerData(data: TrackerData): void {
  const allowedSet = new Set(generateCardOrder());

  // card_order: format + membership + uniqueness + completeness
  const seenOrder = new Set<string>();
  for (const cardId of data.card_order) {
    if (!CARD_ID_PATTERN.test(cardId)) {
      throw new Error(`Invalid card_id in card_order: "${cardId}"`);
    }
    if (!allowedSet.has(cardId)) {
      throw new Error(`Unknown card_id in card_order: "${cardId}" is not in the canonical 189-card set`);
    }
    if (seenOrder.has(cardId)) {
      throw new Error(`Duplicate card_id in card_order: "${cardId}"`);
    }
    seenOrder.add(cardId);
  }

  // card_order must be exactly the canonical 189-card set (no missing cards)
  if (seenOrder.size !== allowedSet.size) {
    throw new Error(
      `card_order has ${seenOrder.size} entries but canonical set has ${allowedSet.size}. ` +
      `Missing cards detected.`,
    );
  }

  // cards: format + membership in allowed set
  for (const cardId of Object.keys(data.cards)) {
    if (!CARD_ID_PATTERN.test(cardId)) {
      throw new Error(`Invalid card_id in cards: "${cardId}"`);
    }
    if (!allowedSet.has(cardId)) {
      throw new Error(`Unknown card_id in cards: "${cardId}" is not in the canonical 189-card set`);
    }
    if (!data.card_order.includes(cardId)) {
      throw new Error(`Card "${cardId}" in cards but not in card_order`);
    }
  }
}

/** Load tracker from JSON file. Returns bootstrapped default if file doesn't exist. */
export async function loadTracker(filePath: string): Promise<Tracker> {
  try {
    const raw = await readFile(filePath, 'utf-8');
    const data: TrackerData = JSON.parse(raw);
    const migrated = ensureCardOrder(data);
    validateTrackerData(migrated);
    return new Tracker(migrated);
  } catch (err: unknown) {
    if ((err as NodeJS.ErrnoException).code === 'ENOENT') {
      const data: TrackerData = {
        version: 1,
        cards: {},
        next_index: { en: 0, ja: 0 },
        card_order: generateCardOrder(),
      };
      return new Tracker(data);
    }
    throw err;
  }
}

/** Save tracker data to JSON file (creates parent directories if needed) */
export async function saveTracker(filePath: string, tracker: Tracker): Promise<void> {
  await mkdir(dirname(filePath), { recursive: true });
  const data = tracker.getData();
  await writeFile(filePath, JSON.stringify(data, null, 2) + '\n', 'utf-8');
}
