'use client';
import { motion, useReducedMotion } from 'framer-motion';
import React from 'react';

type RevealProps = {
  children: React.ReactNode;
  delay?: number;
  className?: string;
};

// §5.C scroll-reveal stagger. §6.B reduced-motion safe.
// Content is rendered VISIBLE by default (opacity 1) so it never disappears
// if IntersectionObserver does not fire (SSR, fullPage screenshot, prerender).
// The y-translate stagger only runs when the element scrolls into view.
export function Reveal({ children, delay = 0, className }: RevealProps) {
  const reduce = useReducedMotion();
  if (reduce) {
    return <div className={className}>{children}</div>;
  }
  return (
    <motion.div
      className={className}
      initial={{ y: 12 }}
      whileInView={{ y: 0 }}
      viewport={{ once: true, amount: 0 }}
      transition={{ duration: 0.6, delay, ease: [0.16, 1, 0.3, 1] }}
    >
      {children}
    </motion.div>
  );
}
