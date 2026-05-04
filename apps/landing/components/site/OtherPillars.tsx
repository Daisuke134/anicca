import Link from 'next/link';
import { translations, type Locale } from '@/lib/i18n';

interface OtherPillarsProps {
  locale: Locale;
}

const PILLARS = [
  { key: 'politics', href: '/politics', emoji: '🏛️' },
  { key: 'research', href: '/research', emoji: '🔬' },
  { key: 'newsletter', href: '/letter', emoji: '✉️' },
  { key: 'tomb', href: '/tomb', emoji: '🪦' },
  { key: 'comedy', href: '/comedy', emoji: '🎭' },
  { key: 'donation', href: '/donation', emoji: '💝' },
  { key: 'webapps', href: '/factory', emoji: '🌐' },
  { key: 'apps', href: '/affirmation-app', emoji: '📱' },
];

export default function OtherPillars({ locale }: OtherPillarsProps) {
  const t = translations[locale].otherPillars;
  return (
    <section className="bg-background px-6 py-20">
      <div className="mx-auto max-w-5xl">
        <h2 className="mb-10 text-center text-3xl font-bold text-foreground md:text-4xl">
          {t.title}
        </h2>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {PILLARS.map((p) => (
            <Link
              key={p.key}
              href={p.href}
              className="flex flex-col items-center justify-center rounded-xl border border-border bg-background p-6 text-center transition-colors hover:border-foreground"
            >
              <div className="text-3xl">{p.emoji}</div>
              <div className="mt-3 text-sm font-bold text-foreground">
                {(t.items as Record<string, string>)[p.key]}
              </div>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}
