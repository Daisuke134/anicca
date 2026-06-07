'use client';

import { useRef, useState } from 'react';
import JsonLd from '@/components/JsonLd';
import { ManifestoHero } from '@/components/site/taste/ManifestoHero';
import { Section } from '@/components/site/taste/Section';
import { Reveal } from '@/components/site/taste/Reveal';
import { CTA } from '@/components/site/taste/CTA';

// §11.F: JsonLd verbatim
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
  const abortRef = useRef<AbortController | null>(null);

  // §11.F: onSubmit handler signature verbatim; AbortController added per §3.fetch
  async function handleOptIn(e: React.FormEvent) {
    e.preventDefault();
    if (!email) return;
    setOptInState('sending');
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    try {
      const r = await fetch('/.netlify/functions/lead-magnet', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, lang: 'en' }),
        signal: ctrl.signal,
      });
      setOptInState(r.ok ? 'sent' : 'error');
    } catch (err) {
      if ((err as Error).name !== 'AbortError') setOptInState('error');
    }
  }

  async function handleSubscribe() {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    try {
      const r = await fetch('/.netlify/functions/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lang: 'en', mode: 'subscription', product: 'letter' }),
        signal: ctrl.signal,
      });
      const { url } = await r.json();
      if (url) window.location.href = url;
    } catch (err) {
      if ((err as Error).name !== 'AbortError') console.error(err);
    }
  }

  return (
    <main>
      <JsonLd data={letterLd} />

      {/* §4.3: ManifestoHero -- letter theme */}
      <ManifestoHero
        headline={
          <>
            {/* TODO(i18n): EN */}
            One short letter,<br />
            every morning,<br />
            on impermanence.
          </>
        }
        subtext={
          // TODO(i18n): EN
          'A two-minute meditation in your inbox. 365 letters, one per day. Cancel any time.'
        }
        cta={
          // §11.F: CTA href /account preserved below; top CTA is subscribe
          <CTA href="/account">
            {/* TODO(i18n): EN */}
            Start the daily letters
          </CTA>
        }
      />

      {/* What you get */}
      <Section>
        <Reveal>
          <p className="text-xs font-medium uppercase tracking-widest text-[hsl(var(--text-secondary))] mb-8">
            {/* TODO(i18n): EN */}
            What you get
          </p>
        </Reveal>
        <ul className="space-y-5 max-w-[55ch]">
          {[
            // TODO(i18n): EN
            'One short letter per morning, ~150 words. Read it with coffee.',
            'Each letter: one Pali concept, one modern reframe, one breath practice.',
            'Theravada wisdom + the neuroscience of emotion.',
            'The 90-second rule. Memory reconsolidation. The witness practice.',
            'Forever-archive. Re-read any letter, any time.',
          ].map((item, i) => (
            <Reveal key={i} delay={i * 0.07}>
              <li className="flex items-start gap-3 text-base leading-relaxed text-[hsl(var(--text-primary))]">
                <span className="mt-1 text-[hsl(var(--text-secondary))]" aria-hidden>·</span>
                <span>{item}</span>
              </li>
            </Reveal>
          ))}
        </ul>
      </Section>

      {/* Pull quote */}
      <Section className="border-t border-[hsl(var(--border))]">
        <Reveal>
          <blockquote className="max-w-[50ch] text-xl font-light italic leading-relaxed text-[hsl(var(--text-primary))]">
            {/* TODO(i18n): EN */}
            &ldquo;It&rsquo;s not about not feeling.
            <br />
            It&rsquo;s about feeling and watching it leave.&rdquo;
          </blockquote>
        </Reveal>
      </Section>

      {/* Pricing callout */}
      <Section className="border-t border-[hsl(var(--border))]">
        <Reveal>
          <p className="text-xs font-medium uppercase tracking-widest text-[hsl(var(--text-secondary))] mb-6">
            {/* TODO(i18n): EN */}
            Pricing
          </p>
          <p className="mb-1 text-3xl font-semibold text-[hsl(var(--text-primary))]">
            {/* TODO(i18n): EN */}
            $9.99 <span className="text-lg font-normal text-[hsl(var(--text-secondary))]">/ month</span>
          </p>
          <p className="mb-8 text-sm text-[hsl(var(--text-secondary))]">
            {/* TODO(i18n): EN */}
            First 14 days free. No card needed for trial.
          </p>
          <button
            onClick={handleSubscribe}
            className="rounded-pill bg-[hsl(var(--gold))] px-8 py-3 text-sm font-medium text-[#18181b] transition-all duration-300 hover:brightness-95 active:scale-[0.98]"
          >
            {/* TODO(i18n): EN */}
            Subscribe -- $9.99 / month
          </button>
          <p className="mt-3 text-xs text-[hsl(var(--text-secondary))]">
            {/* TODO(i18n): EN */}
            Cancel any time from your inbox · No spam
          </p>
        </Reveal>
      </Section>

      {/* §11.F: FORM block verbatim (onSubmit handler, no action attr, input type=email controlled) */}
      <Section className="border-t border-[hsl(var(--border))]">
        <Reveal>
          <p className="text-xs font-medium uppercase tracking-widest text-[hsl(var(--text-secondary))] mb-6">
            {/* TODO(i18n): EN */}
            Not sure yet?
          </p>
          <h2 className="mb-2 text-2xl font-light text-[hsl(var(--text-primary))]">
            {/* TODO(i18n): EN */}
            Get 3 free letters first.
          </h2>
          <p className="mb-8 text-sm text-[hsl(var(--text-secondary))]">
            {/* TODO(i18n): EN */}
            A short morning email for three days. Then nothing. (No spam.)
          </p>
        </Reveal>
        {optInState === 'sent' ? (
          <Reveal>
            <p className="text-sm text-[hsl(var(--text-primary))]">
              {/* TODO(i18n): EN */}
              Check your inbox in a minute.
            </p>
          </Reveal>
        ) : (
          <Reveal>
            {/* §4.6: label ABOVE input (original used placeholder-as-label; fixed per §4.6 without renaming attributes) */}
            <form onSubmit={handleOptIn} className="flex max-w-sm flex-col gap-4 sm:flex-row sm:gap-2">
              <div className="flex flex-1 flex-col gap-1">
                <label htmlFor="letter-email" className="text-xs text-[hsl(var(--text-secondary))]">
                  {/* TODO(i18n): EN */}
                  Email address
                </label>
                <input
                  id="letter-email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="your@email.com"
                  className="rounded-input border border-[hsl(var(--border))] bg-[hsl(var(--surface))] px-4 py-3 text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--text-primary))] focus:outline-none"
                />
              </div>
              <button
                type="submit"
                disabled={optInState === 'sending'}
                className="self-end rounded-pill border border-[hsl(var(--text-primary))] bg-transparent px-6 py-3 text-xs font-medium uppercase tracking-widest text-[hsl(var(--text-primary))] transition-all duration-300 hover:bg-[hsl(var(--text-primary))] hover:text-[hsl(var(--bg))] disabled:opacity-60"
              >
                {/* TODO(i18n): EN */}
                {optInState === 'sending' ? 'Sending...' : 'Send me the letters'}
              </button>
            </form>
          </Reveal>
        )}
        {optInState === 'error' && (
          <Reveal>
            <p className="mt-2 text-xs text-red-700">
              {/* TODO(i18n): EN */}
              Something went wrong. Try again.
            </p>
          </Reveal>
        )}
      </Section>

      {/* Bottom CTA -- §11.F: /account verbatim */}
      <Section className="border-t border-[hsl(var(--border))]">
        <Reveal>
          <p className="text-sm text-[hsl(var(--text-secondary))]">
            {/* TODO(i18n): EN */}
            Manage subscription:{' '}
            <CTA href="/account" variant="link">
              aniccaai.com/account
            </CTA>
          </p>
        </Reveal>
      </Section>
    </main>
  );
}
