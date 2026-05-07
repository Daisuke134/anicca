import Link from 'next/link';
import { translations, type Locale } from '@/lib/i18n';

interface FooterProps {
  locale: Locale;
}

export default function Footer({ locale }: FooterProps) {
  const t = translations[locale].footerV2;

  return (
    <footer className="border-t border-[hsl(var(--hairline))] bg-background">
      <div className="container-wide py-20">
        <div className="grid grid-cols-1 gap-12 md:grid-cols-12">
          {/* Brand */}
          <div className="md:col-span-5">
            <Link href={`/${locale}`} className="font-serif text-3xl tracking-tight text-foreground">
              Anicca
            </Link>
            <p className="mt-4 max-w-sm text-sm leading-relaxed text-secondary">
              {t.tagline}
            </p>
          </div>

          {/* Sitemap */}
          <div className="md:col-span-3">
            <p className="font-mono text-[0.7rem] uppercase tracking-[0.18em] text-muted">
              {t.sitemapTitle}
            </p>
            <ul className="mt-5 space-y-3 text-sm">
              {t.sitemap.map((it) => (
                <li key={it.href}>
                  <Link
                    href={it.href}
                    className="text-foreground transition-colors hover:text-[hsl(var(--amber))]"
                  >
                    {it.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Legal */}
          <div className="md:col-span-2">
            <p className="font-mono text-[0.7rem] uppercase tracking-[0.18em] text-muted">
              {t.legalTitle}
            </p>
            <ul className="mt-5 space-y-3 text-sm">
              {t.legal.map((it) => (
                <li key={it.href}>
                  <Link
                    href={it.href}
                    className="text-secondary transition-colors hover:text-foreground"
                  >
                    {it.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Contact */}
          <div className="md:col-span-2">
            <p className="font-mono text-[0.7rem] uppercase tracking-[0.18em] text-muted">
              {t.contactTitle}
            </p>
            <ul className="mt-5 space-y-3 text-sm">
              <li>
                <a
                  href={`mailto:${t.contactEmail}`}
                  className="text-foreground transition-colors hover:text-[hsl(var(--amber))]"
                >
                  {t.contactEmail}
                </a>
              </li>
              <li>
                <a
                  href="https://github.com/Daisuke134"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-secondary transition-colors hover:text-foreground"
                >
                  {t.githubLabel} ↗
                </a>
              </li>
            </ul>
          </div>
        </div>

        <hr className="hairline mt-16" />

        <div className="mt-8 flex flex-col items-start justify-between gap-3 font-mono text-[0.7rem] uppercase tracking-[0.18em] text-muted md:flex-row md:items-center">
          <span>
            © {new Date().getFullYear()} {t.copyright}
          </span>
          <span>{t.tagline.split('.')[0]}.</span>
        </div>
      </div>
    </footer>
  );
}
