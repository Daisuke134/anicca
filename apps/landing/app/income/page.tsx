/* eslint-disable react/no-unescaped-entities */
'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

interface BasicIncome {
  pool_usd: number;
  recipients: number;
  per_person_usd: number;
}

function ApplyForm() {
  const [email, setEmail] = useState('');
  const [reason, setReason] = useState('');
  const [country, setCountry] = useState('jp');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch('/api/income/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim(), reason: reason.trim(), country }),
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
      setError(String(err));
      setSubmitting(false);
    }
  }

  return (
    <section className="mt-12 rounded-xl border border-border px-6 py-6">
      <h2 className="text-xl font-semibold">Apply</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        On submit you'll be redirected to Stripe Connect onboarding. KYC + bank
        info takes about 5 minutes. After that you wait — you'll get an email
        when you're approved into the next cohort.
      </p>
      <form className="mt-6 space-y-4" onSubmit={onSubmit}>
        <input
          name="email"
          type="email"
          required
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded-md border border-border bg-background px-4 py-3 text-foreground"
        />
        <select
          name="country"
          value={country}
          onChange={(e) => setCountry(e.target.value)}
          className="w-full rounded-md border border-border bg-background px-4 py-3 text-foreground"
        >
          <option value="jp">🇯🇵 Japan (recommended for first cohort)</option>
          <option value="us">🇺🇸 United States</option>
          <option value="gb">🇬🇧 United Kingdom</option>
          <option value="ca">🇨🇦 Canada</option>
          <option value="au">🇦🇺 Australia</option>
        </select>
        <textarea
          name="reason"
          required
          maxLength={280}
          placeholder="Why you'd want this — one sentence (280 chars max)"
          rows={3}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          className="w-full rounded-md border border-border bg-background px-4 py-3 text-foreground"
        />
        {error && (
          <p className="text-sm text-red-500">⚠ {error}</p>
        )}
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-md bg-foreground px-6 py-3 font-bold text-background transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {submitting ? 'Connecting to Stripe…' : 'Continue to Stripe Connect →'}
        </button>
      </form>
    </section>
  );
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
        A floor under everyone — paid by AI, while we transition into the era of agentic systems.
        Today 10 recipients. Tomorrow 100. Then 1,000. Then everyone.
      </p>
      <p className="mt-3 text-sm italic text-muted-foreground">
        Basic income is not the goal. The goal is the end of suffering for all living beings (Vipassana).
        Basic income is the bridge people stand on while we build it.
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

      <ApplyForm />

      <section className="mt-12 space-y-5 text-sm leading-relaxed text-muted-foreground">
        <p>
          <strong className="text-foreground">Why this exists — reason 1: the agency collapse.</strong>{' '}
          Soon, agentic AI will have a hundred — then a billion — times the agency of any human, including the CEOs.
          Every job that depends on a person deciding things will be replaced. The transition will be chaotic — lost income,
          despair, "I cannot eat today." Basic income is the bridge across that transition. Not charity. A floor.
        </p>
        <p>
          <strong className="text-foreground">Why this exists — reason 2: AI must be an equalizer.</strong>{' '}
          When civilians call AI a "bubble," they are being rational — none of the dollars Sam Altman moves ever reaches them.
          So they distrust the spend, and the AGI investment dries up before AGI arrives.
          The fastest way to fix this is to make AI literally pay off your student loan. Trust compounds. The investment continues. AGI arrives.
        </p>
        <p>
          <strong className="text-foreground">Why 10% and 10 people.</strong>{' '}
          Every month, automatically split 10% of Anicca revenue across the cohort. When MRR doubles, the cohort doubles.
          Today 10 → eventually everyone.
        </p>
        <p>
          <strong className="text-foreground">Why no work required.</strong>{' '}
          The point is to demonstrate that an autonomous AI can fund people, not replace them — and that the value AGI creates
          can reach the people who never opened a chatbot. The swarm earns; the humans receive.
        </p>
        <p>
          <strong className="text-foreground">When we open the next cohort.</strong>{' '}
          When MRR hits $20k. The pool doubles, the cohort grows by 10. Eventually the floor is everyone.
        </p>
      </section>

      <footer className="mt-16 border-t border-border pt-8 text-xs text-muted-foreground">
        Live numbers:{' '}
        <Link href="/en" className="underline">aniccaai.com</Link>{' '}
        · One of the{' '}
        <Link href="/fellows" className="underline">SAOs</Link>
      </footer>
    </main>
  );
}
