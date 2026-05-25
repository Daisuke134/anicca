import { describe, it, expect } from 'vitest';
import {
  loadAffirmationCatalog,
  affirmationText,
  appName,
  allQuoteIds,
} from '../affirmationsLoader.js';

const CATALOG_LANGS = ['en', 'ja', 'es'];

describe('affirmation catalogs', () => {
  it('each localized catalog has 200 quotes q001-q200', () => {
    for (const lang of CATALOG_LANGS) {
      const c = loadAffirmationCatalog(lang);
      const ids = Object.keys(c.quotes);
      expect(ids.length).toBe(200);
      expect(ids).toContain('q001');
      expect(ids).toContain('q200');
      expect(c.schemaVersion).toBe(1);
    }
  });

  it('id sets are identical across en/ja/es', () => {
    const base = Object.keys(loadAffirmationCatalog('en').quotes).sort().join(',');
    for (const lang of ['ja', 'es']) {
      const ids = Object.keys(loadAffirmationCatalog(lang).quotes).sort().join(',');
      expect(ids).toBe(base);
    }
  });

  it('affirmationText returns localized body per language', () => {
    expect(affirmationText('q001', 'en')).toMatch(/becoming/i);
    expect(affirmationText('q001', 'ja')).toContain('本当の自分');
    expect(affirmationText('q001', 'es')).toMatch(/convirtiendo/i);
  });

  it('falls back to English text for languages without a catalog', () => {
    expect(affirmationText('q001', 'fr')).toBe(affirmationText('q001', 'en'));
    expect(affirmationText('q001', 'de')).toBe(affirmationText('q001', 'en'));
  });

  it('appName is the localized brand title used as notification TITLE', () => {
    expect(appName('en')).toBe('Anicca');
    expect(appName('ja')).toBe('アニッチャ');
    expect(appName('es')).toBe('Anicca');
    expect(appName('fr')).toBe('Anicca');
    expect(appName(undefined)).toBe('Anicca');
  });

  it('unknown quote id returns null (graceful, no throw)', () => {
    expect(affirmationText('q999', 'en')).toBeNull();
    expect(affirmationText('q999', 'ja')).toBeNull();
  });

  it('allQuoteIds returns the 200 stable ids', () => {
    expect(allQuoteIds().length).toBe(200);
  });
});
