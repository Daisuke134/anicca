import React from 'react';

export const metadata = {
  title: {
    absolute: 'アニッチャ — 苦しみを終わらせる自律型 AI',
  },
  description:
    '自分で稼いで、収支を全部公開して、10% を分配する。オープンソースの自律 AI。',
  alternates: {
    canonical: '/ja',
    languages: {
      en: '/en',
      ja: '/ja',
    },
  },
  openGraph: {
    title: 'アニッチャ — 苦しみを終わらせる自律型 AI',
    description:
      '稼いで、分配して、全部公開する。オープンソースの自律 AI。',
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
