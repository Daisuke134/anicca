/* eslint-disable react/no-unescaped-entities */
'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

interface BasicIncome {
  pool_usd: number;
  recipients: number;
  per_person_usd: number;
}

export default function Page() {
  const [bi, setBi] = useState<BasicIncome | null>(null);

  useEffect(() => {
    fetch('/dashboard.json')
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setBi(d.basic_income))
      .catch(() => {});
  }, []);

  return (
    <main className="mx-auto max-w-2xl px-6 py-20 text-foreground">
      <p className="mb-6 text-sm">
        <Link href="/en" className="text-muted-foreground underline transition-colors hover:text-foreground">
          ← Back to Anicca
        </Link>
      </p>

      <h1 className="text-4xl font-bold md:text-5xl">Basic Income</h1>
      <p className="mt-4 text-lg text-muted-foreground">
        10% of all Anicca revenue is distributed every month. No work required.
      </p>

      <section className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-border px-5 py-5">
          <p className="text-xs uppercase tracking-widest text-muted-foreground">This month's pool</p>
          <p className="mt-2 font-mono text-2xl font-semibold">
            {bi ? `$${bi.pool_usd.toFixed(2)}` : '—'}
          </p>
        </div>
        <div className="rounded-xl border border-border px-5 py-5">
          <p className="text-xs uppercase tracking-widest text-muted-foreground">Spots filled</p>
          <p className="mt-2 font-mono text-2xl font-semibold">
            {bi ? `${bi.recipients} / 10` : '—'}
          </p>
        </div>
        <div className="rounded-xl border border-border px-5 py-5">
          <p className="text-xs uppercase tracking-widest text-muted-foreground">Per person</p>
          <p className="mt-2 font-mono text-2xl font-semibold">
            {bi ? `$${bi.per_person_usd.toFixed(2)}` : '—'}
          </p>
        </div>
      </section>

      <section className="mt-12">
        <h2 className="text-2xl font-semibold">How it works</h2>
        <ol className="mt-4 list-decimal space-y-3 pl-6 text-base leading-relaxed text-foreground">
          <li>Drop your email and one sentence on why you'd want this.</li>
          <li>Connect Stripe (5 minutes — KYC + bank or debit card). One screen, one redirect.</li>
          <li>Wait. We approve 10 people per cohort. You'll get an email when you're in.</li>
          <li>On the 1st of each month, your share lands in your bank automatically.</li>
        </ol>
      </section>

      <section className="mt-12 rounded-xl border border-border px-6 py-6">
        <h2 className="text-xl font-semibold">Apply</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          The form is being wired up to Stripe Connect Express right now. For
          now, drop your email here and we'll email you the moment onboarding
          is live (matter of days).
        </p>
        <form
          className="mt-6 space-y-4"
          action="https://formspree.io/f/xnnvogyr"
          method="POST"
        >
          <input
            name="email"
            type="email"
            required
            placeholder="you@example.com"
            className="w-full rounded-md border border-border bg-background px-4 py-3 text-foreground"
          />
          <textarea
            name="reason"
            required
            maxLength={280}
            placeholder="Why you'd want this — one sentence (280 chars max)"
            rows={3}
            className="w-full rounded-md border border-border bg-background px-4 py-3 text-foreground"
          />
          <button
            type="submit"
            className="w-full rounded-md bg-foreground px-6 py-3 font-bold text-background transition-opacity hover:opacity-90"
          >
            Join the waitlist →
          </button>
        </form>
      </section>

      <section className="mt-12 space-y-4 text-sm leading-relaxed text-muted-foreground">
        <p>
          <strong className="text-foreground">Why 10% and 10 people.</strong>{' '}
          Anicca's rule: every month, automatically split 10% of revenue across 10 humans. When MRR doubles, the cohort grows.
        </p>
        <p>
          <strong className="text-foreground">Why no work required.</strong>{' '}
          Most "AI economy" stories assume the AI keeps the money. Anicca's premise is the opposite — the swarm earns, the humans receive. The point is to demonstrate that an autonomous AI can fund people, not replace them.
        </p>
        <p>
          <strong className="text-foreground">When we open the next cohort.</strong>{' '}
          When MRR hits $20k. The pool doubles, then we add 10 more spots.
        </p>
      </section>

      <footer className="mt-16 border-t border-border pt-8 text-xs text-muted-foreground">
        Live numbers: <Link href="/en" className="underline">aniccaai.com</Link> · Open source: github.com/Daisuke134/anicca
      </footer>
    </main>
  );
}
