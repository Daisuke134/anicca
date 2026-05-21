import { resolve, relative, isAbsolute } from 'node:path';
import type { Language } from './types.js';

const CARD_ID_PATTERN = /^[a-z_]+_\d+$/;

/** Validate card_id format and resolve safe image path (no traversal) */
export function resolveCardImagePath(
  assetsDir: string,
  cardId: string,
  language: Language,
): string {
  if (!CARD_ID_PATTERN.test(cardId)) {
    throw new Error(`Invalid card_id format: "${cardId}". Must match ${CARD_ID_PATTERN}`);
  }
  const imagePath = resolve(assetsDir, language, `${cardId}.png`);
  const rel = relative(assetsDir, imagePath);
  if (rel.startsWith('..') || isAbsolute(rel)) {
    throw new Error(`Path traversal detected for card_id: "${cardId}"`);
  }
  return imagePath;
}
