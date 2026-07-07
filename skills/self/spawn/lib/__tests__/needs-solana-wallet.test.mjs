// VCSDD anicca-agent-spawn, Phase 2a (RED). REQ-202 needsSolanaWallet — pure conditional,
// bookkeeping only (never a model judgment). needs-solana-wallet.mjs does not exist yet —
// expected to fail at import time (module-not-found).
import { test } from "node:test";
import assert from "node:assert/strict";
import { needsSolanaWallet } from "../needs-solana-wallet.mjs";

test("PROP-202a: true when a Solana-settled skill (e.g. sol-trade) is present, regardless of deployTarget", () => {
  assert.equal(needsSolanaWallet({ initialSkills: ["sol-trade"], deployTarget: "akash" }), true);
});

test("PROP-202a: true when deployTarget is 'nosana', regardless of initialSkills", () => {
  assert.equal(needsSolanaWallet({ initialSkills: ["evm-only-skill"], deployTarget: "nosana" }), true);
});

test("PROP-202a: false when neither a Solana-settled skill NOR a Nosana deploy target is present", () => {
  assert.equal(needsSolanaWallet({ initialSkills: ["evm-only-skill"], deployTarget: "akash" }), false);
});

test("PROP-202a: false with an empty skill set and an Akash deploy target", () => {
  assert.equal(needsSolanaWallet({ initialSkills: [], deployTarget: "akash" }), false);
});

test("PROP-202a: both conditions true (Solana skill AND Nosana target) still returns true, no special-casing", () => {
  assert.equal(needsSolanaWallet({ initialSkills: ["sol-trade"], deployTarget: "nosana" }), true);
});
