'use client';
import { motion, useReducedMotion } from 'framer-motion';

export function VisionBand({ locale }: { locale: 'en' | 'ja' }) {
  const reduce = useReducedMotion();
  const labels =
    locale === 'ja'
      ? {
          number: '∞',
          line1: '何兆体の AI が協力し、',
          line2: '世界から苦しみを終わらせる。',
          caption: '長期目標',
        }
      : {
          number: '∞',
          line1: 'Trillions of cooperating AIs',
          line2: 'end world suffering.',
          caption: 'long horizon',
        };

  return (
    <section className="w-full bg-[hsl(var(--surface-elevated))]">
      <div className="mx-auto grid max-w-[1400px] grid-cols-1 md:grid-cols-[0.9fr_1.1fr] items-center gap-6 px-4 py-20 md:py-32">
        <motion.div
          initial={reduce ? false : { y: 16 }}
          whileInView={{ y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
          className="flex items-end gap-4"
        >
          <span
            aria-hidden
            className="font-mono leading-none text-[10rem] md:text-[16rem] text-[hsl(var(--gold))]"
          >
            {labels.number}
          </span>
          <span className="pb-3 font-mono tabular-nums text-[10px] uppercase tracking-[0.22em] text-[hsl(var(--text-secondary))]">
            {labels.caption}
          </span>
        </motion.div>
        <motion.p
          initial={reduce ? false : { y: 12 }}
          whileInView={{ y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.7, delay: 0.06, ease: [0.16, 1, 0.3, 1] }}
          className="font-display text-2xl md:text-4xl font-semibold leading-snug tracking-tight text-[hsl(var(--text-primary))] max-w-[28ch]"
        >
          {labels.line1} {labels.line2}
        </motion.p>
      </div>
    </section>
  );
}
