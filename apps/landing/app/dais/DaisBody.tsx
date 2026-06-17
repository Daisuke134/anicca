'use client';

import Link from 'next/link';
import { translations } from '@/lib/i18n';
import { Section, Reveal } from '@/components/site/taste';
import { useLaunchLocale } from '@/lib/launchLocale';

// /dais — Dais's products hub (spec31 §C / spec30 §13). Lists ALL
// i18n.empireProducts.products EXCEPT `alarm` (anicca does that itself now).
// JP brand = アニッチャ. Localized EN/JA via LaunchLocale (inside <LaunchFrame>).

// product key → route (mirrors TheEmpireProducts.buildLayout, minus `alarm`).
function productRoute(key: string, locale: 'en' | 'ja'): { href: string; external?: boolean } {
  const booksHref = locale === 'ja' ? '/achan' : '/monk';
  const letterHref = locale === 'ja' ? '/tegami' : '/letter';
  const map: Record<string, { href: string; external?: boolean }> = {
    affirmationApp: { href: '/affirmation-app' },
    letter: { href: letterHref },
    music: { href: 'https://open.spotify.com/intl-ja/artist/45zyu1wS5ZxLGJvb1EV5PT', external: true },
    comedy: { href: '/comedy' },
    tomb: { href: '/cemetery' },
    fashion: { href: '/fashion' },
    cafe: { href: '/cafe' },
    retreats: { href: '/retreat' },
    donation: { href: '/donation' },
    socials: { href: '/socials' },
    webapps: { href: '/factory' },
    books: { href: booksHref },
    politics: { href: '/politics' },
    research: { href: '/research' },
    articles: { href: '/blog' },
  };
  return map[key] ?? { href: '#' };
}

export default function DaisBody() {
  const { locale } = useLaunchLocale();
  const en = locale === 'en';
  const products = translations[locale].empireProducts.products as Record<
    string,
    { name: string; tagline: string }
  >;
  // Exclude `alarm` (spec31 §C). Preserve i18n key order otherwise.
  const keys = Object.keys(products).filter((k) => k !== 'alarm');

  return (
    <Section id="dais-products" className="pt-24">
      <Reveal>
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-[hsl(var(--gold))]">
          {en ? "Dais's products" : 'Dais のプロダクト'}
        </p>
        <h1 className="mt-3 font-display text-[34px] leading-tight text-[hsl(var(--text-primary))] sm:text-[46px]">
          {en ? 'Where the money comes from.' : 'お金が、どこから来ているか。'}
        </h1>
        <p className="mt-4 max-w-[60ch] text-[15px] leading-relaxed text-[hsl(var(--text-secondary))]">
          {en
            ? 'Every revenue product Dais ships — the apps, the web tools, the content. Each one is its own Anicca instance. Tap any card for what it is and how it earns.'
            : 'Dais が出している稼ぎのプロダクトすべて — アプリ、Web ツール、コンテンツ。どれも独立した一個体のアニッチャ。タップで、何で・どう稼いでいるかが見える。'}
        </p>
      </Reveal>

      <Reveal delay={0.08}>
        <div className="mt-12 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {keys.map((key) => {
            const meta = products[key];
            const route = productRoute(key, locale);
            const card = (
              <div className="group flex h-full min-h-[120px] flex-col justify-between gap-3 rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-5 transition-transform hover:-translate-y-[2px]">
                <div className="flex items-start justify-between gap-2">
                  <p className="font-display text-[18px] leading-tight text-[hsl(var(--text-primary))] sm:text-[20px]">
                    {meta.name}
                  </p>
                  <span className="text-[hsl(var(--text-secondary))] transition-transform group-hover:translate-x-[2px]">
                    &#x2192;
                  </span>
                </div>
                <p className="text-[13px] leading-snug text-[hsl(var(--text-secondary))]">
                  {meta.tagline}
                </p>
              </div>
            );
            return route.external ? (
              <a key={key} href={route.href} target="_blank" rel="noopener noreferrer">
                {card}
              </a>
            ) : (
              <Link key={key} href={route.href}>
                {card}
              </Link>
            );
          })}
        </div>
      </Reveal>
    </Section>
  );
}
