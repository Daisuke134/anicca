'use client';

import { useState } from 'react';
import JsonLd from '@/components/JsonLd';

const letterLd = {
  '@context': 'https://schema.org',
  '@type': 'Product',
  name: 'The Daily Anicca Letter',
  url: 'https://aniccaai.com/letter',
  brand: { '@type': 'Brand', name: 'Anicca' },
  description:
    'One short letter every morning on impermanence. A two-minute meditation in your inbox. 365 letters, one per day. Each letter pairs one Pali concept with a modern reframe and one breath practice. First 14 days free, cancel any time.',
  offers: {
    '@type': 'Offer',
    price: '9.99',
    priceCurrency: 'USD',
    availability: 'https://schema.org/InStock',
    url: 'https://aniccaai.com/letter',
  },
};

export default function LetterPage() {
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
        body: JSON.stringify({ email, lang: 'en' }),
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
      body: JSON.stringify({ lang: 'en', mode: 'subscription', product: 'letter' }),
    });
    const { url } = await r.json();
    if (url) window.location.href = url;
  }

  return (
    <main className="min-h-screen bg-[#FBF7EF] text-[#2A2520] font-serif">
      <JsonLd data={letterLd} />
      <section className="max-w-xl mx-auto px-6 py-16 text-center">
        <p className="text-xs uppercase tracking-[0.3em] text-[#8B7355] mb-3">Daily Anicca Letter</p>
        <h1 className="text-3xl md:text-4xl font-light leading-snug mb-6">
          One short letter,<br />
          every morning,<br />
          on impermanence.
        </h1>
        <p className="text-base leading-relaxed text-[#2A2520]/90 mb-8">
          A two-minute meditation in your inbox.<br />
          365 letters. One a day. Cancel any time.
        </p>
        <div className="text-2xl mt-8 mb-2">
          <span className="text-[#2A2520] font-medium">$9.99</span>
          <span className="text-[#8B7355] text-base ml-1">/ month</span>
        </div>
        <p className="text-xs text-[#8B7355] mb-6">First 14 days free. No card needed for trial.</p>
        <button
          onClick={handleSubscribe}
          className="bg-[#2A2520] text-[#FBF7EF] px-10 py-4 text-sm tracking-[0.2em] uppercase hover:bg-[#3D3530] transition"
        >
          Start the daily letters →
        </button>
        <p className="text-xs text-[#8B7355] mt-3">Cancel any time from your inbox · No spam</p>
      </section>

      <section className="max-w-xl mx-auto px-6 py-12 border-t border-[#E5DCC9]">
        <p className="text-xs uppercase tracking-[0.3em] text-[#8B7355] text-center mb-6">What you get</p>
        <ul className="space-y-4 text-base leading-relaxed">
          <li>· One short letter per morning, ~150 words. Read it with coffee.</li>
          <li>· Each letter: one Pali concept, one modern reframe, one breath practice.</li>
          <li>· Theravada wisdom + the neuroscience of emotion.</li>
          <li>· The 90-second rule. Memory reconsolidation. The witness practice.</li>
          <li>· Forever-archive. Re-read any letter, any time.</li>
        </ul>
      </section>

      <section className="max-w-xl mx-auto px-6 py-12 border-t border-[#E5DCC9] text-center">
        <p className="italic text-xl leading-relaxed text-[#2A2520]">
          "It's not about not feeling.<br />It's about feeling and watching it leave."
        </p>
      </section>

      <section className="max-w-xl mx-auto px-6 py-12 border-t border-[#E5DCC9] text-center">
        <p className="text-xs uppercase tracking-[0.3em] text-[#8B7355] mb-6">Not sure yet?</p>
        <h2 className="text-xl font-light mb-4">Get 3 free letters first.</h2>
        <p className="text-sm text-[#8B7355] mb-6">A short morning email for three days. Then nothing. (No spam.)</p>
        {optInState === 'sent' ? (
          <p className="text-sm">Check your inbox in a minute. 🌿</p>
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
              className="bg-transparent border border-[#2A2520] text-[#2A2520] px-6 py-3 text-xs tracking-[0.2em] uppercase hover:bg-[#2A2520] hover:text-[#FBF7EF] transition disabled:opacity-60"
            >
              {optInState === 'sending' ? 'Sending…' : 'Send me the letters'}
            </button>
          </form>
        )}
        {optInState === 'error' && <p className="text-xs text-red-700 mt-2">Something went wrong. Try again.</p>}
      </section>

      <section className="max-w-xl mx-auto px-6 py-16 text-center border-t border-[#E5DCC9]">
        <button
          onClick={handleSubscribe}
          className="bg-[#2A2520] text-[#FBF7EF] px-10 py-4 text-sm tracking-[0.2em] uppercase hover:bg-[#3D3530] transition"
        >
          Subscribe — $9.99 / month
        </button>
        <p className="text-xs text-[#8B7355] mt-3">
          Manage subscription: <a href="/account" className="underline">aniccaai.com/account</a>
        </p>
      </section>

      <footer className="text-center text-xs text-[#8B7355] py-8">
        © Anicca · For educational and inspirational purposes only.
      </footer>
    </main>
  );
}
