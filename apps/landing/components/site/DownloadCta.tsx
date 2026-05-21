import Image from 'next/image';
import { translations, type Locale } from '@/lib/i18n';
import { links } from '@/lib/links';

interface DownloadCtaProps {
  locale: Locale;
}

export default function DownloadCta({ locale }: DownloadCtaProps) {
  const t = translations[locale].downloadCta;
  const l = links[locale];

  return (
    <section className="bg-background px-6 py-20">
      <h2 className="text-3xl font-bold text-center text-foreground">
        {t.title}
      </h2>
      <div className="mt-8 flex justify-center">
        <a href={l.appStore} target="_blank" rel="noopener noreferrer">
          <Image
            src={`/app-store-badge-${locale}.svg`}
            alt="Download on the App Store"
            width={180}
            height={60}
          />
        </a>
      </div>
      <p className="mt-4 text-center text-sm text-muted-foreground">
        {t.requirement}
      </p>
    </section>
  );
}
