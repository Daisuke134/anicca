import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import baseLogger from '../../utils/logger.js';

const MODULE_DIR = path.dirname(fileURLToPath(import.meta.url));

const logger = baseLogger.withContext('AffirmationsLoader');

const SUPPORTED_LANGS = new Set(['en', 'ja', 'es', 'fr', 'de', 'pt-BR']);
const CACHE = new Map(); // lang -> { schemaVersion, lang, quotes }

/**
 * Brand name shown as the notification TITLE (per language).
 * The affirmation text itself is the notification BODY.
 * Languages without a localized catalog fall back to English content but keep
 * their localized brand title.
 */
const APP_NAME = {
  en: 'Anicca',
  ja: 'アニッチャ',
  es: 'Anicca',
  fr: 'Anicca',
  de: 'Anicca',
  'pt-BR': 'Anicca',
};

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

/** Languages that ship a localized affirmation catalog. Others reuse English text. */
function catalogLangFor(lang) {
  const key = normalizeLang(lang);
  return key === 'ja' || key === 'es' ? key : 'en';
}

function catalogPathFor(lang) {
  // This file lives in apps/api/src/modules/affirmations/
  return path.join(MODULE_DIR, 'catalog', `${lang}.json`);
}

export function loadAffirmationCatalog(lang) {
  const key = catalogLangFor(lang);
  if (CACHE.has(key)) return CACHE.get(key);

  const p = catalogPathFor(key);
  try {
    const parsed = JSON.parse(fs.readFileSync(p, 'utf8'));
    if (parsed?.schemaVersion !== 1) {
      logger.warn(`Unexpected schemaVersion for affirmation catalog ${key}: ${parsed?.schemaVersion}`);
    }
    CACHE.set(key, parsed);
    return parsed;
  } catch (e) {
    logger.error(`Failed to load affirmation catalog for ${key}`, e);
    if (key !== 'en') return loadAffirmationCatalog('en');
    throw e;
  }
}

/** Brand title for the notification, by user language. Always defined. */
export function appName(lang) {
  return APP_NAME[normalizeLang(lang)] || 'Anicca';
}

/** Affirmation body text for a stable quote id, in the user's language. */
export function affirmationText(quoteId, lang) {
  const catalog = loadAffirmationCatalog(lang);
  const text = catalog?.quotes?.[quoteId];
  if (text) return text;
  // Unknown id (e.g. app catalog drifted ahead): fall back to English, then null.
  if (catalogLangFor(lang) !== 'en') {
    return loadAffirmationCatalog('en')?.quotes?.[quoteId] || null;
  }
  return null;
}

/** Ordered list of all quote ids (from the English catalog, the id authority). */
export function allQuoteIds() {
  const en = loadAffirmationCatalog('en');
  return Object.keys(en?.quotes || {});
}

export function normalizeAffirmationLang(lang) {
  return normalizeLang(lang);
}
