import { Inter, Noto_Sans_JP, Newsreader, Noto_Serif_JP, JetBrains_Mono, Fraunces } from 'next/font/google';

export const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
});

export const notoSansJP = Noto_Sans_JP({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  display: 'swap',
  variable: '--font-noto-sans-jp',
});

// Editorial body & display.
export const newsreader = Newsreader({
  subsets: ['latin'],
  weight: ['300', '400', '500', '600', '700', '800'],
  style: ['normal', 'italic'],
  display: 'swap',
  variable: '--font-newsreader',
});

// JP serif counterpart.
export const notoSerifJP = Noto_Serif_JP({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700', '900'],
  display: 'swap',
  variable: '--font-noto-serif-jp',
});

// Tabular metrics.
export const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['400', '500', '700'],
  display: 'swap',
  variable: '--font-jetbrains',
});

// Soft, optical-sized variable serif for the affirmation app landing.
// Variable font — `axes` config drops the `weight` setting per Next.js rules.
export const fraunces = Fraunces({
  subsets: ['latin'],
  style: ['normal', 'italic'],
  display: 'swap',
  axes: ['SOFT', 'opsz'],
  variable: '--font-fraunces',
});
