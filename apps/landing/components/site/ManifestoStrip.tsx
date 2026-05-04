import Link from 'next/link';
import { translations, type Locale } from '@/lib/i18n';

interface ManifestoStripProps {
  locale: Locale;
}

export default function ManifestoStrip({ locale }: ManifestoStripProps) {
  const t = translations[locale].manifestoStrip;
  return (
    <section className="bg-background px-6 py-20">
      <div className="mx-auto max-w-2xl text-center">
        <p className="text-xl font-semibold leading-relaxed text-foreground md:text-2xl">
          {t.body}
        </p>
        <Link
          href={`/${locale}#vision`}
          className="mt-6 inline-block text-sm text-muted-foreground underline transition-colors hover:text-foreground"
        >
          {t.cta}
        </Link>
      </div>
    </section>
  );
}
