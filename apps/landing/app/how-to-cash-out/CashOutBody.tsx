'use client';

import { Section } from '@/components/site/taste';
import { useLaunchLocale } from '@/lib/launchLocale';

// /how-to-cash-out body (spec31 §E). Renders the locale-matched pre-built HTML
// (server reads content/how-to-cash-out.{en,ja}.md). Locale from LaunchLocale toggle.

export default function CashOutBody({ htmlEn, htmlJa }: { htmlEn: string; htmlJa: string }) {
  const { locale } = useLaunchLocale();
  const html = locale === 'ja' ? htmlJa : htmlEn;

  return (
    <Section className="pt-24">
      <article
        className="mx-auto max-w-3xl"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </Section>
  );
}
