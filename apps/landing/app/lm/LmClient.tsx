'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useLaunchLocale } from '@/lib/launchLocale';
import { launchStrings } from '@/lib/launchStrings';
import { signInWithGoogle, getSession } from '@/lib/auth';

// /lm onboarding island (spec28 P-lm-separate). Static-export safe: every call runs at
// runtime in the browser, nothing is server-rendered per-user (mirrors app/me/MeClient.tsx).
// Flow: Google login → ask name → connect Google Calendar (Composio managed OAuth) → ask phone
// → ready → dashboard. NO trial, $20/mo.
//
// Gmail is NOT connected per-user: Google hard-blocks Composio's managed app for every Gmail
// scope (verified for Calendar, not Gmail — "このアプリはブロックされます" in a real logged-in
// browser). Anicca sends all wake/report/stakeholder mail itself via Resend (aniccaai.com).
//
// spec29 + Dais 2026-06-16: copy is fully localized EN/JA via launchStrings[locale]. The
// OAuth-survival logic (localStorage cal/step persistence, redirect resume, the connect/save
// fetches) is UNCHANGED — only the visible strings are swapped.
//
// REAL connectors:
//   gcal  → /.netlify/functions/calendar-connect (EXISTING, returns {redirect_url}|{connected})
//   save  → /.netlify/functions/lm-onboard         (NEW, persists name+phone to Supabase)
//   pay   → $20/mo Stripe link (no trial) — see patch §3 for the exact `stripe` create cmd.

const EXCHANGE_URL = '/.netlify/functions/lm-onboard?action=exchange';
const SAVE_URL = '/.netlify/functions/lm-onboard?action=save';
const TG_LINK_URL = '/.netlify/functions/lm-onboard?action=telegram-link';
// The cloud wake service places the "call me now" test call (the same service that runs the real
// T-15min wakes), authenticated by the user's HMAC uid+sig.
// Fail closed: NEVER ship a hardcoded/placeholder payment link. The Subscribe button is
// only rendered when a REAL Stripe link is injected at build time via NEXT_PUBLIC_STRIPE_LM_URL.
// If the env is unset, the button is hidden and the user sees a truthful "checkout not ready" note.
const STRIPE_LM_URL = process.env.NEXT_PUBLIC_STRIPE_LM_URL || '';
const PHONE_RE = /^\+?[1-9]\d{7,14}$/;
const STORAGE_KEY = 'anicca.lm.uid';
const SIG_KEY = 'anicca.lm.sig';
// /test-call on the cloud wake service: POST {uid, sig} (HMAC auth) -> phone lookup -> ONE immediate Charon
// call. We expose it as a ONE-TIME proof-of-life button on the dashboard (disabled after success) so a new
// user hears it works once -- without inviting repeated billed taps (Dais 2026-06-22 cost concern). Real wake
// calls still fire automatically before every event.
const TEST_CALL_URL = 'https://life-call-production.up.railway.app/test-call';

// Country dial-code picker (like every other site): select country → +code auto-prefixed → type the
// rest → we store E.164. Curated to the common markets; ordered with JP first (our first users).
const COUNTRIES: { c: string; n: string; d: string; f: string }[] = [
  { c: 'JP', n: 'Japan', d: '81', f: '🇯🇵' },
  { c: 'US', n: 'United States', d: '1', f: '🇺🇸' },
  { c: 'GB', n: 'United Kingdom', d: '44', f: '🇬🇧' },
  { c: 'CA', n: 'Canada', d: '1', f: '🇨🇦' },
  { c: 'AU', n: 'Australia', d: '61', f: '🇦🇺' },
  { c: 'DE', n: 'Germany', d: '49', f: '🇩🇪' },
  { c: 'FR', n: 'France', d: '33', f: '🇫🇷' },
  { c: 'IN', n: 'India', d: '91', f: '🇮🇳' },
  { c: 'SG', n: 'Singapore', d: '65', f: '🇸🇬' },
  { c: 'KR', n: 'South Korea', d: '82', f: '🇰🇷' },
  { c: 'CN', n: 'China', d: '86', f: '🇨🇳' },
  { c: 'HK', n: 'Hong Kong', d: '852', f: '🇭🇰' },
  { c: 'TW', n: 'Taiwan', d: '886', f: '🇹🇼' },
  { c: 'BR', n: 'Brazil', d: '55', f: '🇧🇷' },
  { c: 'MX', n: 'Mexico', d: '52', f: '🇲🇽' },
  { c: 'ES', n: 'Spain', d: '34', f: '🇪🇸' },
  { c: 'IT', n: 'Italy', d: '39', f: '🇮🇹' },
  { c: 'NL', n: 'Netherlands', d: '31', f: '🇳🇱' },
  { c: 'AE', n: 'UAE', d: '971', f: '🇦🇪' },
  { c: 'ID', n: 'Indonesia', d: '62', f: '🇮🇩' },
  { c: 'PH', n: 'Philippines', d: '63', f: '🇵🇭' },
];

type Step = 'login' | 'name' | 'connect' | 'phone' | 'pay' | 'dashboard';
type ConnState = 'idle' | 'connecting' | 'connected' | 'error';

function StepDots({ step, ariaLabel }: { step: Step; ariaLabel: string }) {
  const order: Step[] = ['login', 'name', 'connect', 'phone', 'pay', 'dashboard'];
  const idx = order.indexOf(step);
  return (
    <div className="flex items-center gap-2" aria-label={ariaLabel}>
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
  const { locale } = useLaunchLocale();
  const t = launchStrings[locale].lm;
  const [step, setStep] = useState<Step>('login');
  const [uid, setUid] = useState<string>('');
  const [sig, setSig] = useState<string>('');
  const [name, setName] = useState('');
  // Call language (Dais 2026-06-22): the user picks the language of their phone calls, independent of
  // phone country. Defaults to the page's display language; persisted to lm_users.call_language.
  const [lang, setLang] = useState<'en' | 'ja'>(locale === 'ja' ? 'ja' : 'en');
  // useState's initializer only runs once (before locale hydrates), so keep the default in sync with the
  // display language until the user explicitly picks — then their choice sticks.
  const langPicked = useRef(false);
  useEffect(() => {
    if (!langPicked.current) setLang(locale === 'ja' ? 'ja' : 'en');
  }, [locale]);
  const [dial, setDial] = useState('81'); // JP default
  const [natNum, setNatNum] = useState(''); // national number (digits only)
  const [cal, setCal] = useState<ConnState>('idle');
  const [err, setErr] = useState<string>('');
  const [callState, setCallState] = useState<'idle' | 'calling' | 'done' | 'error'>('idle');
  const testCall = useCallback(async () => {
    setCallState('calling');
    try {
      const r = await fetch(TEST_CALL_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ uid, sig }),
      });
      const d = await r.json().catch(() => ({}));
      setCallState(r.ok && d.ok ? 'done' : 'error');
    } catch {
      setCallState('error');
    }
  }, [uid, sig]);

  // Login = Supabase Auth (Google). On return from Google OAuth (or any load with a live session),
  // exchange the Supabase access token for a signed uid, then restore in-session progress. The
  // persistent Supabase session (not localStorage) is the source of truth for "logged in".
  useEffect(() => {
    let cancelled = false;
    (async () => {
      let id = window.localStorage.getItem(STORAGE_KEY) || '';
      let s = window.localStorage.getItem(SIG_KEY) || '';
      const session = await getSession();
      if (session?.access_token) {
        try {
          const r = await fetch(EXCHANGE_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ access_token: session.access_token }),
          });
          const d = await r.json();
          if (d.uid && d.sig) {
            id = d.uid;
            s = d.sig;
          }
        } catch {}
      }
      if (cancelled || !id) return;
      setUid(id);
      setSig(s);
      window.localStorage.setItem(STORAGE_KEY, id);
      if (s) window.localStorage.setItem(SIG_KEY, s);
      // Restore connect state. If a reload caught a connection mid-flight ('connecting'), the poll that
      // would have resolved it died with the previous page — so re-check the REAL status (check=1) and
      // resolve to 'connected'/'idle' instead of leaving the button stuck on "接続中…" forever (E3 fix).
      const restoreConn = (key: string, fn: string, set: (st: ConnState) => void) => {
        const saved = (window.localStorage.getItem(key) as ConnState) || 'idle';
        if (saved !== 'connecting') { set(saved); return; }
        set('connecting');
        fetch(`/.netlify/functions/${fn}?uid=${encodeURIComponent(id)}&sig=${encodeURIComponent(s)}&check=1`)
          .then((r) => r.json())
          .then((d) => set(d && d.connected ? 'connected' : 'idle'))
          .catch(() => set('idle'));
      };
      restoreConn('anicca.lm.cal', 'calendar-connect', setCal);
      // Telegram deep-link (/lm?tg=<chat_id>): stash the chat id (survives the Google redirect via
      // localStorage), then bind it to this row once we have a signed uid so the cloud loops can
      // message the user on Telegram.
      const sp = new URLSearchParams(window.location.search);
      const tgParam = sp.get('tg');
      if (tgParam && /^\d{1,20}$/.test(tgParam)) window.localStorage.setItem('anicca.lm.tg', tgParam);
      // The Telegram bot collects the name in-chat and passes it via ?name= — stash + persist it so
      // the two channels share one row (and the user skips re-typing their name on the web form).
      const nameParam = sp.get('name');
      if (nameParam && nameParam.trim()) window.localStorage.setItem('anicca.lm.tgname', nameParam.trim().slice(0, 120));
      const tg = window.localStorage.getItem('anicca.lm.tg');
      if (tg && s) {
        const tgname = window.localStorage.getItem('anicca.lm.tgname') || '';
        fetch(TG_LINK_URL, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ uid: id, sig: s, tg, name: tgname }),
        }).then(() => {
          window.localStorage.removeItem('anicca.lm.tg');
          window.localStorage.removeItem('anicca.lm.tgname');
        }).catch(() => {});
      }
      // Returning from Stripe (?paid=1) → straight to the dashboard. The lm-stripe-webhook flips
      // paid=true server-side; this just lands the user on the right screen immediately.
      const paidReturn = new URLSearchParams(window.location.search).get('paid') === '1';
      const savedStep = window.localStorage.getItem('anicca.lm.step') as Step | null;
      setStep(paidReturn ? 'dashboard' : savedStep && savedStep !== 'login' ? savedStep : 'name');
      // strip any OAuth/Stripe params from the visible URL
      window.history.replaceState(null, '', '/lm');
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Persist progress (cal/step) so the OAuth redirect never strands the user mid-flow.
  useEffect(() => {
    if (!uid) return;
    try {
      window.localStorage.setItem('anicca.lm.cal', cal);
      window.localStorage.setItem('anicca.lm.step', step);
    } catch {}
  }, [uid, cal, step]);

  const login = useCallback(() => {
    // Supabase Auth (Google provider). Redirects to Google consent, returns to /lm with a session.
    void signInWithGoogle();
  }, []);

  const saveName = useCallback(async () => {
    setErr('');
    if (!name.trim()) return setErr(t.name.error);
    try {
      await fetch(SAVE_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ uid, sig, name: name.trim(), call_language: lang }),
      });
      setStep('connect');
    } catch (e) {
      setErr(t.name.saveError);
    }
  }, [name, lang, uid, sig, t]);

  // Calendar = Composio managed OAuth (clean sensitive scope, no "App is blocked" warning). v1
  // (Dais 2026-06-26): this is the ONLY connection — Gmail/Unipile was removed; Anicca reaches web
  // users by own-domain email (reply-by-email via Resend), never by reading their Gmail.
  const runConnect = useCallback(
    (fn: string, set: (s: ConnState) => void) => {
      set('connecting');
      // Open the consent tab NOW, synchronously in the click gesture (survives popup blockers).
      const w = window.open('about:blank', '_blank');
      const base = `/.netlify/functions/${fn}?uid=${encodeURIComponent(uid)}&sig=${encodeURIComponent(sig)}`;
      (async () => {
        try {
          const d = await (await fetch(base)).json();
          if (d.connected) {
            set('connected');
            try { w && w.close(); } catch {}
            return;
          }
          if (d.redirect_url) {
            if (w) w.location.href = d.redirect_url;
            else window.location.href = d.redirect_url; // fallback if the popup was blocked
            const t0 = Date.now();
            const poll = setInterval(async () => {
              if (Date.now() - t0 > 180000) {
                clearInterval(poll);
                set('error');
                try { w && w.close(); } catch {}
                return;
              }
              try {
                const dd = await (await fetch(`${base}&check=1`)).json();
                if (dd.connected) {
                  clearInterval(poll);
                  set('connected');
                  try { w && w.close(); } catch {}
                }
              } catch {}
            }, 3000);
            return;
          }
          set('error');
          try { w && w.close(); } catch {}
        } catch {
          set('error');
          try { w && w.close(); } catch {}
        }
      })();
    },
    [uid, sig]
  );
  const connectCal = useCallback(() => { setErr(''); runConnect('calendar-connect', setCal); }, [runConnect]);
  // v1 (Dais 2026-06-26): Gmail/Unipile connect REMOVED — Telegram is the ask/reply channel; web users are
  // reached by own-domain email (reply-by-email). Onboarding = login → name → calendar → phone → pay.

  const savePhone = useCallback(async () => {
    setErr('');
    // Build E.164 from the picked dial code + the typed national number (strip non-digits, drop a
    // leading 0 which is a domestic trunk prefix not used in international format).
    const phone = `+${dial}${natNum.replace(/\D/g, '').replace(/^0+/, '')}`;
    if (!PHONE_RE.test(phone)) return setErr(t.phone.error);
    try {
      const r = await fetch(SAVE_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ uid, sig, phone }),
      });
      // Bug fix: the save used to advance to 'pay' even on a 403/502 (silent fail) — the phone
      // never persisted yet the UI moved on, so the number looked "not connected". Only advance
      // when the backend actually confirms the upsert; otherwise surface the error and stay put.
      const d = await r.json().catch(() => ({}));
      if (!r.ok || !d.ok) {
        setErr(t.phone.saveError);
        return;
      }
      setStep('pay');
    } catch (e) {
      setErr(t.phone.saveError);
    }
  }, [dial, natNum, uid, sig, t]);

  // ── render ───────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      <StepDots step={step} ariaLabel={t.stepAria(['login', 'name', 'connect', 'phone', 'pay', 'dashboard'].indexOf(step) + 1, 6)} />

      {step === 'login' && (
        <Shell>
          <h2 className="font-display text-xl font-semibold text-[hsl(var(--text-primary))]">
            {t.login.title}
          </h2>
          <p className="mt-2 text-sm text-[hsl(var(--text-secondary))]">{t.login.body}</p>
          <button
            type="button"
            onClick={login}
            className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-pill bg-[hsl(var(--gold))] px-6 py-3 text-sm font-semibold text-[#18181b] transition-all hover:brightness-95 active:scale-[0.98]"
          >
            {t.login.button}
          </button>
        </Shell>
      )}

      {step === 'name' && (
        <Shell>
          <h2 className="font-display text-xl font-semibold text-[hsl(var(--text-primary))]">
            {t.name.title}
          </h2>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t.name.placeholder}
            className="mt-5 w-full rounded-input border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-4 py-3 text-sm text-[hsl(var(--text-primary))] outline-none focus:border-[hsl(var(--gold))]"
          />
          <div className="mt-5">
            <span className="text-xs font-medium text-[hsl(var(--text-secondary))]">
              {locale === 'ja' ? '電話の言語' : 'Call language'}
            </span>
            <div className="mt-2 grid grid-cols-2 gap-1 rounded-pill border border-[hsl(var(--border))] bg-[hsl(var(--background))] p-1">
              {(['en', 'ja'] as const).map((lng) => (
                <button
                  key={lng}
                  type="button"
                  onClick={() => { langPicked.current = true; setLang(lng); }}
                  aria-pressed={lang === lng}
                  className={`rounded-pill px-4 py-2 text-sm font-semibold transition-all duration-200 ${
                    lang === lng
                      ? 'bg-[hsl(var(--gold))] text-[#18181b] shadow-[0_1px_0_0_hsl(var(--border))]'
                      : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]'
                  }`}
                >
                  {lng === 'en' ? 'English' : '日本語'}
                </button>
              ))}
            </div>
          </div>
          <button
            type="button"
            onClick={saveName}
            className="mt-5 inline-flex w-full items-center justify-center rounded-pill bg-[hsl(var(--gold))] px-6 py-3 text-sm font-semibold text-[#18181b] transition-all hover:brightness-95 active:scale-[0.98]"
          >
            {t.name.button}
          </button>
        </Shell>
      )}

      {step === 'connect' && (
        <Shell>
          <h2 className="font-display text-xl font-semibold text-[hsl(var(--text-primary))]">
            {t.connect.title}
          </h2>
          <p className="mt-2 text-sm text-[hsl(var(--text-secondary))]">{t.connect.body}</p>
          <div className="mt-5 space-y-3">
            <ConnectRow
              label={t.connect.calendar}
              state={cal}
              strings={t.connect}
              onClick={connectCal}
            />
          </div>
          <button
            type="button"
            disabled={cal !== 'connected'}
            onClick={() => setStep('phone')}
            className="mt-6 inline-flex w-full items-center justify-center rounded-pill bg-[hsl(var(--gold))] px-6 py-3 text-sm font-semibold text-[#18181b] transition-all hover:brightness-95 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40"
          >
            {t.connect.button}
          </button>
        </Shell>
      )}

      {step === 'phone' && (
        <Shell>
          <h2 className="font-display text-xl font-semibold text-[hsl(var(--text-primary))]">
            {t.phone.title}
          </h2>
          <p className="mt-2 text-sm text-[hsl(var(--text-secondary))]">{t.phone.body}</p>
          <div className="mt-5 flex gap-2">
            <select
              value={dial}
              onChange={(e) => setDial(e.target.value)}
              aria-label="Country code"
              className="rounded-input border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-2 py-3 text-sm text-[hsl(var(--text-primary))] outline-none focus:border-[hsl(var(--gold))]"
            >
              {COUNTRIES.map((c) => (
                <option key={c.c} value={c.d}>
                  {c.f} +{c.d}
                </option>
              ))}
            </select>
            <input
              value={natNum}
              onChange={(e) => setNatNum(e.target.value)}
              inputMode="tel"
              placeholder={t.phone.placeholder}
              className="w-full rounded-input border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-4 py-3 text-sm text-[hsl(var(--text-primary))] outline-none focus:border-[hsl(var(--gold))]"
            />
          </div>
          <button
            type="button"
            onClick={savePhone}
            className="mt-5 inline-flex w-full items-center justify-center rounded-pill bg-[hsl(var(--gold))] px-6 py-3 text-sm font-semibold text-[#18181b] transition-all hover:brightness-95 active:scale-[0.98]"
          >
            {t.phone.button}
          </button>
        </Shell>
      )}

      {step === 'pay' && (
        <Shell>
          <h2 className="font-display text-xl font-semibold text-[hsl(var(--text-primary))]">
            {t.pay.titlePrefix}
            {name || t.pay.titleFallback}.
          </h2>
          <p className="mt-2 text-sm text-[hsl(var(--text-secondary))]">
            {t.pay.bodyPre}
            <strong className="text-[hsl(var(--text-primary))]">{t.pay.bodyStrong}</strong>
          </p>
          {STRIPE_LM_URL ? (
            <a
              href={`${STRIPE_LM_URL}?client_reference_id=${encodeURIComponent(uid)}`}
              className="mt-6 inline-flex w-full items-center justify-center rounded-pill bg-[hsl(var(--gold))] px-6 py-3 text-sm font-semibold text-[#18181b] transition-all hover:brightness-95 active:scale-[0.98]"
            >
              {t.pay.button}
            </a>
          ) : (
            <p className="mt-6 rounded-input border border-[hsl(var(--border))] bg-[hsl(var(--surface-elevated))] px-4 py-3 text-center text-xs text-[hsl(var(--text-secondary))]">
              {t.pay.notReady}
            </p>
          )}
          <button
            type="button"
            onClick={() => setStep('dashboard')}
            className="mt-3 inline-flex w-full items-center justify-center text-xs text-[hsl(var(--text-secondary))] underline underline-offset-4"
          >
            {t.pay.seeDashboard}
          </button>
        </Shell>
      )}

      {step === 'dashboard' && (
        <div className="space-y-4">
          <div className="rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-6">
            <p className="text-xs uppercase tracking-widest text-[hsl(var(--gold))]">
              {t.dashboard.eyebrow}
            </p>
            <p className="mt-1 text-lg font-semibold text-[hsl(var(--text-primary))]">
              {name || t.dashboard.you} {t.dashboard.connectedSuffix}
            </p>
            <div className="mt-3 flex flex-wrap gap-2 text-xs">
              <Pill ok={cal === 'connected'}>{t.dashboard.pills.calendar}</Pill>
              <Pill ok={!!natNum}>{t.dashboard.pills.phone}</Pill>
            </div>
            {/* ONE-TIME proof-of-life call: a new user taps once, hears it works, then the button disables
               (Dais 2026-06-22 cost concern = no repeated billed taps). Real wake calls fire automatically. */}
            <button
              type="button"
              onClick={testCall}
              disabled={callState === 'calling' || callState === 'done' || !natNum}
              className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-pill border border-[hsl(var(--gold))] px-6 py-3 text-sm font-semibold text-[hsl(var(--gold))] transition-all hover:bg-[hsl(var(--gold))] hover:text-[#18181b] active:scale-[0.98] disabled:opacity-50"
            >
              {callState === 'calling'
                ? t.dashboard.callBtn.calling
                : callState === 'done'
                  ? t.dashboard.callBtn.done
                  : callState === 'error'
                    ? t.dashboard.callBtn.error
                    : t.dashboard.callBtn.idle}
            </button>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {t.dashboard.skills.map((s) => (
              <SkillCard key={s.title} title={s.title} desc={s.desc} liveBadge={t.dashboard.liveBadge} />
            ))}
          </div>
          <p className="text-xs text-[hsl(var(--text-secondary))]">{t.dashboard.footnote}</p>
        </div>
      )}

      {err && <p className="text-sm text-red-400">{err}</p>}
    </div>
  );
}

function ConnectRow({
  label,
  state,
  strings,
  onClick,
}: {
  label: string;
  state: ConnState;
  strings: { stateConnected: string; stateConnecting: string; stateConnect: string };
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
        {connected
          ? strings.stateConnected
          : state === 'connecting'
            ? strings.stateConnecting
            : strings.stateConnect}
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

function SkillCard({ title, desc, liveBadge }: { title: string; desc: string; liveBadge: string }) {
  return (
    <div className="rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-4">
      <div className="flex items-center gap-2">
        <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-emerald-400 border border-emerald-500/20">
          {liveBadge}
        </span>
        <p className="text-sm font-semibold text-[hsl(var(--text-primary))]">{title}</p>
      </div>
      <p className="mt-1.5 text-xs text-[hsl(var(--text-secondary))] leading-relaxed">{desc}</p>
    </div>
  );
}
