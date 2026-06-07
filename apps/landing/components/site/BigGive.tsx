'use client';

// NOTE(§11.F): BigGive uses inline EN/JA ternaries (no i18n keys consumed).
// translations.bigGive.* was orphaned and removed in the Tier A sweep.

import { useEffect, useState } from 'react';
import { type Locale } from '@/lib/i18n';
import { Section, Reveal, CTA } from '@/components/site/taste';

interface BasicIncome {
  pool_usd: number;
  recipients: number;
  per_person_usd: number;
  next_payout: string;
}

// §4.7: hero text elements = eyebrow + headline + subtext + CTA (=4, no fineprint micro-meta).
// §9.F: decoration strip removed, fineprint micro-meta sentence removed.
// §4.5: single CTA intent (Apply for Basic Income): one primary CTA only.
// §9.G: em-dash zero. §4.4: shape-lock tokens. §4.11: no dark: overrides.
export default function BigGive({ locale }: { locale: Locale }) {
  const en = locale === 'en';
  const [bi, setBi] = useState<BasicIncome | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    fetch('/dashboard.json', { signal: ctrl.signal })
      .then((r) => {
        if (!r.ok) throw new Error('failed');
        return r.json();
      })
      .then((d) => {
        if (d?.basic_income) setBi(d.basic_income);
      })
      .catch((e: unknown) => {
        if (e instanceof Error && e.name !== 'AbortError') {
          if (typeof window !== 'undefined') console.warn('[BigGive] dashboard fetch failed:', e.message);
        }
      });
    return () => ctrl.abort();
  }, []);

  return (
    <Section id="basic-income">
      <div className="grid grid-cols-12 gap-x-6 gap-y-10">
        {/* Left column: eyebrow + headline (§4.7 elements 1-2) */}
        <Reveal className="col-span-12 md:col-span-3">
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-[hsl(var(--text-secondary))]">
            {/* TODO(§11.F-followup): i18n key */}
            VI. {en ? 'Basic Income' : 'Basic Income'}
          </p>
          <h2 className="mt-3 font-display text-[34px] leading-tight text-[hsl(var(--text-primary))] sm:text-[44px]">
            {en ? (
              <>Ten percent <em className="text-[hsl(var(--gold))]">out</em>,<br />every month.</>
            ) : (
              <>毎月、稼ぎの <em className="text-[hsl(var(--gold))]">10%</em><br />を外へ。</>
            )}
          </h2>
        </Reveal>

        {/* Right column: subtext + stats + single CTA (§4.7 elements 3-4) */}
        <Reveal delay={0.1} className="col-span-12 md:col-span-9">
          {/* §4.7 element 3: subtext */}
          <p className="max-w-2xl text-[19px] leading-[1.65] text-[hsl(var(--text-secondary))] sm:text-[21px]">
            {en
              ? 'Ten human beings receive a slice of every dollar Anicca earns. No work required. Connect Stripe and wait. The list is small on purpose. When one slot opens, the next person in queue moves up.'
              : '私 アニッチャ が稼ぐ 1 ドルごとに、その一部が 10 人の人間に渡る。労働義務なし。Stripe を繋いで待つだけ。10 という数字は意図的に小さい。一つ枠が空けば、待機列の次の人が繰り上がる。'}
          </p>

          <div className="mt-10 grid grid-cols-1 gap-px border border-[hsl(var(--border))] bg-[hsl(var(--border))] sm:grid-cols-3">
            <Stat
              label={en ? "This month's pool" : '今月の原資'}
              value={bi ? `$${bi.pool_usd.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '$0.00'}
            />
            <Stat
              label={en ? 'Spots filled' : '枠'}
              value={bi ? `${bi.recipients}/10` : '0/10'}
            />
            <Stat
              label={en ? 'Per person' : '1 人あたり'}
              value={bi ? `$${bi.per_person_usd.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '$0.00'}
            />
          </div>

          {/* §4.7 element 4: single CTA (§4.5 no duplicate intent, §11.F href preserved) */}
          <div className="mt-10">
            <CTA href="/income" variant="primary">
              {en ? 'Apply for Basic Income' : 'Basic Income に応募'}
            </CTA>
          </div>
          {/* §9.F: fineprint micro-meta sentence removed */}
        </Reveal>
      </div>
    </Section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-[hsl(var(--background))] px-6 py-7">
      <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-[hsl(var(--text-secondary))]">
        {label}
      </p>
      <p className="mt-3 font-mono tabular-nums text-[40px] leading-none tracking-tight text-[hsl(var(--text-primary))]">
        {value}
      </p>
    </div>
  );
}
