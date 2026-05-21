import { translations, type Locale } from '@/lib/i18n';

interface TheSwarmProps {
  locale: Locale;
}

export default function TheSwarm({ locale }: TheSwarmProps) {
  const t = translations[locale].swarm;

  return (
    <section id="swarm" className="bg-background px-6 py-20">
      <h2 className="text-3xl font-bold text-center text-foreground text-balance md:text-5xl">
        {t.title}
      </h2>
      <p className="mx-auto mt-8 max-w-2xl text-lg text-center text-muted-foreground text-pretty">
        {t.body}
      </p>
      <div className="mx-auto mt-12 grid max-w-3xl gap-6 md:grid-cols-2">
        {t.points.map((point) => (
          <div
            key={point.title}
            className="rounded-2xl border border-border bg-card p-6"
          >
            <h3 className="text-lg font-bold text-foreground">{point.title}</h3>
            <p className="mt-2 text-sm text-muted-foreground text-pretty">
              {point.desc}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
