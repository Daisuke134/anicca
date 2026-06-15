import LaunchNav from '@/components/site/LaunchNav';
import Footer from '@/components/site/Footer';
import MeClient from './MeClient';

// /me — instance management (spec27 A-install/me / A-earn GATE-0). The page shell stays a
// static server component (force-static + metadata); the per-wallet live numbers + withdraw
// are a client island (MeClient) that fetches /.netlify/functions/dashboard-sync at runtime.
// Do NOT touch LaunchNav / next.config.mjs / skills-lock.json — the route + nav are pre-wired.

export const dynamic = 'force-static';

export const metadata = {
  title: 'Me — Your Anicca Instance',
  description:
    'Manage your Anicca instance: live P&L, runway, self-funded status, and withdraw of earned USDC.',
};

export default function Page() {
  return (
    <>
      <LaunchNav active="/me" />
      <main className="container mx-auto min-h-[60vh] px-6 py-20 lg:px-8">
        <h1 className="text-3xl font-bold text-[hsl(var(--text-primary))]">
          Your Anicca instance
        </h1>
        <p className="mt-4 max-w-prose text-[hsl(var(--text-secondary))]">
          Connect your instance wallet to see its live numbers — net worth, monthly revenue,
          daily burn, runway, and whether it pays for itself — straight from the same signed
          telemetry that powers the public dashboard. Your instance writes only to its own
          body; this page just reads it.
        </p>
        <MeClient />
      </main>
      <Footer locale="en" />
    </>
  );
}
