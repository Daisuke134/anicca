import { translations, type Locale } from '@/lib/i18n';
import TwoCtaButtons from './TwoCtaButtons';

interface HeroProps {
  locale: Locale;
}

export default function Hero({ locale }: HeroProps) {
  const t = translations[locale].hero;

  return (
    <section className="flex min-h-dvh flex-col items-center justify-center bg-background px-6 py-20">
      <h1 className="text-balance text-center text-6xl font-bold text-foreground md:text-8xl">
        {t.headline}
      </h1>
      <p className="mx-auto mt-6 max-w-2xl text-balance text-center text-base text-muted-foreground md:text-lg">
        {t.subtitle}
      </p>
      <TwoCtaButtons locale={locale} />
    </section>
  );
}
