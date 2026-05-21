import { translations, type Locale } from '@/lib/i18n';

interface PhilosophyProps {
  locale: Locale;
}

export default function Philosophy({ locale }: PhilosophyProps) {
  const t = translations[locale].philosophy;

  return (
    <section className="bg-background px-6 py-20">
      <h2 className="text-3xl font-bold text-center text-foreground">
        {t.title}
      </h2>
      <div className="mx-auto mt-8 max-w-xl border-2 border-gold p-8 text-center">
        <p className="text-2xl font-bold text-foreground">
          {t.statement}
        </p>
      </div>
      <div className="mx-auto mt-8 max-w-2xl text-center">
        <p className="text-muted-foreground text-pretty">
          {t.contrast}
        </p>
        <p className="mt-8 text-muted-foreground">
          {t.agi}
        </p>
        <p className="mt-4 text-lg font-bold text-foreground">
          {t.closer}
        </p>
      </div>
    </section>
  );
}
