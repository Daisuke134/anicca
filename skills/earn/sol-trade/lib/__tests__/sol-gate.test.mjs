// VCSDD RED->GREEN: SOL pre-gate pure decision function + free-market-signal fetch wrapper
// (franklin-sol-evolvable-edge, REQ-007/008/009/010). decideEngagement is THE single most
// safety-critical pure function in this feature (verification-architecture.md).
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import fc from "fast-check";

import {
  decideEngagement,
  isLiveEnabled,
  fetchSolMarketSignal,
  describeSignal,
  DEFAULT_TIMEOUT_MS,
} from "../sol-gate.mjs";
import { SAFE_DEFAULT_GENOME } from "../sol-genome.mjs";

function tmpDir(prefix) {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

// --- PROP-008 (Tier 2, fast-check) -----------------------------------------------------------
test("PROP-008: wouldEngage true iff momentum/liquidity/conviction thresholds ALL hold simultaneously", () => {
  fc.assert(
    fc.property(
      fc.double({ min: -20, max: 20, noNaN: true }),
      fc.double({ min: 0, max: 5_000_000, noNaN: true }),
      (momentumPct, liquidityUsd) => {
        const genome = SAFE_DEFAULT_GENOME;
        const { wouldEngage, conviction } = decideEngagement({
          momentumPct,
          liquidityUsd,
          ageSec: 0,
          genome,
          liveEnabled: false,
        });
        const momentumOk = Math.abs(momentumPct) >= genome.SOL_GATE_MIN_MOMENTUM_PCT;
        const liquidityOk = liquidityUsd >= genome.SOL_GATE_MIN_LIQUIDITY_USD;
        const convictionOk = conviction >= genome.SOL_GATE_MIN_CONVICTION;
        assert.equal(wouldEngage, momentumOk && liquidityOk && convictionOk);
      },
    ),
  );
});

test("REQ-008 edge case: momentumPct === 0 (flat market) -> wouldEngage MUST be false", () => {
  const { wouldEngage } = decideEngagement({
    momentumPct: 0,
    liquidityUsd: 10_000_000,
    ageSec: 0,
    genome: SAFE_DEFAULT_GENOME,
    liveEnabled: false,
  });
  assert.equal(wouldEngage, false);
});

test("REQ-008 edge case: negative (bearish) momentumPct compared by magnitude, identical to the positive case", () => {
  const genome = SAFE_DEFAULT_GENOME;
  const pos = decideEngagement({ momentumPct: 3, liquidityUsd: 2_000_000, ageSec: 0, genome, liveEnabled: false });
  const neg = decideEngagement({ momentumPct: -3, liquidityUsd: 2_000_000, ageSec: 0, genome, liveEnabled: false });
  assert.equal(pos.wouldEngage, neg.wouldEngage);
  assert.equal(pos.conviction, neg.conviction);
});

test("PROP-008: NaN/Infinity momentumPct never yields wouldEngage=true (fail-closed)", () => {
  fc.assert(
    fc.property(
      fc.constantFrom(NaN, Infinity, -Infinity),
      fc.double({ min: 0, max: 5_000_000, noNaN: true }),
      (momentumPct, liquidityUsd) => {
        const { wouldEngage } = decideEngagement({
          momentumPct,
          liquidityUsd,
          ageSec: 0,
          genome: SAFE_DEFAULT_GENOME,
          liveEnabled: false,
        });
        assert.equal(wouldEngage, false);
      },
    ),
  );
});

test("PROP-008: NaN/Infinity liquidityUsd never yields wouldEngage=true (fail-closed)", () => {
  fc.assert(
    fc.property(
      fc.double({ min: -20, max: 20, noNaN: true }),
      fc.constantFrom(NaN, Infinity),
      (momentumPct, liquidityUsd) => {
        const { wouldEngage } = decideEngagement({
          momentumPct,
          liquidityUsd,
          ageSec: 0,
          genome: SAFE_DEFAULT_GENOME,
          liveEnabled: false,
        });
        assert.equal(wouldEngage, false);
      },
    ),
  );
});

test("REQ-008 edge case: non-numeric (string) momentumPct never yields wouldEngage=true", () => {
  const { wouldEngage } = decideEngagement({
    momentumPct: "not-a-number",
    liquidityUsd: 10_000_000,
    ageSec: 0,
    genome: SAFE_DEFAULT_GENOME,
    liveEnabled: false,
  });
  assert.equal(wouldEngage, false);
});

// --- PROP-009 (Tier 2, fast-check) -----------------------------------------------------------
test("PROP-009: liveEnabled=false -> engage always false regardless of wouldEngage (HARD dev-safety)", () => {
  fc.assert(
    fc.property(
      fc.double({ min: -20, max: 20, noNaN: true }),
      fc.double({ min: 0, max: 5_000_000, noNaN: true }),
      (momentumPct, liquidityUsd) => {
        const { engage } = decideEngagement({
          momentumPct,
          liquidityUsd,
          ageSec: 0,
          genome: SAFE_DEFAULT_GENOME,
          liveEnabled: false,
        });
        assert.equal(engage, false);
      },
    ),
  );
});

test("PROP-009: only liveEnabled===true AND wouldEngage===true AND not-stale together yield engage===true", () => {
  const genome = SAFE_DEFAULT_GENOME;
  const strong = decideEngagement({ momentumPct: 10, liquidityUsd: 5_000_000, ageSec: 0, genome, liveEnabled: true });
  assert.equal(strong.wouldEngage, true);
  assert.equal(strong.engage, true);

  const weak = decideEngagement({ momentumPct: 0.1, liquidityUsd: 100, ageSec: 0, genome, liveEnabled: true });
  assert.equal(weak.wouldEngage, false);
  assert.equal(weak.engage, false);

  const staleButStrong = decideEngagement({ momentumPct: 10, liquidityUsd: 5_000_000, ageSec: 99999, genome, liveEnabled: true });
  assert.equal(staleButStrong.engage, false, "staleness must defeat an otherwise-engaging signal");
});

test("isLiveEnabled: only exactly '1' is true; unset/'true'/'yes'/'0'/empty/whitespace are ALL false", () => {
  assert.equal(isLiveEnabled({}), false);
  assert.equal(isLiveEnabled({ SOL_GATE_LIVE_ENABLE: "1" }), true);
  for (const v of ["true", "yes", "0", "", "TRUE", " 1", "1 ", "01"]) {
    assert.equal(isLiveEnabled({ SOL_GATE_LIVE_ENABLE: v }), false, `"${v}" must be treated as unset (false)`);
  }
});

// --- PROP-007 ----------------------------------------------------------------------------------
test("PROP-007: fetchSolMarketSignal never throws; fresh success returns usdPrice/priceChange24h/liquidity", async () => {
  const fetchImpl = async () => ({
    ok: true,
    json: async () => ({
      So1111: { usdPrice: 79.03, priceChange24h: 2.66, liquidity: 668904234.36, createdAt: "2024-06-05T08:55:25.527Z" },
    }),
  });
  const cacheDir = tmpDir("sol-gate-cache-");
  const result = await fetchSolMarketSignal("So1111", { fetchImpl, cacheDir, maxStalenessSec: 300 });
  assert.equal(result.ok, true);
  assert.equal(result.source, "live");
  assert.equal(result.usdPrice, 79.03);
  assert.equal(result.priceChange24h, 2.66);
  assert.equal(result.liquidity, 668904234.36);
});

test("PROP-007: network error with no cache -> ok:false, never throws (cold start)", async () => {
  const fetchImpl = async () => {
    throw new Error("network down");
  };
  const cacheDir = tmpDir("sol-gate-cache-cold-");
  await assert.doesNotReject(fetchSolMarketSignal("Mint1", { fetchImpl, cacheDir, maxStalenessSec: 300 }));
  const result = await fetchSolMarketSignal("Mint1", { fetchImpl, cacheDir, maxStalenessSec: 300 });
  assert.equal(result.ok, false);
});

test("PROP-007: non-200 response falls back to a cache snapshot within the staleness bound", async () => {
  const cacheDir = tmpDir("sol-gate-cache-stale-");
  const mint = "Mint2";
  fs.writeFileSync(
    path.join(cacheDir, `${mint}.json`),
    JSON.stringify({ usdPrice: 1, priceChange24h: 1, liquidity: 2_000_000, fetchedAtMs: Date.now() - 10_000 }),
  );
  const fetchImpl = async () => ({ ok: false, status: 500, json: async () => ({}) });
  const result = await fetchSolMarketSignal(mint, { fetchImpl, cacheDir, maxStalenessSec: 300 });
  assert.equal(result.ok, true);
  assert.equal(result.source, "cache");
});

test("PROP-007: cache older than SOL_GATE_MAX_STALENESS_SEC -> no usable signal (skip, never a guessed value)", async () => {
  const cacheDir = tmpDir("sol-gate-cache-toostale-");
  const mint = "Mint3";
  fs.writeFileSync(
    path.join(cacheDir, `${mint}.json`),
    JSON.stringify({ usdPrice: 1, priceChange24h: 1, liquidity: 2_000_000, fetchedAtMs: Date.now() - 400_000 }),
  );
  const fetchImpl = async () => {
    throw new Error("down");
  };
  const result = await fetchSolMarketSignal(mint, { fetchImpl, cacheDir, maxStalenessSec: 300 });
  assert.equal(result.ok, false);
});

test("PROP-007: cold start (no cache at all) and a failing fetch -> skip, no crash, no fabricated signal", async () => {
  const cacheDir = tmpDir("sol-gate-cache-nocache-");
  const fetchImpl = async () => ({ ok: false, status: 503, json: async () => ({}) });
  const result = await fetchSolMarketSignal("NeverFetchedMint", { fetchImpl, cacheDir, maxStalenessSec: 300 });
  assert.equal(result.ok, false);
});

test("PROP-007: malformed JSON response (missing priceChange24h/liquidity) -> no usable signal", async () => {
  const cacheDir = tmpDir("sol-gate-cache-malformed-");
  const fetchImpl = async () => ({ ok: true, json: async () => ({ Mint4: { usdPrice: 5 } }) });
  const result = await fetchSolMarketSignal("Mint4", { fetchImpl, cacheDir, maxStalenessSec: 300 });
  assert.equal(result.ok, false);
});

test("PROP-007: NaN-shaped fields in the response -> no usable signal, never NaN silently accepted", async () => {
  const cacheDir = tmpDir("sol-gate-cache-nan-");
  const fetchImpl = async () => ({
    ok: true,
    json: async () => ({ Mint5x: { usdPrice: 5, priceChange24h: "not-a-number", liquidity: 2_000_000 } }),
  });
  const result = await fetchSolMarketSignal("Mint5x", { fetchImpl, cacheDir, maxStalenessSec: 300 });
  assert.equal(result.ok, false);
});

test("PROP-007: a fresh successful fetch is ALWAYS preferred over a cache snapshot, regardless of cache age", async () => {
  const cacheDir = tmpDir("sol-gate-cache-prefer-fresh-");
  const mint = "Mint6";
  fs.writeFileSync(
    path.join(cacheDir, `${mint}.json`),
    JSON.stringify({ usdPrice: 999, priceChange24h: 999, liquidity: 999, fetchedAtMs: Date.now() }),
  );
  const fetchImpl = async () => ({ ok: true, json: async () => ({ [mint]: { usdPrice: 1, priceChange24h: 1, liquidity: 3_000_000 } }) });
  const result = await fetchSolMarketSignal(mint, { fetchImpl, cacheDir, maxStalenessSec: 300 });
  assert.equal(result.source, "live");
  assert.equal(result.usdPrice, 1);
});

test("PROP-007: multiple mints are fetched/cached independently -- one mint's failure never blocks another", async () => {
  const cacheDir = tmpDir("sol-gate-cache-multi-");
  const fetchImpl = async (url) => {
    if (String(url).includes("BadMint")) throw new Error("down");
    return { ok: true, json: async () => ({ GoodMint: { usdPrice: 10, priceChange24h: 5, liquidity: 2_000_000 } }) };
  };
  const bad = await fetchSolMarketSignal("BadMint", { fetchImpl, cacheDir, maxStalenessSec: 300 });
  const good = await fetchSolMarketSignal("GoodMint", { fetchImpl, cacheDir, maxStalenessSec: 300 });
  assert.equal(bad.ok, false);
  assert.equal(good.ok, true);
});

test("NFR: default fetch timeout MUST NOT exceed 8 seconds", () => {
  assert.ok(DEFAULT_TIMEOUT_MS <= 8000);
});

// --- PROP-010 ------------------------------------------------------------------------------
test("PROP-010: describeSignal payload contains no action/side/size directive token, only observation fields", () => {
  const payload = describeSignal({ momentumPct: 3.5, liquidityUsd: 2_000_000, conviction: 8, mint: "So1111" });
  const serialized = JSON.stringify(payload);
  assert.doesNotMatch(serialized, /\b(buy|sell|long|short|swap now|execute)\b/i);
  assert.deepEqual(Object.keys(payload).sort(), [
    "observedConviction",
    "observedLiquidityUsd",
    "observedMint",
    "observedMomentumPct",
  ]);
});

test("PROP-010: describeSignal fields are fixed numeric/string OBSERVATION fields only (schema check)", () => {
  const payload = describeSignal({ momentumPct: -2.1, liquidityUsd: 1_500_000, conviction: 6.5, mint: "So1111" });
  assert.equal(typeof payload.observedMomentumPct, "number");
  assert.equal(typeof payload.observedLiquidityUsd, "number");
  assert.equal(typeof payload.observedConviction, "number");
  assert.equal(typeof payload.observedMint, "string");
});

test("PROP-010: fast-check -- describeSignal NEVER produces a directive token across randomized inputs", () => {
  fc.assert(
    fc.property(
      fc.double({ min: -50, max: 50, noNaN: true }),
      fc.double({ min: 0, max: 10_000_000, noNaN: true }),
      fc.double({ min: 0, max: 10, noNaN: true }),
      fc.constantFrom("So11111111111111111111111111111111111111112", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"),
      (momentumPct, liquidityUsd, conviction, mint) => {
        const payload = describeSignal({ momentumPct, liquidityUsd, conviction, mint });
        assert.doesNotMatch(JSON.stringify(payload), /\b(buy|sell|long|short|swap now|execute)\b/i);
      },
    ),
  );
});
