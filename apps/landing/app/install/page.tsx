import JsonLd from '@/components/JsonLd';
import LaunchFrame from '@/components/site/LaunchFrame';
import InstallBody from './InstallBody';

// spec27/spec29 A-install: /install = 2-column cloud+OSS layout, fully localized EN/JA.
// The server shell keeps the SEO JsonLd; the localized body + nav + footer live in the
// client island (InstallBody inside LaunchFrame → LaunchLocaleProvider). Static export safe.
// COLLISION RULE: LaunchNav route list is pre-wired; localization only swaps copy.

export const dynamic = 'force-static';

const installLd = {
  '@context': 'https://schema.org',
  '@type': 'TechArticle',
  name: 'Install Anicca',
  url: 'https://aniccaai.com/install',
  description:
    'Install Anicca — AI agent that earns, manages your life, and self-replicates. Choose Cloud (Google login, 1 min) or OSS self-host.',
  publisher: { '@type': 'Organization', name: 'Anicca', url: 'https://aniccaai.com' },
};

export default function Page() {
  return (
    <>
      <JsonLd data={installLd} />
      <LaunchFrame active="/install">
        <InstallBody />
      </LaunchFrame>
    </>
  );
}
