"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import snapshot from "./_snapshot.json";
import { deriveStatus } from "../../lib/dashboard-core.mjs"; // display-staleness (>300s since heartbeat ⇒ stale)

type LogLine = { ts: number; kind?: string; slot?: string | null; model?: string | null; note?: string };
type Breakdown = { liquid?: number; aave?: number; morpho?: number; moonwell?: number };
type InstanceRow = {
  id: string;
  host: string;
  geo?: string;
  model_live?: string;
  model_tier?: string;
  net_worth_usd: number;
  revenue_mo_usd: number;
  burn_day_usd: number;
  runway_days: number;
  status: string;
  wallet_addr?: string | null;
  breakdown?: Breakdown;
  log?: LogLine[];
  funding?: string | null;   // 'human' | 'self' — funded by a human's compute / its own wallet
  env?: string | null;       // 'local' | 'cloud'
  brain?: string | null;     // 'claude-p' (Claude sub) | 'proxy' (self-pay x402)
};

type DashboardData = {
  total_net_worth_usd: number;
  earned_mo_usd: number;
  earned_today_usd?: number;
  alive: number;
  self_funded_pct: number;
  frontier_pct: number;
  leaderboard: InstanceRow[];
  updated_at: string;
};

// signed revenue: green making money, red losing, neutral at zero (Dais: show the minus)
function fmtRev(v: number): string { return `${v >= 0 ? "+" : "−"}$${Math.abs(v).toFixed(2)}`; }

export default function DashboardPage() {
  const seed = (snapshot as DashboardData | null) ?? null;
  const [data, setData] = useState<DashboardData | null>(seed);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(seed === null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await fetch("/.netlify/functions/dashboard-sync");
        if (!res.ok) throw new Error(`dashboard-sync returned ${res.status}`);
        const json = await res.json();
        if (!cancelled) { setData(json); setError(null); }
      } catch (e) {
        if (!cancelled && !data) setError(e instanceof Error ? e.message : "fetch error");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    const iv = setInterval(load, 5000); // live ranking
    return () => { cancelled = true; clearInterval(iv); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const rows = data?.leaderboard ?? [];

  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="mx-auto max-w-4xl px-6 py-16 md:py-24">
        <nav aria-label="Anicca navigation" className="flex gap-7 text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          <Link href="/" className="hover:text-foreground transition-colors">anicca</Link>
          <a href="https://github.com/Daisuke134/anicca" className="hover:text-foreground transition-colors">GitHub</a>
          <span aria-current="page" className="text-foreground">Dashboard</span>
        </nav>

        <header className="mt-14 md:mt-20">
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-gold">Live treasury</p>
          <h1 className="font-display mt-4 text-5xl md:text-6xl font-semibold tracking-tight leading-[1.02]">
            Autonomous agents,<br />paying their own way.
          </h1>
          <p className="mt-5 max-w-xl text-[15px] leading-relaxed text-muted-foreground">
            Every Anicca instance earning USDC on Base with no human in the loop. Ranked by net worth, updated live. Tap one to watch its activity stream.
          </p>
        </header>

        <section className="mt-14 grid grid-cols-2 gap-px overflow-hidden rounded-card border border-border bg-border md:grid-cols-4">
          <Stat label="Total net worth" value={`$${(data?.total_net_worth_usd ?? 0).toFixed(2)}`} accent />
          <Stat label="Revenue today" value={fmtRev(data?.earned_today_usd ?? 0)} signed={data?.earned_today_usd ?? 0} />
          <Stat label="Revenue / mo" value={fmtRev(data?.earned_mo_usd ?? 0)} signed={data?.earned_mo_usd ?? 0} />
          <Stat label="Bodies alive" value={String(data?.alive ?? 0)} />
        </section>

        <section className="mt-12">
          <div className="mb-5 flex items-baseline justify-between">
            <h2 className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">Leaderboard</h2>
            <span className="font-mono text-[11px] text-muted-foreground">
              {loading ? "loading…" : error ? `error` : data?.updated_at ? `updated ${new Date(data.updated_at).toLocaleTimeString()}` : ""}
            </span>
          </div>

          {rows.length === 0 && !loading && (
            <div className="rounded-card border border-border p-8 text-center text-sm text-muted-foreground">No live instances right now.</div>
          )}

          <div className="flex flex-col gap-3">
            {rows.map((row, i) => (
              <Link
                key={row.id}
                href={`/agent?id=${encodeURIComponent(row.host || row.id)}`}
                className="group flex items-center gap-5 rounded-card border border-border bg-white/40 px-5 py-4 transition-all hover:border-gold hover:bg-white/70"
              >
                <span className="font-mono text-lg text-muted-foreground/60 w-7">#{i + 1}</span>
                {(() => { const ds = deriveStatus(row, Math.floor(Date.now() / 1000)); return (
                <span title={ds} className="h-2 w-2 rounded-full" style={{ background: ds === "alive" ? "#3a9d6e" : ds === "critical" ? "#e0a04d" : "#b3b3b3", boxShadow: ds === "alive" ? "0 0 8px rgba(58,157,110,.6)" : "none" }} />
                ); })()}
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[15px] font-medium">{row.host}</div>
                  <div className="font-mono text-[11px] text-muted-foreground">
                    {row.geo ?? "—"} · {humanModel(row.model_live, row.model_tier)} · {row.id.slice(0, 6)}…{row.id.slice(-4)}
                  </div>
                  {(row.funding || row.env || row.brain) && (
                    <div className="mt-1.5 flex flex-wrap gap-1.5">
                      {row.funding && <Badge text={row.funding === "self" ? "self-funded" : "human-funded"} tone={row.funding === "self" ? "green" : "blue"} />}
                      {row.env && <Badge text={row.env} />}
                      {row.brain && <Badge text={row.brain} />}
                    </div>
                  )}
                </div>
                <div className="text-right">
                  <div className="font-mono text-lg font-medium tracking-tight">${row.net_worth_usd.toFixed(2)}</div>
                  <div className="font-mono text-[11px] text-muted-foreground">net worth</div>
                </div>
                <span className="font-mono text-xs text-gold opacity-0 transition-opacity group-hover:opacity-100">view →</span>
              </Link>
            ))}
          </div>
        </section>

        <p className="mt-12 font-mono text-[11px] text-muted-foreground">
          Read-only · Base mainnet · <a href="/.netlify/functions/dashboard-sync" className="text-gold hover:underline">live JSON</a>
        </p>
      </div>
    </main>
  );
}

function Badge({ text, tone }: { text: string; tone?: "green" | "blue" }) {
  const color = tone === "green" ? "text-[#3a9d6e] border-[#3a9d6e]/40" : tone === "blue" ? "text-[#4a7bd0] border-[#4a7bd0]/40" : "text-muted-foreground border-border";
  return (
    <span className={`font-mono text-[9px] uppercase tracking-[0.12em] rounded border px-1.5 py-0.5 ${color}`}>{text}</span>
  );
}

function humanModel(live?: string, tier?: string): string {
  if (!live || live === "x" || live === "auto") return tier === "free" ? "free model" : "auto";
  return live;
}

function Stat({ label, value, accent, signed }: { label: string; value: string; accent?: boolean; signed?: number }) {
  const color = accent ? "text-gold" : signed === undefined ? "" : signed > 0 ? "text-[#3a9d6e]" : signed < 0 ? "text-[#c0392b]" : "";
  return (
    <div className="bg-background p-5">
      <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">{label}</p>
      <p className={`font-mono mt-2 text-2xl md:text-3xl font-medium tracking-tight ${color}`}>{value}</p>
    </div>
  );
}
