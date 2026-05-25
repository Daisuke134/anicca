/**
 * export-affirmations.js — SSOT sync for affirmation notification content.
 *
 * Source of truth: iOS QuoteProvider.swift (en/ja/es Quote pools).
 * This script parses that file and emits one JSON catalog per language under
 *   apps/api/src/modules/affirmations/catalog/<lang>.json
 * so the backend APNs sender can deliver the exact same affirmation text (by
 * stable id qNNN) that the app renders on its Feed card.
 *
 * Run:  node apps/api/scripts/export-affirmations.js
 * The Swift path can be overridden with QUOTE_PROVIDER_PATH for CI.
 *
 * Keeping app + backend in lockstep is mandatory: a tapped notification carries
 * quoteId and the new app scrolls to QuoteProvider[quoteId]; the notification
 * body must be the text of that same id.
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '..', '..', '..');

const SWIFT_PATH =
  process.env.QUOTE_PROVIDER_PATH ||
  path.join(REPO_ROOT, 'aniccaios', 'aniccaios', 'Services', 'QuoteProvider.swift');

const OUT_DIR = path.join(__dirname, '..', 'src', 'modules', 'affirmations', 'catalog');

const LANGS = ['en', 'ja', 'es'];

/** Extract the body of `private static let <lang>: [Quote] = [ ... ]`. */
function extractArrayBody(src, lang) {
  const re = new RegExp(
    `private static let ${lang}: \\[Quote\\] = \\[([\\s\\S]*?)\\n    \\]`,
    'm'
  );
  const m = src.match(re);
  if (!m) throw new Error(`Could not locate Quote pool for lang=${lang}`);
  return m[1];
}

/** Parse `Quote(id: "qNNN", text: "...")` entries into an ordered id->text map. */
function parseQuotes(body, lang) {
  const re = /Quote\(id:\s*"(q\d+)",\s*text:\s*"((?:[^"\\]|\\.)*)"\)/g;
  const quotes = {};
  let count = 0;
  let match;
  while ((match = re.exec(body)) !== null) {
    const id = match[1];
    // Unescape Swift string escapes we might encounter (\" and \\).
    const text = match[2].replace(/\\"/g, '"').replace(/\\\\/g, '\\');
    if (quotes[id]) throw new Error(`Duplicate id ${id} in lang=${lang}`);
    quotes[id] = text;
    count += 1;
  }
  if (count === 0) throw new Error(`No quotes parsed for lang=${lang}`);
  return quotes;
}

function main() {
  const src = fs.readFileSync(SWIFT_PATH, 'utf8');
  fs.mkdirSync(OUT_DIR, { recursive: true });

  const idSets = {};
  for (const lang of LANGS) {
    const body = extractArrayBody(src, lang);
    const quotes = parseQuotes(body, lang);
    idSets[lang] = Object.keys(quotes).sort();
    const out = { schemaVersion: 1, lang, quotes };
    const outPath = path.join(OUT_DIR, `${lang}.json`);
    fs.writeFileSync(outPath, `${JSON.stringify(out, null, 2)}\n`, 'utf8');
    console.log(`wrote ${outPath} (${idSets[lang].length} quotes)`);
  }

  // Cross-language id-set parity check (same qNNN must exist in every language).
  const base = idSets[LANGS[0]].join(',');
  for (const lang of LANGS.slice(1)) {
    if (idSets[lang].join(',') !== base) {
      throw new Error(`id set mismatch: ${LANGS[0]} vs ${lang}`);
    }
  }
  console.log(`OK: ${idSets[LANGS[0]].length} ids aligned across ${LANGS.join('/')}`);
}

main();
