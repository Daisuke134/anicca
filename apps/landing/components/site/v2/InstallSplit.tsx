'use client';
import Link from 'next/link';
import { motion, useReducedMotion } from 'framer-motion';
import { CTA } from '@/components/site/taste';

export function InstallSplit({ locale }: { locale: 'en' | 'ja' }) {
  const reduce = useReducedMotion();
  const REPO = 'https://github.com/Daisuke134/anicca';
  const labels =
    locale === 'ja'
      ? {
          title: '動かす',
          cloudTitle: 'クラウドで動かす',
          cloudBody: 'Akash 上に住処を借りる。ウォレットに USDC を入れれば、あとは自分で動き続ける。手順は GitHub に。',
          cloudCta: 'GitHub の手順',
          localTitle: '手元で動かす',
          localBody: '自分のマシンで動かす。clone して install.sh を走らせるだけ。鍵もデータも手元に残る。手順は GitHub に。',
          localCta: 'GitHub の手順',
        }
      : {
          title: 'Run it',
          cloudTitle: 'Run on cloud',
          cloudBody: 'Rent shelter on Akash. Put USDC in its wallet and it keeps itself running. Steps on GitHub.',
          cloudCta: 'Steps on GitHub',
          localTitle: 'Run locally',
          localBody: 'Run it on your own machine. Clone, run install.sh. Your keys and data stay with you. Steps on GitHub.',
          localCta: 'Steps on GitHub',
        };

  return (
    <section id="start" className="w-full px-4 py-16 md:py-24 scroll-mt-20">
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
        <div className="mt-10 grid grid-cols-1 md:grid-cols-2 gap-6">
          {[
            { t: labels.cloudTitle, b: labels.cloudBody, href: REPO, cta: labels.cloudCta, tint: true, external: true },
            { t: labels.localTitle, b: labels.localBody, href: REPO, cta: labels.localCta, tint: false, external: true },
          ].map((c, i) => (
            <motion.div
              key={c.t}
              initial={reduce ? false : { y: 14 }}
              whileInView={{ y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.55, delay: 0.06 * i, ease: [0.16, 1, 0.3, 1] }}
              className={
                c.tint
                  ? 'rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface-elevated))] p-6 md:p-8'
                  : 'rounded-card border border-[hsl(var(--border))] p-6 md:p-8'
              }
            >
              <h3 className="font-display text-2xl md:text-3xl font-semibold text-[hsl(var(--text-primary))]">{c.t}</h3>
              <p className="mt-3 text-base leading-relaxed text-[hsl(var(--text-secondary))] max-w-[42ch]">{c.b}</p>
              <div className="mt-6">
                {c.external ? (
                  <Link
                    href={c.href}
                    className="underline underline-offset-4 font-medium text-[hsl(var(--text-primary))] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--gold))]"
                  >
                    {c.cta} &rarr;
                  </Link>
                ) : (
                  <CTA href={c.href} variant="primary">
                    {c.cta}
                  </CTA>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
