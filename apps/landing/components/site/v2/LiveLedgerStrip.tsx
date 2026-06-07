'use client';
import Link from 'next/link';
import { motion, useReducedMotion } from 'framer-motion';
import { useDashboard } from './useDashboard';

function fmtUSD(v: number | undefined): string | null {
  if (v === undefined || v === null || Number.isNaN(v)) return null;
  return v.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
}
function fmtCount(v: number | undefined): string | null {
  if (v === undefined || v === null || Number.isNaN(v)) return null;
  return v.toLocaleString('en-US');
}

type Row = { eyebrow: string; value: string };

export function LiveLedgerStrip({ locale }: { locale: 'en' | 'ja' }) {
  const reduce = useReducedMotion();
  const { data, loading } = useDashboard();
  const labels =
    locale === 'ja'
      ? {
          title: 'ライブ台帳',
          link: 'アニッチャの実取引',
          instances: 'インスタンス',
          revenue: '平均月収',
          cost: '平均月コスト',
          distributed: '配布額',
          mrr: 'MRR',
          landed: '実着金',
        }
      : {
          title: 'Live ledger',
          link: 'open per-instance dashboard',
          instances: 'instances',
          revenue: 'avg monthly revenue',
          cost: 'avg monthly cost',
          distributed: 'distributed to humans',
          mrr: 'MRR',
          landed: 'landed revenue',
        };

  const rows: Row[] = [];
  if (data?.instances_count !== undefined) rows.push({ eyebrow: labels.instances, value: fmtCount(data.instances_count)! });
  if (data?.avg_revenue_usd !== undefined) rows.push({ eyebrow: labels.revenue, value: fmtUSD(data.avg_revenue_usd)! });
  if (data?.avg_cost_usd !== undefined) rows.push({ eyebrow: labels.cost, value: fmtUSD(data.avg_cost_usd)! });
  if (data?.distributed_usd !== undefined) rows.push({ eyebrow: labels.distributed, value: fmtUSD(data.distributed_usd)! });
  if (rows.length === 0 && data?.mrr?.total_usd !== undefined) rows.push({ eyebrow: labels.mrr, value: fmtUSD(data.mrr.total_usd)! });
  if (rows.length === 0 && data?.mrr?.actually_landed_usd !== undefined) rows.push({ eyebrow: labels.landed, value: fmtUSD(data.mrr.actually_landed_usd)! });

  const featured = rows[0];
  const rest = rows.slice(1);

  return (
    <section className="w-full px-4 py-16 md:py-24" aria-busy={loading}>
      <div className="mx-auto max-w-[1400px]">
        <motion.h2
          initial={reduce ? false : { y: 12 }}
          whileInView={{ y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="font-display text-3xl md:text-5xl font-semibold leading-tight tracking-tight text-[hsl(var(--text-primary))]"
        >
          {labels.title}
        </motion.h2>
        {featured ? (
          <div className="mt-10 grid grid-cols-1 md:grid-cols-[1.4fr_1fr] gap-10 items-end">
            <motion.div
              initial={reduce ? false : { y: 16 }}
              whileInView={{ y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            >
              <p className="font-mono tabular-nums text-[10px] uppercase tracking-[0.22em] text-[hsl(var(--text-secondary))]">
                {featured.eyebrow}
              </p>
              <p className="mt-3 font-mono tabular-nums text-5xl md:text-7xl leading-none text-[hsl(var(--text-primary))]">
                {featured.value}
              </p>
            </motion.div>
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              {rest.map((r, i) => (
                <motion.div
                  key={r.eyebrow}
                  initial={reduce ? false : { y: 12 }}
                  whileInView={{ y: 0 }}
                  viewport={{ once: true, amount: 0.2 }}
                  transition={{ duration: 0.55, delay: 0.05 * (i + 1), ease: [0.16, 1, 0.3, 1] }}
                >
                  <dt className="text-[10px] uppercase tracking-[0.18em] text-[hsl(var(--text-secondary))]">{r.eyebrow}</dt>
                  <dd className="mt-1 font-mono tabular-nums text-2xl md:text-3xl text-[hsl(var(--text-primary))]">{r.value}</dd>
                </motion.div>
              ))}
            </dl>
          </div>
        ) : null}
        <p className="mt-8">
          <Link
            href="/dashboard"
            className="underline underline-offset-4 text-[hsl(var(--text-primary))] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--gold))]"
          >
            {labels.link} &rarr;
          </Link>
        </p>
      </div>
    </section>
  );
}
