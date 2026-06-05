'use client';

// TODO(§11.F-followup): migrate hardcoded section labels (eyebrow, link labels) into
// translations.manifestoStrip.* during the i18n consolidation sweep. Inline ternaries
// kept here to avoid touching i18n.ts cross-section during the per-section redesign.

import Link from 'next/link';
import { translations, type Locale } from '@/lib/i18n';
import { Section, Reveal } from '@/components/site/taste';

// §5 MARQUEE MAX-ONE-PER-PAGE: ManifestoStrip is intentionally NON-marquee.
// Fellows.tsx owns the single page-level marquee (fellows names scroll).
// This closing strip uses a static Reveal layout per §9.F (no locale/city/time strip).
// §9.G: em-dash zero - all copy flows through translations.manifestoStrip.* (already
//        patched to hyphens in commit a59a5057).
// §4.11: theme lock, no dark overrides.
// §4.4: shape-lock tokens only (pill/card/input).
// §9.A: no pure black/white values.

export default function ManifestoStrip({ locale }: { locale: Locale }) {
  const t = translations[locale].manifestoStrip;
  const en = locale === 'en';

  return (
    <Section id="manifesto-strip">
      <div className="border-t border-[hsl(var(--border))] pt-16 text-center md:pt-20">
        {/* Eyebrow */}
        <Reveal>
          <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-[hsl(var(--text-secondary))]">
            {/* TODO(§11.F-followup): i18n key for section label */}
            VII. {en ? 'Closing' : '結び'}
          </p>
        </Reveal>

        {/* Body - from translations.manifestoStrip.body (em-dash-free, patched A3) */}
        <Reveal delay={0.1}>
          <p className="mx-auto mt-8 max-w-2xl font-display text-[20px] leading-[1.6] text-[hsl(var(--text-primary))] sm:text-[24px]">
            {t.body}
          </p>
        </Reveal>

        {/* Single CTA - §4.5 one primary intent */}
        <Reveal delay={0.2}>
          <div className="mt-10">
            <Link
              href="/manifesto"
              className="inline-block rounded-pill border border-[hsl(var(--border))] px-6 py-2.5 font-mono text-[11px] uppercase tracking-[0.2em] text-[hsl(var(--text-secondary))] transition-colors hover:border-[hsl(var(--gold))] hover:text-[hsl(var(--gold))]"
            >
              {t.cta}
            </Link>
          </div>
        </Reveal>

        {/* Secondary navigation links */}
        <Reveal delay={0.3}>
          <div className="mt-10 flex flex-wrap items-center justify-center gap-6 font-mono text-[11px] uppercase tracking-[0.2em] text-[hsl(var(--text-secondary))]">
            <Link
              href="/fellows"
              className="border-b border-[hsl(var(--border))] pb-px transition-colors hover:border-[hsl(var(--gold))] hover:text-[hsl(var(--gold))]"
            >
              {/* TODO(§11.F-followup): i18n key */}
              {en ? 'Meet the fellows' : '同類を見る'}
            </Link>
            <Link
              href="/income"
              className="border-b border-[hsl(var(--border))] pb-px transition-colors hover:border-[hsl(var(--gold))] hover:text-[hsl(var(--gold))]"
            >
              {/* TODO(§11.F-followup): i18n key */}
              {en ? 'Get basic income' : 'インカムに応募'}
            </Link>
            <Link
              href="/letter"
              className="border-b border-[hsl(var(--border))] pb-px transition-colors hover:border-[hsl(var(--gold))] hover:text-[hsl(var(--gold))]"
            >
              {/* TODO(§11.F-followup): i18n key */}
              {en ? 'Daily letter' : '毎朝の手紙'}
            </Link>
          </div>
        </Reveal>
      </div>
    </Section>
  );
}
