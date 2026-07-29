// VCSDD anicca-agent-spawn, Phase 5 (Formal Hardening) — proves PROP-105a/PROP-105c/PROP-105d/
// PROP-105f/PROP-105h against the real, git-tracked seed template
// `__REPO_ROOT__/skills/self/spawn/registry/citizens.seed.json` (created this session, closing a
// missing-deliverable gap: `specs/verification-architecture.md`'s own Purity Boundary Map declared
// this file as part of the sprint, but it did not exist in the tree until now).
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { isSelfFunded } from "../../../../_shared/lib/is-self-funded.mjs";

const SEED_PATH = new URL("../../registry/citizens.seed.json", import.meta.url);
const seed = JSON.parse(fs.readFileSync(SEED_PATH, "utf8"));

// PROP-105a: the seed template parses as an array of the documented shape (no telemetryPath field),
// and isSelfFunded() (unmodified) accepts any one record's {wallet, fuel, humanDependencies}
// sub-object -- never walletAddress, never coLocatedWithCoordinator -- without throwing.
test("PROP-105a: citizens.seed.json parses as an array of the documented shape, no telemetryPath field, isSelfFunded() never throws on any entry", () => {
  assert.ok(Array.isArray(seed));
  assert.equal(
    seed.length,
    1,
    "today's known-good seed is Franklin only -- automaton was removed per Dais's 2026-07-08 directive " +
      "(docs/loop-engineering/05-coordination-with-agent-economy.md §6): the economy consists of Franklins " +
      "only, and automaton is a self-made reproduction of the not-yet-GA github.com/Conway-Research/automaton, " +
      "not a genuine economic participant"
  );
  for (const entry of seed) {
    assert.equal(typeof entry.id, "string");
    assert.equal(typeof entry.wallet, "object");
    assert.equal(typeof entry.walletAddress, "object");
    assert.equal(typeof entry.fuel, "object");
    assert.ok(Array.isArray(entry.humanDependencies));
    assert.equal(typeof entry.homeDir, "string");
    assert.equal(typeof entry.coLocatedWithCoordinator, "boolean");
    assert.equal(entry.telemetryPath, undefined, "telemetryPath was removed, resolves FIND-302");
    assert.doesNotThrow(() => isSelfFunded({ wallet: entry.wallet, fuel: entry.fuel, humanDependencies: entry.humanDependencies }));
  }
});

// PROP-105c: citizens.seed.json's content, when each entry's {wallet, fuel, humanDependencies}
// sub-object is passed through isSelfFunded(), returns true for EVERY seeded entry -- a direct
// assertion against the literal seed fixture, not an out-of-band-knowledge-dependent comparison.
test("PROP-105c: isSelfFunded() returns true for every seeded entry's {wallet, fuel, humanDependencies}", () => {
  for (const entry of seed) {
    assert.equal(
      isSelfFunded({ wallet: entry.wallet, fuel: entry.fuel, humanDependencies: entry.humanDependencies }),
      true,
      `citizen "${entry.id}" must pass isSelfFunded()`
    );
  }
});

// PROP-105d: neither citizens.seed.json at bootstrap NOR the durable citizens.json at any later
// append ever contains an entry whose {wallet, fuel, humanDependencies} sub-object makes
// isSelfFunded() return false. Tier 0: structural check the seed array contains ONLY the two
// verified self-funded entries and excludes claude-p/any human-funded wallet.
test("PROP-105d: the seed array contains ONLY self-funded entries, excludes claude-p/any human-funded wallet", () => {
  const humanFundedClaudePWallet = "0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74"; // claude-p, human-funded (Anthropic subscription) -- see skills/economy/ubi/colony-wallets.json
  for (const entry of seed) {
    assert.equal(isSelfFunded({ wallet: entry.wallet, fuel: entry.fuel, humanDependencies: entry.humanDependencies }), true);
    const addresses = [entry.walletAddress?.evm, entry.walletAddress?.solana].filter(Boolean);
    assert.ok(!addresses.includes(humanFundedClaudePWallet), "claude-p's human-funded wallet must never appear in the self-funded seed");
  }
});

// PROP-105f: homeDir is present and non-empty on every seeded entry, and is consumed ONLY by
// REQ-403's audit -- never passed to isSelfFunded() (resolves FIND-202).
test("PROP-105f: homeDir is present and non-empty on every seeded entry, and is not among the keys isSelfFunded() reads", () => {
  for (const entry of seed) {
    assert.equal(typeof entry.homeDir, "string");
    assert.ok(entry.homeDir.length > 0);
  }
  // isSelfFunded's own documented input shape (per its own JSDoc) is {wallet, fuel, humanDependencies}
  // only -- passing homeDir alongside it must not change the result (proves it is never read).
  const withHomeDir = { wallet: { evm: true }, fuel: { provider: "x402" }, humanDependencies: [], homeDir: "/should/be/ignored" };
  const withoutHomeDir = { wallet: { evm: true }, fuel: { provider: "x402" }, humanDependencies: [] };
  assert.equal(isSelfFunded(withHomeDir), isSelfFunded(withoutHomeDir));
});

// PROP-105h: every seeded entry's coLocatedWithCoordinator field is present, boolean-typed, and
// true for today's sole seeded entry (Franklin -- genuinely co-located on the same Mac Mini today,
// REQ-106); no seed entry ever has this field false or missing.
test("PROP-105h: coLocatedWithCoordinator is present, boolean, and true for the seeded entry", () => {
  assert.deepEqual(
    seed.map((e) => e.coLocatedWithCoordinator),
    [true]
  );
});
