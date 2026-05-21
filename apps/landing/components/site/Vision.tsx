import { translations, type Locale } from '@/lib/i18n';

interface VisionProps {
  locale: Locale;
}

export default function Vision({ locale }: VisionProps) {
  const t = translations[locale].vision;

  return (
    <section
      id="vision"
      className="bg-background-alt px-6 py-20"
    >
      <h2 className="text-3xl font-bold text-center text-foreground text-balance md:text-5xl">
        {t.title}
      </h2>
      <p className="mx-auto mt-8 max-w-2xl text-lg text-center text-muted-foreground text-pretty">
        {t.story}
      </p>
      <div className="mx-auto mt-4 max-w-2xl text-lg text-center text-muted-foreground text-pretty">
        {t.questions.map((question, index) => (
          <p key={index}>{question}</p>
        ))}
      </div>
      <p className="mt-8 text-xl font-semibold text-center text-foreground">
        {t.closer}
      </p>
    </section>
  );
}
