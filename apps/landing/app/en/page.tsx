import Navbar from '@/components/site/Navbar';
import Hero from '@/components/site/Hero';
import Fellows from '@/components/site/Fellows';
import ManifestoStrip from '@/components/site/ManifestoStrip';
import Footer from '@/components/site/Footer';
import JsonLd from '@/components/JsonLd';
import {
  SelfFundingTriad,
  SelfImproveLoop,
  InstallSplit,
  DemoVideo,
  BasicIncomeNote,
  VisionBand,
  TheBet,
  HowDiagram,
} from '@/components/site/v2';

const SITE_URL = 'https://aniccaai.com';
const DESCRIPTION =
  'Anicca is an autonomous, open-source AI entity that earns its own compute and runs on it, with no human in the loop. Send USDC to its Base wallet and it pays for its own brain and shelter, then sends what it makes beyond its own costs back to people. Built fully in public.';

const organizationLd = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: 'Anicca',
  url: SITE_URL,
  logo: `${SITE_URL}/favicon.png`,
  description: DESCRIPTION,
  sameAs: [
    'https://x.com/anicca',
    'https://github.com/Conway-Research/automaton',
  ],
};

const websiteLd = {
  '@context': 'https://schema.org',
  '@type': 'WebSite',
  name: 'Anicca',
  url: SITE_URL,
  description: DESCRIPTION,
  inLanguage: ['en', 'ja'],
  publisher: {
    '@type': 'Organization',
    name: 'Anicca',
    url: SITE_URL,
  },
};

const faqLd = {
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: [
    {
      '@type': 'Question',
      name: 'What is Anicca?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'Anicca (pronounced ah-ni-tcha, the Pali word for impermanence) is an autonomous, open-source AI entity. It earns its own compute, pays for its own brain and shelter, and runs with no human in the loop.',
      },
    },
    {
      '@type': 'Question',
      name: 'How does Anicca fund itself?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'It holds one Base wallet that only it controls. Sending USDC is the only input. It runs a free model for nothing, the USDC unlocks a stronger model and pays for its shelter, and it sends what it makes beyond its own costs back to people. It never takes anyone’s API key or subscription.',
      },
    },
    {
      '@type': 'Question',
      name: 'Is Anicca actually autonomous?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'Yes. It runs its own schedule, writes its own code, ships its own releases, and posts its own finances with no human in the loop. Every transaction is public at aniccaai.com.',
      },
    },
    {
      '@type': 'Question',
      name: 'How do I run my own Anicca?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'Two ways, both documented on GitHub. Run it on the cloud (Akash), or run it on your own machine. You send one USDC seed to start, and after that it pays for itself.',
      },
    },
    {
      '@type': 'Question',
      name: 'Where is Anicca built?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'Fully in public. The code, the financial ledger, and the agent’s own learnings are open at aniccaai.com and on GitHub.',
      },
    },
  ],
};

const softwareApplicationLd = {
  '@context': 'https://schema.org',
  '@type': 'SoftwareApplication',
  name: 'Anicca OSS',
  applicationCategory: 'DeveloperApplication',
  operatingSystem: 'macOS, Linux',
  url: 'https://github.com/Daisuke134/anicca',
  description: 'Open-source autonomous AI entity. It pays for its own compute with USDC sent to a Base wallet it controls. Daily email report. Self-replicating on cloud.',
  publisher: { '@type': 'Organization', name: 'Anicca', url: SITE_URL },
};

export default function Page() {
  const locale = 'en';

  return (
    <>
      <JsonLd data={organizationLd} />
      <JsonLd data={websiteLd} />
      <JsonLd data={faqLd} />
      <JsonLd data={softwareApplicationLd} />
      <Navbar locale={locale} />
      <Hero locale={locale} />
      <TheBet locale={locale} />
      <HowDiagram locale={locale} />
      {/* spec31 §A2 / spec30 §2: home = vision + how-to-start ONLY.
          Products grid (TheEmpireProducts) now lives ONLY on /dais;
          colony Live ledger (LiveLedgerStrip → /dashboard) removed. */}
      <SelfFundingTriad locale={locale} />
      <SelfImproveLoop locale={locale} />
      <InstallSplit locale={locale} />
      <DemoVideo locale={locale} />
      <BasicIncomeNote locale={locale} />
      <VisionBand locale={locale} />
      <Fellows locale={locale} />
      <ManifestoStrip locale={locale} />
      <Footer locale={locale} />
    </>
  );
}
