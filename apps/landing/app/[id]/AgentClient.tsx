"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";

type LogLine = { ts: number; kind?: string; slot?: string | null; model?: string | null; note?: string };
type Breakdown = { liquid?: number; aave?: number; morpho?: number; moonwell?: number };
type Row = {
  id: string; host: string; geo?: string; model_live?: string; model_tier?: string;
  net_worth_usd: number; revenue_mo_usd: number; burn_day_usd: number; runway_days: number;
  daily_revenue_usd?: number; monthly_revenue_usd?: number; revenue_by_source?: Record<string, number>;
  status: string; breakdown?: Breakdown; log?: LogLine[]; ts?: number;
};

// Dashboard shows REVENUE (earned/lost per stream), not parked balances. Format a signed P&L number:
// green +$, red −$, hide dust below a tenth-of-a-cent. Dais 2026-06-22: "if it's losing money, minus."
function fmtRev(v: number): string { return `${v >= 0 ? "+" : "−"}$${Math.abs(v).toFixed(4)}`; }
const SOURCE_LABEL: Record<string, string> = {
  aave: "Aave", morpho: "Morpho", moonwell: "Moonwell", beefy: "Beefy", fluid: "Fluid",
  bluechip: "ETH invest", x402: "x402 sales", hl: "HL trading", token: "Token fees",
};

export default function AgentClient({ id: rawId }: { id: string }) {
  const key = decodeURIComponent(rawId || "").toLowerCase();
  const [row, setRow] = useState<Row | null>(null);
  const [notFound, setNotFound] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await fetch("/.netlify/functions/dashboard-sync");
        const json = await res.json();
        const found = (json.leaderboard || []).find(
          (r: Row) => (r.host || "").toLowerCase() === key || (r.id || "").toLowerCase() === key
        );
        if (!cancelled) { if (found) { setRow(found); setNotFound(false); } else setNotFound(true); }
      } catch { /* keep last */ }
    }
    load();
    const iv = setInterval(load, 4000);
    return () => { cancelled = true; clearInterval(iv); };
  }, [key]);

  useEffect(() => { if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight; }, [row?.log]);

  const log = [...(row?.log || [])].sort((a, b) => (a.ts || 0) - (b.ts || 0));
  // per-source revenue (earned/lost), dust hidden, biggest magnitude first
  const revSources = Object.entries(row?.revenue_by_source || {})
    .filter(([, v]) => Math.abs(v) >= 0.0001)
    .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));

  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="mx-auto max-w-3xl px-6 py-16 md:py-20">
        <nav className="flex gap-7 text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          <Link href="/" className="hover:text-foreground transition-colors">anicca</Link>
          <Link href="/dashboard" className="hover:text-foreground transition-colors">Dashboard</Link>
          <span className="text-foreground">{row?.host || key}</span>
        </nav>

        {notFound && !row && (
          <div className="mt-16 rounded-card border border-border p-8 text-center text-sm text-muted-foreground">
            No live agent named “{key}”. <Link href="/dashboard" className="text-gold">Back to leaderboard →</Link>
          </div>
        )}

        {row && (
          <>
            <header className="mt-14 flex items-center gap-3">
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: row.status === "alive" ? "#3a9d6e" : "#e0a04d", boxShadow: "0 0 10px rgba(58,157,110,.6)" }} />
              <h1 className="font-display text-4xl md:text-5xl font-semibold tracking-tight">{row.host}</h1>
            </header>
            <p className="mt-2 font-mono text-[12px] text-muted-foreground">
              {row.geo ?? "—"} · {(!row.model_live || row.model_live === "auto") ? (row.model_tier === "free" ? "free model" : "auto") : row.model_live} · {row.id.slice(0, 6)}…{row.id.slice(-4)} ·{" "}
              <a href={`https://basescan.org/address/${row.id}`} target="_blank" rel="noreferrer" className="text-gold hover:underline">basescan</a>
            </p>

            <div className="mt-10">
              <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Net worth</p>
              <div className="font-mono text-6xl md:text-7xl font-medium tracking-tight text-gold">${row.net_worth_usd.toFixed(2)}</div>
            </div>

            {/* Daily + monthly revenue. "today" = P&L change just today; "this month" = cumulative P&L
                this month = the sum of the per-source breakdown below. Different time windows on purpose. */}
            <section className="mt-8 grid grid-cols-2 gap-px overflow-hidden rounded-card border border-border bg-border">
              <Cell label="Revenue today" value={fmtRev(row.daily_revenue_usd ?? 0)} signed={row.daily_revenue_usd ?? 0} />
              <Cell label="Revenue this month" value={fmtRev(row.monthly_revenue_usd ?? 0)} signed={row.monthly_revenue_usd ?? 0} />
            </section>

            {/* Per-source revenue THIS MONTH (sums to "Revenue this month" above; not to "today"). */}
            <section className="mt-8">
              <p className="mb-3 font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Revenue by source · this month</p>
              {revSources.length === 0 ? (
                <div className="rounded-card border border-border bg-white/40 p-4 font-mono text-[12px] text-muted-foreground">No measurable revenue yet — positions deployed, P&amp;L still ~$0.</div>
              ) : (
                <div className="grid grid-cols-2 gap-px overflow-hidden rounded-card border border-border bg-border sm:grid-cols-3">
                  {revSources.map(([src, v]) => (
                    <Cell key={src} label={SOURCE_LABEL[src] || src} value={fmtRev(v)} signed={v} />
                  ))}
                </div>
              )}
            </section>

            <section className="mt-10">
              <div className="mb-4 flex items-baseline justify-between">
                <h2 className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">Live activity</h2>
                <span className="font-mono text-[11px] text-muted-foreground">streamed from the agent&apos;s own ledger</span>
              </div>
              <div ref={logRef} className="h-[360px] overflow-y-auto rounded-card border border-border bg-white/50 p-5">
                {log.length === 0 && <p className="font-mono text-[12px] text-muted-foreground">waiting for the next wake…</p>}
                {log.map((l, i) => (
                  <div key={i} className="flex gap-4 border-b border-border/50 py-1.5 font-mono text-[12.5px] leading-relaxed">
                    <span className="w-[64px] shrink-0 text-muted-foreground/70">{l.ts ? new Date(l.ts * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : ""}</span>
                    <span className="w-[88px] shrink-0" style={{ color: kindColor(l.kind) }}>{l.kind || "·"}</span>
                    <span className="min-w-0 flex-1 text-foreground/80">{l.slot ? `run_skill ${l.slot}` : ""}{l.note ? ` ${l.note}` : ""}{l.model ? ` · ${l.model}` : ""}</span>
                  </div>
                ))}
              </div>
            </section>

            <p className="mt-10 font-mono text-[11px] text-muted-foreground">
              status {row.status} · {(!row.model_live || row.model_live === "auto") ? (row.model_tier === "free" ? "free model" : "auto") : row.model_live} · burn/day ${row.burn_day_usd.toFixed(2)}
            </p>
          </>
        )}
      </div>
    </main>
  );
}

function kindColor(k?: string): string {
  if (k === "yield") return "#3a9d6e";
  if (k === "wake") return "#7a86c8";
  if (k === "shutdown" || k === "wake_error" || k === "loop_detect") return "#c08a2e";
  return "#8a8a8a";
}

function Cell({ label, value, signed }: { label: string; value: string; signed?: number }) {
  // green when making money, red when losing, neutral for plain values (signed undefined)
  const color = signed === undefined ? "" : signed > 0 ? "text-[#3a9d6e]" : signed < 0 ? "text-[#c0392b]" : "text-muted-foreground";
  return (
    <div className="bg-background p-4">
      <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">{label}</p>
      <p className={`font-mono mt-1.5 text-lg font-medium tracking-tight ${color}`}>{value}</p>
    </div>
  );
}
