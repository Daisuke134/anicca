import React from 'react';

export const metadata = {
  title: 'Anicca - 苦しみを終わらせる',
  description:
    'もしブッダがソフトウェアだったら？苦しみを終わらせる。一人ずつ。',
};

export default function JapaneseLayout({ children }: { children: React.ReactNode }) {
  return (
    <div lang="ja" className="font-noto-sans-jp">
      {children}
    </div>
  );
}
