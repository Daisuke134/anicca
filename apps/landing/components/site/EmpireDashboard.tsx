'use client';

import { useEffect, useRef, useState } from 'react';
import { translations, type Locale } from '@/lib/i18n';

function CountUp({ value, prefix = '', suffix = '', decimals = 0 }: { value: number; prefix?: string; suffix?: string; decimals?: number }) {
  const [display, setDisplay] = useState(value);
  const prev = useRef(0);

  useEffect(() => {
    const start = prev.current;
    const delta = value - start;
    const duration = 1200;
    const startedAt = performance.now();
    let frame = 0;

    const tick = (now: number) => {
      const progress = Math.min(1, (now - startedAt) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      const next = start + delta * eased;
      setDisplay(next);
      if (progress < 1) {
        frame = requestAnimationFrame(tick);
      }
    };

    frame = requestAnimationFrame(tick);
    prev.current = value;

    return () => cancelAnimationFrame(frame);
  }, [value]);

  return <span>{`${prefix}${display.toFixed(decimals)}${suffix}`}</span>;
}

interface DashboardData {
  updated_at: string;
  mrr: { total_usd: number; by_product: Record<string, number> };
  goals: { mrr_target: number; mrr_deadline: string; progress_pct: number };
}

export default function EmpireDashboard({ locale }: { locale: Locale }) {
  const t = translations[locale].empire;
  const en = locale === 'en';
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/dashboard.json')
      .then((r) => (r.ok ? r.json() : Promise.reject('fetch failed')))
      .then(setData)
      .catch((e) => setError(String(e)));
  }, []);

  const offline = error || !data;
  const mrrPct = data?.goals.progress_pct ?? 0;
  const updated = data
    ? new Date(data.updated_at).toLocaleString(en ? 'en-US' : 'ja-JP', {
        hour: '2-digit', minute: '2-digit', month: 'short', day: 'numeric',
      })
    : '—';

  return (
    <section id="empire" className="relative bg-cream px-5 pb-20 pt-8">
      <div className="mx-auto max-w-6xl">
        <div className="editorial-rule mb-12" />
        <div className="grid grid-cols-12 gap-x-6 gap-y-8">
          <div className="col-span-12 md:col-span-3">
            <p className="font-mono-ui text-[10px] uppercase tracking-[0.28em] text-mist">
              II. {en ? 'The Empire' : '帝国'}
            </p>
            <h2 className="mt-3 font-display text-[34px] leading-tight text-ink sm:text-[42px]">
              {en ? (
                <>Live revenue,<br /><em className="text-mist">no theatre.</em></>
              ) : (
                <>ライブの売上、<br /><em className="text-mist">演出なし。</em></>
              )}
            </h2>
          </div>

          <div className="col-span-12 md:col-span-9">
            <div className="border border-bone bg-card p-7 sm:p-10">
              <div className="flex flex-wrap items-baseline justify-between gap-3">
                <p className="font-mono-ui text-[11px] uppercase tracking-[0.2em] text-mist">
                  {en ? 'Monthly Recurring Revenue' : '月次経常収益'}
                </p>
                <p className="font-mono-ui text-[10px] uppercase tracking-[0.18em] text-mist">
                  {en ? 'Updated' : '更新'} {updated}
                </p>
              </div>

              <div className="mt-3 flex flex-wrap items-end gap-x-6 gap-y-2">
                <p className="font-display text-[64px] leading-none tracking-tight text-ink sm:text-[88px]">
                  {data ? <CountUp value={data.mrr.total_usd} prefix="$" decimals={2} /> : '—'}
                </p>
                <p className="font-mono-ui text-[14px] text-mist">
                  / ${data?.goals.mrr_target.toLocaleString() ?? '—'} {en ? 'goal' : '目標'}
                </p>
              </div>

              <div className="mt-6 h-[3px] w-full overflow-hidden bg-bone">
                <div
                  className="h-full bg-gold transition-all"
                  style={{ width: `${Math.max(0, Math.min(100, mrrPct))}%` }}
                />
              </div>
              <p className="mt-2 flex items-baseline justify-between font-mono-ui text-[11px] uppercase tracking-[0.18em] text-mist">
                <span>{mrrPct.toFixed(1)}%</span>
                <span>{en ? 'by' : '期日'} {data?.goals.mrr_deadline ?? '—'}</span>
              </p>

              {offline && (
                <p className="mt-6 border-t border-bone pt-4 text-[14px] text-mist">
                  {t.dashboardOffline}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
