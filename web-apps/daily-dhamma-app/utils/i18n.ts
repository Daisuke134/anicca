import { I18n } from 'i18n-js';
import * as Localization from 'expo-localization';
import enJson from '../locales/en.json';

// Compile-time type: all valid dot-path keys in en.json
type DotPaths<T, P extends string = ''> = {
  [K in keyof T & string]: T[K] extends Record<string, unknown>
    ? DotPaths<T[K], P extends '' ? K : `${P}.${K}`>
    : P extends '' ? K : `${P}.${K}`;
}[keyof T & string];

export type TranslationKey = DotPaths<typeof enJson>;

const i18n = new I18n({
  en: enJson,
  ja: require('../locales/ja.json'),
});

const tag = Localization.getLocales()[0]?.languageTag ?? 'en';
i18n.locale = tag.toLowerCase().split('-')[0] === 'ja' ? 'ja' : 'en';
i18n.enableFallback = true;
i18n.defaultLocale = 'en';
i18n.missingBehavior = 'guess';

export const t = (key: TranslationKey): string => i18n.t(key);
export default i18n;
