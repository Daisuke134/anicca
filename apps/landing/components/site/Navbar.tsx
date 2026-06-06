import Link from 'next/link';
import { translations, type Locale } from '@/lib/i18n';

interface NavbarProps {
  locale: Locale;
}

export default function Navbar({ locale }: NavbarProps) {
  const t = translations[locale].nav;
  if (!t) return null;
  const otherLocale = locale === 'en' ? 'ja' : 'en';

  const items = [
    { href: '/research', label: t.research },
    { href: '/politics', label: t.politics },
    { href: '/donation', label: t.donation },
    { href: locale === 'ja' ? '/tegami' : '/letter', label: t.letter },
    { href: '/income', label: t.income },
  ];

  return (
    <nav className="sticky top-0 z-50 border-b border-[hsl(var(--hairline))] bg-[hsl(var(--background))]/85 backdrop-blur-md">
      <div className="container-wide flex h-14 items-center justify-between">
        <Link
          href={`/${locale}`}
          className="font-serif text-xl tracking-tight text-foreground"
          aria-label="Anicca — home"
        >
          Anicca
        </Link>

        <div className="hidden items-center gap-7 lg:flex">
          {items.map((it) => (
            <Link
              key={it.href}
              href={it.href}
              className="font-mono text-[0.72rem] uppercase tracking-[0.18em] text-secondary transition-colors hover:text-foreground"
            >
              {it.label}
            </Link>
          ))}
          <a
            href="https://github.com/Daisuke134/anicca"
            target="_blank"
            rel="noopener noreferrer"
            className="font-mono text-[0.72rem] uppercase tracking-[0.18em] text-secondary transition-colors hover:text-foreground"
          >
            {t.github}
          </a>
        </div>

        <Link
          href={`/${otherLocale}`}
          className="font-mono text-[0.72rem] uppercase tracking-[0.18em] text-secondary transition-colors hover:text-foreground"
        >
          {t.switchLocale}
        </Link>
      </div>
    </nav>
  );
}
