import Navbar from '@/components/site/Navbar';
import Hero from '@/components/site/Hero';
import Manifesto from '@/components/site/Manifesto';
import EmpireDashboard from '@/components/site/EmpireDashboard';
import TheSpend from '@/components/site/TheSpend';
import TheEqualizer from '@/components/site/TheEqualizer';
import TheEmpireProducts from '@/components/site/TheEmpireProducts';
import Fellows from '@/components/site/Fellows';
import BigGive from '@/components/site/BigGive';
import ManifestoStrip from '@/components/site/ManifestoStrip';
import Footer from '@/components/site/Footer';
import JsonLd from '@/components/JsonLd';

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

export default function Page() {
  const locale = 'ja';

  return (
    <>
      <JsonLd data={organizationLd} />
      <JsonLd data={websiteLd} />
      <Navbar locale={locale} />
      <Hero locale={locale} />
      <Manifesto locale={locale} />
      <EmpireDashboard locale={locale} />
      <TheSpend locale={locale} />
      <TheEqualizer locale={locale} />
      <TheEmpireProducts locale={locale} />
      <Fellows locale={locale} />
      <BigGive locale={locale} />
      <ManifestoStrip locale={locale} />
      <Footer locale={locale} />
    </>
  );
}
