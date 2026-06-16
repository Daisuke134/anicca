'use client';

import { Section, Reveal } from '@/components/site/taste';
import { useLaunchLocale } from '@/lib/launchLocale';
import { launchStrings } from '@/lib/launchStrings';
import LmClient from './LmClient';

// /lm body — localized EN/JA hero + the onboarding client island. Renders inside
// <LaunchFrame> (locale context + nav + footer). The onboarding flow logic lives in
// LmClient and is UNCHANGED; this just localizes the marketing hero around it.

export default function LmBody() {
  const { locale } = useLaunchLocale();
  const t = launchStrings[locale].lm;

  return (
    <>
      <Section>
        <Reveal>
          <div className="mx-auto max-w-xl text-center">
            <p className="text-xs uppercase tracking-[0.18em] text-[hsl(var(--gold))]">{t.eyebrow}</p>
            <h1 className="mt-3 font-display text-3xl md:text-4xl font-bold text-[hsl(var(--text-primary))]">
              {t.heroTitle}
            </h1>
            <p className="mt-3 text-base text-[hsl(var(--text-secondary))]">{t.heroBody}</p>
          </div>
        </Reveal>
      </Section>

      <Section className="pt-0">
        <Reveal>
          <LmClient />
        </Reveal>
      </Section>
    </>
  );
}
