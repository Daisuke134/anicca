'use client';

import { useState } from 'react';
import JsonLd from '@/components/JsonLd';

const achanBookLd = {
  '@context': 'https://schema.org',
  '@type': 'Book',
  name: 'アニッチャ・リセット — 49の無常レッスン',
  url: 'https://aniccaai.com/achan',
  bookFormat: 'https://schema.org/EBook',
  inLanguage: 'ja',
  publisher: { '@type': 'Organization', name: 'Anicca', url: 'https://aniccaai.com' },
  description:
    '49の短章、各150字。各章は1つのパーリ語の概念、1つの現代的な言い換え、そして今夜できる1つの実践で構成。テーラワーダの智慧と感情の脳科学を融合。PDF・即時お届け・永久アクセス。',
  offers: {
    '@type': 'Offer',
    price: '1580',
    priceCurrency: 'JPY',
    availability: 'https://schema.org/InStock',
    url: 'https://aniccaai.com/achan',
  },
};

export default function AchanPage() {
  const [email, setEmail] = useState('');
  const [optInState, setOptInState] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle');

  async function handleOptIn(e: React.FormEvent) {
    e.preventDefault();
    if (!email) return;
    setOptInState('sending');
    try {
      const r = await fetch('/.netlify/functions/lead-magnet', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, lang: 'jp' }),
      });
      setOptInState(r.ok ? 'sent' : 'error');
    } catch {
      setOptInState('error');
    }
  }

  async function handleBuy() {
    const r = await fetch('/.netlify/functions/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lang: 'jp' }),
    });
    const { url } = await r.json();
    if (url) window.location.href = url;
  }

  return (
    <main className="min-h-screen bg-[#FBF7EF] text-[#2A2520] font-serif">
      <JsonLd data={achanBookLd} />
      <section className="max-w-xl mx-auto px-6 py-16 text-center">
        <p className="text-xs tracking-[0.3em] text-[#8B7355] mb-3">期間限定オファー</p>
        <div className="mx-auto w-44 h-60 bg-[#EFE5D2] rounded-sm shadow-lg mb-8 flex items-center justify-center">
          <div className="px-4">
            <p className="text-[10px] tracking-widest text-[#8B7355]">無常の本</p>
            <p className="text-2xl tracking-wide mt-1">アニッチャ</p>
            <p className="text-2xl tracking-wide">リセット</p>
            <p className="text-[10px] mt-3 italic">49の無常レッスン</p>
          </div>
        </div>
        <h1 className="text-3xl md:text-4xl font-light leading-snug mb-4">
          すべては移ろう。<br />
          あなたの怒りも、不安も、<br />
          この苦しみも。
        </h1>
        <div className="text-2xl mt-8 mb-2">
          <span className="line-through text-[#8B7355] mr-2 text-base">¥2,480</span>
          <span className="text-[#2A2520] font-medium">¥1,580</span>
        </div>
        <p className="text-xs text-[#8B7355] mb-6">期間限定の早割り価格</p>
        <button
          onClick={handleBuy}
          className="bg-[#2A2520] text-[#FBF7EF] px-10 py-4 text-sm tracking-[0.2em] uppercase hover:bg-[#3D3530] transition"
        >
          今すぐ購入 →
        </button>
        <p className="text-xs text-[#8B7355] mt-3">PDF · 即時お届け · 永久アクセス</p>
      </section>

      <section className="max-w-xl mx-auto px-6 py-12 border-t border-[#E5DCC9]">
        <p className="text-xs tracking-[0.3em] text-[#8B7355] text-center mb-6">本書の中身</p>
        <ul className="space-y-4 text-base leading-relaxed">
          <li>・49の短章、各150字 — 朝の一杯と一緒に読める長さ。</li>
          <li>・各章: パーリ語1つ + 現代の言い換え + 今夜できる小さな実践。</li>
          <li>・テーラワーダ仏教の古い知恵 × 感情の脳科学。</li>
          <li>・90秒の法則、記憶の書き換え、観察するだけの実践。</li>
          <li>・何度でも戻ってこられる、静かな本。</li>
        </ul>
      </section>

      <section className="max-w-xl mx-auto px-6 py-12 border-t border-[#E5DCC9] text-center">
        <p className="italic text-xl leading-relaxed text-[#2A2520]">
          「感じないのではない。<br />感じて、それが去るのを見る」
        </p>
      </section>

      <section className="max-w-xl mx-auto px-6 py-12 border-t border-[#E5DCC9] text-center">
        <p className="text-xs tracking-[0.3em] text-[#8B7355] mb-6">まだ買う気じゃない方へ</p>
        <h2 className="text-xl font-light mb-4">無料の3通の手紙をお送りします。</h2>
        <p className="text-sm text-[#8B7355] mb-6">3日間、朝に1通ずつ。それで終わり。（営業メールはありません）</p>
        {optInState === 'sent' ? (
          <p className="text-sm">受信箱を見てみてください。🌸</p>
        ) : (
          <form onSubmit={handleOptIn} className="flex flex-col sm:flex-row gap-2 max-w-sm mx-auto">
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              className="flex-1 bg-[#FBF7EF] border border-[#8B7355]/40 px-4 py-3 text-sm focus:outline-none focus:border-[#2A2520]"
            />
            <button
              type="submit"
              disabled={optInState === 'sending'}
              className="bg-transparent border border-[#2A2520] text-[#2A2520] px-6 py-3 text-xs tracking-[0.2em] hover:bg-[#2A2520] hover:text-[#FBF7EF] transition disabled:opacity-60"
            >
              {optInState === 'sending' ? '送信中…' : '3通の手紙を受け取る'}
            </button>
          </form>
        )}
        {optInState === 'error' && <p className="text-xs text-red-700 mt-2">エラーが起きました。もう一度試してください。</p>}
      </section>

      <section className="max-w-xl mx-auto px-6 py-16 text-center border-t border-[#E5DCC9]">
        <button
          onClick={handleBuy}
          className="bg-[#2A2520] text-[#FBF7EF] px-10 py-4 text-sm tracking-[0.2em] hover:bg-[#3D3530] transition"
        >
          今すぐ ¥1,580 で購入する
        </button>
      </section>

      <footer className="text-center text-xs text-[#8B7355] py-8">
        © Anicca · 教育・啓発目的のみ
      </footer>
    </main>
  );
}
