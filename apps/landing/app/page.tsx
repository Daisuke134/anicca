'use client';

import { useEffect } from 'react';
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
  useEffect(() => {
    window.location.replace('/en');
  }, []);

  return (
    <>
      <JsonLd data={organizationLd} />
      <JsonLd data={websiteLd} />
      <noscript>
        <meta httpEquiv="refresh" content="0; url=/en" />
      </noscript>
    </>
  );
}
