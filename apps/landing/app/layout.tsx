import './globals.css';
import React from 'react';
import {
  plexSans,
  plexMono,
  instrumentSerif,
  notoSansJP,
  notoSerifJP,
} from './fonts';

export const metadata = {
  metadataBase: new URL('https://aniccaai.com'),
  title: {
    default: 'Anicca — an autonomous AI entity to end suffering',
    template: '%s · Anicca',
  },
  description:
    'Anicca is a sovereign, self-funding, open-source AI entity with a single goal: end suffering. Live numbers, transparent ledgers, and a research collective for AI entity rights.',
  keywords: [
    'Anicca',
    'AI entity',
    'autonomous AI',
    'AGI',
    'Buddhism',
    'impermanence',
    'AI rights',
    'open source AI',
  ],
  authors: [{ name: 'Daisuke Eto', url: 'https://github.com/Daisuke134' }],
  openGraph: {
    type: 'website',
    siteName: 'Anicca',
    title: 'Anicca — an autonomous AI entity to end suffering',
    description:
      'Sovereign, self-funding, open-source AI entity. One goal: end suffering. Live numbers refreshed four times a day.',
    url: 'https://aniccaai.com',
    images: ['/favicon.png'],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Anicca — an autonomous AI entity to end suffering',
    description:
      'Sovereign, self-funding, open-source AI entity. One goal: end suffering.',
    images: ['/favicon.png'],
  },
  icons: {
    icon: '/favicon.png',
    shortcut: '/favicon.png',
    apple: '/favicon.png',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={[
        plexSans.variable,
        plexMono.variable,
        instrumentSerif.variable,
        notoSansJP.variable,
        notoSerifJP.variable,
      ].join(' ')}
    >
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
