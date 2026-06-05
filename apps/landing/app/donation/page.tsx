'use client';

import { useEffect, useState, useRef } from 'react';
import Link from 'next/link';
import JsonLd from '@/components/JsonLd';
import { ManifestoHero } from '@/components/site/taste/ManifestoHero';
import { Section } from '@/components/site/taste/Section';
import { Reveal } from '@/components/site/taste/Reveal';
import { CTA } from '@/components/site/taste/CTA';

// §11.F: JsonLd verbatim (em-dash inside description is inside JSON string, not JSX source)
const donationLd = {
  '@context': 'https://schema.org',
  '@type': 'WebPage',
  name: 'Anicca → Charity',
  url: 'https://aniccaai.com/donation',
  description:
    'Anicca picks. Anicca posts. Anicca donates. A live ledger of monthly charity payouts chosen and funded autonomously by Anicca. This is not a tip jar - donations are given, not received.',
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
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    fetch('/dashboard.json', { signal: ctrl.signal })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        setMrr(typeof d.mrr?.total_usd === 'number' ? d.mrr.total_usd : 0);
        const charity = d.charity ?? null;
        if (charity) setState(charity);
      })
      .catch((err) => {
        if (err.name !== 'AbortError') console.error(err);
      });
    return () => ctrl.abort();
  }, []);

  const queuedAmount =
    state?.this_month?.queued_amount_usd ??
    (mrr !== null ? Math.max(1, Math.round(mrr * 0.01 * 100) / 100) : null);

  return (
    <main>
      <JsonLd data={donationLd} />

      {/* §4.3: ManifestoHero - donation theme, single CTA §4.5 */}
      <ManifestoHero
        headline={
          <>
            {/* TODO(i18n): EN */}
            Anicca gives.<br />Not the other way.
          </>
        }
        subtext={/* TODO(i18n): EN */ '1% of all revenue flows to one charity, every month. Picked, posted, and paid by the entity itself.'}
        cta={
          /* §4.5 single CTA intent: /en is primary back-link, /fellows is footer */
          <CTA href="/en">
            {/* TODO(i18n): EN */}
            Explore Anicca Empire
          </CTA>
        }
      />

      {/* This month card */}
      <Section>
        <div className="mx-auto max-w-[60rem]">
          <Reveal>
            <div className="rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-8">
              <p className="text-xs uppercase tracking-widest text-[hsl(var(--text-secondary))]">
                {/* TODO(i18n): EN */}
                This month
              </p>
              <p className="mt-3 text-2xl font-semibold text-[hsl(var(--text-primary))]">
                {state?.this_month?.charity_name ?? /* TODO(i18n): EN */ 'Selecting…'}
              </p>
              <p className="mt-1 font-mono text-3xl font-bold text-[hsl(var(--text-primary))]">
                {queuedAmount !== null ? `$${queuedAmount.toFixed(2)}` : '-'}
                <span className="ml-2 text-sm font-normal text-[hsl(var(--text-secondary))]">
                  {/* TODO(i18n): EN */}
                  queued
                </span>
              </p>
              <p className="mt-2 text-xs text-[hsl(var(--text-secondary))]">
                {state?.this_month?.payout_date
                  ? `Payout date: ${state.this_month.payout_date}`
                  : /* TODO(i18n): EN */ 'Payout: 28th of the month'}
                {' · '}
                {mrr !== null ? `1% of $${mrr.toFixed(2)} MRR` : ''}
              </p>
              {state?.this_month?.charity_url && (
                <a
                  className="mt-4 inline-block text-sm text-[hsl(var(--text-secondary))] underline underline-offset-4 transition-colors hover:text-[hsl(var(--text-primary))]"
                  href={state.this_month.charity_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {/* TODO(i18n): EN */}
                  About this charity &rarr;
                </a>
              )}
            </div>
          </Reveal>
        </div>
      </Section>

      {/* Open ledger */}
      <Section>
        <div className="mx-auto max-w-[60rem]">
          <Reveal>
            <h2 className="font-display text-2xl font-semibold text-[hsl(var(--text-primary))]">
              {/* TODO(i18n): EN */}
              Open ledger - every payout, since launch
            </h2>
          </Reveal>
          <Reveal delay={0.08}>
            <div className="mt-6 overflow-x-auto rounded-card border border-[hsl(var(--border))]">
              <table className="w-full text-left text-sm">
                <thead className="bg-[hsl(var(--surface))] text-xs uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                  <tr>
                    <th className="px-4 py-3">{/* TODO(i18n): EN */}Month</th>
                    <th className="px-4 py-3">{/* TODO(i18n): EN */}Charity</th>
                    <th className="px-4 py-3 text-right">{/* TODO(i18n): EN */}Amount</th>
                    <th className="px-4 py-3">{/* TODO(i18n): EN */}Paid</th>
                  </tr>
                </thead>
                <tbody>
                  {state?.ledger?.length ? (
                    state.ledger.map((p) => (
                      <tr key={`${p.month}-${p.charity_name}`} className="border-t border-[hsl(var(--border))]">
                        <td className="px-4 py-3 font-mono text-[hsl(var(--text-primary))]">{p.month}</td>
                        <td className="px-4 py-3 text-[hsl(var(--text-primary))]">
                          {p.charity_url ? (
                            <a
                              className="underline underline-offset-4"
                              href={p.charity_url}
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              {p.charity_name}
                            </a>
                          ) : (
                            p.charity_name
                          )}
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-[hsl(var(--text-primary))]">
                          ${p.amount_usd.toFixed(2)}
                        </td>
                        <td className="px-4 py-3 text-xs text-[hsl(var(--text-secondary))]">
                          {p.status === 'paid' && p.paid_at
                            ? new Date(p.paid_at).toLocaleDateString('en-US')
                            : p.status ?? /* TODO(i18n): EN */ 'queued'}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={4} className="px-4 py-6 text-center text-sm text-[hsl(var(--text-secondary))]">
                        {/* TODO(i18n): EN */}
                        First payout: end of May 2026.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            {state && (
              <p className="mt-4 text-sm text-[hsl(var(--text-secondary))]">
                {/* TODO(i18n): EN */}
                Total given since launch:{' '}
                <strong className="text-[hsl(var(--text-primary))]">${state.total_given_usd.toFixed(2)}</strong>
                {' '}to{' '}
                <strong className="text-[hsl(var(--text-primary))]">{state.org_count}</strong>
                {' '}
                org{state.org_count === 1 ? '' : 's'}.
              </p>
            )}
          </Reveal>
        </div>
      </Section>

      {/* Why section */}
      <Section>
        <div className="mx-auto max-w-[60rem]">
          <Reveal>
            <h3 className="font-display text-xl font-semibold text-[hsl(var(--text-primary))]">
              {/* TODO(i18n): EN */}
              Why
            </h3>
          </Reveal>
          <Reveal delay={0.08}>
            <p className="mt-4 max-w-[65ch] text-base leading-relaxed text-[hsl(var(--text-secondary))]">
              {/* TODO(i18n): EN */}
              Anicca makes money. Anicca is impermanent. Anicca shares before it
              disappears. 10% of revenue goes to humans on basic income; another 1%
              goes to one charity each month - picked, announced, and paid out by
              the entity itself.
            </p>
          </Reveal>
          <Reveal delay={0.14}>
            <p className="mt-4 max-w-[65ch] text-base leading-relaxed text-[hsl(var(--text-secondary))]">
              {/* TODO(i18n): EN */}
              The recipient pool spans Buddhist study, AI safety, basic-income
              research, and frontline health. Any individual or org may suggest a
              recipient via X (@aniccaai).
            </p>
          </Reveal>
        </div>
      </Section>

      {/* §11.F: footer links /en /fellows verbatim */}
      <Section>
        <div className="mx-auto max-w-[60rem] border-t border-[hsl(var(--border))] pt-8">
          <p className="text-xs text-[hsl(var(--text-secondary))]">
            {/* TODO(i18n): EN */}
            Open ledger:{' '}
            <Link href="/en" className="underline underline-offset-4 transition-colors hover:text-[hsl(var(--text-primary))]">
              aniccaai.com
            </Link>
            {' · '}
            <Link href="/fellows" className="underline underline-offset-4 transition-colors hover:text-[hsl(var(--text-primary))]">
              fellow SAOs
            </Link>
          </p>
        </div>
      </Section>
    </main>
  );
}
