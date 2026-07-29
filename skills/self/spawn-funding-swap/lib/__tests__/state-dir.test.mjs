// state-dir.test.mjs — Phase-3 impl-review FIND-002 fix. bin/spawn-funding-swap.mjs's STATE_DIR
// previously had NO default (`process.env.SPAWN_FUNDING_SWAP_STATE_DIR` alone), so
// `createLedgerStore({stateDir: undefined})` would throw a raw, untested `path.join(undefined, ...)`
// TypeError the instant identity resolved in production -- violating REQ-008's "self-contained config"
// edge case. This file proves the fix: `resolveSwapStateDir` NEVER returns `undefined`, and handing its
// output straight to the REAL (non-fake) `createLedgerStore` from lib/ledger-store.mjs never throws --
// closing the exact defect class FIND-002 identified. Zero real network/RPC/signing clients are touched
// (Test-Money Safety Rule): `createLedgerStore` only computes a string synchronously at construction time,
// it does not perform disk I/O until `withLock`/`readState`/`writeState` are explicitly called, none of
// which this file calls.
import { test } from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { resolveSwapStateDir } from "../resolve-swap-state-dir.mjs";
import { createLedgerStore } from "../ledger-store.mjs";

test("REQ-008/FIND-002: resolveSwapStateDir returns a concrete, non-empty string when SPAWN_FUNDING_SWAP_STATE_DIR is unset (never undefined)", () => {
  const env = { HOME: "/home/life-manager" }; // no SPAWN_FUNDING_SWAP_STATE_DIR, no ANICCA_STATE_DIR
  const dir = resolveSwapStateDir({ env });
  assert.equal(typeof dir, "string");
  assert.ok(dir.length > 0);
});

test("REQ-008/FIND-002: the unset-env default is never /tmp-rooted (inherits resolveStateDir()'s own durable-state guard)", () => {
  const dir = resolveSwapStateDir({ env: { HOME: "/home/life-manager" } });
  assert.ok(!/^\/(private\/)?tmp(\/|$)/.test(dir), `default must never be /tmp-rooted, got "${dir}"`);
});

test("REQ-008/FIND-002: an explicitly set SPAWN_FUNDING_SWAP_STATE_DIR is still honored verbatim (override behavior unchanged)", () => {
  const dir = resolveSwapStateDir({
    env: { SPAWN_FUNDING_SWAP_STATE_DIR: "/home/life-manager/custom-swap-state" },
  });
  assert.equal(dir, "/home/life-manager/custom-swap-state");
});

test("REQ-008/FIND-002: unset SPAWN_FUNDING_SWAP_STATE_DIR resolves to a 'spawn-funding-swap' subdirectory of the shared colony state dir (reused convention, not invented)", () => {
  const dir = resolveSwapStateDir({ env: { HOME: "/home/life-manager" } });
  assert.equal(path.basename(dir), "spawn-funding-swap");
  assert.equal(path.basename(path.dirname(dir)), "state");
});

test("REQ-008/FIND-002: constructing the REAL createLedgerStore with the resolved default never throws -- the exact production crash site (ledger-store.mjs:37's path.join) is proven safe", () => {
  const stateDir = resolveSwapStateDir({ env: { HOME: "/home/life-manager" } });
  assert.doesNotThrow(() => {
    const store = createLedgerStore({ stateDir });
    assert.equal(typeof store.withLock, "function");
    assert.equal(typeof store.readState, "function");
    assert.equal(typeof store.writeState, "function");
  });
});

test("REQ-008/FIND-002 (regression documentation): the PRE-FIX shape -- createLedgerStore({stateDir: undefined}) -- is exactly the raw path.join(undefined, ...) TypeError this fix closes; production code must never construct it this way again", () => {
  assert.throws(
    () => createLedgerStore({ stateDir: undefined }),
    (err) => err instanceof TypeError,
    "createLedgerStore({stateDir: undefined}) must still throw a TypeError in isolation -- proving bin/spawn-funding-swap.mjs's fix (always passing a resolved default) is what actually closes FIND-002, not a change to ledger-store.mjs itself"
  );
});
