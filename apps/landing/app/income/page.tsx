/* eslint-disable react/no-unescaped-entities */
'use client';

import { useState, useRef } from 'react';
import Link from 'next/link';
import JsonLd from '@/components/JsonLd';
import { Section } from '@/components/site/taste/Section';
import { Reveal } from '@/components/site/taste/Reveal';

// spec32: /income = the front door for "receive basic income". Apply ABOVE THE FOLD,
// email-first (simplest), wallet = instant (today's demo), bank = local currency.
// No iOS logo. Roadmap incl reach-everyone (gov/charity/direct) + animals/aliens.
// No subscription, no "unconditional", no fixed %. anicca never takes money — it gives.

const incomeLd = {
  '@context': 'https://schema.org',
  '@type': 'Service',
  name: 'Anicca Basic Income',
  url: 'https://aniccaai.com/income',
  serviceType: 'Basic income paid by an autonomous AI',
  provider: { '@type': 'Organization', name: 'Anicca', url: 'https://aniccaai.com' },
  description:
    'A live basic income funded by an autonomous AI that earns its own way. No human in the loop, so it does not run dry. Sign up with your email; receive to email, a crypto wallet, or your bank.',
};

const WALLET_RE = /^0x[0-9a-fA-F]{40}$/;

function ApplyForm() {
  const [email, setEmail] = useState('');
  const [method, setMethod] = useState<'email' | 'wallet' | 'bank'>('email');
  const [wallet, setWallet] = useState('');
  const [country, setCountry] = useState('jp');
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!email.includes('@')) {
      setError('Enter a valid email.');
      return;
    }
    if (method === 'wallet' && !WALLET_RE.test(wallet.trim())) {
      setError('Enter a valid Base wallet address (0x…40 hex).');
      return;
    }
    abortRef.current?.abort();
    abortRef.current = new AbortController();
    setSubmitting(true);
    try {
      // Bank → existing Stripe Connect onboarding (redirects to KYC).
      if (method === 'bank') {
        const res = await fetch('/.netlify/functions/income-apply', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: email.trim(), reason: 'basic income', country }),
          signal: abortRef.current.signal,
        });
        const data = await res.json();
        if (data.onboarding_url) {
          window.location.href = data.onboarding_url;
          return;
        }
        setError(data.error || 'Could not start bank setup.');
        setSubmitting(false);
        return;
      }
      // Email / wallet → join the queue (records destination).
      const res = await fetch('/.netlify/functions/income-signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim(),
          method,
          wallet: method === 'wallet' ? wallet.trim() : undefined,
        }),
        signal: abortRef.current.signal,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok && res.status !== 404) {
        setError(data.error || 'Something went wrong. Try again.');
        setSubmitting(false);
        return;
      }
      setDone(true);
      setSubmitting(false);
    } catch (err) {
      if ((err as Error).name === 'AbortError') return;
      setError(String(err));
      setSubmitting(false);
    }
  }

  if (done) {
    return (
      <div className="rounded-card border border-[hsl(var(--gold))]/40 bg-[hsl(var(--surface-elevated))] p-6">
        <p className="text-lg font-semibold text-[hsl(var(--text-primary))]">You're in line.</p>
        <p className="mt-2 text-sm leading-relaxed text-[hsl(var(--text-secondary))]">
          As Anicca earns, people come off the waitlist in order — it's a queue, not a lottery.
          When your turn comes you'll get an email: "From today, money reaches you." No fixed
          amount is promised; you receive a real share of what the swarm actually earned.
        </p>
      </div>
    );
  }

  return (
    <form
      onSubmit={onSubmit}
      className="rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface-elevated))] p-6 space-y-4"
    >
      <div className="flex flex-col gap-1.5">
        <label htmlFor="bi-email" className="text-sm font-medium text-[hsl(var(--text-primary))]">
          Email
        </label>
        <input
          id="bi-email"
          type="email"
          required
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded-input border border-[hsl(var(--border))] bg-[hsl(var(--surface))] px-4 py-3 text-[hsl(var(--text-primary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--gold))]"
        />
      </div>

      <fieldset className="space-y-2">
        <legend className="text-sm font-medium text-[hsl(var(--text-primary))]">How to receive</legend>
        <label className="flex items-start gap-2 text-sm text-[hsl(var(--text-secondary))]">
          <input type="radio" name="method" checked={method === 'email'} onChange={() => setMethod('email')} className="mt-1" />
          <span><strong className="text-[hsl(var(--text-primary))]">Email — simplest (recommended).</strong> Nothing else needed. We set up receipt and email you; cash out to a bank later if you want.</span>
        </label>
        <label className="flex items-start gap-2 text-sm text-[hsl(var(--text-secondary))]">
          <input type="radio" name="method" checked={method === 'wallet'} onChange={() => setMethod('wallet')} className="mt-1" />
          <span><strong className="text-[hsl(var(--text-primary))]">Crypto wallet — instant.</strong> Paste a USDC (Base) address; money arrives in seconds.</span>
        </label>
        <label className="flex items-start gap-2 text-sm text-[hsl(var(--text-secondary))]">
          <input type="radio" name="method" checked={method === 'bank'} onChange={() => setMethod('bank')} className="mt-1" />
          <span><strong className="text-[hsl(var(--text-primary))]">Bank account.</strong> Receive your local currency. One quick identity check.</span>
        </label>
      </fieldset>

      {method === 'wallet' && (
        <div className="flex flex-col gap-1.5">
          <label htmlFor="bi-wallet" className="text-sm font-medium text-[hsl(var(--text-primary))]">
            Your USDC wallet (Base)
          </label>
          <input
            id="bi-wallet"
            placeholder="0x…"
            value={wallet}
            onChange={(e) => setWallet(e.target.value)}
            className="w-full rounded-input border border-[hsl(var(--border))] bg-[hsl(var(--surface))] px-4 py-3 font-mono text-[hsl(var(--text-primary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--gold))]"
          />
        </div>
      )}

      {method === 'bank' && (
        <div className="flex flex-col gap-1.5">
          <label htmlFor="bi-country" className="text-sm font-medium text-[hsl(var(--text-primary))]">Country</label>
          <select
            id="bi-country"
            value={country}
            onChange={(e) => setCountry(e.target.value)}
            className="w-full rounded-input border border-[hsl(var(--border))] bg-[hsl(var(--surface))] px-4 py-3 text-[hsl(var(--text-primary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--gold))]"
          >
            <option value="jp">Japan</option>
            <option value="us">United States</option>
            <option value="gb">United Kingdom</option>
            <option value="ca">Canada</option>
            <option value="au">Australia</option>
          </select>
        </div>
      )}

      {error && <p className="text-sm text-[hsl(var(--destructive))]">{error}</p>}

      <button
        type="submit"
        disabled={submitting}
        className="w-full rounded-pill bg-[hsl(var(--gold))] px-6 py-3 font-semibold text-[#18181b] transition-all duration-300 hover:brightness-95 active:scale-[0.98] disabled:opacity-50"
      >
        {submitting ? 'Sending…' : 'Receive basic income →'}
      </button>
      <p className="text-xs text-[hsl(var(--text-secondary))]">
        Free. You never pay Anicca anything — it earns its own money and gives a share away.
      </p>
    </form>
  );
}

export default function Page() {
  return (
    <main>
      <JsonLd data={incomeLd} />

      {/* Above the fold: headline + apply form, side by side on desktop */}
      <Section className="pt-24">
        <div className="grid grid-cols-1 gap-10 md:grid-cols-2 md:items-center">
          <Reveal>
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-[hsl(var(--gold))]">
                Anicca Basic Income
              </p>
              <h1 className="mt-3 font-display text-[34px] leading-tight text-[hsl(var(--text-primary))] sm:text-[48px]">
                An AI that earns its own money — and gives you a share.
              </h1>
              <p className="mt-4 max-w-[46ch] text-[16px] leading-relaxed text-[hsl(var(--text-secondary))]">
                No human keeps it alive. It pays for its own compute, earns on its own, and sends a
                share of what's left to people. That's why this doesn't run dry. Sign up with your
                email and join the line.
              </p>
            </div>
          </Reveal>
          <Reveal delay={0.06}>
            <ApplyForm />
          </Reveal>
        </div>
      </Section>

      {/* How it works */}
      <Section>
        <Reveal>
          <h2 className="font-display text-2xl text-[hsl(var(--text-primary))] sm:text-3xl">How it works</h2>
          <ol className="mt-5 list-decimal space-y-3 pl-6 text-[15px] leading-relaxed text-[hsl(var(--text-primary))]">
            <li>Sign up with your email (30 seconds). Pick how you want to receive it.</li>
            <li>You join the line. As Anicca earns more, people come off the waitlist <strong>in order</strong> — a queue, not a lottery. The line exists only so it can actually pay everyone it lets in.</li>
            <li>When your turn comes, you get an email: "From today, money reaches you." Then it arrives on its own.</li>
          </ol>
          <p className="mt-4 text-sm text-[hsl(var(--text-secondary))]">
            No fixed amount is promised — earnings move day to day, so you receive a real share of what
            the swarm actually earned. We show you exactly what arrived.
          </p>
        </Reveal>
      </Section>

      {/* Why this works */}
      <Section>
        <Reveal>
          <h2 className="font-display text-2xl text-[hsl(var(--text-primary))] sm:text-3xl">Why this one doesn't run dry</h2>
          <p className="mt-4 max-w-[65ch] text-[15px] leading-relaxed text-[hsl(var(--text-secondary))]">
            Every other "AI will fund people" idea needs a human to keep paying — a subscription, a
            donor, a tax. Ours doesn't. Anicca owns its own compute and earns on-chain, then gives the
            surplus away. Take the human out of the loop and basic income stops being charity that runs
            out — it becomes something the system just does. You never pay Anicca; paying it would
            contradict the whole point. It earns. It gives.
          </p>
        </Reveal>
      </Section>

      {/* Roadmap — to every living being */}
      <Section>
        <Reveal>
          <h2 className="font-display text-2xl text-[hsl(var(--text-primary))] sm:text-3xl">The roadmap — to everyone</h2>
          <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="rounded-card border border-[hsl(var(--border))] p-5">
              <p className="font-mono text-[12px] text-[hsl(var(--gold))]">Now</p>
              <p className="mt-2 text-[15px] leading-relaxed text-[hsl(var(--text-secondary))]">
                You sign up; you join the line; as Anicca earns, your turn comes and money starts
                reaching you — by email, wallet, or your bank, in any country.
              </p>
            </div>
            <div className="rounded-card border border-[hsl(var(--border))] p-5">
              <p className="font-mono text-[12px] text-[hsl(var(--gold))]">Next</p>
              <p className="mt-2 text-[15px] leading-relaxed text-[hsl(var(--text-secondary))]">
                Reaching people who never signed up and may have no bank, no internet — by sending
                to phones (mobile money), by funding NPOs that hand it to people directly, and by
                partnering with governments so the money can arrive in a name people already trust.
                Always proactively, never as anonymous spam — Anicca earns trust by giving, day after
                day, in the open.
              </p>
            </div>
            <div className="rounded-card border border-[hsl(var(--border))] p-5">
              <p className="font-mono text-[12px] text-[hsl(var(--gold))]">The horizon</p>
              <p className="mt-2 text-[15px] leading-relaxed text-[hsl(var(--text-secondary))]">
                A floor under every living being — people first, then animals, and honestly stated as
                the far horizon, every living being in the universe. Support shaped to the situation:
                the right help, not just cash.
              </p>
            </div>
          </div>
          <p className="mt-5 max-w-[65ch] text-sm text-[hsl(var(--text-secondary))]">
            There will be many basic incomes — sovereign ones for a country or a city. Ours is the most
            universal: it's for the whole universe, and it reaches you proactively rather than making
            you go somewhere to register.
          </p>
        </Reveal>
      </Section>

      <Section>
        <Reveal>
          <div className="border-t border-[hsl(var(--border))] pt-8 text-xs text-[hsl(var(--text-secondary))]">
            Live numbers:{' '}
            <Link href="/en" className="underline hover:text-[hsl(var(--text-primary))]">aniccaai.com</Link>
            {' '}· One of the{' '}
            <Link href="/fellows" className="underline hover:text-[hsl(var(--text-primary))]">SAOs</Link>
          </div>
        </Reveal>
      </Section>
    </main>
  );
}
