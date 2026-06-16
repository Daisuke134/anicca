import LaunchFrame from '@/components/site/LaunchFrame';
import { Section, Reveal } from '@/components/site/taste';
import MeGate from './MeGate';

// /me is PRIVATE / per-user (spec29). Anonymous visitors see ONLY a Google login wall — NEVER any
// dashboard, telemetry, wallet, or colony content. Logged-in users see THEIR OWN instance (real
// wallet dashboard + pay tiers). The colony's public proof (first on-chain wake) lives on /dashboard
// and /install, not here. Static export: the whole page is the client-side <MeGate> (lib/auth.ts),
// now fully localized EN/JA via LaunchFrame → LaunchLocaleProvider. The gate is UNCHANGED.

export const dynamic = 'force-static';

export const metadata = {
  title: 'Me — Your Anicca Instance',
  description: 'Sign in to manage your own Anicca instance: live P&L, runway, and withdraw earned USDC.',
};

export default function Page() {
  return (
    <LaunchFrame active="/me">
      <Section>
        <Reveal>
          {/* MeGate is the ENTIRE page body: anonymous → login wall only; logged-in → private dashboard. */}
          <MeGate />
        </Reveal>
      </Section>
    </LaunchFrame>
  );
}
