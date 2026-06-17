import Link from 'next/link';
import { type Locale } from '@/lib/i18n';

interface NavbarProps {
  locale: Locale;
}

export default function Navbar({ locale }: NavbarProps) {
  const otherLocale = locale === 'en' ? 'ja' : 'en';

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 h-16 md:h-[72px] max-h-[80px] border-b border-border bg-[hsl(var(--background))] backdrop-blur supports-[backdrop-filter]:bg-[hsl(var(--background))]/60">
      <div className="container mx-auto flex h-full items-center justify-between gap-6 px-6 lg:px-8">
        <Link
          href={`/${locale}`}
          className="text-xl font-bold text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--gold))]"
        >
          Anicca
        </Link>

        <div className="hidden flex-1 items-center gap-6 whitespace-nowrap md:flex">
          {/* spec31 §G / spec30 §10: no /install route. Anchor to the on-page Start
              section (cloud / local, both on GitHub). */}
          <Link
            href="#start"
            className="text-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--gold))]"
          >
            {locale === 'ja' ? '始める' : 'Start'}
          </Link>
        </div>

        <div className="flex items-center gap-4">
          <Link
            href={`/${otherLocale}`}
            className="rounded-pill border border-border px-3 py-1.5 text-sm font-medium transition-colors hover:bg-muted focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--gold))]"
          >
            {locale === 'en' ? 'JA' : 'EN'}
          </Link>
        </div>
      </div>
    </nav>
  );
}
