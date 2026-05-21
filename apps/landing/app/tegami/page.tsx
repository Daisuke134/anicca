'use client';

import { useState } from 'react';
import JsonLd from '@/components/JsonLd';

const tegamiLd = {
  '@context': 'https://schema.org',
  '@type': 'Product',
  name: '毎日のアニッチャの手紙',
  url: 'https://aniccaai.com/tegami',
  brand: { '@type': 'Brand', name: 'Anicca' },
  inLanguage: 'ja',
  description:
    '毎朝、1通の短い手紙を。無常をめぐる、2分で読める瞑想。365通、毎日1通ずつ。いつでも解約できます。',
  offers: {
    '@type': 'Offer',
    price: '980',
    priceCurrency: 'JPY',
    availability: 'https://schema.org/InStock',
    url: 'https://aniccaai.com/tegami',
  },
};

export default function TegamiPage() {
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

  async function handleSubscribe() {
    const r = await fetch('/.netlify/functions/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lang: 'jp', mode: 'subscription', product: 'letter' }),
    });
    const { url } = await r.json();
    if (url) window.location.href = url;
  }

  return (
    <main className="min-h-screen bg-[#FBF7EF] text-[#2A2520] font-serif">
      <JsonLd data={tegamiLd} />
      <section className="max-w-xl mx-auto px-6 py-16 text-center">
        <p className="text-xs tracking-[0.3em] text-[#8B7355] mb-3">無常の手紙</p>
        <h1 className="text-3xl md:text-4xl font-light leading-snug mb-6">
          毎朝、1通の短い手紙を。<br />
          無常をめぐる、<br />
          2分で読める瞑想。
        </h1>
        <p className="text-base leading-relaxed text-[#2A2520]/90 mb-8">
          365通、毎日1通ずつ。<br />
          いつでも解約できます。
        </p>
        <div className="text-2xl mt-8 mb-2">
          <span className="text-[#2A2520] font-medium">¥980</span>
          <span className="text-[#8B7355] text-base ml-1">/ 月</span>
        </div>
        <p className="text-xs text-[#8B7355] mb-6">最初の14日間は無料。カード登録不要。</p>
        <button
          onClick={handleSubscribe}
          className="bg-[#2A2520] text-[#FBF7EF] px-10 py-4 text-sm tracking-[0.2em] hover:bg-[#3D3530] transition"
        >
          手紙を受け取る →
        </button>
        <p className="text-xs text-[#8B7355] mt-3">いつでも受信メールから解約可能 · 営業メールなし</p>
      </section>

      <section className="max-w-xl mx-auto px-6 py-12 border-t border-[#E5DCC9]">
        <p className="text-xs tracking-[0.3em] text-[#8B7355] text-center mb-6">手紙の中身</p>
        <ul className="space-y-4 text-base leading-relaxed">
          <li>・毎朝1通、約350字の短い手紙。お茶と一緒に読める長さ。</li>
          <li>・各手紙: パーリ語1つ + 現代の言い換え + 今夜できる呼吸の実践。</li>
          <li>・テーラワーダ仏教の古い知恵 × 感情の脳科学。</li>
          <li>・90秒の法則。記憶の書き換え。観察するだけの実践。</li>
          <li>・全手紙アーカイブ閲覧可。何度でも戻ってこられる。</li>
        </ul>
      </section>

      <section className="max-w-xl mx-auto px-6 py-12 border-t border-[#E5DCC9] text-center">
        <p className="italic text-xl leading-relaxed text-[#2A2520]">
          「感じないのではない。<br />感じて、それが去るのを見る」
        </p>
      </section>

      <section className="max-w-xl mx-auto px-6 py-12 border-t border-[#E5DCC9] text-center">
        <p className="text-xs tracking-[0.3em] text-[#8B7355] mb-6">まだ迷っている方へ</p>
        <h2 className="text-xl font-light mb-4">無料の3通の手紙をまずお送りします。</h2>
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
          onClick={handleSubscribe}
          className="bg-[#2A2520] text-[#FBF7EF] px-10 py-4 text-sm tracking-[0.2em] hover:bg-[#3D3530] transition"
        >
          月 ¥980 で購読する
        </button>
        <p className="text-xs text-[#8B7355] mt-3">
          サブスク管理: <a href="/account" className="underline">aniccaai.com/account</a>
        </p>
      </section>

      <footer className="text-center text-xs text-[#8B7355] py-8">
        © Anicca · 教育・啓発目的のみ
      </footer>
    </main>
  );
}
