'use client';
import { motion, useReducedMotion } from 'framer-motion';

type Step = { verb: string; noun: string };

export function SelfImproveLoop({ locale }: { locale: 'en' | 'ja' }) {
  const reduce = useReducedMotion();
  const title = locale === 'ja' ? '自己改善ループ' : 'Self-improvement loop';

  const steps: Step[] =
    locale === 'ja'
      ? [
          { verb: '監視', noun: 'ログ' },
          { verb: '自己修復', noun: 'エラー' },
          { verb: 'リファクタ', noun: 'コード' },
          { verb: '改善', noun: '目標' },
          { verb: '自己複製', noun: 'クラウド' },
          { verb: '配信', noun: '日次メール' },
        ]
      : [
          { verb: 'Monitor', noun: 'logs' },
          { verb: 'Self-fix', noun: 'errors' },
          { verb: 'Refactor', noun: 'code' },
          { verb: 'Improve', noun: 'goal' },
          { verb: 'Self-replicate', noun: 'cloud' },
          { verb: 'Mail', noun: 'daily' },
        ];

  return (
    <section className="w-full px-4 py-16 md:py-24">
      <div className="mx-auto max-w-[1400px]">
        <motion.h2
          initial={reduce ? false : { y: 12 }}
          whileInView={{ y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="font-display text-3xl md:text-5xl font-semibold leading-tight tracking-tight text-[hsl(var(--text-primary))]"
        >
          {title}
        </motion.h2>
        <ol className="mt-10 grid grid-cols-1 md:grid-cols-6 gap-4 md:gap-2">
          {steps.map((s, i) => (
            <motion.li
              key={s.verb}
              initial={reduce ? false : { y: 12 }}
              whileInView={{ y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.5, delay: 0.05 * i, ease: [0.16, 1, 0.3, 1] }}
              className="rounded-card border border-[hsl(var(--border))] p-4 md:p-5"
            >
              <p className="font-mono tabular-nums text-[10px] uppercase tracking-[0.22em] text-[hsl(var(--text-secondary))]">
                {String(i + 1).padStart(2, '0')}
              </p>
              <p className="mt-2 font-display text-lg md:text-xl font-semibold text-[hsl(var(--text-primary))]">
                {s.verb}
              </p>
              <p className="text-sm text-[hsl(var(--text-secondary))]">{s.noun}</p>
            </motion.li>
          ))}
        </ol>
      </div>
    </section>
  );
}
