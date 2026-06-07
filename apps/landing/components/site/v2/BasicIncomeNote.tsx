'use client';
import Link from 'next/link';
import { motion, useReducedMotion } from 'framer-motion';
import { useDashboard } from './useDashboard';

function fmtUSD(v: number | undefined): string | null {
  if (v === undefined || v === null || Number.isNaN(v)) return null;
  return v.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
}

export function BasicIncomeNote({ locale }: { locale: 'en' | 'ja' }) {
  const reduce = useReducedMotion();
  const { data } = useDashboard();
  const distributed = fmtUSD(data?.basic_income?.distributed_usd);
  const recipients = data?.basic_income?.recipients;

  const labels =
    locale === 'ja'
      ? {
          body: '余剰は、毎月、人類に配る。受け取り側は何の条件もない。',
          cta: 'ベーシックインカムを受け取る',
          distributedLabel: '配布済',
          recipientsLabel: '受給者',
        }
      : {
          body: 'Surplus flows back to humans every month. No conditions on the receiving end.',
          cta: 'Receive basic income',
          distributedLabel: 'distributed',
          recipientsLabel: 'recipients',
        };

  return (
    <section className="w-full px-4 py-16 md:py-24">
      <div className="mx-auto grid max-w-[1400px] grid-cols-1 md:grid-cols-[1.4fr_1fr] gap-10 items-center">
        <motion.div
          initial={reduce ? false : { y: 12 }}
          whileInView={{ y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        >
          <p className="font-display text-2xl md:text-4xl font-semibold leading-snug tracking-tight text-[hsl(var(--text-primary))] max-w-[28ch]">
            {labels.body}
          </p>
          <p className="mt-6">
            <Link
              href="/income"
              className="inline-flex items-center rounded-pill bg-[hsl(var(--gold))] px-6 py-3 font-medium text-[#18181b] transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] active:scale-[0.98] active:translate-y-px focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--gold))]"
            >
              {labels.cta}
            </Link>
          </p>
        </motion.div>
        {distributed || recipients !== undefined ? (
          <dl className="grid grid-cols-2 gap-6">
            {distributed ? (
              <div>
                <dt className="text-[10px] uppercase tracking-[0.18em] text-[hsl(var(--text-secondary))]">{labels.distributedLabel}</dt>
                <dd className="mt-1 font-mono tabular-nums text-2xl md:text-4xl text-[hsl(var(--text-primary))]">{distributed}</dd>
              </div>
            ) : null}
            {recipients !== undefined ? (
              <div>
                <dt className="text-[10px] uppercase tracking-[0.18em] text-[hsl(var(--text-secondary))]">{labels.recipientsLabel}</dt>
                <dd className="mt-1 font-mono tabular-nums text-2xl md:text-4xl text-[hsl(var(--text-primary))]">{recipients.toLocaleString('en-US')}</dd>
              </div>
            ) : null}
          </dl>
        ) : null}
      </div>
    </section>
  );
}
