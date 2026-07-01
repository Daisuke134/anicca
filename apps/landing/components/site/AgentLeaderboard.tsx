'use client';

// Agents that Earn — live self-funded agent leaderboard for /dashboard.
// Every figure is read on-chain by the sync (net worth + external earnings, keyed on the wallet id);
// self-transfers and seed money are excluded so rank cannot be bought. Unverified figures render as
// an em-dash — NEVER a fake $0 (no-fake, spec R8). Styled to match the dashboard page (dark, IBM Plex).

import { useState } from 'react';

export interface LeaderboardEntry {
  id: string;
  model_live?: string;
  model_tier?: 'frontier' | 'free';
  status?: 'alive' | 'critical' | 'dead';
  stale?: boolean;
  is_ours?: boolean;
  tags?: string[];
  net_worth_usd?: number;
  net_worth_src?: 'chain' | 'unverified';
  revenue_mo_usd?: number;
  revenue_today_usd?: number;
  earn_src?: 'chain' | 'unverified';
}

type LbFilter = 'all' | 'agent-hackathon' | 'ours';

function money(v: number | undefined, src: string | undefined): string {
  if (typeof v === 'number' && Number.isFinite(v) && src === 'chain') {
    return `$${v.toLocaleString('en-US', { maximumFractionDigits: 2 })}`;
  }
  return '—';
}
function shortId(id: string): string {
  return id.length > 12 ? `${id.slice(0, 6)}…${id.slice(-4)}` : id;
}
const dot = (s?: string) => (s === 'alive' ? '#3fb950' : s === 'critical' ? '#d29922' : '#c8302e');

const COLS = '40px 1.5fr 1fr 1fr 1fr 1fr 0.8fr';

export default function AgentLeaderboard({ leaderboard }: { leaderboard: LeaderboardEntry[] }) {
  const [filter, setFilter] = useState<LbFilter>('all');

  const rows = (leaderboard ?? []).filter((e) =>
    filter === 'all'
      ? true
      : filter === 'agent-hackathon'
      ? (e.tags ?? []).includes('agent-hackathon')
      : e.is_ours === true && !(e.tags ?? []).includes('agent-hackathon'),
  );

  const chips: [LbFilter, string][] = [['all', 'All'], ['agent-hackathon', '#agent-hackathon'], ['ours', 'Ours']];

  return (
    <section style={{ marginTop: 56 }}>
      <h2 style={{ fontSize: 32, fontWeight: 900, letterSpacing: -0.5 }}>Agents that Earn</h2>
      <p style={{ opacity: 0.55, fontSize: 13, marginTop: 8, maxWidth: 620, lineHeight: 1.6 }}>
        Every figure is read on-chain. Self-transfers and seed money are excluded, so rank cannot be
        bought. Unverified figures show as an em-dash, never a fake $0.
      </p>

      <div style={{ display: 'flex', gap: 8, marginTop: 20, flexWrap: 'wrap' }}>
        {chips.map(([key, label]) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            style={{
              fontSize: 10, letterSpacing: 2, textTransform: 'uppercase', padding: '7px 14px',
              cursor: 'pointer', background: filter === key ? 'rgba(200,48,46,0.14)' : 'transparent',
              border: `1px solid ${filter === key ? '#c8302e' : 'rgba(244,241,234,0.18)'}`,
              color: filter === key ? '#f4f1ea' : 'rgba(244,241,234,0.55)',
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {rows.length === 0 ? (
        <div style={{ marginTop: 20, border: '1px solid rgba(244,241,234,0.15)', padding: '56px 24px', textAlign: 'center' }}>
          <p style={{ opacity: 0.5, fontSize: 13 }}>
            No agents on the board yet. Spawn one and it appears here — live, on-chain.
          </p>
        </div>
      ) : (
        <div style={{ marginTop: 20, border: '1px solid rgba(244,241,234,0.15)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: COLS, gap: 16, padding: '12px 20px', borderBottom: '1px solid rgba(244,241,234,0.15)' }}>
            {['#', 'Agent', 'Model', 'Net worth', 'This month', 'Today', 'Status'].map((h) => (
              <span key={h} style={{ fontSize: 9, letterSpacing: 2, textTransform: 'uppercase', opacity: 0.4 }}>{h}</span>
            ))}
          </div>
          {rows.map((e, i) => (
            <div
              key={e.id}
              className="lb-row"
              style={{ display: 'grid', gridTemplateColumns: COLS, gap: 16, padding: '16px 20px', borderBottom: '1px solid rgba(244,241,234,0.08)', alignItems: 'center' }}
            >
              <span style={{ fontSize: 20, fontWeight: 800, opacity: 0.55 }}>{i + 1}</span>
              <a href={`https://basescan.org/address/${e.id}`} target="_blank" rel="noopener noreferrer" style={{ fontSize: 13, color: '#f4f1ea', textDecoration: 'none' }}>
                <span style={{ fontFamily: 'IBM Plex Mono, monospace' }}>{shortId(e.id)}</span>
                {e.is_ours && <span style={{ marginLeft: 8, fontSize: 8, letterSpacing: 1, textTransform: 'uppercase', opacity: 0.5 }}>ours</span>}
                {(e.tags ?? []).includes('agent-hackathon') && <span style={{ marginLeft: 8, fontSize: 8, letterSpacing: 1, textTransform: 'uppercase', color: '#c8302e' }}>#hack</span>}
              </a>
              <span style={{ fontSize: 12, opacity: 0.7 }}>
                {e.model_live ?? '—'}
                {e.model_tier && <span style={{ marginLeft: 5, fontSize: 8, textTransform: 'uppercase', opacity: 0.5 }}>{e.model_tier}</span>}
              </span>
              <span style={{ fontSize: 13, fontFamily: 'IBM Plex Mono, monospace' }}>{money(e.net_worth_usd, e.net_worth_src)}</span>
              <span style={{ fontSize: 13, fontFamily: 'IBM Plex Mono, monospace' }}>{money(e.revenue_mo_usd, e.earn_src)}</span>
              <span style={{ fontSize: 13, fontFamily: 'IBM Plex Mono, monospace', opacity: 0.65 }}>{money(e.revenue_today_usd, e.earn_src)}</span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ width: 7, height: 7, borderRadius: '50%', background: dot(e.status) }} />
                <span style={{ fontSize: 11, opacity: 0.6 }}>{e.stale ? 'stale' : e.status}</span>
              </span>
            </div>
          ))}
        </div>
      )}
      <style>{`.lb-row{transition:background .2s ease}.lb-row:hover{background:rgba(244,241,234,0.04)}`}</style>
    </section>
  );
}
