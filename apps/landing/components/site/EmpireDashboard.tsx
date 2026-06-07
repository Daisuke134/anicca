'use client';

// TODO(§11.F-followup): migrate hardcoded labels into translations.empireDashboard.*
// during the i18n consolidation sweep. Inline ternaries kept here to avoid
// touching i18n.ts cross-section during the per-page redesign.

import { useEffect, useRef, useState } from 'react';
import { useReducedMotion } from 'framer-motion';
import { translations, type Locale } from '@/lib/i18n';
import { Section, Reveal } from '@/components/site/taste';

function CountUp({ value, prefix = '', suffix = '', decimals = 0 }: { value: number; prefix?: string; suffix?: string; decimals?: number }) {
  const reduce = useReducedMotion();
  const [display, setDisplay] = useState(value);
  const prev = useRef<number | null>(null);

  useEffect(() => {
    if (reduce || prev.current === null) {
      // First mount: render the real value immediately (ledger trust, §11.F)
      // OR user prefers reduced motion: skip animation
      prev.current = value;
      setDisplay(value);
      return;
    }
    if (prev.current === value) return;

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
  }, [value, reduce]);

  return <span className="font-mono tabular-nums">{`${prefix}${display.toFixed(decimals)}${suffix}`}</span>;
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
    const ctrl = new AbortController();
    fetch('/dashboard.json', { signal: ctrl.signal })
      .then((r) => {
        if (!r.ok) throw new Error('fetch failed');
        return r.json();
      })
      .then((j: DashboardData) => setData(j))
      .catch((e: unknown) => {
        if (e instanceof Error && e.name !== 'AbortError') setError(e.message);
      });
    return () => ctrl.abort();
  }, []);

  const offline = error || !data;
  const mrrPct = data?.goals.progress_pct ?? 0;
  const updated = data
    ? new Date(data.updated_at).toLocaleString(en ? 'en-US' : 'ja-JP', {
        hour: '2-digit', minute: '2-digit', month: 'short', day: 'numeric',
      })
    : '--';

  return (
    <Section id="empire" className="bg-[hsl(var(--background))]">
      <Reveal>
        {/* Section header */}
        <div className="mb-12">
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            II. {en ? 'The Empire' : '帝国'}
          </p>
          <h2 className="mt-3 font-display text-[34px] leading-tight text-foreground sm:text-[42px]">
            {en ? (
              <>Live revenue,<br /><em className="text-muted-foreground">no theatre.</em></>
            ) : (
              <>ライブの売上、<br /><em className="text-muted-foreground">演出なし。</em></>
            )}
          </h2>
        </div>
      </Reveal>

      {/* Featured hero metrics - 3 tiles */}
      <Reveal delay={0.08}>
        <div className="grid grid-cols-1 gap-8 md:grid-cols-3">

          {/* Hero tile 1: MRR value */}
          <div className="col-span-1 md:col-span-2 border border-border p-7 sm:p-10">
            <div className="flex flex-wrap items-baseline justify-between gap-3">
              <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
                {en ? 'Monthly Recurring Revenue' : '月次経常収益'}
              </p>
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                {en ? 'Updated' : '更新'} {updated}
              </p>
            </div>
            <div className="mt-3 flex flex-wrap items-end gap-x-6 gap-y-2">
              <p className="font-display text-[64px] leading-none tracking-tight text-foreground sm:text-[88px]">
                {data ? <CountUp value={data.mrr.total_usd} prefix="$" decimals={2} /> : '--'}
              </p>
              <p className="font-mono text-[14px] text-muted-foreground">
                / <span className="font-mono tabular-nums">${data?.goals.mrr_target.toLocaleString() ?? '--'}</span>{' '}
                {en ? 'goal' : '目標'}
              </p>
            </div>
          </div>

          {/* Hero tile 2: progress toward goal */}
          <div className="col-span-1 border border-border p-7 sm:p-10 flex flex-col justify-between">
            <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
              {en ? 'Goal Progress' : '達成率'}
            </p>
            <div className="mt-6">
              <p className="font-display text-[56px] leading-none tracking-tight text-foreground sm:text-[72px]">
                <span className="font-mono tabular-nums">{mrrPct.toFixed(1)}</span>
                <span className="font-mono text-[28px] text-muted-foreground">%</span>
              </p>
              <div className="mt-4 h-[3px] w-full overflow-hidden bg-muted">
                <div
                  className="h-full bg-gold transition-all"
                  style={{ width: `${Math.max(0, Math.min(100, mrrPct))}%` }}
                />
              </div>
            </div>
          </div>

        </div>
      </Reveal>

      {/* Grouped chunks - supplemental rows */}
      <Reveal delay={0.16}>
        <div className="mt-2 border-t border-border">

          {/* Deadline row */}
          <div className="flex items-baseline justify-between py-4 border-b border-border">
            <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              {en ? 'Deadline' : '期日'}
            </p>
            <p className="font-mono tabular-nums text-[14px] text-foreground">
              {en ? 'by ' : ''}{data?.goals.mrr_deadline ?? '--'}
            </p>
          </div>

          {/* Offline notice */}
          {offline && (
            <div className="py-4">
              <p className="text-[14px] text-muted-foreground">{t.dashboardOffline}</p>
            </div>
          )}

        </div>
      </Reveal>
    </Section>
  );
}
