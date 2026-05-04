/* eslint-disable react/no-unescaped-entities */
import Link from 'next/link';

export const metadata = {
  title: 'Anicca Comedy — AI-generated skits + live shows',
  description:
    'Anicca Comedy: daily AI-generated comedy skits on TikTok, Instagram and X. Plus weekly stand-up at Tokyo Comedy Bar and monthly shows in SF/LA. The Buddhist comedian and his AI co-host.',
};

export default function Page() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-20 text-foreground leading-relaxed">
      <p className="mb-6 text-sm">
        <Link href="/en" className="text-muted-foreground underline transition-colors hover:text-foreground">
          ← Back to Anicca
        </Link>
      </p>

      <h1 className="text-4xl font-bold md:text-5xl">Anicca Comedy</h1>
      <p className="mt-4 text-lg text-muted-foreground">
        A Buddhist comedian and his AI co-host. Daily skits online. Live stand-up in Tokyo and the US.
      </p>

      <section className="mt-12">
        <h2 className="text-2xl font-semibold">What it is</h2>
        <p className="mt-4">
          Anicca Comedy is the comedy instance of the Anicca swarm. Three streams of output, one through-line: laugh while suffering passes.
        </p>
      </section>

      <section className="mt-10 space-y-8">
        <div>
          <h3 className="text-xl font-semibold">1. Daily AI skits — TT / IG / X</h3>
          <p className="mt-2 text-base text-muted-foreground">
            Two AI-generated comedy posts per day, fully automated. Pika avatars, ElevenLabs voices, ffmpeg. Hooks like "If the Godfather were lazy af," "AI is your interviewer," "This too shall pass — but the rent shall not."
          </p>
        </div>

        <div>
          <h3 className="text-xl font-semibold">2. Director-mode skits</h3>
          <p className="mt-2 text-base text-muted-foreground">
            The AI writes the bit. The human performs it. Anicca pings #anicca-comedy-ideas every morning with a script. Dais shoots a 30-second take and posts it back. The AI handles distribution.
          </p>
        </div>

        <div>
          <h3 className="text-xl font-semibold">3. Live stand-up</h3>
          <p className="mt-2 text-base text-muted-foreground">
            <strong className="text-foreground">Tokyo:</strong> weekly open mic at Tokyo Comedy Bar (Shibuya). Monthly headliner show.<br />
            <strong className="text-foreground">SF / LA:</strong> monthly. Open mic walk-ins to start. Cheapest path: ZIPAIR + hostel.
          </p>
        </div>
      </section>

      <section className="mt-12 rounded-xl border border-border px-6 py-6">
        <h2 className="text-xl font-semibold">Subscribe — $10/mo</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Discord access, member-only skits, vote on next bits, early access to live show tickets.
        </p>
        <p className="mt-4 text-xs text-muted-foreground">Stripe checkout coming soon.</p>
      </section>

      <footer className="mt-16 border-t border-border pt-8 text-xs text-muted-foreground">
        Live numbers: <Link href="/en" className="underline">aniccaai.com</Link>
      </footer>
    </main>
  );
}
