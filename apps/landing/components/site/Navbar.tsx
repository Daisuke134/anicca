import Link from 'next/link';
import { type Locale } from '@/lib/i18n';

interface NavbarProps {
  locale: Locale;
}

export default function Navbar({ locale }: NavbarProps) {
  const otherLocale = locale === 'en' ? 'ja' : 'en';

  const items = locale === 'en'
    ? [
        { href: '/income', label: 'Income' },
        { href: 'https://github.com/Daisuke134/anicca', label: 'Local', external: true },
        { href: '/research', label: 'Research' },
        { href: '/letter', label: 'Newsletter' },
        { href: '/comedy', label: 'Comedy' },
        { href: '/tomb', label: 'Tomb' },
      ]
    : [
        { href: '/income', label: 'インカム' },
        { href: 'https://github.com/Daisuke134/anicca', label: 'ローカル', external: true },
        { href: '/research', label: '研究' },
        { href: '/tegami', label: '手紙' },
        { href: '/comedy', label: 'コメディ' },
        { href: '/tomb', label: '墓' },
      ];

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto flex h-16 items-center justify-between px-4 lg:px-8">
        <Link href={`/${locale}`} className="text-xl font-bold text-foreground">
          Anicca
        </Link>

        <div className="hidden items-center gap-5 lg:flex">
          {items.map((it) =>
            it.external ? (
              <a
                key={it.href}
                href={it.href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-muted-foreground transition-colors hover:text-foreground"
              >
                {it.label}
              </a>
            ) : (
              <Link
                key={it.href}
                href={it.href}
                className="text-sm text-muted-foreground transition-colors hover:text-foreground"
              >
                {it.label}
              </Link>
            ),
          )}
        </div>

        <Link
          href={`/${otherLocale}`}
          className="rounded-md border border-border px-3 py-1.5 text-sm font-medium transition-colors hover:bg-muted"
        >
          {locale === 'en' ? 'JA' : 'EN'}
        </Link>
      </div>
    </nav>
  );
}
