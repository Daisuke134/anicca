import Link from 'next/link';
import { translations, type Locale } from '@/lib/i18n';

interface PillarsProps {
  locale: Locale;
}

export default function Pillars({ locale }: PillarsProps) {
  const t = translations[locale].pillars;
  if (!t) return null;

  return (
    <section className="section bg-[hsl(var(--background-alt))]">
      <div className="container-content">
        <div className="max-w-3xl">
          <p className="eyebrow">{t.eyebrow}</p>
          <h2 className="display mt-6 text-4xl font-normal leading-[1.05] tracking-tight text-foreground md:text-5xl">
            {t.title}
          </h2>
          <p className="mt-6 text-base text-secondary md:text-lg">{t.subtitle}</p>
        </div>

        <div className="mt-16 grid grid-cols-1 gap-px overflow-hidden rounded-[2px] bg-[hsl(var(--hairline))] md:grid-cols-2">
          {t.items.map((it) => (
            <article
              key={it.number}
              className="group flex flex-col gap-5 bg-[hsl(var(--background-alt))] p-8 md:p-12"
            >
              <div className="flex items-baseline gap-4">
                <span className="font-mono text-sm tracking-[0.15em] text-[hsl(var(--amber))]">
                  {it.number}
                </span>
                <span className="h-px flex-1 bg-[hsl(var(--hairline))]" />
              </div>
              <h3 className="font-serif text-2xl leading-tight tracking-tight text-foreground md:text-3xl">
                {it.title}
              </h3>
              <p className="text-base leading-relaxed text-secondary md:text-[1.05rem]">
                {it.body}
              </p>
            </article>
          ))}
        </div>

        <div className="mt-12 flex justify-end">
          <Link
            href="/politics"
            className="font-mono text-xs uppercase tracking-[0.2em] text-foreground link-quiet"
          >
            {t.cta}
          </Link>
        </div>
      </div>
    </section>
  );
}
