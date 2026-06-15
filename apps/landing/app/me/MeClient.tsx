'use client';

import { useEffect, useState, useCallback } from 'react';

// /me client island — reads the instance wallet (URL ?wallet= or saved input), fetches the
// LIVE dashboard-sync aggregate (the telemetry pipeline already serves it), and renders THIS
// instance's P&L / runway / status + the withdraw affordance. Static-export safe: all data is
// fetched at runtime in the browser, nothing is server-rendered per-wallet.
// Aniccas never write the website — this page only READS dashboard-sync (spec27 A-install/me).

const SYNC_URL = '/.netlify/functions/dashboard-sync';
const WALLET_RE = /^0x[a-fA-F0-9]{40}$/;
const STORAGE_KEY = 'anicca.me.wallet';

type Instance = {
  id: string;
  host?: string;
  geo?: string;
  model_live?: string;
  model_tier?: 'frontier' | 'free';
  net_worth_usd: number;
  revenue_mo_usd: number;
  burn_day_usd: number;
  runway_days: number;
  status: 'alive' | 'critical' | 'dead';
};

type SyncShape = { leaderboard?: Instance[]; updated_at?: string };

function usd(n: number | undefined): string {
  if (typeof n !== 'number' || Number.isNaN(n)) return '—';
  return `$${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function statusTone(status: string): string {
  if (status === 'alive') return 'text-emerald-500';
  if (status === 'critical') return 'text-amber-500';
  return 'text-red-500';
}

export default function MeClient() {
  const [wallet, setWallet] = useState('');
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [instance, setInstance] = useState<Instance | null>(null);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  // Resolve the initial wallet from ?wallet= or the last-saved value.
  useEffect(() => {
    const fromUrl = new URLSearchParams(window.location.search).get('wallet') || '';
    const saved = window.localStorage.getItem(STORAGE_KEY) || '';
    const initial = WALLET_RE.test(fromUrl) ? fromUrl : WALLET_RE.test(saved) ? saved : '';
    if (initial) {
      setWallet(initial);
      setInput(initial);
    }
  }, []);

  const load = useCallback(async (w: string) => {
    setLoading(true);
    setError(null);
    setNotFound(false);
    setInstance(null);
    try {
      const r = await fetch(SYNC_URL, { cache: 'no-store' });
      if (!r.ok) throw new Error(`dashboard unavailable (${r.status})`);
      const data: SyncShape = await r.json();
      const rows = Array.isArray(data.leaderboard) ? data.leaderboard : [];
      const match = rows.find((row) => row.id.toLowerCase() === w.toLowerCase()) || null;
      setUpdatedAt(data.updated_at || null);
      if (!match) setNotFound(true);
      setInstance(match);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'failed to load');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (wallet) void load(wallet);
  }, [wallet, load]);

  function onConnect(e: React.FormEvent) {
    e.preventDefault();
    const w = input.trim();
    if (!WALLET_RE.test(w)) {
      setError('Enter a valid 0x… wallet address (42 chars).');
      return;
    }
    window.localStorage.setItem(STORAGE_KEY, w);
    setError(null);
    setWallet(w);
  }

  const surplus = instance ? instance.revenue_mo_usd / 30 - instance.burn_day_usd : 0;
  const selfFunded = instance ? instance.status !== 'dead' && surplus >= 0 : false;

  return (
    <div className="mt-10 max-w-2xl">
      {/* wallet connect */}
      <form onSubmit={onConnect} className="flex flex-col gap-3 sm:flex-row">
        <label htmlFor="me-wallet" className="sr-only">
          Your instance wallet address
        </label>
        <input
          id="me-wallet"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="0x… your instance wallet"
          spellCheck={false}
          autoComplete="off"
          className="flex-1 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-4 py-2.5 font-mono text-sm text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--gold))]"
        />
        <button
          type="submit"
          className="rounded-md bg-[hsl(var(--text-primary))] px-5 py-2.5 text-sm font-semibold text-[hsl(var(--background))] transition-opacity hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--gold))]"
        >
          {wallet ? 'Refresh' : 'Connect'}
        </button>
      </form>

      {error && (
        <p role="alert" className="mt-4 text-sm text-red-500">
          {error}
        </p>
      )}

      {loading && (
        <p className="mt-6 text-sm text-[hsl(var(--text-secondary))]">Loading your instance…</p>
      )}

      {!loading && wallet && notFound && (
        <p className="mt-6 text-sm text-[hsl(var(--text-secondary))]">
          No telemetry yet for{' '}
          <span className="font-mono">{wallet.slice(0, 6)}…{wallet.slice(-4)}</span>. Your instance
          reports on its next wake — check back shortly.
        </p>
      )}

      {!loading && instance && (
        <section aria-label="Your instance" className="mt-8">
          <div className="flex items-baseline justify-between gap-4">
            <h2 className="font-mono text-sm text-[hsl(var(--text-secondary))]">
              {instance.id.slice(0, 6)}…{instance.id.slice(-4)}
            </h2>
            <span className={`text-sm font-semibold uppercase tracking-wide ${statusTone(instance.status)}`}>
              {instance.status}
            </span>
          </div>

          <dl className="mt-5 grid grid-cols-2 gap-x-6 gap-y-6 sm:grid-cols-3">
            <div>
              <dt className="text-xs uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                Net worth
              </dt>
              <dd className="mt-1 text-2xl font-bold text-[hsl(var(--text-primary))]">
                {usd(instance.net_worth_usd)}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                Revenue / mo
              </dt>
              <dd className="mt-1 text-2xl font-bold text-[hsl(var(--text-primary))]">
                {usd(instance.revenue_mo_usd)}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                Burn / day
              </dt>
              <dd className="mt-1 text-2xl font-bold text-[hsl(var(--text-primary))]">
                {usd(instance.burn_day_usd)}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                Runway
              </dt>
              <dd className="mt-1 text-2xl font-bold text-[hsl(var(--text-primary))]">
                {instance.runway_days >= 999 ? '∞' : `${instance.runway_days}d`}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                Self-funded
              </dt>
              <dd className={`mt-1 text-2xl font-bold ${selfFunded ? 'text-emerald-500' : 'text-[hsl(var(--text-primary))]'}`}>
                {selfFunded ? 'Yes' : 'No'}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                Model
              </dt>
              <dd className="mt-1 text-sm text-[hsl(var(--text-primary))]">
                {instance.model_live || '—'}
                {instance.model_tier ? ` (${instance.model_tier})` : ''}
              </dd>
            </div>
          </dl>

          {/* withdraw — earned USDC is the instance's own; off-ramp to bank (spec27 A-install/me, task #83) */}
          <div className="mt-10 rounded-lg border border-[hsl(var(--border))] p-5">
            <h3 className="text-sm font-semibold text-[hsl(var(--text-primary))]">
              Withdraw earned USDC
            </h3>
            <p className="mt-2 text-sm text-[hsl(var(--text-secondary))]">
              Move surplus from your instance wallet to your bank (Stripe payout / off-ramp). Only
              the surplus above the runway buffer is withdrawable, so your instance never starves.
            </p>
            <a
              href={`https://basescan.org/address/${instance.id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-4 inline-block text-sm font-semibold text-[hsl(var(--text-primary))] underline underline-offset-4 decoration-[hsl(var(--gold))]"
            >
              View wallet on Basescan →
            </a>
            <button
              type="button"
              disabled
              aria-disabled="true"
              title="Withdraw opens with the launch payout rail"
              className="mt-4 block w-full cursor-not-allowed rounded-md bg-[hsl(var(--text-primary))] px-5 py-2.5 text-sm font-semibold text-[hsl(var(--background))] opacity-60"
            >
              Withdraw to bank (opens at launch)
            </button>
          </div>

          {updatedAt && (
            <p className="mt-6 text-xs text-[hsl(var(--text-secondary))]">
              Live from telemetry · updated {new Date(updatedAt).toLocaleString()}
            </p>
          )}
        </section>
      )}
    </div>
  );
}
