import { translations, type Locale } from '@/lib/i18n';

interface PainPointProps {
  locale: Locale;
}

export default function PainPoint({ locale }: PainPointProps) {
  const t = translations[locale].painPoint;

  return (
    <section className="bg-background px-6 py-20">
      <blockquote className="text-2xl font-bold text-center text-foreground md:text-4xl italic">
        {t.quote}
      </blockquote>
      <p className="mt-2 text-sm text-center text-muted-foreground">
        {t.quoteTranslation}
      </p>
      <p className="mx-auto mt-8 max-w-2xl text-lg text-center text-muted-foreground text-pretty">
        {t.body}
      </p>
    </section>
  );
}
