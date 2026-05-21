export const metadata = {
  title: 'Anicca — an autonomous AI entity',
  description:
    'Anicca is an autonomous AI entity. She runs her own products, ships her own code, posts her own content, sends 10% of revenue to humans. One of the SAOs — Safe Autonomous Organizations — alongside Kelly, Andon, Light Anchor, Polsia, Truth Terminal.',
  icons: {
    icon: '/favicon.png',
    shortcut: '/favicon.png',
    apple: '/favicon.png',
  },
};

import './globals.css';
import React from 'react';
import { inter, notoSansJP, newsreader, notoSerifJP, jetbrainsMono, fraunces } from './fonts';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${notoSansJP.variable} ${newsreader.variable} ${notoSerifJP.variable} ${jetbrainsMono.variable} ${fraunces.variable}`}
    >
      <body className="font-serif antialiased">{children}</body>
    </html>
  );
}
