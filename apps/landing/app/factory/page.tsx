/* eslint-disable react/no-unescaped-entities */
import Link from 'next/link';

export const metadata = {
  title: 'Anicca Web Apps — small useful tools, weekly',
  description:
    'Anicca Web Apps: a weekly micro-SaaS, autonomously built and deployed by Anicca. Each app is one tool that solves one suffering. Each subscribes for $9–$19/mo.',
};

export default function Page() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-20 text-foreground leading-relaxed">
      <p className="mb-6 text-sm">
        <Link href="/en" className="text-muted-foreground underline transition-colors hover:text-foreground">
          ← Back to Anicca
        </Link>
      </p>

      <h1 className="text-4xl font-bold md:text-5xl">Web Apps</h1>
      <p className="mt-4 text-lg text-muted-foreground">
        A small useful tool, every week. Anicca picks the niche, builds the app, ships it, charges for it.
      </p>

      <section className="mt-12">
        <h2 className="text-2xl font-semibold">What it is</h2>
        <p className="mt-4">
          The web instance of the Anicca swarm. One tool per week. Written by Anicca with the open-source ralph loop, deployed to Vercel, Stripe-billed, marketed by the comedy and content instances.
        </p>
        <p className="mt-4">
          Each app solves one specific suffering: too many PDFs, too long emails, too many unread Slack threads. $9–$19/mo. They don't all hit. The ones that do, scale.
        </p>
      </section>

      <section className="mt-10">
        <h2 className="text-2xl font-semibold">Already shipped</h2>
        <ul className="mt-4 list-disc space-y-1 pl-6 text-base">
          <li><a href="https://clear-pdf-converter.com" className="underline" target="_blank" rel="noopener noreferrer">PDF Insight</a> — turn any PDF into instant answers, $19/mo</li>
          <li><a href="https://iglowup-ai.lovable.app" className="underline" target="_blank" rel="noopener noreferrer">GlowUp AI</a> — AI face score + glow-up roadmap</li>
          <li>Lookmax, Honne — small tools that fund the mission</li>
        </ul>
      </section>

      <section className="mt-10">
        <h2 className="text-2xl font-semibold">Coming weekly from May</h2>
        <p className="mt-4">
          The web-app-factory cron picks a niche from trends every Monday and ships an app by Friday. Each lives at its own URL. Revenue from all of them flows into{' '}
          <Link href="/en" className="underline transition-colors hover:text-foreground">aniccaai.com</Link>.
        </p>
      </section>

      <footer className="mt-16 border-t border-border pt-8 text-xs text-muted-foreground">
        Live numbers: <Link href="/en" className="underline">aniccaai.com</Link> · Source: github.com/Daisuke134/anicca
      </footer>
    </main>
  );
}
