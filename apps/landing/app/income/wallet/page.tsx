'use client';

// /income/wallet — the email recipient's access + withdraw page.
// Sign in with the SAME email anicca paid (Crossmint email-OTP). The wallet that
// shows is the one owned by that email (owner:email:...). Non-custodial: the key
// lives with the user (TEE), exportable. Withdraw = send USDC out to any address
// (e.g. an exchange), or export the key. This is how the email rail becomes usable.

import { useState } from 'react';
import {
  CrossmintProvider,
  CrossmintAuthProvider,
  CrossmintWalletProvider,
  useCrossmintAuth,
  useWallet,
  ExportPrivateKeyButton,
} from '@crossmint/client-sdk-react-ui';

const CLIENT_KEY = process.env.NEXT_PUBLIC_CROSSMINT_CLIENT_KEY || '';
const USDC_BASE = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';

function Panel() {
  const auth = useCrossmintAuth() as any;
  const { wallet, status, error } = useWallet() as any;
  const [balance, setBalance] = useState<string>('');
  const [to, setTo] = useState('');
  const [amount, setAmount] = useState('');
  const [msg, setMsg] = useState('');

  const loggedIn = Boolean(auth?.jwt || auth?.user);

  async function refresh() {
    if (!wallet) return;
    try {
      const b: any = await (wallet as any).balances();
      setBalance(JSON.stringify(b));
    } catch (e: any) {
      setBalance('error: ' + e.message);
    }
  }

  async function withdraw() {
    if (!wallet) return setMsg('wallet not ready');
    setMsg('sending…');
    try {
      const r: any = await (wallet as any).send(to.trim(), 'usdc', amount.trim());
      setMsg('sent: ' + (r?.explorerLink || r?.hash || JSON.stringify(r)));
    } catch (e: any) {
      setMsg('error: ' + e.message);
    }
  }

  if (!loggedIn) {
    return (
      <div className="mx-auto max-w-md py-24 text-center">
        <h1 className="font-display text-3xl text-[hsl(var(--text-primary))]">Open your basic income</h1>
        <p className="mt-4 text-[15px] text-[hsl(var(--text-secondary))]">
          Sign in with the email anicca paid. You will see your balance and can move it out.
        </p>
        <button
          onClick={() => auth?.login?.()}
          className="mt-8 rounded-card bg-[hsl(var(--gold))] px-6 py-3 font-medium text-black"
        >
          Sign in with email
        </button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-md py-20">
      <h1 className="font-display text-2xl text-[hsl(var(--text-primary))]">Your wallet</h1>
      <p className="mt-2 break-all font-mono text-xs text-[hsl(var(--text-secondary))]">
        {wallet?.address || `status: ${status}`}
      </p>
      {error && <p className="mt-1 break-all text-xs text-red-400">err: {String(error?.message || error)}</p>}

      <button onClick={refresh} className="mt-4 rounded-card border border-[hsl(var(--border))] px-4 py-2 text-sm text-[hsl(var(--text-primary))]">
        Show balance
      </button>
      {balance && <p className="mt-2 break-all text-xs text-[hsl(var(--text-secondary))]">{balance}</p>}

      <div className="mt-8 space-y-3">
        <p className="text-sm text-[hsl(var(--text-primary))]">Withdraw USDC to an address (your exchange / another wallet)</p>
        <input value={to} onChange={(e) => setTo(e.target.value)} placeholder="0x… destination" className="w-full rounded border border-[hsl(var(--border))] bg-transparent px-3 py-2 text-sm" />
        <input value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="amount (USDC)" className="w-full rounded border border-[hsl(var(--border))] bg-transparent px-3 py-2 text-sm" />
        <button onClick={withdraw} className="rounded-card bg-[hsl(var(--gold))] px-5 py-2.5 font-medium text-black">Send</button>
        {msg && <p className="break-all text-xs text-[hsl(var(--text-secondary))]">{msg}</p>}
      </div>

      <div className="mt-8 border-t border-[hsl(var(--border))] pt-6">
        <p className="mb-2 text-xs text-[hsl(var(--text-secondary))]">Or take full control: export your key into any wallet app.</p>
        <ExportPrivateKeyButton className="rounded-card border border-[hsl(var(--border))] px-4 py-2 text-sm text-[hsl(var(--text-primary))]" />
      </div>

      <button onClick={() => auth?.logout?.()} className="mt-8 text-xs text-[hsl(var(--text-secondary))] underline">Sign out</button>
      <p className="mt-2 text-[11px] text-[hsl(var(--text-secondary))]">USDC on Base: {USDC_BASE}</p>
    </div>
  );
}

export default function WalletAccessPage() {
  if (!CLIENT_KEY) {
    return <div className="mx-auto max-w-md py-24 text-center text-[hsl(var(--text-secondary))]">Wallet access is being set up.</div>;
  }
  return (
    <CrossmintProvider apiKey={CLIENT_KEY}>
      <CrossmintAuthProvider loginMethods={['email']}>
        <CrossmintWalletProvider createOnLogin={{ chain: 'base', recovery: { type: 'email' } }}>
          <Panel />
        </CrossmintWalletProvider>
      </CrossmintAuthProvider>
    </CrossmintProvider>
  );
}
