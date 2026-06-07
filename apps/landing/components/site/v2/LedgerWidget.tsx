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
          instances: 'インスタンス',
          revenue: '月収',
          cost: '月コスト',
          distributed: '配布額',
          loading: '読み込み中',
        }
      : {
          instances: 'instances',
          revenue: 'monthly revenue',
          cost: 'monthly cost',
          distributed: 'distributed',
          loading: 'loading',
        };

  const tiles: Tile[] = [];
  if (data?.instances_count !== undefined) {
    tiles.push({ label: labels.instances, value: formatCount(data.instances_count)! });
  }
  if (data?.avg_revenue_usd !== undefined) {
    tiles.push({ label: labels.revenue, value: formatUSD(data.avg_revenue_usd)! });
  }
  if (data?.avg_cost_usd !== undefined) {
    tiles.push({ label: labels.cost, value: formatUSD(data.avg_cost_usd)! });
  }
  if (data?.distributed_usd !== undefined) {
    tiles.push({ label: labels.distributed, value: formatUSD(data.distributed_usd)! });
  }

  // Fallback: if no instance-economics fields are present yet, surface
  // the existing MRR-style numbers so the hero asset is never empty.
  if (tiles.length === 0 && data?.mrr?.actually_landed_usd !== undefined) {
    tiles.push({
      label: locale === 'ja' ? '実着金' : 'landed revenue',
      value: formatUSD(data.mrr.actually_landed_usd)!,
    });
  }
  if (tiles.length === 0 && data?.mrr?.total_usd !== undefined) {
    tiles.push({
      label: locale === 'ja' ? 'MRR' : 'MRR',
      value: formatUSD(data.mrr.total_usd)!,
    });
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
