#!/usr/bin/env node
import { promises as fs } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { summarizeRealizedRevenue } from "./lib/money-truth.mjs";
import { graduationGate } from "./lib/treasury-policy.mjs";

const WINDOW_MS = 30 * 86400000;

function timestampMs(row) {
  const raw = row?.ts ?? row?.timestamp ?? row?.occurred_at;
  const value = Number(raw);
  if (Number.isFinite(value)) return value > 1e12 ? value : value * 1000;
  const parsed = Date.parse(String(raw ?? ""));
  return Number.isFinite(parsed) ? parsed : null;
}

function recent(rows, startMs, endMs) {
  return (Array.isArray(rows) ? rows : []).filter((row) => {
    const at = timestampMs(row);
    return at !== null && at >= startMs && at < endMs;
  });
}

function sumField(rows, fields) {
  return Math.round((Array.isArray(rows) ? rows : []).reduce((sum, row) => {
    const value = fields.map((field) => row?.[field]).find((candidate) => candidate !== undefined);
    const number = Number(value);
    return Number.isFinite(number) && number >= 0 ? sum + number : sum;
  }, 0) * 1e6) / 1e6;
}

export function summarizeEconomyStatus({
  earnRows = [],
  corrections = [],
  computeRows = [],
  shelterRows = [],
  nowMs = Date.now(),
  liquidRunwayDays,
  humanPaidInference30d,
} = {}) {
  const now = Number(nowMs);
  if (!Number.isFinite(now)) throw new TypeError("nowMs must be finite");
  const start = now - WINDOW_MS;
  const earn30 = recent(earnRows, start, now);
  const compute30 = recent(computeRows, start, now);
  const shelter30 = recent(shelterRows, start, now);
  // Production status requires the same verified proof gate as the reconcile loop.  Legacy rows that
  // merely claim status=0x1 remain visible as unverified but never become realized revenue.
  const revenue = summarizeRealizedRevenue(earn30, corrections);
  const computeCost = sumField(compute30, ["cost_usd", "costUsd", "est_usd"]);
  const shelterCost = sumField(shelter30, ["settledLeaseCostUsd", "shelter_cost_usd"]);
  const graduation = graduationGate({
    externalRealizedNet30d: revenue.external_net_usdc,
    computeCost30d: computeCost,
    shelterCost30d: shelterCost,
    liquidRunwayDays,
    humanPaidInference30d,
  });
  return {
    window_days: 30,
    external_realized_net_30d: revenue.external_net_usdc,
    verified_external_rows_30d: revenue.verified_external_rows,
    unverified_external_rows_30d: revenue.unverified_external_rows,
    compute_cost_30d: computeCost,
    shelter_cost_30d: shelterCost,
    graduation,
  };
}

async function readJsonl(file) {
  if (!file) return [];
  try {
    const raw = await fs.readFile(file, "utf8");
    return raw.split("\n").filter(Boolean).map((line) => {
      try { return JSON.parse(line); } catch { return null; }
    }).filter(Boolean);
  } catch (error) {
    if (error?.code === "ENOENT") return [];
    throw error;
  }
}

const isMain = process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1]);
if (isMain) {
  const [earnPath, correctionPath, computePath, shelterPath, journalPath] = process.argv.slice(2);
  const defaultJournalPath = process.env.ANICCA_HOME
    ? path.join(process.env.ANICCA_HOME, "skills", "earn", "state", "revenue-receipts.jsonl") : undefined;
  const [earnRows, corrections, computeRows, shelterRows, journalRows] = await Promise.all([
    readJsonl(earnPath), readJsonl(correctionPath), readJsonl(computePath), readJsonl(shelterPath),
    readJsonl(journalPath || defaultJournalPath),
  ]);
  const receiptKeys = new Set();
  const combinedEarnRows = [...earnRows, ...journalRows].filter((row) => {
    const key = row?.kind === "revenue_receipt" && typeof row.idempotency_key === "string" ? row.idempotency_key : null;
    if (!key) return true;
    if (receiptKeys.has(key)) return false;
    receiptKeys.add(key);
    return true;
  });
  process.stdout.write(`${JSON.stringify(summarizeEconomyStatus({
    earnRows: combinedEarnRows,
    corrections,
    computeRows,
    shelterRows,
    liquidRunwayDays: process.env.ANICCA_LIQUID_RUNWAY_DAYS === undefined
      ? undefined : Number(process.env.ANICCA_LIQUID_RUNWAY_DAYS),
    humanPaidInference30d: process.env.ANICCA_HUMAN_PAID_INFERENCE_30D === undefined
      ? undefined : Number(process.env.ANICCA_HUMAN_PAID_INFERENCE_30D),
  }))}\n`);
}
