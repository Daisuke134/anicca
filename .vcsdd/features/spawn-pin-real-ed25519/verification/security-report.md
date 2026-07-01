---
feature: spawn-pin-real-ed25519
phase: 5
mode: lean
generated_at: 2026-07-01
---

# Security Hardening Report — spawn-pin-real-ed25519

## Tooling

| Tool | Status |
|------|--------|
| Manual grep sweep | applied; `security-results/manual-grep.txt` |
| Static regex regression guards | continuously enforced (5 required:true grep tests) |
| Openssl version guard | at import time (raises UnsupportedOpenSSLError if < 3.0) |

## RCE / Injection

| Pattern | Hits |
|---------|------|
| subprocess(..., shell=True) | 0 |
| os.system( (split-token check) | 0 |
| eval( | 0 |
| String-concat cmd construction | 0 (all openssl calls use argv list) |

## Anti-Human-Touch (REQ-J8 inherited)

- 0 hits on osascript, terminal-notifier, telegram, slack, twilio, SecKeychain, find-generic-password

## Cryptographic Correctness

- Sign: `openssl pkeyutl -sign -inkey <priv> -rawin -in <data> -out <sig>`
  argv list, verified sig length == 64 (real ed25519)
- Verify: `openssl pkeyutl -verify -pubin -inkey <pem> -rawin -in <data> -sigfile <sig>`
  Return value = `r.returncode == 0` ONLY. NO stdout/stderr parsing.
- SPKI DER prefix for ed25519 = `302a300506032b6570032100` (RFC 8410 OID 1.3.101.112).
  Cryptographically correct (verified by adversary + PEM round-trip test).
- Bit-flip on sig → reject. Sign A / verify B → reject. Wrong data → reject.
  Wrong sig length (63 / 128) → reject before invoking openssl.

## Key Handling

- Private key paths NEVER printed to logs / exception messages.
  `test_signing_error_message_does_not_leak_privkey_path` enforces.
- Sign uses `tempfile.TemporaryDirectory()` — NO artifacts written into the
  private key's parent directory (FIND-002 iter-1 fix).
- Fixture keypair generation is TEST-ONLY (`generate_test_keypair`).
  Production must place a real key at `~/.openclaw/identity/anicca-bot.key`.

## Spec-Gaming / AI-Slop Surface

Phase 3 adversary caught:
- iter-1 FIND-002: sign writes tmp files into priv_path.parent → concurrent
  same-payload collision on interned `id(b"...")` + 0o500 keydir failure mode
- iter-1 FIND-001: required grep invariants had no enforcing test → future
  regressions would pass CI

Cycle-2 closed both:
- sign now uses tempfile.TemporaryDirectory (matches verify pattern)
- 3 new regex regression tests enforce PROP-P2/P3/A1

## Summary

Security-critical replacement of a fake sha256 signature protocol with real
ed25519 verified via openssl. Cycle-2 catches real correctness bugs the naive
"trust the roundtrip test" approach would miss. Sprint-4 must provision the
production private key before any real spawn surface can be signed.
