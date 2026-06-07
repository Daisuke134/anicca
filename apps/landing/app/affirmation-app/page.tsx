import AffirmationLanding from '@/components/affirmation/AffirmationLanding';
import JsonLd from '@/components/JsonLd';

export const metadata = {
  title: 'Anicca - the affirmation app that finds you',
  description:
    "Anicca is an iOS app that delivers a single line of kindness at the exact moment your mind starts to spiral. AI-personalised, Buddhist-rooted (Anicca = impermanence), proactive, free to download.",
};

const jsonLd = {
  '@context': 'https://schema.org',
  '@type': 'SoftwareApplication',
  name: 'Anicca',
  applicationCategory: 'HealthApplication',
  operatingSystem: 'iOS',
  url: 'https://aniccaai.com/affirmation-app',
  description:
    'Anicca is an iOS affirmation app that delivers one personalised line of kindness at the moment your mind starts to spiral. AI-timed, Buddhist-rooted (anicca = impermanence), proactive.',
  offers: { '@type': 'Offer', price: '9.99', priceCurrency: 'USD' },
  publisher: { '@type': 'Organization', name: 'Anicca', url: 'https://aniccaai.com' },
};

const faqLd = {
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: [
    { '@type': 'Question', name: 'What is Anicca?', acceptedAnswer: { '@type': 'Answer', text: 'An iOS app that sends one short, personalised affirmation at the moment you are most likely to spiral. Not a feed, not a streak — one line, then it gets out of the way.' } },
    { '@type': 'Question', name: 'How is it different from Calm or Headspace?', acceptedAnswer: { '@type': 'Answer', text: 'Calm and Headspace are libraries you browse. Anicca is proactive and tiny: it finds you with one line instead of asking you to find a session.' } },
    { '@type': 'Question', name: 'Does it have streaks?', acceptedAnswer: { '@type': 'Answer', text: 'No. Streaks punish the day you miss, which is usually the day you needed it. Anicca has nothing to maintain.' } },
    { '@type': 'Question', name: 'What does Anicca mean?', acceptedAnswer: { '@type': 'Answer', text: 'Anicca is the Buddhist term for impermanence — the idea that every state passes. The app is built around that single observation.' } },
    { '@type': 'Question', name: 'How much does it cost?', acceptedAnswer: { '@type': 'Answer', text: 'Free to download; $9.99/month or $49.99/year for the full proactive experience. iOS 15+.' } },
  ],
};

export default function Page() {
  return (
    <>
      <JsonLd data={jsonLd} />
      <JsonLd data={faqLd} />
      <AffirmationLanding locale="en" />
    </>
  );
}
