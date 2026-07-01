---
feature: spawn-pin-real-ed25519
phase: 1b
mode: lean
generated_at: 2026-07-01
---

# Verification Architecture — spawn-pin-real-ed25519

## Purity boundary

| Layer | Symbol | Side effects |
|---|---|---|
| PURE — `lib/ed25519_util.py` (new) | `is_valid_ed25519_pubkey(b64)` | none (str → bool) |
| PURE — `lib/ed25519_util.py` | `pubkey_b64_to_pem(pubkey_b64)` | none (deterministic DER wrap) |
| I/O (subprocess) — `lib/ed25519_util.py` | `sign_bytes_ed25519(data, privkey_pem)` | openssl subprocess + tmp file for stdin data |
| I/O (subprocess) — `lib/ed25519_util.py` | `verify_bytes_ed25519(data, sig, pubkey_b64)` | openssl subprocess + tmp file for pubkey PEM |
| I/O (test-only) — `lib/ed25519_util.py` | `generate_test_keypair(tmp_path)` → (privkey_pem_path, pubkey_b64) | openssl subprocess (test fixture use only) — SINGLE canonical name matching REQ-P4 (FIND-001 fix) |
| ORCHESTRATOR — `lib/spawn_pin.py` (modified) | fixture_clean + verify_spawn_surface | composes; REMOVES fixture sha256 protocol |
| SPEC — `earn-shared-skeleton/specs/verification-architecture.md` | Pure-layer table | text edit only (FIND-006 alignment) |

## Proof obligations

| PROP | Tier | Required | Maps to |
|---|---|---|---|
| PROP-C1-pubkey-validation | 1 | true | REQ-C1 (parametrized valid + 5 invalid cases) |
| PROP-C2-sign-roundtrip | 1 | true | REQ-C2, REQ-C3 — sign then verify → True |
| PROP-C3-verify-wrong-sig-false | 1 | true | REQ-C3 — bit-flip sig → False |
| PROP-C3-verify-wrong-pubkey-false | 1 | true | REQ-C3 — sign with key A, verify with key B → False |
| PROP-C3-verify-wrong-length-sig | 1 | true | EDGE-E3/E4 |
| PROP-C3-exit-code-only (FIND-002 fix) | 1 | true | REQ-C3(iv) — grep verify_bytes_ed25519 for 'stdout' and 'Signature Verified' substring = 0 hits; exit code IS the sole predicate |
| PROP-C4-pem-format | 1 | true | REQ-C4 — round-trip openssl accepts our PEM |
| PROP-P1-fixture-uses-ephemeral | 1 | true | REQ-P1 — fixture_clean does NOT hard-code anicca-bot key |
| PROP-P2-verify-real-ed25519 | 1 | true | REQ-P2 — spawn_pin's verify path uses ed25519_util.verify (grep for sha256 in verify path = 0) |
| PROP-P3-no-fixture-sha256-in-prod | 1 | true | REQ-P3 — grep spawn_pin.py for `hashlib.sha256.*pubkey_raw` = 0 |
| PROP-A1-spec-symbol-alignment | 1 | true | REQ-A1 — earn-shared-skeleton spec references roi_track / menu / no manifest module |
| PROP-I1-no-shell-injection | 1 | true | REQ-I1 grep — subprocess.run always with list-argv, NEVER with shell=True or string cmd |
| PROP-I2-privkey-path-not-logged | 1 | true | REQ-I2 — grep exceptions/logs for `privkey_pem` = only in argv, not in messages |
| PROP-I3-openssl-version-check | 1 | true | REQ-I3 — at import, openssl version ≥ 3.0 or raise |
| PROP-NFR3-deterministic-sign | 0 | false | ed25519 property; optional smoke test |

13 required:true. Tests:
- `__tests__/test_ed25519_util.py` — PURE + subprocess unit tests (Darwin needs openssl 3)
- `__tests__/test_spawn_pin_ed25519_integration.py` — spawn_pin integration with real keypair
- Modification to existing `test_spawn_pin.py` if the sha256 fixture protocol path is currently tested

## Sprint-3 migration audit deliverables (FIND-003 + FIND-004)

Sprint-3 ships two audit artifacts alongside the code:

1. `evidence/sprint-1-migration-audit.txt` — output of the pre-deploy
   `find + sig fingerprint` command, listing every `spawn-surface.pinned.json.sig`
   file that used the sha256 fixture protocol.
2. `evidence/sprint-1-post-deploy-audit.txt` — post-deploy re-run confirming
   0 sha256-fixture sigs remain.

The tests SHALL fail if the audit script cannot enumerate the paths (= the
audit code exists AND runs green).

## Done = 4-D convergence

- spec ✓ test ✓ impl ✓ verification ✓
- adversary PASS + `openssl version` reports ≥ 3.0 + sign+verify roundtrip on
  a 32-byte pubkey + 64-byte sig + PROP-P3 grep on spawn_pin.py returns 0
  hits on the fixture-protocol pattern.
