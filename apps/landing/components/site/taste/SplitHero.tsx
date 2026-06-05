'use client';
import { motion, useReducedMotion } from 'framer-motion';
import React from 'react';

type SplitHeroProps = {
  eyebrow?: string;           // §4.7: hero text 要素 max4 のうち任意1
  headline: React.ReactNode;  // ≤2行
  subtext: string;            // ≤20語 ≤4行
  primary: React.ReactNode;   // CTA primary
  secondary?: React.ReactNode;// CTA secondary (任意)
  asset: React.ReactNode;     // 実ビジュアル (§4.8, div偽UI禁止)
};

// §4.3 ANTI-CENTER (VARIANCE>4): 左テキスト / 右アセット。
// §4.7: pt-24上限, min-h-[100dvh], headline≤2行, subtext≤20語, CTA viewport内。
export function SplitHero({ eyebrow, headline, subtext, primary, secondary, asset }: SplitHeroProps) {
  const reduce = useReducedMotion();
  const enter = (delay: number) => ({
    initial: reduce ? false : { opacity: 0, y: 24 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.6, delay, ease: [0.16, 1, 0.3, 1] as const },
  });
  // §4.7: pt-24(6rem) + pb-16(4rem) = 10rem。内部grid は viewport 残量に収め
  // CTA を desktop で必ず viewport 内に出す (Hero MUST fit in the initial viewport)。
  return (
    <section className="w-full px-4 pt-24 pb-16 md:min-h-[100dvh]">
      <div className="mx-auto grid max-w-[1400px] grid-cols-1 items-center gap-10 md:min-h-[calc(100dvh-10rem)] md:grid-cols-[1.1fr_0.9fr]">
        <div className="max-w-[34rem]">
          {eyebrow ? (
            <motion.p {...enter(0)} className="mb-4 text-[11px] uppercase tracking-[0.18em] text-[hsl(var(--text-secondary))]">
              {eyebrow}
            </motion.p>
          ) : null}
          <motion.h1 {...enter(0.06)} className="font-display text-4xl font-semibold leading-[1.05] tracking-tight text-[hsl(var(--text-primary))] md:text-6xl">
            {headline}
          </motion.h1>
          <motion.p {...enter(0.12)} className="mt-5 max-w-[40ch] text-base leading-relaxed text-[hsl(var(--text-secondary))]">
            {subtext}
          </motion.p>
          <motion.div {...enter(0.18)} className="mt-8 flex flex-wrap items-center gap-5">
            {primary}
            {secondary}
          </motion.div>
        </div>
        <motion.div {...enter(0.1)} className="overflow-hidden rounded-card">
          {asset}
        </motion.div>
      </div>
    </section>
  );
}
