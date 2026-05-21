import Link from 'next/link';
import { translations, type Locale } from '@/lib/i18n';

interface TwoCtaButtonsProps {
  locale: Locale;
}

export default function TwoCtaButtons({ locale }: TwoCtaButtonsProps) {
  const t = translations[locale].twoCta;

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col items-stretch gap-4 px-6 py-10 sm:flex-row sm:justify-center">
      <Link
        href="/income"
        className="flex flex-1 flex-col items-center justify-center rounded-xl border border-foreground bg-foreground px-6 py-5 text-center text-background transition-opacity hover:opacity-90"
      >
        <span className="text-xl font-bold sm:text-2xl">{t.income.title}</span>
        <span className="mt-1 text-sm opacity-80">{t.income.subtitle}</span>
      </Link>

      <a
        href="https://github.com/Daisuke134/anicca"
        target="_blank"
        rel="noopener noreferrer"
        className="flex flex-1 flex-col items-center justify-center rounded-xl border border-foreground bg-background px-6 py-5 text-center text-foreground transition-colors hover:bg-muted"
      >
        <span className="text-xl font-bold sm:text-2xl">{t.local.title}</span>
        <span className="mt-1 text-sm text-muted-foreground">{t.local.subtitle}</span>
      </a>
    </div>
  );
}
