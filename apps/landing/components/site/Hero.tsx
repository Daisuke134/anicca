import { translations, type Locale } from '@/lib/i18n';
import { SplitHero, CTA } from '@/components/site/taste';
import { LedgerWidget } from '@/components/site/v2/LedgerWidget';

interface HeroProps {
  locale: Locale;
}

// §v2.5: headline verbatim from translations.hero.headline (no added period).
// §4.3 ANTI-CENTER (VARIANCE 7 > 4) via SplitHero. §4.7 ≤4 hero text elements
// (headline + subtext + 2 CTAs). Asset = LedgerWidget, real visual per §4.8.
// TODO(§11.F-followup): migrate hardcoded subtext/CTA labels into
// translations[locale].hero (subtext, ctaPrimary, ctaSecondary).
export default function Hero({ locale }: HeroProps) {
  const t = translations[locale].hero;
  const subtext =
    locale === 'ja'
      ? '自分でコンピュート代を稼いで動く AI。自分の分を払って、残ったぶんを人に送る。'
      : 'An AI that earns its own compute. After it covers itself, it sends what is left to people.';
  // spec32: most people benefit via UBI, not by running one → "Receive basic income"
  // is the PRIMARY/top CTA; running an anicca yourself is the secondary path.
  const primaryLabel = locale === 'ja' ? 'ベーシックインカムを受け取る' : 'Receive basic income';
  const secondaryLabel = locale === 'ja' ? '自分で動かす（GitHub）' : 'Run one yourself (GitHub)';

  return (
    <SplitHero
      headline={t.headline}
      subtext={subtext}
      primary={
        <CTA href="/income" variant="primary">
          {primaryLabel}
        </CTA>
      }
      secondary={
        <CTA href="https://github.com/Daisuke134/anicca" variant="link">
          {secondaryLabel}
        </CTA>
      }
      asset={
        <a href="/dashboard" className="group block transition-opacity hover:opacity-90" aria-label="Live dashboard">
          <LedgerWidget locale={locale} />
          <span className="mt-3 inline-flex items-center gap-1 text-[13px] text-[hsl(var(--gold))] underline underline-offset-4">
            {locale === 'ja' ? 'ライブの数字を見る → aniccaai.com/dashboard' : 'See the live numbers → aniccaai.com/dashboard'}
          </span>
        </a>
      }
    />
  );
}
