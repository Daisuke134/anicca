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

export default function Page() {
  const locale = 'en';

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
