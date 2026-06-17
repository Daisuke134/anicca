'use client';
import Link from 'next/link';
import { translations, type Locale } from '@/lib/i18n';
import { Reveal } from '@/components/site/taste';

interface FooterProps {
  locale: Locale;
}

// §9.F NO version stamps. §11.F legal hrefs fully preserved. §4.5 focus-visible gold on every link.
const LINK_CLASS =
  'transition-colors hover:text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--gold))]';

export default function Footer({ locale }: FooterProps) {
  const t = translations[locale].footer;

  return (
    <footer className="border-t border-[hsl(var(--border))] py-8 md:py-8">
      <div className="mx-auto max-w-[1400px] px-4">
        <Reveal>
          <div className="text-center">
            <p className="font-bold text-foreground">Anicca</p>

            <div className="mt-4 flex flex-wrap justify-center gap-4 text-sm text-muted-foreground">
              {/* spec31 §D/§E: surface /dais hub + cash-out guide (not in top nav) */}
              <Link href="/dais" className={LINK_CLASS}>
                {locale === 'ja' ? 'Dais のプロダクト' : "Dais's products"}
              </Link>
              <span aria-hidden="true">|</span>
              <Link href="/how-to-cash-out" className={LINK_CLASS}>
                {locale === 'ja' ? '現金化ガイド' : 'How to cash out'}
              </Link>
              <span aria-hidden="true">|</span>
              {/* §11.F legal link hrefs + labels preserved */}
              <Link href={`/privacy/${locale}`} className={LINK_CLASS}>
                {t.privacy}
              </Link>
              <span aria-hidden="true">|</span>
              <Link href={`/terms/${locale}`} className={LINK_CLASS}>
                {t.terms}
              </Link>
              <span aria-hidden="true">|</span>
              <Link href="/tokushoho" className={LINK_CLASS}>
                {t.tokushoho}
              </Link>
              <span aria-hidden="true">|</span>
              <a href="mailto:contact@aniccaai.com" className={LINK_CLASS}>
                {t.contact}
              </a>
            </div>

            <p className="mt-4 text-sm text-muted-foreground">
              &copy; {new Date().getFullYear()} Anicca. All rights reserved.
            </p>
          </div>
        </Reveal>
      </div>
    </footer>
  );
}
