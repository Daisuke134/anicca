'use client';

import { useEffect, useState } from 'react';
import { translations, type Locale } from '@/lib/i18n';

interface EmpireDashboardProps {
  locale: Locale;
}

interface DashboardData {
  updated_at: string;
  mrr: { total_usd: number; by_product: Record<string, number> };
  followers: { total: number };
  views: { weekly_total: number; target: number; progress_pct: number };
  spend: { total_usd: number };
  profit_usd: number;
  goals: { mrr_target: number; mrr_deadline: string; progress_pct: number };
}

function ProgressBar({ pct }: { pct: number }) {
  const safePct = Math.max(0, Math.min(100, pct));
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
      <div
        className="h-full rounded-full bg-foreground transition-all"
        style={{ width: `${safePct}%` }}
      />
    </div>
  );
}

export default function EmpireDashboard({ locale }: EmpireDashboardProps) {
  const t = translations[locale].empire;
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/dashboard.json')
      .then((r) => (r.ok ? r.json() : Promise.reject('fetch failed')))
      .then(setData)
      .catch((e) => setError(String(e)));
  }, []);

  if (error) {
    return (
      <section className="bg-background px-6 py-16">
        <p className="mx-auto max-w-3xl text-center text-sm text-muted-foreground">
          {t.dashboardOffline}
        </p>
      </section>
    );
  }

  if (!data) {
    return (
      <section className="bg-background px-6 py-16">
        <p className="mx-auto max-w-3xl text-center text-sm text-muted-foreground">
          {t.loading}
        </p>
      </section>
    );
  }

  const mrrPct = data.goals.progress_pct;
  const viewsPct = data.views.progress_pct;
  const updated = new Date(data.updated_at).toLocaleString(
    locale === 'ja' ? 'ja-JP' : 'en-US',
    { hour: '2-digit', minute: '2-digit', month: 'short', day: 'numeric' }
  );

  return (
    <section className="bg-background px-6 py-20">
      <div className="mx-auto max-w-4xl">
        <h2 className="mb-2 text-center text-3xl font-bold text-foreground md:text-4xl">
          {t.title}
        </h2>
        <p className="mb-12 text-center text-sm text-muted-foreground">
          {t.subtitle} · {t.updatedAt} {updated}
        </p>

        <div className="space-y-8">
          {/* MRR */}
          <div>
            <div className="mb-2 flex items-baseline justify-between">
              <span className="font-semibold text-foreground">{t.mrr}</span>
              <span className="font-mono text-lg text-foreground">
                ${data.mrr.total_usd.toLocaleString()} / ${data.goals.mrr_target.toLocaleString()}
              </span>
            </div>
            <ProgressBar pct={mrrPct} />
            <p className="mt-1 text-right text-xs text-muted-foreground">
              {mrrPct.toFixed(1)}% — {t.mrrDeadline} {data.goals.mrr_deadline}
            </p>
          </div>

          {/* Weekly Views */}
          <div>
            <div className="mb-2 flex items-baseline justify-between">
              <span className="font-semibold text-foreground">{t.weeklyViews}</span>
              <span className="font-mono text-lg text-foreground">
                {data.views.weekly_total.toLocaleString()} / {data.views.target.toLocaleString()}
              </span>
            </div>
            <ProgressBar pct={viewsPct} />
            <p className="mt-1 text-right text-xs text-muted-foreground">
              {viewsPct.toFixed(1)}%
            </p>
          </div>

          {/* Followers + Spend in 2-col */}
          <div className="grid grid-cols-2 gap-8">
            <div>
              <p className="text-sm text-muted-foreground">{t.followers}</p>
              <p className="font-mono text-2xl font-semibold text-foreground">
                {data.followers.total.toLocaleString()}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">{t.spendThisMonth}</p>
              <p className="font-mono text-2xl font-semibold text-foreground">
                ${data.spend.total_usd.toLocaleString()}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {t.profit}: ${data.profit_usd.toLocaleString()}
              </p>
            </div>
          </div>
        </div>

        <p className="mt-10 text-center text-xs text-muted-foreground">
          ★ {t.openSource}{' '}
          <a
            href="https://github.com/Daisuke134/anicca"
            target="_blank"
            rel="noopener noreferrer"
            className="underline transition-colors hover:text-foreground"
          >
            github.com/Daisuke134/anicca
          </a>
        </p>
      </div>
    </section>
  );
}
