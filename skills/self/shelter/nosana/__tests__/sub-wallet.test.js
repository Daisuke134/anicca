// node:test — sub-wallet: the S8 on-chain spend cap. Because nosana-jobs' `list` constrains the
// NOS source to the payer's OWN ATA (delegate path is structurally impossible — see the S8 plan),
// the cap is enforced by balance: a sub-wallet holds at most cap NOS + cap SOL, and only ITS
// secret ever leaves the Mac. These tests cover the pure funding gate, keypair file handling,
// and load-or-create idempotency — all offline, throwaway keys only.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  evaluateFundingGate,
  materializeSubWalletFile,
  ensureSubWallet,
  DEFAULT_NOS_CAP,
  DEFAULT_SOL_CAP,
} from "../sub-wallet.mjs";

test("default NOS cap can fund one fixed escrow while preserving the move-out reserve", () => {
  assert.equal(DEFAULT_NOS_CAP, 0.75);
  assert.ok(DEFAULT_NOS_CAP >= 0.3456 + 0.34);
});

const BASE = {
  requestNos: 0.2,
  requestSol: 0.004,
  subNosBalance: 0,
  subSolBalance: 0,
  ownerNosBalance: 2.4,
  ownerSolBalance: 0.02,
};

test("funding gate: happy path within caps and floors", () => {
  const verdict = evaluateFundingGate(BASE);
  assert.equal(verdict.allowed, true, verdict.reason);
});

test("funding gate: refuses non-positive and non-finite requests", () => {
  for (const bad of [{ requestNos: 0, requestSol: 0 }, { requestNos: -1 }, { requestNos: NaN }, { requestSol: Infinity }]) {
    const verdict = evaluateFundingGate({ ...BASE, ...bad });
    assert.equal(verdict.allowed, false);
  }
});

test("funding gate: refuses when sub-wallet would exceed NOS cap (existing balance counts)", () => {
  const verdict = evaluateFundingGate({ ...BASE, subNosBalance: 0.65, requestNos: 0.2 });
  assert.equal(verdict.allowed, false);
  assert.match(verdict.reason, /NOS cap/);
});

test("funding gate: refuses when sub-wallet would exceed SOL cap", () => {
  const verdict = evaluateFundingGate({ ...BASE, subSolBalance: 0.004, requestSol: 0.003 });
  assert.equal(verdict.allowed, false);
  assert.match(verdict.reason, /SOL cap/);
});

test("funding gate: refuses when owner would drop below SOL fee floor", () => {
  const verdict = evaluateFundingGate({ ...BASE, ownerSolBalance: 0.006, requestSol: 0.004 });
  assert.equal(verdict.allowed, false);
  assert.match(verdict.reason, /floor/);
});

test("funding gate: refuses when owner lacks the NOS being sent", () => {
  const verdict = evaluateFundingGate({ ...BASE, ownerNosBalance: 0.1, requestNos: 0.2 });
  assert.equal(verdict.allowed, false);
});

test("funding gate: custom caps via config override defaults", () => {
  const verdict = evaluateFundingGate({ ...BASE, requestNos: 0.9, config: { nosCap: 1.0, solCap: DEFAULT_SOL_CAP } });
  assert.equal(verdict.allowed, true, verdict.reason);
  assert.equal(evaluateFundingGate({ ...BASE, requestNos: 0.9 }).allowed, false); // default 0.75 cap refuses the same request
});

test("materializeSubWalletFile: 0600 file in 0700 dir", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "subw-"));
  const p = path.join(dir, "inner", "sub_key.json");
  materializeSubWalletFile({ secretBytes: new Uint8Array(64).fill(7), subWalletPath: p });
  assert.equal(fs.statSync(p).mode & 0o777, 0o600);
  assert.equal(fs.statSync(path.dirname(p)).mode & 0o777, 0o700);
  assert.equal(JSON.parse(fs.readFileSync(p, "utf8")).length, 64);
});

test("ensureSubWallet: creates once, then loads the SAME key (idempotent)", () => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), "subw-home-"));
  const first = ensureSubWallet({ env: {}, home });
  assert.equal(first.created, true);
  assert.equal(typeof first.address, "string");
  const second = ensureSubWallet({ env: {}, home });
  assert.equal(second.created, false);
  assert.equal(second.address, first.address); // never silently rotates the cloud identity
  assert.equal(fs.statSync(first.keypairPath).mode & 0o777, 0o600);
});

// S12: USDC leg — Franklin's cloud identity needs capped USDC for BlockRun x402 calls.
test("funding gate: USDC leg capped like the others", () => {
  const ok = evaluateFundingGate({ ...BASE, requestUsdc: 0.025, ownerUsdcBalance: 0.0317 });
  assert.equal(ok.allowed, true, ok.reason);
  assert.equal(ok.usdc, 0.025);
  const overCap = evaluateFundingGate({ ...BASE, requestUsdc: 0.02, subUsdcBalance: 0.02, ownerUsdcBalance: 0.05 });
  assert.equal(overCap.allowed, false);
  assert.match(overCap.reason, /USDC cap/);
  const insufficientOwner = evaluateFundingGate({ ...BASE, requestUsdc: 0.05, ownerUsdcBalance: 0.03 });
  assert.equal(insufficientOwner.allowed, false);
});

test("funding gate: USDC-only request is a valid request", () => {
  const verdict = evaluateFundingGate({ ...BASE, requestNos: 0, requestSol: 0, requestUsdc: 0.01, ownerUsdcBalance: 0.03 });
  assert.equal(verdict.allowed, true, verdict.reason);
});

test("an over-cap balance in one asset does not block funding a different asset", () => {
  // Live 2026-07-27: the sub-wallet held 0.026 SOL against a 0.005 cap because Nosana escrow
  // refunds paid it back. That froze a NOS-only top-up and left the agent unable to rent.
  const gate = evaluateFundingGate({
    requestNos: 0.47,
    subNosBalance: 0.0267,
    subSolBalance: 0.0261,
    ownerNosBalance: 0.607,
    ownerSolBalance: 0.0079,
  });
  assert.equal(gate.allowed, true);
  assert.match(gate.warning, /SOL/);
});

test("the cap still bites for the asset actually being funded", () => {
  const gate = evaluateFundingGate({
    requestSol: 0.5,
    subSolBalance: 0,
    ownerNosBalance: 10,
    ownerSolBalance: 10,
  });
  assert.equal(gate.allowed, false);
  assert.match(gate.reason, /SOL cap/);
});
