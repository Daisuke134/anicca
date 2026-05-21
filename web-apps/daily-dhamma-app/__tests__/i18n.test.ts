import { I18n } from 'i18n-js';
import * as fs from 'fs';
import * as path from 'path';

const en = require('../locales/en.json');
const ja = require('../locales/ja.json');

function flattenKeys(obj: Record<string, unknown>, prefix = ''): string[] {
  return Object.entries(obj).flatMap(([key, value]) => {
    const full = prefix ? `${prefix}.${key}` : key;
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      return flattenKeys(value as Record<string, unknown>, full);
    }
    return [full];
  });
}

function flattenValues(obj: Record<string, unknown>): string[] {
  return Object.entries(obj).flatMap(([, value]) => {
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      return flattenValues(value as Record<string, unknown>);
    }
    return typeof value === 'string' ? [value] : [];
  });
}

describe('i18n', () => {
  // T-L1: すべてのENキーがJAにも存在する
  test('T-L1: all en keys have ja translation', () => {
    const enKeys = flattenKeys(en).sort();
    const jaKeys = flattenKeys(ja).sort();
    expect(enKeys).toEqual(jaKeys);
  });

  // T-L2: ENロケールでt()がキーをそのまま返さない
  test('T-L2: en locale returns translated string, not raw key', () => {
    const i18n = new I18n({ en, ja });
    i18n.locale = 'en';
    i18n.enableFallback = true;
    i18n.defaultLocale = 'en';
    expect(i18n.t('onboarding.slide1.title')).toBe('Ancient wisdom for\nmodern minds');
    expect(i18n.t('paywall.title')).toBe('Deepen Your\nPractice');
    expect(i18n.t('settings.title')).toBe('Settings');
    expect(i18n.t('index.swipeHint')).toBe('Swipe up for next verse');
  });

  // T-L3: JAロケールで日本語が返る
  test('T-L3: ja locale returns japanese string', () => {
    const i18n = new I18n({ en, ja });
    i18n.locale = 'ja';
    i18n.enableFallback = true;
    i18n.defaultLocale = 'en';
    expect(i18n.t('onboarding.slide1.title')).toBe('現代の心に\n古代の智慧を');
    expect(i18n.t('paywall.title')).toBe('修行を\n深める');
    expect(i18n.t('settings.title')).toBe('設定');
    expect(i18n.t('index.swipeHint')).toBe('スワイプで次の法句経へ');
  });

  // T-L4: JAロケールでEN fallbackが動く
  test('T-L4: unknown locale falls back to en', () => {
    const i18n = new I18n({ en, ja });
    i18n.locale = 'de';
    i18n.enableFallback = true;
    i18n.defaultLocale = 'en';
    const result = i18n.t('onboarding.skip');
    expect(result).toBe('Skip');
  });

  // T-L5: 全キーに空文字・undefinedがない
  test('T-L5: no empty values in en or ja', () => {
    const enKeys = flattenKeys(en);
    const jaKeys = flattenKeys(ja);

    const i18nEn = new I18n({ en, ja });
    i18nEn.locale = 'en';
    i18nEn.enableFallback = false;

    const i18nJa = new I18n({ en, ja });
    i18nJa.locale = 'ja';
    i18nJa.enableFallback = false;

    for (const key of enKeys) {
      const val = i18nEn.t(key);
      expect(val).toBeTruthy();
      expect(typeof val).toBe('string');
    }
    for (const key of jaKeys) {
      const val = i18nJa.t(key);
      expect(val).toBeTruthy();
      expect(typeof val).toBe('string');
    }
  });

  // T-L6: jaに存在しないキーはenにfallbackする（[missing...]でない）
  test('T-L6: ja locale falls back to en when key missing in ja', () => {
    // jaにはないがenにはあるキーをシミュレート: en専用オブジェクトで検証
    const enOnly = { ...en, test_only: { key: 'fallback value' } };
    const i18n = new I18n({ en: enOnly, ja });
    i18n.locale = 'ja';
    i18n.enableFallback = true;
    i18n.defaultLocale = 'en';
    const result = i18n.t('test_only.key');
    expect(result).toBe('fallback value');
    expect(result).not.toMatch(/^\[missing/);
  });

  // T-L7: en.json のキー数が仕様一覧（66件）と一致
  test('T-L7: en.json key count matches spec inventory (66)', () => {
    const enKeys = flattenKeys(en);
    expect(enKeys.length).toBe(66);
  });

  // T-L8: 画面ファイルに本番ユーザー向けの hardcoded 英語文字列がない
  // NOTE: __DEV__ ブロック内の文字列（DEVELOPER, Test Morning Verse 等）は
  //       App Store ビルドに含まれないため i18n 対象外とする。
  test('T-L8: no hardcoded user-visible English strings in production screen sections', () => {
    const screenFiles = [
      path.resolve(__dirname, '../app/onboarding.tsx'),
      path.resolve(__dirname, '../app/paywall.tsx'),
      path.resolve(__dirname, '../app/index.tsx'),
      path.resolve(__dirname, '../app/settings.tsx'),
    ];

    // en.json の葉ノード値（翻訳すべき文字列）
    const enValues = flattenValues(en).filter(v =>
      v.length > 3 && // 短い文字列（"/month" 等）を除外
      !v.includes('\n') && // 複数行テキストを除外（JSXでは使用しない形式）
      !v.includes('https://') && // URLを除外
      !v.startsWith('$') // 変数を除外
    );

    for (const filePath of screenFiles) {
      const rawContent = fs.readFileSync(filePath, 'utf8');

      // __DEV__ ブロックを除去（App Store ビルドには含まれない）
      const content = rawContent.replace(
        /\{__DEV__\s*&&\s*\([\s\S]*?\)\s*\}\s*/g,
        ''
      );

      for (const value of enValues) {
        // JSX の Text 要素内に直書きされている場合のみ検出
        // パターン: >{value}< または >{value}\n
        const escaped = value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const directTextPattern = new RegExp(`>\\s*${escaped}\\s*<`);
        expect(content).not.toMatch(directTextPattern);
      }
    }
  });
});
