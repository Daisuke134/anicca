// dashboard-core — PURE render helpers for /dashboard. NO fetch/supabase/fs/Date.now: `nowSec` is
// always a parameter so every function is deterministic + unit-testable without network or clock.
// Source of truth = the spec at .vcsdd/features/realtime-fleet-dashboard/specs/ (REQ-4/5/6/8/14).

const STALE_SECS = 300; // > the real 120s telemetry heartbeat (REQ-4 / F12)
const LOG_KINDS = new Set(['earn', 'claim', 'blocked', 'done', 'ping', 'spawn', 'info']);

// REQ-4: dead > stale(missing/NaN ts | now-ts>300) > critical > alive
export function deriveStatus(row, nowSec) {
  if (row && row.status === 'dead') return 'dead';
  const ts = row ? Number(row.ts) : NaN;
  if (!Number.isFinite(ts) || nowSec - ts > STALE_SECS) return 'stale';
  if (row.status === 'critical') return 'critical';
  return 'alive';
}

// REQ-5: economic self-funded = not-dead AND monthly revenue / 30 covers daily burn
export function isSelfFundedEconomic(row, nowSec) {
  if (deriveStatus(row, nowSec) === 'dead') return false;
  return Number(row.revenue_mo_usd || 0) / 30 >= Number(row.burn_day_usd || 0);
}

// REQ-6: the ONLY new aggregation (display-status counts). $ totals come from server aggregate().
export function countByStatus(rows, nowSec) {
  const c = { alive: 0, stale: 0, critical: 0, dead: 0 };
  for (const r of rows || []) c[deriveStatus(r, nowSec)]++;
  return c;
}

export function normalizeLogKind(kind) {
  return LOG_KINDS.has(kind) ? kind : 'info';
}

// REQ-8 + REQ-14: full fixed card view-model. funding/env/brain null ⇒ 'unknown'; logs newest-first ≤20.
export function toCardModel(row, nowSec) {
  if (row === null || row === undefined || typeof row !== 'object') row = {}; // null-row guard (FIND-006)
  const orDefault = (v) => (v === null || v === undefined || v === '' ? 'unknown' : v);
  const logs = (Array.isArray(row.log) ? row.log : [])
    .slice()
    .sort((a, b) => Number(b.ts) - Number(a.ts))
    .slice(0, 20)
    .map((l) => ({ ts: l.ts, kind: normalizeLogKind(l.kind), note: l.note ?? '' }));
  const revenueMoUsd = Number(row.revenue_mo_usd || 0);
  const burnDayUsd = Number(row.burn_day_usd || 0);
  return {
    id: row.id,
    host: row.host,
    statusDisplay: deriveStatus(row, nowSec),
    funding: orDefault(row.funding),
    env: orDefault(row.env),
    brain: orDefault(row.brain),
    model: orDefault(row.model_live),
    modelTier: orDefault(row.model_tier),
    walletUrl: row.id ? `https://basescan.org/address/${row.id}` : null,
    assetsUsd: Number(row.net_worth_usd || 0),
    revenueMoUsd,
    burnDayUsd,
    netUsd: +(revenueMoUsd - burnDayUsd * 30).toFixed(6), // monthly basis (M1)
    selfFundedEconomic: isSelfFundedEconomic(row, nowSec),
    logs,
  };
}
