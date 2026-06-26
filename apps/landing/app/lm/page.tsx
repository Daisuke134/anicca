import LaunchFrame from '@/components/site/LaunchFrame';
import LmBody from './LmBody';

// /lm — the SEPARATE Life Manager cloud product (spec28 P-lm-separate). NOT /install.
// Static export shell (force-static) + a client island (LmBody → hero + LmClient) that
// runs the Google→name→gcal(Composio)→phone→dashboard onboarding at runtime.
// $20/mo, no trial. spec29 + Dais 2026-06-16: fully localized EN/JA via LaunchFrame.
// COLLISION RULE: nav + footer come from LaunchFrame; the OAuth-survival flow is UNCHANGED.

export const dynamic = 'force-static';

export const metadata = {
  title: 'Life Manager — Get started',
  description:
    'Life Manager by Anicca: connect your Google Calendar, add your phone, and Anicca calls you before you need to leave, fills in travel time, and keeps you on time. $20/mo.',
};

export default function Page() {
  return (
    <LaunchFrame active="/life-manager">
      <LmBody />
    </LaunchFrame>
  );
}
