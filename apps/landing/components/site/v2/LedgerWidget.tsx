'use client';
import { motion, useReducedMotion } from 'framer-motion';
import { useDashboard } from './useDashboard';

type Tile = { label: string; value: string };

function formatUSD(v: number | undefined): string | null {
  if (v === undefined || v === null || Number.isNaN(v)) return null;
  return v.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  });
}

function formatCount(v: number | undefined): string | null {
  if (v === undefined || v === null || Number.isNaN(v)) return null;
  return v.toLocaleString('en-US');
}

export function LedgerWidget({ locale }: { locale: 'en' | 'ja' }) {
  const { data, loading } = useDashboard();
  const reduce = useReducedMotion();

  const labels =
    locale === 'ja'
      ? {
          netWorth: '純資産',
          earned: '月の稼ぎ',
          alive: '稼働中',
          selfFunded: '自給率',
          loading: '読み込み中',
        }
      : {
          netWorth: 'net worth',
          earned: 'earned / mo',
          alive: 'alive',
          selfFunded: 'self-funded',
          loading: 'loading',
        };

  // Real Anicca-colony numbers from dashboard-sync (same source as /dashboard).
  // No iOS/RevenueCat MRR here — an anicca's revenue is its own, near zero today.
  const tiles: Tile[] = [];
  if (data?.total_net_worth_usd !== undefined) {
    tiles.push({ label: labels.netWorth, value: formatUSD(data.total_net_worth_usd)! });
  }
  if (data?.earned_mo_usd !== undefined) {
    tiles.push({ label: labels.earned, value: formatUSD(data.earned_mo_usd)! });
  }
  if (data?.alive !== undefined) {
    tiles.push({ label: labels.alive, value: formatCount(data.alive)! });
  }
  if (data?.self_funded_pct !== undefined) {
    tiles.push({ label: labels.selfFunded, value: `${formatCount(data.self_funded_pct)!}%` });
  }

  const enter = (delay: number) => ({
    initial: reduce ? false : { opacity: 0, y: 12 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.5, delay, ease: [0.16, 1, 0.3, 1] as const },
  });

  return (
    <dl
      aria-busy={loading}
      className="grid grid-cols-2 gap-3 rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface-elevated))] p-6 md:p-8"
    >
      {tiles.length === 0 && loading ? (
        // §6.B reduced-motion: skeleton is a static dash, not a spinner
        <motion.div {...enter(0)} className="col-span-2">
          <span className="font-mono tabular-nums text-2xl text-[hsl(var(--text-secondary))]">
            {labels.loading}
          </span>
        </motion.div>
      ) : (
        tiles.map((t, i) => (
          <motion.div key={t.label} {...enter(0.06 * i)} className="min-w-0">
            <dt className="text-[10px] uppercase tracking-[0.18em] text-[hsl(var(--text-secondary))]">
              {t.label}
            </dt>
            <dd className="mt-1 font-mono tabular-nums text-2xl md:text-3xl text-[hsl(var(--text-primary))]">
              {t.value}
            </dd>
          </motion.div>
        ))
      )}
    </dl>
  );
}
