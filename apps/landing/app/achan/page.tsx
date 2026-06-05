'use client';

import { useState } from 'react';
import JsonLd from '@/components/JsonLd';
import { ManifestoHero, Section, Reveal } from '@/components/site/taste';

const achanBookLd = {
  '@context': 'https://schema.org',
  '@type': 'Book',
  name: 'アニッチャ・リセット - 49の無常レッスン',
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
    const ctrl = new AbortController();
    try {
      const r = await fetch('/.netlify/functions/lead-magnet', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, lang: 'jp' }),
        signal: ctrl.signal,
      });
      setOptInState(r.ok ? 'sent' : 'error');
    } catch (e: unknown) {
      if (e instanceof Error && e.name !== 'AbortError') {
        if (typeof window !== 'undefined') console.warn('[/achan:optIn] fetch failed:', e.message);
      }
      setOptInState('error');
    }
  }

  async function handleBuy() {
    const ctrl = new AbortController();
    try {
      const r = await fetch('/.netlify/functions/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lang: 'jp' }),
        signal: ctrl.signal,
      });
      const { url } = await r.json();
      if (url) window.location.href = url;
    } catch (e: unknown) {
      if (e instanceof Error && e.name !== 'AbortError') {
        if (typeof window !== 'undefined') console.warn('[/achan:buy] checkout failed:', e.message);
      }
    }
  }

  // Buy CTA: button (async fetch, not a plain href) with taste §4.5 gold + #18181b text
  const BuyButton = ({ label }: { label: string }) => (
    <button
      onClick={handleBuy}
      className="inline-flex items-center justify-center whitespace-nowrap font-medium transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] active:scale-[0.98] active:translate-y-px focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--gold))] rounded-pill px-6 py-3 bg-[hsl(var(--gold))] text-[#18181b] hover:brightness-95"
    >
      {label}
    </button>
  );

  return (
    <main className="min-h-screen bg-[hsl(var(--background))] font-serif">
      <JsonLd data={achanBookLd} />

      {/* Hero: manifesto-style - book-sales message IS the design */}
      <ManifestoHero
        headline={
          <>
            すべては移ろう。<br />
            あなたの怒りも、不安も、<br />
            この苦しみも。
          </>
        }
        subtext="49の短章、各150字。テーラワーダの智慧と感情の脳科学を、静かに読める本。"
        cta={
          <div className="flex flex-col items-start gap-3">
            <div className="flex items-baseline gap-2">
              <span className="line-through text-sm text-[hsl(var(--text-secondary))]">¥2,480</span>
              <span className="text-2xl font-medium text-[hsl(var(--text-primary))]">¥1,580</span>
            </div>
            <p className="text-xs text-[hsl(var(--text-secondary))] -mt-1">期間限定の早割り価格</p>
            <BuyButton label="今すぐ購入 →" />
            <p className="text-xs text-[hsl(var(--text-secondary))]">PDF · 即時お届け · 永久アクセス</p>
          </div>
        }
      />

      {/* Contents section */}
      <Section>
        <Reveal>
          <p className="text-xs tracking-[0.3em] text-[hsl(var(--text-secondary))] text-center mb-8 uppercase">本書の中身</p>
        </Reveal>
        <ul className="mx-auto max-w-xl space-y-4 text-base leading-relaxed text-[hsl(var(--text-primary))]">
          {[
            '・49の短章、各150字 - 朝の一杯と一緒に読める長さ。',
            '・各章: パーリ語1つ + 現代の言い換え + 今夜できる小さな実践。',
            '・テーラワーダ仏教の古い知恵 × 感情の脳科学。',
            '・90秒の法則、記憶の書き換え、観察するだけの実践。',
            '・何度でも戻ってこられる、静かな本。',
          ].map((item, i) => (
            <Reveal key={i} delay={i * 0.06}>
              <li>{item}</li>
            </Reveal>
          ))}
        </ul>
      </Section>

      {/* Pull-quote */}
      <Section>
        <Reveal>
          <p className="mx-auto max-w-xl text-center italic text-xl leading-relaxed text-[hsl(var(--text-primary))]">
            「感じないのではない。<br />感じて、それが去るのを見る」
          </p>
        </Reveal>
      </Section>

      {/* Email opt-in */}
      <Section>
        <Reveal>
          <div className="mx-auto max-w-xl text-center">
            <p className="text-xs tracking-[0.3em] text-[hsl(var(--text-secondary))] mb-6 uppercase">まだ買う気じゃない方へ</p>
            <h2 className="text-xl font-light mb-4 text-[hsl(var(--text-primary))]">無料の3通の手紙をお送りします。</h2>
            <p className="text-sm text-[hsl(var(--text-secondary))] mb-6">3日間、朝に1通ずつ。それで終わり。（営業メールはありません）</p>
            {optInState === 'sent' ? (
              <p className="text-sm text-[hsl(var(--text-primary))]">受信箱を見てみてください。🌸</p>
            ) : (
              <form onSubmit={handleOptIn} className="flex flex-col sm:flex-row gap-2 max-w-sm mx-auto">
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="your@email.com"
                  className="flex-1 rounded-input bg-[hsl(var(--background))] border border-[hsl(var(--text-secondary))]/40 px-4 py-3 text-sm focus:outline-none focus:border-[hsl(var(--text-primary))] text-[hsl(var(--text-primary))]"
                />
                <button
                  type="submit"
                  disabled={optInState === 'sending'}
                  className="rounded-pill bg-transparent border border-[hsl(var(--text-primary))] text-[hsl(var(--text-primary))] px-6 py-3 text-xs tracking-[0.2em] hover:bg-[hsl(var(--text-primary))] hover:text-[hsl(var(--background))] transition disabled:opacity-60"
                >
                  {optInState === 'sending' ? '送信中…' : '3通の手紙を受け取る'}
                </button>
              </form>
            )}
            {optInState === 'error' && (
              <p className="text-xs text-red-700 mt-2">エラーが起きました。もう一度試してください。</p>
            )}
          </div>
        </Reveal>
      </Section>

      {/* Final CTA */}
      <Section>
        <Reveal>
          <div className="flex justify-center">
            <BuyButton label="今すぐ ¥1,580 で購入する" />
          </div>
        </Reveal>
      </Section>

      <footer className="text-center text-xs text-[hsl(var(--text-secondary))] py-8">
        © Anicca · 教育・啓発目的のみ
      </footer>
    </main>
  );
}
