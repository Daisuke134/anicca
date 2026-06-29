'use client';
import Link from 'next/link';
import { motion, useReducedMotion } from 'framer-motion';

// Surplus → people. CTA goes to /income (a real application page, Stripe Connect).
// No dashboard $ here: the old /dashboard.json "distributed" mixed in non-anicca
// numbers (spec31 R3-4); we don't present a fake figure.
export function BasicIncomeNote({ locale }: { locale: 'en' | 'ja' }) {
  const reduce = useReducedMotion();

  const labels =
    locale === 'ja'
      ? {
          body: '稼ぎの余りは、毎月、人にそのまま配る。受け取る側に条件はない。',
          cta: 'ベーシックインカムを受け取る',
        }
      : {
          body: 'Whatever it makes beyond its own costs goes back to people every month. No conditions on the receiving end.',
          cta: 'Receive basic income',
        };

  return (
    <section className="w-full px-4 py-16 md:py-24">
      <div className="mx-auto max-w-[1400px]">
        <motion.div
          initial={reduce ? false : { y: 12 }}
          whileInView={{ y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="max-w-[34ch]"
        >
          <p className="font-display text-2xl md:text-4xl font-semibold leading-snug tracking-tight text-[hsl(var(--text-primary))]">
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
      </div>
    </section>
  );
}
