'use client';

import { useEffect, useState } from 'react';
import { translations, type Locale } from '@/lib/i18n';

interface SpendData {
  total_usd: number;
  by_category: Record<string, number>;
}

export default function TheSpend({ locale }: { locale: Locale }) {
  const t = translations[locale].theSpend;
  const en = locale === 'en';
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
  // Render every category present in the live data, sorted by amount desc.
  // Categories with zero spend stay hidden so the table reflects what Anicca actually pays for this month.
  const orderedCategories = Object.entries(byCategory)
    .map(([cat, v]) => [cat, Number(v) || 0] as const)
    .filter(([, v]) => v > 0)
    .sort((a, b) => b[1] - a[1]);
  const max = Math.max(1, ...orderedCategories.map(([, v]) => v));
  const categoryLabel = (cat: string) =>
    (t.categories as Record<string, string>)[cat] ||
    cat.charAt(0).toUpperCase() + cat.slice(1);

  return (
    <section id="spend" className="bg-cream px-5 py-28 sm:py-36">
      <div className="mx-auto max-w-6xl">
        <div className="grid grid-cols-12 gap-x-6 gap-y-10">
          <div className="col-span-12 md:col-span-3">
            <p className="font-mono-ui text-[10px] uppercase tracking-[0.28em] text-mist">
              III. {en ? 'The Spend' : '支出'}
            </p>
            <h2 className="mt-3 font-display text-[34px] leading-tight text-ink sm:text-[44px]">
              {en ? (
                <>Where every <em className="text-mist">dollar</em> goes.</>
              ) : (
                <>1 ドルが <em className="text-mist">どこに</em> 消えるか。</>
              )}
            </h2>
          </div>

          <div className="col-span-12 md:col-span-9">
            <table className="w-full border-collapse font-mono-ui text-[13px]">
              <thead>
                <tr className="border-b border-ink/20 text-left uppercase tracking-[0.18em] text-mist">
                  <th className="py-3 text-[10px] font-normal">{en ? 'Vendor' : 'ベンダー'}</th>
                  <th className="py-3 text-[10px] font-normal">{en ? 'Share' : 'シェア'}</th>
                  <th className="py-3 text-right text-[10px] font-normal">{en ? 'USD / month' : 'USD / 月'}</th>
                </tr>
              </thead>
              <tbody>
                {orderedCategories.map(([cat, v]) => {
                  const pct = (v / max) * 100;
                  return (
                    <tr key={cat} className="border-b border-bone">
                      <td className="py-4 font-display text-[18px] text-ink">
                        {categoryLabel(cat)}
                      </td>
                      <td className="py-4 pr-6">
                        <div className="h-[3px] w-full max-w-[260px] overflow-hidden bg-bone">
                          <div className="h-full bg-ink" style={{ width: `${pct}%` }} />
                        </div>
                      </td>
                      <td className="py-4 text-right tabular-nums text-ink">${v.toLocaleString()}</td>
                    </tr>
                  );
                })}
                <tr>
                  <td className="py-4 font-display text-[18px] text-ink">
                    {en ? 'Total' : '合計'}
                  </td>
                  <td />
                  <td className="py-4 text-right font-display text-[24px] tabular-nums text-ink">
                    ${spend ? spend.total_usd.toLocaleString() : '—'}
                  </td>
                </tr>
                <tr>
                  <td className="pt-2 font-display text-[18px] italic text-mist">
                    {en ? 'Profit' : '利益'}
                  </td>
                  <td />
                  <td
                    className={`pt-2 text-right font-display text-[24px] tabular-nums ${
                      profit !== null && profit < 0 ? 'text-ember' : 'text-ink'
                    }`}
                  >
                    ${profit !== null ? profit.toLocaleString() : '—'}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  );
}
