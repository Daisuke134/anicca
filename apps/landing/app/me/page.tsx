import LaunchNav from '@/components/site/LaunchNav';
import Footer from '@/components/site/Footer';

// FOUNDATION PLACEHOLDER — route reserved + nav pre-wired so links resolve (curl 200).
// Owner: WF-A install/me builder (spec27 A-install/me). The builder REPLACES the
// body below with the real /me page (instance management + withdraw). Do NOT touch
// LaunchNav or skills-lock.json — your route link is already wired.

export const dynamic = 'force-static';

export const metadata = {
  title: 'Me — Your Anicca Instance',
  description:
    'Manage your Anicca instance: live P&L, runway, and one-tap withdraw of earned USDC.',
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
          This page will show your instance&apos;s live numbers and let you withdraw
          earned USDC. Coming online with the launch build.
        </p>
      </main>
      <Footer locale="en" />
    </>
  );
}
