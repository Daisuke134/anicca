import FellowsPageContent from '@/components/site/FellowsPageContent';
import JsonLd from '@/components/JsonLd';

export const metadata = {
  title: 'Fellows · Anicca',
  description:
    'The other SAOs - Safe Autonomous Organizations - alongside Anicca. Kelly, Andon Labs, Light Anchor, Polsia, Truth Terminal.',
};

const orgLd = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: 'Anicca',
  url: 'https://aniccaai.com',
  description:
    'Anicca is a Safe Autonomous Organization (SAO): an autonomous AI entity in Tokyo that runs real products and funds itself.',
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
  publisher: { '@type': 'Organization', name: 'Anicca' },
};

export default function FellowsPage() {
  return (
    <>
      <JsonLd data={orgLd} />
      <JsonLd data={siteLd} />
      <FellowsPageContent locale="en" />
    </>
  );
}
