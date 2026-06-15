/* eslint-disable react/no-unescaped-entities */
import Link from 'next/link';
import LaunchNav from '@/components/site/LaunchNav';
import Footer from '@/components/site/Footer';
import { Section, Reveal } from '@/components/site/taste';

// spec27 A-install/me: /me = instance management page (self-funded P&L + withdraw).
// Static export — data shown is illustrative; real-time data comes from telemetry→dashboard.json
// once the Stripe-spawn pipeline is live (spec26 A8c). Withdraw button links to Stripe portal.
// COLLISION RULE: LaunchNav and skills-lock.json are NEVER touched here (pre-wired by Foundation).

export const dynamic = 'force-static';

export const metadata = {
  title: 'Me — Your Anicca Instance',
  description:
    'Manage your Anicca instance: live P&L, runway, and one-tap withdraw of earned USDC to your bank account.',
};

// ─── Types ────────────────────────────────────────────────────────────────────

type ChildInstance = {
  id: string;
  host: 'cloud' | 'local';
  hostLabel: string;
  model: string;
  balance: number;
  status: 'alive' | 'warning' | 'critical';
};

// ─── Static demo data (spec20 §3 wireframe values) ────────────────────────────

const GENESIS = {
  id: 'genesis',
  host: '☁ akash · US-west',
  model: '⚡ claude-sonnet-4-6',
  balance: 12.40,
  runwayDays: 29,
  status: 'alive' as const,
};

const COLONY = {
  totalAssets: 46.20,
  instanceCount: 3,
  selfFunded: true,
};

const MONEY = {
  sentToYou: 6.00,
  earnedThisMonth: 18.40,
  subscriptionCancelled: true,
};

const CHILDREN: ChildInstance[] = [
  {
    id: 'anicca-001',
    host: 'cloud',
    hostLabel: '☁ akash · EU',
    model: '⚡ sonnet',
    balance: 6.20,
    status: 'alive',
  },
  {
    id: 'anicca-002',
    host: 'local',
    hostLabel: '💻 local · JP',
    model: '○ free',
    balance: 0.90,
    status: 'warning',
  },
];

const ACTIVITY_LOG = [
  { time: '14:00', icon: '💰', label: '0xwork #412', delta: '+$3.00' },
  { time: '18:00', icon: '💰', label: 'litcoin 0.8 mined', delta: '+$0.80' },
  { time: '22:00', icon: '📈', label: 'yield compound', delta: '+$0.12' },
];

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

      {/* ── Money (hero — spec20 §3 primary card) ── */}
      <Section>
        <Reveal>
          <h1 className="sr-only">Your Anicca Instance</h1>
          <Card className="border-[hsl(var(--gold))]/40 bg-[hsl(var(--surface-elevated))]">
            <CardLabel>お金</CardLabel>
            <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
              <div className="flex flex-wrap gap-8">
                {/* Sent to you */}
                <div>
                  <p className="text-3xl font-bold text-[hsl(var(--gold))]">
                    ${MONEY.sentToYou.toFixed(2)}
                  </p>
                  <p className="mt-0.5 text-xs text-[hsl(var(--text-secondary))]">
                    あなたへ送金済
                  </p>
                </div>
                {/* Earned this month */}
                <div>
                  <p className="text-3xl font-bold text-[hsl(var(--text-primary))]">
                    ${MONEY.earnedThisMonth.toFixed(2)}
                  </p>
                  <p className="mt-0.5 text-xs text-[hsl(var(--text-secondary))]">
                    今月の稼ぎ
                  </p>
                </div>
                {/* Subscription status */}
                <div>
                  <p className="text-base font-semibold text-emerald-400">
                    {MONEY.subscriptionCancelled ? '解約済（自給）' : '稼働中 $30/mo'}
                  </p>
                  <p className="mt-0.5 text-xs text-[hsl(var(--text-secondary))]">
                    サブスク
                  </p>
                </div>
              </div>

              {/* Withdraw CTA — links to Stripe portal once wired (task#83) */}
              <a
                href="https://billing.stripe.com/p/login/anicca"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 rounded-pill bg-[hsl(var(--gold))] px-5 py-2.5 text-sm font-semibold text-[#18181b] transition-all duration-300 hover:brightness-95 active:scale-[0.98] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--gold))]"
              >
                銀行に引き出す →
              </a>
            </div>
          </Card>
        </Reveal>
      </Section>

      {/* ── Instance + Colony cards (2-up) ── */}
      <Section>
        <Reveal>
          <div className="grid gap-4 md:grid-cols-2">
            {/* Your Anicca */}
            <Card>
              <CardLabel>あなたのAnicca</CardLabel>
              <div className="flex items-start gap-3">
                <StatusDot status={GENESIS.status} />
                <div className="min-w-0 flex-1">
                  <p className="font-semibold text-[hsl(var(--text-primary))]">
                    {GENESIS.id}
                  </p>
                  <p className="mt-0.5 text-xs text-[hsl(var(--text-secondary))] truncate">
                    {GENESIS.host}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-4">
                    <div>
                      <p className="text-xs text-[hsl(var(--text-secondary))]">モデル</p>
                      <p className="text-sm font-medium text-[hsl(var(--text-primary))]">
                        {GENESIS.model}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-[hsl(var(--text-secondary))]">残高</p>
                      <p className="text-sm font-medium text-[hsl(var(--text-primary))]">
                        ${GENESIS.balance.toFixed(2)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-[hsl(var(--text-secondary))]">残命</p>
                      <p className="text-sm font-medium text-amber-400">
                        ☠ {GENESIS.runwayDays}日後
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </Card>

            {/* Colony summary */}
            <Card>
              <CardLabel>全体</CardLabel>
              <div className="space-y-3">
                <div>
                  <p className="text-2xl font-bold text-[hsl(var(--text-primary))]">
                    ${COLONY.totalAssets.toFixed(2)}
                  </p>
                  <p className="text-xs text-[hsl(var(--text-secondary))]">総資産</p>
                </div>
                <div className="flex flex-wrap gap-4 text-sm">
                  <span className="text-[hsl(var(--text-primary))]">
                    体数{' '}
                    <strong>{COLONY.instanceCount}</strong>
                    <span className="text-[hsl(var(--text-secondary))]">
                      {' '}(あなた1 + 自己増殖{COLONY.instanceCount - 1})
                    </span>
                  </span>
                </div>
                <p className="text-xs text-emerald-400 font-medium">
                  {COLONY.selfFunded ? '✓ server + compute 自給中' : 'まだ自給未達'}
                </p>
                <Link
                  href="/dashboard"
                  className="block text-xs underline underline-offset-4 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors"
                >
                  全コロニーを見る →
                </Link>
              </div>
            </Card>
          </div>
        </Reveal>
      </Section>

      {/* ── Children (self-spawned) ── */}
      <Section>
        <Reveal>
          <CardLabel>子（自己増殖）</CardLabel>
          <div className="grid gap-3 sm:grid-cols-2">
            {CHILDREN.map((child) => (
              <Card key={child.id}>
                <div className="flex items-center gap-2">
                  <StatusDot status={child.status} />
                  <span className="text-sm font-semibold text-[hsl(var(--text-primary))]">
                    {child.id}
                  </span>
                </div>
                <div className="mt-2 flex flex-wrap gap-3 text-xs text-[hsl(var(--text-secondary))]">
                  <span>{child.hostLabel}</span>
                  <span>{child.model}</span>
                  <span className="font-medium text-[hsl(var(--text-primary))]">
                    ${child.balance.toFixed(2)}
                  </span>
                  {child.status === 'warning' && (
                    <span className="text-amber-400">⚠ 残少</span>
                  )}
                </div>
              </Card>
            ))}
          </div>
        </Reveal>
      </Section>

      {/* ── Activity log (24h) ── */}
      <Section>
        <Reveal>
          <Card>
            <CardLabel>行動ログ（直近24h）</CardLabel>
            <ul className="space-y-2">
              {ACTIVITY_LOG.map((entry) => (
                <li
                  key={`${entry.time}-${entry.label}`}
                  className="flex items-center gap-3 text-sm"
                >
                  <span className="w-10 text-xs text-[hsl(var(--text-secondary))] tabular-nums shrink-0">
                    {entry.time}
                  </span>
                  <span>{entry.icon}</span>
                  <span className="flex-1 text-[hsl(var(--text-secondary))] truncate">
                    {entry.label}
                  </span>
                  <span className="font-mono text-xs text-emerald-400 shrink-0">
                    {entry.delta}
                  </span>
                </li>
              ))}
            </ul>
            <p className="mt-3 text-[10px] text-[hsl(var(--text-secondary))]">
              ☎ 起こし / ✉ メールは文脈連携時のみ表示
            </p>
          </Card>
        </Reveal>
      </Section>

      {/* ── Life context (optional, shown when connected) ── */}
      <Section>
        <Reveal>
          <Card>
            <CardLabel>あなたの生活（連携時のみ）</CardLabel>
            <p className="text-sm text-[hsl(var(--text-secondary))]">
              次:{' '}
              <strong className="text-[hsl(var(--text-primary))]">Team Sync 9:30</strong>
              {'  ·  '}受信: 要対応{' '}
              <strong className="text-[hsl(var(--text-primary))]">2</strong> / 処理済{' '}
              <span>8</span>
            </p>
            <p className="mt-3 text-[10px] text-[hsl(var(--text-secondary))]">
              カレンダー・メール連携後に実データに切り替わります。
            </p>
          </Card>
        </Reveal>
      </Section>

      {/* ── Action buttons ── */}
      <Section>
        <Reveal>
          <div className="flex flex-wrap gap-3">
            <a
              href="https://t.me/AniccaLifeBot"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 rounded-pill border border-[hsl(var(--border))] bg-[hsl(var(--surface))] px-5 py-2.5 text-sm font-medium text-[hsl(var(--text-primary))] transition-colors hover:bg-[hsl(var(--surface-elevated))] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--gold))]"
            >
              Aniccaと話す
            </a>
            <button
              type="button"
              disabled
              className="inline-flex items-center gap-2 rounded-pill border border-[hsl(var(--border))] bg-[hsl(var(--surface))] px-5 py-2.5 text-sm font-medium text-[hsl(var(--text-secondary))] cursor-not-allowed opacity-60"
            >
              一時停止
            </button>
            <button
              type="button"
              disabled
              className="inline-flex items-center gap-2 rounded-pill border border-[hsl(var(--border))] bg-[hsl(var(--surface))] px-5 py-2.5 text-sm font-medium text-[hsl(var(--text-secondary))] cursor-not-allowed opacity-60"
            >
              日次報告
            </button>
          </div>
          <p className="mt-3 text-xs text-[hsl(var(--text-secondary))]">
            一時停止 · 日次報告は Stripe 課金後に有効化されます。
          </p>
        </Reveal>
      </Section>

      {/* ── Bottom nav links ── */}
      <Section>
        <Reveal>
          <div className="grid gap-4 md:grid-cols-2">
            <Link
              href="/install"
              className="block rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-5 transition-colors hover:bg-[hsl(var(--surface-elevated))]"
            >
              <p className="text-xs uppercase tracking-widest text-[hsl(var(--text-secondary))]">
                new instance
              </p>
              <p className="mt-2 text-base font-semibold text-[hsl(var(--text-primary))]">
                aniccaai.com/install
              </p>
              <p className="mt-1 text-xs text-[hsl(var(--text-secondary))]">
                Cloud $30/mo · または OSS で無料自己ホスト
              </p>
            </Link>
            <Link
              href="/dashboard"
              className="block rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-5 transition-colors hover:bg-[hsl(var(--surface-elevated))]"
            >
              <p className="text-xs uppercase tracking-widest text-[hsl(var(--text-secondary))]">
                live colony
              </p>
              <p className="mt-2 text-base font-semibold text-[hsl(var(--text-primary))]">
                aniccaai.com/dashboard
              </p>
              <p className="mt-1 text-xs text-[hsl(var(--text-secondary))]">
                全個体のリアルタイム収支 · P&L 公開
              </p>
            </Link>
          </div>
        </Reveal>
      </Section>

      <Footer locale="en" />
    </>
  );
}
