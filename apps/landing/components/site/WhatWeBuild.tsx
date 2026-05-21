import { translations, type Locale } from '@/lib/i18n';

interface WhatWeBuildProps {
  locale: Locale;
}

export default function WhatWeBuild({ locale }: WhatWeBuildProps) {
  const t = translations[locale].whatWeBuild;

  return (
    <section id="what-we-build" className="bg-background-alt px-6 py-20">
      <h2 className="text-3xl font-bold text-center text-foreground text-balance md:text-5xl">
        {t.title}
      </h2>
      <p className="mx-auto mt-8 max-w-2xl text-lg text-center text-muted-foreground text-pretty">
        {t.intro}
      </p>
      <div className="mx-auto mt-12 grid max-w-5xl gap-4 md:grid-cols-3">
        {t.verticals.map((v) => (
          <div
            key={v.title}
            className="rounded-2xl border border-border bg-background p-6"
          >
            <span className="inline-block rounded-full border border-gold/40 bg-gold/10 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-foreground">
              {v.tag}
            </span>
            <h3 className="mt-4 text-xl font-bold text-foreground">{v.title}</h3>
            <p className="mt-2 text-sm text-muted-foreground text-pretty">
              {v.desc}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
