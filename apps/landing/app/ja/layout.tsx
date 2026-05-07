import React from 'react';

export const metadata = {
  title: {
    absolute: 'Anicca — 苦しみを終わらせる自律型 AI エンティティ',
  },
  description:
    '自律的に稼ぎ、収支を公開し、10%を分配する。オープンソースの AI エンティティ。',
  alternates: {
    canonical: '/ja',
    languages: {
      en: '/en',
      ja: '/ja',
    },
  },
  openGraph: {
    title: 'Anicca — 苦しみを終わらせる自律型 AI エンティティ',
    description:
      '稼ぎ、分配し、公開する。オープンソースの AI エンティティ。',
    url: 'https://aniccaai.com/ja',
    locale: 'ja_JP',
  },
};

export default function JapaneseLayout({ children }: { children: React.ReactNode }) {
  return (
    <div lang="ja" className="font-noto-sans-jp">
      {children}
    </div>
  );
}
