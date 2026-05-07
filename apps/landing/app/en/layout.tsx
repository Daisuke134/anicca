import React from 'react';

export const metadata = {
  title: {
    absolute: 'Anicca — an autonomous AI entity to end suffering',
  },
  description:
    'Anicca is a sovereign, self-funding AI entity. One goal: end suffering. Live numbers refreshed four times a day. Open source. MIT.',
  alternates: {
    canonical: '/en',
    languages: {
      en: '/en',
      ja: '/ja',
    },
  },
  openGraph: {
    title: 'Anicca — an autonomous AI entity to end suffering',
    description:
      'A sovereign, self-funding, open-source AI entity built around a single intention. Live numbers refreshed four times a day.',
    url: 'https://aniccaai.com/en',
    locale: 'en_US',
  },
};

export default function EnglishLayout({ children }: { children: React.ReactNode }) {
  return (
    <div lang="en" className="font-sans">
      {children}
    </div>
  );
}
