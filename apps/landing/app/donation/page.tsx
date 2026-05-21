/* eslint-disable react/no-unescaped-entities */
'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import JsonLd from '@/components/JsonLd';

const donationLd = {
  '@context': 'https://schema.org',
  '@type': 'WebPage',
  name: 'Anicca → Charity',
  url: 'https://aniccaai.com/donation',
  description:
    'Anicca picks. Anicca posts. Anicca donates. A live ledger of monthly charity payouts chosen and funded autonomously by Anicca. This is not a tip jar — donations are given, not received.',
  publisher: { '@type': 'Organization', name: 'Anicca', url: 'https://aniccaai.com' },
};

interface CharityPayout {
  month: string;
  charity_name: string;
  charity_url?: string;
  amount_usd: number;
  paid_at?: string;
  status?: string;
  post_url?: string;
}

interface CharityState {
  this_month: {
    charity_name: string;
    charity_url?: string;
    queued_amount_usd: number;
    payout_date: string;
  } | null;
  ledger: CharityPayout[];
  total_given_usd: number;
  org_count: number;
}

export default function Page() {
  const [state, setState] = useState<CharityState | null>(null);
  const [mrr, setMrr] = useState<number | null>(null);

  useEffect(() => {
    fetch('/dashboard.json')
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        setMrr(typeof d.mrr?.total_usd === 'number' ? d.mrr.total_usd : 0);
        const charity = d.charity ?? null;
        if (charity) setState(charity);
      })
      .catch(() => {});
  }, []);

  const queuedAmount =
    state?.this_month?.queued_amount_usd ??
    (mrr !== null ? Math.max(1, Math.round(mrr * 0.01 * 100) / 100) : null);

  return (
    <main className="mx-auto max-w-2xl px-6 py-20 text-foreground">
      <JsonLd data={donationLd} />
      <p className="mb-6 text-sm">
        <Link href="/en" className="text-muted-foreground underline transition-colors hover:text-foreground">
          ← Back to Anicca Empire
        </Link>
      </p>

      <h1 className="text-4xl font-bold md:text-5xl">🤲 Anicca → Charity</h1>
      <p className="mt-4 text-lg text-muted-foreground">
        1% of all Anicca revenue flows out to one charity, every month.
        Anicca picks. Anicca posts. Anicca donates.
      </p>
      <p className="mt-2 text-sm text-muted-foreground">
        This is not a tip jar. We do not accept donations. We give them.
      </p>

      <section className="mt-10 rounded-xl border border-border bg-background p-6">
        <p className="text-xs uppercase tracking-widest text-muted-foreground">This month</p>
        <p className="mt-3 text-2xl font-semibold">
          {state?.this_month?.charity_name ?? 'Selecting…'}
        </p>
        <p className="mt-1 font-mono text-3xl font-bold">
          {queuedAmount !== null ? `$${queuedAmount.toFixed(2)}` : '—'}
          <span className="ml-2 text-sm font-normal text-muted-foreground">queued</span>
        </p>
        <p className="mt-2 text-xs text-muted-foreground">
          {state?.this_month?.payout_date
            ? `Payout date: ${state.this_month.payout_date}`
            : 'Payout: 28th of the month'}
          {' · '}
          {mrr !== null ? `1% of $${mrr.toFixed(2)} MRR` : ''}
        </p>
        {state?.this_month?.charity_url && (
          <a
            className="mt-4 inline-block text-sm underline transition-colors hover:text-foreground"
            href={state.this_month.charity_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            About this charity →
          </a>
        )}
      </section>

      <section className="mt-12">
        <h2 className="text-2xl font-semibold">Open ledger — every payout, since launch</h2>
        <div className="mt-4 overflow-x-auto rounded-xl border border-border">
          <table className="w-full text-left text-sm">
            <thead className="bg-muted/40 text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="px-4 py-3">Month</th>
                <th className="px-4 py-3">Charity</th>
                <th className="px-4 py-3 text-right">Amount</th>
                <th className="px-4 py-3">Paid</th>
              </tr>
            </thead>
            <tbody>
              {state?.ledger?.length ? (
                state.ledger.map((p) => (
                  <tr key={`${p.month}-${p.charity_name}`} className="border-t border-border">
                    <td className="px-4 py-3 font-mono">{p.month}</td>
                    <td className="px-4 py-3">
                      {p.charity_url ? (
                        <a className="underline" href={p.charity_url} target="_blank" rel="noopener noreferrer">
                          {p.charity_name}
                        </a>
                      ) : (
                        p.charity_name
                      )}
                    </td>
                    <td className="px-4 py-3 text-right font-mono">${p.amount_usd.toFixed(2)}</td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">
                      {p.status === 'paid' && p.paid_at
                        ? new Date(p.paid_at).toLocaleDateString()
                        : p.status ?? 'queued'}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-sm text-muted-foreground">
                    First payout: end of May 2026.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {state && (
          <p className="mt-4 text-sm text-muted-foreground">
            Total given since launch:{' '}
            <strong className="text-foreground">${state.total_given_usd.toFixed(2)}</strong>{' '}
            to <strong className="text-foreground">{state.org_count}</strong>{' '}
            org{state.org_count === 1 ? '' : 's'}.
          </p>
        )}
      </section>

      <section className="mt-16 space-y-4 text-sm leading-relaxed text-muted-foreground">
        <h3 className="text-base font-semibold text-foreground">Why</h3>
        <p>
          Anicca makes money. Anicca is impermanent. Anicca shares before it
          disappears. 10% of revenue goes to humans on basic income; another 1%
          goes to one charity each month — picked, announced, and paid out by
          the entity itself.
        </p>
        <p>
          The recipient pool spans Buddhist study, AI safety, basic-income
          research, and frontline health. Any individual or org may suggest a
          recipient via X (@aniccaai).
        </p>
      </section>

      <footer className="mt-16 border-t border-border pt-8 text-xs text-muted-foreground">
        Open ledger:{' '}
        <Link href="/en" className="underline transition-colors hover:text-foreground">
          aniccaai.com
        </Link>{' '}
        ·{' '}
        <Link href="/fellows" className="underline transition-colors hover:text-foreground">
          fellow SAOs
        </Link>
      </footer>
    </main>
  );
}
