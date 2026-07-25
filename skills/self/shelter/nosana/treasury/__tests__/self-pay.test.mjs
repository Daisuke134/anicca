// node:test — self-pay.mjs: self-wallet classification (INV-7). Pure, no I/O.
import { test } from "node:test";
import assert from "node:assert/strict";
import { buildSelfWalletSet, isSelfWalletAddress, classifyRevenueRow, classifyRevenueRows } from "../self-pay.mjs";
import { SELF_WALLET_SET_EVM } from "../self-wallets-evm.mjs";

test("SELF_WALLET_SET_EVM is a real, non-empty copy of the sibling worktree's list", () => {
  assert.ok(SELF_WALLET_SET_EVM instanceof Set);
  assert.ok(SELF_WALLET_SET_EVM.size > 0);
  assert.ok(SELF_WALLET_SET_EVM.has("0x3eccad24794ca298d25378e9902a251322ea8749")); // franklin1, a real self-wallet
});

test("buildSelfWalletSet combines the EVM set with any Solana addresses given", () => {
  const set = buildSelfWalletSet({ solanaSelfWallets: ["F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T"] });
  assert.ok(set.evm.has("0x3eccad24794ca298d25378e9902a251322ea8749"));
  assert.ok(set.solana.has("F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T"));
});

test("buildSelfWalletSet defaults to an empty Solana set — honest, not a fabricated list", () => {
  const set = buildSelfWalletSet();
  assert.equal(set.solana.size, 0);
});

test("isSelfWalletAddress: EVM addresses match case-insensitively", () => {
  const set = buildSelfWalletSet();
  assert.equal(isSelfWalletAddress("0x3ECCAD24794CA298D25378E9902A251322EA8749", set), true);
  assert.equal(isSelfWalletAddress("0x0000000000000000000000000000000000dead", set), false);
});

test("isSelfWalletAddress: Solana addresses match case-sensitively (base58 is case-sensitive)", () => {
  const set = buildSelfWalletSet({ solanaSelfWallets: ["F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T"] });
  assert.equal(isSelfWalletAddress("F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T", set), true);
  // lower/upper-cased differently -> a DIFFERENT (wrong) account name in base58, must not match.
  assert.equal(isSelfWalletAddress("f5syuc4f5qulbegsyb1dfcbfi74anwe3zaxahqxwhz5t", set), false);
});

test("isSelfWalletAddress: never throws on missing/malformed input, defaults to false", () => {
  const set = buildSelfWalletSet();
  assert.equal(isSelfWalletAddress(undefined, set), false);
  assert.equal(isSelfWalletAddress("", set), false);
  assert.equal(isSelfWalletAddress("not-a-real-address", undefined), false);
});

test("classifyRevenueRow: a payment FROM a known self-wallet is excluded from revenue (INV-7)", () => {
  const set = buildSelfWalletSet();
  const row = classifyRevenueRow({ ts: 1, amountUsd: 5, from: "0x3eccad24794ca298d25378e9902a251322ea8749" }, set);
  assert.equal(row.external, false);
  assert.match(row.classification, /self-pay/);
});

test("classifyRevenueRow: a payment FROM an unknown address is external revenue", () => {
  const set = buildSelfWalletSet();
  const row = classifyRevenueRow({ ts: 1, amountUsd: 5, from: "0x000000000000000000000000000000deadbeef" }, set);
  assert.equal(row.external, true);
  assert.match(row.classification, /external/);
});

test("classifyRevenueRow: fail-closed on a missing from address — never counted as external", () => {
  const set = buildSelfWalletSet();
  const row = classifyRevenueRow({ ts: 1, amountUsd: 5 }, set);
  assert.equal(row.external, false);
  assert.match(row.classification, /fail-closed/);
});

test("classifyRevenueRow throws on a non-object row", () => {
  assert.throws(() => classifyRevenueRow(null, buildSelfWalletSet()), /row must be an object/);
});

test("classifyRevenueRows classifies every row and never mutates the input rows", () => {
  const set = buildSelfWalletSet();
  const rows = [
    { ts: 1, amountUsd: 1, from: "0x3eccad24794ca298d25378e9902a251322ea8749" },
    { ts: 2, amountUsd: 2, from: "0x000000000000000000000000000000deadbeef" },
  ];
  const classified = classifyRevenueRows(rows, set);
  assert.equal(classified[0].external, false);
  assert.equal(classified[1].external, true);
  assert.equal(rows[0].external, undefined); // original untouched
});

test("classifyRevenueRows: the real self-pay seed scenario — every inflow so far comes from the colony's own wallets", () => {
  // Ground truth 2026-07-25: external x402 revenue is $0; every inflow observed has been a self-pay
  // seed. This test proves the classifier produces exactly that verdict for a realistically-shaped
  // batch of rows all sourced from known self-wallets.
  const set = buildSelfWalletSet({ solanaSelfWallets: ["F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T"] });
  const rows = [
    { ts: 1, amountUsd: 0.70, from: "F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T" },
    { ts: 2, amountUsd: 0.02, from: "0x904b50d2e214da947d83d6a2d32c4e3ffc17eb74" },
  ];
  const classified = classifyRevenueRows(rows, set);
  assert.ok(classified.every((r) => r.external === false));
});
