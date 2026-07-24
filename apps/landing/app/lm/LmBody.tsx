'use client';

import { useEffect, useState } from 'react';
import { Reveal } from '@/components/site/taste';
import { useLaunchLocale } from '@/lib/launchLocale';
import { launchStrings } from '@/lib/launchStrings';
import LmClient from './LmClient';

// /lm — v1 GATE (Dais 2026-06-25/26): standalone web onboarding stays "coming soon" (we ship on Telegram
// first), BUT the Telegram funnel /lm?tg=<chat_id> MUST render the real onboarding (LmClient) — name + phone
// are collected in the bot, but the Google Calendar OAuth (Composio) and Stripe payment can only happen on the
// web, and the Telegram "Connect Calendar"/"Subscribe" buttons open exactly this page with ?tg=. Without this,
// a Telegram user taps Connect Calendar and lands on the coming-soon gate = onboarding dead at the calendar step.
// Standalone visitors (no ?tg=) keep the coming-soon gate. At v1.5 (S6) the gate is removed entirely.
const TG_DEEPLINK = 'https://t.me/LifeManagerBotbot?start=lp';

export default function LmBody() {
  const { locale } = useLaunchLocale();
  const t = launchStrings[locale].lm;
  // undefined = not yet read (pre-mount/SSR) → show the gate; a digit string = Telegram funnel → LmClient;
  // null = standalone web → gate.
  const [tg, setTg] = useState<string | null | undefined>(undefined);
  useEffect(() => {
    const p = new URLSearchParams(window.location.search).get('tg');
    setTg(p && /^\d{1,20}$/.test(p) ? p : null);
  }, []);

  // Pre-mount (SSR + first client paint, before the effect reads the URL): show a neutral loader, NOT the
  // gate — a Telegram visitor (?tg=) must never flash "coming soon" while we resolve the param.
  if (tg === undefined) {
    return (
      <section className="w-full px-4 pt-28 pb-24 text-center">
        <div
          className="mx-auto h-6 w-6 animate-spin rounded-full border-2 border-[hsl(var(--gold))] border-t-transparent"
          role="status"
          aria-label="Loading"
        />
      </section>
    );
  }
  if (tg) return <LmClient />;

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
