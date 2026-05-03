'use client';

import { useState } from 'react';

export default function MonkPage() {
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

  async function handleBuy() {
    const r = await fetch('/.netlify/functions/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lang: 'en' }),
    });
    const { url } = await r.json();
    if (url) window.location.href = url;
  }

  return (
    <main className="min-h-screen bg-[#FBF7EF] text-[#2A2520] font-serif">
      <section className="max-w-xl mx-auto px-6 py-16 text-center">
        <p className="text-xs uppercase tracking-[0.3em] text-[#8B7355] mb-3">Limited-Time Offer</p>
        <div className="mx-auto w-44 h-60 bg-[#EFE5D2] rounded-sm shadow-lg mb-8 flex items-center justify-center text-[#2A2520]">
          <div className="px-4">
            <p className="text-[10px] tracking-widest text-[#8B7355]">THE</p>
            <p className="text-2xl tracking-wide mt-1">ANICCA</p>
            <p className="text-2xl tracking-wide">RESET</p>
            <p className="text-[10px] mt-3 italic">49 lessons in impermanence</p>
          </div>
        </div>
        <h1 className="text-3xl md:text-4xl font-light leading-snug mb-4">
          Everything passes.<br />
          Your anger. Your anxiety.<br />
          Your heartbreak too.
        </h1>
        <div className="text-2xl mt-8 mb-2">
          <span className="line-through text-[#8B7355] mr-2 text-base">$16.99</span>
          <span className="text-[#2A2520] font-medium">$10.99</span>
        </div>
        <p className="text-xs text-[#8B7355] mb-6">Limited-time release pricing</p>
        <button
          onClick={handleBuy}
          className="bg-[#2A2520] text-[#FBF7EF] px-10 py-4 text-sm tracking-[0.2em] uppercase hover:bg-[#3D3530] transition"
        >
          Get Instant Access →
        </button>
        <p className="text-xs text-[#8B7355] mt-3">PDF · instant delivery · lifetime access</p>
      </section>

      <section className="max-w-xl mx-auto px-6 py-12 border-t border-[#E5DCC9]">
        <p className="text-xs uppercase tracking-[0.3em] text-[#8B7355] text-center mb-6">What's inside</p>
        <ul className="space-y-4 text-base leading-relaxed">
          <li>· 49 short chapters, ~150 words each — read one at breakfast.</li>
          <li>· Each chapter: one Pali term, one modern reframe, one practice you can do tonight.</li>
          <li>· Ancient Theravada wisdom meets neuroscience of emotion.</li>
          <li>· The 90-second rule. Memory reconsolidation. The witness practice.</li>
          <li>· No fluff. No filler. Calm guidance you'll return to forever.</li>
        </ul>
      </section>

      <section className="max-w-xl mx-auto px-6 py-12 border-t border-[#E5DCC9] text-center">
        <p className="italic text-xl leading-relaxed text-[#2A2520]">
          "It's not about not feeling.<br />It's about feeling and watching it leave."
        </p>
      </section>

      <section className="max-w-xl mx-auto px-6 py-12 border-t border-[#E5DCC9] text-center">
        <p className="text-xs uppercase tracking-[0.3em] text-[#8B7355] mb-6">Not ready?</p>
        <h2 className="text-xl font-light mb-4">Get the free 3-day letter on impermanence.</h2>
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
          onClick={handleBuy}
          className="bg-[#2A2520] text-[#FBF7EF] px-10 py-4 text-sm tracking-[0.2em] uppercase hover:bg-[#3D3530] transition"
        >
          Get the book — $10.99
        </button>
      </section>

      <footer className="text-center text-xs text-[#8B7355] py-8">
        © Anicca · For educational and inspirational purposes only.
      </footer>
    </main>
  );
}
