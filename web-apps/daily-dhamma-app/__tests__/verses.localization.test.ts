import { getLocalizedSource, getLocalizedChapter } from '../data/verses';

describe('getLocalizedSource', () => {
  const jaLocale = 'ja';
  const enLocale = 'en';
  const enUSLocale = 'en-US';
  const jaJPLocale = 'ja-JP';

  // 正常系: 全5ソースが ja で日本語訳になる
  test('Dhammapada → 法句経 in ja', () => {
    expect(getLocalizedSource('Dhammapada', jaLocale)).toBe('法句経');
  });

  test('Buddha → ブッダ in ja', () => {
    expect(getLocalizedSource('Buddha', jaLocale)).toBe('ブッダ');
  });

  test('Khaggavisana Sutta → 犀角経 in ja', () => {
    expect(getLocalizedSource('Khaggavisana Sutta', jaLocale)).toBe('犀角経');
  });

  test('Majjhima Nikaya → 中部経典 in ja', () => {
    expect(getLocalizedSource('Majjhima Nikaya', jaLocale)).toBe('中部経典');
  });

  test('Metta Sutta → 慈悲経 in ja', () => {
    expect(getLocalizedSource('Metta Sutta', jaLocale)).toBe('慈悲経');
  });

  // 非 ja locale は原文を返す
  test('Dhammapada stays Dhammapada in en', () => {
    expect(getLocalizedSource('Dhammapada', enLocale)).toBe('Dhammapada');
  });

  test('Dhammapada stays Dhammapada in en-US', () => {
    expect(getLocalizedSource('Dhammapada', enUSLocale)).toBe('Dhammapada');
  });

  // ja-JP でも正しく動作する (locale を先頭言語コードに正規化)
  test('Dhammapada → 法句経 in ja-JP', () => {
    expect(getLocalizedSource('Dhammapada', jaJPLocale)).toBe('法句経');
  });

  // 未知 source は ja でも原文 fallback
  test('unknown source returns original in ja', () => {
    expect(getLocalizedSource('Unknown Source', jaLocale)).toBe('Unknown Source');
  });

  test('unknown source returns original in en', () => {
    expect(getLocalizedSource('Unknown Source', enLocale)).toBe('Unknown Source');
  });
});

describe('getLocalizedChapter', () => {
  // en: "Chapter N (Name), Verse N" 形式
  test('en: returns chapter and verseNumber joined', () => {
    expect(getLocalizedChapter('Chapter 1 (Yamaka Vagga)', 'Verse 1-2', 'en')).toBe(
      'Chapter 1 (Yamaka Vagga), Verse 1-2'
    );
  });

  test('en: returns chapter only when verseNumber is empty', () => {
    expect(getLocalizedChapter('Chapter 1 (Yamaka Vagga)', '', 'en')).toBe(
      'Chapter 1 (Yamaka Vagga)'
    );
  });

  // ja: "Chapter N (Name), Verse N" → "第N章、第N偈"
  test('ja: converts Chapter 1 Verse 5 to 第1章、第5偈', () => {
    expect(getLocalizedChapter('Chapter 1 (Yamaka Vagga)', 'Verse 5', 'ja')).toBe('第1章、第5偈');
  });

  test('ja: converts Chapter 17 Verse 223 to 第17章、第223偈', () => {
    expect(getLocalizedChapter('Chapter 17 (Kodha Vagga)', 'Verse 223', 'ja')).toBe('第17章、第223偈');
  });

  test('ja: converts range verse Verse 1-2 to 第1章、第1-2偈', () => {
    expect(getLocalizedChapter('Chapter 1 (Yamaka Vagga)', 'Verse 1-2', 'ja')).toBe('第1章、第1-2偈');
  });

  test('ja: returns chapter only (localized) when verseNumber is empty', () => {
    expect(getLocalizedChapter('Chapter 1 (Yamaka Vagga)', '', 'ja')).toBe('第1章');
  });

  // ja-JP でも動作
  test('ja-JP: localizes chapter correctly', () => {
    expect(getLocalizedChapter('Chapter 5 (Bala Vagga)', 'Verse 67', 'ja-JP')).toBe('第5章、第67偈');
  });

  // 非 Chapter N (...) 形式の chapter は原文のまま
  test('ja: non-standard chapter format returned as-is', () => {
    expect(getLocalizedChapter('Prologue', 'Verse 1', 'ja')).toBe('Prologue、第1偈');
  });
});
