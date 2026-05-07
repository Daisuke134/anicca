'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { translations, type Locale } from '@/lib/i18n';

interface LiveNumbersProps {
  locale: Locale;
}

interface DashboardData {
  updated_at: string;
  mrr: { total_usd: number };
  followers: { total: number };
  views: { weekly_total: number; target: number; progress_pct: number };
  spend: { total_usd: number };
  profit_usd: number;
  goals: { mrr_target: number; mrr_deadline: string; progress_pct: number };
  basic_income?: { pool_usd: number };
}

function CountUp({
  value,
  prefix = '',
  suffix = '',
  decimals = 0,
}: {
  value: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    let raf: number;
    const start = performance.now();
    const duration = 900;
    const from = 0;
    const to = value;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      // ease-out cubic
      const e = 1 - Math.pow(1 - t, 3);
      const v = from + (to - from) * e;
      if (ref.current) {
        ref.current.textContent = `${prefix}${v.toFixed(decimals)}${suffix}`;
      }
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, prefix, suffix, decimals]);
  return <span ref={ref}>{`${prefix}${value.toFixed(decimals)}${suffix}`}</span>;
}

function fmtUSD(n: number, decimals = 0) {
  return `$${n.toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}`;
}

interface RowProps {
  label: string;
  primary: React.ReactNode;
  meta?: React.ReactNode;
}

function Row({ label, primary, meta }: RowProps) {
  return (
    <div className="grid grid-cols-12 items-baseline gap-4 border-t border-[hsl(var(--hairline))] py-7">
      <div className="col-span-12 sm:col-span-5">
        <p className="font-mono text-[0.72rem] uppercase tracking-[0.18em] text-secondary">{label}</p>
      </div>
      <div className="col-span-7 sm:col-span-5 font-serif text-3xl tracking-tight text-foreground md:text-4xl">
        {primary}
      </div>
      <div className="col-span-5 sm:col-span-2 text-right font-mono text-xs text-muted">
        {meta}
      </div>
    </div>
  );
}

export default function LiveNumbers({ locale }: LiveNumbersProps) {
  const t = translations[locale].liveNumbers;
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/dashboard.json')
      .then((r) => (r.ok ? r.json() : Promise.reject('fetch failed')))
      .then(setData)
      .catch((e) => setError(String(e)));
  }, []);

  if (error || !data) {
    return (
      <section className="section bg-background">
        <div className="container-content">
          <p className="eyebrow">{t.eyebrow}</p>
          <h2 className="display mt-6 text-4xl text-foreground md:text-5xl">{t.title}</h2>
          <p className="mt-10 text-secondary">{error ? t.labels.offline : t.labels.loading}</p>
        </div>
      </section>
    );
  }

  const updated = new Date(data.updated_at).toLocaleString(
    locale === 'ja' ? 'ja-JP' : 'en-US',
    { hour: '2-digit', minute: '2-digit', month: 'short', day: 'numeric' },
  );
  const mrrPct = data.goals.progress_pct;
  const profit = data.profit_usd;

  return (
    <section className="section bg-background">
      <div className="container-content">
        <div className="grid grid-cols-1 gap-x-16 gap-y-10 md:grid-cols-12">
          <div className="md:col-span-4">
            <p className="eyebrow">{t.eyebrow}</p>
            <h2 className="display mt-6 text-4xl font-normal leading-[1.05] tracking-tight text-foreground md:text-5xl">
              {t.title}
            </h2>
            <p className="mt-6 max-w-prose text-base text-secondary">{t.subtitle}</p>
            <p className="mt-6 font-mono text-[0.7rem] uppercase tracking-[0.18em] text-muted">
              {t.labels.updated} · {updated}
            </p>
          </div>

          <div className="md:col-span-8">
            <div className="border-b border-[hsl(var(--hairline))]">
              <Row
                label={t.labels.mrr}
                primary={<CountUp value={data.mrr.total_usd} prefix="$" decimals={2} />}
                meta={
                  <>
                    {mrrPct.toFixed(1)}% {t.labels.mrrTarget}{' '}
                    {fmtUSD(data.goals.mrr_target)}
                  </>
                }
              />
              <Row
                label={t.labels.spend}
                primary={<CountUp value={data.spend.total_usd} prefix="$" decimals={0} />}
                meta="/mo"
              />
              <Row
                label={t.labels.profit}
                primary={
                  <span className={profit < 0 ? 'text-[hsl(0,60%,42%)]' : ''}>
                    <CountUp value={profit} prefix="$" decimals={0} />
                  </span>
                }
                meta="/mo"
              />
              <Row
                label={t.labels.weeklyViews}
                primary={<CountUp value={data.views.weekly_total} />}
                meta={
                  <>
                    {data.views.progress_pct.toFixed(1)}% {t.labels.viewsTarget}
                  </>
                }
              />
              <Row
                label={t.labels.basicIncomePool}
                primary={
                  <CountUp
                    value={data.basic_income?.pool_usd ?? 0}
                    prefix="$"
                    decimals={2}
                  />
                }
                meta="·"
              />
              <Row
                label={t.labels.followers}
                primary={<CountUp value={data.followers.total} />}
                meta="·"
              />
            </div>

            <p className="mt-10 font-mono text-[0.72rem] uppercase tracking-[0.18em] text-secondary">
              ★ {t.footer.prefix}{' '}
              <a
                href="https://github.com/Daisuke134/anicca"
                target="_blank"
                rel="noopener noreferrer"
                className="link-quiet"
              >
                {t.footer.link}
              </a>
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
