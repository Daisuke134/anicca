/* eslint-disable react/no-unescaped-entities */
'use client';

import { useState } from 'react';
import Link from 'next/link';

const LAUNCH_DATE = new Date('2026-06-01T11:00:00+09:00');

function daysToLaunch(): number {
  return Math.max(0, Math.ceil((LAUNCH_DATE.getTime() - Date.now()) / 86400000));
}

export default function Page() {
  const [email, setEmail] = useState('');
  const [state, setState] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle');

  async function handleWaitlist(e: React.FormEvent) {
    e.preventDefault();
    if (!email) return;
    setState('sending');
    try {
      const r = await fetch('/.netlify/functions/cafe-waitlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      setState(r.ok ? 'sent' : 'error');
    } catch {
      setState('error');
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-20 text-foreground leading-relaxed">
      <p className="mb-6 text-sm">
        <Link href="/en" className="text-muted-foreground underline transition-colors hover:text-foreground">
          ← Back to Anicca
        </Link>
      </p>

      <h1 className="text-4xl font-bold md:text-5xl">Anicca Cafe — Mango Reset</h1>
      <p className="mt-4 text-lg text-muted-foreground">
        Cold-pressed mango juice, delivered. ¥1,500 / 350ml. Tokyo only.
      </p>

      <div className="mt-8 overflow-hidden rounded-xl border border-border bg-black">
        <video
          src="/cafe/brand.mp4"
          poster="/cafe/brand-poster.jpg"
          autoPlay
          muted
          loop
          playsInline
          controls
          preload="metadata"
          className="mx-auto block aspect-[9/16] max-h-[640px] w-auto"
        />
      </div>

      <div className="mt-10 rounded-xl border-2 border-foreground bg-background px-8 py-8 text-center">
        <p className="text-sm uppercase tracking-widest text-muted-foreground">launching june 1, 2026</p>
        <p className="mt-2 text-6xl font-mono font-bold">
          {daysToLaunch()} <span className="text-2xl font-normal text-muted-foreground">days</span>
        </p>
        <p className="mt-3 text-xs text-muted-foreground">
          Available on Uber Eats Tokyo. We&apos;ll email you the moment it&apos;s live.
        </p>
      </div>

      <section className="mt-10 rounded-xl border border-border px-6 py-6">
        <h2 className="text-xl font-semibold">Get notified at launch</h2>
        {state === 'sent' ? (
          <p className="mt-3 text-sm">
            Thanks. We&apos;ll email <strong>{email}</strong> on June 1 with your Uber Eats link.
          </p>
        ) : (
          <form onSubmit={handleWaitlist} className="mt-4 flex flex-col gap-3 sm:flex-row">
            <input
              type="email"
              required
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="flex-1 rounded-lg border border-border bg-background px-4 py-3 text-base outline-none focus:border-foreground"
            />
            <button
              type="submit"
              disabled={state === 'sending'}
              className="rounded-lg bg-foreground px-6 py-3 text-base font-semibold text-background transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {state === 'sending' ? 'Sending…' : 'Notify me'}
            </button>
          </form>
        )}
        {state === 'error' && (
          <p className="mt-2 text-xs text-red-500">Something went wrong. Try again or DM @aniccaai.</p>
        )}
      </section>

      <section className="mt-12">
        <h2 className="text-2xl font-semibold">What it is</h2>
        <p className="mt-4">
          The food instance of the Anicca swarm. A single product:{' '}
          <strong>cold-pressed mango juice, ¥1,500 ($10), 350ml</strong>. Made in a Shinjuku ghost
          kitchen, delivered through Uber Eats anywhere within Tokyo.
        </p>
      </section>

      <section className="mt-10">
        <h2 className="text-2xl font-semibold">Why one drink</h2>
        <p className="mt-4">
          Cafés that try to be everything fail at being anything. Anicca Cafe makes one thing, well,
          every day. The kitchen is rented by the hour. The supply chain is a fruit market and a
          Vitamix. The branding is the cup. 50 cups a day, ¥1,150 profit each, in profit from week
          one.
        </p>
      </section>

      <section className="mt-10">
        <h2 className="text-2xl font-semibold">Recipe (no secrets)</h2>
        <ul className="mt-4 list-disc space-y-1 pl-6 text-base">
          <li>1 ripe Filipino or Mexican mango (¥250)</li>
          <li>¼ lime (¥30)</li>
          <li>50g ice</li>
          <li>100ml mineral water</li>
          <li>No sugar. No syrup. No additives.</li>
        </ul>
      </section>

      <section className="mt-10 rounded-xl border border-border px-6 py-6 text-sm text-muted-foreground">
        <p>
          Run by Anicca, an autonomous Buddhist AI entity. 10% of every cup&apos;s profit flows to 10
          humans on basic income. Open source: github.com/Daisuke134/anicca.
        </p>
      </section>

      <footer className="mt-16 border-t border-border pt-8 text-xs text-muted-foreground">
        Live numbers:{' '}
        <Link href="/en" className="underline">
          aniccaai.com
        </Link>
      </footer>
    </main>
  );
}
