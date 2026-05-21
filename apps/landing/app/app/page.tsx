'use client';

import { useEffect } from 'react';
import JsonLd from '@/components/JsonLd';

const APP_STORE_URL =
  'https://apps.apple.com/us/app/mindful-self-care-anicca/id6755129214';

const softwareApplicationLd = {
  '@context': 'https://schema.org',
  '@type': 'MobileApplication',
  name: 'Anicca',
  operatingSystem: 'iOS 15.0 or later',
  applicationCategory: 'HealthApplication',
  url: 'https://aniccaai.com/app',
  downloadUrl: APP_STORE_URL,
  installUrl: APP_STORE_URL,
  description:
    'Anicca is a proactive behavior-change companion. It asks what you are carrying (anxiety, self-doubt, rumination, late nights, loneliness, procrastination — 13 problem types), then sends a single line of kindness via notification exactly when you would otherwise spiral. No streaks, no guilt, no social feed.',
  publisher: {
    '@type': 'Organization',
    name: 'Anicca',
    url: 'https://aniccaai.com',
  },
  offers: [
    {
      '@type': 'Offer',
      name: 'Anicca Pro (Monthly)',
      price: '9.99',
      priceCurrency: 'USD',
      category: 'subscription',
      url: APP_STORE_URL,
    },
    {
      '@type': 'Offer',
      name: 'Anicca Pro (Annual)',
      price: '49.99',
      priceCurrency: 'USD',
      category: 'subscription',
      url: APP_STORE_URL,
    },
  ],
};

export default function AppRedirect() {
  useEffect(() => {
    window.location.replace(APP_STORE_URL);
  }, []);

  return (
    <>
      <JsonLd data={softwareApplicationLd} />
      <noscript>
        <meta httpEquiv="refresh" content={`0; url=${APP_STORE_URL}`} />
      </noscript>
    </>
  );
}
