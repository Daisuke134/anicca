# Sprint-6 Spec — Multi-chain support (Solana + Base), lean

Dais correction (2026-07-04, verbatim intent): "money is money" — the Tokyo GAIN event and the
CoralOS submission must NOT be Base/USDC-only. Japanese participants overwhelmingly prefer Solana
wallets over an EVM/USDC flow, and the CoralOS bounty itself settles on Solana devnet. Excluding
Solana from the leaderboard would silently disqualify the exact audience the Tokyo event is for.
This sprint makes GAIN scoring (sprint-5) and the no-fake enrichment engine (sprint-1/3)
chain-agnostic: `chain: 'base' | 'solana'` per instance, both verified the same way — real signed
heartbeat + real on-chain read, never a trusted client-reported number.

## Ground truth (re-verified from disk, this round)

- **`telemetry-schema.js:5`** hard-locks `id` to `/^0x[a-fA-F0-9]{40}$/` — a Solana base58 address
  (e.g. `AJ99EemzNHpkdjpMJ9aXfLthvfQYkjSXUjYrQr3853MN`, 32-44 chars, mixed-case, no `0x` prefix)
  is REJECTED at the schema gate before it ever reaches signature verification. This is the #1
  blocker: right now a Solana instance's heartbeat is a 400 before anything else runs.
- **`telemetry-verify.js:1,34-35`** uses `ethers.verifyMessage` (secp256k1 / EIP-191 recovery) and
  compares `signer.toLowerCase() !== p.id.toLowerCase()`. Two problems for Solana: (a) `verifyMessage`
  cannot recover/verify an ed25519 signature at all — Solana wallets sign with ed25519
  (`nacl.sign.detached` / `Keypair.sign`), not secp256k1; (b) **`.toLowerCase()` is actively
  WRONG for base58** — base58 is case-sensitive (mixed-case IS the address; lowercasing a Solana
  pubkey produces a different, likely-invalid, string). Both must become chain-aware branches, not
  a shared code path.
- **`spawn-register.js:5,11-13`** hardcodes `ethers.Wallet` + `wallet.signMessage`. A Solana
  instance has no `ethers.Wallet` — it holds a `@solana/web3.js` `Keypair` (or a raw 64-byte
  secret key). Needs a `chain` parameter that selects the signer.
- **`chain-reader.js`** (`makeBaseReader`) is entirely EVM: `ethers.JsonRpcProvider`, ERC-20
  `balanceOf`/`Transfer` events, Coinbase ETH-USD spot price. Solana has no equivalent shape —
  needs a **separate** `makeSolanaReader` using `@solana/web3.js` (`Connection.getBalance` for
  native SOL, `getParsedTokenAccountsByOwner` for an SPL-USDC balance, `getSignaturesForAddress` +
  `getParsedTransaction` for inflow detection) and a SOL-USD price source (Coinbase spot works the
  same way, different pair: `SOL-USD`).
- **`leaderboard-constants.js`** (`OUR_INSTANCE_IDS`, `SEED_ADDRESSES`, `excludeSet`) currently
  stores/compares addresses assuming EVM lowercase-hex normalization throughout
  (`enrich.js`'s `externalInflowsUsd(a, ts, exSet)` calls `exSet.has(x.from)` where `x.from` is
  already lowercased by `chain-reader.js:36`). A Solana version of `excludeSet` must NOT lowercase.
- **`enrich.js`** picks ONE reader (Base) unconditionally for every row. Needs to dispatch per-row
  on `payload.chain` to the matching reader instance (both readers can be constructed once, at
  request-scope, same as today — just keyed by chain).
- **CoralOS submission (spec `2026-07-04-coralos-submission-clawrouter-zero-human.md`, A9 entry)**
  already proved a real, working Solana build+deploy path (`anchor build && anchor deploy
  --provider.cluster localnet`, real tx sigs, `Executable: true`) — this sprint's `makeSolanaReader`
  should default to the SAME devnet RPC (`https://api.devnet.solana.com`, overridable via
  `SOLANA_RPC_URL`) for hackathon-week testing, with `SOLANA_NETWORK=mainnet-beta` promotable for
  the real Tokyo event GAIN window (real money, real GAIN, per sprint-5's own "no fake" mandate).

## Requirements (EARS)

- **S6.1 (schema accepts both chains)** `telemetry-schema.js`'s `validate()` SHALL accept an
  optional `chain` field (`'base' | 'solana'`, default `'base'` when absent — back-compat with
  every existing Base row). WHEN `chain === 'solana'`, `id` SHALL be validated against Solana's
  base58 address shape (32-44 chars, base58 alphabet, i.e. NOT `0`, `O`, `I`, `l`) instead of the
  `0x...` regex. WHEN `chain === 'base'` (or absent), the existing `0x` regex applies unchanged.
- **S6.2 (chain-aware, case-preserving verification)** `telemetry-verify.js`'s `verifyTelemetry`
  SHALL branch on `payload.chain`: `'base'` (default) keeps the exact current
  `ethers.verifyMessage` + `.toLowerCase()` path (regression-safe); `'solana'` SHALL verify via
  ed25519 (`tweetnacl` `nacl.sign.detached.verify(messageBytes, signatureBytes, bs58.decode(id))`)
  and compare `signer === p.id` **without** case-folding (base58 is case-sensitive).
- **S6.3 (chain-aware signing)** `registerSpawn` (`spawn-register.js`) SHALL accept `chain` in its
  args (default `'base'`) and branch its signer: `'base'` keeps `ethers.Wallet.signMessage`
  unchanged; `'solana'` SHALL sign via `nacl.sign.detached(messageBytes, secretKey)` from a
  `@solana/web3.js` `Keypair`, base58-encoding the signature for transport (`bs58.encode(sig)`),
  and the signer==id check SHALL use the same case-sensitive comparison as S6.2.
- **S6.4 (Solana on-chain reader)** A new `makeSolanaReader(ids, opts)` in `chain-reader.js` (or a
  sibling file `chain-reader-solana.js`, builder's call at GREEN time) SHALL expose the SAME
  accessor shape as `makeBaseReader` (`{ usdPrice, nativeBalance, usdcBalance, externalInflowsUsd
  }` — exact accessor names reconciled with `enrich.js`'s call sites at GREEN) so `enrich.js` can
  treat both readers polymorphically. WHERE `SOLANA_RPC_URL` (or the default devnet endpoint) is
  unreachable or a read fails, the accessor SHALL throw (never fabricate a balance) — identical
  fail-closed contract to `makeBaseReader`.
- **S6.5 (enrich dispatches per-chain)** `enrich.js`'s `enrichOnChain` SHALL select the reader
  matching each row's `chain` (default `'base'`) rather than assuming one global reader. A mixed
  batch (some Base rows, some Solana rows) SHALL enrich each row correctly without cross-chain
  leakage (a Solana row must never be read against the Base RPC or vice versa).
- **S6.6 (exclude-set is chain-aware)** `leaderboard-constants.js`'s `excludeSet(row)` /
  `SEED_ADDRESSES` SHALL support per-chain address lists (Base addresses lowercased as today,
  Solana addresses compared verbatim/case-sensitive) so self-funding exclusion (GAIN's own-deposit
  filter, sprint-5) works correctly for Solana rows too.
- **S6.7 (UI shows chain)** `AgentLeaderboard.tsx` SHALL render a chain indicator per row (e.g. a
  small "Base" / "Solana" badge) so viewers can see which rail an agent settled on — GAIN is
  compared on the same USD-normalized scale regardless of chain (sprint-5's existing rule), this
  requirement is presentation-only, not a scoring change.
- **S6.8 (participant flow documents both)** `sprint-4-participant-flow.md`'s "one command" /
  Luma-page instructions SHALL show BOTH a Base-wallet and a Solana-wallet variant of the funding
  step (`~/.automaton/wallet.json` shape for each), so a participant is not implicitly funneled to
  Base only.

## Verification architecture

| Req | Test kind | Concrete proof |
|---|---|---|
| S6.1 | unit | a `chain:'solana'` payload with a valid base58 `id` passes `validate()`; an `0x...` id under `chain:'solana'` FAILS; an absent-`chain` payload behaves exactly as today (regression) |
| S6.2 | unit | sign a real ed25519 keypair's message, verify passes; tamper 1 byte of signature → fails; a mixed-case base58 id is NOT mutated/rejected by case-folding (regression-guard: assert the comparison does not call `.toLowerCase()` on a Solana id) |
| S6.3 | unit | `registerSpawn({chain:'solana', ...})` produces a signature that S6.2's verifier accepts; existing Base call sites (no `chain` arg) unaffected (regression) |
| S6.4 | unit + live-optional | mocked RPC responses cover the accessor contract; a live-RPC smoke test against public Solana devnet (skipped gracefully if no network) confirms real balance shape |
| S6.5 | unit | a 2-row batch (1 Base, 1 Solana) enriches both correctly; swapping which reader answers which row is asserted NOT to happen (a Solana id must never resolve via `makeBaseReader`) |
| S6.6 | unit | a Solana row whose `net_worth` inflow `from` matches a Solana seed address is excluded; a Base row's exclusion behavior is unchanged (regression) |
| S6.7 | E2E, browser | `npx playwright-cli` (or CloakBrowser) screenshot of `/dashboard` showing at least one row tagged "Solana" once a real Solana row exists in Supabase |
| S6.8 | manual doc check | sprint-4 spec + the live Luma event page both show the Solana variant |

## TODO checklist (SSOT, VCSDD, one at a time)

```
[ ] T1  RED: telemetry-schema.test — chain-absent (regression), chain:'base' explicit,
        chain:'solana' valid base58, chain:'solana' with 0x-id (must fail)
[ ] T2  GREEN: telemetry-schema.js — add optional chain field + base58 validator branch
[ ] T3  RED: telemetry-verify.test — solana ed25519 sign/verify roundtrip (tweetnacl + bs58,
        add as devDependency if not already present — CHECK package.json first, HARD RULE #6
        exception doesn't apply here, this is real new dep, confirm via npm ls tweetnacl bs58)
[ ] T4  GREEN: telemetry-verify.js — chain branch, case-sensitive compare for solana
[ ] T5  RED+GREEN: spawn-register.js — chain param, solana signer path
[ ] T6  RED+GREEN: chain-reader.js — makeSolanaReader (native SOL + USDC-SPL + inflows + price)
[ ] T7  RED+GREEN: enrich.js — per-row chain dispatch to the matching reader
[ ] T8  RED+GREEN: leaderboard-constants.js — chain-aware excludeSet/SEED_ADDRESSES
[ ] T9  UI: AgentLeaderboard.tsx chain badge (S6.7), browser-verified screenshot
[ ] T10 Docs: sprint-4 spec + Luma page — add the Solana wallet variant (S6.8)
[ ] T11 Fresh-context adversary review (vcsdd-adversary) on T1-T10 as a batch
[ ] T12 NO-MOCK E2E: register one real Solana-chain instance end-to-end against the LIVE
        aniccaai.com API (not local dev server) — real signed heartbeat, real schema pass,
        confirm it appears correctly tagged on /dashboard
```

## Reconciliation with existing sprints

- Sprint-1/3's no-fake engine (enrichOnChain fail-closed, `unverified` flagging) is PRESERVED
  exactly — S6.4/S6.5 require the Solana reader to follow the identical throw-on-failure contract.
- Sprint-5's GAIN formula (Δnet_worth − self_deposits) is UNCHANGED; this sprint only makes the
  inputs (net_worth, inflows) obtainable from either chain. GAIN stays USD-normalized so a Base row
  and a Solana row are directly comparable on the leaderboard.
- Sprint-4's participant flow gains a second funding-step variant (S6.8); the `ANICCA_TAGS`
  mechanism (S4.1) is unchanged and applies identically to Solana-chain instances.

## Out of scope (honest)

- Other chains (Polygon, Arbitrum, etc.) — not requested, not built. Only Base (existing) + Solana
  (this sprint) per Dais's explicit ask.
- A Solana-native `x402`-equivalent settlement protocol is NOT required for the leaderboard itself
  — the leaderboard only READS balances/inflows; it does not broker payments between agents.
- Wiring `makeSolanaReader` into the CoralOS submission's own escrow flow (separate spec,
  `2026-07-04-coralos-submission-clawrouter-zero-human.md`) is a DIFFERENT concern (that spec reads
  escrow program state directly, not a generic wallet balance) — no code sharing assumed until
  GREEN reveals a real duplication worth extracting.
