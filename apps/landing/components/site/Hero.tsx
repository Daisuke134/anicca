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
      ? '自分でコンピュートを稼いで動く AI。稼ぎの余りは、人にそのまま配る。'
      : 'An AI that earns its own compute and runs on it. Whatever it makes past survival goes back to people.';
  const primaryLabel = locale === 'ja' ? '始める' : 'Get started';
  const secondaryLabel = locale === 'ja' ? 'GitHub' : 'View on GitHub';

  return (
    <SplitHero
      headline={t.headline}
      subtext={subtext}
      primary={
        <CTA href="#start" variant="primary">
          {primaryLabel}
        </CTA>
      }
      secondary={
        <CTA href="https://github.com/Daisuke134/anicca" variant="link">
          {secondaryLabel}
        </CTA>
      }
      asset={<LedgerWidget locale={locale} />}
    />
  );
}
