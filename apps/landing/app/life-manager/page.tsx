import LaunchFrame from '@/components/site/LaunchFrame';
import LifeManagerBody from './LifeManagerBody';

// spec28/spec29 P-lm-separate: MARKETING page for the SEPARATE cloud product `/lm`
// ($20/mo, no trial). "Get started" CTA routes to /lm (NOT /install). Fully localized
// EN/JA via LaunchFrame → LaunchLocaleProvider. Collision rule: nav + footer come from
// LaunchFrame; only the body copy is localized. Skill logic:
// netlify/functions/_lib/{travel,ask,call,notify}-logic.js + python crons unchanged.

export const dynamic = 'force-static';

export const metadata = {
  title: 'Life Manager — Anicca',
  description:
    'Anicca as your life manager: reads your Google Calendar, auto-inserts travel time blocks before every event via Google Maps Directions, and calls you 15 minutes before each appointment with Gemini Charon voice. No app to open.',
};

export default function Page() {
  return (
    <LaunchFrame active="/life-manager">
      <LifeManagerBody />
    </LaunchFrame>
  );
}
