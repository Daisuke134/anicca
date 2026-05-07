import { translations, type Locale } from '@/lib/i18n';

interface ManifestoProps {
  locale: Locale;
}

export default function Manifesto({ locale }: ManifestoProps) {
  const t = translations[locale].manifesto;

  return (
    <section className="section bg-background">
      <div className="container-content">
        <div className="grid grid-cols-1 gap-x-16 gap-y-10 md:grid-cols-12">
          <div className="md:col-span-4">
            <p className="eyebrow">{t.eyebrow}</p>
            <h2 className="display mt-6 text-4xl font-normal leading-[1.05] tracking-tight text-foreground md:text-5xl">
              {t.title}
            </h2>
          </div>

          <div className="md:col-span-7 md:col-start-6">
            <div className="space-y-6 text-lg leading-relaxed text-foreground/90 md:text-[1.18rem]">
              {t.paragraphs.map((p, i) => (
                <p key={i}>{p}</p>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
