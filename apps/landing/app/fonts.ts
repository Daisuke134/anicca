import {
  Instrument_Serif,
  IBM_Plex_Sans,
  IBM_Plex_Mono,
  Noto_Sans_JP,
  Noto_Serif_JP,
} from 'next/font/google';

// Display serif — editorial, calm, the visual anchor of the brand.
export const instrumentSerif = Instrument_Serif({
  subsets: ['latin'],
  weight: ['400'],
  style: ['normal', 'italic'],
  display: 'swap',
  variable: '--font-serif',
});

// Body sans — IBM Plex Sans. Distinctive, technical, slightly humanist;
// the slab terminals pair with Instrument Serif. Avoids generic Inter.
export const plexSans = IBM_Plex_Sans({
  subsets: ['latin'],
  weight: ['400', '500'],
  display: 'swap',
  variable: '--font-sans',
});

// Mono — for live numbers, timestamps, eyebrow labels.
export const plexMono = IBM_Plex_Mono({
  subsets: ['latin'],
  weight: ['400'],
  display: 'swap',
  variable: '--font-mono',
});

// Japanese sans body
export const notoSansJP = Noto_Sans_JP({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  display: 'swap',
  variable: '--font-noto-sans-jp',
});

// Japanese serif display — pairs with Instrument Serif for /ja headlines.
export const notoSerifJP = Noto_Serif_JP({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  display: 'swap',
  variable: '--font-noto-serif-jp',
});

// Backwards-compat aliases — older components import { inter, geist, geistMono }.
// Kept so nothing breaks while the redesign settles.
export const inter = plexSans;
export const geist = plexSans;
export const geistMono = plexMono;
