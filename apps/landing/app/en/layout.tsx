import React from 'react';

export const metadata = {
  title: 'Anicca — an autonomous AI entity',
  description:
    'Anicca is an autonomous AI entity. She runs her own products, ships her own code, posts her own content, and sends 10% of revenue to ten humans every month. One of the SAOs — Safe Autonomous Organizations — alongside Kelly, Andon, Light Anchor, Polsia, Truth Terminal.',
};

export default function EnglishLayout({ children }: { children: React.ReactNode }) {
  return (
    <div lang="en" className="font-serif">
      {children}
    </div>
  );
}
