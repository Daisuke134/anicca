/* eslint-disable react/no-unescaped-entities */
'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

export default function Page() {
  const [thisMonth, setThisMonth] = useState<number | null>(null);

  useEffect(() => {
    fetch('/dashboard.json')
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        const v = d.mrr?.by_product?.donation || d.mrr?.by_product?._other || 0;
        setThisMonth(typeof v === 'number' ? v : 0);
      })
      .catch(() => {});
  }, []);

  return (
    <main className="mx-auto max-w-2xl px-6 py-20 text-foreground">
      <p className="mb-6 text-sm">
        <Link href="/en" className="text-muted-foreground underline transition-colors hover:text-foreground">
          ← Back to Anicca Empire
        </Link>
      </p>

      <h1 className="text-4xl font-bold md:text-5xl">💝 Anicca Donation Jar</h1>
      <p className="mt-4 text-lg text-muted-foreground">
        Tip the empire. Every dollar funds basic income + the next product.
      </p>

      <div className="mt-10 rounded-xl border border-border bg-background px-6 py-6 text-center">
        <p className="text-sm uppercase tracking-widest text-muted-foreground">
          This month so far
        </p>
        <p className="mt-2 font-mono text-3xl font-semibold">
          {thisMonth !== null ? `$${thisMonth.toFixed(2)}` : '—'}
        </p>
        <p className="mt-2 text-xs text-muted-foreground">
          (live from Stripe via /dashboard.json)
        </p>
      </div>

      <div className="mt-10 text-center">
        <a
          href="https://buy.stripe.com/6oU9ATgcC8Bo5D25ca28802"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block rounded-xl bg-foreground px-8 py-4 text-lg font-bold text-background transition-opacity hover:opacity-90"
        >
          Drop a tip — any amount →
        </a>
        <p className="mt-3 text-xs text-muted-foreground">
          Stripe-secured · USD · custom amount (min $1)
        </p>
      </div>

      <section className="mt-16 space-y-4 text-sm leading-relaxed text-muted-foreground">
        <p>
          Anicca is open source and self-funding. Mobile app subscriptions,
          newsletter, music royalties, comedy tickets, t-shirts and (soon)
          mango juice all go into one pot. <strong className="text-foreground">10% of all of it</strong> flows
          back out as basic income to 10 humans, every month.
        </p>
        <p>
          Tipping the donation jar is one more way to fund the work. No
          obligation. No subscription. Just one quiet contribution.
        </p>
        <p>
          The total here updates automatically when each Stripe charge clears
          (refresh fires 4× daily).
        </p>
      </section>

      <footer className="mt-16 border-t border-border pt-8 text-xs text-muted-foreground">
        Open ledger:{' '}
        <Link href="/en" className="underline transition-colors hover:text-foreground">
          aniccaai.com
        </Link>{' '}
        · github.com/Daisuke134/anicca
      </footer>
    </main>
  );
}
