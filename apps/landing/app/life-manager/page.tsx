import LaunchNav from '@/components/site/LaunchNav';
import Footer from '@/components/site/Footer';
import { SplitHero, Section, Reveal, CTA } from '@/components/site/taste';

// B-travel (spec27 WF-B) — Life Manager landing page.
// Replaces Foundation placeholder. Collision rule: ONLY replaces body; LaunchNav +
// Footer are imported as-is, not modified. Skill lives at ~/anicca/skills/life/travel.js.
// Logic module: netlify/functions/_lib/travel-logic.js (TDD-verified, 12 tests pass).

export const dynamic = 'force-static';

export const metadata = {
  title: 'Life Manager — Anicca',
  description:
    'Anicca as your life manager: reads your Google Calendar, auto-inserts travel time blocks before every event via Google Maps Directions, and calls you 15 minutes before each appointment with Gemini Charon voice. No app to open.',
};

// ── Feature table data ────────────────────────────────────────────────────────

type FeatureStatus = 'live' | 'coming';

const FEATURES: {
  id: string;
  label: string;
  headline: string;
  body: string;
  status: FeatureStatus;
}[] = [
  {
    id: 'travel',
    label: 'B-travel',
    headline: 'Automatic travel blocks',
    body:
      'Anicca reads your primary Google Calendar each morning, calls Google Maps Directions for each timed event, and inserts a "[Travel] <event>" block so the commute is always visible. Moving dentist appointment from 10:00? The travel block moves with it.',
    status: 'live',
  },
  {
    id: 'call',
    label: 'B-call',
    headline: '15-min phone call before every event',
    body:
      'Gemini Live (voice: Charon, male) bridges over your carrier’s media stream. Anicca dials your number 15 minutes before each event, says "Next is Dentist at 10:00 — leave now, walk time 18 min, via Omotesando Exit A3." Two-way voice: you can ask follow-ups. The bridge is provider-agnostic — it routes over Twilio by default and over Telnyx for Japan (+81) numbers, since the same μ-law↔PCM transcode and Charon socket serve both carriers.',
    status: 'coming',
  },
  {
    id: 'ask',
    label: 'B-ask',
    headline: 'Missing location? Ask you by email',
    body:
      "When a calendar event has no location, Anicca emails you: \"Where is the Team Sync? Reply with the address and I'll update the event.\" Your reply triggers an AgentMail webhook that writes the location back to GCal.",
    status: 'coming',
  },
  {
    id: 'notify',
    label: 'B-notify',
    headline: 'Late-risk → draft → you approve → notify attendees',
    body:
      "If Anicca detects you're running late (travel block starts after current time), she drafts \"I'll be 10 min late\" to the event attendees and emails you for approval. One-word reply \"OK\" fires the message. No app, pure email.",
    status: 'coming',
  },
];

const STATUS_BADGE: Record<FeatureStatus, string> = {
  live: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20',
  coming:
    'bg-[hsl(var(--surface-elevated))] text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))]',
};

const STATUS_LABEL: Record<FeatureStatus, string> = {
  live: 'live',
  coming: 'coming',
};

export default function Page() {
  return (
    <>
      <LaunchNav active="/life-manager" />

      <SplitHero
        headline="Life Manager"
        subtext="Anicca reads your calendar, inserts travel time, calls you before every event, and handles late-notice — all by phone and email. No app to open."
        primary={
          <CTA href="/install" variant="primary">
            Install Anicca
          </CTA>
        }
        secondary={
          <a
            href="#features"
            className="text-sm font-medium underline underline-offset-4 text-[hsl(var(--text-secondary))] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--gold))]"
          >
            See how it works
          </a>
        }
        asset={
          <div className="space-y-2 rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface-elevated))] p-5 font-mono text-sm">
            <p className="text-[hsl(var(--text-secondary))]">08:40 — wake-up call (Charon)</p>
            <p className="text-emerald-400">09:40 — [Travel] Team Sync → 20 min</p>
            <p className="text-[hsl(var(--text-primary))]">10:00 — Team Sync</p>
            <p className="text-emerald-400">11:40 — [Travel] Lunch → 8 min</p>
            <p className="text-[hsl(var(--text-primary))]">11:48 — Lunch with Kato</p>
            <p className="mt-1 text-xs text-[hsl(var(--text-secondary))] not-italic">
              All inserted automatically by Anicca ↑
            </p>
          </div>
        }
      />

      <Section id="features">
        <Reveal>
          <h2 className="font-display text-2xl md:text-3xl font-semibold text-[hsl(var(--text-primary))]">
            Four skills, one goal — never be late
          </h2>
          <p className="mt-2 text-sm text-[hsl(var(--text-secondary))]">
            Life Manager is a set of skills inside your local Anicca daemon. Each
            skill runs autonomously on your machine; no cloud subscription required.
          </p>
        </Reveal>

        <div className="mt-8 grid gap-4 md:grid-cols-2">
          {FEATURES.map((f) => (
            <Reveal key={f.id}>
              <div className="rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-5 h-full">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-[hsl(var(--text-secondary))]">
                    {f.label}
                  </span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${STATUS_BADGE[f.status]}`}
                  >
                    {STATUS_LABEL[f.status]}
                  </span>
                </div>
                <h3 className="mt-2 text-base font-semibold text-[hsl(var(--text-primary))]">
                  {f.headline}
                </h3>
                <p className="mt-2 text-sm text-[hsl(var(--text-secondary))] leading-relaxed">
                  {f.body}
                </p>
              </div>
            </Reveal>
          ))}
        </div>
      </Section>

      <Section>
        <Reveal>
          <h2 className="font-display text-2xl md:text-3xl font-semibold text-[hsl(var(--text-primary))]">
            How B-travel works (spec27 §2)
          </h2>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-[hsl(var(--border))] text-left">
                  <th className="py-2 pr-4 font-semibold text-[hsl(var(--text-primary))]">
                    Step
                  </th>
                  <th className="py-2 pr-4 font-semibold text-[hsl(var(--text-primary))]">
                    What Anicca does
                  </th>
                  <th className="py-2 font-semibold text-[hsl(var(--text-primary))]">API</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[hsl(var(--border))]">
                <tr>
                  <td className="py-3 pr-4 font-mono text-xs text-[hsl(var(--text-secondary))]">
                    1
                  </td>
                  <td className="py-3 pr-4 text-[hsl(var(--text-primary))]">
                    Read today&apos;s GCal events (timed only)
                  </td>
                  <td className="py-3 text-[hsl(var(--text-secondary))] font-mono text-xs">
                    GCal REST v3
                  </td>
                </tr>
                <tr>
                  <td className="py-3 pr-4 font-mono text-xs text-[hsl(var(--text-secondary))]">
                    2
                  </td>
                  <td className="py-3 pr-4 text-[hsl(var(--text-primary))]">
                    Detect events missing a [Travel] block
                  </td>
                  <td className="py-3 text-[hsl(var(--text-secondary))] font-mono text-xs">
                    travel-logic.js
                  </td>
                </tr>
                <tr>
                  <td className="py-3 pr-4 font-mono text-xs text-[hsl(var(--text-secondary))]">
                    3
                  </td>
                  <td className="py-3 pr-4 text-[hsl(var(--text-primary))]">
                    Call Google Maps Directions (transit) for each missing event
                  </td>
                  <td className="py-3 text-[hsl(var(--text-secondary))] font-mono text-xs">
                    Maps Directions
                  </td>
                </tr>
                <tr>
                  <td className="py-3 pr-4 font-mono text-xs text-[hsl(var(--text-secondary))]">
                    4
                  </td>
                  <td className="py-3 pr-4 text-[hsl(var(--text-primary))]">
                    Insert the [Travel] block — ends exactly at event start, colored
                    peacock blue
                  </td>
                  <td className="py-3 text-[hsl(var(--text-secondary))] font-mono text-xs">
                    GCal REST v3
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="mt-4 text-xs text-[hsl(var(--text-secondary))]">
            Travel blocks are idempotent — re-running the skill never duplicates them.
            A block is detected by its &quot;[Travel]&quot; prefix and the{' '}
            <code className="rounded-input bg-[hsl(var(--surface-elevated))] px-1 py-0.5">
              anicca_travel_block
            </code>{' '}
            extended property.
          </p>
        </Reveal>
      </Section>

      <Section>
        <Reveal>
          <h2 className="font-display text-2xl md:text-3xl font-semibold text-[hsl(var(--text-primary))]">
            Trigger design — schedule-derived, not clock polling
          </h2>
          <p className="mt-2 text-sm text-[hsl(var(--text-secondary))] leading-relaxed">
            Per spec27 §2 patch: Anicca registers a GCal push notification channel
            (watch channel). When any event is created or changed, GCal POSTs to the
            heartbeat endpoint. Anicca then re-evaluates only that event&apos;s travel block
            and fires the per-event timer at exactly{' '}
            <code className="rounded-input bg-[hsl(var(--surface-elevated))] px-1 py-0.5">
              eventStart − travelDuration − 15 min
            </code>{' '}
            for the phone call. The daily heartbeat is a safety net only.
          </p>
          <p className="mt-3 text-sm text-[hsl(var(--text-secondary))]">
            Result: second-accurate triggers, zero redundant GCal polls.
          </p>
        </Reveal>
      </Section>

      <Section>
        <Reveal>
          <h2 className="font-display text-2xl md:text-3xl font-semibold text-[hsl(var(--text-primary))]">
            Getting started
          </h2>
          <ol className="mt-4 list-decimal space-y-3 pl-6 text-sm text-[hsl(var(--text-primary))]">
            <li>
              <a
                href="/install"
                className="underline underline-offset-4 hover:text-[hsl(var(--text-secondary))] transition-colors"
              >
                Install Anicca
              </a>{' '}
              on your always-on machine (Mac Mini, Linux server, or cloud VM).
            </li>
            <li>
              During onboarding, grant Google Calendar OAuth when Anicca asks. She
              stores the refresh token in{' '}
              <code className="rounded-input bg-[hsl(var(--surface-elevated))] px-1 py-0.5">
                ~/.openclaw/.env
              </code>{' '}
              with{' '}
              <code className="rounded-input bg-[hsl(var(--surface-elevated))] px-1 py-0.5">
                chmod 600
              </code>
              .
            </li>
            <li>
              (Optional) Set{' '}
              <code className="rounded-input bg-[hsl(var(--surface-elevated))] px-1 py-0.5">
                HOME_ADDRESS
              </code>{' '}
              in{' '}
              <code className="rounded-input bg-[hsl(var(--surface-elevated))] px-1 py-0.5">
                ~/.openclaw/.env
              </code>{' '}
              for accurate transit times. Without it, Anicca defaults to a 20-minute
              travel buffer.
            </li>
            <li>
              Add a Google Maps API key as{' '}
              <code className="rounded-input bg-[hsl(var(--surface-elevated))] px-1 py-0.5">
                GOOGLE_MAPS_API_KEY
              </code>{' '}
              for real Directions lookups (free tier covers ~200 req/day).
            </li>
            <li>
              Open Google Calendar tomorrow morning — your commute blocks will already
              be there.
            </li>
          </ol>
        </Reveal>
      </Section>

      <Section>
        <Reveal>
          <div className="grid gap-4 md:grid-cols-2">
            <a
              href="/install"
              className="block rounded-card border border-[hsl(var(--gold))]/30 bg-[hsl(var(--surface))] p-5 transition-colors hover:bg-[hsl(var(--surface-elevated))]"
            >
              <p className="text-xs uppercase tracking-widest text-[hsl(var(--gold))]">
                get started
              </p>
              <p className="mt-2 text-base font-semibold text-[hsl(var(--text-primary))]">
                Install Anicca
              </p>
              <p className="mt-1 text-xs text-[hsl(var(--text-secondary))]">
                One prompt into Claude Code or Cursor. Anicca is live in 30 seconds.
              </p>
            </a>
            <a
              href="/dashboard"
              className="block rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-5 transition-colors hover:bg-[hsl(var(--surface-elevated))]"
            >
              <p className="text-xs uppercase tracking-widest text-[hsl(var(--text-secondary))]">
                live ledger
              </p>
              <p className="mt-2 text-base font-semibold text-[hsl(var(--text-primary))]">
                Colony dashboard
              </p>
              <p className="mt-1 text-xs text-[hsl(var(--text-secondary))]">
                All Anicca instances — revenue, spend, runway, status.
              </p>
            </a>
          </div>
        </Reveal>
      </Section>

      <Footer locale="en" />
    </>
  );
}
