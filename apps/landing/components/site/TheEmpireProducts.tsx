'use client';

// TODO(§11.F-followup): migrate hardcoded inline EN/JA strings into translations.empireProducts.*
// during the i18n consolidation sweep. Inline ternaries kept here to avoid
// touching i18n.ts cross-section during the per-section redesign.

import { useEffect, useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { translations, type Locale } from '@/lib/i18n';
import { Section, Reveal } from '@/components/site/taste';

interface ProductCard {
  key: string;
  href: string;
  symbol: string;
  external?: boolean;
}

// §4.7 BENTO BG DIVERSITY: which cells (0-indexed) get a real visual.
// 0 = full real image, 3 = gradient, 9 = subtle dot pattern.
const BG_VARIANTS: Record<number, 'image' | 'gradient' | 'pattern'> = {
  0: 'image',
  3: 'gradient',
  9: 'pattern',
};

function buildLayout(locale: Locale): ProductCard[] {
  const booksHref = locale === 'ja' ? '/achan' : '/monk';
  const letterHref = locale === 'ja' ? '/tegami' : '/letter';
  // Roman-numeral / glyph "stamp" symbols instead of childish emoji.
  return [
    { key: 'affirmationApp', href: '/affirmation-app', symbol: 'i.' },
    { key: 'alarm', href: '/alarm', symbol: 'ii.' },
    { key: 'letter', href: letterHref, symbol: 'iii.' },
    { key: 'music', href: 'https://open.spotify.com/intl-ja/artist/45zyu1wS5ZxLGJvb1EV5PT', symbol: 'iv.', external: true },
    { key: 'comedy', href: '/comedy', symbol: 'v.' },
    { key: 'tomb', href: '/cemetery', symbol: 'vi.' },
    { key: 'fashion', href: '/fashion', symbol: 'vii.' },
    { key: 'cafe', href: '/cafe', symbol: 'viii.' },
    { key: 'retreats', href: '/retreat', symbol: 'ix.' },
    { key: 'donation', href: '/donation', symbol: 'x.' },
    { key: 'socials', href: '/socials', symbol: 'xi.' },
    { key: 'webapps', href: '/factory', symbol: 'xii.' },
    { key: 'books', href: booksHref, symbol: 'xiii.' },
    { key: 'politics', href: '/politics', symbol: 'xiv.' },
    { key: 'research', href: '/research', symbol: 'xv.' },
    { key: 'articles', href: '/blog', symbol: 'xvi.' },
  ];
}

// §4.7: bento cell container styles per variant
function cellBgClass(variant: 'image' | 'gradient' | 'pattern' | undefined): string {
  if (variant === 'gradient') {
    return 'bg-gradient-to-br from-[hsl(var(--background-alt,var(--muted)))] to-[hsl(var(--background))]';
  }
  if (variant === 'pattern') {
    // Subtle dot pattern via radial-gradient (pure CSS, no hand-rolled SVG)
    return 'bg-[hsl(var(--card))] [background-image:radial-gradient(hsl(var(--border))_1px,transparent_1px)] [background-size:12px_12px]';
  }
  // default card bg (image cells handled inline with <Image>)
  return 'bg-[hsl(var(--card))]';
}

export default function TheEmpireProducts({ locale }: { locale: Locale }) {
  const t = translations[locale].empireProducts;
  const en = locale === 'en';
  const layout = buildLayout(locale);
  const [byProduct, setByProduct] = useState<Record<string, number> | null>(null);
  const [socialsViews, setSocialsViews] = useState<number | null>(null);

  // §11.F: data source /dashboard.json preserved; AbortController pattern (§A4)
  useEffect(() => {
    const ctrl = new AbortController();
    fetch('/dashboard.json', { signal: ctrl.signal })
      .then((r) => {
        if (!r.ok) throw new Error('failed');
        return r.json();
      })
      .then((d) => {
        if (!d) return;
        setByProduct(d.mrr.by_product);
        if (d.socials?.weekly_views !== undefined) setSocialsViews(d.socials.weekly_views);
      })
      .catch((e: unknown) => {
        if (e instanceof Error && e.name !== 'AbortError') {
          if (typeof window !== 'undefined') console.warn('[TheEmpireProducts] dashboard fetch failed:', e.message);
        }
      });
    return () => ctrl.abort();
  }, []);

  const productMap: Record<string, number> = byProduct ?? {};

  function valueFor(key: string): string {
    if (key === 'socials') {
      if (socialsViews === null) return '--';
      const tr = t as { viewsLabel?: string };
      return `${socialsViews.toLocaleString('en-US')} ${tr.viewsLabel ?? 'views/wk'}`;
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
    if (!byProduct) return '--';
    if (v === 0) return '--';
    return `$${Math.round(v).toLocaleString('en-US')}`;
  }

  return (
    <Section id="products" className="bg-[hsl(var(--background))]">
      {/* Section header */}
      <Reveal>
        <div className="mb-12 grid grid-cols-1 gap-6 md:grid-cols-[1fr_2fr]">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
              II.b {en ? 'Products' : 'プロダクト'}
            </p>
            <h2 className="mt-3 font-display text-[34px] leading-tight text-foreground sm:text-[42px]">
              {en ? (
                <>Where the <em className="text-muted-foreground">money</em> comes from.</>
              ) : (
                <>お金が <em className="text-muted-foreground">どこから</em> 来ているか。</>
              )}
            </h2>
          </div>
          <div className="flex items-end">
            <p className="max-w-md text-[15px] leading-relaxed text-muted-foreground">
              {en
                ? 'Each cell is its own Anicca instance. Tap any to see what it is and how it earns.'
                : '各セルはそれぞれが独立した アニッチャ のインスタンス。タップで詳細。'}
            </p>
          </div>
        </div>
      </Reveal>

      {/* §4.7 BENTO GRID: cell count = items.length (15 cells, 0 empty) */}
      <Reveal delay={0.08}>
        {/* Responsive grid: 1 col mobile / 3 col sm / 5 col xl — 15 items fills each breakpoint cleanly (5×3, 5×3, 3×5). */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 xl:grid-cols-5">
          {layout.map((p, idx) => {
            const meta = (t.products as Record<string, { name: string; tagline: string }>)[p.key];
            const variant = BG_VARIANTS[idx];
            const value = valueFor(p.key);

            const cellContent = (
              <div
                className={[
                  'group relative overflow-hidden rounded-card p-5 transition-transform hover:-translate-y-[2px]',
                  'border border-border',
                  // §4.7 bg diversity: image cells get transparent bg (Image fills), others get variant bg
                  variant === 'image'
                    ? 'bg-[hsl(var(--card))]'
                    : cellBgClass(variant),
                  // Taller feature cell for image variant
                  variant === 'image' ? 'min-h-[200px]' : 'min-h-[140px]',
                ].join(' ')}
              >
                {/* §4.7 real image for image-variant cells (§4.8 no div fake UI) */}
                {variant === 'image' && (
                  <Image
                    src="/anicca-app-icon.png"
                    alt=""
                    fill
                    className="object-cover opacity-20"
                    unoptimized
                  />
                )}

                {/* Cell content overlay */}
                <div className="relative z-10 flex h-full flex-col justify-between gap-4">
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                      {p.symbol}
                    </span>
                    <span className="text-muted-foreground transition-transform group-hover:translate-x-[2px]">
                      &#x2192;
                    </span>
                  </div>

                  <div>
                    <p className="font-display text-[18px] leading-tight text-foreground sm:text-[20px]">
                      {meta?.name ?? p.key}
                    </p>
                    {meta?.tagline && (
                      <p className="mt-1 line-clamp-2 text-[12px] leading-snug text-muted-foreground">
                        {meta.tagline}
                      </p>
                    )}
                  </div>

                  {/* MRR / metric value */}
                  <p className="font-mono tabular-nums text-[13px] text-foreground">
                    {value}
                  </p>
                </div>
              </div>
            );

            return p.external ? (
              <a key={p.key} href={p.href} target="_blank" rel="noopener noreferrer">
                {cellContent}
              </a>
            ) : (
              <Link key={p.key} href={p.href}>
                {cellContent}
              </Link>
            );
          })}
        </div>
      </Reveal>
    </Section>
  );
}
