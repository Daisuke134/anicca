import { translations, type Locale } from '@/lib/i18n';

interface RoadmapProps {
  locale: Locale;
}

export default function Roadmap({ locale }: RoadmapProps) {
  const t = translations[locale].roadmap;

  return (
    <section className="bg-background-alt px-6 py-20">
      <h2 className="text-3xl font-bold text-center text-foreground">
        {t.title}
      </h2>

      {/* Timeline */}
      <div className="mt-12 flex items-center justify-center gap-4">
        {t.timeline.map((point, index) => (
          <div key={point} className="flex items-center">
            <div className="size-4 rounded-full bg-foreground" />
            {index < t.timeline.length - 1 && (
              <div className="h-0.5 w-16 bg-foreground" />
            )}
          </div>
        ))}
      </div>
      <div className="mt-2 flex justify-center gap-8 text-sm text-muted-foreground">
        {t.timeline.map((point) => (
          <span key={point}>{point}</span>
        ))}
      </div>

      {/* Phases */}
      <div className="mx-auto mt-12 max-w-2xl space-y-8">
        {t.phases.map((phase) => (
          <div key={phase.title}>
            <h3 className="font-bold text-foreground">{phase.title}</h3>
            <p className="text-muted-foreground">{phase.desc}</p>
          </div>
        ))}
      </div>

      <p className="mx-auto mt-12 max-w-2xl text-lg font-semibold text-center text-foreground">
        {t.final}
      </p>
    </section>
  );
}
