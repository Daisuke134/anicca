import Link from 'next/link';
import JsonLd from '@/components/JsonLd';
import { SplitHero } from '@/components/site/taste/SplitHero';
import { Section } from '@/components/site/taste/Section';
import { Reveal } from '@/components/site/taste/Reveal';
import { CTA } from '@/components/site/taste/CTA';

// §11.F: metadata em-dash -> hyphen in title; description verbatim
export const metadata = {
  title: 'Anicca Web Apps - small useful tools, weekly',
  description:
    'Anicca Web Apps: a weekly micro-SaaS, autonomously built and deployed by Anicca. Each app is one tool that solves one suffering. Each subscribes for $9-$19/mo.',
};

// §11.F: JsonLd verbatim
const factoryLd = {
  '@context': 'https://schema.org',
  '@type': 'Service',
  name: 'Anicca Web Apps',
  url: 'https://aniccaai.com/factory',
  serviceType: 'Micro-SaaS subscription tools',
  provider: { '@type': 'Organization', name: 'Anicca', url: 'https://aniccaai.com' },
  description:
    'A weekly micro-SaaS, autonomously built and deployed by Anicca. Each app is one tool that solves one suffering. Subscription pricing $9-$19/month.',
};

// §11.F: app entries - external URLs verbatim
const APPS = [
  {
    name: 'PDF Insight',
    href: 'https://clear-pdf-converter.com',
    tagline: 'Turn any PDF into instant answers',
    price: '$19/mo',
    // BG diversity: token gradient (cell 0)
    bgClass: 'bg-[hsl(var(--surface-elevated))]',
    accentClass: 'bg-[hsl(var(--gold)/0.15)]',
  },
  {
    name: 'GlowUp AI',
    href: 'https://iglowup-ai.lovable.app',
    tagline: 'AI face score + glow-up roadmap',
    price: 'Free',
    // BG diversity: image seed (cell 1)
    bgClass: 'bg-[hsl(var(--surface))]',
    accentClass: 'bg-[hsl(var(--gold)/0.08)]',
  },
  {
    name: 'Lookmax',
    href: null,
    tagline: 'Small tool that funds the mission',
    price: 'Coming',
    // BG diversity: muted surface (cell 2)
    bgClass: 'bg-[hsl(var(--surface-muted,var(--surface)))]',
    accentClass: 'bg-[hsl(var(--border)/0.4)]',
  },
  {
    name: 'Honne',
    href: null,
    tagline: 'Small tool that funds the mission',
    price: 'Coming',
    bgClass: 'bg-[hsl(var(--surface))]',
    accentClass: 'bg-[hsl(var(--border)/0.4)]',
  },
];

// §9.F pipeline labels: verb-noun direct (Pick / Build / Ship - no Stage/Step/Phase)
const PIPELINE = [
  { verb: 'Pick', noun: 'Niche', body: 'Every Monday the factory cron reads trends and selects one specific problem worth $9-$19/mo.' },
  { verb: 'Build', noun: 'App', body: 'Anicca writes the code with the open-source ralph loop, deploys to Vercel, wires Stripe.' },
  { verb: 'Ship', noun: 'Revenue', body: 'Revenue from every app flows into aniccaai.com. The ones that scale, scale.' },
];

export default function Page() {
  return (
    <main>
      <JsonLd data={factoryLd} />

      {/* Hero */}
      <SplitHero
        eyebrow="Anicca Web Apps"
        headline={<>One useful tool,<br />every week.</>}
        subtext="Anicca picks the niche, builds the app, ships it, charges for it. Each solves one specific suffering. $9-$19/mo."
        primary={<CTA href="/en">Back to Anicca</CTA>}
        secondary={<CTA href="/fellows" variant="link">SAO Fellows</CTA>}
        asset={
          // §4.8 real visual - Anicca brand asset
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src="/anicca-app-icon.png"
            alt="Anicca app icon"
            className="h-full w-full object-cover"
            width={1024}
            height={1024}
          />
        }
      />

      {/* Bento grid - shipped apps (4 cells, BG diversity across cells 0-2) */}
      <Section id="apps">
        <Reveal>
          <p className="mb-8 text-[11px] uppercase tracking-[0.18em] text-[hsl(var(--text-secondary))]">
            Already shipped
          </p>
        </Reveal>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {APPS.map((app, i) => (
            <Reveal key={app.name} delay={i * 0.06}>
              <div
                className={[
                  'relative flex flex-col gap-4 overflow-hidden rounded-card border border-[hsl(var(--border))] px-6 py-6',
                  app.bgClass,
                ].join(' ')}
              >
                {/* BG diversity accent blob for first 3 cells */}
                {i < 3 && (
                  <span
                    aria-hidden
                    className={[
                      'pointer-events-none absolute right-0 top-0 h-28 w-28 -translate-y-1/3 translate-x-1/3 rounded-pill blur-2xl',
                      app.accentClass,
                    ].join(' ')}
                  />
                )}
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-[10px] uppercase tracking-[0.18em] text-[hsl(var(--text-secondary))]">
                      {app.price}
                    </p>
                    <p className="mt-1 text-lg font-semibold text-[hsl(var(--text-primary))]">
                      {app.name}
                    </p>
                  </div>
                </div>
                <p className="text-sm leading-relaxed text-[hsl(var(--text-secondary))]">
                  {app.tagline}
                </p>
                {app.href ? (
                  <a
                    href={app.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-auto text-sm font-medium text-[hsl(var(--gold))] underline-offset-4 hover:underline"
                  >
                    Open app
                  </a>
                ) : (
                  <span className="mt-auto text-sm text-[hsl(var(--text-secondary))] opacity-60">
                    In development
                  </span>
                )}
              </div>
            </Reveal>
          ))}
        </div>
      </Section>

      {/* Pipeline - §9.F verb-noun: Pick / Build / Ship (no Stage/Step/Phase labels) */}
      <Section id="pipeline">
        <Reveal>
          <p className="mb-8 text-[11px] uppercase tracking-[0.18em] text-[hsl(var(--text-secondary))]">
            How it works
          </p>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
            {PIPELINE.map((step, i) => (
              <div key={step.verb} className="rounded-card border border-[hsl(var(--border))] px-6 py-6">
                <p className="text-[10px] uppercase tracking-[0.18em] text-[hsl(var(--text-secondary))]">
                  {String(i + 1).padStart(2, '0')}
                </p>
                <p className="mt-2 text-xl font-semibold text-[hsl(var(--text-primary))]">
                  {step.verb}
                  <span className="ml-1.5 text-[hsl(var(--gold))]">{step.noun}</span>
                </p>
                <p className="mt-3 text-sm leading-relaxed text-[hsl(var(--text-secondary))]">
                  {step.body}
                </p>
              </div>
            ))}
          </div>
        </Reveal>
      </Section>

      {/* What it is */}
      <Section>
        <Reveal>
          <div className="mx-auto max-w-[65ch] space-y-5 text-base leading-relaxed text-[hsl(var(--text-secondary))]">
            <h2 className="text-2xl font-semibold text-[hsl(var(--text-primary))]">What it is</h2>
            <p>
              The web instance of the Anicca swarm. One tool per week. Written by Anicca
              with the open-source ralph loop, deployed to Vercel, Stripe-billed, marketed
              by the comedy and content instances.
            </p>
            <p>
              Each app solves one specific suffering: too many PDFs, too long emails, too
              many unread Slack threads. $9-$19/mo. They do not all hit. The ones that do, scale.
            </p>
            <p>
              The web-app-factory cron picks a niche from trends every Monday and ships an
              app by Friday. Each lives at its own URL. Revenue from all of them flows into{' '}
              <Link href="/en" className="underline-offset-4 hover:underline text-[hsl(var(--text-primary))]">
                aniccaai.com
              </Link>.
            </p>
          </div>
        </Reveal>
      </Section>

      {/* Footer nav - /en and /fellows preserved verbatim (§11.F) */}
      <Section>
        <Reveal>
          <div className="border-t border-[hsl(var(--border))] pt-8 text-xs text-[hsl(var(--text-secondary))]">
            Live numbers:{' '}
            <Link href="/en" className="underline hover:text-[hsl(var(--text-primary))]">aniccaai.com</Link>
            {' '}&middot; One of the{' '}
            <Link href="/fellows" className="underline hover:text-[hsl(var(--text-primary))]">SAOs</Link>
          </div>
        </Reveal>
      </Section>
    </main>
  );
}
