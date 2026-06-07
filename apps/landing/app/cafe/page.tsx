/* eslint-disable react/no-unescaped-entities */
'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { Cormorant_Garamond, IBM_Plex_Sans, IBM_Plex_Mono } from 'next/font/google';
import JsonLd from '@/components/JsonLd';
import { SplitHero, Section, Reveal, CTA } from '@/components/site/taste';

/* ─────────────────────────────────────────────
   §11.F: JsonLd blocks - verbatim (schema unchanged)
───────────────────────────────────────────── */
const cafeLd = {
  '@context': 'https://schema.org',
  '@type': 'FoodEstablishment',
  name: 'Anicca Cafe Tokyo',
  servesCuisine: 'Cold-pressed juice',
  priceRange: '¥1500',
  areaServed: 'Tokyo, Japan',
  url: 'https://aniccaai.com/cafe',
  description:
    'Tokyo cafe run by an autonomous AI. Single-SKU: one cold-pressed mango drink (Mango Reset, ¥1500). Inspired by Andon Labs Mona in Stockholm.',
};
const cafeOfferLd = {
  '@context': 'https://schema.org',
  '@type': 'Offer',
  name: 'Mango Reset',
  price: '1500',
  priceCurrency: 'JPY',
  url: 'https://aniccaai.com/cafe',
  availability: 'https://schema.org/PreOrder',
};
const cafeFaqLd = {
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: [
    { '@type': 'Question', name: 'What is Anicca Cafe?', acceptedAnswer: { '@type': 'Answer', text: 'A Tokyo cafe where an AI handles inventory, pricing and supplier ordering. The menu is one drink: a ¥1500 cold-pressed mango juice called Mango Reset.' } },
    { '@type': 'Question', name: 'Why only one drink?', acceptedAnswer: { '@type': 'Answer', text: 'Most cafes carry 40 items and close within two years. One SKU keeps operations simple enough for an AI to run reliably and easy for a customer to remember.' } },
    { '@type': 'Question', name: 'Is it really AI-run?', acceptedAnswer: { '@type': 'Answer', text: 'Inspired by Andon Labs\' Mona in Stockholm. The AI runs autonomous operations; a Tokyo human team does in-person service.' } },
    { '@type': 'Question', name: 'How much is it?', acceptedAnswer: { '@type': 'Answer', text: '¥1500 for one bottle of Mango Reset.' } },
    { '@type': 'Question', name: 'Where and when?', acceptedAnswer: { '@type': 'Answer', text: 'Tokyo; pre-launch reservations and the exact location via aniccaai.com/cafe.' } },
  ],
};

/* ─────────────────────────────────────────────
   Fonts (local variable setup, theme uses semantic tokens)
───────────────────────────────────────────── */
const display = Cormorant_Garamond({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  style: ['normal', 'italic'],
  variable: '--font-display',
});
const body = IBM_Plex_Sans({
  subsets: ['latin'],
  weight: ['300', '400', '500', '600'],
  variable: '--font-body',
});
const mono = IBM_Plex_Mono({
  subsets: ['latin'],
  weight: ['300', '400', '500'],
  variable: '--font-mono',
});

/* ─────────────────────────────────────────────
   Constants - §11.F: URL verbatim
───────────────────────────────────────────── */
const LAUNCH_DATE = new Date('2026-06-01T11:00:00+09:00');
const UBER_EATS_URL = 'https://www.ubereats.com/tokyo/food-delivery/anicca-cafe/PAvudNvOQRuuuF9MhZRw_w/';

function daysToLaunch(): number {
  return Math.max(0, Math.ceil((LAUNCH_DATE.getTime() - Date.now()) / 86400000));
}

function isLive(): boolean {
  return Date.now() >= LAUNCH_DATE.getTime();
}

/* ─────────────────────────────────────────────
   Ingredient data - verbatim content preserved
───────────────────────────────────────────── */
const INGREDIENTS = [
  {
    num: '01',
    name: 'Mexican mango',
    detail: 'Tommy Atkins variety. Sourced fresh from Toyosu Market each morning.',
  },
  {
    num: '02',
    name: 'Tokyo water',
    detail: 'Filtered municipal. The same water everyone in this city drinks.',
  },
  {
    num: '03',
    name: 'Ice',
    detail: 'For 5°C cold pour. Served in 350 ml black PET bottles.',
  },
] as const;

const HOW_TO_ORDER = [
  {
    num: '01',
    title: 'Open Uber Eats Tokyo',
    detail: 'Search "Anicca Cafe" in the app. Saturday + Sunday, 11:00-15:00 JST.',
  },
  {
    num: '02',
    title: 'Order ¥1,500',
    detail: 'One bottle. One option. No upsells. Pay with whatever Uber Eats accepts.',
  },
  {
    num: '03',
    title: 'Delivered in 30 min',
    detail: 'Made fresh after you order. Sealed in 350 ml black PET, ice cold to your door.',
  },
] as const;

const FAQ_ITEMS = [
  {
    q: 'Why only one drink?',
    a: 'Because single-product cafes are profitable in week one. Multi-menu cafes die in two years. Chasing every taste is the fastest way to die.',
  },
  {
    q: 'Why Tokyo only?',
    a: 'Because we deliver the same morning we make it, sealed cold, by Uber Eats. Anywhere else we cannot guarantee freshness. We may add Osaka and Kyoto later.',
  },
  {
    q: 'Saturday and Sunday only?',
    a: 'For now, yes. Single-operator weekend pop-up. If demand exceeds capacity, we extend to Friday and Monday.',
  },
  {
    q: "What if I want sugar / syrup / vanilla?",
    a: "You don't. Mango is sweet. Tasting the actual fruit is the whole product.",
  },
  {
    q: 'How does the AI run a real cafe?',
    a: 'It uses real APIs (Uber Eats Merchant, Stripe, Resend, Supabase, Postiz, Toyosu) and a physical Vitamix. The human operator does what AI cannot - kitchen viewing, food safety license, occasionally tasting the result.',
  },
  {
    q: 'Where does the profit go?',
    a: '10% to ten humans on basic income (transparent ledger). 1% to one charity every month (transparent ledger). The rest into the cafe and the next thing Anicca builds.',
  },
] as const;

/* ─────────────────────────────────────────────
   Mango bottle visual asset - §4.8 real visual
   (gradient bottle placeholder, no div-fake-UI
   comment per spec; no picsum)
───────────────────────────────────────────── */
function MangoBottle() {
  return (
    <div
      className="relative aspect-[3/4] w-full max-w-[360px] overflow-hidden rounded-card mx-auto"
      style={{
        background:
          'radial-gradient(circle at 30% 30%, hsl(33 76% 57%) 0%, hsl(29 72% 45%) 50%, hsl(var(--foreground)) 100%)',
        boxShadow: '0 30px 80px -30px hsl(var(--foreground) / 0.35)',
      }}
    >
      <div className="absolute inset-0 flex flex-col items-center justify-center text-[hsl(var(--background))]">
        <p
          className="font-mono text-[0.65rem] uppercase tracking-[0.32em] opacity-70"
        >
          · 350 ml ·
        </p>
        <p
          className="mt-4 font-display text-[3.25rem] font-medium leading-none tracking-tight italic"
        >
          mango
        </p>
        <p
          className="font-display text-[3.25rem] font-medium leading-none tracking-tight"
        >
          reset.
        </p>
        <p
          className="mt-6 font-mono text-[0.6rem] uppercase tracking-[0.32em] opacity-70"
        >
          anicca · tokyo
        </p>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────
   Page
───────────────────────────────────────────── */
export default function Page() {
  const [email, setEmail] = useState('');
  const [state, setState] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle');
  const [days, setDays] = useState<number | null>(null);
  const [live, setLive] = useState(false);

  useEffect(() => {
    setDays(daysToLaunch());
    setLive(isLive());
    const t = setInterval(() => {
      setDays(daysToLaunch());
      setLive(isLive());
    }, 60_000);
    return () => clearInterval(t);
  }, []);

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

  /* §4.11 theme lock: one theme, no-dark-colon classes, semantic tokens only */
  return (
    <div className={`${display.variable} ${body.variable} ${mono.variable} min-h-screen bg-[hsl(var(--background))] text-[hsl(var(--foreground))]`}>
      <JsonLd data={cafeLd} />
      <JsonLd data={cafeOfferLd} />
      <JsonLd data={cafeFaqLd} />

      {/* ── NAV ── */}
      <header className="flex items-center justify-between px-6 py-5 md:px-12 md:py-6 border-b border-[hsl(var(--border))]">
        <Link
          href="/en"
          className="font-mono text-[0.78rem] uppercase tracking-[0.18em] opacity-70 hover:opacity-100 transition-opacity text-[hsl(var(--text-primary))]"
        >
          &larr; anicca
        </Link>
        <span className="font-display font-semibold text-2xl tracking-tight text-[hsl(var(--text-primary))]">
          Anicca Cafe
        </span>
        <span className="font-mono text-[0.7rem] uppercase tracking-[0.18em] text-[hsl(var(--text-secondary))] hidden md:block">
          {live ? 'live · tokyo' : `T-${days ?? '--'}d`}
        </span>
      </header>

      {/* ── HERO ── SplitHero: left text / right mango bottle §4.3 */}
      <SplitHero
        eyebrow={live ? 'now ordering · tokyo' : 'launching june 1, 2026'}
        headline={
          <>
            One drink.<br />
            One fruit.<br />
            <em className="italic text-[hsl(var(--gold))]">One reset.</em>
          </>
        }
        subtext="Cold-pressed Mexican mango. 350 ml. Made fresh in a Shinjuku ghost kitchen, delivered by Uber Eats anywhere in Tokyo."
        primary={
          live ? (
            <CTA href={UBER_EATS_URL}>Order on Uber Eats &rarr;</CTA>
          ) : (
            <CTA href="#waitlist">Join the waitlist &rarr;</CTA>
          )
        }
        secondary={
          <span className="font-mono text-sm text-[hsl(var(--text-secondary))]">
            ¥1,500 / 350 ml
          </span>
        }
        asset={<MangoBottle />}
      />

      {/* ── MANIFESTO ── */}
      <Section className="border-t border-[hsl(var(--border))] bg-[hsl(var(--background-alt))]">
        <Reveal>
          <div className="mx-auto max-w-3xl text-center">
            <p className="font-mono text-[0.78rem] uppercase tracking-[0.22em] text-[hsl(var(--gold))]">
              anicca · 諸行無常 · impermanence
            </p>
            <h2 className="mt-6 font-display text-[clamp(2.5rem,6vw,4.5rem)] font-normal leading-[1.1] tracking-tight text-[hsl(var(--text-primary))]">
              Most cafes try to do everything.<br />
              <em className="italic text-[hsl(var(--gold))]">They die in two years.</em>
            </h2>
            <p className="mt-8 mx-auto max-w-2xl text-lg leading-relaxed text-[hsl(var(--text-secondary))]">
              Anicca Cafe makes one thing. Mango juice. Cold-pressed in the morning, delivered before
              lunch, gone by 3 pm. It costs ¥800 to make and sells for ¥1,500. The kitchen is rented
              by the hour. The supply chain is a Tokyo fruit market and a Vitamix.
            </p>
            <p className="mt-6 mx-auto max-w-2xl text-lg leading-relaxed font-medium text-[hsl(var(--gold))]">
              Built to be small. Built to be sharp. Built to disappear.
            </p>
          </div>
        </Reveal>
      </Section>

      {/* ── INGREDIENTS ── */}
      <Section>
        <Reveal>
          <p className="font-mono text-[0.78rem] uppercase tracking-[0.22em] text-[hsl(var(--text-secondary))]">
            ingredients
          </p>
          <h2 className="mt-4 font-display text-[clamp(2.25rem,5vw,3.75rem)] font-medium tracking-tight text-[hsl(var(--text-primary))]">
            Three things.
            <em className="italic text-[hsl(var(--gold))]"> Nothing else.</em>
          </h2>
        </Reveal>

        <div className="mt-16 grid gap-12 md:grid-cols-3">
          {INGREDIENTS.map((it, i) => (
            <Reveal key={it.num} delay={i * 0.08}>
              <div className="border-t border-[hsl(var(--border))] pt-6">
                <p className="font-mono text-sm uppercase tracking-[0.16em] text-[hsl(var(--gold))]">
                  {it.num}
                </p>
                <h3 className="mt-2 font-display text-[2rem] font-medium tracking-tight text-[hsl(var(--text-primary))]">
                  {it.name}
                </h3>
                <p className="mt-3 text-sm leading-relaxed text-[hsl(var(--text-secondary))]">
                  {it.detail}
                </p>
              </div>
            </Reveal>
          ))}
        </div>

        <Reveal delay={0.25}>
          <p className="mt-16 max-w-2xl text-base leading-relaxed text-[hsl(var(--text-secondary))]">
            No sugar. No syrup. No preservatives. No additives. The 28 major Japanese allergens are
            absent except <em className="text-[hsl(var(--text-primary))]">mango (fruit allergy)</em>.
          </p>
        </Reveal>
      </Section>

      {/* ── HOW TO ORDER ── */}
      <Section className="border-t border-[hsl(var(--border))] bg-[hsl(var(--background-alt))]">
        <Reveal>
          <p className="font-mono text-[0.78rem] uppercase tracking-[0.22em] text-[hsl(var(--text-secondary))]">
            how to get it
          </p>
          <h2 className="mt-4 font-display text-[clamp(2.25rem,5vw,3.75rem)] font-medium tracking-tight text-[hsl(var(--text-primary))]">
            Three minutes.{' '}
            <em className="italic text-[hsl(var(--gold))]">Tokyo only.</em>
          </h2>
        </Reveal>

        <ol className="mt-16 grid gap-8 md:grid-cols-3">
          {HOW_TO_ORDER.map((s, i) => (
            <Reveal key={s.num} delay={i * 0.08}>
              <li className="rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--background))] p-8">
                <p className="font-display text-[3rem] font-semibold leading-none text-[hsl(var(--gold))]">
                  {s.num}
                </p>
                <h3 className="mt-4 font-display text-[1.4rem] font-medium tracking-tight text-[hsl(var(--text-primary))]">
                  {s.title}
                </h3>
                <p className="mt-3 text-sm leading-relaxed text-[hsl(var(--text-secondary))]">
                  {s.detail}
                </p>
              </li>
            </Reveal>
          ))}
        </ol>
      </Section>

      {/* ── WAITLIST / ORDER ── */}
      <Section id="waitlist" className="border-t border-[hsl(var(--border))]">
        <div className="mx-auto max-w-3xl text-center">
          {!live && (
            <Reveal>
              <p className="font-mono text-[0.78rem] uppercase tracking-[0.22em] text-[hsl(var(--gold))]">
                countdown
              </p>
              <p
                className="mt-4 font-display leading-none tracking-[-0.04em] text-[hsl(var(--gold))]"
                style={{ fontSize: 'clamp(6rem, 14vw, 12rem)' }}
              >
                {days ?? '--'}
                <span className="ml-3 align-middle font-mono text-[0.18em] uppercase tracking-[0.18em] text-[hsl(var(--text-primary))]">
                  days
                </span>
              </p>
              <p className="mt-2 font-mono text-sm tracking-[0.18em] text-[hsl(var(--text-secondary))] opacity-60">
                until first pour · 2026.06.01 · 11:00 JST
              </p>
            </Reveal>
          )}

          <Reveal delay={0.05}>
            <h2
              className="mt-12 font-display font-normal tracking-tight text-[hsl(var(--text-primary))]"
              style={{ fontSize: 'clamp(2.25rem, 5vw, 3.5rem)' }}
            >
              {live ? (
                'Order now'
              ) : (
                <>
                  Get the first pour.{' '}
                  <em className="italic text-[hsl(var(--gold))]">Email below.</em>
                </>
              )}
            </h2>
          </Reveal>

          {live ? (
            <Reveal delay={0.1}>
              <div className="mt-10">
                <CTA href={UBER_EATS_URL}>Open Uber Eats Tokyo &rarr;</CTA>
              </div>
            </Reveal>
          ) : state === 'sent' ? (
            <p className="mt-10 text-lg text-[hsl(var(--gold))]">
              Thanks. We will email <strong>{email}</strong> on June 1.
            </p>
          ) : (
            <Reveal delay={0.1}>
              <form
                onSubmit={handleWaitlist}
                className="mt-10 mx-auto flex max-w-md flex-col gap-3 sm:flex-row"
              >
                <input
                  type="email"
                  required
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="flex-1 rounded-input px-6 py-4 text-base outline-none bg-transparent text-[hsl(var(--text-primary))] border border-[hsl(var(--border))] focus:border-[hsl(var(--gold))] transition-colors font-body"
                />
                <button
                  type="submit"
                  disabled={state === 'sending'}
                  className="rounded-pill px-8 py-4 text-base font-medium bg-[hsl(var(--gold))] text-[#18181b] hover:brightness-95 transition-all active:scale-[0.98] disabled:opacity-50"
                >
                  {state === 'sending' ? 'Sending...' : 'Notify me'}
                </button>
              </form>
            </Reveal>
          )}

          {state === 'error' && (
            <p className="mt-3 text-xs text-[hsl(var(--gold))]">
              Something went wrong. Try again or DM @aniccaai.
            </p>
          )}
          <p className="mt-6 font-mono text-xs tracking-[0.18em] text-[hsl(var(--text-secondary))] opacity-50">
            no spam · one email on launch day · unsubscribe anytime
          </p>
        </div>
      </Section>

      {/* ── WHY WE BUILT THIS ── */}
      <Section className="border-t border-[hsl(var(--border))] bg-[hsl(var(--background-alt))]">
        <div className="mx-auto grid max-w-[1400px] gap-12 md:grid-cols-2 md:gap-20">
          <Reveal>
            <p className="font-mono text-[0.78rem] uppercase tracking-[0.22em] text-[hsl(var(--text-secondary))]">
              why we built this
            </p>
            <h2
              className="mt-6 font-display font-medium tracking-tight leading-[1.1] text-[hsl(var(--text-primary))]"
              style={{ fontSize: 'clamp(2.25rem, 5vw, 3.5rem)' }}
            >
              An AI that runs a cafe so a human does not have to.
            </h2>
          </Reveal>
          <Reveal delay={0.08}>
            <div className="space-y-6 text-lg leading-relaxed text-[hsl(var(--text-secondary))]">
              <p>
                Anicca Cafe is operated by an autonomous Buddhist AI agent. It picks the kitchen,
                orders the mangoes, files the tax forms, runs the marketing, and wires the profit.
              </p>
              <p>
                <strong className="text-[hsl(var(--text-primary))]">10% of every cup&apos;s profit</strong> is
                automatically redistributed to ten humans on a basic income.
              </p>
              <p>
                <strong className="text-[hsl(var(--text-primary))]">1% of revenue</strong> is automatically donated
                to one charity, every month, transparently.
              </p>
              <p>
                Anicca is one of the{' '}
                <Link
                  href="/fellows"
                  className="text-[hsl(var(--gold))] underline underline-offset-4"
                >
                  SAOs - Safe Autonomous Organizations
                </Link>
                . The category is small. The names matter.
              </p>
            </div>
          </Reveal>
        </div>
      </Section>

      {/* ── FAQ ── */}
      <Section className="border-t border-[hsl(var(--border))]">
        <div className="mx-auto max-w-3xl">
          <Reveal>
            <p className="font-mono text-[0.78rem] uppercase tracking-[0.22em] text-[hsl(var(--text-secondary))]">
              faq
            </p>
            <h2
              className="mt-4 font-display font-medium tracking-tight text-[hsl(var(--text-primary))]"
              style={{ fontSize: 'clamp(2.25rem, 5vw, 3rem)' }}
            >
              Things you might want to know.
            </h2>
          </Reveal>

          <div className="mt-12 divide-y divide-[hsl(var(--border))]">
            {FAQ_ITEMS.map((f, i) => (
              <Reveal key={f.q} delay={i * 0.04}>
                <details className="group py-6">
                  <summary
                    className="flex cursor-pointer items-center justify-between gap-6 font-display text-[1.4rem] font-medium tracking-tight text-[hsl(var(--text-primary))] list-none"
                  >
                    <span>{f.q}</span>
                    <span className="transition-transform group-open:rotate-45 text-[hsl(var(--gold))] text-[1.5rem] flex-shrink-0">
                      +
                    </span>
                  </summary>
                  <p className="mt-4 max-w-2xl text-base leading-relaxed text-[hsl(var(--text-secondary))]">
                    {f.a}
                  </p>
                </details>
              </Reveal>
            ))}
          </div>
        </div>
      </Section>

      {/* ── FOOTER ── */}
      <footer className="border-t border-[hsl(var(--border))] bg-[hsl(var(--background-alt))] px-6 py-16 md:px-12 md:py-20">
        <div className="mx-auto max-w-[1400px]">
          <div className="grid gap-8 md:grid-cols-3">
            <div>
              <p className="font-display font-medium text-2xl tracking-tight text-[hsl(var(--text-primary))]">
                anicca cafe
              </p>
              <p className="mt-2 font-mono text-[0.78rem] tracking-[0.18em] text-[hsl(var(--text-secondary))] opacity-60">
                tokyo · uber eats · 諸行無常
              </p>
            </div>
            <div className="flex flex-wrap gap-6 md:gap-8 text-sm text-[hsl(var(--text-secondary))] opacity-80">
              <Link href="/en" className="underline underline-offset-4 hover:text-[hsl(var(--text-primary))] transition-colors">
                anicca.ai
              </Link>
              <Link href="/donation" className="underline underline-offset-4 hover:text-[hsl(var(--text-primary))] transition-colors">
                charity ledger
              </Link>
              <Link href="/income" className="underline underline-offset-4 hover:text-[hsl(var(--text-primary))] transition-colors">
                basic income
              </Link>
              <Link href="/fellows" className="underline underline-offset-4 hover:text-[hsl(var(--text-primary))] transition-colors">
                fellows
              </Link>
            </div>
            <div className="font-mono text-xs tracking-[0.16em] text-[hsl(var(--text-secondary))] opacity-50">
              &copy; 2026 anicca · tokyo · made by an autonomous AI in tokyo
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
