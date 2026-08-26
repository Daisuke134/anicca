'use client';

import { Reveal } from '@/components/site/taste';
import { useLaunchLocale } from '@/lib/launchLocale';
import { launchStrings } from '@/lib/launchStrings';

const TG_DEEPLINK = 'https://t.me/LifeManagerBotbot?start=lp';

// The public landing page is a single Telegram handoff. Authenticated onboarding and payment
// continue in the Railway Mini App, so this page never reads query identity or owns user state.
export default function LmBody() {
  const { locale } = useLaunchLocale();
  const t = launchStrings[locale].lm;

  return (
    <section className="w-full px-4 pt-16 pb-20 md:pt-24">
      <div className="mx-auto max-w-md text-center">
        <Reveal>
          <p className="text-xs uppercase tracking-[0.18em] text-[hsl(var(--gold))]">{t.eyebrow}</p>
          <h1 className="mt-3 font-display text-2xl md:text-3xl font-bold text-[hsl(var(--text-primary))]">
            {t.soonTitle}
          </h1>
          <p className="mt-4 text-sm leading-relaxed text-[hsl(var(--text-secondary))]">{t.soonBody}</p>
          <a
            href={TG_DEEPLINK}
            target="_blank"
            rel="noreferrer"
            className="mt-7 inline-flex items-center justify-center rounded-pill bg-[hsl(var(--gold))] px-7 py-3 text-sm font-semibold text-black transition-all hover:brightness-95 active:scale-[0.98]"
          >
            {t.soonCta}
          </a>
        </Reveal>
      </div>
    </section>
  );
}
