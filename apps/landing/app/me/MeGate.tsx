'use client';

// /me auth gate (spec28 §1): /me is PRIVATE/per-user. Anonymous visitors NEVER see
// instance telemetry — they see a Google login wall. Logged-in users see THEIR own
// instance (spawn CTA + the real MeClient wallet dashboard). The old public
// "illustrative" /me ($6/$18.40 fake numbers, 3 hard-coded children) is removed.

import { useEffect, useState } from 'react';
import type { Session } from '@supabase/supabase-js';
import { getSession, onAuthChange, signInWithGoogle, signOut, supabase } from '@/lib/auth';
import MeClient from './MeClient';

// Real Stripe Payment Links (spec28 §0): $30/mo frontier already exists; $5/mo free-tier
// must be created (see patch §Stripe). Until NEXT_PUBLIC_STRIPE_PRICE5 link is set, the
// $5 button points at the same hosted checkout once the link is created.
const PAY_30 =
  process.env.NEXT_PUBLIC_STRIPE_LINK_30 || 'https://buy.stripe.com/cNi7sL0dEdVI0iI7ki2880U';
const PAY_5 = process.env.NEXT_PUBLIC_STRIPE_LINK_5 || '';

function Tier({
  name,
  price,
  blurb,
  href,
  highlight,
}: {
  name: string;
  price: string;
  blurb: string;
  href?: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={`rounded-card border p-5 ${
        highlight
          ? 'border-[hsl(var(--gold))]/50 bg-[hsl(var(--surface-elevated))]'
          : 'border-[hsl(var(--border))] bg-[hsl(var(--surface))]'
      }`}
    >
      <p className="text-sm font-semibold text-[hsl(var(--text-primary))]">{name}</p>
      <p className="mt-1 text-2xl font-bold text-[hsl(var(--text-primary))]">{price}</p>
      <p className="mt-2 text-xs text-[hsl(var(--text-secondary))]">{blurb}</p>
      {href ? (
        <a
          href={href}
          className="mt-4 inline-flex w-full items-center justify-center rounded-pill bg-[hsl(var(--gold))] px-4 py-2 text-sm font-semibold text-[#18181b] transition-all hover:brightness-95"
        >
          3日間無料で試す →
        </a>
      ) : (
        <p className="mt-4 text-xs text-emerald-400">現在のプラン（無料）</p>
      )}
    </div>
  );
}

export default function MeGate() {
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);
  const configured = typeof window !== 'undefined' && !!supabase();

  useEffect(() => {
    let active = true;
    getSession().then((s) => {
      if (active) {
        setSession(s);
        setReady(true);
      }
    });
    const off = onAuthChange((s) => active && setSession(s));
    return () => {
      active = false;
      off();
    };
  }, []);

  // ── not configured (env missing) — fail honest, still no fake telemetry ──
  if (!configured) {
    return (
      <div className="mt-10 max-w-md rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-6">
        <p className="text-sm text-[hsl(var(--text-secondary))]">
          ログインは準備中です。<code>NEXT_PUBLIC_SUPABASE_URL</code> /{' '}
          <code>NEXT_PUBLIC_SUPABASE_ANON_KEY</code> が未設定のためサインインできません。
        </p>
      </div>
    );
  }

  if (!ready) {
    return <p className="mt-10 text-sm text-[hsl(var(--text-secondary))]">読み込み中…</p>;
  }

  // ── ANONYMOUS — login wall. NEVER render instance telemetry here. ──
  if (!session) {
    return (
      <div className="mt-10 max-w-md rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-8 text-center">
        <h2 className="text-xl font-semibold text-[hsl(var(--text-primary))]">
          あなたのAniccaにログイン
        </h2>
        <p className="mt-3 text-sm text-[hsl(var(--text-secondary))]">
          Googleアカウントでログインすると、あなた専用のAnicca個体（純資産・収益・稼働ログ・自給率）が表示されます。
        </p>
        <button
          type="button"
          onClick={() => void signInWithGoogle()}
          className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-pill bg-[hsl(var(--text-primary))] px-5 py-3 text-sm font-semibold text-[hsl(var(--background))] transition-opacity hover:opacity-90"
        >
          Googleでログイン
        </button>
        <p className="mt-4 text-xs text-[hsl(var(--text-secondary))]">無料 · クレカ不要で開始</p>
      </div>
    );
  }

  // ── LOGGED IN — THEIR own instance: spawn + real wallet dashboard + tiers ──
  const email = session.user?.email ?? '';
  return (
    <div className="mt-8">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-[hsl(var(--text-secondary))]">
          ログイン中: <span className="text-[hsl(var(--text-primary))]">{email}</span>
        </p>
        <button
          type="button"
          onClick={() => void signOut()}
          className="text-xs underline underline-offset-4 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
        >
          ログアウト
        </button>
      </div>

      {/* Real per-user telemetry (connect this instance's wallet → live numbers). */}
      <MeClient />

      {/* Pricing tiers — free (current) / $5 free-tier / $30 frontier. 3-day trial on paid. */}
      <div className="mt-12">
        <h3 className="text-sm font-semibold uppercase tracking-widest text-[hsl(var(--text-secondary))]">
          稼ぎを伸ばす（24/7いつでも）
        </h3>
        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          <Tier name="Free" price="$0" blurb="ログインで誕生。無料枠モデルで稼働。" />
          <Tier
            name="Plus"
            price="$5/月"
            blurb="無料枠モデルをクラウドで常時稼働。"
            href={PAY_5 || undefined}
          />
          <Tier
            name="Pro"
            price="$30/月"
            blurb="フロンティアモデル＝より多く稼ぐ。鍵込み。"
            href={PAY_30}
            highlight
          />
        </div>
        <p className="mt-3 text-xs text-[hsl(var(--text-secondary))]">
          有料プランは3日間無料トライアル。いつでも開始・解約できます。
        </p>
      </div>
    </div>
  );
}
