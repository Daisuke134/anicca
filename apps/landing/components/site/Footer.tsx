import Link from 'next/link';
import { translations, type Locale } from '@/lib/i18n';

export default function Footer({ locale }: { locale: Locale }) {
  const t = translations[locale].footer;
  const en = locale === 'en';

  return (
    <footer className="border-t border-bone bg-cream px-5 py-12">
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-wrap items-end justify-between gap-y-6">
          <div>
            <p className="font-display text-[28px] italic tracking-tight text-ink">
              anicca <span className="text-gold">·</span>
            </p>
            <p className="mt-1 font-mono-ui text-[11px] uppercase tracking-[0.2em] text-mist">
              {en ? 'an autonomous AI entity · est. 2025 · Tokyo' : '自律的 AI エンティティ · 創業 2025 · 東京'}
            </p>
          </div>

          <div className="flex flex-wrap gap-x-5 gap-y-2 font-mono-ui text-[11px] uppercase tracking-[0.18em] text-mist">
            <Link href={`/privacy/${locale}`} className="hover:text-ink">{t.privacy}</Link>
            <Link href={`/terms/${locale}`} className="hover:text-ink">{t.terms}</Link>
            <Link href="/tokushoho" className="hover:text-ink">{t.tokushoho}</Link>
            <a href="mailto:contact@aniccaai.com" className="hover:text-ink">{t.contact}</a>
          </div>
        </div>

        <div className="editorial-rule my-8" />

        <p className="font-mono-ui text-[10px] uppercase tracking-[0.18em] text-mist">
          © {new Date().getFullYear()} Anicca · {en ? 'all conditioned things shall pass' : 'すべての構築されたものは滅びる'}
        </p>
      </div>
    </footer>
  );
}
