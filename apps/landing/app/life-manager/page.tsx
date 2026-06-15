import LaunchNav from '@/components/site/LaunchNav';
import Footer from '@/components/site/Footer';

// FOUNDATION PLACEHOLDER — route reserved + nav pre-wired so links resolve (curl 200).
// Owner: WF-B Life Manager builders (spec27 WF-B: travel/call/ask/notify). The builder
// REPLACES the body below with the real /life-manager page. Do NOT touch LaunchNav or
// skills-lock.json — your route link is already wired.

export const dynamic = 'force-static';

export const metadata = {
  title: 'Life Manager — Anicca',
  description:
    'Anicca as your life manager: auto travel blocks, a real phone call 15 min before each event (Gemini Charon), mail-based ask + late-notify. No human in the loop.',
};

export default function Page() {
  return (
    <>
      <LaunchNav active="/life-manager" />
      <main className="container mx-auto min-h-[60vh] px-6 py-20 lg:px-8">
        <h1 className="text-3xl font-bold text-[hsl(var(--text-primary))]">
          Life Manager
        </h1>
        <p className="mt-4 max-w-prose text-[hsl(var(--text-secondary))]">
          Anicca reads your calendar, inserts travel time, calls you before every
          event, and never lets you be late — all by mail and phone, no app to open.
          Coming online with the launch build.
        </p>
      </main>
      <Footer locale="en" />
    </>
  );
}
