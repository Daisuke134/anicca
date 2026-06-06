'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { translations, type Locale } from '@/lib/i18n';

interface RecentWritingProps {
  locale: Locale;
}

interface WritingItem {
  date: string;
  kind: string;
  title: string;
  href: string;
  external?: boolean;
}

interface DashboardWithWriting {
  recent_writing?: WritingItem[];
}

export default function RecentWriting({ locale }: RecentWritingProps) {
  const t = translations[locale].recentWriting;
  if (!t) return null;
  const [items, setItems] = useState<WritingItem[]>(
    t.fallback as unknown as WritingItem[],
  );

  useEffect(() => {
    fetch('/dashboard.json')
      .then((r) => (r.ok ? r.json() : null))
      .then((d: DashboardWithWriting | null) => {
        if (d?.recent_writing && Array.isArray(d.recent_writing) && d.recent_writing.length > 0) {
          setItems(d.recent_writing.slice(0, 3));
        }
      })
      .catch(() => {});
  }, []);

  return (
    <section className="section bg-background">
      <div className="container-content">
        <div className="grid grid-cols-1 gap-x-16 gap-y-10 md:grid-cols-12">
          <div className="md:col-span-4">
            <p className="eyebrow">{t.eyebrow}</p>
            <h2 className="display mt-6 text-4xl font-normal leading-[1.05] tracking-tight text-foreground md:text-5xl">
              {t.title}
            </h2>
            <p className="mt-6 text-base text-secondary md:text-lg">{t.subtitle}</p>
          </div>

          <div className="md:col-span-8">
            <ul>
              {items.map((it, idx) => {
                const Comp: React.ElementType = it.external ? 'a' : Link;
                const linkProps = it.external
                  ? { href: it.href, target: '_blank', rel: 'noopener noreferrer' }
                  : { href: it.href };
                return (
                  <li
                    key={`${it.href}-${idx}`}
                    className="border-t border-[hsl(var(--hairline))] last:border-b"
                  >
                    <Comp
                      {...linkProps}
                      className="group flex items-baseline gap-6 py-7 transition-colors"
                    >
                      <time className="hidden w-24 shrink-0 font-mono text-[0.72rem] uppercase tracking-[0.18em] text-muted sm:block">
                        {it.date}
                      </time>
                      <span className="hidden w-16 shrink-0 font-mono text-[0.72rem] uppercase tracking-[0.18em] text-[hsl(var(--amber))] sm:inline">
                        {it.kind}
                      </span>
                      <span className="flex-1 font-serif text-xl leading-snug text-foreground md:text-2xl">
                        {it.title}
                      </span>
                      <span
                        aria-hidden
                        className="ml-2 font-mono text-sm text-secondary transition-transform group-hover:translate-x-1"
                      >
                        →
                      </span>
                    </Comp>
                  </li>
                );
              })}
            </ul>

            <a
              href={t.socialPost.href}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-12 block rounded-[2px] border border-[hsl(var(--hairline))] p-8 transition-colors hover:border-foreground"
            >
              <p className="eyebrow">{t.socialPost.eyebrow}</p>
              <p className="mt-4 font-serif text-2xl leading-snug text-foreground">
                “{t.socialPost.body}”
              </p>
              <p className="mt-4 font-mono text-xs uppercase tracking-[0.18em] text-secondary">
                {t.socialPost.cta} ↗
              </p>
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
