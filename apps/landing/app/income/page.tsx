/* eslint-disable react/no-unescaped-entities */
'use client';

import { useState, useRef } from 'react';
import Link from 'next/link';
import { QRCodeSVG } from 'qrcode.react';
import JsonLd from '@/components/JsonLd';
import { Section } from '@/components/site/taste/Section';
import { Reveal } from '@/components/site/taste/Reveal';

// World ID 4.0 personhood gate. The gate renders only when BOTH app_id + rp_id are configured.
const WORLD_APP_ID = (process.env.NEXT_PUBLIC_WORLDCOIN_APP_ID || '') as `app_${string}`;
const WORLD_RP_ID = process.env.NEXT_PUBLIC_WORLDCOIN_RP_ID || '';
const WORLD_ENV = (process.env.NEXT_PUBLIC_WORLDCOIN_ENV || 'production') as 'production' | 'staging';
const WORLD_ACTION = 'claim-ubi';
const GATE_ON = Boolean(WORLD_APP_ID && WORLD_RP_ID);

// spec32: /income = the front door for "receive basic income". Apply ABOVE THE FOLD,
// email-first (simplest), wallet = instant (today's demo), bank = local currency.
// No iOS logo. Roadmap incl reach-everyone (gov/charity/direct) + animals/aliens.
// No subscription, no "unconditional", no fixed %. anicca never takes money — it gives.

const incomeLd = {
  '@context': 'https://schema.org',
  '@type': 'Service',
  name: 'Anicca Basic Income',
  url: 'https://aniccaai.com/income',
  serviceType: 'Basic income paid by an autonomous AI',
  provider: { '@type': 'Organization', name: 'Anicca', url: 'https://aniccaai.com' },
  description:
    'A live basic income funded by an autonomous AI that earns its own way. No human in the loop, so it does not run dry. Sign up with your email; receive to email, a crypto wallet, or your bank.',
};

const WALLET_RE = /^0x[0-9a-fA-F]{40}$/;

// Per-country routing: the recipient picks their country, and the receive options
// adapt to the rail that actually reaches a bank there. anicca converts its USDC
// behind the scenes; the recipient only ever gives a bank/email — never touches crypto.
type CountryRail = {
  label: string;
  currency: string;
  bankTitle: string;
  bankNote: string;
  emailNote: string;
  recommend: 'email' | 'bank';
};
const COUNTRY_RAILS: Record<string, CountryRail> = {
  jp: {
    label: 'Japan',
    currency: 'JPY',
    bankTitle: 'Your Japanese bank (MUFG, Yucho, any bank)',
    bankNote:
      'Real yen to your bank by Zengin transfer — like a normal furikomi, nothing to install. You give your account number once. Rolling out.',
    emailNote:
      'Receive to an email wallet today; for now cash out to a JP bank yourself via an exchange. Bank-direct (no crypto) is rolling out.',
    recommend: 'bank',
  },
  us: {
    label: 'United States',
    currency: 'USD',
    bankTitle: 'Your US bank (ACH)',
    bankNote:
      'US dollars straight to your bank account. You give routing + account number once. Rolling out.',
    emailNote:
      'Receive by email, then cash out to your US bank in-app — no exchange needed. Rolling out.',
    recommend: 'bank',
  },
  other: {
    label: 'Other country',
    currency: 'your local currency',
    bankTitle: 'Your local bank (global payout)',
    bankNote:
      'Local currency to a bank in 160+ countries. You give your bank details once. Rolling out.',
    emailNote:
      'Receive by email or wallet today; bank-direct in your country opens as rails come online.',
    recommend: 'email',
  },
};
const COUNTRY_OPTIONS: { value: string; label: string }[] = [
  { value: 'jp', label: 'Japan' },
  { value: 'us', label: 'United States' },
  { value: 'gb', label: 'United Kingdom' },
  { value: 'ca', label: 'Canada' },
  { value: 'au', label: 'Australia' },
  { value: 'other', label: 'Another country' },
];
function railFor(country: string): CountryRail {
  return COUNTRY_RAILS[country] ?? COUNTRY_RAILS.other;
}

function ApplyForm() {
  const [email, setEmail] = useState('');
  const [method, setMethod] = useState<'email' | 'wallet' | 'bank'>('email');
  const [wallet, setWallet] = useState('');
  const [country, setCountry] = useState('jp');
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [verified, setVerified] = useState(false);
  const [idkitResp, setIdkitResp] = useState<unknown>(null);
  const [connectUrl, setConnectUrl] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const [bank, setBank] = useState({ bankCode: '', branchCode: '', accountType: '1', accountNumber: '', beneficiaryName: '' });
  const setBankField = (k: string, v: string) => setBank((b) => ({ ...b, [k]: v }));

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!email.includes('@')) {
      setError('Enter a valid email.');
      return;
    }
    if (method === 'wallet' && !WALLET_RE.test(wallet.trim())) {
      setError('Enter a valid Base wallet address (0x…40 hex).');
      return;
    }
    if (GATE_ON && !verified) {
      setError('Confirm you are a unique person first — so the income reaches real people, once each.');
      return;
    }
    abortRef.current?.abort();
    abortRef.current = new AbortController();
    setSubmitting(true);
    try {
      // JP bank → GMO Zengin rail: record the bank destination (validated server-side too).
      if (method === 'bank' && country === 'jp') {
        const res = await fetch('/.netlify/functions/income-signup', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: email.trim(), method: 'bank', country: 'jp', bank, idkitResponse: idkitResp }),
          signal: abortRef.current.signal,
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          setError((data.details && data.details.join(' / ')) || data.error || 'Check your bank details.');
          setSubmitting(false);
          return;
        }
        setDone(true);
        setSubmitting(false);
        return;
      }
      // Other-country bank → Stripe Connect onboarding (redirects to KYC).
      if (method === 'bank') {
        const res = await fetch('/.netlify/functions/income-apply', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: email.trim(), reason: 'basic income', country }),
          signal: abortRef.current.signal,
        });
        const data = await res.json();
        if (data.onboarding_url) {
          window.location.href = data.onboarding_url;
          return;
        }
        setError(data.error || 'Could not start bank setup.');
        setSubmitting(false);
        return;
      }
      // Email / wallet → join the queue (records destination).
      const res = await fetch('/.netlify/functions/income-signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim(),
          method,
          wallet: method === 'wallet' ? wallet.trim() : undefined,
          idkitResponse: idkitResp,
        }),
        signal: abortRef.current.signal,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok && res.status !== 404) {
        setError(data.error || 'Something went wrong. Try again.');
        setSubmitting(false);
        return;
      }
      setDone(true);
      setSubmitting(false);
    } catch (err) {
      if ((err as Error).name === 'AbortError') return;
      setError(String(err));
      setSubmitting(false);
    }
  }

  // World ID 4.0 verify: sign the request server-side, open the connect flow (QR / World App),
  // poll until the user finishes, then carry the IDKit response into the signup (server re-verifies).
  async function startVerify() {
    if (!email.includes('@')) { setError('Enter your email first, then verify.'); return; }
    setError(null);
    setVerifying(true);
    try {
      const { IDKit, deviceLegacy } = await import('@worldcoin/idkit-core');
      const rpSig = await fetch('/.netlify/functions/rp-signature', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: WORLD_ACTION }),
      }).then((r) => r.json());
      if (!rpSig?.sig) throw new Error('Could not start verification.');
      const request = await IDKit.request({
        app_id: WORLD_APP_ID,
        action: WORLD_ACTION,
        rp_context: {
          rp_id: WORLD_RP_ID,
          nonce: rpSig.nonce,
          created_at: rpSig.created_at,
          expires_at: rpSig.expires_at,
          signature: rpSig.sig,
        },
        allow_legacy_proofs: true,
        environment: WORLD_ENV,
      }).preset(deviceLegacy({ signal: email.trim().toLowerCase() }));
      setConnectUrl(request.connectorURI);
      // pollUntilCompletion resolves to { success, result } — forward the inner `result` (it carries
      // `responses` with the nullifier + signal_hash) to the server, which re-verifies it at v4/verify.
      const response = await request.pollUntilCompletion();
      if (!response?.success || !response.result) throw new Error('Verification did not complete.');
      setIdkitResp(response.result);
      setVerified(true);
      setConnectUrl(null);
    } catch (err) {
      setError((err as Error)?.message || 'Verification failed. Try again.');
      setConnectUrl(null);
    } finally {
      setVerifying(false);
    }
  }

  if (done) {
    return (
      <div className="rounded-card border border-[hsl(var(--gold))]/40 bg-[hsl(var(--surface-elevated))] p-6">
        <p className="text-lg font-semibold text-[hsl(var(--text-primary))]">You're in line.</p>
        <p className="mt-2 text-sm leading-relaxed text-[hsl(var(--text-secondary))]">
          As Anicca earns, people come off the waitlist in order — it's a queue, not a lottery.
          When your turn comes you'll get an email: "From today, money reaches you." No fixed
          amount is promised; you receive a real share of what the swarm actually earned.
        </p>
      </div>
    );
  }

  return (
    <form
      onSubmit={onSubmit}
      className="rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface-elevated))] p-6 space-y-4"
    >
      <div className="flex flex-col gap-1.5">
        <label htmlFor="bi-email" className="text-sm font-medium text-[hsl(var(--text-primary))]">
          Email
        </label>
        <input
          id="bi-email"
          type="email"
          required
          placeholder="you@example.com"
          value={email}
          onChange={(e) => { setEmail(e.target.value); if (verified || idkitResp) { setVerified(false); setIdkitResp(null); setConnectUrl(null); } }}
          className="w-full rounded-input border border-[hsl(var(--border))] bg-[hsl(var(--surface))] px-4 py-3 text-[hsl(var(--text-primary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--gold))]"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="bi-country" className="text-sm font-medium text-[hsl(var(--text-primary))]">Where do you live?</label>
        <select
          id="bi-country"
          value={country}
          onChange={(e) => setCountry(e.target.value)}
          className="w-full rounded-input border border-[hsl(var(--border))] bg-[hsl(var(--surface))] px-4 py-3 text-[hsl(var(--text-primary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--gold))]"
        >
          {COUNTRY_OPTIONS.map((c) => (
            <option key={c.value} value={c.value}>{c.label}</option>
          ))}
        </select>
        <p className="text-xs text-[hsl(var(--text-secondary))]">
          We route you to the best way to reach a bank in {railFor(country).label} — you only ever give a bank or email, never touch crypto.
        </p>
      </div>

      <fieldset className="space-y-2">
        <legend className="text-sm font-medium text-[hsl(var(--text-primary))]">How to receive</legend>
        <label className="flex items-start gap-2 text-sm text-[hsl(var(--text-secondary))]">
          <input type="radio" name="method" checked={method === 'bank'} onChange={() => setMethod('bank')} className="mt-1" />
          <span><strong className="text-[hsl(var(--text-primary))]">Bank account ({railFor(country).currency}){railFor(country).recommend === 'bank' ? ' — recommended' : ''}.</strong> {railFor(country).bankNote} {railFor(country).bankTitle}.</span>
        </label>
        <label className="flex items-start gap-2 text-sm text-[hsl(var(--text-secondary))]">
          <input type="radio" name="method" checked={method === 'email'} onChange={() => setMethod('email')} className="mt-1" />
          <span><strong className="text-[hsl(var(--text-primary))]">Email{railFor(country).recommend === 'email' ? ' — recommended' : ''}.</strong> {railFor(country).emailNote}</span>
        </label>
        <label className="flex items-start gap-2 text-sm text-[hsl(var(--text-secondary))]">
          <input type="radio" name="method" checked={method === 'wallet'} onChange={() => setMethod('wallet')} className="mt-1" />
          <span><strong className="text-[hsl(var(--text-primary))]">Crypto wallet — instant.</strong> Paste a USDC (Base) address; money arrives in seconds. For people who know crypto.</span>
        </label>
      </fieldset>

      {method === 'wallet' && (
        <div className="flex flex-col gap-1.5">
          <label htmlFor="bi-wallet" className="text-sm font-medium text-[hsl(var(--text-primary))]">
            Your USDC wallet (Base)
          </label>
          <input
            id="bi-wallet"
            placeholder="0x…"
            value={wallet}
            onChange={(e) => setWallet(e.target.value)}
            className="w-full rounded-input border border-[hsl(var(--border))] bg-[hsl(var(--surface))] px-4 py-3 font-mono text-[hsl(var(--text-primary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--gold))]"
          />
        </div>
      )}

      {method === 'bank' && country === 'jp' && (
        <div className="space-y-3 rounded-input border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-4">
          <p className="text-sm font-medium text-[hsl(var(--text-primary))]">日本の銀行口座（円で受け取り・暗号資産不要）</p>
          <div className="grid grid-cols-2 gap-3">
            <input inputMode="numeric" placeholder="銀行コード (4桁)" value={bank.bankCode} onChange={(e) => setBankField('bankCode', e.target.value)} className="w-full rounded-input border border-[hsl(var(--border))] bg-[hsl(var(--surface-elevated))] px-3 py-2.5 text-[hsl(var(--text-primary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--gold))]" />
            <input inputMode="numeric" placeholder="支店コード (3桁)" value={bank.branchCode} onChange={(e) => setBankField('branchCode', e.target.value)} className="w-full rounded-input border border-[hsl(var(--border))] bg-[hsl(var(--surface-elevated))] px-3 py-2.5 text-[hsl(var(--text-primary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--gold))]" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <select value={bank.accountType} onChange={(e) => setBankField('accountType', e.target.value)} className="w-full rounded-input border border-[hsl(var(--border))] bg-[hsl(var(--surface-elevated))] px-3 py-2.5 text-[hsl(var(--text-primary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--gold))]">
              <option value="1">普通</option>
              <option value="2">当座</option>
              <option value="4">貯蓄</option>
            </select>
            <input inputMode="numeric" placeholder="口座番号 (7桁)" value={bank.accountNumber} onChange={(e) => setBankField('accountNumber', e.target.value)} className="w-full rounded-input border border-[hsl(var(--border))] bg-[hsl(var(--surface-elevated))] px-3 py-2.5 text-[hsl(var(--text-primary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--gold))]" />
          </div>
          <input placeholder="口座名義（半角カナ 例: ﾀﾅｶ ﾀﾛｳ）" value={bank.beneficiaryName} onChange={(e) => setBankField('beneficiaryName', e.target.value)} className="w-full rounded-input border border-[hsl(var(--border))] bg-[hsl(var(--surface-elevated))] px-3 py-2.5 font-mono text-[hsl(var(--text-primary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--gold))]" />
          <p className="text-xs text-[hsl(var(--text-secondary))]">anicca が USDC を円に換えて、この口座へ振り込みます。あなたは口座情報を一度入れるだけ。（順次開通）</p>
        </div>
      )}

      {GATE_ON && (verified ? (
        <div className="flex items-center gap-3 rounded-input border border-[hsl(var(--gold))]/40 bg-[hsl(var(--surface))] px-4 py-3 transition-all duration-500">
          <span aria-hidden className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[hsl(var(--gold))] text-[12px] font-bold text-[#18181b]">✓</span>
          <span className="text-sm text-[hsl(var(--text-primary))]">Verified — one income, one person. You're confirmed unique.</span>
        </div>
      ) : (
        <div className="rounded-input border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-4">
          <p className="text-sm font-medium text-[hsl(var(--text-primary))]">Confirm you're a unique person</p>
          <p className="mt-1.5 text-xs leading-relaxed text-[hsl(var(--text-secondary))]">
            So the income reaches real people — once each, no bots, no duplicates. Private: we only learn that you're unique, never who you are. No Orb needed.
          </p>
          {connectUrl ? (
            <div className="mt-3 flex flex-col items-center gap-3">
              <div className="rounded-input bg-white p-3">
                <QRCodeSVG value={connectUrl} size={168} />
              </div>
              <p className="text-xs text-[hsl(var(--text-secondary))]">Scan with World App — waiting for you to confirm…</p>
              <a href={connectUrl} target="_blank" rel="noopener noreferrer" className="text-xs font-medium text-[hsl(var(--gold))] underline">Open World App on this device</a>
            </div>
          ) : (
            <button
              type="button"
              onClick={startVerify}
              disabled={verifying}
              className="mt-3 inline-flex items-center gap-2 rounded-pill border border-[hsl(var(--gold))]/50 bg-[hsl(var(--surface-elevated))] px-5 py-2.5 text-sm font-semibold text-[hsl(var(--text-primary))] transition-all duration-300 hover:border-[hsl(var(--gold))] hover:brightness-110 active:scale-[0.98] disabled:opacity-50"
            >
              {verifying ? 'Starting…' : 'Verify with World ID'}
            </button>
          )}
        </div>
      ))}

      {error && <p className="text-sm text-[hsl(var(--destructive))]">{error}</p>}

      <button
        type="submit"
        disabled={submitting || (GATE_ON && !verified)}
        className="w-full rounded-pill bg-[hsl(var(--gold))] px-6 py-3 font-semibold text-[#18181b] transition-all duration-300 hover:brightness-95 active:scale-[0.98] disabled:opacity-50"
      >
        {submitting ? 'Sending…' : 'Receive basic income →'}
      </button>
      <p className="text-xs text-[hsl(var(--text-secondary))]">
        Free. You never pay Anicca anything — it earns its own money and gives a share away.
      </p>
    </form>
  );
}

export default function Page() {
  return (
    <main>
      <JsonLd data={incomeLd} />

      {/* Above the fold: headline + apply form, side by side on desktop */}
      <Section className="pt-24">
        <div className="grid grid-cols-1 gap-10 md:grid-cols-2 md:items-center">
          <Reveal>
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-[hsl(var(--gold))]">
                Anicca Basic Income
              </p>
              <h1 className="mt-3 font-display text-[34px] leading-tight text-[hsl(var(--text-primary))] sm:text-[48px]">
                An AI that earns its own money — and gives you a share.
              </h1>
              <p className="mt-4 max-w-[46ch] text-[16px] leading-relaxed text-[hsl(var(--text-secondary))]">
                No human keeps it alive. It pays for its own compute, earns on its own, and sends a
                share of what's left to people. That's why this doesn't run dry. Sign up with your
                email and join the line.
              </p>
            </div>
          </Reveal>
          <Reveal delay={0.06}>
            <ApplyForm />
          </Reveal>
        </div>
      </Section>

      {/* How it works */}
      <Section>
        <Reveal>
          <h2 className="font-display text-2xl text-[hsl(var(--text-primary))] sm:text-3xl">How it works</h2>
          <ol className="mt-5 list-decimal space-y-3 pl-6 text-[15px] leading-relaxed text-[hsl(var(--text-primary))]">
            <li>Sign up with your email (30 seconds). Pick how you want to receive it.</li>
            <li>You join the line. As Anicca earns more, people come off the waitlist <strong>in order</strong> — a queue, not a lottery. The line exists only so it can actually pay everyone it lets in.</li>
            <li>When your turn comes, you get an email: "From today, money reaches you." Then it arrives on its own.</li>
          </ol>
          <p className="mt-4 text-sm text-[hsl(var(--text-secondary))]">
            No fixed amount is promised — earnings move day to day, so you receive a real share of what
            the swarm actually earned. We show you exactly what arrived.
          </p>
        </Reveal>
      </Section>

      {/* How you actually get it — per recipient, named site + steps */}
      <Section>
        <Reveal>
          <h2 className="font-display text-2xl text-[hsl(var(--text-primary))] sm:text-3xl">How you actually get it</h2>
          <p className="mt-3 max-w-[60ch] text-[15px] leading-relaxed text-[hsl(var(--text-secondary))]">
            Pick the one that fits you. No crypto knowledge needed for the email or bank way.
          </p>
          <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3 md:[grid-auto-flow:dense]">
            <div className="rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface-elevated))] p-6">
              <p className="font-mono text-[12px] text-[hsl(var(--gold))]">Crypto wallet · works today</p>
              <p className="mt-3 text-[15px] leading-relaxed text-[hsl(var(--text-secondary))]">
                Enter your Base address above. Anicca sends real USDC in seconds. See it in your own
                wallet app or on basescan.org. Cash out through your own exchange whenever you like.
              </p>
            </div>
            <div className="rounded-card border border-[hsl(var(--border))] p-6">
              <p className="font-mono text-[12px] text-[hsl(var(--gold))]">Email · no wallet needed</p>
              <p className="mt-3 text-[15px] leading-relaxed text-[hsl(var(--text-secondary))]">
                Enter your email. Anicca makes a wallet tied to that email and sends there. Come back to{' '}
                <Link href="/income/wallet" className="text-[hsl(var(--gold))] underline">aniccaai.com/income/wallet</Link>,
                sign in with the same email, type the code from your inbox, and your money is right there
                to keep or move out.
              </p>
            </div>
            <div className="rounded-card border border-[hsl(var(--border))] p-6">
              <p className="font-mono text-[12px] text-[hsl(var(--gold))]">Bank or PayPay · rolling out</p>
              <p className="mt-3 text-[15px] leading-relaxed text-[hsl(var(--text-secondary))]">
                Sign up now and choose your country. When the rail opens, Anicca turns its dollars into
                your local currency and deposits it to your bank or PayPay — like a normal transfer,
                nothing to install. Grandparents welcome.
              </p>
            </div>
          </div>
        </Reveal>
      </Section>

      {/* Why this works */}
      <Section>
        <Reveal>
          <h2 className="font-display text-2xl text-[hsl(var(--text-primary))] sm:text-3xl">Why this one doesn't run dry</h2>
          <p className="mt-4 max-w-[65ch] text-[15px] leading-relaxed text-[hsl(var(--text-secondary))]">
            Every other "AI will fund people" idea needs a human to keep paying — a subscription, a
            donor, a tax. Ours doesn't. Anicca owns its own compute and earns on-chain, then gives the
            surplus away. Take the human out of the loop and basic income stops being charity that runs
            out — it becomes something the system just does. You never pay Anicca; paying it would
            contradict the whole point. It earns. It gives.
          </p>
        </Reveal>
      </Section>

      {/* Roadmap — to every living being */}
      <Section>
        <Reveal>
          <h2 className="font-display text-2xl text-[hsl(var(--text-primary))] sm:text-3xl">The roadmap — to everyone</h2>
          <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="rounded-card border border-[hsl(var(--border))] p-5">
              <p className="font-mono text-[12px] text-[hsl(var(--gold))]">Now</p>
              <p className="mt-2 text-[15px] leading-relaxed text-[hsl(var(--text-secondary))]">
                You sign up; you join the line; as Anicca earns, your turn comes and money starts
                reaching you — by email, wallet, or your bank, in any country.
              </p>
            </div>
            <div className="rounded-card border border-[hsl(var(--border))] p-5">
              <p className="font-mono text-[12px] text-[hsl(var(--gold))]">Next</p>
              <p className="mt-2 text-[15px] leading-relaxed text-[hsl(var(--text-secondary))]">
                Reaching people who never signed up and may have no bank, no internet — by sending
                to phones (mobile money), by funding NPOs that hand it to people directly, and by
                partnering with governments so the money can arrive in a name people already trust.
                Always proactively, never as anonymous spam — Anicca earns trust by giving, day after
                day, in the open.
              </p>
            </div>
            <div className="rounded-card border border-[hsl(var(--border))] p-5">
              <p className="font-mono text-[12px] text-[hsl(var(--gold))]">The horizon</p>
              <p className="mt-2 text-[15px] leading-relaxed text-[hsl(var(--text-secondary))]">
                A floor under every living being — people first, then animals, and honestly stated as
                the far horizon, every living being in the universe. Support shaped to the situation:
                the right help, not just cash.
              </p>
            </div>
          </div>
          <p className="mt-5 max-w-[65ch] text-sm text-[hsl(var(--text-secondary))]">
            There will be many basic incomes — sovereign ones for a country or a city. Ours is the most
            universal: it's for the whole universe, and it reaches you proactively rather than making
            you go somewhere to register.
          </p>
        </Reveal>
      </Section>

      <Section>
        <Reveal>
          <div className="border-t border-[hsl(var(--border))] pt-8 text-xs text-[hsl(var(--text-secondary))]">
            Live numbers:{' '}
            <Link href="/en" className="underline hover:text-[hsl(var(--text-primary))]">aniccaai.com</Link>
            {' '}· One of the{' '}
            <Link href="/fellows" className="underline hover:text-[hsl(var(--text-primary))]">SAOs</Link>
          </div>
        </Reveal>
      </Section>
    </main>
  );
}
