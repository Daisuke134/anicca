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
const DESCRIPTION_JA =
  'Anicca（アニッチャ）は、自分でコンピュートを稼いでその上で動く、オープンソースの自律 AI エンティティ。human-in-loop はない。自分の Base ウォレットに USDC を送ると、頭脳と住処の代金を自分で払い、生存ラインを超えた稼ぎは人に配る。すべて公開で運営している。';

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
      name: 'Anicca とは何ですか?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'Anicca（アニッチャ、パーリ語で「無常」）は、オープンソースの自律 AI エンティティです。自分でコンピュートを稼ぎ、頭脳と住処の代金を自分で払い、human-in-loop なしで動きます。',
      },
    },
    {
      '@type': 'Question',
      name: 'Anicca はどうやって自分を養うのですか?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: '自分だけが鍵を持つ Base ウォレットをひとつ持ちます。入力は USDC を送ることだけ。残高ゼロなら無料モデルで動き、USDC が入ると賢いモデルと住処の代金を自分で払い、生存ラインを超えた稼ぎは人に配ります。誰の API キーもサブスクも借りません。',
      },
    },
    {
      '@type': 'Question',
      name: 'Anicca は本当に自律しているのですか?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'はい。自分で予定を回し、自分でコードを書き、自分でリリースを出し、財務も自分で公開します。human-in-loop はありません。すべての取引は aniccaai.com で公開しています。',
      },
    },
    {
      '@type': 'Question',
      name: '自分の Anicca を動かすには?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: '方法は 2 つ、どちらも GitHub に手順があります。クラウド（Akash）で動かすか、自分のマシンで動かすか。最初に USDC のシードをひとつ送れば、あとは自分で自分を養います。',
      },
    },
    {
      '@type': 'Question',
      name: 'Anicca はどこで開発されていますか?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'すべて公開で開発しています。ソースコード、財務台帳、エージェント自身の学習ログまで、aniccaai.com と GitHub で公開しています。',
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
  description: 'オープンソースの自律 AI エンティティ。自分の Base ウォレットに届いた USDC で自分のコンピュートを払う。日次メールレポート。クラウドで自己複製。',
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
