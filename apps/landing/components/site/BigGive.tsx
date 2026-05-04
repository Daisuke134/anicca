'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { translations, type Locale } from '@/lib/i18n';

interface BigGiveProps {
  locale: Locale;
}

interface BasicIncome {
  pool_usd: number;
  recipients: number;
  per_person_usd: number;
  next_payout: string;
}

export default function BigGive({ locale }: BigGiveProps) {
  const t = translations[locale].bigGive;
  const [bi, setBi] = useState<BasicIncome | null>(null);

  useEffect(() => {
    fetch('/dashboard.json')
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setBi(d.basic_income))
      .catch(() => {});
  }, []);

  return (
    <section className="bg-foreground px-6 py-20 text-background">
      <div className="mx-auto max-w-3xl text-center">
        <h2 className="mb-2 text-3xl font-bold md:text-4xl">{t.title}</h2>
        <p className="mb-10 text-base opacity-80">{t.subtitle}</p>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          <div className="rounded-xl border border-background/30 px-6 py-6">
            <p className="text-xs uppercase tracking-widest opacity-70">
              {t.poolLabel}
            </p>
            <p className="mt-2 font-mono text-2xl font-semibold">
              {bi ? `$${bi.pool_usd.toFixed(2)}` : '—'}
            </p>
          </div>
          <div className="rounded-xl border border-background/30 px-6 py-6">
            <p className="text-xs uppercase tracking-widest opacity-70">
              {t.spotsLabel}
            </p>
            <p className="mt-2 font-mono text-2xl font-semibold">
              {bi ? `${bi.recipients} / 10` : '—'}
            </p>
          </div>
          <div className="rounded-xl border border-background/30 px-6 py-6">
            <p className="text-xs uppercase tracking-widest opacity-70">
              {t.perPersonLabel}
            </p>
            <p className="mt-2 font-mono text-2xl font-semibold">
              {bi ? `$${bi.per_person_usd.toFixed(2)}` : '—'}
            </p>
          </div>
        </div>

        <Link
          href="/income"
          className="mt-10 inline-block rounded-xl bg-background px-8 py-3 text-base font-bold text-foreground transition-opacity hover:opacity-90"
        >
          {t.applyButton}
        </Link>

        <p className="mt-4 text-xs opacity-70">{t.fineprint}</p>
      </div>
    </section>
  );
}
