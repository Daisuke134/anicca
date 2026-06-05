'use client';

import { useState } from 'react';
import JsonLd from '@/components/JsonLd';
import { ManifestoHero, Section, Reveal } from '@/components/site/taste';

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
    const ctrl = new AbortController();
    try {
      const r = await fetch('/.netlify/functions/lead-magnet', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, lang: 'jp' }),
        signal: ctrl.signal,
      });
      setOptInState(r.ok ? 'sent' : 'error');
    } catch (err: unknown) {
      if (err instanceof Error && err.name !== 'AbortError') {
        if (typeof window !== 'undefined') console.warn('[/tegami:optIn] fetch failed:', err.message);
      }
      setOptInState('error');
    }
  }

  async function handleSubscribe() {
    const ctrl = new AbortController();
    try {
      const r = await fetch('/.netlify/functions/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lang: 'jp', mode: 'subscription', product: 'letter' }),
        signal: ctrl.signal,
      });
      const { url } = await r.json();
      if (url) window.location.href = url;
    } catch (err: unknown) {
      if (err instanceof Error && err.name !== 'AbortError') {
        if (typeof window !== 'undefined') console.warn('[/tegami:subscribe] checkout failed:', err.message);
      }
    }
  }

  const SubscribeButton = ({ label }: { label: string }) => (
    <button
      onClick={handleSubscribe}
      className="inline-flex items-center justify-center whitespace-nowrap font-medium transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] active:scale-[0.98] active:translate-y-px focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--gold))] rounded-pill px-6 py-3 bg-[hsl(var(--gold))] text-[#18181b] hover:brightness-95"
    >
      {label}
    </button>
  );

  return (
    <main className="min-h-screen bg-[hsl(var(--background))] font-serif">
      <JsonLd data={tegamiLd} />

      <ManifestoHero
        headline={
          <>
            毎朝、1通の短い手紙を。<br />
            無常をめぐる、<br />
            2分で読める瞑想。
          </>
        }
        subtext="365通、毎日1通ずつ。いつでも解約できます。"
        cta={
          <div className="flex flex-col items-start gap-3">
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-medium text-[hsl(var(--text-primary))]">¥980</span>
              <span className="text-base text-[hsl(var(--text-secondary))]">/ 月</span>
            </div>
            <p className="text-xs text-[hsl(var(--text-secondary))] -mt-1">最初の14日間は無料。カード登録不要。</p>
            <SubscribeButton label="手紙を受け取る →" />
            <p className="text-xs text-[hsl(var(--text-secondary))]">いつでも受信メールから解約可能 · 営業メールなし</p>
          </div>
        }
      />

      <Section>
        <Reveal>
          <p className="text-xs tracking-[0.3em] text-[hsl(var(--text-secondary))] text-center mb-8">手紙の中身</p>
        </Reveal>
        <ul className="mx-auto max-w-xl space-y-4 text-base leading-relaxed text-[hsl(var(--text-primary))]">
          {[
            '・毎朝1通、約350字の短い手紙。お茶と一緒に読める長さ。',
            '・各手紙: パーリ語1つ + 現代の言い換え + 今夜できる呼吸の実践。',
            '・テーラワーダ仏教の古い知恵 × 感情の脳科学。',
            '・90秒の法則。記憶の書き換え。観察するだけの実践。',
            '・全手紙アーカイブ閲覧可。何度でも戻ってこられる。',
          ].map((item, i) => (
            <Reveal key={i} delay={i * 0.06}>
              <li>{item}</li>
            </Reveal>
          ))}
        </ul>
      </Section>

      <Section>
        <Reveal>
          <p className="mx-auto max-w-xl text-center italic text-xl leading-relaxed text-[hsl(var(--text-primary))]">
            「感じないのではない。<br />感じて、それが去るのを見る」
          </p>
        </Reveal>
      </Section>

      <Section>
        <Reveal>
          <div className="mx-auto max-w-xl text-center">
            <p className="text-xs tracking-[0.3em] text-[hsl(var(--text-secondary))] mb-6">まだ迷っている方へ</p>
            <h2 className="text-xl font-light mb-4 text-[hsl(var(--text-primary))]">無料の3通の手紙をまずお送りします。</h2>
            <p className="text-sm text-[hsl(var(--text-secondary))] mb-6">3日間、朝に1通ずつ。それで終わり。（営業メールはありません）</p>
            {optInState === 'sent' ? (
              <p className="text-sm text-[hsl(var(--text-primary))]">受信箱を見てみてください。🌸</p>
            ) : (
              <form onSubmit={handleOptIn} className="flex flex-col sm:flex-row gap-2 max-w-sm mx-auto">
                <input
                  type="email"
                  required
                  name="email"
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
                  {optInState === 'sending' ? '送信中...' : '3通の手紙を受け取る'}
                </button>
              </form>
            )}
            {optInState === 'error' && <p className="text-xs text-red-700 mt-2">エラーが起きました。もう一度試してください。</p>}
          </div>
        </Reveal>
      </Section>

      <Section>
        <Reveal>
          <div className="flex flex-col items-center gap-3">
            <SubscribeButton label="月 ¥980 で購読する" />
            <p className="text-xs text-[hsl(var(--text-secondary))]">
              サブスク管理: <a href="/account" className="underline">aniccaai.com/account</a>
            </p>
          </div>
        </Reveal>
      </Section>

      <footer className="text-center text-xs text-[hsl(var(--text-secondary))] py-8">
        © Anicca · 教育・啓発目的のみ
      </footer>
    </main>
  );
}
