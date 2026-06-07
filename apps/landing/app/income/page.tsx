/* eslint-disable react/no-unescaped-entities */
'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import JsonLd from '@/components/JsonLd';
import { SplitHero } from '@/components/site/taste/SplitHero';
import { Section } from '@/components/site/taste/Section';
import { Reveal } from '@/components/site/taste/Reveal';
import { CTA } from '@/components/site/taste/CTA';

// JsonLd structured data - verbatim (§11.F)
const incomeLd = {
  '@context': 'https://schema.org',
  '@type': 'Service',
  name: 'Anicca Basic Income',
  url: 'https://aniccaai.com/income',
  serviceType: 'Unconditional cash transfers',
  provider: { '@type': 'Organization', name: 'Anicca', url: 'https://aniccaai.com' },
  description:
    'A live, autonomous basic-income program funded by Anicca revenue and distributed via Stripe Connect. Anicca accepts 10 humans per cohort; accepted recipients receive their share on the 1st of each month, automatically.',
};

interface BasicIncome {
  pool_usd: number;
  recipients: number;
  per_person_usd: number;
}

// §11.F: FORM block - field names, onSubmit handler, and fetch endpoint preserved verbatim
// §4.6: labels ABOVE inputs (fixed from placeholder-as-label)
function ApplyForm() {
  const [email, setEmail] = useState('');
  const [reason, setReason] = useState('');
  const [country, setCountry] = useState('jp');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // A4 pattern: AbortController on fetch
  const abortRef = useRef<AbortController | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    abortRef.current?.abort();
    abortRef.current = new AbortController();
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch('/api/income/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim(), reason: reason.trim(), country }),
        signal: abortRef.current.signal,
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error || 'something went wrong');
        setSubmitting(false);
        return;
      }
      if (data.onboarding_url) {
        window.location.href = data.onboarding_url;
        return;
      }
      setError('no onboarding url returned');
      setSubmitting(false);
    } catch (err) {
      if ((err as Error).name === 'AbortError') return;
      setError(String(err));
      setSubmitting(false);
    }
  }

  return (
    <Section>
      <Reveal>
        <div className="mx-auto max-w-[40rem] rounded-card border border-[hsl(var(--border))] px-8 py-10">
          <h2 className="text-2xl font-semibold text-[hsl(var(--text-primary))]">Apply</h2>
          <p className="mt-3 text-sm leading-relaxed text-[hsl(var(--text-secondary))]">
            On submit you will be redirected to Stripe Connect onboarding. KYC + bank
            info takes about 5 minutes. After that you wait - you will get an email
            when you are approved into the next cohort.
          </p>
          <form className="mt-8 space-y-6" onSubmit={onSubmit}>
            {/* §4.6: label ABOVE input */}
            <div className="flex flex-col gap-1.5">
              <label htmlFor="income-email" className="text-sm font-medium text-[hsl(var(--text-primary))]">
                Email
              </label>
              <input
                id="income-email"
                name="email"
                type="email"
                required
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-input border border-[hsl(var(--border))] bg-[hsl(var(--surface))] px-4 py-3 text-[hsl(var(--text-primary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--gold))]"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label htmlFor="income-country" className="text-sm font-medium text-[hsl(var(--text-primary))]">
                Country
              </label>
              <select
                id="income-country"
                name="country"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                className="w-full rounded-input border border-[hsl(var(--border))] bg-[hsl(var(--surface))] px-4 py-3 text-[hsl(var(--text-primary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--gold))]"
              >
                <option value="jp">Japan (recommended for first cohort)</option>
                <option value="us">United States</option>
                <option value="gb">United Kingdom</option>
                <option value="ca">Canada</option>
                <option value="au">Australia</option>
              </select>
            </div>
            <div className="flex flex-col gap-1.5">
              <label htmlFor="income-reason" className="text-sm font-medium text-[hsl(var(--text-primary))]">
                Why you want this
              </label>
              <textarea
                id="income-reason"
                name="reason"
                required
                maxLength={280}
                placeholder="One sentence, 280 chars max"
                rows={3}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                className="w-full rounded-input border border-[hsl(var(--border))] bg-[hsl(var(--surface))] px-4 py-3 text-[hsl(var(--text-primary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--gold))]"
              />
            </div>
            {error && (
              <p className="text-sm text-[hsl(var(--destructive))]">Error: {error}</p>
            )}
            {/* gold button text fixed off-black for AA contrast 7.5:1 (matches taste/CTA primary, §4.5) */}
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-pill bg-[hsl(var(--gold))] px-6 py-3 font-medium text-[#18181b] transition-all duration-300 hover:brightness-95 active:scale-[0.98] disabled:opacity-50"
            >
              {submitting ? 'Connecting to Stripe...' : 'Continue to Stripe Connect'}
            </button>
          </form>
        </div>
      </Reveal>
    </Section>
  );
}

// Ledger stat card - §9.A tabular-nums + en-US pin
function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-card border border-[hsl(var(--border))] px-6 py-6">
      <p className="text-[10px] uppercase tracking-[0.18em] text-[hsl(var(--text-secondary))]">{label}</p>
      <p className="mt-2 font-mono tabular-nums text-2xl font-semibold text-[hsl(var(--text-primary))]">
        {value}
      </p>
    </div>
  );
}

export default function Page() {
  const [bi, setBi] = useState<BasicIncome | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    fetch('/dashboard.json', { signal: ctrl.signal })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setBi(d.basic_income))
      .catch((err) => { if ((err as Error).name !== 'AbortError') console.warn(err); });
    return () => ctrl.abort();
  }, []);

  return (
    <main>
      <JsonLd data={incomeLd} />

      {/* Hero */}
      <SplitHero
        eyebrow="Anicca Basic Income"
        headline={<>A floor<br />under everyone.</>}
        subtext="Paid by AI, while we transition into the era of agentic systems. Today 10 recipients. Tomorrow 100. Then 1,000. Then everyone."
        primary={<CTA href="/en">Back to Anicca</CTA>}
        secondary={<CTA href="/fellows" variant="link">SAO Fellows</CTA>}
        asset={
          // §4.8 real visual - Anicca brand asset
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src="/anicca-app-icon.png"
            alt="Anicca app icon"
            className="h-full w-full object-cover"
            width={1024}
            height={1024}
          />
        }
      />

      {/* Stats tiles */}
      <Section>
        <Reveal>
          <p className="mb-6 text-[11px] uppercase tracking-[0.18em] text-[hsl(var(--text-secondary))]">
            This month
          </p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard
              label="Pool"
              value={bi ? `$${bi.pool_usd.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '-'}
            />
            <StatCard
              label="Spots filled"
              value={bi ? `${bi.recipients.toLocaleString('en-US')} / 10` : '-'}
            />
            <StatCard
              label="Per person"
              value={bi ? `$${bi.per_person_usd.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '-'}
            />
          </div>
        </Reveal>
      </Section>

      {/* How it works */}
      <Section>
        <Reveal>
          <h2 className="text-2xl font-semibold text-[hsl(var(--text-primary))]">How it works</h2>
          <ol className="mt-6 list-decimal space-y-4 pl-6 text-base leading-relaxed text-[hsl(var(--text-primary))]">
            <li>Drop your email and one sentence on why you want this.</li>
            <li>Connect Stripe (5 minutes - KYC + bank or debit card). One screen, one redirect.</li>
            <li>Wait. We approve 10 people per cohort. You will get an email when you are in.</li>
            <li>On the 1st of each month, your share lands in your bank automatically.</li>
          </ol>
        </Reveal>
      </Section>

      {/* Apply form - §11.F verbatim FORM block */}
      <ApplyForm />

      {/* Why this exists */}
      <Section>
        <div className="mx-auto max-w-[65ch] space-y-8">
          <Reveal delay={0}>
            <div className="text-base leading-relaxed text-[hsl(var(--text-secondary))]">
              <strong className="text-[hsl(var(--text-primary))]">Why this exists - reason 1: the agency collapse.</strong>{' '}
              Soon, agentic AI will have a hundred - then a billion - times the agency of any human, including the CEOs.
              Every job that depends on a person deciding things will be replaced. The transition will be chaotic - lost income,
              despair, &quot;I cannot eat today.&quot; Basic income is the bridge across that transition. Not charity. A floor.
            </div>
          </Reveal>
          <Reveal delay={0.05}>
            <div className="text-base leading-relaxed text-[hsl(var(--text-secondary))]">
              <strong className="text-[hsl(var(--text-primary))]">Why this exists - reason 2: AI must be an equalizer.</strong>{' '}
              When civilians call AI a &quot;bubble,&quot; they are being rational - none of the dollars Sam Altman moves ever reaches them.
              So they distrust the spend, and the AGI investment dries up before AGI arrives.
              The fastest way to fix this is to make AI literally pay off your student loan. Trust compounds. The investment continues. AGI arrives.
            </div>
          </Reveal>
          <Reveal delay={0.1}>
            <div className="text-base leading-relaxed text-[hsl(var(--text-secondary))]">
              <strong className="text-[hsl(var(--text-primary))]">Why 10% and 10 people.</strong>{' '}
              Every month, automatically split 10% of Anicca revenue across the cohort. When MRR doubles, the cohort doubles.
              Today 10 - eventually everyone.
            </div>
          </Reveal>
          <Reveal delay={0.15}>
            <div className="text-base leading-relaxed text-[hsl(var(--text-secondary))]">
              <strong className="text-[hsl(var(--text-primary))]">Why no work required.</strong>{' '}
              The point is to demonstrate that an autonomous AI can fund people, not replace them - and that the value AGI creates
              can reach the people who never opened a chatbot. The swarm earns; the humans receive.
            </div>
          </Reveal>
          <Reveal delay={0.2}>
            <div className="text-base leading-relaxed text-[hsl(var(--text-secondary))]">
              <strong className="text-[hsl(var(--text-primary))]">When we open the next cohort.</strong>{' '}
              When MRR hits $20k. The pool doubles, the cohort grows by 10. Eventually the floor is everyone.
            </div>
          </Reveal>
          <Reveal delay={0.25}>
            <p className="text-sm italic text-[hsl(var(--text-secondary))]">
              Basic income is not the goal. The goal is the end of suffering for all living beings (Vipassana).
              Basic income is the bridge people stand on while we build it.
            </p>
          </Reveal>
        </div>
      </Section>

      {/* Footer nav - /en and /fellows preserved verbatim (§11.F) */}
      <Section>
        <Reveal>
          <div className="border-t border-[hsl(var(--border))] pt-8 text-xs text-[hsl(var(--text-secondary))]">
            Live numbers:{' '}
            <Link href="/en" className="underline hover:text-[hsl(var(--text-primary))]">aniccaai.com</Link>
            {' '}&middot; One of the{' '}
            <Link href="/fellows" className="underline hover:text-[hsl(var(--text-primary))]">SAOs</Link>
          </div>
        </Reveal>
      </Section>
    </main>
  );
}
