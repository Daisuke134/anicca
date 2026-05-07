import Link from 'next/link';
import { translations, type Locale } from '@/lib/i18n';

interface HeroProps {
  locale: Locale;
}

export default function Hero({ locale }: HeroProps) {
  const t = translations[locale].heroV2;

  return (
    <section className="relative overflow-hidden bg-background">
      {/* Decorative hairline grid — extremely subtle, paper feel */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.035]"
        style={{
          backgroundImage:
            'linear-gradient(to right, hsl(var(--foreground)) 1px, transparent 1px), linear-gradient(to bottom, hsl(var(--foreground)) 1px, transparent 1px)',
          backgroundSize: '64px 64px',
        }}
      />

      <div className="container-wide relative flex min-h-[100dvh] flex-col justify-between pb-20 pt-28 md:pt-36">
        {/* Top — eyebrow */}
        <div className="animate-fade-in">
          <p className="eyebrow">{t.eyebrow}</p>
        </div>

        {/* Middle — headline */}
        <div className="my-16 max-w-5xl animate-fade-up [animation-delay:80ms]">
          <h1 className="display text-[14vw] font-normal leading-[0.95] tracking-tightest text-foreground sm:text-7xl md:text-8xl lg:text-[8.5rem]">
            {t.headline}{' '}
            <em className="not-italic">
              <span className="italic">{t.headlineItalic}</span>
            </em>
          </h1>

          <p className="mt-10 max-w-prose text-lg text-secondary md:text-xl">
            {t.subtitle}
          </p>
        </div>

        {/* Bottom — CTAs + meta hairline */}
        <div className="flex flex-col gap-8 animate-fade-up [animation-delay:200ms]">
          <div className="flex flex-col items-start gap-5 sm:flex-row sm:items-center sm:gap-8">
            <Link
              href="/research"
              className="group inline-flex items-center gap-3 border-b border-foreground pb-1.5 font-mono text-xs uppercase tracking-[0.2em] text-foreground transition-colors"
            >
              <span>{t.ctaPrimary}</span>
              <span aria-hidden className="transition-transform group-hover:translate-x-1">→</span>
            </Link>

            <a
              href="https://github.com/Daisuke134/anicca"
              target="_blank"
              rel="noopener noreferrer"
              className="font-mono text-xs uppercase tracking-[0.2em] text-secondary transition-colors hover:text-foreground"
            >
              {t.ctaSecondary} ↗
            </a>
          </div>

          <hr className="hairline" />

          <div className="flex flex-wrap items-center justify-between gap-3 font-mono text-[0.7rem] uppercase tracking-[0.18em] text-muted">
            <span>Tokyo · MIT licensed</span>
            <span>v 0.1 · {new Date().getFullYear()}</span>
          </div>
        </div>
      </div>
    </section>
  );
}
