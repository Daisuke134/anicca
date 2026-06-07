'use client';
import { motion, useReducedMotion } from 'framer-motion';
import React from 'react';

type ManifestoHeroProps = {
  headline: React.ReactNode;  // ≤2行, 大型タイポ
  subtext?: string;           // ≤20語
  cta?: React.ReactNode;      // 単一 CTA
};

// §4.3 override: editorial / manifesto は中央 hero 可（message itself is the design）。
export function ManifestoHero({ headline, subtext, cta }: ManifestoHeroProps) {
  const reduce = useReducedMotion();
  const enter = (delay: number) => ({
    initial: reduce ? false : { opacity: 0, y: 24 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.7, delay, ease: [0.16, 1, 0.3, 1] as const },
  });
  return (
    <section className="w-full px-4 pt-24 pb-16">
      <div className="mx-auto flex max-w-[60rem] flex-col items-start">
        <motion.h1 {...enter(0)} className="font-display text-4xl font-semibold leading-[1.05] tracking-tight text-balance text-[hsl(var(--text-primary))] md:text-6xl">
          {headline}
        </motion.h1>
        {subtext ? (
          <motion.p {...enter(0.1)} className="mt-6 max-w-[50ch] text-lg leading-relaxed text-[hsl(var(--text-secondary))]">
            {subtext}
          </motion.p>
        ) : null}
        {cta ? <motion.div {...enter(0.18)} className="mt-8">{cta}</motion.div> : null}
      </div>
    </section>
  );
}
