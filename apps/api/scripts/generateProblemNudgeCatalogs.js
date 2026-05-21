// Generate backend problem nudge catalogs from iOS Localizable.strings.
//
// Why this exists:
// - We need 6 languages worth of hook/detail pairs sized to 42 (normal) / 70 (staying_up_late)
// - iOS currently ships fewer variants; this script expands deterministically with small,
//   language-appropriate prefixes per slot to guarantee string-uniqueness.
//
// Usage:
//   node apps/api/scripts/generateProblemNudgeCatalogs.js
//
// Output:
//   apps/api/src/modules/problem_nudges/catalog/{lang}.json
//
import fs from 'fs';
import path from 'path';

const REPO_ROOT = process.cwd();

const IOS_RESOURCES_DIR = path.join(REPO_ROOT, 'aniccaios', 'aniccaios', 'Resources');
const OUT_DIR = path.join(REPO_ROOT, 'apps', 'api', 'src', 'modules', 'problem_nudges', 'catalog');

const LANGS = ['en', 'ja', 'es', 'fr', 'de', 'pt-BR'];

const PROBLEM_TYPES = [
  'staying_up_late',
  'cant_wake_up',
  'self_loathing',
  'rumination',
  'procrastination',
  'anxiety',
  'lying',
  'bad_mouthing',
  'porn_addiction',
  'alcohol_dependency',
  'anger',
  'obsessive',
  'loneliness',
];

function readStringsFile(filePath) {
  const src = fs.readFileSync(filePath, 'utf8');
  // Very small .strings parser: match `"key" = "value";` lines.
  // This is sufficient for our Localizable.strings in this repo.
  const map = new Map();
  const re = /^\s*"([^"]+)"\s*=\s*"((?:\\.|[^"\\])*)"\s*;\s*$/gm;
  let m;
  while ((m = re.exec(src)) !== null) {
    const key = m[1];
    const raw = m[2];
    // Unescape common sequences used in .strings files.
    const val = raw
      .replace(/\\"/g, '"')
      .replace(/\\n/g, '\n')
      .replace(/\\\\/g, '\\');
    map.set(key, val);
  }
  return map;
}

function mustGet(map, key) {
  const v = map.get(key);
  if (v == null) throw new Error(`Missing key in Localizable.strings: ${key}`);
  return v;
}

function range(n) {
  return Array.from({ length: n }, (_, i) => i);
}

// Slot prefixes must be language-appropriate, short, and not obnoxious.
// These prefixes exist to guarantee uniqueness across the 3/5 slots per day while reusing
// the smaller iOS variant pools.
const SLOT_PREFIX = {
  en: {
    normal: ['Morning: ', 'Midday: ', 'Evening: '],
    staying_up_late: ['Tonight: ', 'Late: ', 'Wrap up: ', 'Midnight: ', '1 AM: '],
  },
  ja: {
    normal: ['朝: ', '昼: ', '夜: '],
    staying_up_late: ['今夜: ', '夜: ', '締める: ', '0時: ', '1時: '],
  },
  es: {
    normal: ['Mañana: ', 'Mediodía: ', 'Noche: '],
    staying_up_late: ['Esta noche: ', 'Tarde: ', 'Cierre: ', 'Medianoche: ', '1 AM: '],
  },
  fr: {
    normal: ['Matin: ', 'Midi: ', 'Soir: '],
    staying_up_late: ['Ce soir: ', 'Tard: ', 'On clôt: ', 'Minuit: ', '1h: '],
  },
  de: {
    normal: ['Morgen: ', 'Mittag: ', 'Abend: '],
    staying_up_late: ['Heute: ', 'Spät: ', 'Schluss: ', 'Mitternacht: ', '1 Uhr: '],
  },
  'pt-BR': {
    normal: ['Manhã: ', 'Meio-dia: ', 'Noite: '],
    staying_up_late: ['Hoje: ', 'Tarde: ', 'Encerrar: ', 'Meia-noite: ', '1h: '],
  },
};

function pickPool(arr, desired, { allowReuse = false } = {}) {
  if (!Array.isArray(arr) || arr.length === 0) return [];
  if (arr.length >= desired && !allowReuse) return arr.slice(0, desired);
  // If not enough, we can reuse, but we will add prefixes anyway to ensure uniqueness.
  return arr.slice(0);
}

function buildUniquePool(primary, fallback, desired) {
  const out = [];
  const seen = new Set();
  const add = (s) => {
    const v = String(s || '');
    if (!v) return;
    if (seen.has(v)) return;
    seen.add(v);
    out.push(v);
  };
  for (const s of primary || []) add(s);
  for (const s of fallback || []) add(s);
  return out.slice(0, desired);
}

function isDeepNightCandidate(s, lang) {
  const t = String(s || '').toLowerCase();
  const kw = {
    en: ['sleep', 'bed', 'rest', 'dream', 'eyes'],
    ja: ['寝', '睡眠', 'ベッド', '布団', '休'],
    es: ['dorm', 'cama', 'descans', 'sueñ', 'ojos'],
    fr: ['dorm', 'lit', 'repos', 'sommeil', 'yeux'],
    de: ['schlaf', 'bett', 'ruhe', 'träum', 'augen'],
    'pt-BR': ['dorm', 'cama', 'descans', 'sonh', 'olhos'],
  }[lang] || [];
  return kw.some(k => t.includes(k));
}

function buildCatalogForLang(langKey, stringsMap) {
  const prefixes = SLOT_PREFIX[langKey];
  if (!prefixes) throw new Error(`Missing SLOT_PREFIX for lang=${langKey}`);

  const titles = {};
  const hooks = {};
  const details = {};

  for (const pt of PROBLEM_TYPES) {
    titles[pt] = mustGet(stringsMap, `problem_${pt}_notification_title`);

    if (pt !== 'staying_up_late') {
      const baseHooks = range(14).map(i => mustGet(stringsMap, `nudge_${pt}_notification_${i + 1}`));
      const baseDetails = range(14).map(i => mustGet(stringsMap, `nudge_${pt}_detail_${i + 1}`));

      const outHooks = [];
      const outDetails = [];

      for (const day of range(14)) {
        for (const slot of range(3)) {
          const prefix = prefixes.normal[slot] || '';
          const idx = (day + slot * 5) % 14;
          outHooks.push(prefix + baseHooks[idx]);
          outDetails.push(prefix + baseDetails[idx]);
        }
      }

      hooks[pt] = outHooks;
      details[pt] = outDetails;
      continue;
    }

    // staying_up_late: need 70 (14 * 5)
    const stayingHooksAll = [];
    const stayingDetailsAll = [];
    // iOS currently has 21; use all as a pool.
    const baseHooksAll = [];
    const baseDetailsAll = [];
    for (let i = 1; i <= 99; i++) {
      const hk = stringsMap.get(`nudge_${pt}_notification_${i}`);
      const dt = stringsMap.get(`nudge_${pt}_detail_${i}`);
      if (!hk || !dt) break;
      baseHooksAll.push(hk);
      baseDetailsAll.push(dt);
    }
    if (baseHooksAll.length < 14) throw new Error(`staying_up_late hooks too small (${baseHooksAll.length}) for lang=${langKey}`);

    const deepNightHooks = baseHooksAll.filter(s => isDeepNightCandidate(s, langKey));
    const deepNightDetails = baseDetailsAll.filter(s => isDeepNightCandidate(s, langKey));

    // Ensure we have at least 14 distinct strings for each deep-night slot.
    // If keyword-filtered pool is too small, fill from the full staying_up_late pool.
    const deepHookPool = buildUniquePool(deepNightHooks, baseHooksAll, 14);
    const deepDetailPool = buildUniquePool(deepNightDetails, baseDetailsAll, 14);

    const eveningHookPool = pickPool(baseHooksAll, 21, { allowReuse: true });
    const eveningDetailPool = pickPool(baseDetailsAll, 21, { allowReuse: true });

    for (const day of range(14)) {
      for (const slot of range(5)) {
        const prefix = prefixes.staying_up_late[slot] || '';

        let hk = '';
        let dt = '';

        if (slot === 3) {
          // 00:00 deep-night slot
          hk = deepHookPool[day % deepHookPool.length];
          dt = deepDetailPool[day % deepDetailPool.length];
        } else if (slot === 4) {
          // 01:00 deep-night slot (shifted to avoid exact repeats vs slot=3)
          const idx = (day + 7) % deepHookPool.length;
          hk = deepHookPool[idx];
          dt = deepDetailPool[(day + 7) % deepDetailPool.length];
        } else {
          const idx = (day + slot * 4) % eveningHookPool.length;
          hk = eveningHookPool[idx];
          dt = eveningDetailPool[idx];
        }

        stayingHooksAll.push(prefix + hk);
        stayingDetailsAll.push(prefix + dt);
      }
    }

    hooks[pt] = stayingHooksAll;
    details[pt] = stayingDetailsAll;
  }

  return {
    schemaVersion: 1,
    titles,
    hooks,
    details,
  };
}

function ensureDir(p) {
  fs.mkdirSync(p, { recursive: true });
}

function main() {
  ensureDir(OUT_DIR);

  for (const lang of LANGS) {
    const file = path.join(IOS_RESOURCES_DIR, `${lang}.lproj`, 'Localizable.strings');
    if (!fs.existsSync(file)) throw new Error(`Missing iOS Localizable.strings for lang=${lang}: ${file}`);
    const stringsMap = readStringsFile(file);
    const catalog = buildCatalogForLang(lang, stringsMap);

    const outFile = path.join(OUT_DIR, `${lang}.json`);
    fs.writeFileSync(outFile, JSON.stringify(catalog, null, 2) + '\n', 'utf8');
    process.stdout.write(`wrote ${path.relative(REPO_ROOT, outFile)}\n`);
  }
}

main();
