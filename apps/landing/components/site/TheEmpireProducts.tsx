'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { translations, type Locale } from '@/lib/i18n';

interface TheEmpireProductsProps {
  locale: Locale;
}

interface ProductCard {
  key: string;
  href: string;
  emoji: string;
  external?: boolean;
}

const PRODUCT_LAYOUT: ProductCard[] = [
  { key: 'affirmationApp', href: '/affirmation-app', emoji: '🪷' },
  { key: 'letter', href: '/letter', emoji: '✉️' },
  { key: 'music', href: 'https://open.spotify.com', emoji: '🎵', external: true },
  { key: 'comedy', href: '/comedy', emoji: '🎭' },
  { key: 'tomb', href: '/tomb', emoji: '🪦' },
  { key: 'fashion', href: '/fashion', emoji: '👕' },
  { key: 'cafe', href: '/cafe', emoji: '🥭' },
  { key: 'donation', href: '/donation', emoji: '💝' },
  { key: 'webapps', href: '/factory', emoji: '🌐' },
  { key: 'books', href: '#', emoji: '📚' },
  { key: 'retreats', href: '#', emoji: '🏞️' },
];

export default function TheEmpireProducts({ locale }: TheEmpireProductsProps) {
  const t = translations[locale].empireProducts;
  const [byProduct, setByProduct] = useState<Record<string, number> | null>(null);

  useEffect(() => {
    fetch('/dashboard.json')
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setByProduct(d.mrr.by_product))
      .catch(() => {});
  }, []);

  const productMap: Record<string, number> = byProduct ?? {};

  function valueFor(key: string): string {
    const map: Record<string, string[]> = {
      affirmationApp: ['anicca-ios-rc', 'anicca-app', 'anicca-ios'],
      letter: ['letter'],
      music: ['music'],
      comedy: ['comedy'],
      tomb: ['tomb'],
      fashion: ['fashion'],
      cafe: ['cafe'],
      donation: ['donation'],
      webapps: ['webapps', 'factory'],
      books: ['books'],
      retreats: ['retreats'],
    };
    const cats = map[key] || [];
    let v = 0;
    for (const c of cats) v += productMap[c] || 0;
    if (!byProduct) return t.loading;
    if (v === 0) return t.zeroLabel;
    return `$${Math.round(v).toLocaleString()}`;
  }

  return (
    <section className="bg-background px-6 py-20">
      <div className="mx-auto max-w-5xl">
        <h2 className="mb-2 text-center text-3xl font-bold text-foreground md:text-4xl">
          {t.title}
        </h2>
        <p className="mb-12 text-center text-sm text-muted-foreground">
          {t.subtitle}
        </p>

        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {PRODUCT_LAYOUT.map((p) => {
            const card = (
              <div className="flex h-full flex-col rounded-xl border border-border bg-background p-4 transition-colors hover:border-foreground">
                <div className="mb-2 text-3xl">{p.emoji}</div>
                <div className="text-sm font-bold text-foreground">
                  {(t.products as Record<string, { name: string; tagline: string }>)[p.key]?.name || p.key}
                </div>
                <div className="mt-1 text-xs text-muted-foreground">
                  {(t.products as Record<string, { name: string; tagline: string }>)[p.key]?.tagline || ''}
                </div>
                <div className="mt-3 font-mono text-lg font-semibold text-foreground">
                  {valueFor(p.key)}
                </div>
              </div>
            );
            return p.external ? (
              <a key={p.key} href={p.href} target="_blank" rel="noopener noreferrer">
                {card}
              </a>
            ) : (
              <Link key={p.key} href={p.href}>
                {card}
              </Link>
            );
          })}
        </div>
      </div>
    </section>
  );
}
