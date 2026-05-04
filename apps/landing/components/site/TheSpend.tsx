'use client';

import { useEffect, useState } from 'react';
import { translations, type Locale } from '@/lib/i18n';

interface TheSpendProps {
  locale: Locale;
}

interface SpendData {
  total_usd: number;
  by_category: Record<string, number>;
}

const CATEGORY_ORDER = [
  'claude',
  'living',
  'postiz',
  'supabase',
  'chatgpt',
  'railway',
] as const;

export default function TheSpend({ locale }: TheSpendProps) {
  const t = translations[locale].theSpend;
  const [spend, setSpend] = useState<SpendData | null>(null);
  const [profit, setProfit] = useState<number | null>(null);

  useEffect(() => {
    fetch('/dashboard.json')
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        setSpend(d.spend);
        setProfit(d.profit_usd);
      })
      .catch(() => {});
  }, []);

  const byCategory = spend?.by_category ?? {};
  const max = Math.max(1, ...Object.values(byCategory).map((v) => Number(v) || 0));

  return (
    <section className="bg-background px-6 py-20">
      <div className="mx-auto max-w-3xl">
        <h2 className="mb-2 text-center text-3xl font-bold text-foreground md:text-4xl">
          {t.title}
        </h2>
        <p className="mb-10 text-center text-sm text-muted-foreground">
          {t.subtitle}
        </p>

        <div className="space-y-3">
          {CATEGORY_ORDER.map((cat) => {
            const v = Number(byCategory[cat] || 0);
            const pct = (v / max) * 100;
            return (
              <div key={cat}>
                <div className="mb-1 flex items-baseline justify-between text-sm">
                  <span className="text-foreground">
                    {(t.categories as Record<string, string>)[cat] || cat}
                  </span>
                  <span className="font-mono text-foreground">${v.toLocaleString()}</span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-foreground"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>

        <div className="mt-10 grid grid-cols-2 gap-6">
          <div>
            <p className="text-sm text-muted-foreground">{t.total}</p>
            <p className="font-mono text-2xl font-semibold text-foreground">
              ${spend ? spend.total_usd.toLocaleString() : '—'}/mo
            </p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">{t.profit}</p>
            <p className={`font-mono text-2xl font-semibold ${profit !== null && profit < 0 ? 'text-red-500' : 'text-foreground'}`}>
              ${profit !== null ? profit.toLocaleString() : '—'}/mo
            </p>
          </div>
        </div>

      </div>
    </section>
  );
}
