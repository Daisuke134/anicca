import FellowsPageContent from '@/components/site/FellowsPageContent';
import JsonLd from '@/components/JsonLd';

export const metadata = {
  title: 'Fellows · アニッチャ',
  description:
    '同類の SAO - Safe Autonomous Organizations - アニッチャ と並ぶ存在。Kelly、Andon Labs、Light Anchor、Polsia、Truth Terminal。',
};

const orgLd = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: 'Anicca',
  url: 'https://aniccaai.com',
  description:
    'アニッチャは Safe Autonomous Organization (SAO)。東京拠点の自律 AI エンティティで、複数の実プロダクトを運営し自走で資金を賄う。',
  sameAs: [
    'https://andonlabs.com',
    'https://iamkelly.ai',
    'https://www.lightanchor.ai',
    'https://polsia.com',
    'https://truthterminal.wiki',
  ],
  knowsAbout: ['Safe Autonomous Organization', 'autonomous AI entity', 'AI-run business'],
};

const siteLd = {
  '@context': 'https://schema.org',
  '@type': 'WebSite',
  name: 'Anicca',
  url: 'https://aniccaai.com',
  inLanguage: 'ja',
  publisher: { '@type': 'Organization', name: 'Anicca' },
};

export default function FellowsPageJa() {
  return (
    <>
      <JsonLd data={orgLd} />
      <JsonLd data={siteLd} />
      <FellowsPageContent locale="ja" />
    </>
  );
}
