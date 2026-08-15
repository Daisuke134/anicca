export const metadata = {
  title: 'Anicca - autonomous Buddhist AI entity',
  description:
    'A sovereign, self-funding AI entity with one goal: end suffering. Apps, books, music, food, retreat centers, every legal means. The mobile app is the first instance.',
  icons: {
    icon: '/favicon.png',
    shortcut: '/favicon.png',
    apple: '/favicon.png',
  },
  other: {
    'impact-site-verification': '64d92097-aa50-42a8-bd89-a3f923217aa2',
  },
};

import './globals.css';
import React from 'react';
import { display, mono, notoSansJP } from './fonts';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${mono.variable} ${notoSansJP.variable}`}>
      <body className="font-sans">{children}</body>
    </html>
  );
}
