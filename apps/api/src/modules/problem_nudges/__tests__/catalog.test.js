import { describe, it, expect } from 'vitest';
import { loadProblemNudgeCatalog } from '../catalogLoader.js';

const LANGS = ['en', 'ja', 'es', 'fr', 'de', 'pt-BR'];
const PROBLEMS = [
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

function sleepKw(lang) {
  return {
    en: ['sleep', 'bed', 'rest', 'dream', 'eyes', 'midnight', '1 am'],
    ja: ['寝', '睡眠', 'ベッド', '布団', '休', '0時', '1時'],
    es: ['dorm', 'cama', 'descans', 'sueñ', 'medianoche', '1 am'],
    fr: ['dorm', 'lit', 'repos', 'sommeil', 'minuit', '1h'],
    de: ['schlaf', 'bett', 'ruhe', 'mitternacht', '1 uhr'],
    'pt-BR': ['dorm', 'cama', 'descans', 'sonh', 'meia-noite', '1h'],
  }[lang] || ['sleep'];
}

describe('problem nudges catalog', () => {
  it('has expected schema and sizes for all languages', () => {
    for (const lang of LANGS) {
      const c = loadProblemNudgeCatalog(lang);
      expect(c.schemaVersion).toBe(1);
      expect(c.titles).toBeTruthy();
      expect(c.hooks).toBeTruthy();
      expect(c.details).toBeTruthy();

      for (const pt of PROBLEMS) {
        expect(typeof c.titles[pt]).toBe('string');
        const hooks = c.hooks[pt];
        const details = c.details[pt];
        expect(Array.isArray(hooks)).toBe(true);
        expect(Array.isArray(details)).toBe(true);
        if (pt === 'staying_up_late') {
          expect(hooks).toHaveLength(70);
          expect(details).toHaveLength(70);
        } else {
          expect(hooks).toHaveLength(42);
          expect(details).toHaveLength(42);
        }
      }
    }
  });

  it('ensures hook/detail are unique per problem type within the catalog window', () => {
    for (const lang of LANGS) {
      const c = loadProblemNudgeCatalog(lang);
      for (const pt of PROBLEMS) {
        const hooks = c.hooks[pt];
        const details = c.details[pt];
        expect(new Set(hooks).size).toBe(hooks.length);
        expect(new Set(details).size).toBe(details.length);
      }
    }
  });

  it('staying_up_late deep-night (00:00/01:00) slots look sleep-focused', () => {
    // staying_up_late has 5 slots/day; slotIndex 3/4 => indices day*5+3, day*5+4
    for (const lang of LANGS) {
      const c = loadProblemNudgeCatalog(lang);
      const hooks = c.hooks.staying_up_late;
      const details = c.details.staying_up_late;
      const kw = sleepKw(lang).map(s => s.toLowerCase());
      for (let day = 0; day < 14; day++) {
        for (const slot of [3, 4]) {
          const idx = day * 5 + slot;
          const h = String(hooks[idx] || '').toLowerCase();
          const d = String(details[idx] || '').toLowerCase();
          const hit = kw.some(k => h.includes(k) || d.includes(k));
          expect(hit).toBe(true);
        }
      }
    }
  });
});

