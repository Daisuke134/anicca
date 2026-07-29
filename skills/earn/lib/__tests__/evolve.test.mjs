// VSDD RED->GREEN + synthetic-ledger E2E (spec §4.2): realized P&L takes days to accumulate on
// real Polymarket redeems, so the promote/no-promote gate is proven here against a CRAFTED
// (synthetic) earn-ledger + pm-trade trace, isolated to a temp dir/temp git repo — this test
// NEVER touches the real the canonical checkout repo, the real earn-ledger, or places any real order.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { execFileSync } from "node:child_process";

import {
  summarizeByGenome,
  attributeGenomeId,
  buildGenomeIndex,
  evaluatePromotion,
  promote,
  runEvolve,
  readTrace,
  DEFAULT_MIN_REDEEMS,
} from "../evolve.mjs";
import { genomeId, SAFE_DEFAULT_GENOME } from "../genome.mjs";

function tmpDir(prefix) {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

function writeJsonl(filePath, rows) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, rows.map((r) => JSON.stringify(r)).join("\n") + "\n");
}

function initGitRepo(dir) {
  execFileSync("git", ["init", "-q"], { cwd: dir });
  execFileSync("git", ["-c", "user.name=t", "-c", "user.email=t@t.local", "commit", "--allow-empty", "-q", "-m", "init"], {
    cwd: dir,
  });
}

const GENOME_A = { ...SAFE_DEFAULT_GENOME }; // baseline
const GENOME_B = { ...SAFE_DEFAULT_GENOME, MIN_EDGE: 0.18 }; // mutant, winner
const ID_A = genomeId(GENOME_A);
const ID_B = genomeId(GENOME_B);

function tradeTrace({ ts, genome, genomeIdValue, market }) {
  return [
    { ts, slot: "earn/pm-trade", action: "genome", genome_id: genomeIdValue, mutated: genomeIdValue !== ID_A, genome },
    {
      ts,
      slot: "earn/pm-trade",
      action: "trade",
      market,
      genome_id: genomeIdValue,
      order: { ok: true },
    },
  ];
}

function redeemRow({ ts, market, earn, cost, tx, statusOk = true }) {
  const net = Math.round((earn - cost) * 1e6) / 1e6;
  return {
    ts,
    wallet: "0x904b50d2e214da947d83d6a2d32c4e3ffc17eb74",
    source: "polymarket-redeem",
    task: market,
    earn_usdc: earn,
    cost_usdc: cost,
    net_usdc: net,
    tx,
    status: statusOk ? "0x1" : "0x0",
    chain: "polygon",
    external: true,
    wake: `redeem-${tx.slice(0, 8)}`,
  };
}

test("attributeGenomeId matches the most recent preceding trade for the same market", () => {
  const trace = [
    ...tradeTrace({ ts: "2026-07-01T00:00:00Z", genome: GENOME_A, genomeIdValue: ID_A, market: "M1" }),
    ...tradeTrace({ ts: "2026-07-02T00:00:00Z", genome: GENOME_B, genomeIdValue: ID_B, market: "M1" }),
  ];
  const row = redeemRow({ ts: 1783296000, market: "M1", earn: 5, cost: 4, tx: "0xaaa" }); // 2026-07-04
  assert.equal(attributeGenomeId(row, trace), ID_B, "the LATER trade (still before redeem) wins");
});

test("attributeGenomeId returns null when no trace line matches the market", () => {
  const trace = tradeTrace({ ts: "2026-07-01T00:00:00Z", genome: GENOME_A, genomeIdValue: ID_A, market: "Other market" });
  const row = redeemRow({ ts: 1783296000, market: "M1", earn: 5, cost: 4, tx: "0xaaa" });
  assert.equal(attributeGenomeId(row, trace), null);
});

test("summarizeByGenome counts ONLY on-chain-verified (tx + status 0x1) redeem rows, sums net_usdc", () => {
  const trace = [
    ...tradeTrace({ ts: "2026-07-01T00:00:00Z", genome: GENOME_A, genomeIdValue: ID_A, market: "M1" }),
    ...tradeTrace({ ts: "2026-07-01T00:00:00Z", genome: GENOME_B, genomeIdValue: ID_B, market: "M2" }),
  ];
  const ledger = [
    redeemRow({ ts: 1783296000, market: "M1", earn: 5, cost: 4, tx: "0xa1" }), // A: net 1
    redeemRow({ ts: 1783296100, market: "M2", earn: 6, cost: 3, tx: "0xb1" }), // B: net 3
    redeemRow({ ts: 1783296200, market: "M2", earn: 6, cost: 3, tx: "0xb2", statusOk: false }), // NOT verified -> excluded
    { ts: 1783296300, source: "polymarket-redeem", task: "M2", earn_usdc: 100, cost_usdc: 0, net_usdc: 100 }, // no tx -> excluded (paper)
  ];
  const summary = summarizeByGenome(ledger, trace);
  assert.equal(summary.get(ID_A).realized_usdc, 1);
  assert.equal(summary.get(ID_A).redeem_count, 1);
  assert.equal(summary.get(ID_B).realized_usdc, 3);
  assert.equal(summary.get(ID_B).redeem_count, 1);
});

test("evaluatePromotion: below-K redeems never promotes even if P&L beats baseline", () => {
  const summary = new Map([
    [ID_A, { genome_id: ID_A, realized_usdc: 1, redeem_count: 5 }],
    [ID_B, { genome_id: ID_B, realized_usdc: 100, redeem_count: 1 }],
  ]);
  const verdict = evaluatePromotion({ summary, baselineId: ID_A, mutantId: ID_B, minRedeems: 3 });
  assert.equal(verdict.promote, false);
  assert.match(verdict.reason, /below-K/);
});

test("evaluatePromotion: does not beat baseline -> no promote", () => {
  const summary = new Map([
    [ID_A, { genome_id: ID_A, realized_usdc: 10, redeem_count: 5 }],
    [ID_B, { genome_id: ID_B, realized_usdc: 3, redeem_count: 5 }],
  ]);
  const verdict = evaluatePromotion({ summary, baselineId: ID_A, mutantId: ID_B, minRedeems: 3 });
  assert.equal(verdict.promote, false);
  assert.match(verdict.reason, /does-not-beat-baseline/);
});

test("evaluatePromotion: beats baseline AND >=K redeems -> promote", () => {
  const summary = new Map([
    [ID_A, { genome_id: ID_A, realized_usdc: 1, redeem_count: 3 }],
    [ID_B, { genome_id: ID_B, realized_usdc: 3, redeem_count: 3 }],
  ]);
  const verdict = evaluatePromotion({ summary, baselineId: ID_A, mutantId: ID_B, minRedeems: 3 });
  assert.equal(verdict.promote, true);
});

// MUST-FIX 1 (adversary, money-safety HARD 0.24): "less-negative" must NEVER promote. A
// challenger that beats a losing baseline only by losing less money is still a net-losing
// strategy — auto-adopting it would lock in a losing genome. The challenger must clear an
// absolute net-positive floor (realized_usdc > 0), not merely outperform baseline.
test("evaluatePromotion: challenger less-negative than a losing baseline -> NO promote (net-positive floor)", () => {
  const summary = new Map([
    [ID_A, { genome_id: ID_A, realized_usdc: -5, redeem_count: 3 }], // baseline: net LOSS -$5
    [ID_B, { genome_id: ID_B, realized_usdc: -2, redeem_count: 3 }], // challenger: net LOSS -$2 (less bad, still a loss)
  ]);
  const verdict = evaluatePromotion({ summary, baselineId: ID_A, mutantId: ID_B, minRedeems: 3 });
  assert.equal(verdict.promote, false, "-2 > -5 must NOT promote — the challenger still lost money");
  assert.match(verdict.reason, /challenger-not-net-positive/);
});

test("evaluatePromotion: baseline has no on-chain history (defaults to 0) -> a net-positive challenger still promotes", () => {
  const summary = new Map([[ID_B, { genome_id: ID_B, realized_usdc: 2, redeem_count: 3 }]]);
  const verdict = evaluatePromotion({ summary, baselineId: ID_A, mutantId: ID_B, minRedeems: 3 });
  assert.equal(verdict.promote, true, "baseline defaults to {realized_usdc:0}; a net-positive challenger clears both floors");
});

test("evaluatePromotion: challenger itself net-negative with NO baseline history -> NO promote", () => {
  const summary = new Map([[ID_B, { genome_id: ID_B, realized_usdc: -1, redeem_count: 3 }]]);
  const verdict = evaluatePromotion({ summary, baselineId: ID_A, mutantId: ID_B, minRedeems: 3 });
  assert.equal(verdict.promote, false);
  assert.match(verdict.reason, /challenger-not-net-positive/);
});

test("promote() writes the canonical baseline-genome.json AND git-commits it", () => {
  const repo = tmpDir("evolve-promote-");
  initGitRepo(repo);
  const canonicalPath = path.join(repo, "baseline-genome.json");
  fs.writeFileSync(canonicalPath, JSON.stringify(GENOME_A));
  execFileSync("git", ["add", "baseline-genome.json"], { cwd: repo });
  execFileSync("git", ["-c", "user.name=t", "-c", "user.email=t@t.local", "commit", "-q", "-m", "seed baseline"], {
    cwd: repo,
  });

  const before = execFileSync("git", ["rev-parse", "HEAD"], { cwd: repo }).toString().trim();
  const result = promote(GENOME_B, { canonicalPath, cwd: repo });
  const after = execFileSync("git", ["rev-parse", "HEAD"], { cwd: repo }).toString().trim();

  assert.notEqual(before, after, "promote() must create a new commit");
  assert.equal(result.genome_id, genomeId(GENOME_B));
  const written = JSON.parse(fs.readFileSync(canonicalPath, "utf8"));
  assert.deepEqual(written, GENOME_B);

  const log = execFileSync("git", ["log", "-1", "--format=%s"], { cwd: repo }).toString();
  assert.match(log, /promote genome/);
});

// LOW-SEV fix (adversary, repo safety): promote() must NEVER sweep unrelated staged/working-tree
// changes into its commit on a shared checkout. Simulates exactly the observed real scenario
// (another process's edit sitting staged in the canonical checkout while a promotion runs).
test("promote() is path-scoped: an unrelated STAGED file is never swept into the promotion commit", () => {
  const repo = tmpDir("evolve-promote-pathscope-");
  initGitRepo(repo);
  const canonicalPath = path.join(repo, "baseline-genome.json");
  fs.writeFileSync(canonicalPath, JSON.stringify(GENOME_A));
  const unrelatedPath = path.join(repo, "unrelated-other-file.txt");
  fs.writeFileSync(unrelatedPath, "seed\n");
  execFileSync("git", ["add", "."], { cwd: repo });
  execFileSync("git", ["-c", "user.name=t", "-c", "user.email=t@t.local", "commit", "-q", "-m", "seed both files"], {
    cwd: repo,
  });

  // Simulate a concurrent, unrelated process staging a change to a DIFFERENT file right before
  // promote() runs (exactly what was observed live on the shared the canonical checkout checkout).
  fs.writeFileSync(unrelatedPath, "modified by an unrelated concurrent process\n");
  execFileSync("git", ["add", unrelatedPath], { cwd: repo });

  promote(GENOME_B, { canonicalPath, cwd: repo });

  const committedFiles = execFileSync("git", ["show", "--name-only", "--format=", "HEAD"], { cwd: repo })
    .toString()
    .trim()
    .split("\n")
    .filter(Boolean);
  assert.deepEqual(committedFiles, ["baseline-genome.json"], "the commit must touch ONLY baseline-genome.json");

  // The unrelated file's staged change must still be sitting in the index, untouched/uncommitted.
  const stagedDiff = execFileSync("git", ["diff", "--cached", "--name-only"], { cwd: repo }).toString().trim();
  assert.equal(stagedDiff, "unrelated-other-file.txt", "the unrelated staged change must remain staged, not committed");
});

// ---------------------------------------------------------------------------------------------
// SYNTHETIC-LEDGER E2E (spec §4.2) — the two required outcomes, both proven end to end.
// ---------------------------------------------------------------------------------------------

test("E2E PROMOTE: genome B (realized $3, 3 on-chain redeems) beats baseline A (realized $1) -> promoted", async () => {
  const repo = tmpDir("evolve-e2e-promote-");
  initGitRepo(repo);
  const canonicalPath = path.join(repo, "baseline-genome.json");
  fs.writeFileSync(canonicalPath, JSON.stringify(GENOME_A, null, 2) + "\n");
  execFileSync("git", ["add", "baseline-genome.json"], { cwd: repo });
  execFileSync("git", ["-c", "user.name=t", "-c", "user.email=t@t.local", "commit", "-q", "-m", "seed baseline A"], {
    cwd: repo,
  });

  const stateDir = path.join(repo, "state");
  const tracePath = path.join(stateDir, "pm-trade.trace.jsonl");
  const ledgerPath = path.join(stateDir, "earn-ledger.jsonl");

  const trace = [
    ...tradeTrace({ ts: "2026-07-01T00:00:00Z", genome: GENOME_A, genomeIdValue: ID_A, market: "A-market-1" }),
    ...tradeTrace({ ts: "2026-07-02T00:00:00Z", genome: GENOME_B, genomeIdValue: ID_B, market: "B-market-1" }),
    ...tradeTrace({ ts: "2026-07-02T01:00:00Z", genome: GENOME_B, genomeIdValue: ID_B, market: "B-market-2" }),
    ...tradeTrace({ ts: "2026-07-02T02:00:00Z", genome: GENOME_B, genomeIdValue: ID_B, market: "B-market-3" }),
  ];
  writeJsonl(tracePath, trace);

  // baseline A: realized $1 total across 1 redeem. mutant B: realized $3 total across 3 redeems (K=3).
  const ledger = [
    redeemRow({ ts: 1783296000, market: "A-market-1", earn: 5, cost: 4, tx: "0xA0001" }), // net 1
    redeemRow({ ts: 1783382400, market: "B-market-1", earn: 3, cost: 2, tx: "0xB0001" }), // net 1
    redeemRow({ ts: 1783386000, market: "B-market-2", earn: 3, cost: 2, tx: "0xB0002" }), // net 1
    redeemRow({ ts: 1783389600, market: "B-market-3", earn: 3, cost: 2, tx: "0xB0003" }), // net 1
  ];
  writeJsonl(ledgerPath, ledger);

  const before = execFileSync("git", ["rev-parse", "HEAD"], { cwd: repo }).toString().trim();
  const result = await runEvolve({ ledgerPath, tracePath, canonicalPath, minRedeems: 3, cwd: repo });
  const after = execFileSync("git", ["rev-parse", "HEAD"], { cwd: repo }).toString().trim();

  assert.equal(result.promoted, true, "B must be promoted: beats baseline AND has >=3 on-chain redeems");
  assert.equal(result.newBaselineId, ID_B);
  assert.notEqual(before, after, "a real git commit must have been made");

  const writtenBaseline = JSON.parse(fs.readFileSync(canonicalPath, "utf8"));
  assert.deepEqual(writtenBaseline, GENOME_B, "baseline-genome.json now holds B's actual knob values");

  console.log("SYNTHETIC E2E PROMOTE result:", JSON.stringify(result, null, 2));
});

// MUST-FIX 1 regression E2E (adversary): a challenger that is still net-LOSING must never be
// promoted just because it loses LESS than a losing baseline. baseline realized -$5, challenger
// realized -$2, BOTH with >=3 on-chain-verified redeems — must NOT promote, and no commit made.
test("E2E NO-PROMOTE (still-losing challenger): baseline -$5, challenger -$2, both >=3 redeems -> NO promote", async () => {
  const repo = tmpDir("evolve-e2e-nopromote-lessnegative-");
  initGitRepo(repo);
  const canonicalPath = path.join(repo, "baseline-genome.json");
  fs.writeFileSync(canonicalPath, JSON.stringify(GENOME_A, null, 2) + "\n");
  execFileSync("git", ["add", "baseline-genome.json"], { cwd: repo });
  execFileSync("git", ["-c", "user.name=t", "-c", "user.email=t@t.local", "commit", "-q", "-m", "seed baseline A"], {
    cwd: repo,
  });

  const stateDir = path.join(repo, "state");
  const tracePath = path.join(stateDir, "pm-trade.trace.jsonl");
  const ledgerPath = path.join(stateDir, "earn-ledger.jsonl");

  const trace = [
    ...tradeTrace({ ts: "2026-07-01T00:00:00Z", genome: GENOME_A, genomeIdValue: ID_A, market: "A-market-1" }),
    ...tradeTrace({ ts: "2026-07-01T01:00:00Z", genome: GENOME_A, genomeIdValue: ID_A, market: "A-market-2" }),
    ...tradeTrace({ ts: "2026-07-01T02:00:00Z", genome: GENOME_A, genomeIdValue: ID_A, market: "A-market-3" }),
    ...tradeTrace({ ts: "2026-07-02T00:00:00Z", genome: GENOME_B, genomeIdValue: ID_B, market: "B-market-1" }),
    ...tradeTrace({ ts: "2026-07-02T01:00:00Z", genome: GENOME_B, genomeIdValue: ID_B, market: "B-market-2" }),
    ...tradeTrace({ ts: "2026-07-02T02:00:00Z", genome: GENOME_B, genomeIdValue: ID_B, market: "B-market-3" }),
  ];
  writeJsonl(tracePath, trace);

  // baseline A: realized -$5 total across 3 on-chain redeems (a real losing genome).
  // mutant B:  realized -$2 total across 3 on-chain redeems — loses LESS, but still a net loss.
  const ledger = [
    redeemRow({ ts: 1783296000, market: "A-market-1", earn: 3, cost: 5, tx: "0xA0001" }), // net -2
    redeemRow({ ts: 1783296100, market: "A-market-2", earn: 3, cost: 5, tx: "0xA0002" }), // net -2
    redeemRow({ ts: 1783296200, market: "A-market-3", earn: 3, cost: 4, tx: "0xA0003" }), // net -1  (sum -5)
    redeemRow({ ts: 1783382400, market: "B-market-1", earn: 3, cost: 4, tx: "0xB0001" }), // net -1
    redeemRow({ ts: 1783386000, market: "B-market-2", earn: 2, cost: 2.5, tx: "0xB0002" }), // net -0.5
    redeemRow({ ts: 1783389600, market: "B-market-3", earn: 2, cost: 2.5, tx: "0xB0003" }), // net -0.5  (sum -2)
  ];
  writeJsonl(ledgerPath, ledger);

  const before = execFileSync("git", ["rev-parse", "HEAD"], { cwd: repo }).toString().trim();
  const result = await runEvolve({ ledgerPath, tracePath, canonicalPath, minRedeems: 3, cwd: repo });
  const after = execFileSync("git", ["rev-parse", "HEAD"], { cwd: repo }).toString().trim();

  assert.equal(result.summary[ID_A].realized_usdc, -5);
  assert.equal(result.summary[ID_B].realized_usdc, -2);
  assert.equal(result.promoted, false, "-2 beats -5 but is still a LOSS — must never promote (HARD 0.24)");
  assert.match(result.evaluations[ID_B].reason, /challenger-not-net-positive/);
  assert.equal(before, after, "no commit must have been made");
  const stillBaseline = JSON.parse(fs.readFileSync(canonicalPath, "utf8"));
  assert.deepEqual(stillBaseline, GENOME_A, "baseline-genome.json must be untouched");

  console.log("SYNTHETIC E2E NO-PROMOTE (still-losing challenger, -5 vs -2) result:", JSON.stringify(result, null, 2));
});

test("E2E NO-PROMOTE (paper rows only): mutant B has no on-chain tx -> never promoted", async () => {
  const repo = tmpDir("evolve-e2e-nopromote-paper-");
  initGitRepo(repo);
  const canonicalPath = path.join(repo, "baseline-genome.json");
  fs.writeFileSync(canonicalPath, JSON.stringify(GENOME_A, null, 2) + "\n");
  execFileSync("git", ["add", "baseline-genome.json"], { cwd: repo });
  execFileSync("git", ["-c", "user.name=t", "-c", "user.email=t@t.local", "commit", "-q", "-m", "seed baseline A"], {
    cwd: repo,
  });

  const stateDir = path.join(repo, "state");
  const tracePath = path.join(stateDir, "pm-trade.trace.jsonl");
  const ledgerPath = path.join(stateDir, "earn-ledger.jsonl");

  const trace = [
    ...tradeTrace({ ts: "2026-07-01T00:00:00Z", genome: GENOME_A, genomeIdValue: ID_A, market: "A-market-1" }),
    ...tradeTrace({ ts: "2026-07-02T00:00:00Z", genome: GENOME_B, genomeIdValue: ID_B, market: "B-market-1" }),
    ...tradeTrace({ ts: "2026-07-02T01:00:00Z", genome: GENOME_B, genomeIdValue: ID_B, market: "B-market-2" }),
    ...tradeTrace({ ts: "2026-07-02T02:00:00Z", genome: GENOME_B, genomeIdValue: ID_B, market: "B-market-3" }),
  ];
  writeJsonl(tracePath, trace);

  const ledger = [
    redeemRow({ ts: 1783296000, market: "A-market-1", earn: 5, cost: 4, tx: "0xA0001" }), // baseline: real, net 1
    // B's rows are PAPER/SIMULATED — no tx, no status (exactly what HARD 0.24 forbids counting)
    { ts: 1783382400, source: "polymarket-redeem", task: "B-market-1", earn_usdc: 30, cost_usdc: 0, net_usdc: 30 },
    { ts: 1783386000, source: "polymarket-redeem", task: "B-market-2", earn_usdc: 30, cost_usdc: 0, net_usdc: 30 },
    { ts: 1783389600, source: "polymarket-redeem", task: "B-market-3", earn_usdc: 30, cost_usdc: 0, net_usdc: 30 },
  ];
  writeJsonl(ledgerPath, ledger);

  const before = execFileSync("git", ["rev-parse", "HEAD"], { cwd: repo }).toString().trim();
  const result = await runEvolve({ ledgerPath, tracePath, canonicalPath, minRedeems: 3, cwd: repo });
  const after = execFileSync("git", ["rev-parse", "HEAD"], { cwd: repo }).toString().trim();

  assert.equal(result.promoted, false, "paper/simulated rows must NEVER promote (HARD 0.24)");
  assert.equal(before, after, "no commit must have been made");
  const stillBaseline = JSON.parse(fs.readFileSync(canonicalPath, "utf8"));
  assert.deepEqual(stillBaseline, GENOME_A, "baseline-genome.json must be untouched");

  console.log("SYNTHETIC E2E NO-PROMOTE (paper) result:", JSON.stringify(result, null, 2));
});

test("E2E NO-PROMOTE (below K): mutant B beats baseline P&L but has only 2 on-chain redeems (<K=3)", async () => {
  const repo = tmpDir("evolve-e2e-nopromote-belowk-");
  initGitRepo(repo);
  const canonicalPath = path.join(repo, "baseline-genome.json");
  fs.writeFileSync(canonicalPath, JSON.stringify(GENOME_A, null, 2) + "\n");
  execFileSync("git", ["add", "baseline-genome.json"], { cwd: repo });
  execFileSync("git", ["-c", "user.name=t", "-c", "user.email=t@t.local", "commit", "-q", "-m", "seed baseline A"], {
    cwd: repo,
  });

  const stateDir = path.join(repo, "state");
  const tracePath = path.join(stateDir, "pm-trade.trace.jsonl");
  const ledgerPath = path.join(stateDir, "earn-ledger.jsonl");

  const trace = [
    ...tradeTrace({ ts: "2026-07-01T00:00:00Z", genome: GENOME_A, genomeIdValue: ID_A, market: "A-market-1" }),
    ...tradeTrace({ ts: "2026-07-02T00:00:00Z", genome: GENOME_B, genomeIdValue: ID_B, market: "B-market-1" }),
    ...tradeTrace({ ts: "2026-07-02T01:00:00Z", genome: GENOME_B, genomeIdValue: ID_B, market: "B-market-2" }),
  ];
  writeJsonl(tracePath, trace);

  const ledger = [
    redeemRow({ ts: 1783296000, market: "A-market-1", earn: 5, cost: 4, tx: "0xA0001" }), // baseline: net 1
    redeemRow({ ts: 1783382400, market: "B-market-1", earn: 10, cost: 5, tx: "0xB0001" }), // B: net 5
    redeemRow({ ts: 1783386000, market: "B-market-2", earn: 10, cost: 5, tx: "0xB0002" }), // B: net 5 (only 2 redeems total)
  ];
  writeJsonl(ledgerPath, ledger);

  const before = execFileSync("git", ["rev-parse", "HEAD"], { cwd: repo }).toString().trim();
  const result = await runEvolve({ ledgerPath, tracePath, canonicalPath, minRedeems: 3, cwd: repo });
  const after = execFileSync("git", ["rev-parse", "HEAD"], { cwd: repo }).toString().trim();

  assert.equal(result.promoted, false, "2 redeems < K=3 must never promote, even with a real P&L lead");
  assert.equal(before, after);

  console.log("SYNTHETIC E2E NO-PROMOTE (below-K) result:", JSON.stringify(result, null, 2));
});

test("runEvolve default minRedeems is 3 (spec §2.3 default K)", () => {
  assert.equal(DEFAULT_MIN_REDEEMS, 3);
});

test("readTrace on a missing file returns [] (fail-closed, never throws)", async () => {
  const trace = await readTrace("/no/such/trace/file.jsonl");
  assert.deepEqual(trace, []);
});

test("buildGenomeIndex captures genome VALUES keyed by genome_id from 'genome' trace lines", () => {
  const trace = tradeTrace({ ts: "2026-07-01T00:00:00Z", genome: GENOME_B, genomeIdValue: ID_B, market: "M" });
  const index = buildGenomeIndex(trace);
  assert.deepEqual(index.get(ID_B), GENOME_B);
});
