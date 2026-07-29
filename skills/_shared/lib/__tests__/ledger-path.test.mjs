// node:test — ledger-uniqueness (REQ-001/002/004/005): canonical earn-ledger path resolution
// and wallet-based row filtering, both pure, both read-only. RED phase: resolveEarnLedgerPath
// and filterOwnWalletRows do not exist yet on ../ledger.mjs — every test below is EXPECTED TO
// FAIL (import throws, or the destructured binding is undefined and calling it throws) until
// Phase 2b implements REQ-001/002. Kept in a SEPARATE new file (verification-architecture.md
// lists this exact path as NEW) so the pre-existing ledger.test.js/ledger.test.mjs (EVM/Solana/
// Hyperliquid coverage) are left completely untouched.
//
// Covers verification-architecture.md PROP-LU-001..006, PROP-LU-010.
import { test } from "node:test";
import assert from "node:assert/strict";
import fc from "fast-check";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  resolveEarnLedgerPath,
  filterOwnWalletRows,
} from "../ledger.mjs";

// SHARED wallets pinned in skills/self/founder-loop/record-earn.mjs:39 — the exact
// contamination class found live in .anicca-founder/skills/earn/state/earn-ledger.jsonl
// (155 rows wallet=0xa3cdd4..., additional rows wallet=0xb9dd3b67...).
const AUTOMATON_PRE_ROTATION = "0xa3cdd4ec6b94f01826aaf90a6d5538a2aa8c4c21";
const AUTOMATON_POST_ROTATION = "0xb9dd3b67921b354c656523d6851537988f31dd56";
const FOUNDER_WALLET = "0x810f6d61f7606deee2657d3083e150a222bc29c5";

// --- PROP-LU-001 (REQ-001.1): explicit home wins ---

test("resolveEarnLedgerPath({ home }) returns <home>/skills/earn/state/earn-ledger.jsonl", () => {
  const r = resolveEarnLedgerPath({ home: "/tmp/instX" });
  assert.equal(r.path, path.join("/tmp/instX", "skills", "earn", "state", "earn-ledger.jsonl"));
  assert.equal(r.resolved, true);
  assert.equal(r.resolutionSource, "anicca_home_env");
});

test("resolveEarnLedgerPath({ env: { ANICCA_HOME } }) honors env when home is omitted", () => {
  const r = resolveEarnLedgerPath({ env: { ANICCA_HOME: "/tmp/instY" } });
  assert.equal(r.path, path.join("/tmp/instY", "skills", "earn", "state", "earn-ledger.jsonl"));
  assert.equal(r.resolutionSource, "anicca_home_env");
});

test("resolveEarnLedgerPath property: any non-empty string home always yields <home>/skills/earn/state/earn-ledger.jsonl", () => {
  fc.assert(
    fc.property(fc.string({ minLength: 1 }).filter((s) => s.trim().length > 0), (home) => {
      const r = resolveEarnLedgerPath({ home });
      assert.equal(r.path, path.join(home, "skills", "earn", "state", "earn-ledger.jsonl"));
      assert.equal(r.resolved, true);
      assert.equal(r.resolutionSource, "anicca_home_env");
    })
  );
});

// --- PROP-LU-002 (REQ-001.2): file-relative fallback branch ---

test("resolveEarnLedgerPath({ env: {} }) falls back to a module-relative path ending in earn/state/earn-ledger.jsonl", () => {
  const r = resolveEarnLedgerPath({ env: {} });
  assert.equal(r.resolved, true);
  assert.equal(r.resolutionSource, "file_relative_default");
  assert.ok(r.path.endsWith(path.join("earn", "state", "earn-ledger.jsonl")));

  // Independently derived (not by calling the module's own internals): ledger.mjs lives at
  // skills/_shared/lib/ledger.mjs; this TEST file lives at skills/_shared/lib/__tests__/*.mjs
  // — one directory deeper — so climbing from THIS file one extra level reaches the same
  // skills/_shared/lib directory ledger.mjs itself resolves __dirname to.
  const thisTestDir = path.dirname(fileURLToPath(import.meta.url));
  const libDir = path.dirname(thisTestDir); // skills/_shared/lib
  const sharedDir = path.dirname(libDir); // skills/_shared
  const skillsDir = path.dirname(sharedDir); // skills
  const expected = path.join(skillsDir, "earn", "state", "earn-ledger.jsonl");
  assert.equal(r.path, expected);
});

test("resolveEarnLedgerPath({ home: '' }) treats empty string as absent and falls back to branch 2", () => {
  const r = resolveEarnLedgerPath({ home: "", env: {} });
  assert.equal(r.resolutionSource, "file_relative_default");
});

// --- PROP-LU-003 (REQ-001, INV: cross-instance path uniqueness) ---

test("resolveEarnLedgerPath property: two distinct non-empty home values never resolve to the same path", () => {
  fc.assert(
    fc.property(
      fc.string({ minLength: 1 }).filter((s) => s.trim().length > 0),
      fc.string({ minLength: 1 }).filter((s) => s.trim().length > 0),
      (a, b) => {
        fc.pre(a !== b);
        const pa = resolveEarnLedgerPath({ home: a }).path;
        const pb = resolveEarnLedgerPath({ home: b }).path;
        assert.notEqual(pa, pb);
      }
    )
  );
});

test("resolveEarnLedgerPath resolves fresh per call, never a frozen constant (two calls, two homes, two answers)", () => {
  const r1 = resolveEarnLedgerPath({ home: "/tmp/freshA" });
  const r2 = resolveEarnLedgerPath({ home: "/tmp/freshB" });
  assert.notEqual(r1.path, r2.path);
});

// --- PROP-LU-004/005 (REQ-002): wallet-based allow-list filter ---

test("filterOwnWalletRows: keeps own-wallet rows, excludes foreign-wallet rows, keeps walletless rows", () => {
  const rows = [
    { ts: 1, wallet: FOUNDER_WALLET, net_usdc: 5 },
    { ts: 2, wallet: AUTOMATON_PRE_ROTATION, net_usdc: 100 },
    { ts: 3, wallet: AUTOMATON_POST_ROTATION, net_usdc: 100 },
    { ts: 4, source: "cook", net_usdc: 0 }, // no wallet key at all (narrate row)
  ];
  const kept = filterOwnWalletRows(rows, FOUNDER_WALLET);
  assert.deepEqual(kept.map((r) => r.ts), [1, 4]);
});

test("filterOwnWalletRows: case-insensitive wallet match", () => {
  const rows = [{ ts: 1, wallet: FOUNDER_WALLET.toUpperCase() }];
  const kept = filterOwnWalletRows(rows, FOUNDER_WALLET.toLowerCase());
  assert.equal(kept.length, 1);
});

test("filterOwnWalletRows: ownWallets omitted excludes every walleted row, keeps every walletless row", () => {
  const rows = [{ ts: 1, wallet: FOUNDER_WALLET }, { ts: 2 }];
  const kept = filterOwnWalletRows(rows);
  assert.deepEqual(kept.map((r) => r.ts), [2]);
});

test("filterOwnWalletRows: ownWallets accepts an array of multiple own wallets", () => {
  const rows = [
    { ts: 1, wallet: FOUNDER_WALLET },
    { ts: 2, wallet: "0xSecondOwnWallet" },
    { ts: 3, wallet: AUTOMATON_PRE_ROTATION },
  ];
  const kept = filterOwnWalletRows(rows, [FOUNDER_WALLET, "0xSecondOwnWallet"]);
  assert.deepEqual(kept.map((r) => r.ts), [1, 2]);
});

test("filterOwnWalletRows: [] rows -> []", () => {
  assert.deepEqual(filterOwnWalletRows([], FOUNDER_WALLET), []);
});

test("filterOwnWalletRows property: every surviving walleted row's wallet (lower-cased) is in ownWallets (lower-cased)", () => {
  fc.assert(
    fc.property(
      fc.array(
        fc.record({
          ts: fc.integer(),
          wallet: fc.option(fc.constantFrom(FOUNDER_WALLET, AUTOMATON_PRE_ROTATION, AUTOMATON_POST_ROTATION), { nil: undefined }),
        })
      ),
      (rows) => {
        const kept = filterOwnWalletRows(rows, FOUNDER_WALLET);
        for (const row of kept) {
          if (row.wallet !== undefined) {
            assert.equal(row.wallet.toLowerCase(), FOUNDER_WALLET.toLowerCase());
          }
        }
      }
    )
  );
});

test("filterOwnWalletRows property: every row with no wallet key is preserved, order-stable", () => {
  fc.assert(
    fc.property(
      fc.array(fc.record({ ts: fc.integer(), tag: fc.constant("walletless") })),
      (rows) => {
        const kept = filterOwnWalletRows(rows, FOUNDER_WALLET);
        assert.deepEqual(kept, rows);
      }
    )
  );
});

// --- PROP-LU-006 (REQ-004): immutability ---

test("filterOwnWalletRows never mutates the input array or its row objects", () => {
  const rows = [{ ts: 1, wallet: FOUNDER_WALLET }, { ts: 2, wallet: AUTOMATON_PRE_ROTATION }];
  const snapshot = JSON.parse(JSON.stringify(rows));
  const result = filterOwnWalletRows(rows, FOUNDER_WALLET);
  assert.deepEqual(rows, snapshot, "input array must be byte-for-byte unchanged");
  assert.notEqual(result, rows, "must return a NEW array, not the same reference");
});

// --- PROP-LU-010 (REQ-004): neither new function ever touches a write/delete file API ---

test("resolveEarnLedgerPath source contains no write/delete file API call", () => {
  const src = resolveEarnLedgerPath.toString();
  assert.doesNotMatch(src, /writeFile|appendFile|fs\.rm\b|unlink|rename/);
});

test("filterOwnWalletRows source contains no write/delete file API call", () => {
  const src = filterOwnWalletRows.toString();
  assert.doesNotMatch(src, /writeFile|appendFile|fs\.rm\b|unlink|rename/);
});

// --- REQ-004 acceptance: read-only on a real-shaped fixture copy (never the live prod path) ---

test("filterOwnWalletRows applied to rows parsed from a fixture ledger never mutates the fixture file", async () => {
  const { promises: fs } = await import("node:fs");
  const os = await import("node:os");
  const { readLedger, deriveLine, appendLedger } = await import("../ledger.mjs");

  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "ledger-uniqueness-fixture-"));
  const fixture = path.join(dir, "earn-ledger.jsonl");
  // Shape mirrors the real contaminated file: own-wallet rows + foreign (SHARED-list) wallet
  // rows + walletless narrate rows — built here, NEVER read from /home/life-manager/.anicca-founder.
  await appendLedger(fixture, deriveLine({ wallet: FOUNDER_WALLET, source: "x402-serve", task: "up", earn_usdc: 0, cost_usdc: 0, wake: "w1" }));
  await appendLedger(fixture, deriveLine({ wallet: AUTOMATON_PRE_ROTATION, source: "hl-trade", task: "hl-close ETH", earn_usdc: 0.0006, cost_usdc: 0, wake: "w2" }));
  await appendLedger(fixture, deriveLine({ source: "cook", task: "explore", earn_usdc: 0, cost_usdc: 0, wake: "w3" }));

  const before = await fs.stat(fixture);
  const rows = await readLedger(fixture);
  filterOwnWalletRows(rows, FOUNDER_WALLET);
  const after = await fs.stat(fixture);

  assert.equal(before.size, after.size, "fixture file size must be unchanged");
  assert.equal(before.mtimeMs, after.mtimeMs, "fixture file mtime must be unchanged (never opened for writing)");
});
