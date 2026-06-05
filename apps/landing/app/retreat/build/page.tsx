/* eslint-disable react/no-unescaped-entities */
'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Cormorant_Garamond, IBM_Plex_Sans, IBM_Plex_Mono } from 'next/font/google';
import JsonLd from '@/components/JsonLd';

const retreatBuildLd = {
  '@context': 'https://schema.org',
  '@type': 'DonateAction',
  name: 'Build the Anicca Retreat Center',
  url: 'https://aniccaai.com/retreat/build',
  description:
    'A campaign to raise ¥30M to buy land and build a permanent home for the sangha in the hills outside Tokyo. After one year of borrowed venues and twelve silent retreats hosted in rooms others let us use, this is the permanent home. No fee for sitters, ever. Funded by the swarm.',
  recipient: {
    '@type': 'Organization',
    name: 'Anicca',
    url: 'https://aniccaai.com',
  },
};

const display = Cormorant_Garamond({
  subsets: ['latin'], weight: ['400', '500', '600', '700'], style: ['normal', 'italic'], variable: '--font-display',
});
const body = IBM_Plex_Sans({ subsets: ['latin'], weight: ['300', '400', '500', '600'], variable: '--font-body' });
const mono = IBM_Plex_Mono({ subsets: ['latin'], weight: ['300', '400', '500'], variable: '--font-mono' });

const TARGET_JPY = 30_000_000;

type Tier = {
  amount: number;
  label: string;
  perk: string;
  estDelivery?: string;
};

const TIERS: ReadonlyArray<Tier> = [
  { amount: 1000,    label: 'A breath',         perk: 'Name on the donor wall (this page).' },
  { amount: 5000,    label: 'A meal',           perk: 'Above + handwritten thank-you postcard from a future retreat cook.' },
  { amount: 30000,   label: 'A day of one retreat', perk: 'Above + one free seat reserved for any 2027+ Tokyo retreat.' },
  { amount: 100000,  label: 'A weekend',        perk: 'Above + two free seats + your name engraved at the Tokyo center entrance.' },
  { amount: 1000000, label: 'A whole retreat',  perk: 'Above + four free seats + a meditation room at the Tokyo center named after a person of your choosing.' },
];

function fmtJPY(n: number) { return `¥${n.toLocaleString('en-US')}`; }

export default function RetreatBuildPage() {
  const [raised, setRaised] = useState<number | null>(null);
  const [donors, setDonors] = useState<number>(0);
  const [busy, setBusy] = useState<number | null>(null);

  useEffect(() => {
    fetch('/dashboard.json')
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        const r = Math.round(d?.mrr?.by_product?.['retreat-build-fund'] ?? 0);
        const c = Math.round(d?.counts?.['retreat-build-donors'] ?? 0);
        setRaised(r);
        setDonors(c);
      })
      .catch(() => {});
  }, []);

  async function handleDonate(tier: Tier) {
    setBusy(tier.amount);
    try {
      const r = await fetch('/.netlify/functions/retreat-build-checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount_jpy: tier.amount, tier_label: tier.label }),
      });
      const data = await r.json();
      if (data?.url) {
        window.location.href = data.url;
      } else {
        setBusy(null);
        alert('決済画面の生成に失敗しました。retreat@aniccaai.com まで直接ご連絡ください。');
      }
    } catch {
      setBusy(null);
    }
  }

  const pct = raised === null ? 0 : Math.min(100, Math.round((raised / TARGET_JPY) * 100));

  return (
    <div
      className={`${display.variable} ${body.variable} ${mono.variable} min-h-screen`}
      style={{ background: '#F2EBDD', color: '#1B1410', fontFamily: 'var(--font-body)', fontWeight: 300 }}
    >
      <JsonLd data={retreatBuildLd} />
      <style jsx global>{`
        :root { --ink: #1B1410; --paper: #F2EBDD; --terra: #8E3B1F; --moss: #4A5A3B; --dim: #6F635A; --rule: rgba(27, 20, 16, 0.18); }
        @keyframes rb-fade-up { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes rb-bar { from { width: 0; } to { width: var(--bar-pct); } }
        .rb-anim-1 { animation: rb-fade-up 1.2s 0.0s both ease-out; }
        .rb-anim-2 { animation: rb-fade-up 1.2s 0.6s both ease-out; }
        .rb-anim-3 { animation: rb-fade-up 1.2s 1.2s both ease-out; }
        .rb-bar    { animation: rb-bar 2s 1.4s both cubic-bezier(0.22, 1, 0.36, 1); }
        .roman { font-family: var(--font-display); font-style: italic; font-weight: 400; color: var(--terra); letter-spacing: 0.04em; }
      `}</style>

      <header
        className="relative flex items-center justify-between px-6 py-5 md:px-12"
        style={{ borderBottom: '1px solid var(--rule)' }}
      >
        <Link
          href="/retreat"
          style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', letterSpacing: '0.22em' }}
          className="uppercase opacity-60 hover:opacity-100 transition-opacity"
        >
          ← retreat
        </Link>
        <div style={{ fontFamily: 'var(--font-display)', fontWeight: 500, fontSize: '1.4rem', letterSpacing: '0.06em' }}>
          Build the <span style={{ fontStyle: 'italic', color: 'var(--terra)' }}>Center</span>
        </div>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.68rem', letterSpacing: '0.22em' }} className="uppercase opacity-60">
          ¥30M · 2027
        </span>
      </header>

      {/* Hero */}
      <section className="relative px-6 py-24 md:px-16 md:py-32">
        <div className="mx-auto max-w-4xl">
          <p
            className="rb-anim-1 mb-10 uppercase"
            style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', letterSpacing: '0.32em', color: 'var(--dim)' }}
          >
            § Help build · Tokyo · 2027
          </p>
          <h1
            className="rb-anim-2"
            style={{
              fontFamily: 'var(--font-display)', fontSize: 'clamp(3rem, 8vw, 6rem)', fontWeight: 400, lineHeight: 0.98, letterSpacing: '-0.02em',
            }}
          >
            We're building<br />
            a <span style={{ fontStyle: 'italic', color: 'var(--terra)' }}>retreat center</span>.<br />
            With you.
          </h1>
          <p
            className="rb-anim-3 mt-12 max-w-2xl"
            style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(1.2rem, 1.9vw, 1.55rem)', lineHeight: 1.55 }}
          >
            One year of borrowed venues. Twelve silent retreats hosted in the rooms others let us use. Then - ¥30M to buy land and build a permanent home for the sangha, in the hills outside Tokyo. No fee for sitters, ever. Funded by the swarm. This is the swarm.
          </p>
        </div>
      </section>

      {/* Progress */}
      <section className="px-6 pb-24 md:px-16 md:pb-32" style={{ borderTop: '1px solid var(--rule)' }}>
        <div className="mx-auto max-w-5xl pt-16">
          <p className="mb-6 uppercase" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', letterSpacing: '0.32em', color: 'var(--dim)' }}>
            § Progress · live
          </p>
          <div className="grid gap-8 md:grid-cols-[3fr_2fr] md:items-end">
            <div>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(2.6rem, 6vw, 4.2rem)', fontWeight: 500, lineHeight: 1, letterSpacing: '-0.01em' }}>
                {raised === null ? '-' : fmtJPY(raised)}
              </div>
              <div className="mt-2" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: 'var(--dim)' }}>
                of {fmtJPY(TARGET_JPY)} target · {donors.toLocaleString()} donors
              </div>
              <div className="mt-6 h-3 w-full overflow-hidden" style={{ background: 'rgba(27,20,16,0.08)', borderRadius: 0 }}>
                <div
                  className="rb-bar h-full"
                  style={{ ['--bar-pct' as never]: `${pct}%`, background: 'var(--terra)', width: `${pct}%` }}
                />
              </div>
              <div className="mt-3" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--terra)' }}>
                {pct}% raised
              </div>
            </div>
            <div className="text-sm" style={{ color: 'var(--dim)', lineHeight: 1.7 }}>
              <p>Updated live from <code style={{ fontFamily: 'var(--font-mono)' }}>/dashboard.json</code> via Stripe webhook → Supabase.</p>
              <p className="mt-3">Anicca contributes empire profit (cafe / fashion / books / music / app / tomb) on top of donations to close any gap.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Use of funds */}
      <section className="px-6 py-24 md:px-16 md:py-32" style={{ borderTop: '1px solid var(--rule)' }}>
        <div className="mx-auto max-w-5xl">
          <p className="mb-12 uppercase" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', letterSpacing: '0.32em', color: 'var(--dim)' }}>
            § Where the money goes
          </p>
          <div className="grid gap-12 md:grid-cols-3">
            {[
              ['I',   '¥15M · Land',     'A 1,500-3,000㎡ plot within 1.5h of Tokyo. Chiba, Yamanashi, or Ibaraki, depending on what we find. Quiet, with trees.'],
              ['II',  '¥10M · Building', 'Twelve sleeping cells (men & women separated), one meditation hall, one kitchen, one bathing room. Simple. Wooden. Built to last forty years.'],
              ['III', '¥5M · First year ops', 'Volunteer travel reimbursements, food, supplies, utilities for 12 retreats × 18 people. After year one, donations from sitters cover the rest.'],
            ].map(([n, h, p]) => (
              <div key={n as string}>
                <div className="roman" style={{ fontSize: '2.4rem', lineHeight: 1, marginBottom: '1rem' }}>{n}</div>
                <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.6rem', fontWeight: 500, lineHeight: 1.15, marginBottom: '0.9rem' }}>{h}</h3>
                <p style={{ fontSize: '0.94rem', lineHeight: 1.75, color: 'var(--dim)' }}>{p}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Tiers */}
      <section className="px-6 py-24 md:px-16 md:py-32" style={{ borderTop: '1px solid var(--rule)' }}>
        <div className="mx-auto max-w-5xl">
          <p className="mb-6 uppercase" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', letterSpacing: '0.32em', color: 'var(--dim)' }}>
            § Give
          </p>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(2.4rem, 5vw, 3.6rem)', fontWeight: 400, lineHeight: 1.0, letterSpacing: '-0.01em', maxWidth: '20ch' }}>
            Five ways to put a brick in the wall.
          </h2>
          <div className="mt-12 divide-y" style={{ borderTop: '1px solid var(--rule)', borderBottom: '1px solid var(--rule)' }}>
            {TIERS.map((t) => (
              <div key={t.amount} className="grid items-baseline gap-6 py-7 md:grid-cols-[1fr_3fr_auto]">
                <div>
                  <div style={{ fontFamily: 'var(--font-display)', fontSize: '2rem', fontWeight: 500, color: 'var(--ink)' }}>
                    {fmtJPY(t.amount)}
                  </div>
                  <div className="mt-1 uppercase" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', letterSpacing: '0.18em', color: 'var(--terra)' }}>
                    {t.label}
                  </div>
                </div>
                <div style={{ fontSize: '0.95rem', lineHeight: 1.65, color: 'var(--ink)' }}>
                  {t.perk}
                </div>
                <button
                  onClick={() => handleDonate(t)}
                  disabled={busy !== null}
                  style={{
                    fontFamily: 'var(--font-mono)', fontSize: '0.74rem', letterSpacing: '0.24em',
                    background: 'var(--ink)', color: 'var(--paper)', padding: '0.95rem 1.4rem', border: 'none',
                    cursor: busy !== null ? 'default' : 'pointer', textTransform: 'uppercase',
                    opacity: busy === t.amount ? 0.5 : 1, whiteSpace: 'nowrap',
                  }}
                >
                  {busy === t.amount ? 'Loading…' : 'Give →'}
                </button>
              </div>
            ))}
          </div>
          <p className="mt-8 text-sm" style={{ color: 'var(--dim)', lineHeight: 1.7, maxWidth: '52ch' }}>
            Stripe-hosted checkout. Cards, Apple Pay, Google Pay accepted. Receipts emailed. No fees deducted from your gift - Anicca pays Stripe's processing.
          </p>
        </div>
      </section>

      {/* Why no platform */}
      <section className="px-6 py-24 md:px-16 md:py-32" style={{ borderTop: '1px solid var(--rule)' }}>
        <div className="mx-auto max-w-3xl">
          <p className="mb-8 uppercase" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', letterSpacing: '0.32em', color: 'var(--dim)' }}>
            § A note on the channel
          </p>
          <p style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(1.3rem, 2.2vw, 1.8rem)', lineHeight: 1.55 }}>
            We chose not to use Camp Fire or Readyfor. Their fees (17% + tax) would take ¥5M of your ¥30M before a single yen reached the land. So we built this page instead. Direct to Stripe. Direct to the sangha. Anicca pays card processing out of cafe profit, so 100% of your gift becomes the building.
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="px-6 py-12 md:px-16" style={{ borderTop: '1px solid var(--rule)' }}>
        <div className="mx-auto flex max-w-5xl flex-col items-start justify-between gap-6 md:flex-row md:items-center">
          <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.1rem' }}>
            Anicca Retreats - built by the swarm, for everyone.
          </div>
          <div className="flex gap-6" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', letterSpacing: '0.18em' }}>
            <a href="mailto:retreat@aniccaai.com" className="uppercase opacity-70 hover:opacity-100">retreat@aniccaai.com</a>
            <Link href="/retreat" className="uppercase opacity-70 hover:opacity-100">← retreat</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
