"use client";

import { useEffect, useState } from "react";
// PURE render helpers (REQ-4/5/6/8) — single source of display logic, unit-tested separately.
import { toCardModel, countByStatus } from "../../lib/dashboard-core.mjs";

// Metadata is exported from a separate layout or via static export approach
// (app/dashboard/layout.tsx) — cannot use export const metadata in "use client".

type InstanceRow = {
  id: string;
  host: string;
  geo?: string;
  ts?: number;
  model_live?: string;
  model_tier?: string;
  net_worth_usd: number;
  revenue_mo_usd: number;
  burn_day_usd: number;
  runway_days: number;
  status: string;
  wallet_addr?: string | null;
  funding?: string | null;
  env?: string | null;
  brain?: string | null;
  log?: Array<{ ts: number; kind: string; note?: string }>;
};

type DashboardData = {
  total_net_worth_usd: number;
  earned_mo_usd: number;
  alive: number;
  self_funded_pct: number;
  frontier_pct: number;
  leaderboard: InstanceRow[];
  updated_at: string;
};

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await fetch("/.netlify/functions/dashboard-sync");
        if (!res.ok) throw new Error(`dashboard-sync returned ${res.status}`);
        const json = await res.json();
        if (!cancelled) setData(json);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "fetch error");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    // REQ-10: refresh from the live registry every 30s (< the 120s telemetry heartbeat) so the board is
    // near-real-time. Polling (not websocket) is the chosen mechanism for static-export compatibility.
    const timer = setInterval(load, 30_000);
    return () => { cancelled = true; clearInterval(timer); };
  }, []);

  return (
    <main style={{ background: "#0a0a0a", color: "#f4f1ea", minHeight: "100vh", fontFamily: "IBM Plex Sans, sans-serif", padding: "40px 24px" }}>
      <div style={{ maxWidth: 960, margin: "0 auto" }}>
        {/* Foundation pre-wired nav — DO NOT EDIT (Foundation owns nav) */}
        <nav aria-label="Anicca launch navigation" style={{ display: "flex", gap: 20, fontSize: 12, letterSpacing: 4, textTransform: "uppercase" }}>
          <a href="/" style={{ color: "#f4f1ea", opacity: 0.6, textDecoration: "none" }}>← anicca</a>
          <a href="/install" style={{ color: "#f4f1ea", opacity: 0.6, textDecoration: "none" }}>Install</a>
          <a href="/me" style={{ color: "#f4f1ea", opacity: 0.6, textDecoration: "none" }}>Me</a>
          <a href="/dashboard" aria-current="page" style={{ color: "#f4f1ea", opacity: 1, textDecoration: "underline", textUnderlineOffset: 4 }}>Dashboard</a>
          <a href="/life-manager" style={{ color: "#f4f1ea", opacity: 0.6, textDecoration: "none" }}>Life Manager</a>
        </nav>

        <h1 style={{ fontSize: 56, fontWeight: 900, marginTop: 24 }}>Dashboard</h1>
        <p style={{ opacity: 0.6, fontSize: 14 }}>
          {loading ? "Loading…" : error ? `Error: ${error}` : `Live · ${data?.updated_at ? new Date(data.updated_at).toLocaleString("ja-JP") : "?"}`}
        </p>

        {loading && <Skeleton />}
        {error && <ErrorCard message={error} />}
        {!loading && !error && data && <DashboardBody data={data} />}
      </div>
    </main>
  );
}

function DashboardBody({ data }: { data: DashboardData }) {
  const counts = countByStatus(data.leaderboard, Math.floor(Date.now() / 1000));
  return (
    <>
      {/* Group P&L — summary metrics */}
      <section style={{ marginTop: 40, padding: 24, border: "1px solid rgba(244,241,234,0.15)" }}>
        <h2 style={{ fontSize: 14, letterSpacing: 4, textTransform: "uppercase", opacity: 0.7, marginBottom: 16 }}>Group P&amp;L</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 24 }}>
          <Stat label="Total Net Worth" value={`$${data.total_net_worth_usd.toFixed(2)}`} />
          <Stat label="Earned / mo" value={`$${data.earned_mo_usd.toFixed(2)}`} />
          <Stat label="Bodies (alive / stale)" value={`${counts.alive} / ${counts.stale}`} />
          <Stat label="Self-funded %" value={`${data.self_funded_pct}%`} />
          <Stat label="Frontier model %" value={`${data.frontier_pct}%`} />
        </div>
      </section>

      {/* Leaderboard */}
      <section style={{ marginTop: 40 }}>
        <h2 style={{ fontSize: 14, letterSpacing: 4, textTransform: "uppercase", opacity: 0.7, marginBottom: 16 }}>
          Leaderboard ({data.leaderboard.length} bodies)
        </h2>
        <div style={{ display: "grid", gap: 16 }}>
          {data.leaderboard.map((row, i) => (
            <InstanceCard key={row.id} row={row} rank={i + 1} />
          ))}
        </div>
      </section>

      <p style={{ fontSize: 11, opacity: 0.5, marginTop: 32 }}>
        Data: <a href="/.netlify/functions/dashboard-sync" style={{ color: "#c8302e" }}>live JSON</a>
        {" · "}Source: <a href="https://github.com/Daisuke134/anicca-products" style={{ color: "#c8302e" }}>anicca-products</a>
      </p>
    </>
  );
}

function InstanceCard({ row, rank }: { row: InstanceRow; rank: number }) {
  // All display logic via the PURE core (display-staleness, self-funded test, view-model, log cap/order).
  const c = toCardModel(row, Math.floor(Date.now() / 1000));
  return (
    <div style={{ border: "1px solid rgba(244,241,234,0.15)", padding: 20 }}>
      <div style={{ display: "grid", gridTemplateColumns: "auto 1fr auto", gap: 16, alignItems: "flex-start" }}>
        <div style={{ fontSize: 24, opacity: 0.3, fontWeight: 900, minWidth: 32 }}>#{rank}</div>
        <div>
          <p style={{ fontSize: 18 }}>{c.host} · {row.geo ?? "?"}</p>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 6 }}>
            <Tag text={c.funding === "human" ? "HUMAN-FUNDED" : c.funding === "self" ? "SELF-FUNDED" : "FUNDING?"} tone={c.funding === "self" ? "green" : "blue"} />
            <Tag text={String(c.env).toUpperCase()} tone="dim" />
            <Tag text={String(c.brain)} tone="dim" />
            <Tag text={`${c.model} · ${c.modelTier}`} tone="dim" />
            {c.selfFundedEconomic && <Tag text="ECON SELF-FUNDED" tone="green" />}
          </div>
          <a href={c.walletUrl ?? "#"} target="_blank" rel="noopener noreferrer"
             style={{ fontSize: 11, color: "#c8302e", textDecoration: "none", marginTop: 6, display: "inline-block" }}>
            {c.id ? `${c.id.slice(0, 6)}…${c.id.slice(-4)}` : ""}
          </a>
        </div>
        <StatusBadge status={c.statusDisplay} />
      </div>

      <div style={{
        marginTop: 12, paddingTop: 12, borderTop: "1px solid rgba(244,241,234,0.08)",
        display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 12,
      }}>
        <Metric label="Assets" value={`$${c.assetsUsd.toFixed(2)}`} />
        <Metric label="Revenue / mo" value={`$${c.revenueMoUsd.toFixed(2)}`} />
        <Metric label="Burn / day" value={`$${c.burnDayUsd.toFixed(2)}`} />
        <Metric label="Net / mo" value={`$${c.netUsd.toFixed(2)}`} highlight={c.netUsd >= 0} />
      </div>

      {c.logs.length > 0 && (
        <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid rgba(244,241,234,0.08)" }}>
          <p style={{ fontSize: 9, letterSpacing: 2, textTransform: "uppercase", opacity: 0.4, marginBottom: 6 }}>Live log</p>
          <div style={{ display: "grid", gap: 2, fontFamily: "monospace", fontSize: 11, opacity: 0.75, maxHeight: 130, overflowY: "auto" }}>
            {c.logs.slice(0, 8).map((l: { ts: number; kind: string; note?: string }, i: number) => (
              <div key={i}>
                <span style={{ opacity: 0.5 }}>{new Date((Number(l.ts) || 0) * 1000).toLocaleTimeString("ja-JP")}</span>{" "}
                <span style={{ color: "#c8302e" }}>{l.kind}</span>{l.note ? ` ${l.note}` : ""}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Tag({ text, tone }: { text: string; tone: "green" | "blue" | "dim" }) {
  const color = tone === "green" ? "#4ade80" : tone === "blue" ? "#60a5fa" : "rgba(244,241,234,0.6)";
  return (
    <span style={{ fontSize: 9, letterSpacing: 1.5, textTransform: "uppercase", padding: "3px 8px", border: `1px solid ${color}`, color, borderRadius: 2, whiteSpace: "nowrap" }}>
      {text}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const alive = status === "alive";
  const critical = status === "critical";
  return (
    <span style={{
      fontSize: 10, padding: "4px 10px", border: "1px solid",
      borderColor: alive ? "#c8302e" : critical ? "#e87c00" : "rgba(244,241,234,0.4)",
      color: alive ? "#c8302e" : critical ? "#e87c00" : "rgba(244,241,234,0.7)",
      letterSpacing: 2, whiteSpace: "nowrap",
    }}>
      {status.toUpperCase()}
    </span>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p style={{ fontSize: 10, letterSpacing: 3, textTransform: "uppercase", opacity: 0.5 }}>{label}</p>
      <p style={{ fontSize: 32, marginTop: 4 }}>{value}</p>
    </div>
  );
}

function Metric({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div>
      <p style={{ fontSize: 9, letterSpacing: 2, textTransform: "uppercase", opacity: 0.4 }}>{label}</p>
      <p style={{ fontSize: 13, marginTop: 2, color: highlight ? "#4ade80" : undefined }}>{value}</p>
    </div>
  );
}

function Skeleton() {
  return (
    <div style={{ marginTop: 40 }}>
      {[0, 1, 2].map(i => (
        <div key={i} style={{ height: 80, marginBottom: 16, background: "rgba(244,241,234,0.05)", border: "1px solid rgba(244,241,234,0.08)", borderRadius: 2 }} />
      ))}
    </div>
  );
}

function ErrorCard({ message }: { message: string }) {
  return (
    <div style={{ marginTop: 40, padding: 24, border: "1px solid rgba(200,48,46,0.4)", color: "#c8302e", fontSize: 14 }}>
      Failed to load dashboard: {message}
    </div>
  );
}
