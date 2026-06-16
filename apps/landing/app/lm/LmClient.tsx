'use client';

import { useCallback, useEffect, useState } from 'react';

// /lm onboarding island (spec28 P-lm-separate). Static-export safe: every call runs at
// runtime in the browser, nothing is server-rendered per-user (mirrors app/me/MeClient.tsx).
// Flow: Google login → ask name → connect gcal + Gmail (Composio managed OAuth) → ask phone
// → ready → dashboard. NO trial, $20/mo. UX taste: design-taste-frontend +
// nextlevelbuilder/ui-ux-pro-max-skill (premium, EN-only locale surface, no AI-slop).
//
// REAL connectors:
//   gcal  → /.netlify/functions/calendar-connect (EXISTING, returns {redirect_url}|{connected})
//   gmail → /.netlify/functions/gmail-connect     (NEW, mirrors calendar-connect, toolkit=gmail)
//   save  → /.netlify/functions/lm-onboard         (NEW, persists name+phone to Supabase)
//   pay   → $20/mo Stripe link (no trial) — see patch §3 for the exact `stripe` create cmd.

const GOOGLE_LOGIN_URL = '/.netlify/functions/lm-onboard?action=google-start';
const SAVE_URL = '/.netlify/functions/lm-onboard?action=save';
// Fail closed: NEVER ship a hardcoded/placeholder payment link. The Subscribe button is
// only rendered when a REAL Stripe link is injected at build time via NEXT_PUBLIC_STRIPE_LM_URL.
// If the env is unset, the button is hidden and the user sees a truthful "checkout not ready" note.
const STRIPE_LM_URL = process.env.NEXT_PUBLIC_STRIPE_LM_URL || '';
const PHONE_RE = /^\+?[1-9]\d{7,14}$/;
const STORAGE_KEY = 'anicca.lm.uid';
const SIG_KEY = 'anicca.lm.sig';

type Step = 'login' | 'name' | 'connect' | 'phone' | 'pay' | 'dashboard';
type ConnState = 'idle' | 'connecting' | 'connected' | 'error';

function StepDots({ step }: { step: Step }) {
  const order: Step[] = ['login', 'name', 'connect', 'phone', 'pay', 'dashboard'];
  const idx = order.indexOf(step);
  return (
    <div className="flex items-center gap-2" aria-label={`step ${idx + 1} of ${order.length}`}>
      {order.map((s, i) => (
        <span
          key={s}
          className={`h-1.5 rounded-full transition-all duration-300 ${
            i <= idx ? 'w-8 bg-[hsl(var(--gold))]' : 'w-3 bg-[hsl(var(--border))]'
          }`}
        />
      ))}
    </div>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto max-w-md rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-7 shadow-[0_1px_0_0_hsl(var(--border))]">
      {children}
    </div>
  );
}

export default function LmClient() {
  const [step, setStep] = useState<Step>('login');
  const [uid, setUid] = useState<string>('');
  const [sig, setSig] = useState<string>('');
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [cal, setCal] = useState<ConnState>('idle');
  const [gmail, setGmail] = useState<ConnState>('idle');
  const [err, setErr] = useState<string>('');

  // Resume: if Google login redirected back with ?uid=… (set by lm-onboard google-callback),
  // or a uid is saved, skip the login step.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const fromCb = params.get('uid');
    const fromSig = params.get('sig');
    const saved = window.localStorage.getItem(STORAGE_KEY);
    const savedSig = window.localStorage.getItem(SIG_KEY);
    const id = fromCb || saved || '';
    const s = fromSig || savedSig || '';
    if (!id) return;
    setUid(id);
    setSig(s);
    window.localStorage.setItem(STORAGE_KEY, id);
    if (s) window.localStorage.setItem(SIG_KEY, s);

    // Restore prior progress so the flow SURVIVES the Composio OAuth redirect (which reloads the
    // page and would otherwise wipe React state — the bug where nobody could reach the dashboard).
    let cal0 = (window.localStorage.getItem('anicca.lm.cal') as ConnState) || 'idle';
    let gmail0 = (window.localStorage.getItem('anicca.lm.gmail') as ConnState) || 'idle';
    const pending = window.localStorage.getItem('anicca.lm.pending'); // the connect we just sent to OAuth
    if (pending === 'gcal') cal0 = 'connected';
    if (pending === 'gmail') gmail0 = 'connected';
    window.localStorage.removeItem('anicca.lm.pending');
    setCal(cal0);
    setGmail(gmail0);
    const savedStep = window.localStorage.getItem('anicca.lm.step') as Step | null;
    setStep(savedStep && savedStep !== 'login' ? savedStep : 'name');
    // strip uid/sig from the visible URL so they don't leak via Referer/history
    window.history.replaceState(null, '', '/lm');
  }, []);

  // Persist progress (cal/gmail/step) so the OAuth redirect never strands the user mid-flow.
  useEffect(() => {
    if (!uid) return;
    try {
      window.localStorage.setItem('anicca.lm.cal', cal);
      window.localStorage.setItem('anicca.lm.gmail', gmail);
      window.localStorage.setItem('anicca.lm.step', step);
    } catch {}
  }, [uid, cal, gmail, step]);

  const login = useCallback(() => {
    // Real Google OAuth handoff (managed by lm-onboard google-start → Google consent → callback).
    window.location.href = `${GOOGLE_LOGIN_URL}&return=${encodeURIComponent(
      window.location.origin + '/lm',
    )}`;
  }, []);

  const saveName = useCallback(async () => {
    setErr('');
    if (!name.trim()) return setErr('Please enter your name.');
    try {
      await fetch(SAVE_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ uid, sig, name: name.trim() }),
      });
      setStep('connect');
    } catch (e) {
      setErr('Could not save. Try again.');
    }
  }, [name, uid, sig]);

  const connect = useCallback(
    async (kind: 'gcal' | 'gmail') => {
      const set = kind === 'gcal' ? setCal : setGmail;
      const fn = kind === 'gcal' ? 'calendar-connect' : 'gmail-connect';
      set('connecting');
      setErr('');
      try {
        const r = await fetch(
          `/.netlify/functions/${fn}?uid=${encodeURIComponent(uid)}&sig=${encodeURIComponent(sig)}`,
        );
        const d = await r.json();
        if (d.connected) return set('connected');
        if (d.redirect_url) {
          // one-click Google consent (Composio's verified app) — same tab, returns to /lm.
          // Mark which connect is in flight + stay on the connect step so resume restores it.
          try {
            window.localStorage.setItem('anicca.lm.pending', kind);
            window.localStorage.setItem('anicca.lm.step', 'connect');
          } catch {}
          window.location.href = d.redirect_url;
          return;
        }
        set('error');
        setErr(d.error || 'Connection failed.');
      } catch (e) {
        set('error');
        setErr('Connection failed.');
      }
    },
    [uid, sig],
  );

  const savePhone = useCallback(async () => {
    setErr('');
    if (!PHONE_RE.test(phone.trim()))
      return setErr('Enter a valid phone number in E.164 form, e.g. +818012345678.');
    try {
      await fetch(SAVE_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ uid, sig, phone: phone.trim() }),
      });
      setStep('pay');
    } catch (e) {
      setErr('Could not save. Try again.');
    }
  }, [phone, uid, sig]);

  // ── render ───────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      <StepDots step={step} />

      {step === 'login' && (
        <Shell>
          <h2 className="font-display text-xl font-semibold text-[hsl(var(--text-primary))]">
            Sign in to start
          </h2>
          <p className="mt-2 text-sm text-[hsl(var(--text-secondary))]">
            Life Manager keeps you on time by phone and email. $20/mo, no trial.
          </p>
          <button
            type="button"
            onClick={login}
            className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-pill bg-[hsl(var(--gold))] px-6 py-3 text-sm font-semibold text-[#18181b] transition-all hover:brightness-95 active:scale-[0.98]"
          >
            Continue with Google
          </button>
        </Shell>
      )}

      {step === 'name' && (
        <Shell>
          <h2 className="font-display text-xl font-semibold text-[hsl(var(--text-primary))]">
            What should Anicca call you?
          </h2>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Your name"
            className="mt-5 w-full rounded-input border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-4 py-3 text-sm text-[hsl(var(--text-primary))] outline-none focus:border-[hsl(var(--gold))]"
          />
          <button
            type="button"
            onClick={saveName}
            className="mt-5 inline-flex w-full items-center justify-center rounded-pill bg-[hsl(var(--gold))] px-6 py-3 text-sm font-semibold text-[#18181b] transition-all hover:brightness-95 active:scale-[0.98]"
          >
            Continue
          </button>
        </Shell>
      )}

      {step === 'connect' && (
        <Shell>
          <h2 className="font-display text-xl font-semibold text-[hsl(var(--text-primary))]">
            Connect your calendar &amp; email
          </h2>
          <p className="mt-2 text-sm text-[hsl(var(--text-secondary))]">
            One-click, managed OAuth via Composio. Anicca reads events and sends asks/late-notices.
          </p>
          <div className="mt-5 space-y-3">
            <ConnectRow label="Google Calendar" state={cal} onClick={() => connect('gcal')} />
            <ConnectRow label="Gmail" state={gmail} onClick={() => connect('gmail')} />
          </div>
          <button
            type="button"
            disabled={cal !== 'connected' || gmail !== 'connected'}
            onClick={() => setStep('phone')}
            className="mt-6 inline-flex w-full items-center justify-center rounded-pill bg-[hsl(var(--gold))] px-6 py-3 text-sm font-semibold text-[#18181b] transition-all hover:brightness-95 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40"
          >
            Continue
          </button>
        </Shell>
      )}

      {step === 'phone' && (
        <Shell>
          <h2 className="font-display text-xl font-semibold text-[hsl(var(--text-primary))]">
            Your phone number
          </h2>
          <p className="mt-2 text-sm text-[hsl(var(--text-secondary))]">
            Anicca calls 15 minutes before each event with route guidance.
          </p>
          <input
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            inputMode="tel"
            placeholder="+818012345678"
            className="mt-5 w-full rounded-input border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-4 py-3 text-sm text-[hsl(var(--text-primary))] outline-none focus:border-[hsl(var(--gold))]"
          />
          <button
            type="button"
            onClick={savePhone}
            className="mt-5 inline-flex w-full items-center justify-center rounded-pill bg-[hsl(var(--gold))] px-6 py-3 text-sm font-semibold text-[#18181b] transition-all hover:brightness-95 active:scale-[0.98]"
          >
            Continue
          </button>
        </Shell>
      )}

      {step === 'pay' && (
        <Shell>
          <h2 className="font-display text-xl font-semibold text-[hsl(var(--text-primary))]">
            You&apos;re set, {name || 'friend'}.
          </h2>
          <p className="mt-2 text-sm text-[hsl(var(--text-secondary))]">
            Subscribe to activate 24/7 management. <strong className="text-[hsl(var(--text-primary))]">$20/mo, no trial.</strong>
          </p>
          {STRIPE_LM_URL ? (
            <a
              href={`${STRIPE_LM_URL}?client_reference_id=${encodeURIComponent(uid)}`}
              className="mt-6 inline-flex w-full items-center justify-center rounded-pill bg-[hsl(var(--gold))] px-6 py-3 text-sm font-semibold text-[#18181b] transition-all hover:brightness-95 active:scale-[0.98]"
            >
              Subscribe — $20/mo
            </a>
          ) : (
            <p className="mt-6 rounded-input border border-[hsl(var(--border))] bg-[hsl(var(--surface-elevated))] px-4 py-3 text-center text-xs text-[hsl(var(--text-secondary))]">
              Checkout is being finalized — we&apos;ll email you the secure $20/mo link shortly.
            </p>
          )}
          <button
            type="button"
            onClick={() => setStep('dashboard')}
            className="mt-3 inline-flex w-full items-center justify-center text-xs text-[hsl(var(--text-secondary))] underline underline-offset-4"
          >
            See my dashboard
          </button>
        </Shell>
      )}

      {step === 'dashboard' && (
        <div className="space-y-4">
          <div className="rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-6">
            <p className="text-xs uppercase tracking-widest text-[hsl(var(--gold))]">
              your life manager
            </p>
            <p className="mt-1 text-lg font-semibold text-[hsl(var(--text-primary))]">
              {name || 'You'} — connected
            </p>
            <div className="mt-3 flex flex-wrap gap-2 text-xs">
              <Pill ok={cal === 'connected'}>Calendar</Pill>
              <Pill ok={gmail === 'connected'}>Gmail</Pill>
              <Pill ok={!!phone}>Phone</Pill>
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <SkillCard title="Travel blocks" desc="Travel time auto-inserted before every event." />
            <SkillCard title="15-min calls" desc="Anicca calls before each event with route guidance." />
            <SkillCard title="Location asks" desc="Missing location? Anicca emails you; your reply updates the event." />
            <SkillCard title="Late-notice" desc="Running late? Anicca drafts an attendee note; you approve, it sends." />
          </div>
          <p className="text-xs text-[hsl(var(--text-secondary))]">
            All four run 24/7 on Anicca&apos;s server. Live per-event telemetry lands here next.
          </p>
        </div>
      )}

      {err && <p className="text-sm text-red-400">{err}</p>}
    </div>
  );
}

function ConnectRow({
  label,
  state,
  onClick,
}: {
  label: string;
  state: ConnState;
  onClick: () => void;
}) {
  const connected = state === 'connected';
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={state === 'connecting' || connected}
      className={`flex w-full items-center justify-between rounded-input border px-4 py-3 text-sm transition-colors ${
        connected
          ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
          : 'border-[hsl(var(--border))] bg-[hsl(var(--background))] text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-elevated))]'
      }`}
    >
      <span>{label}</span>
      <span className="text-xs">
        {connected ? 'connected ✓' : state === 'connecting' ? 'connecting…' : 'connect →'}
      </span>
    </button>
  );
}

function Pill({ ok, children }: { ok: boolean; children: React.ReactNode }) {
  return (
    <span
      className={`rounded-full px-2.5 py-0.5 font-semibold ${
        ok
          ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20'
          : 'bg-[hsl(var(--surface-elevated))] text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))]'
      }`}
    >
      {children} {ok ? '✓' : '—'}
    </span>
  );
}

function SkillCard({ title, desc }: { title: string; desc: string }) {
  return (
    <div className="rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-4">
      <div className="flex items-center gap-2">
        <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-emerald-400 border border-emerald-500/20">
          live
        </span>
        <p className="text-sm font-semibold text-[hsl(var(--text-primary))]">{title}</p>
      </div>
      <p className="mt-1.5 text-xs text-[hsl(var(--text-secondary))] leading-relaxed">{desc}</p>
    </div>
  );
}
