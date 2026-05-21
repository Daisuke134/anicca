import Image from 'next/image';
import { translations, type Locale } from '@/lib/i18n';

interface HowItWorksProps {
  locale: Locale;
}

const getScreenshots = (locale: Locale) => [
  `/screenshots/${locale}/onboarding.png`,
  `/screenshots/${locale}/notification.png`,
  `/screenshots/${locale}/nudge-card.png`,
];

export default function HowItWorks({ locale }: HowItWorksProps) {
  const t = translations[locale].howItWorks;
  const screenshots = getScreenshots(locale);

  return (
    <section
      id="how-it-works"
      className="bg-background px-6 py-20"
    >
      <h2 className="text-3xl font-bold text-center text-foreground">
        {t.title}
      </h2>

      <div className="mx-auto mt-12 grid max-w-4xl gap-8 md:grid-cols-3">
        {t.steps.map((step, index) => (
          <div key={step.title} className="text-center">
            <div className="relative mx-auto h-96 w-48">
              <Image
                src={screenshots[index]}
                alt={step.title}
                fill
                className="object-contain"
              />
            </div>
            <h3 className="mt-4 font-bold text-foreground">{step.title}</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              {step.desc}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
