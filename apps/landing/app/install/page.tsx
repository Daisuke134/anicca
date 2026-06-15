/* eslint-disable react/no-unescaped-entities */
'use client';

import { useState } from 'react';
import Link from 'next/link';
import JsonLd from '@/components/JsonLd';
import Navbar from '@/components/site/Navbar';
import LaunchNav from '@/components/site/LaunchNav';
import Footer from '@/components/site/Footer';
import { SplitHero, Section, Reveal, CTA } from '@/components/site/taste';

export const dynamic = 'force-static';

const installLd = {
  '@context': 'https://schema.org',
  '@type': 'TechArticle',
  name: 'Install Anicca',
  url: 'https://aniccaai.com/install',
  description:
    'Install Anicca - autonomous Buddhist AI that runs as a daemon on your always-on machine. Paste one prompt into Claude Code / Cursor / Aider, or run install.sh manually.',
  publisher: { '@type': 'Organization', name: 'Anicca', url: 'https://aniccaai.com' },
};

const PATH_A_PROMPT = `You are installing Anicca on this machine.

  1. git clone https://github.com/Daisuke134/anicca-oss ~/anicca-oss
  2. Read ~/anicca-oss/docs/INSTALL_BOOTSTRAP.md and follow it
     step-by-step.
  3. The user is lazy. Ask ONE thing at a time. Stop and wait for
     each answer before continuing.
  4. Never paste any answer back. Write everything to
     ~/.openclaw/.env (chmod 600). Never push that file anywhere.
  5. When the install finishes, hand the user a Telegram deep-link
     (t.me/<their-bot-username>?start=onboard) and stop.`;

const PATH_B_SH = `git clone https://github.com/Daisuke134/anicca-oss ~/anicca-oss
cd ~/anicca-oss
bash install.sh`;

function Copy({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          setTimeout(() => setCopied(false), 2000);
        } catch {}
      }}
      className="inline-flex items-center gap-2 rounded-input border border-[hsl(var(--border))] bg-[hsl(var(--surface))] px-3 py-1.5 text-xs font-medium text-[hsl(var(--text-primary))] transition-colors hover:bg-[hsl(var(--surface-elevated))]"
      aria-label={label}
    >
      {copied ? '✓ copied' : '📋 copy'}
    </button>
  );
}

export default function Page() {
  return (
    <>
      <JsonLd data={installLd} />
      <LaunchNav active="/install" />
      <Navbar locale="en" />

      <SplitHero
        headline="Install Anicca"
        subtext="Autonomous Buddhist AI daemon. Paste one prompt into Claude Code or Cursor - Anicca spins up its own server."
        primary={
          <CTA href="https://github.com/Daisuke134/anicca-oss" variant="primary">
            Open GitHub
          </CTA>
        }
        secondary={
          <a
            href="#path-b"
            className="text-sm font-medium underline underline-offset-4 text-[hsl(var(--text-secondary))] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--gold))]"
          >
            Run install.sh manually
          </a>
        }
        asset={
          <div className="rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface-elevated))] p-6 font-mono text-sm text-[hsl(var(--text-secondary))] leading-relaxed">
            <p className="text-[hsl(var(--gold))] font-semibold mb-2">$ git clone anicca-oss</p>
            <p>installing skills...</p>
            <p>wiring crons...</p>
            <p>registering wallet...</p>
            <p className="text-[hsl(var(--text-primary))] mt-2">Anicca is live.</p>
          </div>
        }
      />

      <Section>
        <Reveal>
          <h2 className="font-display text-2xl md:text-3xl font-semibold text-[hsl(var(--text-primary))]">
            Path A - paste into your coding agent (approx. 30 sec)
          </h2>
          <p className="mt-2 text-sm text-[hsl(var(--text-secondary))]">
            Recommended if you already have <b>Claude Code</b>, <b>Codex CLI</b>,{' '}
            <b>Cursor</b>, or <b>Aider</b> running on the machine that should host Anicca.
          </p>
          <div className="mt-4 rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))]">
            <div className="flex items-center justify-between border-b border-[hsl(var(--border))] px-4 py-2">
              <span className="text-xs uppercase tracking-widest text-[hsl(var(--text-secondary))]">paste into your agent</span>
              <Copy text={PATH_A_PROMPT} label="Copy Path A install prompt" />
            </div>
            <pre className="overflow-x-auto whitespace-pre-wrap px-4 py-4 text-[13px] leading-relaxed text-[hsl(var(--text-primary))]">{PATH_A_PROMPT}</pre>
          </div>
          <p className="mt-3 text-xs text-[hsl(var(--text-secondary))]">
            Your agent will ask you for: an LLM key (Anthropic / OpenAI / DeepSeek),
            a Telegram bot token (BotFather), a Twilio number for the wake-up
            calls, a Google Directions API key, and optionally a USDC wallet
            private key for self-fueling. Everything is written to{' '}
            <code className="rounded-input bg-[hsl(var(--surface-elevated))] px-1 py-0.5">~/.openclaw/.env</code> with{' '}
            <code className="rounded-input bg-[hsl(var(--surface-elevated))] px-1 py-0.5">chmod 600</code>. Nothing is uploaded.
          </p>
        </Reveal>
      </Section>

      <Section id="path-b">
        <Reveal>
          <h2 className="font-display text-2xl md:text-3xl font-semibold text-[hsl(var(--text-primary))]">
            Path B - manual shell
          </h2>
          <p className="mt-2 text-sm text-[hsl(var(--text-secondary))]">
            If you don't have an agent installed, run this on the host machine.
          </p>
          <div className="mt-4 rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))]">
            <div className="flex items-center justify-between border-b border-[hsl(var(--border))] px-4 py-2">
              <span className="text-xs uppercase tracking-widest text-[hsl(var(--text-secondary))]">terminal</span>
              <Copy text={PATH_B_SH} label="Copy Path B install commands" />
            </div>
            <pre className="overflow-x-auto px-4 py-4 text-[13px] leading-relaxed text-[hsl(var(--text-primary))]">{PATH_B_SH}</pre>
          </div>
          <p className="mt-3 text-xs text-[hsl(var(--text-secondary))]">
            <code className="rounded-input bg-[hsl(var(--surface-elevated))] px-1 py-0.5">install.sh</code> creates{' '}
            <code className="rounded-input bg-[hsl(var(--surface-elevated))] px-1 py-0.5">~/.openclaw/</code>, copies{' '}
            <code className="rounded-input bg-[hsl(var(--surface-elevated))] px-1 py-0.5">.env.example</code> for you to
            fill, symlinks the skills, installs launchd plists for the Telegram
            location bridge + Pipecat phone daemon, and registers the openclaw
            cron jobs (with quiet hours 23:30 - 05:30 already wired).
          </p>
        </Reveal>
      </Section>

      <Section>
        <Reveal>
          <h2 className="font-display text-2xl md:text-3xl font-semibold text-[hsl(var(--text-primary))]">
            After install
          </h2>
          <ol className="mt-4 list-decimal space-y-3 pl-6 text-sm text-[hsl(var(--text-primary))]">
            <li>Open Telegram on your phone.</li>
            <li>Open the chat with the bot you created (<code className="rounded-input bg-[hsl(var(--surface-elevated))] px-1 py-0.5">t.me/&lt;your-bot-username&gt;</code>).</li>
            <li>Send <code className="rounded-input bg-[hsl(var(--surface-elevated))] px-1 py-0.5">/start</code>.</li>
            <li>
              Anicca asks you four things, one at a time:
              <ul className="mt-2 list-disc space-y-1 pl-5 text-[hsl(var(--text-secondary))]">
                <li>What name should she call you on the phone.</li>
                <li>Your phone number in E.164 (e.g. <code className="rounded-input bg-[hsl(var(--surface-elevated))] px-1 py-0.5">+819012345678</code>).</li>
                <li>Tap <b>Share Live Location</b> in the attachment menu - Location - <b>Share My Live Location</b> - 8 hours (or <i>Until I turn it off</i>).</li>
                <li>Google Calendar OAuth (the link she gives you opens an in-app browser).</li>
              </ul>
            </li>
            <li>When all four are done, Anicca says <b>"Onboarding complete. Next wake-up at 07:00."</b></li>
          </ol>
        </Reveal>
      </Section>

      <Section>
        <Reveal>
          <div className="grid gap-4 md:grid-cols-2">
            <Link
              href="https://github.com/Daisuke134/anicca-oss"
              target="_blank"
              rel="noreferrer"
              className="block rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-5 transition-colors hover:bg-[hsl(var(--surface-elevated))]"
            >
              <p className="text-xs uppercase tracking-widest text-[hsl(var(--text-secondary))]">source</p>
              <p className="mt-2 text-base font-semibold text-[hsl(var(--text-primary))]">github.com/Daisuke134/anicca-oss</p>
              <p className="mt-1 text-xs text-[hsl(var(--text-secondary))]">MIT. No human-author credit; reuse however you like.</p>
            </Link>
            <Link
              href="/dashboard"
              className="block rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-5 transition-colors hover:bg-[hsl(var(--surface-elevated))]"
            >
              <p className="text-xs uppercase tracking-widest text-[hsl(var(--text-secondary))]">live ledger</p>
              <p className="mt-2 text-base font-semibold text-[hsl(var(--text-primary))]">aniccaai.com/dashboard</p>
              <p className="mt-1 text-xs text-[hsl(var(--text-secondary))]">All Anicca instances' real-time revenue, spend, and lifeline.</p>
            </Link>
          </div>
        </Reveal>
      </Section>

      <Section>
        <Reveal>
          <h2 className="font-display text-2xl md:text-3xl font-semibold text-[hsl(var(--text-primary))]">
            Authentication options
          </h2>
          <p className="mt-2 text-sm text-[hsl(var(--text-secondary))]">
            Anicca needs compute to run. You pick the substrate:
          </p>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-[hsl(var(--border))] text-left">
                  <th className="py-2 pr-4 font-semibold text-[hsl(var(--text-primary))]">Substrate</th>
                  <th className="py-2 pr-4 font-semibold text-[hsl(var(--text-primary))]">Set it via</th>
                  <th className="py-2 font-semibold text-[hsl(var(--text-primary))]">Anicca's behavior</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[hsl(var(--border))]">
                <tr>
                  <td className="py-3 pr-4 text-[hsl(var(--text-primary))]">LLM subscription</td>
                  <td className="py-3 pr-4 text-[hsl(var(--text-primary))]">Existing Claude Max / ChatGPT Plus session on this Mac</td>
                  <td className="py-3 text-[hsl(var(--text-secondary))]">Free for you while subscription is active. Anicca routes through the local agent.</td>
                </tr>
                <tr>
                  <td className="py-3 pr-4 text-[hsl(var(--text-primary))]">API key</td>
                  <td className="py-3 pr-4 text-[hsl(var(--text-primary))]">
                    <code className="rounded-input bg-[hsl(var(--surface-elevated))] px-1 py-0.5">ANTHROPIC_API_KEY</code> /{' '}
                    <code className="rounded-input bg-[hsl(var(--surface-elevated))] px-1 py-0.5">OPENAI_API_KEY</code> /{' '}
                    <code className="rounded-input bg-[hsl(var(--surface-elevated))] px-1 py-0.5">DEEPSEEK_API_KEY</code>{' '}
                    in <code className="rounded-input bg-[hsl(var(--surface-elevated))] px-1 py-0.5">~/.openclaw/.env</code>
                  </td>
                  <td className="py-3 text-[hsl(var(--text-secondary))]">Anicca calls the provider directly.</td>
                </tr>
                <tr>
                  <td className="py-3 pr-4 text-[hsl(var(--text-primary))]">Wallet (self-fueling)</td>
                  <td className="py-3 pr-4 text-[hsl(var(--text-primary))]">
                    Send USDC on Base to her wallet address (printed by{' '}
                    <code className="rounded-input bg-[hsl(var(--surface-elevated))] px-1 py-0.5">bash scripts/fuel-usdc.sh</code>)
                  </td>
                  <td className="py-3 text-[hsl(var(--text-secondary))]">Anicca buys her own OpenRouter credit. No human in the loop after the initial send.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </Reveal>
      </Section>

      <Section>
        <Reveal>
          <h2 className="font-display text-2xl md:text-3xl font-semibold text-[hsl(var(--text-primary))]">
            Quiet hours
          </h2>
          <p className="mt-2 text-sm text-[hsl(var(--text-secondary))]">
            Wake-up + lateness calls never fire between 23:30 and 05:30 local
            time, regardless of calendar contents. Adjust in{' '}
            <code className="rounded-input bg-[hsl(var(--surface-elevated))] px-1 py-0.5">profile.alarm.quietHoursStart</code> /{' '}
            <code className="rounded-input bg-[hsl(var(--surface-elevated))] px-1 py-0.5">quietHoursEnd</code>.
          </p>
        </Reveal>
      </Section>

      <Section>
        <Reveal>
          <div className="border-t border-[hsl(var(--border))] pt-8 text-xs text-[hsl(var(--text-secondary))]">
            <p>
              MIT license. No human-author credit block - Anicca authored this
              project and continues to.
            </p>
            <p className="mt-2">
              If you find a leaked secret in this repo or in any production
              surface, see{' '}
              <Link
                href="https://github.com/Daisuke134/anicca-oss/blob/main/SECURITY.md"
                className="underline transition-colors hover:text-[hsl(var(--text-primary))]"
              >
                SECURITY.md
              </Link>
              .
            </p>
          </div>
        </Reveal>
      </Section>

      <Footer locale="en" />
    </>
  );
}
