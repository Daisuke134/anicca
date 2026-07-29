// VCSDD RED->GREEN: SOL earnings-gate attribution + promotion wiring (franklin-sol-evolvable-edge,
// REQ-012b/013/014/015/015b). REUSES evolve.mjs's evaluatePromotion/promote verbatim (never
// reimplemented) -- PROP-014/PROP-015b assert import-identity. This test NEVER touches the real
// the canonical checkout repo, the real earn-ledger, or places any real order; git operations run in a temp repo.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import fc from "fast-check";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

import {
  attributeGenomeIdSol,
  summarizeByGenomeSol,
  evaluatePromotion,
  promote,
  runEvolveSol,
} from "../sol-evolve.mjs";
import { evaluatePromotion as evaluatePromotionDirect, promote as promoteDirect } from "../../../lib/evolve.mjs";
import { SAFE_DEFAULT_GENOME, genomeId } from "../sol-genome.mjs";

function tmpDir(prefix) {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}
function initGitRepo(dir) {
  execFileSync("git", ["init", "-q"], { cwd: dir });
  execFileSync(
    "git",
    ["-c", "user.name=t", "-c", "user.email=t@t.local", "commit", "--allow-empty", "-q", "-m", "init"],
    { cwd: dir },
  );
}
function writeJsonl(filePath, rows) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, rows.map((r) => JSON.stringify(r)).join("\n") + "\n");
}

const GENOME_A = { ...SAFE_DEFAULT_GENOME };
const GENOME_B = { ...SAFE_DEFAULT_GENOME, SOL_GATE_MIN_MOMENTUM_PCT: 3.0 };
const ID_A = genomeId(GENOME_A);
const ID_B = genomeId(GENOME_B);

function genomeLinkLine(ts, genome, id) {
  return { ts, slot: "earn/sol-trade", action: "genome", genome_id: id, genome };
}

function swapRow({ ts, netUsdc, sig, confirmed = true, source = "sol-trade", task = "jupiter swap round-trip" }) {
  const earn = netUsdc > 0 ? netUsdc : 0;
  const cost = netUsdc < 0 ? -netUsdc : 0;
  return {
    ts,
    wallet: "8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9",
    source,
    task,
    earn_usdc: earn,
    cost_usdc: cost,
    net_usdc: netUsdc,
    sig,
    confirmed,
    chain: "solana",
  };
}

// --- PROP-014 ------------------------------------------------------------------------------
test("PROP-014: sol-evolve's evaluatePromotion IS the same function object imported from evolve.mjs (import-identity)", () => {
  assert.equal(evaluatePromotion, evaluatePromotionDirect);
});

test("PROP-014: SOL wiring produces IDENTICAL promote/no-promote verdicts to calling evolve.mjs's own function directly, reproducing its fixtures", () => {
  // mirrors evolve.test.mjs's own "beats baseline AND >=K redeems -> promote" fixture
  const summaryPromote = new Map([
    [ID_A, { genome_id: ID_A, realized_usdc: 1, redeem_count: 3 }],
    [ID_B, { genome_id: ID_B, realized_usdc: 3, redeem_count: 3 }],
  ]);
  const verdict1a = evaluatePromotion({ summary: summaryPromote, baselineId: ID_A, mutantId: ID_B, minRedeems: 3 });
  const verdict1b = evaluatePromotionDirect({ summary: summaryPromote, baselineId: ID_A, mutantId: ID_B, minRedeems: 3 });
  assert.deepEqual(verdict1a, verdict1b);
  assert.equal(verdict1a.promote, true);

  // mirrors "below-K-redeems never promotes"
  const summaryBelowK = new Map([
    [ID_A, { genome_id: ID_A, realized_usdc: 1, redeem_count: 5 }],
    [ID_B, { genome_id: ID_B, realized_usdc: 100, redeem_count: 1 }],
  ]);
  const verdict2a = evaluatePromotion({ summary: summaryBelowK, baselineId: ID_A, mutantId: ID_B, minRedeems: 3 });
  const verdict2b = evaluatePromotionDirect({ summary: summaryBelowK, baselineId: ID_A, mutantId: ID_B, minRedeems: 3 });
  assert.deepEqual(verdict2a, verdict2b);
  assert.equal(verdict2a.promote, false);

  // mirrors "challenger less-negative than a losing baseline -> NO promote (net-positive floor)"
  const summaryLessNegative = new Map([
    [ID_A, { genome_id: ID_A, realized_usdc: -5, redeem_count: 3 }],
    [ID_B, { genome_id: ID_B, realized_usdc: -2, redeem_count: 3 }],
  ]);
  const verdict3a = evaluatePromotion({ summary: summaryLessNegative, baselineId: ID_A, mutantId: ID_B, minRedeems: 3 });
  const verdict3b = evaluatePromotionDirect({ summary: summaryLessNegative, baselineId: ID_A, mutantId: ID_B, minRedeems: 3 });
  assert.deepEqual(verdict3a, verdict3b);
  assert.equal(verdict3a.promote, false);
});

// --- PROP-015b -----------------------------------------------------------------------------
test("PROP-015b: sol-evolve's promote IS the same function object imported from evolve.mjs (import-identity, mirrors PROP-014)", () => {
  assert.equal(promote, promoteDirect);
});

// --- PROP-015 --------------------------------------------------------------------------------
test("PROP-015: promote() commits ONLY the SOL canonical baseline-genome.json path (path-scoped, git show --stat = 1 file)", () => {
  const repo = tmpDir("sol-evolve-promote-");
  initGitRepo(repo);
  const canonicalPath = path.join(repo, "skills", "earn", "sol-trade", "baseline-genome.json");
  fs.mkdirSync(path.dirname(canonicalPath), { recursive: true });
  fs.writeFileSync(canonicalPath, JSON.stringify(GENOME_A, null, 2) + "\n");
  execFileSync("git", ["add", "-A"], { cwd: repo });
  execFileSync("git", ["-c", "user.name=t", "-c", "user.email=t@t.local", "commit", "-q", "-m", "seed"], { cwd: repo });

  // unrelated concurrent change that must NEVER be swept into the promotion commit
  fs.writeFileSync(path.join(repo, "unrelated.txt"), "concurrent edit elsewhere in the shared checkout");

  const result = promote(GENOME_B, { canonicalPath, cwd: repo });
  assert.ok(result.commit);
  const stat = execFileSync("git", ["show", "--stat", "--format=", result.commit], { cwd: repo, encoding: "utf8" });
  assert.match(stat, /baseline-genome\.json/);
  assert.doesNotMatch(stat, /unrelated\.txt/);
  const filesChanged = stat.trim().split("\n").filter((l) => l.includes("|"));
  assert.equal(filesChanged.length, 1);
});

// --- PROP-012b -------------------------------------------------------------------------------
test("PROP-012b: attributeGenomeIdSol resolves EACH swap to the nearest-preceding genome-linked line (multi-pass, different genome_ids)", () => {
  const trace = [
    genomeLinkLine("2026-07-01T00:00:00Z", GENOME_A, ID_A),
    { ts: "2026-07-01T00:05:00Z", slot: "earn/sol-trade", action: "live-pass", exit: 0, note: "WAIT no clear signal" },
    genomeLinkLine("2026-07-02T00:00:00Z", GENOME_B, ID_B),
    { ts: "2026-07-02T00:05:00Z", slot: "earn/sol-trade", action: "live-pass", exit: 0 },
  ];
  const swap1 = swapRow({ ts: Math.floor(Date.parse("2026-07-01T12:00:00Z") / 1000), netUsdc: 0.5, sig: "sig1" });
  const swap2 = swapRow({ ts: Math.floor(Date.parse("2026-07-03T00:00:00Z") / 1000), netUsdc: 0.3, sig: "sig2" });

  assert.equal(attributeGenomeIdSol(swap1, trace), ID_A, "swap1 preceded only by genome A's linkage line");
  assert.equal(attributeGenomeIdSol(swap2, trace), ID_B, "swap2 must attribute to the LATER genome B, not the earlier A");
});

test("PROP-012b: returns null when no genome-linked line precedes the swap", () => {
  const trace = [genomeLinkLine("2026-07-05T00:00:00Z", GENOME_A, ID_A)];
  const swap = swapRow({ ts: Math.floor(Date.parse("2026-07-01T00:00:00Z") / 1000), netUsdc: 0.1, sig: "sigX" });
  assert.equal(attributeGenomeIdSol(swap, trace), null);
});

test("PROP-012b: exact timestamp equality is treated as 'at or before' (<=)", () => {
  const ts = "2026-07-01T00:00:00Z";
  const trace = [genomeLinkLine(ts, GENOME_A, ID_A)];
  const swap = swapRow({ ts: Math.floor(Date.parse(ts) / 1000), netUsdc: 0.1, sig: "sigEq" });
  assert.equal(attributeGenomeIdSol(swap, trace), ID_A);
});

test("PROP-012b: multiple preceding genome-linked lines -> selects the LARGEST (nearest) timestamp, never earliest/average", () => {
  const trace = [
    genomeLinkLine("2026-07-01T00:00:00Z", GENOME_A, ID_A),
    genomeLinkLine("2026-07-01T06:00:00Z", GENOME_B, ID_B),
  ];
  const swap = swapRow({ ts: Math.floor(Date.parse("2026-07-01T12:00:00Z") / 1000), netUsdc: 0.2, sig: "sigNearest" });
  assert.equal(attributeGenomeIdSol(swap, trace), ID_B);
});

test("PROP-012b: does NOT compare any market/task/mint field (structural, mirrors record-swap.mjs's fixed-constant task)", () => {
  const trace = [genomeLinkLine("2026-07-01T00:00:00Z", GENOME_A, ID_A)];
  const swapDefaultTask = swapRow({ ts: Math.floor(Date.parse("2026-07-01T06:00:00Z") / 1000), netUsdc: 0.1, sig: "s1" });
  const swapDifferentTask = { ...swapDefaultTask, task: "some totally different string that never appears in the trace", sig: "s2" };
  assert.equal(attributeGenomeIdSol(swapDefaultTask, trace), attributeGenomeIdSol(swapDifferentTask, trace));
});

test("PROP-012b: fast-check randomized multi-pass timestamp sequences always attribute to the correct nearest-preceding genome", () => {
  fc.assert(
    fc.property(fc.array(fc.integer({ min: 0, max: 10 }), { minLength: 2, maxLength: 6 }), (offsets) => {
      let t = 1_800_000_000;
      const links = offsets.map((offset, i) => {
        t += offset + 1; // strictly increasing timestamps
        const id = i % 2 === 0 ? ID_A : ID_B;
        const genome = i % 2 === 0 ? GENOME_A : GENOME_B;
        return { ts: new Date(t * 1000).toISOString(), slot: "earn/sol-trade", action: "genome", genome_id: id, genome };
      });
      for (let i = 0; i < links.length; i++) {
        // Use the link's OWN timestamp exactly (never +1): links are strictly increasing by >=1s
        // by construction, so this is always < the NEXT link's ts (avoiding an off-by-one overlap
        // with it) while still being >= this link's own ts (exercising the "<=" / "at or before"
        // contract, REQ-012b's own exact-equality edge case).
        const swapTs = Math.floor(Date.parse(links[i].ts) / 1000);
        const swap = swapRow({ ts: swapTs, netUsdc: 0.1, sig: `sig-${i}` });
        assert.equal(attributeGenomeIdSol(swap, links), links[i].genome_id);
      }
    }),
  );
});

// --- PROP-013 --------------------------------------------------------------------------------
test("PROP-013: summarizeByGenomeSol counts ONLY source===sol-trade && sig present && confirmed===true rows", () => {
  const trace = [genomeLinkLine("2026-07-01T00:00:00Z", GENOME_A, ID_A)];
  const rows = [
    swapRow({ ts: Math.floor(Date.parse("2026-07-01T01:00:00Z") / 1000), netUsdc: 0.5, sig: "ok1" }), // counted
    swapRow({ ts: Math.floor(Date.parse("2026-07-01T02:00:00Z") / 1000), netUsdc: 0.4, sig: "notconf", confirmed: false }), // excluded
    swapRow({ ts: Math.floor(Date.parse("2026-07-01T03:00:00Z") / 1000), netUsdc: 0.4, sig: "", confirmed: true }), // excluded (no sig)
    swapRow({ ts: Math.floor(Date.parse("2026-07-01T04:00:00Z") / 1000), netUsdc: 0.4, sig: "othersrc", confirmed: true, source: "polymarket-redeem" }), // excluded
  ];
  const summary = summarizeByGenomeSol(rows, trace);
  assert.equal(summary.get(ID_A).realized_usdc, 0.5);
  assert.equal(summary.get(ID_A).redeem_count, 1);
});

test("PROP-013: WIN row (net_usdc +0.5) + LOSS row (net_usdc -0.3), SAME genome -> realized_usdc === 0.2 EXACTLY (net_usdc, never earn_usdc)", () => {
  const trace = [genomeLinkLine("2026-07-01T00:00:00Z", GENOME_A, ID_A)];
  const rows = [
    swapRow({ ts: Math.floor(Date.parse("2026-07-01T01:00:00Z") / 1000), netUsdc: 0.5, sig: "win1" }),
    swapRow({ ts: Math.floor(Date.parse("2026-07-01T02:00:00Z") / 1000), netUsdc: -0.3, sig: "loss1" }),
  ];
  const summary = summarizeByGenomeSol(rows, trace);
  assert.equal(summary.get(ID_A).realized_usdc, 0.2, "a summarizer that sums earn_usdc instead of net_usdc would yield 0.5 and MUST fail this test");
  assert.equal(summary.get(ID_A).redeem_count, 2);
});

test("PROP-013 edge case: a genome whose ONLY counted rows are net-negative has a NEGATIVE summed realized_usdc", () => {
  const trace = [genomeLinkLine("2026-07-01T00:00:00Z", GENOME_A, ID_A)];
  const rows = [
    swapRow({ ts: Math.floor(Date.parse("2026-07-01T01:00:00Z") / 1000), netUsdc: -0.2, sig: "l1" }),
    swapRow({ ts: Math.floor(Date.parse("2026-07-01T02:00:00Z") / 1000), netUsdc: -0.1, sig: "l2" }),
  ];
  const summary = summarizeByGenomeSol(rows, trace);
  assert.ok(summary.get(ID_A).realized_usdc < 0);
});

test("PROP-013 edge case: an unattributed confirmed row (no preceding genome-link) counts toward NO genome", () => {
  const trace = [genomeLinkLine("2026-07-05T00:00:00Z", GENOME_A, ID_A)]; // AFTER the swap below
  const rows = [swapRow({ ts: Math.floor(Date.parse("2026-07-01T00:00:00Z") / 1000), netUsdc: 0.5, sig: "unattributed" })];
  const summary = summarizeByGenomeSol(rows, trace);
  assert.equal(summary.size, 0);
});

test("PROP-013: fast-check randomized mixed ledger only counts the valid (sol-trade + sig + confirmed) category, sums net_usdc exactly", () => {
  fc.assert(
    fc.property(
      fc.array(
        fc.record({
          netUsdc: fc.double({ min: -5, max: 5, noNaN: true }),
          confirmed: fc.boolean(),
          hasSig: fc.boolean(),
          source: fc.constantFrom("sol-trade", "sol-trade", "other-source"),
        }),
        { minLength: 1, maxLength: 8 },
      ),
      (specs) => {
        const trace = [genomeLinkLine("2026-07-01T00:00:00Z", GENOME_A, ID_A)];
        let expectedSum = 0;
        let expectedCount = 0;
        const rows = specs.map((s, i) => {
          const netUsdc = Math.round(s.netUsdc * 1e6) / 1e6;
          const row = swapRow({
            ts: Math.floor(Date.parse("2026-07-01T01:00:00Z") / 1000) + i,
            netUsdc,
            sig: s.hasSig ? `sig-${i}` : "",
            confirmed: s.confirmed,
            source: s.source,
          });
          const valid = row.source === "sol-trade" && typeof row.sig === "string" && row.sig.length > 0 && row.confirmed === true;
          if (valid) {
            expectedSum += row.net_usdc;
            expectedCount += 1;
          }
          return row;
        });
        const summary = summarizeByGenomeSol(rows, trace);
        if (expectedCount === 0) {
          assert.equal(summary.size, 0);
        } else {
          const entry = summary.get(ID_A);
          assert.equal(entry.redeem_count, expectedCount);
          assert.ok(Math.abs(entry.realized_usdc - Math.round(expectedSum * 1e6) / 1e6) < 1e-6);
        }
      },
    ),
  );
});

// --- FIND-002 (impl-review iteration-1): runEvolveSol orchestration + CLI entrypoint -----------
// Mirrors evolve.test.mjs's own runEvolve E2E fixtures shape, using SOL's field names/genome
// shapes. NEVER touches the real the canonical checkout repo or real earn-ledger.jsonl -- every git op runs in a
// fresh temp repo (initGitRepo), every ledger/trace path is a fresh temp file.
test("FIND-002 E2E PROMOTE: mutant B beats baseline A (0), has >=K=3 chain-verified confirmed swaps -> promoted, canonical baseline written + committed", async () => {
  const repo = tmpDir("sol-evolve-e2e-promote-");
  initGitRepo(repo);
  const canonicalPath = path.join(repo, "skills", "earn", "sol-trade", "baseline-genome.json");
  fs.mkdirSync(path.dirname(canonicalPath), { recursive: true });
  fs.writeFileSync(canonicalPath, JSON.stringify(GENOME_A, null, 2) + "\n");
  execFileSync("git", ["add", "-A"], { cwd: repo });
  execFileSync("git", ["-c", "user.name=t", "-c", "user.email=t@t.local", "commit", "-q", "-m", "seed baseline A"], { cwd: repo });

  const stateDir = path.join(repo, "state");
  const tracePath = path.join(stateDir, "sol-trade.trace.jsonl");
  const ledgerPath = path.join(stateDir, "earn-ledger.jsonl");

  writeJsonl(tracePath, [
    genomeLinkLine("2026-07-01T00:00:00Z", GENOME_A, ID_A),
    genomeLinkLine("2026-07-02T00:00:00Z", GENOME_B, ID_B),
  ]);
  writeJsonl(ledgerPath, [
    swapRow({ ts: Math.floor(Date.parse("2026-07-02T01:00:00Z") / 1000), netUsdc: 0.5, sig: "sig-b1" }),
    swapRow({ ts: Math.floor(Date.parse("2026-07-02T02:00:00Z") / 1000), netUsdc: 0.4, sig: "sig-b2" }),
    swapRow({ ts: Math.floor(Date.parse("2026-07-02T03:00:00Z") / 1000), netUsdc: 0.3, sig: "sig-b3" }),
  ]);

  const before = execFileSync("git", ["rev-parse", "HEAD"], { cwd: repo }).toString().trim();
  const result = await runEvolveSol({ ledgerPath, tracePath, canonicalPath, minRedeems: 3, cwd: repo });
  const after = execFileSync("git", ["rev-parse", "HEAD"], { cwd: repo }).toString().trim();

  assert.equal(result.promoted, true, "B must be promoted: net-positive, beats baseline's 0 floor, >=3 confirmed swaps");
  assert.equal(result.newBaselineId, ID_B);
  assert.notEqual(before, after, "a real git commit must have been made");

  const writtenBaseline = JSON.parse(fs.readFileSync(canonicalPath, "utf8"));
  assert.deepEqual(writtenBaseline, GENOME_B, "canonical baseline-genome.json now holds B's actual knob values");
});

test("FIND-002: runEvolveSol does NOT promote a mutant below K=3 confirmed swaps (cold-start-adjacent)", async () => {
  const repo = tmpDir("sol-evolve-e2e-belowk-");
  initGitRepo(repo);
  const canonicalPath = path.join(repo, "baseline-genome.json");
  fs.writeFileSync(canonicalPath, JSON.stringify(GENOME_A, null, 2) + "\n");
  execFileSync("git", ["add", "baseline-genome.json"], { cwd: repo });
  execFileSync("git", ["-c", "user.name=t", "-c", "user.email=t@t.local", "commit", "-q", "-m", "seed"], { cwd: repo });

  const stateDir = path.join(repo, "state");
  const tracePath = path.join(stateDir, "sol-trade.trace.jsonl");
  const ledgerPath = path.join(stateDir, "earn-ledger.jsonl");
  writeJsonl(tracePath, [genomeLinkLine("2026-07-02T00:00:00Z", GENOME_B, ID_B)]);
  writeJsonl(ledgerPath, [
    swapRow({ ts: Math.floor(Date.parse("2026-07-02T01:00:00Z") / 1000), netUsdc: 5.0, sig: "sig-1" }),
    swapRow({ ts: Math.floor(Date.parse("2026-07-02T02:00:00Z") / 1000), netUsdc: 5.0, sig: "sig-2" }),
  ]);

  const before = execFileSync("git", ["rev-parse", "HEAD"], { cwd: repo }).toString().trim();
  const result = await runEvolveSol({ ledgerPath, tracePath, canonicalPath, minRedeems: 3, cwd: repo });
  const after = execFileSync("git", ["rev-parse", "HEAD"], { cwd: repo }).toString().trim();

  assert.equal(result.promoted, false);
  assert.match(result.evaluations[ID_B].reason, /below-K-redeems/);
  assert.equal(before, after, "no commit must have been made");
});

test("FIND-002: runEvolveSol does NOT promote a still-net-losing mutant even if less negative than a losing baseline", async () => {
  const repo = tmpDir("sol-evolve-e2e-lessneg-");
  initGitRepo(repo);
  const canonicalPath = path.join(repo, "baseline-genome.json");
  fs.writeFileSync(canonicalPath, JSON.stringify(GENOME_A, null, 2) + "\n");
  execFileSync("git", ["add", "baseline-genome.json"], { cwd: repo });
  execFileSync("git", ["-c", "user.name=t", "-c", "user.email=t@t.local", "commit", "-q", "-m", "seed"], { cwd: repo });

  const stateDir = path.join(repo, "state");
  const tracePath = path.join(stateDir, "sol-trade.trace.jsonl");
  const ledgerPath = path.join(stateDir, "earn-ledger.jsonl");
  writeJsonl(tracePath, [
    genomeLinkLine("2026-07-01T00:00:00Z", GENOME_A, ID_A),
    genomeLinkLine("2026-07-02T00:00:00Z", GENOME_B, ID_B),
  ]);
  writeJsonl(ledgerPath, [
    // baseline A: -5 total across 3 confirmed swaps
    swapRow({ ts: Math.floor(Date.parse("2026-07-01T01:00:00Z") / 1000), netUsdc: -2, sig: "a1" }),
    swapRow({ ts: Math.floor(Date.parse("2026-07-01T02:00:00Z") / 1000), netUsdc: -2, sig: "a2" }),
    swapRow({ ts: Math.floor(Date.parse("2026-07-01T03:00:00Z") / 1000), netUsdc: -1, sig: "a3" }),
    // mutant B: -2 total across 3 confirmed swaps (LESS negative than A, but still a loser)
    swapRow({ ts: Math.floor(Date.parse("2026-07-02T01:00:00Z") / 1000), netUsdc: -1, sig: "b1" }),
    swapRow({ ts: Math.floor(Date.parse("2026-07-02T02:00:00Z") / 1000), netUsdc: -0.5, sig: "b2" }),
    swapRow({ ts: Math.floor(Date.parse("2026-07-02T03:00:00Z") / 1000), netUsdc: -0.5, sig: "b3" }),
  ]);

  const before = execFileSync("git", ["rev-parse", "HEAD"], { cwd: repo }).toString().trim();
  const result = await runEvolveSol({ ledgerPath, tracePath, canonicalPath, minRedeems: 3, cwd: repo });
  const after = execFileSync("git", ["rev-parse", "HEAD"], { cwd: repo }).toString().trim();

  assert.equal(result.summary[ID_A].realized_usdc, -5);
  assert.equal(result.summary[ID_B].realized_usdc, -2);
  assert.equal(result.promoted, false, "-2 beats -5 but is still a LOSS -- must never promote (HARD 0.24)");
  assert.match(result.evaluations[ID_B].reason, /challenger-not-net-positive/);
  assert.equal(before, after, "no commit must have been made");
});

test("FIND-002: runEvolveSol cold-start (missing ledger/trace files) never throws, promoted:false", async () => {
  const dir = tmpDir("sol-evolve-cold-start-");
  const result = await runEvolveSol({
    ledgerPath: path.join(dir, "does-not-exist-ledger.jsonl"),
    tracePath: path.join(dir, "does-not-exist-trace.jsonl"),
    canonicalPath: path.join(dir, "does-not-exist-baseline.json"),
    minRedeems: 3,
    cwd: dir,
  });
  assert.equal(result.promoted, false);
  assert.equal(result.baselineId, ID_A, "missing canonical falls back to SAFE_DEFAULT_GENOME's own id");
});

test("FIND-002: sol-evolve.mjs CLI entrypoint runs standalone, prints promoted:false JSON for cold-start fixtures, never touches the real repo", () => {
  const cliPath = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "sol-evolve.mjs");
  const dir = tmpDir("sol-evolve-cli-smoke-");
  const ledgerPath = path.join(dir, "no-ledger.jsonl");
  const tracePath = path.join(dir, "no-trace.jsonl");
  const out = execFileSync(process.execPath, [cliPath, ledgerPath, tracePath], { encoding: "utf8" });
  const parsed = JSON.parse(out);
  assert.equal(parsed.promoted, false);
});
