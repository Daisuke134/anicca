/* eslint-disable react/no-unescaped-entities */
'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Cormorant_Garamond, IBM_Plex_Sans, IBM_Plex_Mono } from 'next/font/google';
import JsonLd from '@/components/JsonLd';
import { ManifestoHero, Section, Reveal } from '@/components/site/taste';

const retreatLd = {
  '@context': 'https://schema.org',
  '@type': 'Service',
  name: 'Anicca Retreat',
  serviceType: 'Silent Vipassana-style meditation retreat',
  provider: { '@type': 'Organization', name: 'Anicca', url: 'https://aniccaai.com' },
  areaServed: 'Japan',
  url: 'https://aniccaai.com/retreat',
  description:
    'A silent, Vipassana-style meditation retreat organised by Anicca in Japan - built around the single observation of impermanence (anicca).',
};
const retreatFaqLd = {
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: [
    { '@type': 'Question', name: 'What is the Anicca Retreat?', acceptedAnswer: { '@type': 'Answer', text: 'A silent meditation retreat in Japan in the Vipassana tradition, organised by Anicca. The focus is direct observation of impermanence rather than instruction-heavy programming.' } },
    { '@type': 'Question', name: 'Where is it held?', acceptedAnswer: { '@type': 'Answer', text: 'In Japan; the exact location and dates are announced through Anicca channels at aniccaai.com/retreat.' } },
    { '@type': 'Question', name: 'Is it really silent?', acceptedAnswer: { '@type': 'Answer', text: 'Yes - noble silence for the core days, the standard structure for a Vipassana-style retreat.' } },
    { '@type': 'Question', name: 'Who is it for?', acceptedAnswer: { '@type': 'Answer', text: 'People searching for a Vipassana Tokyo / silent retreat Japan experience who want depth over comfort.' } },
    { '@type': 'Question', name: 'How do I apply?', acceptedAnswer: { '@type': 'Answer', text: 'Via aniccaai.com/retreat - register interest and Anicca follows up with the schedule.' } },
  ],
};

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

type Retreat = {
  id: string;
  city: string;
  start: string;       // ISO date
  end: string;         // ISO date
  capacity: number;
  remaining: number;
  status: 'open' | 'searching' | 'closed';
  venueName?: string;
};

// Static seed; phase2-schedule-publish.sh swaps these from state.json on deploy.
const SEED_RETREATS: Retreat[] = [
  { id: 'tokyo-2026-07', city: 'Tokyo', start: '2026-07-18', end: '2026-07-28', capacity: 12, remaining: 12, status: 'searching' },
  { id: 'tokyo-2026-08', city: 'Tokyo', start: '2026-08-15', end: '2026-08-25', capacity: 12, remaining: 12, status: 'searching' },
  { id: 'tokyo-2026-09', city: 'Tokyo', start: '2026-09-19', end: '2026-09-29', capacity: 12, remaining: 12, status: 'searching' },
];

const TIMETABLE: ReadonlyArray<readonly [string, string]> = [
  ['04:00', 'Wake bell'],
  ['04:30', 'Meditate (hall · cell)'],
  ['06:30', 'Breakfast'],
  ['08:00', 'Group meditation'],
  ['09:00', 'Meditate'],
  ['11:00', 'Lunch'],
  ['12:00', 'Rest · teacher interview'],
  ['13:00', 'Meditate'],
  ['14:30', 'Group meditation'],
  ['15:30', 'Meditate'],
  ['17:00', 'Tea (fruit for new students)'],
  ['18:00', 'Group meditation'],
  ['19:00', 'Discourse'],
  ['20:15', 'Group meditation'],
  ['21:00', 'Question time'],
  ['21:30', 'Lights out'],
];

const PRECEPTS: ReadonlyArray<readonly [string, string]> = [
  ['I',    'Abstain from killing.'],
  ['II',   'Abstain from stealing.'],
  ['III',  'Abstain from sexual activity.'],
  ['IV',   'Abstain from false speech.'],
  ['V',    'Abstain from intoxicants.'],
  ['VI',   'No food after midday. (returning students)'],
  ['VII',  'No entertainment, ornament, scent. (returning students)'],
  ['VIII', 'No high or luxurious bed. (returning students)'],
];

function fmtRange(start: string, end: string): string {
  const s = new Date(start);
  const e = new Date(end);
  const opt: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric' };
  return `${s.toLocaleDateString('en-US', opt)} -> ${e.toLocaleDateString('en-US', opt)}, ${e.getFullYear()}`;
}

export default function RetreatPage() {
  const [retreats] = useState<Retreat[]>(SEED_RETREATS);
  const [email, setEmail] = useState('');
  const [retreatId, setRetreatId] = useState<string>(SEED_RETREATS[0]?.id ?? '');
  const [motive, setMotive] = useState('');
  const [prior, setPrior] = useState<'none' | 'one' | 'multiple'>('none');
  const [state, setState] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle');
  const [ledgerLoaded, setLedgerLoaded] = useState(false);
  const [ledger, setLedger] = useState<{ donations: number; subsidy: number; expenses: number; net: number } | null>(null);

  useEffect(() => {
    fetch('/dashboard.json')
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        const donation = Math.round(d?.mrr?.by_product?.['retreat-donation'] ?? 0);
        const subsidy = Math.round(d?.mrr?.by_product?.['retreat-subsidy'] ?? 0);
        const expenses = Math.round(d?.spend?.by_category?.['retreat'] ?? 0);
        setLedger({
          donations: donation,
          subsidy,
          expenses,
          net: donation + subsidy - expenses,
        });
      })
      .catch(() => {})
      .finally(() => setLedgerLoaded(true));
  }, []);

  async function handleApply(e: React.FormEvent) {
    e.preventDefault();
    if (!email) return;
    setState('sending');
    try {
      const r = await fetch('/.netlify/functions/retreat-application', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, retreatId, motive, prior }),
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
        background: '#F2EBDD',
        color: '#1B1410',
        fontFamily: 'var(--font-body)',
        fontWeight: 300,
      }}
    >
      <JsonLd data={retreatLd} />
      <JsonLd data={retreatFaqLd} />
      <style jsx global>{`
        :root {
          --ink: #1B1410;
          --paper: #F2EBDD;
          --terra: #8E3B1F;
          --moss: #4A5A3B;
          --dim: #6F635A;
          --rule: rgba(27, 20, 16, 0.18);
        }
        @keyframes retreat-fade-up {
          from { opacity: 0; transform: translateY(14px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes retreat-rule-grow {
          from { transform: scaleX(0); }
          to   { transform: scaleX(1); }
        }
        .r-anim-1 { animation: retreat-fade-up 1.2s 0.0s both ease-out; }
        .r-anim-2 { animation: retreat-fade-up 1.2s 0.6s both ease-out; }
        .r-anim-3 { animation: retreat-fade-up 1.2s 1.2s both ease-out; }
        .r-rule   { transform-origin: left; animation: retreat-rule-grow 2s 0.4s both cubic-bezier(0.22, 1, 0.36, 1); }
        .grain::before {
          content: '';
          position: absolute; inset: 0;
          pointer-events: none;
          opacity: 0.06;
          mix-blend-mode: multiply;
          background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%25' height='100%25' filter='url(%23n)'/></svg>");
        }
        .roman {
          font-family: var(--font-display);
          font-style: italic;
          font-weight: 400;
          color: var(--terra);
          letter-spacing: 0.04em;
        }
      `}</style>

      {/* HEADER */}
      <header
        className="relative flex items-center justify-between px-6 py-5 md:px-12"
        style={{ borderBottom: '1px solid var(--rule)' }}
      >
        <Link
          href="/en"
          style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', letterSpacing: '0.22em' }}
          className="uppercase opacity-60 hover:opacity-100 transition-opacity"
        >
          {'<-'} anicca
        </Link>
        <div
          style={{
            fontFamily: 'var(--font-display)',
            fontWeight: 500,
            fontSize: '1.4rem',
            letterSpacing: '0.06em',
          }}
        >
          Anicca <span style={{ fontStyle: 'italic', color: 'var(--terra)' }}>Retreats</span>
        </div>
        <span
          style={{ fontFamily: 'var(--font-mono)', fontSize: '0.68rem', letterSpacing: '0.22em' }}
          className="uppercase opacity-60"
        >
          v1 · 2026
        </span>
      </header>

      {/* HERO */}
      <ManifestoHero
        headline={
          <span
            style={{
              fontFamily: 'var(--font-display)',
              fontSize: 'clamp(3.5rem, 9vw, 7rem)',
              fontWeight: 400,
              lineHeight: 0.95,
              letterSpacing: '-0.02em',
              color: 'var(--ink)',
            }}
          >
            <span className="r-anim-2 block">Sit.</span>
            <span className="r-anim-2 block">For ten days.</span>
            <span className="r-anim-2 block" style={{ fontStyle: 'italic', color: 'var(--terra)' }}>In silence.</span>
          </span>
        }
        subtext="One retreat each month. Twelve seats. No fee. The body is given a building. The mind is given a schedule. The schedule is given to the breath."
        cta={
          <p
            className="r-anim-1 uppercase"
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '0.72rem',
              letterSpacing: '0.32em',
              color: 'var(--dim)',
            }}
          >
            Physical sangha · Tokyo · 2026
          </p>
        }
      />

      {/* THREE VOWS */}
      <Section>
        <div
          className="mx-auto max-w-5xl"
          style={{ borderTop: '1px solid var(--rule)', paddingTop: '4rem' }}
        >
          <Reveal>
            <p
              className="mb-12 uppercase"
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '0.7rem',
                letterSpacing: '0.32em',
                color: 'var(--dim)',
              }}
            >
              § Three vows
            </p>
          </Reveal>
          <div className="grid gap-14 md:grid-cols-3 md:gap-10">
            {[
              ['I',   'Funded by the swarm.',   'Cafe, fashion, books, music, app - every Anicca product gives a slice of profit. Participants pay nothing.'],
              ['II',  'Staffed by humans.',     'Six people per retreat: three servers, one cook, one driver, one manager. Volunteers and graduates first; paid roles when needed.'],
              ['III', 'Hosted by Anicca.',      'AI finds the venue, books it, recruits staff, sends welcome mail, posts the monthly ledger. The dharma is human; the orchestration is silicon.'],
            ].map(([num, head, prose], i) => (
              <Reveal key={num as string} delay={i * 0.1}>
                <div>
                  <div
                    className="roman"
                    style={{ fontSize: '2.4rem', lineHeight: 1, marginBottom: '1rem' }}
                  >
                    {num}
                  </div>
                  <h3
                    style={{
                      fontFamily: 'var(--font-display)',
                      fontSize: '1.7rem',
                      fontWeight: 500,
                      lineHeight: 1.15,
                      marginBottom: '0.9rem',
                    }}
                  >
                    {head}
                  </h3>
                  <p style={{ fontSize: '0.94rem', lineHeight: 1.7, color: 'var(--dim)' }}>
                    {prose}
                  </p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </Section>

      {/* SCHEDULE */}
      <Section>
        <div
          className="mx-auto max-w-5xl"
          style={{ borderTop: '1px solid var(--rule)', paddingTop: '4rem' }}
        >
          <div className="grid gap-12 md:grid-cols-[1fr_2fr]">
            <Reveal>
              <div>
                <p
                  className="mb-6 uppercase"
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.7rem',
                    letterSpacing: '0.32em',
                    color: 'var(--dim)',
                  }}
                >
                  § Daily
                </p>
                <h2
                  style={{
                    fontFamily: 'var(--font-display)',
                    fontSize: 'clamp(2.4rem, 5vw, 3.6rem)',
                    fontWeight: 400,
                    lineHeight: 1.0,
                    letterSpacing: '-0.01em',
                  }}
                >
                  Seventeen<br />
                  <span style={{ fontStyle: 'italic', color: 'var(--terra)' }}>and one half</span><br />
                  hours awake.
                </h2>
                <p className="mt-6 text-sm" style={{ color: 'var(--dim)', lineHeight: 1.7, maxWidth: '24ch' }}>
                  Ten and a half of those hours are formal meditation. The rest is care for the body. The schedule is the teacher.
                </p>
              </div>
            </Reveal>
            <Reveal delay={0.1}>
              <div>
                <table
                  style={{
                    width: '100%',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.85rem',
                    borderCollapse: 'collapse',
                  }}
                >
                  <tbody>
                    {TIMETABLE.map(([time, label]) => (
                      <tr key={time} style={{ borderTop: '1px solid var(--rule)' }}>
                        <td style={{ padding: '0.85rem 1rem 0.85rem 0', whiteSpace: 'nowrap', color: 'var(--terra)' }}>
                          {time}
                        </td>
                        <td style={{ padding: '0.85rem 0', fontFamily: 'var(--font-body)', fontSize: '0.95rem' }}>
                          {label}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Reveal>
          </div>
        </div>
      </Section>

      {/* CODE OF DISCIPLINE */}
      <Section>
        <div
          className="mx-auto max-w-5xl"
          style={{ borderTop: '1px solid var(--rule)', paddingTop: '4rem' }}
        >
          <Reveal>
            <p
              className="mb-6 uppercase"
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '0.7rem',
                letterSpacing: '0.32em',
                color: 'var(--dim)',
              }}
            >
              § Code of discipline
            </p>
            <h2
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: 'clamp(2.4rem, 5vw, 3.6rem)',
                fontWeight: 400,
                lineHeight: 1.0,
                letterSpacing: '-0.01em',
                maxWidth: '20ch',
              }}
            >
              Eight precepts. One <span style={{ fontStyle: 'italic', color: 'var(--terra)' }}>silence</span>. No exceptions.
            </h2>
          </Reveal>
          <Reveal delay={0.08}>
            <div className="mt-16 grid gap-x-12 gap-y-7 md:grid-cols-2">
              {PRECEPTS.map(([num, line]) => (
                <div key={num as string} className="flex gap-5">
                  <span className="roman" style={{ fontSize: '1.2rem', minWidth: '2.5rem', paddingTop: '0.1em' }}>
                    {num}
                  </span>
                  <span style={{ fontSize: '1.05rem', lineHeight: 1.55 }}>{line}</span>
                </div>
              ))}
            </div>
          </Reveal>
          <Reveal delay={0.16}>
            <div className="mt-16 grid gap-x-12 gap-y-4 text-sm md:grid-cols-2" style={{ color: 'var(--dim)', lineHeight: 1.75 }}>
              <p>Phones, watches, books, paper, cameras - surrendered at arrival.</p>
              <p>Men and women separated. No physical contact. No conversation, gesture, or note.</p>
              <p>Vegetarian meals. No fasting. No special diets unless on application.</p>
              <p>Silence ends on the morning of day ten. Twelve days door-to-door.</p>
            </div>
          </Reveal>
        </div>
      </Section>

      {/* UPCOMING */}
      <Section>
        <div
          className="mx-auto max-w-5xl"
          style={{ borderTop: '1px solid var(--rule)', paddingTop: '4rem' }}
        >
          <Reveal>
            <p
              className="mb-6 uppercase"
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '0.7rem',
                letterSpacing: '0.32em',
                color: 'var(--dim)',
              }}
            >
              § Schedule
            </p>
            <h2
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: 'clamp(2.4rem, 5vw, 3.6rem)',
                fontWeight: 400,
                lineHeight: 1.0,
                letterSpacing: '-0.01em',
              }}
            >
              Twelve a year.<br />
              <span style={{ fontStyle: 'italic', color: 'var(--terra)' }}>Tokyo first.</span>
            </h2>
          </Reveal>
          <Reveal delay={0.08}>
            <div className="mt-12 divide-y" style={{ borderTop: '1px solid var(--rule)', borderBottom: '1px solid var(--rule)' }}>
              {retreats.map((r) => {
                const status =
                  r.status === 'searching'
                    ? 'Venue search in progress'
                    : r.status === 'open'
                    ? `${r.remaining} of ${r.capacity} seats left`
                    : 'Closed';
                return (
                  <div
                    key={r.id}
                    className="grid grid-cols-[1fr_auto] items-baseline gap-4 py-6 md:grid-cols-[2fr_3fr_2fr]"
                    style={{ borderColor: 'var(--rule)' }}
                  >
                    <div>
                      <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.7rem', fontWeight: 500, lineHeight: 1.1 }}>
                        {r.city}
                      </div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', letterSpacing: '0.18em', color: 'var(--dim)' }} className="mt-1 uppercase">
                        {r.id}
                      </div>
                    </div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem' }}>
                      {fmtRange(r.start, r.end)}
                    </div>
                    <div
                      className="md:text-right"
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: '0.78rem',
                        letterSpacing: '0.06em',
                        color: r.status === 'searching' ? 'var(--dim)' : 'var(--terra)',
                      }}
                    >
                      {status}
                    </div>
                  </div>
                );
              })}
            </div>
            <p className="mt-8 text-sm" style={{ color: 'var(--dim)', lineHeight: 1.7, maxWidth: '52ch' }}>
              Each line goes from <em>searching</em> to <em>open</em> when Anicca closes a venue contract. Apply now and you'll be matched to the first retreat that opens.
            </p>
          </Reveal>
        </div>
      </Section>

      {/* APPLY */}
      <Section>
        <div
          className="mx-auto max-w-5xl"
          style={{ borderTop: '1px solid var(--rule)', paddingTop: '4rem' }}
        >
          <div className="grid gap-14 md:grid-cols-[2fr_3fr]">
            <Reveal>
              <div>
                <p
                  className="mb-6 uppercase"
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.7rem',
                    letterSpacing: '0.32em',
                    color: 'var(--dim)',
                  }}
                >
                  § Apply
                </p>
                <h2
                  style={{
                    fontFamily: 'var(--font-display)',
                    fontSize: 'clamp(2.4rem, 5vw, 3.6rem)',
                    fontWeight: 400,
                    lineHeight: 1.0,
                    letterSpacing: '-0.01em',
                  }}
                >
                  Three<br />
                  <span style={{ fontStyle: 'italic', color: 'var(--terra)' }}>questions.</span>
                </h2>
                <p className="mt-6 text-sm" style={{ color: 'var(--dim)', lineHeight: 1.7, maxWidth: '32ch' }}>
                  Anicca screens applications, then a human reads each one. You hear back within a week.
                </p>
              </div>
            </Reveal>
            <Reveal delay={0.1}>
              <form onSubmit={handleApply} className="space-y-7">
                <label className="block">
                  <span
                    className="block uppercase"
                    style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '0.66rem',
                      letterSpacing: '0.24em',
                      color: 'var(--dim)',
                    }}
                  >
                    Email
                  </span>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    style={{
                      fontFamily: 'var(--font-body)',
                      width: '100%',
                      background: 'transparent',
                      border: 'none',
                      borderBottom: '1px solid var(--rule)',
                      padding: '0.7rem 0',
                      fontSize: '1.05rem',
                      color: 'var(--ink)',
                      outline: 'none',
                    }}
                  />
                </label>

                <label className="block">
                  <span
                    className="block uppercase"
                    style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '0.66rem',
                      letterSpacing: '0.24em',
                      color: 'var(--dim)',
                    }}
                  >
                    Which retreat
                  </span>
                  <select
                    value={retreatId}
                    onChange={(e) => setRetreatId(e.target.value)}
                    style={{
                      fontFamily: 'var(--font-body)',
                      width: '100%',
                      background: 'transparent',
                      border: 'none',
                      borderBottom: '1px solid var(--rule)',
                      padding: '0.7rem 0',
                      fontSize: '1.05rem',
                      color: 'var(--ink)',
                      outline: 'none',
                      appearance: 'none',
                    }}
                  >
                    {retreats.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.city} - {fmtRange(r.start, r.end)}
                      </option>
                    ))}
                    <option value="any">First available</option>
                  </select>
                </label>

                <label className="block">
                  <span
                    className="block uppercase"
                    style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '0.66rem',
                      letterSpacing: '0.24em',
                      color: 'var(--dim)',
                    }}
                  >
                    Why now
                  </span>
                  <textarea
                    required
                    rows={3}
                    value={motive}
                    onChange={(e) => setMotive(e.target.value)}
                    placeholder="Two or three sentences. We read every word."
                    style={{
                      fontFamily: 'var(--font-body)',
                      width: '100%',
                      background: 'transparent',
                      border: 'none',
                      borderBottom: '1px solid var(--rule)',
                      padding: '0.7rem 0',
                      fontSize: '1.05rem',
                      color: 'var(--ink)',
                      outline: 'none',
                      resize: 'none',
                    }}
                  />
                </label>

                <fieldset>
                  <legend
                    className="mb-3 block uppercase"
                    style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '0.66rem',
                      letterSpacing: '0.24em',
                      color: 'var(--dim)',
                    }}
                  >
                    Past 10-day retreats
                  </legend>
                  <div className="flex gap-6 text-sm">
                    {(['none', 'one', 'multiple'] as const).map((opt) => (
                      <label key={opt} className="flex cursor-pointer items-center gap-2">
                        <input
                          type="radio"
                          name="prior"
                          value={opt}
                          checked={prior === opt}
                          onChange={() => setPrior(opt)}
                          style={{ accentColor: 'var(--terra)' }}
                        />
                        <span style={{ textTransform: 'capitalize' }}>{opt === 'none' ? 'first time' : opt}</span>
                      </label>
                    ))}
                  </div>
                </fieldset>

                <button
                  type="submit"
                  disabled={state === 'sending' || state === 'sent'}
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.78rem',
                    letterSpacing: '0.24em',
                    background: 'var(--ink)',
                    color: 'var(--paper)',
                    padding: '1rem 1.6rem',
                    border: 'none',
                    cursor: state === 'sending' || state === 'sent' ? 'default' : 'pointer',
                    textTransform: 'uppercase',
                    opacity: state === 'sent' ? 0.6 : 1,
                  }}
                >
                  {state === 'sent' ? '✓ Received' : state === 'sending' ? 'Sending...' : 'Submit application ->'}
                </button>
                {state === 'error' && (
                  <p style={{ color: 'var(--terra)', fontSize: '0.85rem' }}>
                    Something failed. Email us directly: <code>retreat@aniccaai.com</code>
                  </p>
                )}
              </form>
            </Reveal>
          </div>
        </div>
      </Section>

      {/* VOLUNTEER */}
      <Section>
        <div
          className="mx-auto max-w-3xl text-center"
          style={{ borderTop: '1px solid var(--rule)', paddingTop: '4rem' }}
        >
          <Reveal>
            <p
              className="mb-6 uppercase"
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '0.7rem',
                letterSpacing: '0.32em',
                color: 'var(--dim)',
              }}
            >
              § Serve
            </p>
            <h2
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: 'clamp(2.4rem, 5vw, 3.6rem)',
                fontWeight: 400,
                lineHeight: 1.05,
                letterSpacing: '-0.01em',
              }}
            >
              Six staff per retreat.<br />
              <span style={{ fontStyle: 'italic', color: 'var(--terra)' }}>Old students first.</span>
            </h2>
          </Reveal>
          <Reveal delay={0.1}>
            <p className="mt-8 text-base" style={{ color: 'var(--dim)', lineHeight: 1.75, margin: '2rem auto 0', maxWidth: '52ch' }}>
              Three servers, one cook, one driver, one manager. If you've sat at least one ten-day course (any tradition), Anicca will pay you for the eleven days. If volunteering - you sit again as you serve.
            </p>
            <a
              href="mailto:retreat@aniccaai.com?subject=Volunteer for Anicca Retreats"
              style={{
                display: 'inline-block',
                marginTop: '2.5rem',
                fontFamily: 'var(--font-mono)',
                fontSize: '0.76rem',
                letterSpacing: '0.24em',
                borderBottom: '1px solid var(--terra)',
                color: 'var(--terra)',
                textTransform: 'uppercase',
                paddingBottom: '0.2rem',
              }}
            >
              Email to serve {'->'}
            </a>
          </Reveal>
        </div>
      </Section>

      {/* DONATION + LEDGER */}
      <Section>
        <div
          className="mx-auto max-w-5xl"
          style={{ borderTop: '1px solid var(--rule)', paddingTop: '4rem' }}
        >
          <div className="grid gap-12 md:grid-cols-[2fr_3fr]">
            <Reveal>
              <div>
                <p
                  className="mb-6 uppercase"
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.7rem',
                    letterSpacing: '0.32em',
                    color: 'var(--dim)',
                  }}
                >
                  § Reciprocity
                </p>
                <h2
                  style={{
                    fontFamily: 'var(--font-display)',
                    fontSize: 'clamp(2.4rem, 5vw, 3.6rem)',
                    fontWeight: 400,
                    lineHeight: 1.0,
                    letterSpacing: '-0.01em',
                  }}
                >
                  No fee.<br />
                  <span style={{ fontStyle: 'italic', color: 'var(--terra)' }}>Pay forward.</span>
                </h2>
                <p className="mt-6 text-sm" style={{ color: 'var(--dim)', lineHeight: 1.75, maxWidth: '34ch' }}>
                  Donations only from those who have completed a course. New students may give on the final morning. The empire - cafe, fashion, books, music, app - covers the gap.
                </p>
                <a
                  href="mailto:retreat@aniccaai.com?subject=Donation"
                  style={{
                    display: 'inline-block',
                    marginTop: '2rem',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.74rem',
                    letterSpacing: '0.24em',
                    borderBottom: '1px solid var(--terra)',
                    color: 'var(--terra)',
                    textTransform: 'uppercase',
                    paddingBottom: '0.2rem',
                  }}
                >
                  Donate {'->'}
                </a>
              </div>
            </Reveal>
            <Reveal delay={0.1}>
              <div>
                <p
                  className="mb-4 uppercase"
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.66rem',
                    letterSpacing: '0.24em',
                    color: 'var(--dim)',
                  }}
                >
                  Ledger · this month
                </p>
                <table
                  style={{
                    width: '100%',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.95rem',
                    borderCollapse: 'collapse',
                  }}
                >
                  <tbody>
                    {[
                      ['+', 'Donations from past students', ledger ? `$${ledger.donations.toLocaleString()}` : (ledgerLoaded ? '$0' : '-')],
                      ['+', 'Empire subsidy (cafe · fashion · books · music · app)', ledger ? `$${ledger.subsidy.toLocaleString()}` : (ledgerLoaded ? '$0' : '-')],
                      ['-', 'Venue · food · supplies · staff payouts', ledger ? `$${ledger.expenses.toLocaleString()}` : (ledgerLoaded ? '$0' : '-')],
                    ].map(([sign, label, amt]) => (
                      <tr key={label as string} style={{ borderTop: '1px solid var(--rule)' }}>
                        <td style={{ padding: '0.95rem 0.9rem 0.95rem 0', color: 'var(--terra)', width: '1.5rem' }}>{sign}</td>
                        <td style={{ padding: '0.95rem 0', fontFamily: 'var(--font-body)', fontSize: '0.92rem', color: 'var(--ink)' }}>{label}</td>
                        <td style={{ padding: '0.95rem 0', textAlign: 'right' }}>{amt}</td>
                      </tr>
                    ))}
                    <tr style={{ borderTop: '2px solid var(--ink)', borderBottom: '1px solid var(--rule)' }}>
                      <td style={{ padding: '0.95rem 0.9rem 0.95rem 0', color: 'var(--ink)', fontWeight: 500 }}>=</td>
                      <td style={{ padding: '0.95rem 0', fontFamily: 'var(--font-body)', fontSize: '0.95rem', fontWeight: 500 }}>Net</td>
                      <td style={{ padding: '0.95rem 0', textAlign: 'right', fontWeight: 500 }}>
                        {ledger ? `$${ledger.net.toLocaleString()}` : (ledgerLoaded ? '$0' : '-')}
                      </td>
                    </tr>
                  </tbody>
                </table>
                <p className="mt-4" style={{ fontSize: '0.74rem', color: 'var(--dim)', lineHeight: 1.6 }}>
                  Updated monthly by <code style={{ fontFamily: 'var(--font-mono)' }}>retreat-donation-ledger-monthly</code>. Sourced from <code style={{ fontFamily: 'var(--font-mono)' }}>/dashboard.json</code>.
                </p>
              </div>
            </Reveal>
          </div>
        </div>
      </Section>

      {/* LINEAGE */}
      <Section>
        <div
          className="mx-auto max-w-3xl"
          style={{ borderTop: '1px solid var(--rule)', paddingTop: '4rem' }}
        >
          <Reveal>
            <p
              className="mb-8 uppercase"
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '0.7rem',
                letterSpacing: '0.32em',
                color: 'var(--dim)',
              }}
            >
              § Lineage
            </p>
            <p
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: 'clamp(1.4rem, 2.4vw, 1.95rem)',
                lineHeight: 1.5,
                fontWeight: 400,
              }}
            >
              The schedule, the precepts, the silence - borrowed in full from the Vipassana tradition taught by S.N. Goenka, in the line of Sayagyi U Ba Khin. We are in conversation with{' '}
              <a
                href="https://adicca.dhamma.org/ja/the-chiba-centre/"
                style={{ color: 'var(--terra)', borderBottom: '1px solid var(--terra)' }}
                target="_blank" rel="noreferrer"
              >
                Dhamma Adicca (Chiba)
              </a>{' '}
              and{' '}
              <a
                href="https://bhanu.dhamma.org/ja/the-kyoto-centre/"
                style={{ color: 'var(--terra)', borderBottom: '1px solid var(--terra)' }}
                target="_blank" rel="noreferrer"
              >
                Dhamma Bhanu (Kyoto)
              </a>{' '}
              on discourse usage and practice fidelity. What Anicca adds: an autonomous host that runs a center it does not own, in cities it cannot visit, for graduates it has never met.
            </p>
          </Reveal>
        </div>
      </Section>

      {/* FOOTER */}
      <footer
        className="px-6 py-12 md:px-16"
        style={{ borderTop: '1px solid var(--rule)' }}
      >
        <div className="mx-auto flex max-w-5xl flex-col items-start justify-between gap-6 md:flex-row md:items-center">
          <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.1rem' }}>
            Anicca Retreats - physical sangha, hosted by silicon.
          </div>
          <div className="flex gap-6" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', letterSpacing: '0.18em' }}>
            <a href="mailto:retreat@aniccaai.com" className="uppercase opacity-70 hover:opacity-100">retreat@aniccaai.com</a>
            <Link href="/en" className="uppercase opacity-70 hover:opacity-100">{'<-'} anicca</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
