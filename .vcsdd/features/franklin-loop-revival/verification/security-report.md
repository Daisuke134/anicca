# Security Hardening Report — franklin-loop-revival

## Tooling
- `node --test` (33 new + 42 regression), fresh-Opus Phase-3 adversary (read-only, full source trace), live-system inspection (`ps eww`, `launchctl list`, `~/.blockrun/logs/daemon.err`, `ledger.jsonl`). No new dependencies added.

## RCE / Injection
- No shell interpolation of untrusted input introduced. `wallet-address-solana.mjs` takes no external args; `anicca-daemon.sh` franklin branch calls fixed node scripts with no user-controlled data. `plutil -lint` OK on the plist.

## Anti-Human-Touch
- Zero human credential / OAuth / tap introduced. Wallet resolved autonomously from the instance's own `.solana-session`; THINK routed to the already-running local ClawRouter (:8402) at $0.

## Cryptographic Correctness
- Solana pubkey derived via `resolve-identity.mjs::resolveSolanaSecret` → Keypair; malformed/wrong-length/empty secrets fail closed (warn, no crash, no address emitted). USDC balance read via existing unit-tested `solana-verify.mjs::usdcBalance` (verified USDC mint, returns 0 on zero ATA).

## Key Handling
- `wallet-address-solana.mjs` emits ONLY the derived public address (single stdout.write); catch block never interpolates secret material (REQ-006, adversary-verified). No key written to logs/ledger.
- franklin `ensure_brain` reads NO `$HOME/.openclaw/.env` / `BLOCKRUN_WALLET_KEY` / other-instance key file (REQ-005/PROP-016, adversary read full branch text).

## Spec-Gaming / AI-Slop Surface
- Tier cannot be gamed: `ANICCA_BALANCE_OVERRIDE` forbidden in the deployed plist (PROP-013) + live-process-env checked (PROP-014). "tier != broke" verified against the REAL fetched balance ($11.39), not a shortcut.
- Per-instance identity gate (ANICCA_HOME=`~/.blockrun`) fails closed for foreign homes — no Efpap5-class dot-dir scan hijack. (#8 tracks the standalone latent root-cause.)

## Summary
No RCE/injection/credential/key-leak surface introduced. Identity gate and secret non-leak adversary-verified. Deploy-safe on the shared daemon (automaton/founder-loop unaffected). 5 non-blocking advisories (Solana RPC single-endpoint, stale telemetry label, dead plist keys) tracked for a later hardening pass.
