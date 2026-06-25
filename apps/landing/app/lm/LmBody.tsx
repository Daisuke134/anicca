'use client';

import { Reveal } from '@/components/site/taste';
import { useLaunchLocale } from '@/lib/launchLocale';
import { launchStrings } from '@/lib/launchStrings';
import LmClient from './LmClient';

// /lm body — localized EN/JA. COMPACT above-the-fold layout (Dais 2026-06-25: the onboarding buttons must
// be reachable WITHOUT scrolling). A tiny header (eyebrow + one-line title) then the onboarding island
// immediately, in a centered max-w-xl card. The onboarding flow logic (LmClient) is UNCHANGED.

export default function LmBody() {
  const { locale } = useLaunchLocale();
  const t = launchStrings[locale].lm;

  return (
    <section className="w-full px-4 pt-8 pb-12 md:pt-10">
      <div className="mx-auto max-w-xl">
        <Reveal>
          <div className="text-center">
            <p className="text-xs uppercase tracking-[0.18em] text-[hsl(var(--gold))]">{t.eyebrow}</p>
            <h1 className="mt-2 font-display text-2xl md:text-3xl font-bold text-[hsl(var(--text-primary))]">
              {t.heroTitle}
            </h1>
          </div>
          <div className="mt-6">
            <LmClient />
          </div>
        </Reveal>
      </div>
    </section>
  );
}
