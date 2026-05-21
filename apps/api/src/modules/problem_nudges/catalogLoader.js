import fs from 'fs';
import path from 'path';
import baseLogger from '../../utils/logger.js';

const logger = baseLogger.withContext('ProblemNudgeCatalogLoader');

const SUPPORTED_LANGS = new Set(['en', 'ja', 'es', 'fr', 'de', 'pt-BR']);
const CACHE = new Map(); // lang -> catalog json

function normalizeLang(lang) {
  if (!lang) return 'en';
  const raw = String(lang).trim();
  if (!raw) return 'en';
  if (raw.toLowerCase() === 'pt-br') return 'pt-BR';
  const two = raw.toLowerCase().slice(0, 2);
  if (two === 'pt') return 'pt-BR';
  if (SUPPORTED_LANGS.has(two)) return two;
  if (SUPPORTED_LANGS.has(raw)) return raw;
  return 'en';
}

function catalogPathFor(lang) {
  // This file lives in apps/api/src/modules/problem_nudges/
  return path.join(path.dirname(new URL(import.meta.url).pathname), 'catalog', `${lang}.json`);
}

export function loadProblemNudgeCatalog(lang) {
  const key = normalizeLang(lang);
  if (CACHE.has(key)) return CACHE.get(key);

  const p = catalogPathFor(key);
  try {
    const src = fs.readFileSync(p, 'utf8');
    const parsed = JSON.parse(src);
    if (parsed?.schemaVersion !== 1) {
      logger.warn(`Unexpected schemaVersion for catalog ${key}: ${parsed?.schemaVersion}`);
    }
    CACHE.set(key, parsed);
    return parsed;
  } catch (e) {
    logger.error(`Failed to load problem nudge catalog for ${key}`, e);
    // Fallback: English is required to exist.
    if (key !== 'en') return loadProblemNudgeCatalog('en');
    throw e;
  }
}

export function normalizeCatalogLang(lang) {
  return normalizeLang(lang);
}

