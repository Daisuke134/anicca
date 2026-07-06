// node:test — P1 fail-closed CUMULATIVE earn>spend guard (spec .vcsdd/features/anicca-agent-economy
// §3 P1 / §4). ledger.mjs already proves ONE pass profitable; this proves the CUMULATIVE
// invariant across many passes and the fail-closed HALT the instant it breaks.
import { test } from "node:test";
import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { appendLedger, deriveLine } from "../ledger.mjs";
import { cumulativeNet, evaluateScope, evaluateHalt, checkHalt, DEFAULT_RESERVE_USDC } from "../earn-guard.mjs";

async function tmpLedger() {
  const d = await fs.mkdtemp(path.join(os.tmpdir(), "earn-guard-"));
  return path.join(d, "earn-ledger.jsonl");
}

function line(o) {
  return deriveLine(o);
}

// ---------------------------------------------------------------------------
// cumulativeNet: pure sum over a scope.
// ---------------------------------------------------------------------------
test("cumulativeNet sums net_usdc across matching lines only (wallet+source scope)", () => {
  const lines = [
    line({ wallet: "0xa", source: "polymarket-redeem", earn_usdc: 1, cost_usdc: 0.4 }), // net 0.6
    line({ wallet: "0xa", source: "polymarket-redeem", earn_usdc: 0.5, cost_usdc: 0.1 }), // net 0.4
    line({ wallet: "0xa", source: "hl-trade", earn_usdc: 5, cost_usdc: 0 }), // different source, excluded
    line({ wallet: "0xb", source: "polymarket-redeem", earn_usdc: 9, cost_usdc: 0 }), // different wallet, excluded
  ];
  const { cumulativeNet: net, trustworthy } = cumulativeNet(lines, { wallet: "0xa", source: "polymarket-redeem" });
  assert.equal(net, 1.0);
  assert.equal(trustworthy, true);
});

test("cumulativeNet with wallet-only scope aggregates every source for that agent", () => {
  const lines = [
    line({ wallet: "0xa", source: "polymarket-redeem", earn_usdc: 1, cost_usdc: 0.4 }), // net 0.6
    line({ wallet: "0xa", source: "hl-trade", earn_usdc: 0.2, cost_usdc: 0.1 }), // net 0.1
    line({ wallet: "0xb", source: "hl-trade", earn_usdc: 9, cost_usdc: 0 }), // different agent, excluded
  ];
  const { cumulativeNet: net } = cumulativeNet(lines, { wallet: "0xa" });
  assert.equal(net, 0.7);
});

// ---------------------------------------------------------------------------
// evaluateScope: positive cumulative net -> continue (no halt).
// ---------------------------------------------------------------------------
test("positive cumulative net -> no halt, reserve=0 default", () => {
  const lines = [
    line({ wallet: "0xa", source: "hl-trade", earn_usdc: 2, cost_usdc: 1 }), // net +1
    line({ wallet: "0xa", source: "hl-trade", earn_usdc: 3, cost_usdc: 2 }), // net +1 (cum +2)
  ];
  const r = evaluateScope(lines, { wallet: "0xa", source: "hl-trade" });
  assert.equal(r.halt, false);
  assert.equal(r.reason, null);
  assert.equal(r.cumulativeNet, 2);
});

// ---------------------------------------------------------------------------
// evaluateScope: a pass that pushes cumulative net negative -> HALT (the spec's exact
// verification: "赤字になる pass が実際に停止").
// ---------------------------------------------------------------------------
test("a pass that pushes cumulative net negative -> HALT", () => {
  const lines = [
    line({ wallet: "0xa", source: "hl-trade", earn_usdc: 1, cost_usdc: 0 }), // net +1 (cum +1)
    line({ wallet: "0xa", source: "hl-trade", earn_usdc: 0, cost_usdc: 1.5 }), // net -1.5 (cum -0.5) <- this pass tips it
  ];
  const r = evaluateScope(lines, { wallet: "0xa", source: "hl-trade" });
  assert.equal(r.halt, true);
  assert.equal(r.reason, "cumulative-net-below-reserve");
  assert.equal(r.cumulativeNet, -0.5);
});

test("still-positive-but-declining cumulative net does NOT halt (only actual deficit halts)", () => {
  const lines = [
    line({ wallet: "0xa", source: "hl-trade", earn_usdc: 5, cost_usdc: 0 }), // net +5
    line({ wallet: "0xa", source: "hl-trade", earn_usdc: 0, cost_usdc: 4 }), // net -4 (cum +1, still solvent)
  ];
  const r = evaluateScope(lines, { wallet: "0xa", source: "hl-trade" });
  assert.equal(r.halt, false);
  assert.equal(r.cumulativeNet, 1);
});

// ---------------------------------------------------------------------------
// missing/malformed spend or income fields -> fail-closed HALT (never silently zero it).
// ---------------------------------------------------------------------------
test("malformed earn_usdc (non-numeric) -> fail-closed HALT even though prior passes were profitable", () => {
  const lines = [
    line({ wallet: "0xa", source: "hl-trade", earn_usdc: 10, cost_usdc: 1 }), // net +9, healthy
    line({ wallet: "0xa", source: "hl-trade", earn_usdc: "oops", cost_usdc: 1 }), // malformed -> net NaN
  ];
  const r = evaluateScope(lines, { wallet: "0xa", source: "hl-trade" });
  assert.equal(r.halt, true);
  assert.equal(r.reason, "malformed-ledger-data");
  assert.equal(r.cumulativeNet, null);
});

test("malformed cost_usdc (non-numeric) -> fail-closed HALT", () => {
  const lines = [line({ wallet: "0xa", source: "hl-trade", earn_usdc: 5, cost_usdc: "???" })];
  const r = evaluateScope(lines, { wallet: "0xa", source: "hl-trade" });
  assert.equal(r.halt, true);
  assert.equal(r.reason, "malformed-ledger-data");
});

test("a raw (non-derived) line with missing earn_usdc/cost_usdc entirely -> fail-closed HALT", () => {
  // simulate a line that never went through deriveLine (e.g. a hand-crafted/corrupt ledger row)
  const lines = [{ wallet: "0xa", source: "hl-trade", net_usdc: undefined }];
  const r = evaluateScope(lines, { wallet: "0xa", source: "hl-trade" });
  assert.equal(r.halt, true);
  assert.equal(r.reason, "malformed-ledger-data");
});

// ---------------------------------------------------------------------------
// reserve-threshold boundary.
// ---------------------------------------------------------------------------
test("reserve boundary: cumulative net exactly AT the reserve -> NOT halted (inclusive)", () => {
  const lines = [line({ wallet: "0xa", source: "hl-trade", earn_usdc: 2, cost_usdc: 1 })]; // net +1
  const r = evaluateScope(lines, { wallet: "0xa", source: "hl-trade" }, 1);
  assert.equal(r.halt, false);
  assert.equal(r.cumulativeNet, 1);
});

test("reserve boundary: cumulative net one cent below the reserve -> HALT", () => {
  const lines = [line({ wallet: "0xa", source: "hl-trade", earn_usdc: 2, cost_usdc: 1.01 })]; // net 0.99
  const r = evaluateScope(lines, { wallet: "0xa", source: "hl-trade" }, 1);
  assert.equal(r.halt, true);
  assert.equal(r.reason, "cumulative-net-below-reserve");
});

test("DEFAULT_RESERVE_USDC is 0 (halt only on a true deficit, not on break-even)", () => {
  assert.equal(DEFAULT_RESERVE_USDC, 0);
  const lines = [line({ wallet: "0xa", source: "hl-trade", earn_usdc: 1, cost_usdc: 1 })]; // net exactly 0
  const r = evaluateScope(lines, { wallet: "0xa", source: "hl-trade" });
  assert.equal(r.halt, false);
});

// ---------------------------------------------------------------------------
// evaluateHalt: the per-skill (wallet+source) AND per-agent (wallet) union gate.
// ---------------------------------------------------------------------------
test("evaluateHalt: HALTs if the per-SKILL scope is insolvent even though the per-AGENT (wallet-wide) total is positive", () => {
  const lines = [
    line({ wallet: "0xa", source: "hl-trade", earn_usdc: 0, cost_usdc: 2 }), // this skill: net -2
    line({ wallet: "0xa", source: "polymarket-redeem", earn_usdc: 10, cost_usdc: 0 }), // other skill: net +10
  ];
  const r = evaluateHalt(lines, { wallet: "0xa", source: "hl-trade" });
  assert.equal(r.halt, true);
  assert.equal(r.reason, "cumulative-net-below-reserve");
  assert.equal(r.bySkill.halt, true);
  assert.equal(r.byAgent.halt, false, "wallet-wide total (+8) is still solvent");
});

test("evaluateHalt: HALTs if the per-AGENT (wallet) total is insolvent even though THIS skill alone is positive", () => {
  const lines = [
    line({ wallet: "0xa", source: "hl-trade", earn_usdc: 1, cost_usdc: 0 }), // this skill: net +1
    line({ wallet: "0xa", source: "sol-trade", earn_usdc: 0, cost_usdc: 5 }), // sibling skill: net -5
  ];
  const r = evaluateHalt(lines, { wallet: "0xa", source: "hl-trade" });
  assert.equal(r.halt, true);
  assert.equal(r.bySkill.halt, false, "this skill alone (+1) is fine");
  assert.equal(r.byAgent.halt, true, "wallet-wide total (-4) is insolvent");
});

test("evaluateHalt: source omitted -> only the per-agent (wallet) scope is evaluated, bySkill is null", () => {
  const lines = [line({ wallet: "0xa", source: "hl-trade", earn_usdc: 0, cost_usdc: 1 })];
  const r = evaluateHalt(lines, { wallet: "0xa" });
  assert.equal(r.bySkill, null);
  assert.equal(r.byAgent.halt, true);
  assert.equal(r.halt, true);
});

test("evaluateHalt: both scopes solvent -> no halt", () => {
  const lines = [line({ wallet: "0xa", source: "hl-trade", earn_usdc: 3, cost_usdc: 1 })];
  const r = evaluateHalt(lines, { wallet: "0xa", source: "hl-trade" });
  assert.equal(r.halt, false);
  assert.equal(r.reason, null);
});

// ---------------------------------------------------------------------------
// ADVERSARY FINDING A/B (round 2): a missing/empty wallet must NEVER silently become a
// cross-wallet aggregate (scope.wallet==null matches every line) or a "matches nothing, so it
// looks solvent" false pass (scope.wallet=="" matches zero lines) — evaluateHalt/checkHalt
// MUST assert a non-empty wallet BEFORE computing any scope and fail-closed HALT otherwise.
// ---------------------------------------------------------------------------
test("FIND-B: evaluateHalt with wallet omitted entirely -> fail-closed HALT, reason missing-wallet, no scopes computed", () => {
  const lines = [line({ wallet: "0xa", source: "hl-trade", earn_usdc: 5, cost_usdc: 0 })]; // healthy, irrelevant
  const r = evaluateHalt(lines, { source: "hl-trade" });
  assert.equal(r.halt, true);
  assert.equal(r.reason, "missing-wallet");
  assert.equal(r.bySkill, null);
  assert.equal(r.byAgent, null);
});

test("FIND-B: evaluateHalt with wallet='' (empty string) -> fail-closed HALT, not a false 'matches nothing' pass", () => {
  const lines = [line({ wallet: "0xa", source: "hl-trade", earn_usdc: 0, cost_usdc: 999 })]; // a real, huge loss elsewhere
  const r = evaluateHalt(lines, { wallet: "", source: "hl-trade" });
  assert.equal(r.halt, true);
  assert.equal(r.reason, "missing-wallet");
});

test("FIND-B: evaluateHalt called with NO scope args at all -> fail-closed HALT (never silently checks nothing)", () => {
  const r = evaluateHalt([line({ wallet: "0xa", source: "hl-trade", earn_usdc: 1, cost_usdc: 0 })]);
  assert.equal(r.halt, true);
  assert.equal(r.reason, "missing-wallet");
});

test("FIND-B regression: an omitted wallet must NOT silently cross-aggregate two different agents' totals", () => {
  // 0xa is deeply insolvent (-100); 0xb is rich (+200). A naive wallet-less scope would sum to
  // +100 and report 'solvent' — hiding 0xa's real deficit under 0xb's surplus. Must HALT instead.
  const lines = [
    line({ wallet: "0xa", source: "hl-trade", earn_usdc: 0, cost_usdc: 100 }),
    line({ wallet: "0xb", source: "hl-trade", earn_usdc: 200, cost_usdc: 0 }),
  ];
  const r = evaluateHalt(lines, { source: "hl-trade" });
  assert.equal(r.halt, true);
  assert.equal(r.reason, "missing-wallet");
});

test("FIND-B: checkHalt (I/O wrapper) also fail-closed HALTs on a missing wallet against a real ledger file", async () => {
  const f = await tmpLedger();
  await appendLedger(f, line({ wallet: "0xa", source: "hl-trade", earn_usdc: 5, cost_usdc: 0 }));
  const r = await checkHalt(f, { source: "hl-trade" }); // wallet omitted
  assert.equal(r.halt, true);
  assert.equal(r.reason, "missing-wallet");
});

test("valid non-empty wallet is unaffected by the FIND-B fix (regression: normal solvent case still passes)", () => {
  const lines = [line({ wallet: "0xa", source: "hl-trade", earn_usdc: 3, cost_usdc: 1 })];
  const r = evaluateHalt(lines, { wallet: "0xa", source: "hl-trade" });
  assert.equal(r.halt, false);
  assert.equal(r.reason, null);
  assert.ok(r.bySkill && r.byAgent, "both scopes ARE computed for a valid wallet");
});

// ---------------------------------------------------------------------------
// ADVERSARY FINDING C (round 2): wallet matching must be case-insensitive — a mixed-case wallet
// in a ledger line must still be found under a lowercased scope wallet (and vice versa), or a
// real loss silently escapes every check because of a casing mismatch.
// ---------------------------------------------------------------------------
test("FIND-C: a mixed-case wallet in the ledger line is matched by a lowercase scope wallet", () => {
  const lines = [line({ wallet: "0xABCDEF0000000000000000000000000000000001", source: "hl-trade", earn_usdc: 1, cost_usdc: 0.4 })];
  const { cumulativeNet: net } = cumulativeNet(lines, { wallet: "0xabcdef0000000000000000000000000000000001", source: "hl-trade" });
  assert.equal(net, 0.6, "case must not stop the sum from finding this line");
});

test("FIND-C: a real loss recorded under a mixed-case wallet still triggers HALT when checked lowercase", () => {
  const lines = [line({ wallet: "0xABCDEF0000000000000000000000000000000001", source: "hl-trade", earn_usdc: 0, cost_usdc: 50 })];
  const r = evaluateHalt(lines, { wallet: "0xabcdef0000000000000000000000000000000001", source: "hl-trade" });
  assert.equal(r.halt, true, "the mixed-case loss must not silently escape the lowercase-scoped check");
  assert.equal(r.reason, "cumulative-net-below-reserve");
});

test("FIND-C: scope wallet in upper/mixed case also finds a lowercase-recorded line (symmetric)", () => {
  const lines = [line({ wallet: "0xa", source: "hl-trade", earn_usdc: 0, cost_usdc: 3 })];
  const r = evaluateHalt(lines, { wallet: "0XA", source: "hl-trade" });
  assert.equal(r.halt, true);
});

// ---------------------------------------------------------------------------
// checkHalt: I/O wrapper reads the REAL ledger off disk (append-only, same file record.mjs writes).
// ---------------------------------------------------------------------------
test("checkHalt reads a real ledger file and halts once appended lines go net-negative", async () => {
  const f = await tmpLedger();
  await appendLedger(f, line({ wallet: "0xc", source: "x402-sell", earn_usdc: 1, cost_usdc: 0.2 })); // +0.8
  let r = await checkHalt(f, { wallet: "0xc", source: "x402-sell" });
  assert.equal(r.halt, false);

  await appendLedger(f, line({ wallet: "0xc", source: "x402-sell", earn_usdc: 0, cost_usdc: 2 })); // -2 (cum -1.2)
  r = await checkHalt(f, { wallet: "0xc", source: "x402-sell" });
  assert.equal(r.halt, true);
  assert.equal(r.reason, "cumulative-net-below-reserve");
  assert.equal(r.bySkill.cumulativeNet, -1.2);
});

test("checkHalt on a missing ledger file -> zero lines -> solvent (no halt, not fail-closed for absence)", async () => {
  const r = await checkHalt("/no/such/path/earn-ledger.jsonl", { wallet: "0xc", source: "x402-sell" });
  assert.equal(r.halt, false);
  assert.equal(r.bySkill.cumulativeNet, 0);
});

// ---------------------------------------------------------------------------
// ADVERSARY FINDING D (round 2): ledger.mjs's readLedger silently DROPS any line that fails
// JSON.parse (a crash mid-append truncates the last line, e.g.). earn-guard's own read path
// must detect that and fail-closed HALT — summing over a silently-dropped line could hide the
// exact loss that made this wallet insolvent. Do NOT change ledger.mjs's shared drop-on-parse-
// error behavior (other callers may depend on that resilience) — earn-guard reads independently.
// ---------------------------------------------------------------------------
test("FIND-D: a truncated/corrupt line in the ledger file -> fail-closed HALT, even though the parseable lines look solvent", async () => {
  const f = await tmpLedger();
  await appendLedger(f, line({ wallet: "0xd", source: "x402-sell", earn_usdc: 100, cost_usdc: 1 })); // healthy +99
  // simulate a crash mid-append: a second line that never finished writing (no closing brace).
  await fs.appendFile(f, '{"wallet":"0xd","source":"x402-sell","earn_usdc":0,"cost_\n', "utf8");
  const r = await checkHalt(f, { wallet: "0xd", source: "x402-sell" });
  assert.equal(r.halt, true);
  assert.equal(r.reason, "unparseable-ledger-line");
});

test("FIND-D: a corrupt line for a DIFFERENT wallet still halts this wallet's check (can't prove the gap wasn't ours)", async () => {
  const f = await tmpLedger();
  await appendLedger(f, line({ wallet: "0xe", source: "x402-sell", earn_usdc: 10, cost_usdc: 1 }));
  await fs.appendFile(f, "not even close to json\n", "utf8");
  const r = await checkHalt(f, { wallet: "0xe", source: "x402-sell" });
  assert.equal(r.halt, true);
  assert.equal(r.reason, "unparseable-ledger-line");
});

test("FIND-D regression: a clean ledger (every line parses) is completely unaffected — no false HALT", async () => {
  const f = await tmpLedger();
  await appendLedger(f, line({ wallet: "0xf", source: "x402-sell", earn_usdc: 10, cost_usdc: 1 }));
  await appendLedger(f, line({ wallet: "0xf", source: "x402-sell", earn_usdc: 2, cost_usdc: 1 }));
  const r = await checkHalt(f, { wallet: "0xf", source: "x402-sell" });
  assert.equal(r.halt, false);
  assert.equal(r.bySkill.cumulativeNet, 10);
});

test("FIND-D regression: blank lines between real lines are still just skipped (not treated as corruption)", async () => {
  const f = await tmpLedger();
  await appendLedger(f, line({ wallet: "0xg", source: "x402-sell", earn_usdc: 5, cost_usdc: 1 }));
  await fs.appendFile(f, "\n\n", "utf8"); // blank lines only — NOT corruption
  await appendLedger(f, line({ wallet: "0xg", source: "x402-sell", earn_usdc: 1, cost_usdc: 1 }));
  const r = await checkHalt(f, { wallet: "0xg", source: "x402-sell" });
  assert.equal(r.halt, false);
  assert.equal(r.bySkill.cumulativeNet, 4);
});

// ---------------------------------------------------------------------------
// CLI-level regression for FIND-A/B: the CLI must map an empty/missing wallet to exit 1 (HALT),
// never exit 2 (usage error) and never exit 0 (silent pass) — this is exactly what run.sh relies
// on when it now ALWAYS calls the guard (no more `[ -n "$WLOW" ] &&` bash-side bypass, FIND-A fix).
// ---------------------------------------------------------------------------
test("CLI: `check '' '' <ledger>` (empty wallet) exits 1 (HALT), not 2 (usage) and not 0 (pass)", async () => {
  const f = await tmpLedger();
  const { execFile } = await import("node:child_process");
  const { promisify } = await import("node:util");
  const run = promisify(execFile);
  const cli = new URL("../earn-guard.mjs", import.meta.url).pathname;
  await assert.rejects(
    run("node", [cli, "check", "", "", f]),
    (e) => {
      assert.equal(e.code, 1, "must be the HALT exit code, not usage(2) or pass(0)");
      assert.match(e.stderr, /missing-wallet/);
      return true;
    }
  );
});
