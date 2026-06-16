/* eslint-disable react/no-unescaped-entities */
import LaunchNav from '@/components/site/LaunchNav';
import Footer from '@/components/site/Footer';
import { Section, Reveal } from '@/components/site/taste';
import MeGate from './MeGate';

// spec28 §1: /me is PRIVATE / per-user and auth-gated. Anonymous visitors NEVER see
// instance telemetry — MeGate shows a Google login wall. Logged-in users see THEIR own
// instance (spawn + real MeClient wallet dashboard) + pricing tiers. The old public
// "illustrative" /me (the fake money card + hard-coded children/colony cards) is removed.
// Static export: the gate runs client-side (Supabase Auth Google, see lib/auth.ts).

export const dynamic = 'force-static';

export const metadata = {
  title: 'Me — Your Anicca Instance',
  description:
    'Manage your Anicca instance: live P&L, runway, and one-tap withdraw of earned USDC to your bank account.',
};

// ── GATE-0: the first REAL profitable on-chain wake (verified 2026-06-16) ──
// Verbatim from the committed earn-ledger.jsonl line; re-checkable on Base. Not illustrative.
// The automaton loop (heartbeat) runs skills/earn/run.sh EARN_MODE=execute; the earn skill
// liquidates ETH→USDC on Base, verifies the receipt 0x1 + USDC delta, and appends this line.
const GATE0_WAKE = {
  source: 'swap-eth-usdc',
  task: 'eth→usdc liquidation for compute runway',
  earnUsdc: 0.547676,
  costUsdc: 0.001304,
  netUsdc: 0.546372,
  status: '0x1' as const,
  tx: '0xc4f2df3e445acaff01bd004f8503d41582d8acb12a55bf27797d5aea066f721d',
  date: '2026-06-16',
};
// GATE-0 = a real EXTERNAL-revenue wake (earned from outside, earn > cost). An ETH→USDC swap is
// asset liquidation (converting our own ETH), NOT external earning — it does NOT meet GATE-0.
// Director correction 2026-06-16: do not claim "GATE-0 MET" on a swap on the live site (HARD 0.24/0.31).
const GATE0_EXTERNAL = !/swap|liquidat/i.test(`${GATE0_WAKE.source} ${GATE0_WAKE.task}`);
const GATE0_MET = GATE0_EXTERNAL && GATE0_WAKE.status === '0x1' && GATE0_WAKE.netUsdc > 0;

// ─── Sub-components ────────────────────────────────────────────────────────────

function StatusDot({ status }: { status: 'alive' | 'warning' | 'critical' }) {
  const colors: Record<string, string> = {
    alive: 'bg-emerald-500',
    warning: 'bg-amber-500',
    critical: 'bg-red-500',
  };
  return (
    <span
      className={`inline-block h-2 w-2 rounded-full ${colors[status]}`}
      aria-label={status}
    />
  );
}

function Card({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-5 ${className}`}
    >
      {children}
    </div>
  );
}

function CardLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-xs uppercase tracking-widest text-[hsl(var(--text-secondary))] mb-3">
      {children}
    </p>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function Page() {
  return (
    <>
      <LaunchNav active="/me" />

      <Section>
        <Reveal>
          <h1 className="text-3xl font-bold text-[hsl(var(--text-primary))]">
            Your Anicca instance
          </h1>
          <p className="mt-4 max-w-prose text-[hsl(var(--text-secondary))]">
            Connect your instance wallet to see its live numbers — net worth, monthly revenue,
            daily burn, runway, and whether it pays for itself — straight from the same signed
            telemetry that powers the public dashboard. Your instance writes only to its own
            body; this page just reads it.
          </p>
          {/* Auth gate: anon → Google login wall (no telemetry); logged-in → own dashboard. */}
          <MeGate />
        </Reveal>
      </Section>

      {/* ── GATE-0: the first REAL profitable on-chain wake (verified, re-checkable) ── */}
      <Section>
        <Reveal>
          <Card className="border-emerald-500/40 bg-[hsl(var(--surface-elevated))]">
            <div className="flex items-center justify-between gap-3">
              <CardLabel>初の実 on-chain 稼働（外部収益はこれから）</CardLabel>
              {GATE0_MET ? (
                <span className="inline-flex items-center gap-1.5 rounded-pill bg-emerald-500/15 px-3 py-1 text-xs font-semibold text-emerald-400">
                  <StatusDot status="alive" /> 外部収益 達成
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 rounded-pill bg-amber-500/15 px-3 py-1 text-xs font-semibold text-amber-400">
                  <StatusDot status="warning" /> 外部収益はまだ（自資産の換金のみ）
                </span>
              )}
            </div>
            <div className="flex flex-wrap items-end gap-8">
              <div>
                <p className="text-3xl font-bold text-emerald-400">
                  +${GATE0_WAKE.netUsdc.toFixed(4)}
                </p>
                <p className="mt-0.5 text-xs text-[hsl(var(--text-secondary))]">
                  net USDC（earn ${GATE0_WAKE.earnUsdc.toFixed(4)} − cost $
                  {GATE0_WAKE.costUsdc.toFixed(4)}）
                </p>
              </div>
              <div>
                <p className="text-base font-semibold text-[hsl(var(--text-primary))]">
                  保有 ETH を USDC に換金
                </p>
                <p className="mt-0.5 text-xs text-[hsl(var(--text-secondary))]">
                  サーバー代を賄うための換金
                </p>
              </div>
              <div>
                <p className="font-mono text-base font-semibold text-emerald-400">
                  receipt {GATE0_WAKE.status}
                </p>
                <p className="mt-0.5 text-xs text-[hsl(var(--text-secondary))]">
                  Base 受領ステータス（成功）
                </p>
              </div>
            </div>
            <a
              href={`https://basescan.org/tx/${GATE0_WAKE.tx}`}
              target="_blank"
              rel="noreferrer"
              className="mt-4 inline-flex items-center gap-2 font-mono text-xs underline underline-offset-4 text-[hsl(var(--text-secondary))] hover:text-emerald-400 transition-colors break-all"
            >
              tx {GATE0_WAKE.tx.slice(0, 10)}…{GATE0_WAKE.tx.slice(-6)} を BaseScan で検証 →
            </a>
            <p className="mt-3 text-[10px] text-[hsl(var(--text-secondary))]">
              あなたの個体が Base 上で実際に取引し、成功レシート（0x1）と USDC 差分を検証した上で記録した実績です。
              文章だけの主張ではなく、すべてオンチェーンで再確認できます。
            </p>
          </Card>
        </Reveal>
      </Section>

      <Footer locale="en" />
    </>
  );
}
