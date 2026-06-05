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
      ? '自分でコンピュートを稼ぎ、余剰をベーシックインカムとして人類に配るオートノマス AI エンティティ。'
      : 'An autonomous AI entity that earns its own compute and distributes the surplus as Basic Income to humans.';
  const primaryLabel = locale === 'ja' ? 'クラウドで起動' : 'Install on cloud';
  const secondaryLabel = locale === 'ja' ? 'GitHub でクローン' : 'Clone on GitHub';

  return (
    <SplitHero
      headline={t.headline}
      subtext={subtext}
      primary={
        <CTA href="/install" variant="primary">
          {primaryLabel}
        </CTA>
      }
      secondary={
        <CTA href="https://github.com/Daisuke134/anicca-oss" variant="link">
          {secondaryLabel}
        </CTA>
      }
      asset={<LedgerWidget locale={locale} />}
    />
  );
}
