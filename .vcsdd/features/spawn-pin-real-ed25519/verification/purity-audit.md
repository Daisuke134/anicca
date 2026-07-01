---
feature: spawn-pin-real-ed25519
phase: 5
mode: lean
generated_at: 2026-07-01
---

# Purity Boundary Audit — spawn-pin-real-ed25519

## Declared Boundaries

| Layer | Symbol | Side effects |
|---|---|---|
| PURE — `lib/ed25519_util.py` | `is_valid_ed25519_pubkey(b64)` | none |
| PURE — `lib/ed25519_util.py` | `pubkey_b64_to_pem(pubkey_b64)` | none (deterministic DER wrap) |
| I/O SUBPROCESS | `_openssl_version_ok()` | openssl version subprocess (one-shot at import) |
| I/O SUBPROCESS + tmpdir | `sign_bytes_ed25519(data, privkey_pem)` | tempfile.TemporaryDirectory + openssl subprocess |
| I/O SUBPROCESS + tmpdir | `verify_bytes_ed25519(data, sig, pubkey_b64)` | tempfile.TemporaryDirectory + openssl subprocess |
| I/O SUBPROCESS | `generate_test_keypair(tmp_dir)` | openssl genpkey (test-only) |
| ORCHESTRATOR — `lib/spawn_pin.py` | `fixture_clean` + `verify_spawn_surface` | composes; sha256 fixture protocol REMOVED |

## Observed Boundaries

- `is_valid_ed25519_pubkey` — parametrized over 5 invalid + valid + newline;
  all pure str → bool.
- `pubkey_b64_to_pem` — SPKI DER wrap deterministic; openssl round-trip test
  proves output structurally valid.
- `sign_bytes_ed25519` — creates ephemeral tmpdir per call; no state leaks.
- `verify_bytes_ed25519` — same tmpdir pattern; exit-code-only predicate.
- `spawn_pin.verify_spawn_surface` — imports verify_bytes_ed25519; uses it
  as the sole sig-verification primitive; fixture protocol code removed.

## Sprint-3 boundary changes vs sprint-1

- Previously: fixture sha256 protocol lived INSIDE spawn_pin.py — both sign
  and verify paths.
- Now: sign and verify are external PURE-ish helpers in ed25519_util.py.
  spawn_pin composes them + owns the spawn-surface state check.

## Summary

PURE + declared-I/O separation clean. Tempfile-based side effects contained
in the callsite tmpdir (no artifacts left near private key). No new
purity violations vs sprint-2 baseline.
