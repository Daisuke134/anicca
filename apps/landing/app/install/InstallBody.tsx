'use client';

/* eslint-disable react/no-unescaped-entities */
import Link from 'next/link';
import { Section, Reveal, CTA } from '@/components/site/taste';
import { useLaunchLocale } from '@/lib/launchLocale';
import { launchStrings } from '@/lib/launchStrings';

// /install body — localized EN/JA (spec29). Renders inside <LaunchFrame> (provides
// the locale context + nav + footer). Two-column cloud+OSS layout; MUST NOT show raw
// shell commands (git clone) prominently. All copy comes from launchStrings[locale].

function ColumnCard({
  emoji,
  label,
  sublabel,
  recommended,
  recommendedBadge,
  children,
  cta,
}: {
  emoji: string;
  label: string;
  sublabel: string;
  recommended?: boolean;
  recommendedBadge?: string;
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
          {recommendedBadge}
        </span>
      )}
      <div className="flex items-center gap-2 mb-4">
        <span className="text-2xl">{emoji}</span>
        <div>
          <p className="font-semibold text-lg text-[hsl(var(--text-primary))]">{label}</p>
          <p className="text-xs text-[hsl(var(--text-secondary))]">{sublabel}</p>
        </div>
      </div>
      <div className="flex-1 space-y-3 text-sm text-[hsl(var(--text-secondary))]">{children}</div>
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

// Minimal stroke icons (ui-ux-pro-max: "no emoji as icons"). 24×24 viewBox, gold stroke, decorative.
function FeatureIcon({ id }: { id: string }) {
  const d: Record<string, string> = {
    earn: 'M12 1v22M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6',
    call: 'M22 16.92v3a2 2 0 0 1-2.18 2 19.8 19.8 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.8 19.8 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z',
    spawn: 'M12 22V8M5 12a7 7 0 0 1 7-7 7 7 0 0 1 7 7M9 18l3 3 3-3',
    ubi: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zM2 12h20M12 2a15 15 0 0 1 0 20 15 15 0 0 1 0-20z',
    report: 'M3 3v18h18M7 16l4-6 4 4 5-8',
    improve: 'M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15',
  };
  return (
    <svg
      viewBox="0 0 24 24"
      width="24"
      height="24"
      fill="none"
      stroke="hsl(var(--gold))"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="h-6 w-6"
    >
      <path d={d[id] ?? d.report} />
    </svg>
  );
}

export default function InstallBody() {
  const { locale } = useLaunchLocale();
  const t = launchStrings[locale].install;

  return (
    <>
      {/* ── Hero ── */}
      <Section>
        <div className="grid items-center gap-10 md:grid-cols-[1.05fr_0.95fr]">
          <Reveal>
            <div className="max-w-[34rem]">
              <h1 className="font-display text-3xl md:text-5xl font-bold leading-[1.05] tracking-tight text-[hsl(var(--text-primary))]">
                {t.heroTitle}
              </h1>
              <p className="mt-5 max-w-[42ch] text-base leading-relaxed text-[hsl(var(--text-secondary))]">
                {t.heroBody}
              </p>
              <div className="mt-7 flex flex-wrap items-center gap-4">
                <a
                  href="#paths"
                  className="inline-flex items-center justify-center rounded-pill bg-[hsl(var(--gold))] px-6 py-3 text-sm font-semibold text-[#18181b] transition-all duration-200 hover:brightness-95 active:scale-[0.98] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--gold))]"
                >
                  {t.heroCtaPrimary}
                </a>
                <a
                  href="/dashboard"
                  className="text-sm font-medium underline underline-offset-4 text-[hsl(var(--text-secondary))] transition-colors hover:text-[hsl(var(--text-primary))]"
                >
                  {t.heroCtaSecondary}
                </a>
              </div>
            </div>
          </Reveal>
          <Reveal delay={0.1}>
            <div className="space-y-2 rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface-elevated))] p-5 font-mono text-sm">
              <p className="text-[hsl(var(--text-secondary))]">{t.ledger.netWorth}</p>
              <p className="text-emerald-400">{t.ledger.earn}</p>
              <p className="text-[hsl(var(--text-primary))]">{t.ledger.host}</p>
              <p className="text-[hsl(var(--text-secondary))]">{t.ledger.subscription}</p>
              <p className="mt-1 text-xs not-italic text-[hsl(var(--text-secondary))]">
                {t.ledger.caption}
              </p>
            </div>
          </Reveal>
        </div>
      </Section>

      {/* ── Trust strip (honest, verifiable — reuses /me GATE-0 receipt, no new claim) ── */}
      <Section className="pt-0">
        <Reveal>
          <a
            href="https://basescan.org/tx/0xc4f2df3e445acaff01bd004f8503d41582d8acb12a55bf27797d5aea066f721d"
            target="_blank"
            rel="noreferrer"
            className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] px-5 py-3 text-xs text-[hsl(var(--text-secondary))] transition-colors hover:border-[hsl(var(--gold))]/40"
          >
            <span className="font-mono text-emerald-400">{t.trust.net}</span>
            <span>{t.trust.label}</span>
            <span className="underline underline-offset-4">{t.trust.verify}</span>
          </a>
        </Reveal>
      </Section>

      {/* ── 2-column: CLOUD + OSS ── */}
      <Section id="paths">
        <Reveal>
          <div className="grid gap-6 md:grid-cols-2">
            {/* ☁ CLOUD — main product / recommended */}
            <ColumnCard
              emoji="☁"
              label={t.cloud.label}
              sublabel={t.cloud.sublabel}
              recommended
              recommendedBadge={t.recommendedBadge}
              cta={
                <CTA href="/me" variant="primary">
                  {t.cloud.cta}
                </CTA>
              }
            >
              {t.cloud.points.map((p, i) => (
                <CheckItem key={i}>{p}</CheckItem>
              ))}
              <div className="pt-2 border-t border-[hsl(var(--border))]">
                <p className="text-xs text-[hsl(var(--text-secondary))]">
                  <strong className="text-[hsl(var(--text-primary))]">{t.cloud.footnoteStrong}</strong>
                  {t.cloud.footnoteRest}
                </p>
              </div>
            </ColumnCard>

            {/* ⌨ OSS — builders / self-host */}
            <ColumnCard
              emoji="⌨"
              label={t.oss.label}
              sublabel={t.oss.sublabel}
              cta={
                <Link
                  href="https://github.com/Daisuke134/anicca"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 w-full justify-center rounded-pill border border-[hsl(var(--border))] bg-[hsl(var(--surface))] px-5 py-2.5 text-sm font-semibold text-[hsl(var(--text-primary))] transition-colors hover:bg-[hsl(var(--surface-elevated))] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--gold))]"
                >
                  {t.oss.cta}
                </Link>
              }
            >
              {t.oss.points.map((p, i) => (
                <DotItem key={i}>{p}</DotItem>
              ))}
              <DotItem>
                {t.oss.installPointPre}
                <code className="rounded-input bg-[hsl(var(--surface-elevated))] px-1 py-0.5 text-xs">
                  bash install.sh
                </code>
                {t.oss.installPointPost}
              </DotItem>
              <DotItem>{t.oss.costPoint}</DotItem>
              <div className="pt-2 border-t border-[hsl(var(--border))]">
                <p className="text-xs text-[hsl(var(--text-secondary))]">{t.oss.specNote}</p>
              </div>
            </ColumnCard>
          </div>
        </Reveal>
      </Section>

      {/* ── What Anicca does (shared by both paths) ── */}
      <Section>
        <Reveal>
          <h2 className="font-display text-xl md:text-2xl font-semibold text-[hsl(var(--text-primary))] mb-4">
            {t.whatTitle}
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {t.features.map(({ id, title, desc }) => (
              <div
                key={id}
                className="rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-5 transition-colors hover:border-[hsl(var(--gold))]/30"
              >
                <FeatureIcon id={id} />
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
              className="block rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-5 transition-colors hover:bg-[hsl(var(--surface-elevated))] hover:border-[hsl(var(--gold))]/30"
            >
              <p className="text-xs uppercase tracking-widest text-[hsl(var(--text-secondary))]">
                {t.linkInstanceEyebrow}
              </p>
              <p className="mt-2 text-base font-semibold text-[hsl(var(--text-primary))]">
                aniccaai.com/me
              </p>
              <p className="mt-1 text-xs text-[hsl(var(--text-secondary))]">{t.linkInstanceDesc}</p>
            </Link>
            <Link
              href="/dashboard"
              className="block rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-5 transition-colors hover:bg-[hsl(var(--surface-elevated))] hover:border-[hsl(var(--gold))]/30"
            >
              <p className="text-xs uppercase tracking-widest text-[hsl(var(--text-secondary))]">
                {t.linkColonyEyebrow}
              </p>
              <p className="mt-2 text-base font-semibold text-[hsl(var(--text-primary))]">
                aniccaai.com/dashboard
              </p>
              <p className="mt-1 text-xs text-[hsl(var(--text-secondary))]">{t.linkColonyDesc}</p>
            </Link>
          </div>
        </Reveal>
      </Section>

      {/* ── Footer note ── */}
      <Section>
        <Reveal>
          <div className="border-t border-[hsl(var(--border))] pt-8 text-xs text-[hsl(var(--text-secondary))]">
            <p>
              {t.footerLicense}{' '}
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
    </>
  );
}
