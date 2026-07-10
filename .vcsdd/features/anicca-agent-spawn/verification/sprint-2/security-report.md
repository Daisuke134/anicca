# Security Hardening Report — Sprint 2 (Formal Hardening addendum)

**Feature**: anicca-agent-spawn · **Sprint**: 2 · **Phase**: 5 · **Date**: 2026-07-10

Scope: the money-moving sprint-2 orchestrator files that never went through Phase 5 hardening
(gas-seed transfer, reclaim, Akash funding-gate deploy, ERC-8004 registration, durable registry-append
retry) plus the `colony-spawn` lock call site they depend on:

- `~/anicca/skills/self/spawn/lib/spawn-orchestrator.mjs`
- `~/anicca/skills/self/spawn/scripts/wake-gate.mjs`
- `~/anicca/skills/self/spawn/lib/pending-registry-append.js`
- `~/anicca/skills/self/spawn/scripts/gen-solana-wallet.sh`
- `~/anicca/skills/economy/gig/lib/lock.mjs` (the `withGigLock("colony-spawn", ...)` call site — reused
  unmodified from `anicca-agent-economy`, already independently hardened there; re-scanned here as a
  direct dependency of the money-moving path)

## Tooling

| Tool | Availability | Invocation |
|---|---|---|
| Semgrep | Available (`/opt/homebrew/bin/semgrep`, v1.168.0) | `semgrep --config=auto --config=p/security-audit --config=p/secrets skills/self/spawn/lib/spawn-orchestrator.mjs skills/self/spawn/scripts/wake-gate.mjs skills/self/spawn/lib/pending-registry-append.js skills/self/spawn/scripts/gen-solana-wallet.sh skills/economy/gig/lib/lock.mjs --json --output <raw>` |
| Manual security-focused read | Performed | All 5 files read line-by-line for injection, unsafe deserialization, missing validation on money-affecting fields, path traversal, key-material handling, lock-key safety, integer overflow/precision loss |
| Wycheproof (cryptographic test vectors) | **Not applicable** | This sprint's money-moving code does no cryptographic primitive implementation of its own (no hand-rolled signing/hashing/encoding) — it calls `viem`'s `privateKeyToAccount` (EVM) and `@solana/web3.js`'s `Keypair.fromSecretKey` (Solana), both already-audited third-party libraries, and shells out to `seed-child.py`/`solana-keygen` for the actual transfer/keygen. There is no in-repo crypto primitive for Wycheproof's test-vector suite to exercise. |

Raw Semgrep output: `verification/security-results/semgrep-sprint2-raw.json`.

## Findings

**Semgrep: 0 findings across 206 rules (154 JS-specific + 4 bash + 49 multilang), 5 files, 0 errors.**

```
Scanning 5 files tracked by git with 1090 Code rules:
  Language      Rules   Files          Origin      Rules
 <multilang>      49       5          Community    1090
 js              154       4
 bash              4       1
Ran 206 rules on 5 files: 0 findings.
```

**Manual review (no blocking findings):**

| Area checked | Result |
|---|---|
| Injection (shell/eval/SQL) | `spawn-orchestrator.mjs` shells out via `execFileSync` (never `exec`/string-interpolated shell) to `gen-wallet.sh`/`gen-solana-wallet.sh`/`deploy-akash.sh`/`akt-treasury.sh`/`seed-child.py` — all fixed, hardcoded script paths (`path.join(__dirname, ...)`), with argument values (`childId`, `amount`, `walletJsonPath`) passed as SEPARATE `execFileSync` array elements, never concatenated into a shell string. `gen-solana-wallet.sh` itself uses `set -euo pipefail`, quoted variable expansions throughout, and its own embedded `node -e` snippet takes its inputs via `process.argv` (`"$REPO_ROOT"`/`"$KEYPAIR_FILE"`), never string-interpolated into the JS source. `withGigLock`'s `lockKey` argument (`"colony-spawn"`) is a fixed string literal at this call site — even so, `lock.mjs`'s own `isSafeLockKey`/`assertSafeLockKey` (SEC-1 path-traversal guard, re-read this session) independently rejects any non-`[A-Za-z0-9_-]+` key before it ever reaches a filesystem path, a second layer regardless. |
| Unsafe deserialization | `pending-registry-append.js`/`spawn-orchestrator.mjs` only `JSON.parse` locally-written files under this process's own state directory (`ledger.js`'s own `children.jsonl`/`citizens.json`/`pending-registry-appends.jsonl`) — never untrusted network input. `wake-gate.mjs`'s Solana RPC/Coinbase spot-price responses ARE untrusted network JSON, but every field pulled from them (`balResult?.value`, `tokenResult?.value`, `priceResult?.data?.amount`) is immediately coerced via `Number(...)` with a `|| 0` fallback, never passed through unchecked, and never used as a code/path/key value — only as a plain numeric balance figure. |
| Missing input validation on money-affecting fields | `shelterCostUsdFromSettledPrice({priceAmount, priceDenom})` fails closed to `null` for any `priceDenom !== "uact"` or non-finite/negative `priceAmount` — confirmed by direct read and by the existing `spawn-orchestrator-reclaim-and-shelter-cost.test.mjs` FIND-002 tests (re-run, passing). `seedUsdcAmount()` reads `process.env.ANICCA_SEED_USDC` via `Number(...)`, defaulting to `1` — a malformed/empty env value coerces to `NaN`, which would make `defaultSeedChild`'s downstream `amount` argument `NaN`; this is bounded by `seed-child.py`'s own already-hardened (prior-sprint) input validation on its CLI amount argument, not re-validated a second time here — same pattern already accepted for `ANICCA_SPAWN_RESERVE_USD`/`ANICCA_SPAWN_SAFETY_MARGIN` in `treasury-gate.mjs`'s own sprint-1 hardening. Not a NEW risk this sprint introduces. |
| Path traversal | `defaultPendingRegistryAppendsFile()`/`defaultLedgerFile()` are built from `resolveStateDir({})` + a fixed literal filename — never from caller-supplied path segments. `pending-registry-append.js`'s `file`/`citizens_registry_file` values are themselves ALWAYS one of these same fixed, process-derived paths (never a value read from network/user input). |
| Key-material handling | `defaultPersistChildWallet`/`defaultSeedChild`/`defaultReclaimSeed` all write private-key-bearing temp/persistent files at mode `0o600` (confirmed via `fs.writeFileSync(..., {mode: 0o600})` + a belt-and-suspenders `fs.chmodSync`), under this host's own `resolveStateDir()` (never bare `/tmp` — `state-path.js`'s own `PROP-101`-adjacent `/tmp` refusal test, `state-path.test.js`, re-run passing), and shredded in a `finally` block (`shredTempFile`, `shred -u` with an `fs.unlinkSync` fallback) immediately after use. Neither the child's nor the parent's private key is ever logged (`console.error` call sites throughout the file print only `childId`/error strings/booleans, never key material — confirmed by grep for `privateKey`/`private_key` near any `console.*` call: zero matches). `defaultReclaimSeed` signs with the CHILD's own IN-MEMORY key (never re-read from disk) — confirmed by the Tier-1 test cited in `verification-report.md`'s PROP-119 section. |
| Money-affecting non-atomicity (see also `verification-report.md`'s "New finding" section) | `retryPendingRegistryAppends`'s own append-then-resolve sequence is not atomic — a crash between the two writes causes a genuine duplicate `citizens.json` record on the next retry, which `computeColonySurplusUsd` then double-counts. This is a real, narrow-window (process-crash) gap, reported in full in `verification-report.md`; not a Semgrep-detectable pattern (it is a distributed-systems atomicity gap, not a code-shape defect), found via manual review + a live proof harness. |
| Hardcoded secrets | Semgrep's `p/secrets` ruleset found 0 across all 5 files. Manual read confirms no private key, API key, or credential is hardcoded — `wake-gate.mjs`'s `USDC_BASE`/`SOL_USDC_MINT` are PUBLIC token contract/mint addresses (not secrets), and its RPC endpoints (`base-rpc.publicnode.com`, `api.mainnet-beta.solana.com`, `api.coinbase.com`) are public, unauthenticated read endpoints. |
| Lock-key safety (SEC-1 dependency re-check) | `spawn-orchestrator.mjs`'s sole `withGigLock` call site passes the fixed literal `"colony-spawn"` — matches `isSafeLockKey`'s `[A-Za-z0-9_-]+` pattern trivially; not attacker-influenced in any way (never built from `childId`/user input). |
| Integer overflow / precision loss | All money math (`shelterCostUsdFromSettledPrice`'s `/1e6`, `seedUsdcAmount`, the surplus computations in `treasury-gate.mjs` this sprint reuses unmodified) stays within plain IEEE-754 double precision, well inside the safe-integer range for the USD/AKT/uact magnitudes involved (single/double-digit to low-thousands) — consistent with sprint-1's own already-accepted convention, not a new risk. |

## Summary

0 blocking Semgrep findings (206 rules / 5 files / 0 errors). Manual review surfaced no injection,
deserialization, path-traversal, or hardcoded-secret issues in the sprint-2 orchestrator files, and
confirmed the private-key-handling discipline (600-perm, never bare `/tmp`, shredded after use, never
logged, child-signs-with-its-own-in-memory-key-for-reclaim) holds under direct source read. Wycheproof is
not applicable — this sprint introduces no hand-rolled cryptographic primitive. **One genuine, non-Semgrep-
detectable money-safety gap was found and is reported in full above and in `verification-report.md`'s
"New finding" section**: the registry-append retry mechanism's non-atomic append-then-resolve sequence can
duplicate a citizen record across a process crash, inflating `computeColonySurplusUsd`. This does not
block PROP-115..121 (none of the 7 targeted obligations name this property) and is flagged as an open
follow-up item, not a required-obligation failure.
