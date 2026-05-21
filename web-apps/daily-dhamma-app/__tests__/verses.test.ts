/**
 * T-3: verses.ts に 50個の verse が存在する
 * T-4: 全 verse に textJa が存在する（null/undefined なし）
 * T-5: Stay Present に日本語メッセージが存在する
 * T-6: getLocalizedVerse() が locale に応じて EN/JP を返す
 */
import {
  getAllVerses,
  getFreeVerses,
  getLocalizedVerse,
  stayPresentMessages,
  stayPresentMessagesJa,
} from '../data/verses';

describe('Verse count', () => {
  it('should have exactly 50 verses in total', () => {
    expect(getAllVerses()).toHaveLength(50);
  });

  it('should have exactly 10 free verses', () => {
    expect(getFreeVerses()).toHaveLength(10);
  });

  it('should have exactly 40 premium verses', () => {
    const premium = getAllVerses().filter(v => v.isPremium);
    expect(premium).toHaveLength(40);
  });
});

describe('Japanese localization', () => {
  it('all verses should have a non-empty textJa field', () => {
    getAllVerses().forEach(verse => {
      expect(verse.textJa).toBeDefined();
      expect(typeof verse.textJa).toBe('string');
      expect(verse.textJa.length).toBeGreaterThan(0);
    });
  });

  it('all verses should have a non-empty text (English) field', () => {
    getAllVerses().forEach(verse => {
      expect(verse.text).toBeDefined();
      expect(verse.text.length).toBeGreaterThan(0);
    });
  });

  it('stayPresentMessagesJa should have the same length as stayPresentMessages', () => {
    expect(stayPresentMessagesJa).toHaveLength(stayPresentMessages.length);
  });

  it('stayPresentMessagesJa should have no empty strings', () => {
    stayPresentMessagesJa.forEach(msg => {
      expect(msg.length).toBeGreaterThan(0);
    });
  });
});

describe('getLocalizedVerse', () => {
  it('should return English text when locale is en', () => {
    const verse = getLocalizedVerse(getAllVerses()[0], 'en');
    expect(verse).toBe(getAllVerses()[0].text);
  });

  it('should return Japanese text when locale is ja', () => {
    const verse = getLocalizedVerse(getAllVerses()[0], 'ja');
    expect(verse).toBe(getAllVerses()[0].textJa);
  });

  it('should return Japanese text when locale is ja-JP', () => {
    const verse = getLocalizedVerse(getAllVerses()[0], 'ja-JP');
    expect(verse).toBe(getAllVerses()[0].textJa);
  });

  it('should return Japanese text when locale is ja_JP', () => {
    const verse = getLocalizedVerse(getAllVerses()[0], 'ja_JP');
    expect(verse).toBe(getAllVerses()[0].textJa);
  });

  it('should return Japanese text when locale is JA (uppercase)', () => {
    const verse = getLocalizedVerse(getAllVerses()[0], 'JA');
    expect(verse).toBe(getAllVerses()[0].textJa);
  });

  it('should fall back to English when locale is unknown', () => {
    const verse = getLocalizedVerse(getAllVerses()[0], 'de');
    expect(verse).toBe(getAllVerses()[0].text);
  });
});

describe('Verse IDs', () => {
  it('all verse IDs should be unique', () => {
    const ids = getAllVerses().map(v => v.id);
    const uniqueIds = new Set(ids);
    expect(uniqueIds.size).toBe(ids.length);
  });
});
