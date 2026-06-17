import LaunchFrame from '@/components/site/LaunchFrame';
import { SplitHero, Section, Reveal, CTA } from '@/components/site/taste';

// B-call (spec27c WF-B) — Gemini Charon bidirectional phone bridge.
// NEW route (no nav / install.sh / registry / shared-page edits — collision rule).
// Skill entrypoint: ~/anicca/skills/life/call. Pure logic: netlify/functions/_lib/call-logic.js
// (TDD, 18 tests). Real ws bridge: scripts/call-bridge.cjs (TDD, 7 tests). Runner: scripts/life-call.mjs.
// LIVE E2E proof recorded below (real Twilio call SID + recording + bidirectional frame counts).

export const dynamic = 'force-static';

export const metadata = {
  title: 'B-call — Anicca calls you (Gemini Charon)',
  description:
    'Anicca phones you 15 minutes before every calendar event and talks two-way via Gemini Live (voice: Charon, male) bridged over Twilio Media Streams. Verified live: a real Twilio call connected the bridge to Gemini and Charon spoke on the line.',
};

// The real, re-checkable proof from the 2026-06-16 live E2E run.
const PROOF: { label: string; value: string }[] = [
  { label: 'Call SID', value: 'CA2c025395dd03adc740faef93f856717d' },
  { label: 'Status / duration', value: 'completed / 45s' },
  { label: 'Recording SID', value: 'RE8d3e28f117164498c3ac968e20370cba' },
  { label: 'Gemini Live setup', value: 'setupComplete (Charon, native-audio model)' },
  { label: 'Uplink frames (caller → Gemini)', value: '2200' },
  { label: 'Downlink frames (Charon → caller)', value: '214' },
];

const STEPS: { n: string; what: string; api: string }[] = [
  { n: '1', what: 'Twilio dials you (REST Calls API) 15 min before the event', api: 'Twilio Voice' },
  { n: '2', what: 'TwiML <Connect><Stream> pipes the call audio to our ws bridge', api: 'Media Streams' },
  { n: '3', what: 'Bridge transcodes μ-law 8k ↔ PCM 16k/24k each frame', api: 'call-logic.js' },
  { n: '4', what: 'Gemini Live (voice: Charon) does STT + LLM + TTS in one socket', api: 'Gemini Live' },
  { n: '5', what: 'Charon speaks "leave now for <event>" and answers your follow-ups', api: 'two-way' },
];

export default function Page() {
  return (
    <LaunchFrame active="/life-manager">
      <SplitHero
        headline="Anicca calls you"
        subtext="15 minutes before every event, Anicca phones you and talks — two-way — in Gemini's Charon voice over Twilio. No app to open, no button to press. Just answer."
        primary={
          <CTA href="https://github.com/Daisuke134/anicca" variant="primary">
            Get Anicca on GitHub
          </CTA>
        }
        secondary={
          <a
            href="#proof"
            className="text-sm font-medium underline underline-offset-4 text-[hsl(var(--text-secondary))] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--gold))]"
          >
            See the live proof
          </a>
        }
        asset={
          <div className="space-y-2 rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface-elevated))] p-5 font-mono text-sm">
            <p className="text-[hsl(var(--text-secondary))]">☎ incoming — Anicca (Charon)</p>
            <p className="text-[hsl(var(--text-primary))]">&ldquo;Hi, it&apos;s Anicca.</p>
            <p className="text-[hsl(var(--text-primary))]">Next is 伊藤歯科 at 09:45 —</p>
            <p className="text-[hsl(var(--text-primary))]">time to leave now.&rdquo;</p>
            <p className="mt-1 text-xs text-emerald-400 not-italic">
              Bidirectional · you can ask follow-ups ↑
            </p>
          </div>
        }
      />

      <Section id="proof">
        <Reveal>
          <div className="flex items-center gap-2">
            <h2 className="font-display text-2xl md:text-3xl font-semibold text-[hsl(var(--text-primary))]">
              Live proof (2026-06-16)
            </h2>
            <span className="rounded-full border border-emerald-500/20 bg-emerald-500/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-emerald-400">
              live
            </span>
          </div>
          <p className="mt-2 text-sm text-[hsl(var(--text-secondary))]">
            A real Twilio call connected the bridge to Gemini Live and Charon spoke on the line —
            the call SID and recording below are re-checkable against the Twilio API.
          </p>
        </Reveal>

        <div className="mt-6 overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <tbody className="divide-y divide-[hsl(var(--border))]">
              {PROOF.map((p) => (
                <tr key={p.label}>
                  <td className="py-3 pr-4 text-[hsl(var(--text-secondary))]">{p.label}</td>
                  <td className="py-3 font-mono text-xs text-[hsl(var(--text-primary))] break-all">
                    {p.value}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section>
        <Reveal>
          <h2 className="font-display text-2xl md:text-3xl font-semibold text-[hsl(var(--text-primary))]">
            How B-call works (spec27c)
          </h2>
        </Reveal>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-[hsl(var(--border))] text-left">
                <th className="py-2 pr-4 font-semibold text-[hsl(var(--text-primary))]">Step</th>
                <th className="py-2 pr-4 font-semibold text-[hsl(var(--text-primary))]">
                  What Anicca does
                </th>
                <th className="py-2 font-semibold text-[hsl(var(--text-primary))]">API</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[hsl(var(--border))]">
              {STEPS.map((s) => (
                <tr key={s.n}>
                  <td className="py-3 pr-4 font-mono text-xs text-[hsl(var(--text-secondary))]">
                    {s.n}
                  </td>
                  <td className="py-3 pr-4 text-[hsl(var(--text-primary))]">{s.what}</td>
                  <td className="py-3 text-[hsl(var(--text-secondary))] font-mono text-xs">
                    {s.api}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

    </LaunchFrame>
  );
}
