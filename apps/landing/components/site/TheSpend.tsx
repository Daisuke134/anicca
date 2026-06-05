'use client';

// TODO(§11.F-followup): migrate hardcoded labels into translations.theSpend.*
// during the i18n consolidation sweep. Inline ternaries kept here to avoid
// touching i18n.ts cross-section during the per-page redesign.

import { useEffect, useState } from 'react';
import { translations, type Locale } from '@/lib/i18n';
import { Section, Reveal } from '@/components/site/taste';

interface SpendData {
  total_usd: number;
  by_category: Record<string, number>;
}

export default function TheSpend({ locale }: { locale: Locale }) {
  const t = translations[locale].theSpend;
  const en = locale === 'en';
  const [spend, setSpend] = useState<SpendData | null>(null);
  const [profit, setProfit] = useState<number | null>(null);

  // §11.F: data source /dashboard.json preserved verbatim
  useEffect(() => {
    const ctrl = new AbortController();
    fetch('/dashboard.json', { signal: ctrl.signal })
      .then((r) => {
        if (!r.ok) throw new Error('failed');
        return r.json();
      })
      .then((d) => {
        setSpend(d.spend);
        setProfit(d.profit_usd);
      })
      .catch((e: unknown) => {
        if (e instanceof Error && e.name !== 'AbortError') {
          // swallow non-abort errors silently (component degrades to '...' skeleton)
        }
      });
    return () => ctrl.abort();
  }, []);

  const byCategory = spend?.by_category ?? {};
  // Render every category present in the live data, sorted by amount desc.
  // Categories with zero spend stay hidden so the table reflects what Anicca actually pays for this month.
  const orderedCategories = Object.entries(byCategory)
    .map(([cat, v]) => [cat, Number(v) || 0] as const)
    .filter(([, v]) => v > 0)
    .sort((a, b) => b[1] - a[1]);

  const categoryLabel = (cat: string) =>
    (t.categories as Record<string, string>)[cat] ||
    cat.charAt(0).toUpperCase() + cat.slice(1);

  // §4.9 featured-vs-rest: top 3 as hero tiles, rest as compact grouped chunk
  const featured = orderedCategories.slice(0, 3);
  const rest = orderedCategories.slice(3);
  const maxFeatured = Math.max(1, ...featured.map(([, v]) => v));

  return (
    <Section id="spend" className="bg-[hsl(var(--background))]">
      <Reveal>
        {/* Section header */}
        <div className="mb-12">
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            III. {en ? 'The Spend' : '支出'}
          </p>
          <h2 className="mt-3 font-display text-[34px] leading-tight text-foreground sm:text-[44px]">
            {en ? (
              <>Where every <em className="text-muted-foreground">dollar</em> goes.</>
            ) : (
              <>1 ドルが <em className="text-muted-foreground">どこに</em> 消えるか。</>
            )}
          </h2>
        </div>
      </Reveal>

      {/* §4.9 featured hero tiles: top 3 biggest spend categories */}
      <Reveal delay={0.1}>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {(spend ? featured : ([['', 0], ['', 0], ['', 0]] as const)).map(([cat, v], i) => {
            const barPct = spend ? (v / maxFeatured) * 100 : 0;
            const label = cat ? categoryLabel(cat) : ' ';
            return (
              <div
                key={cat || i}
                className="rounded-card bg-card p-6 shadow-[0_1px_2px_hsl(var(--foreground)/.05),0_4px_16px_hsl(var(--foreground)/.04)]"
              >
                <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                  {en ? 'Top spend' : 'トップ支出'}
                </p>
                <p className="mt-2 font-display text-[22px] leading-tight text-foreground sm:text-[26px]">
                  {label}
                </p>
                <p className="mt-1 font-mono tabular-nums text-[32px] font-semibold leading-none text-foreground">
                  {spend ? `$${v.toLocaleString('en-US')}` : '...'}
                </p>
                {/* Proportional bar within featured tiles */}
                {spend && (
                  <div className="mt-4 h-[3px] w-full overflow-hidden rounded-pill bg-border">
                    <div
                      className="h-full rounded-pill bg-foreground"
                      style={{ width: `${barPct}%` }}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </Reveal>

      {/* §4.9 grouped chunk: remaining categories (compact 2-col) */}
      {(spend ? rest.length > 0 : true) && (
        <Reveal delay={0.2}>
          <div className="mt-6 rounded-card bg-card p-6 shadow-[0_1px_2px_hsl(var(--foreground)/.05)]">
            <p className="mb-4 font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
              {en ? 'Other costs' : 'その他のコスト'}
            </p>
            <div className="grid grid-cols-2 gap-x-8 gap-y-3 sm:grid-cols-3">
              {(spend ? rest : []).map(([cat, v]) => (
                <div key={cat} className="flex items-baseline justify-between gap-2">
                  <span className="truncate text-[14px] text-foreground">{categoryLabel(cat)}</span>
                  <span className="shrink-0 font-mono tabular-nums text-[13px] text-muted-foreground">
                    ${v.toLocaleString('en-US')}
                  </span>
                </div>
              ))}
              {spend && rest.length === 0 && (
                <p className="col-span-full text-[13px] text-muted-foreground">
                  {en ? 'No further items.' : 'その他のコストはありません。'}
                </p>
              )}
            </div>
          </div>
        </Reveal>
      )}

      {/* Totals row: total + profit */}
      <Reveal delay={0.3}>
        <div className="mt-6 grid grid-cols-2 gap-4">
          <div className="rounded-card border border-border p-5">
            <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
              {t.total}
            </p>
            <p className="mt-1 font-display font-mono tabular-nums text-[28px] text-foreground sm:text-[34px]">
              {spend ? `$${spend.total_usd.toLocaleString('en-US')}` : '...'}
            </p>
          </div>
          <div className="rounded-card border border-border p-5">
            <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
              {t.profit}
            </p>
            <p
              className={`mt-1 font-display font-mono tabular-nums text-[28px] sm:text-[34px] ${
                profit !== null && profit < 0 ? 'text-destructive' : 'text-foreground'
              }`}
            >
              {profit !== null ? `$${profit.toLocaleString('en-US')}` : '...'}
            </p>
          </div>
        </div>
      </Reveal>
    </Section>
  );
}
