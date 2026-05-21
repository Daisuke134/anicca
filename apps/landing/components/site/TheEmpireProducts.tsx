'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { translations, type Locale } from '@/lib/i18n';

interface ProductCard {
  key: string;
  href: string;
  symbol: string;
  external?: boolean;
}

function buildLayout(locale: Locale): ProductCard[] {
  const booksHref = locale === 'ja' ? '/achan' : '/monk';
  const letterHref = locale === 'ja' ? '/tegami' : '/letter';
  // Roman-numeral / glyph "stamp" symbols instead of childish emoji.
  return [
    { key: 'affirmationApp', href: '/affirmation-app', symbol: 'i.' },
    { key: 'letter', href: letterHref, symbol: 'ii.' },
    { key: 'music', href: 'https://open.spotify.com/intl-ja/artist/45zyu1wS5ZxLGJvb1EV5PT', symbol: 'iii.', external: true },
    { key: 'comedy', href: '/comedy', symbol: 'iv.' },
    { key: 'tomb', href: '/cemetery', symbol: 'v.' },
    { key: 'fashion', href: '/fashion', symbol: 'vi.' },
    { key: 'cafe', href: '/cafe', symbol: 'vii.' },
    { key: 'retreats', href: '/retreat', symbol: 'viii.' },
    { key: 'donation', href: '/donation', symbol: 'ix.' },
    { key: 'socials', href: '/socials', symbol: 'x.' },
    { key: 'webapps', href: '/factory', symbol: 'xi.' },
    { key: 'books', href: booksHref, symbol: 'xii.' },
    { key: 'politics', href: '/politics', symbol: 'xiii.' },
    { key: 'research', href: '/research', symbol: 'xiv.' },
    { key: 'articles', href: '/blog', symbol: 'xv.' },
  ];
}

export default function TheEmpireProducts({ locale }: { locale: Locale }) {
  const t = translations[locale].empireProducts;
  const en = locale === 'en';
  const layout = buildLayout(locale);
  const [byProduct, setByProduct] = useState<Record<string, number> | null>(null);
  const [socialsViews, setSocialsViews] = useState<number | null>(null);

  useEffect(() => {
    fetch('/dashboard.json')
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        setByProduct(d.mrr.by_product);
        if (d.socials?.weekly_views !== undefined) setSocialsViews(d.socials.weekly_views);
      })
      .catch(() => {});
  }, []);

  const productMap: Record<string, number> = byProduct ?? {};

  function valueFor(key: string): string {
    if (key === 'socials') {
      if (socialsViews === null) return '—';
      const tr = t as { viewsLabel?: string };
      return `${socialsViews.toLocaleString()} ${tr.viewsLabel ?? 'views/wk'}`;
    }
    const map: Record<string, string[]> = {
      affirmationApp: ['anicca-ios-rc', 'anicca-app', 'anicca-ios'],
      letter: ['letter'], music: ['music'], comedy: ['comedy'], tomb: ['tomb'],
      fashion: ['fashion'], cafe: ['cafe'], retreats: ['retreat-donation', 'retreat-subsidy'],
      donation: ['donation'],
      webapps: ['webapps', 'factory'], books: ['books'], politics: ['politics'], research: ['research'],
      articles: ['articles', 'substack', 'x-articles', 'newsletter'],
    };
    const cats = map[key] || [];
    let v = 0;
    for (const c of cats) v += productMap[c] || 0;
    if (!byProduct) return '—';
    if (v === 0) return en ? '—' : '—';
    return `$${Math.round(v).toLocaleString()}`;
  }

  return (
    <section id="products" className="relative bg-cream px-5 py-20">
      <div className="mx-auto max-w-6xl">
        <div className="grid grid-cols-12 gap-x-6 gap-y-8">
          <div className="col-span-12 md:col-span-3">
            <p className="font-mono-ui text-[10px] uppercase tracking-[0.28em] text-mist">
              II.b {en ? 'Products' : 'プロダクト'}
            </p>
            <h2 className="mt-3 font-display text-[34px] leading-tight text-ink sm:text-[42px]">
              {en ? (
                <>Where the <em className="text-mist">money</em> comes from.</>
              ) : (
                <>お金が <em className="text-mist">どこから</em> 来ているか。</>
              )}
            </h2>
            <p className="mt-4 max-w-xs text-[15px] leading-relaxed text-mist">
              {en
                ? 'Each line is its own Anicca instance. Tap any to see what it is and how it earns.'
                : '各行はそれぞれが独立した アニッチャ のインスタンス。タップで詳細。'}
            </p>
          </div>

          <div className="col-span-12 md:col-span-9">
            <ol className="divide-y divide-bone border-y border-bone">
              {layout.map((p) => {
                const meta = (t.products as Record<string, { name: string; tagline: string }>)[p.key];
                const inner = (
                  <div className="group grid grid-cols-12 items-baseline gap-x-3 px-1 py-4 transition-colors hover:bg-bone/50">
                    <span className="col-span-1 font-mono-ui text-[11px] uppercase tracking-[0.18em] text-mist">
                      {p.symbol}
                    </span>
                    <span className="col-span-7 font-display text-[20px] text-ink sm:text-[22px]">
                      {meta?.name ?? p.key}
                    </span>
                    <span className="col-span-12 -mt-1 ml-[8.33%] text-[13px] text-mist sm:col-span-7 sm:col-start-2 sm:ml-0 sm:mt-0 sm:hidden">
                      {meta?.tagline}
                    </span>
                    <span className="hidden sm:col-span-3 sm:col-start-9 sm:block text-right font-mono-ui text-[14px] tabular-nums text-ink">
                      {valueFor(p.key)}
                    </span>
                    <span className="col-span-1 hidden text-right text-mist transition-transform group-hover:translate-x-1 sm:block">→</span>
                    <span className="col-span-12 sm:col-span-7 sm:col-start-2 mt-1 text-[13px] text-mist sm:block hidden">
                      {meta?.tagline}
                    </span>
                  </div>
                );
                return p.external ? (
                  <li key={p.key}>
                    <a href={p.href} target="_blank" rel="noopener noreferrer">{inner}</a>
                  </li>
                ) : (
                  <li key={p.key}>
                    <Link href={p.href}>{inner}</Link>
                  </li>
                );
              })}
            </ol>
          </div>
        </div>
      </div>
    </section>
  );
}
