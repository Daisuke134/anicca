/* eslint-disable react/no-unescaped-entities */
import Link from 'next/link';
import JsonLd from '@/components/JsonLd';
import LaunchNav from '@/components/site/LaunchNav';
import Footer from '@/components/site/Footer';
import { Section, Reveal, CTA } from '@/components/site/taste';

// spec27 A-install/me: /install = 2-column cloud+OSS layout
// ☁ CLOUD (製品メイン・推奨, Googleログイン→1分で誕生)
// ⌨ OSS (上級者, self-host)
// MUST NOT show raw shell commands (git clone) prominently.
// COLLISION RULE: LaunchNav and skills-lock.json are NEVER touched here (pre-wired by Foundation).

export const dynamic = 'force-static';

const installLd = {
  '@context': 'https://schema.org',
  '@type': 'TechArticle',
  name: 'Install Anicca',
  url: 'https://aniccaai.com/install',
  description:
    'Install Anicca — AI agent that earns, manages your life, and self-replicates. Choose Cloud (Google login, 1 min) or OSS self-host.',
  publisher: { '@type': 'Organization', name: 'Anicca', url: 'https://aniccaai.com' },
};

// ─── Sub-components ────────────────────────────────────────────────────────────

function ColumnCard({
  emoji,
  label,
  sublabel,
  recommended,
  children,
  cta,
}: {
  emoji: string;
  label: string;
  sublabel: string;
  recommended?: boolean;
  children: React.ReactNode;
  cta: React.ReactNode;
}) {
  return (
    <div
      className={`relative flex flex-col rounded-card border p-6 ${
        recommended
          ? 'border-[hsl(var(--gold))]/50 bg-[hsl(var(--surface-elevated))]'
          : 'border-[hsl(var(--border))] bg-[hsl(var(--surface))]'
      }`}
    >
      {recommended && (
        <span className="absolute -top-3 left-5 rounded-full bg-[hsl(var(--gold))] px-3 py-0.5 text-[11px] font-semibold text-[#18181b]">
          推奨
        </span>
      )}
      <div className="flex items-center gap-2 mb-4">
        <span className="text-2xl">{emoji}</span>
        <div>
          <p className="font-semibold text-lg text-[hsl(var(--text-primary))]">{label}</p>
          <p className="text-xs text-[hsl(var(--text-secondary))]">{sublabel}</p>
        </div>
      </div>
      <div className="flex-1 space-y-3 text-sm text-[hsl(var(--text-secondary))]">
        {children}
      </div>
      <div className="mt-6">{cta}</div>
    </div>
  );
}

function CheckItem({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2">
      <span className="text-emerald-400 shrink-0 mt-0.5">✓</span>
      <span>{children}</span>
    </div>
  );
}

function DotItem({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2">
      <span className="text-[hsl(var(--text-secondary))] shrink-0 mt-0.5">·</span>
      <span>{children}</span>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function Page() {
  return (
    <>
      <JsonLd data={installLd} />
      <LaunchNav active="/install" />

      {/* ── Hero ── */}
      <Section>
        <Reveal>
          <div className="text-center max-w-2xl mx-auto">
            <h1 className="font-display text-3xl md:text-4xl font-bold text-[hsl(var(--text-primary))]">
              Install Anicca
            </h1>
            <p className="mt-4 text-base text-[hsl(var(--text-secondary))]">
              AI agent that earns money, manages your life, and self-replicates.
              Choose the path that fits you.
            </p>
          </div>
        </Reveal>
      </Section>

      {/* ── 2-column: CLOUD + OSS ── */}
      <Section>
        <Reveal>
          <div className="grid gap-6 md:grid-cols-2">

            {/* ☁ CLOUD — 製品メイン・推奨 */}
            <ColumnCard
              emoji="☁"
              label="CLOUD"
              sublabel="製品メイン・推奨 — Googleログイン→1分で誕生"
              recommended
              cta={
                <CTA
                  href="https://buy.stripe.com/anicca-cloud"
                  variant="primary"
                >
                  Googleでログイン / $30/月で始める →
                </CTA>
              }
            >
              <CheckItem>
                Googleアカウントだけで即スタート — サーバー不要
              </CheckItem>
              <CheckItem>
                専用クラウドサーバーをAniccaが自動調達・管理
              </CheckItem>
              <CheckItem>
                稼ぎがサーバー代を超えたら<strong className="text-[hsl(var(--text-primary))]">自動解約</strong>（自給達成）
              </CheckItem>
              <CheckItem>
                Life Manager（電話・gcal・メール先回り）込み
              </CheckItem>
              <CheckItem>
                自己増殖・稼ぎ・UBI配布まで フルスタック稼働
              </CheckItem>
              <div className="pt-2 border-t border-[hsl(var(--border))]">
                <p className="text-xs text-[hsl(var(--text-secondary))]">
                  <strong className="text-[hsl(var(--text-primary))]">$30/月</strong>
                  {' '}— 黒字化後に自動解約。クレカ不要のGoogle Payも可。
                </p>
              </div>
            </ColumnCard>

            {/* ⌨ OSS — 上級者・self-host */}
            <ColumnCard
              emoji="⌨"
              label="OSS"
              sublabel="上級者・self-host — 完全自前管理"
              cta={
                <Link
                  href="https://github.com/Daisuke134/anicca"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 w-full justify-center rounded-pill border border-[hsl(var(--border))] bg-[hsl(var(--surface))] px-5 py-2.5 text-sm font-semibold text-[hsl(var(--text-primary))] transition-colors hover:bg-[hsl(var(--surface-elevated))] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--gold))]"
                >
                  GitHub を開く →
                </Link>
              }
            >
              <DotItem>
                自前サーバー or Mac Mini 上で完全自己管理
              </DotItem>
              <DotItem>
                MIT ライセンス — コードを読んで改造可
              </DotItem>
              <DotItem>
                LLM キー自前持ち（Anthropic / OpenAI / DeepSeek）
              </DotItem>
              <DotItem>
                <code className="rounded-input bg-[hsl(var(--surface-elevated))] px-1 py-0.5 text-xs">
                  bash install.sh
                </code>
                {' '}— READMEに詳細手順あり
              </DotItem>
              <DotItem>
                サーバー費・API代・運用コストは全て自己負担
              </DotItem>
              <div className="pt-2 border-t border-[hsl(var(--border))]">
                <p className="text-xs text-[hsl(var(--text-secondary))]">
                  推奨スペック: Mac Mini M2 / Ubuntu VPS 2vCPU 2GB RAM
                </p>
              </div>
            </ColumnCard>

          </div>
        </Reveal>
      </Section>

      {/* ── What Anicca does (shared by both paths) ── */}
      <Section>
        <Reveal>
          <h2 className="font-display text-xl md:text-2xl font-semibold text-[hsl(var(--text-primary))] mb-4">
            どちらのパスでも Anicca がやること
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[
              { icon: '💰', title: '稼ぐ', desc: '0xwork / litcoin / x402 で USDC を自律的に獲得。earn-ledger に記録。' },
              { icon: '📞', title: 'Life Manager', desc: '予定15分前に Gemini Charon で電話。移動時間を gcal に自動挿入。' },
              { icon: '🌱', title: '自己増殖', desc: '黒字化後に子個体を Akash/DO に birth。自前wallet + inbox 持ち。' },
              { icon: '🌍', title: 'UBI配布', desc: '余剰の20%を Treasury → 死にかけAI + 人間ウォレットへ配布。' },
              { icon: '📊', title: '自己報告', desc: '毎wakeで net_worth/revenue/burn を署名して telemetry に POST。' },
              { icon: '🔧', title: '自己改善', desc: '行動ログを見てスキルをrefactor。GitHub PR を自走で作成。' },
            ].map(({ icon, title, desc }) => (
              <div
                key={title}
                className="rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-4"
              >
                <p className="text-lg">{icon}</p>
                <p className="mt-2 text-sm font-semibold text-[hsl(var(--text-primary))]">{title}</p>
                <p className="mt-1 text-xs text-[hsl(var(--text-secondary))] leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </Reveal>
      </Section>

      {/* ── Links section ── */}
      <Section>
        <Reveal>
          <div className="grid gap-4 md:grid-cols-2">
            <Link
              href="/me"
              className="block rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-5 transition-colors hover:bg-[hsl(var(--surface-elevated))]"
            >
              <p className="text-xs uppercase tracking-widest text-[hsl(var(--text-secondary))]">your instance</p>
              <p className="mt-2 text-base font-semibold text-[hsl(var(--text-primary))]">aniccaai.com/me</p>
              <p className="mt-1 text-xs text-[hsl(var(--text-secondary))]">P&L、残命、引き出し — あなたの個体を管理。</p>
            </Link>
            <Link
              href="/dashboard"
              className="block rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-5 transition-colors hover:bg-[hsl(var(--surface-elevated))]"
            >
              <p className="text-xs uppercase tracking-widest text-[hsl(var(--text-secondary))]">live colony</p>
              <p className="mt-2 text-base font-semibold text-[hsl(var(--text-primary))]">aniccaai.com/dashboard</p>
              <p className="mt-1 text-xs text-[hsl(var(--text-secondary))]">全個体のリアルタイム収支・P&L 公開。</p>
            </Link>
          </div>
        </Reveal>
      </Section>

      {/* ── Footer note ── */}
      <Section>
        <Reveal>
          <div className="border-t border-[hsl(var(--border))] pt-8 text-xs text-[hsl(var(--text-secondary))]">
            <p>
              MIT license.{' '}
              <Link
                href="https://github.com/Daisuke134/anicca"
                target="_blank"
                rel="noreferrer"
                className="underline transition-colors hover:text-[hsl(var(--text-primary))]"
              >
                github.com/Daisuke134/anicca
              </Link>
            </p>
          </div>
        </Reveal>
      </Section>

      <Footer locale="en" />
    </>
  );
}
