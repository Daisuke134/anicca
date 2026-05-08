/* eslint-disable react/no-unescaped-entities */
'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Cormorant_Garamond, IBM_Plex_Sans, IBM_Plex_Mono } from 'next/font/google';

const display = Cormorant_Garamond({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
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

const LAUNCH_DATE = new Date('2026-06-01T11:00:00+09:00');
const UBER_EATS_URL = 'https://www.ubereats.com/tokyo/food-delivery/anicca-cafe/PAvudNvOQRuuuF9MhZRw_w/';

function daysToLaunch(): number {
  return Math.max(0, Math.ceil((LAUNCH_DATE.getTime() - Date.now()) / 86400000));
}

function isLive(): boolean {
  return Date.now() >= LAUNCH_DATE.getTime();
}

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

  return (
    <div
      className={`${display.variable} ${body.variable} ${mono.variable} min-h-screen`}
      style={{
        background: '#FBF7EF',
        color: '#14100E',
        fontFamily: 'var(--font-body)',
      }}
    >
      <style jsx global>{`
        :root {
          --ink: #14100E;
          --cream: #FBF7EF;
          --mango: #E89A3C;
          --beige: #C4A77A;
          --dim: #6B6258;
        }
        @keyframes anicca-fade-up {
          from { opacity: 0; transform: translateY(12px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes anicca-mango-bob {
          0%, 100% { transform: translateY(0) rotate(-2deg); }
          50%      { transform: translateY(-8px) rotate(2deg); }
        }
        .anicca-anim-1 { animation: anicca-fade-up 0.8s 0.0s both ease-out; }
        .anicca-anim-2 { animation: anicca-fade-up 0.8s 0.15s both ease-out; }
        .anicca-bottle { animation: anicca-mango-bob 6s infinite ease-in-out; }
      `}</style>

      <header
        className="flex items-center justify-between px-6 py-5 md:px-12 md:py-6"
        style={{ borderBottom: '1px solid #14100E' }}
      >
        <Link
          href="/en"
          style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', letterSpacing: '0.18em' }}
          className="uppercase opacity-70 hover:opacity-100 transition-opacity"
        >
          ← anicca
        </Link>
        <div
          style={{
            fontFamily: 'var(--font-display)',
            fontWeight: 600,
            fontSize: '1.5rem',
            letterSpacing: '0.02em',
          }}
        >
          Anicca Cafe
        </div>
        <span
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '0.7rem',
            letterSpacing: '0.18em',
            color: 'var(--dim)',
          }}
          className="uppercase hidden md:block"
        >
          {live ? 'live · tokyo' : `T-${days ?? '–'}d`}
        </span>
      </header>

      <section className="px-6 py-16 md:px-12 md:py-28">
        <div className="mx-auto grid max-w-6xl gap-12 md:grid-cols-2 md:items-center md:gap-16">
          <div className="anicca-anim-1">
            <p
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '0.78rem',
                letterSpacing: '0.22em',
                color: 'var(--mango)',
              }}
              className="uppercase mb-6"
            >
              {live ? '— now ordering · tokyo' : '— launching june 1, 2026'}
            </p>
            <h1
              style={{
                fontFamily: 'var(--font-display)',
                fontWeight: 500,
                fontSize: 'clamp(3.5rem, 8vw, 6.75rem)',
                lineHeight: 0.95,
                letterSpacing: '-0.02em',
              }}
            >
              One drink.
              <br />
              One fruit.
              <br />
              <em style={{ fontStyle: 'italic', color: 'var(--mango)' }}>One reset.</em>
            </h1>
            <p className="mt-8 max-w-md text-lg leading-relaxed" style={{ color: 'var(--dim)' }}>
              Cold-pressed Mexican mango. 350 ml. Made fresh in a Shinjuku ghost kitchen, delivered
              by Uber Eats anywhere in Tokyo.
            </p>

            <div className="mt-10 flex flex-wrap items-center gap-4">
              {live ? (
                <a
                  href={UBER_EATS_URL}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-block rounded-full px-9 py-4 text-base font-medium transition-all hover:scale-[1.02]"
                  style={{
                    background: 'var(--ink)',
                    color: 'var(--cream)',
                    fontFamily: 'var(--font-body)',
                    letterSpacing: '0.04em',
                  }}
                >
                  Order on Uber Eats →
                </a>
              ) : (
                <a
                  href="#waitlist"
                  className="inline-block rounded-full px-9 py-4 text-base font-medium transition-all hover:scale-[1.02]"
                  style={{
                    background: 'var(--ink)',
                    color: 'var(--cream)',
                    fontFamily: 'var(--font-body)',
                    letterSpacing: '0.04em',
                  }}
                >
                  Join the waitlist →
                </a>
              )}
              <span
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.85rem',
                  color: 'var(--dim)',
                }}
              >
                ¥1,500 / 350 ml
              </span>
            </div>
          </div>

          <div className="anicca-anim-2 flex justify-center">
            <div
              className="anicca-bottle relative aspect-[3/4] w-full max-w-[360px] overflow-hidden rounded-3xl"
              style={{
                background:
                  'radial-gradient(circle at 30% 30%, #E89A3C 0%, #C97A1F 50%, #14100E 100%)',
                boxShadow: '0 30px 80px -30px rgba(20,16,14,0.5)',
              }}
            >
              <div
                className="absolute inset-0 flex flex-col items-center justify-center"
                style={{ color: 'var(--cream)' }}
              >
                <div
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.7rem',
                    letterSpacing: '0.32em',
                  }}
                  className="uppercase opacity-70"
                >
                  · 350 ml ·
                </div>
                <div
                  style={{
                    fontFamily: 'var(--font-display)',
                    fontWeight: 500,
                    fontSize: '3.25rem',
                    lineHeight: 1,
                    letterSpacing: '-0.02em',
                  }}
                  className="mt-4 italic"
                >
                  mango
                </div>
                <div
                  style={{
                    fontFamily: 'var(--font-display)',
                    fontWeight: 500,
                    fontSize: '3.25rem',
                    lineHeight: 1,
                    letterSpacing: '-0.02em',
                  }}
                >
                  reset.
                </div>
                <div
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.65rem',
                    letterSpacing: '0.32em',
                  }}
                  className="mt-6 uppercase opacity-70"
                >
                  anicca · tokyo
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="px-6 py-20 md:px-12 md:py-32" style={{ background: 'var(--ink)' }}>
        <div className="mx-auto max-w-3xl text-center" style={{ color: 'var(--cream)' }}>
          <p
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '0.78rem',
              letterSpacing: '0.22em',
              color: 'var(--mango)',
            }}
            className="uppercase"
          >
            anicca · 諸行無常 · impermanence
          </p>
          <h2
            style={{
              fontFamily: 'var(--font-display)',
              fontWeight: 400,
              fontSize: 'clamp(2.5rem, 6vw, 4.5rem)',
              lineHeight: 1.1,
              letterSpacing: '-0.01em',
            }}
            className="mt-6"
          >
            Most cafes try to do everything.
            <br />
            <em style={{ fontStyle: 'italic', color: 'var(--mango)' }}>They die in two years.</em>
          </h2>
          <p
            className="mt-8 mx-auto max-w-2xl text-lg leading-relaxed opacity-80"
            style={{ color: 'var(--cream)' }}
          >
            Anicca Cafe makes one thing. Mango juice. Cold-pressed in the morning, delivered before
            lunch, gone by 3 pm. It costs ¥800 to make and sells for ¥1,500. The kitchen is rented
            by the hour. The supply chain is a Tokyo fruit market and a Vitamix.
          </p>
          <p className="mt-6 mx-auto max-w-2xl text-lg leading-relaxed" style={{ color: 'var(--mango)' }}>
            Built to be small. Built to be sharp. Built to disappear.
          </p>
        </div>
      </section>

      <section className="px-6 py-20 md:px-12 md:py-28">
        <div className="mx-auto max-w-5xl">
          <p
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '0.78rem',
              letterSpacing: '0.22em',
              color: 'var(--dim)',
            }}
            className="uppercase"
          >
            ── ingredients ──
          </p>
          <h2
            style={{
              fontFamily: 'var(--font-display)',
              fontWeight: 500,
              fontSize: 'clamp(2.25rem, 5vw, 3.75rem)',
              letterSpacing: '-0.01em',
            }}
            className="mt-4"
          >
            Three things.
            <em style={{ fontStyle: 'italic', color: 'var(--mango)' }}> Nothing else.</em>
          </h2>

          <div className="mt-16 grid gap-12 md:grid-cols-3">
            {[
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
            ].map((it) => (
              <div key={it.num} style={{ borderTop: '1px solid #14100E' }} className="pt-6">
                <p
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.85rem',
                    letterSpacing: '0.16em',
                    color: 'var(--mango)',
                  }}
                  className="uppercase"
                >
                  {it.num}
                </p>
                <h3
                  style={{
                    fontFamily: 'var(--font-display)',
                    fontWeight: 500,
                    fontSize: '2rem',
                    letterSpacing: '-0.01em',
                  }}
                  className="mt-2"
                >
                  {it.name}
                </h3>
                <p className="mt-3 text-sm leading-relaxed" style={{ color: 'var(--dim)' }}>
                  {it.detail}
                </p>
              </div>
            ))}
          </div>

          <p className="mt-16 max-w-2xl text-base leading-relaxed" style={{ color: 'var(--dim)' }}>
            No sugar. No syrup. No preservatives. No additives. The 28 major Japanese allergens are
            absent except <em style={{ color: 'var(--ink)' }}>mango (fruit allergy)</em>.
          </p>
        </div>
      </section>

      <section
        className="px-6 py-20 md:px-12 md:py-28"
        style={{ background: 'var(--cream)', borderTop: '1px solid #14100E' }}
      >
        <div className="mx-auto max-w-5xl">
          <p
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '0.78rem',
              letterSpacing: '0.22em',
              color: 'var(--dim)',
            }}
            className="uppercase"
          >
            ── how to get it ──
          </p>
          <h2
            style={{
              fontFamily: 'var(--font-display)',
              fontWeight: 500,
              fontSize: 'clamp(2.25rem, 5vw, 3.75rem)',
              letterSpacing: '-0.01em',
            }}
            className="mt-4"
          >
            Three minutes. <em style={{ fontStyle: 'italic', color: 'var(--mango)' }}>Tokyo only.</em>
          </h2>

          <ol className="mt-16 grid gap-8 md:grid-cols-3">
            {[
              {
                num: '①',
                title: 'Open Uber Eats Tokyo',
                detail: 'Search "Anicca Cafe" in the app. Saturday + Sunday, 11:00–15:00 JST.',
              },
              {
                num: '②',
                title: 'Order ¥1,500',
                detail: 'One bottle. One option. No upsells. Pay with whatever Uber Eats accepts.',
              },
              {
                num: '③',
                title: 'Delivered in 30 min',
                detail: 'Made fresh after you order. Sealed in 350 ml black PET, ice cold to your door.',
              },
            ].map((s) => (
              <li
                key={s.num}
                className="rounded-3xl p-8"
                style={{ background: 'var(--cream)', border: '1px solid #14100E' }}
              >
                <p
                  style={{
                    fontFamily: 'var(--font-display)',
                    fontWeight: 600,
                    fontSize: '3rem',
                    color: 'var(--mango)',
                    lineHeight: 1,
                  }}
                >
                  {s.num}
                </p>
                <h3
                  style={{
                    fontFamily: 'var(--font-display)',
                    fontWeight: 500,
                    fontSize: '1.4rem',
                    letterSpacing: '-0.01em',
                  }}
                  className="mt-4"
                >
                  {s.title}
                </h3>
                <p className="mt-3 text-sm leading-relaxed" style={{ color: 'var(--dim)' }}>
                  {s.detail}
                </p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section
        id="waitlist"
        className="px-6 py-24 md:px-12 md:py-36"
        style={{ background: 'var(--ink)', color: 'var(--cream)' }}
      >
        <div className="mx-auto max-w-3xl text-center">
          {!live && (
            <>
              <p
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.78rem',
                  letterSpacing: '0.22em',
                  color: 'var(--mango)',
                }}
                className="uppercase"
              >
                — countdown
              </p>
              <p
                style={{
                  fontFamily: 'var(--font-display)',
                  fontWeight: 400,
                  fontSize: 'clamp(6rem, 14vw, 12rem)',
                  lineHeight: 1,
                  letterSpacing: '-0.04em',
                  color: 'var(--mango)',
                }}
                className="mt-4"
              >
                {days ?? '—'}
                <span
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.18em',
                    letterSpacing: '0.18em',
                    color: 'var(--cream)',
                  }}
                  className="ml-3 align-middle uppercase"
                >
                  days
                </span>
              </p>
              <p
                className="mt-2 opacity-60"
                style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', letterSpacing: '0.18em' }}
              >
                until first pour · 2026.06.01 · 11:00 JST
              </p>
            </>
          )}

          <h2
            style={{
              fontFamily: 'var(--font-display)',
              fontWeight: 400,
              fontSize: 'clamp(2.25rem, 5vw, 3.5rem)',
              letterSpacing: '-0.01em',
            }}
            className="mt-12"
          >
            {live ? (
              'Order now'
            ) : (
              <>
                Get the first pour.{' '}
                <em style={{ fontStyle: 'italic', color: 'var(--mango)' }}>Email below.</em>
              </>
            )}
          </h2>

          {live ? (
            <div className="mt-10">
              <a
                href={UBER_EATS_URL}
                target="_blank"
                rel="noreferrer"
                className="inline-block rounded-full px-12 py-5 text-base font-medium transition-all hover:scale-[1.02]"
                style={{
                  background: 'var(--mango)',
                  color: 'var(--ink)',
                  fontFamily: 'var(--font-body)',
                  letterSpacing: '0.04em',
                }}
              >
                Open Uber Eats Tokyo →
              </a>
            </div>
          ) : state === 'sent' ? (
            <p className="mt-10 text-lg" style={{ color: 'var(--mango)' }}>
              Thanks. We'll email <strong>{email}</strong> on June 1.
            </p>
          ) : (
            <form onSubmit={handleWaitlist} className="mt-10 mx-auto flex max-w-md flex-col gap-3 sm:flex-row">
              <input
                type="email"
                required
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="flex-1 rounded-full px-6 py-4 text-base outline-none"
                style={{
                  background: 'transparent',
                  color: 'var(--cream)',
                  border: '1px solid #C4A77A',
                  fontFamily: 'var(--font-body)',
                }}
              />
              <button
                type="submit"
                disabled={state === 'sending'}
                className="rounded-full px-8 py-4 text-base font-medium transition-opacity hover:opacity-90 disabled:opacity-50"
                style={{
                  background: 'var(--mango)',
                  color: 'var(--ink)',
                  fontFamily: 'var(--font-body)',
                  letterSpacing: '0.04em',
                }}
              >
                {state === 'sending' ? 'Sending…' : 'Notify me'}
              </button>
            </form>
          )}
          {state === 'error' && (
            <p className="mt-3 text-xs" style={{ color: '#E89A3C' }}>
              Something went wrong. Try again or DM @aniccaai.
            </p>
          )}
          <p
            className="mt-6 text-xs opacity-50"
            style={{ fontFamily: 'var(--font-mono)', letterSpacing: '0.18em' }}
          >
            no spam · one email on launch day · unsubscribe anytime
          </p>
        </div>
      </section>

      <section className="px-6 py-20 md:px-12 md:py-28">
        <div className="mx-auto grid max-w-6xl gap-12 md:grid-cols-2 md:gap-20">
          <div>
            <p
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '0.78rem',
                letterSpacing: '0.22em',
                color: 'var(--dim)',
              }}
              className="uppercase"
            >
              ── why we built this ──
            </p>
            <h2
              style={{
                fontFamily: 'var(--font-display)',
                fontWeight: 500,
                fontSize: 'clamp(2.25rem, 5vw, 3.5rem)',
                letterSpacing: '-0.01em',
                lineHeight: 1.1,
              }}
              className="mt-6"
            >
              An AI that runs a cafe so a human doesn't have to.
            </h2>
          </div>
          <div className="space-y-6 text-lg leading-relaxed" style={{ color: 'var(--dim)' }}>
            <p>
              Anicca Cafe is operated by an autonomous Buddhist AI agent. It picks the kitchen,
              orders the mangoes, files the tax forms, runs the marketing, and wires the profit.
            </p>
            <p>
              <strong style={{ color: 'var(--ink)' }}>10% of every cup's profit</strong> is
              automatically redistributed to ten humans on a basic income.
            </p>
            <p>
              <strong style={{ color: 'var(--ink)' }}>1% of revenue</strong> is automatically donated
              to one charity, every month, transparently.
            </p>
            <p>
              The whole system is open source.{' '}
              <a
                href="https://github.com/Daisuke134/anicca"
                target="_blank"
                rel="noreferrer"
                style={{ color: 'var(--mango)', textDecoration: 'underline', textUnderlineOffset: '4px' }}
              >
                github.com/Daisuke134/anicca
              </a>
              . Fork it. Run your own cafe. Or your own anything.
            </p>
          </div>
        </div>
      </section>

      <section className="px-6 py-20 md:px-12 md:py-28" style={{ borderTop: '1px solid #14100E' }}>
        <div className="mx-auto max-w-3xl">
          <p
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '0.78rem',
              letterSpacing: '0.22em',
              color: 'var(--dim)',
            }}
            className="uppercase"
          >
            ── faq ──
          </p>
          <h2
            style={{
              fontFamily: 'var(--font-display)',
              fontWeight: 500,
              fontSize: 'clamp(2.25rem, 5vw, 3rem)',
              letterSpacing: '-0.01em',
            }}
            className="mt-4"
          >
            Things you might want to know.
          </h2>

          <div className="mt-12 divide-y" style={{ borderColor: '#14100E' }}>
            {[
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
                q: 'What if I want sugar / syrup / vanilla?',
                a: 'You don\'t. Mango is sweet. Tasting the actual fruit is the whole product.',
              },
              {
                q: 'How does the AI run a real cafe?',
                a: 'It uses real APIs (Uber Eats Merchant, Stripe, Resend, Supabase, Postiz, Toyosu) and a physical Vitamix. The human (Daisuke) does what AI cannot — kitchen viewing, food safety license, occasionally tasting the result.',
              },
              {
                q: 'Where does the profit go?',
                a: '10% to ten humans on basic income (transparent ledger). 1% to one charity every month (transparent ledger). The rest into the cafe and the next thing Anicca builds.',
              },
            ].map((f) => (
              <details key={f.q} className="group py-6">
                <summary
                  className="flex cursor-pointer items-center justify-between gap-6 text-lg"
                  style={{
                    fontFamily: 'var(--font-display)',
                    fontWeight: 500,
                    fontSize: '1.4rem',
                    letterSpacing: '-0.01em',
                  }}
                >
                  <span>{f.q}</span>
                  <span
                    className="transition-transform group-open:rotate-45"
                    style={{ color: 'var(--mango)', fontSize: '1.5rem' }}
                  >
                    +
                  </span>
                </summary>
                <p className="mt-4 max-w-2xl text-base leading-relaxed" style={{ color: 'var(--dim)' }}>
                  {f.a}
                </p>
              </details>
            ))}
          </div>
        </div>
      </section>

      <footer
        className="px-6 py-16 md:px-12 md:py-20"
        style={{ background: 'var(--ink)', color: 'var(--cream)' }}
      >
        <div className="mx-auto max-w-6xl">
          <div className="grid gap-8 md:grid-cols-3">
            <div>
              <p
                style={{
                  fontFamily: 'var(--font-display)',
                  fontWeight: 500,
                  fontSize: '1.5rem',
                  letterSpacing: '0.02em',
                }}
              >
                anicca cafe
              </p>
              <p
                className="mt-2 opacity-60"
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.78rem',
                  letterSpacing: '0.18em',
                }}
              >
                tokyo · uber eats · 諸行無常
              </p>
            </div>
            <div className="flex flex-wrap gap-6 md:gap-8 text-sm opacity-80">
              <Link href="/en" style={{ textDecoration: 'underline', textUnderlineOffset: '4px' }}>
                anicca.ai
              </Link>
              <Link href="/donation" style={{ textDecoration: 'underline', textUnderlineOffset: '4px' }}>
                charity ledger
              </Link>
              <Link href="/income" style={{ textDecoration: 'underline', textUnderlineOffset: '4px' }}>
                basic income
              </Link>
              <a
                href="https://github.com/Daisuke134/anicca"
                target="_blank"
                rel="noreferrer"
                style={{ textDecoration: 'underline', textUnderlineOffset: '4px' }}
              >
                github
              </a>
            </div>
            <div
              className="text-xs opacity-50"
              style={{ fontFamily: 'var(--font-mono)', letterSpacing: '0.16em' }}
            >
              © 2026 anicca · tokyo · made by an autonomous AI in tokyo
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
