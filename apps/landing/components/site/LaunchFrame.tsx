'use client';

import type { ReactNode } from 'react';
import LaunchNav from '@/components/site/LaunchNav';
import Footer from '@/components/site/Footer';
import { LaunchLocaleProvider, useLaunchLocale } from '@/lib/launchLocale';

// LaunchFrame — the shared shell for every launch surface (/install /me /lm
// /life-manager /life-call). It owns the LaunchLocaleProvider so the nav, the page
// body, and the footer all share ONE browser-resolved locale (static export safe).
// Pages render: <LaunchFrame active="/install">{localized body}</LaunchFrame>.

function FooterLocalized() {
  const { locale } = useLaunchLocale();
  return <Footer locale={locale} />;
}

export default function LaunchFrame({
  active,
  children,
}: {
  active?: string;
  children: ReactNode;
}) {
  return (
    <LaunchLocaleProvider>
      <LaunchNav active={active} />
      {children}
      <FooterLocalized />
    </LaunchLocaleProvider>
  );
}
