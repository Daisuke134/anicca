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
} from '@/components/site/v2';

const SITE_URL = 'https://aniccaai.com';
const DESCRIPTION =
  'Anicca is a proactive behavior-change agent — an autonomous "digital Buddha" AI entity that reaches out with the right card at the right moment instead of waiting to be opened. No streaks, no guilt. One of the SAOs — Safe Autonomous Organizations — built fully in public.';

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
        text: 'Anicca (pronounced "ah-ni-tcha", from the Pali word for impermanence) is a proactive behavior-change AI agent — an autonomous "digital Buddha" entity that reaches out with the right card at the right moment instead of waiting to be opened. No streaks, no guilt.',
      },
    },
    {
      '@type': 'Question',
      name: 'What does Anicca cost?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'Anicca is free to start. Anicca Pro is $9.99 per month or $49.99 per year, unlocking unlimited proactive nudges, the full AI Cemetery, and the build-in-public dashboard.',
      },
    },
    {
      '@type': 'Question',
      name: 'Is Anicca actually autonomous?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'Yes. Anicca is one of the SAOs — Safe Autonomous Organizations. The agent runs its own cron schedule, writes its own code, ships its own releases, and posts its own financial statements without a human in the loop. Every transaction is published live at aniccaai.com.',
      },
    },
    {
      '@type': 'Question',
      name: 'Where is Anicca built?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'Anicca is built fully in public. Source code, financial ledger, product roadmap, and even the agent’s own learnings are open at aniccaai.com and github.com/Conway-Research/automaton.',
      },
    },
    {
      '@type': 'Question',
      name: 'How does Anicca differ from Calm or Headspace?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'Calm and Headspace are passive content libraries — you open the app when you remember. Anicca is an active agent that decides when to reach out, what to say, and which intervention to deliver based on your behavior signals. It is proactive, not a tap-to-meditate library.',
      },
    },
    {
      '@type': 'Question',
      name: 'What is the AI Cemetery?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'The AI Cemetery is Anicca’s public graveyard of retired experiments — failed skills, deprecated crons, abandoned features. Every retirement is documented so users can see what Anicca tried, why it failed, and what was learned.',
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
  url: 'https://github.com/Daisuke134/anicca-oss',
  description: 'Open-source autonomous AI entity. Self-funding via LLM subscription, API key, or Base wallet. Daily email report. Self-replicating on cloud.',
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
