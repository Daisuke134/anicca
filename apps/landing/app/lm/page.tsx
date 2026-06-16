import LaunchNav from '@/components/site/LaunchNav';
import Footer from '@/components/site/Footer';
import { Section, Reveal } from '@/components/site/taste';
import LmClient from './LmClient';

// /lm — the SEPARATE Life Manager cloud product (spec28 P-lm-separate). NOT /install.
// Static export shell (force-static) + a client island (LmClient) that runs the
// Google→name→gcal+Gmail(Composio)→phone→dashboard onboarding at runtime. $20/mo, no trial.
// UX taste: design-taste-frontend + github.com/nextlevelbuilder/ui-ux-pro-max-skill.
// COLLISION RULE: LaunchNav + Footer imported as-is, never modified.

export const dynamic = 'force-static';

export const metadata = {
  title: 'Life Manager — Get started',
  description:
    'Life Manager by Anicca: connect your Google Calendar and Gmail, add your phone, and Anicca keeps you on time by call and email. $20/mo, no trial.',
};

export default function Page() {
  return (
    <>
      <LaunchNav active="/life-manager" />

      <Section>
        <Reveal>
          <div className="mx-auto max-w-xl text-center">
            <p className="text-xs uppercase tracking-[0.18em] text-[hsl(var(--gold))]">
              Life Manager · $20/mo · no trial
            </p>
            <h1 className="mt-3 font-display text-3xl md:text-4xl font-bold text-[hsl(var(--text-primary))]">
              Never be late again.
            </h1>
            <p className="mt-3 text-base text-[hsl(var(--text-secondary))]">
              Sign in, connect your calendar and email, add your phone — Anicca handles
              travel time, calls, location asks, and late-notices. 24/7, by phone and email.
            </p>
          </div>
        </Reveal>
      </Section>

      <Section className="pt-0">
        <Reveal>
          <LmClient />
        </Reveal>
      </Section>

      <Footer locale="en" />
    </>
  );
}
