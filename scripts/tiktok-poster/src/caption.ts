import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import type { Language } from './types.js';

interface CaptionEntry {
  hook: string;
  value: string;
  cta: string;
}

interface CaptionPool {
  captions: CaptionEntry[];
  hashtags: string[];
}

interface CaptionInput {
  cardId: string;
  language: Language;
  problemType: string;
}

const CAPTION_DATA_DIR = resolve(
  import.meta.dirname ?? '.',
  './caption-data',
);

/** Load caption pool JSON for a problem type + language */
function loadCaptionPool(problemType: string, language: Language): CaptionPool {
  const filePath = resolve(CAPTION_DATA_DIR, language, `${problemType}.json`);
  const raw = readFileSync(filePath, 'utf-8');
  return JSON.parse(raw) as CaptionPool;
}

/** Extract the numeric suffix from a cardId (e.g. "staying_up_late_3" → 3) */
function extractCardIndex(cardId: string): number {
  const match = cardId.match(/_(\d+)$/);
  return match ? parseInt(match[1], 10) : 0;
}

/**
 * Generate a TikTok caption from the pre-written caption pool.
 * Selection is deterministic: cardIndex % poolSize ensures the same card
 * always gets the same caption.
 */
export function generateCaption(input: CaptionInput): string {
  const { cardId, language, problemType } = input;
  const pool = loadCaptionPool(problemType, language);
  const cardIndex = extractCardIndex(cardId);
  const selected = pool.captions[cardIndex % pool.captions.length]!;

  return [
    selected.hook,
    selected.value,
    selected.cta,
    pool.hashtags.join(' '),
  ].join('\n\n');
}

// Exported for testing
export { loadCaptionPool, extractCardIndex };
export type { CaptionPool, CaptionEntry, CaptionInput };
