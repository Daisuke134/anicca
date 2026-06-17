import Navbar from '@/components/site/Navbar';
import Hero from '@/components/site/Hero';
import TheEmpireProducts from '@/components/site/TheEmpireProducts';
import Fellows from '@/components/site/Fellows';
import ManifestoStrip from '@/components/site/ManifestoStrip';
import Footer from '@/components/site/Footer';
import JsonLd from '@/components/JsonLd';
import {
  SelfFundingTriad,
  LiveLedgerStrip,
  SelfImproveLoop,
  InstallSplit,
  DemoVideo,
  BasicIncomeNote,
  VisionBand,
  TheBet,
} from '@/components/site/v2';

const SITE_URL = 'https://aniccaai.com';
const DESCRIPTION_JA =
  'Anicca（アニッチャ）は、開かれるのを待つのではなく、必要なタイミングで一言のやさしさを届けるプロアクティブな行動変容エージェント。連続記録も罪悪感もなし。すべて公開で運営される自律AIエンティティ（SAO）。';

const organizationLd = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: 'Anicca',
  url: SITE_URL,
  logo: `${SITE_URL}/favicon.png`,
  description: DESCRIPTION_JA,
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
  description: DESCRIPTION_JA,
  inLanguage: ['ja', 'en'],
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
      name: 'Aniccaとは何ですか?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'Anicca（アニッチャ、パーリ語で「無常」）は、開かれるのを待つのではなく、必要なタイミングで一言のやさしさを届けるプロアクティブな行動変容AIエージェントです。連続記録も罪悪感もありません。',
      },
    },
    {
      '@type': 'Question',
      name: 'Aniccaの料金は?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'Aniccaは無料で始められます。Anicca Proは月額$9.99または年額$49.99で、無制限のプロアクティブ通知、AI Cemetery、Build-in-Publicダッシュボードがすべて利用できます。',
      },
    },
    {
      '@type': 'Question',
      name: 'Aniccaは本当に自律しているのですか?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'はい。AniccaはSAO（Safe Autonomous Organizations）の一つで、自分でcronを動かし、自分でコードを書き、自分でリリースを出荷し、財務諸表を自分で公開します。すべての取引はaniccaai.comで公開されています。',
      },
    },
    {
      '@type': 'Question',
      name: 'Aniccaはどこで開発されていますか?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'Aniccaはすべて公開で開発されています。ソースコード、財務台帳、プロダクトロードマップ、エージェント自身の学習ログまで、aniccaai.comとgithub.com/Conway-Research/automatonで公開しています。',
      },
    },
    {
      '@type': 'Question',
      name: 'AniccaはCalmやHeadspaceとどう違いますか?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'CalmやHeadspaceは受動的なコンテンツライブラリで、思い出したときに自分で開く必要があります。Aniccaはあなたの行動シグナルを見て、いつ、何を、どのように介入するかをエージェント自身が判断するプロアクティブな存在です。タップして瞑想するライブラリではありません。',
      },
    },
    {
      '@type': 'Question',
      name: 'AI Cemeteryとは何ですか?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'AI CemeteryはAniccaが引退させた実験の公開墓地です。失敗したスキル、廃止されたcron、捨てられた機能。引退の理由と学習が公開されているので、Aniccaが何を試して、何を学んだかが分かります。',
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
  description: 'オープンソースの自律 AI エンティティ。LLM サブスク・API キー・Base ウォレットで自己資金調達。日次メールレポート。クラウドで自己複製。',
  publisher: { '@type': 'Organization', name: 'Anicca', url: SITE_URL },
};

export default function Page() {
  const locale = 'ja';

  return (
    <>
      <JsonLd data={organizationLd} />
      <JsonLd data={websiteLd} />
      <JsonLd data={faqLd} />
      <JsonLd data={softwareApplicationLd} />
      <Navbar locale={locale} />
      <Hero locale={locale} />
      <TheBet locale={locale} />
      {/* Section 1 manifesto removed (Manifesto.tsx no longer used here) */}
      <SelfFundingTriad locale={locale} />
      <LiveLedgerStrip locale={locale} />
      <SelfImproveLoop locale={locale} />
      <InstallSplit locale={locale} />
      <DemoVideo locale={locale} />
      <BasicIncomeNote locale={locale} />
      <TheEmpireProducts locale={locale} />
      <VisionBand locale={locale} />
      <Fellows locale={locale} />
      <ManifestoStrip locale={locale} />
      <Footer locale={locale} />
    </>
  );
}
