import { Outfit, JetBrains_Mono, Noto_Sans_JP } from 'next/font/google';

// §4.1 sans-display 既定 (Outfit)。§3.F: Geist は Next 14.2.5 の next/font/google 在庫に
// 無いため、新規 npm 依存を増やさず承認済み Outfit + JetBrains Mono を採用。
export const display = Outfit({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-display',
});

export const mono = JetBrains_Mono({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-mono',
});

export const notoSansJP = Noto_Sans_JP({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  display: 'swap',
  variable: '--font-noto-sans-jp',
});
