import Link from 'next/link';
import { type Locale } from '@/lib/i18n';

interface NavbarProps {
  locale: Locale;
}

export default function Navbar({ locale }: NavbarProps) {
  const otherLocale = locale === 'en' ? 'ja' : 'en';

  const items = locale === 'en'
    ? [
        { href: '/#products', label: 'Empire' },
        { href: '/fellows', label: 'Fellows' },
        { href: '/income', label: 'Basic Income' },
        { href: '/blog', label: 'Articles' },
        { href: '/letter', label: 'Letter' },
        { href: '/socials', label: 'Socials' },
      ]
    : [
        { href: '/#products', label: '帝国' },
        { href: '/fellows', label: '同類' },
        { href: '/income', label: 'インカム' },
        { href: '/blog', label: '記事' },
        { href: '/tegami', label: '手紙' },
        { href: '/socials', label: 'Socials' },
      ];

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-border/60 bg-cream/85 backdrop-blur supports-[backdrop-filter]:bg-cream/65">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-5">
        <Link
          href={`/${locale}`}
          className="font-display text-[19px] italic tracking-tight text-ink"
          aria-label="Anicca"
        >
          anicca
          <span className="ml-1.5 align-middle text-gold">·</span>
        </Link>

        <div className="hidden items-center gap-6 md:flex">
          {items.map((it) => (
            <Link
              key={it.href}
              href={it.href}
              className="text-[13px] tracking-wide text-mist transition-colors hover:text-ink"
            >
              {it.label}
            </Link>
          ))}
        </div>

        <Link
          href={`/${otherLocale}`}
          className="font-mono-ui text-[11px] uppercase tracking-[0.2em] text-mist hover:text-ink"
        >
          {locale === 'en' ? 'JA' : 'EN'}
        </Link>
      </div>
    </nav>
  );
}
