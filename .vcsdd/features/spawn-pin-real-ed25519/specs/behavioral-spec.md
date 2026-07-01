---
feature: spawn-pin-real-ed25519
mode: lean
sprint: 1
language: python
created: 2026-07-01
carries: earn-shared-skeleton FIND-006 (medium) + FIND-015 (critical)
---

# Behavioral Specification — spawn-pin-real-ed25519 (sprint-3 #29)

## 1. Purpose

Close two sprint-1 carry findings on `skills/_shared/lib/spawn_pin.py`:

- **FIND-015 critical**: replace the fixture sha256 "signature" protocol with
  REAL ed25519 sign+verify using `openssl` subprocess (no new pip deps).
- **FIND-006 medium**: align the earn-shared-skeleton verification-architecture
  Pure-layer table with the actual sprint-3 impl symbols (roi_row / pick_next /
  novelty logic already ship; the sprint-1 aspirational names never materialized).

Both are security/correctness fixes; neither changes any production flow that
is currently live-earning ¥.

## 2. Out of scope

- Does NOT change spawn-surface FILE LIST (still 7 files per sprint-2 v7).
- Does NOT rotate the anicca-bot pubkey.
- Does NOT ship a private key. Production wiring documents where the private
  key MUST be placed; if absent, sign() refuses (fail-closed).
- Does NOT introduce PyNaCl dep — openssl (macOS system) via subprocess is
  the only crypto backend.

## 3. Requirements (EARS)

### Group C — Real ed25519 crypto helpers

- **REQ-C1**: THE PURE HELPER `is_valid_ed25519_pubkey(b64: str) -> bool` SHALL
  return True iff the base64-decoded input is exactly 32 bytes. Anything else
  (wrong length, malformed base64, None) returns False. NO side-effects.
- **REQ-C2**: THE I/O HELPER `sign_bytes_ed25519(data: bytes, privkey_pem: Path)
  -> bytes` SHALL invoke `openssl pkeyutl -sign -inkey <privkey_pem> -rawin`
  (openssl ≥ 3.0 for ed25519 -rawin) and return the raw 64-byte signature.
  Raises SigningError on any failure (subprocess non-zero, wrong output length).
- **REQ-C3**: THE I/O HELPER `verify_bytes_ed25519(data: bytes, sig: bytes,
  pubkey_b64: str) -> bool` SHALL:
  (i) reject non-ed25519 pubkey via is_valid_ed25519_pubkey (return False),
  (ii) reject wrong-length signature (!= 64 bytes, return False),
  (iii) invoke `openssl pkeyutl -verify -pubin -inkey <derived_pem> -rawin`
       with the signature via stdin,
  (iv) return True iff openssl exits 0 and prints "Signature Verified Successfully".
- **REQ-C4**: THE HELPER `pubkey_b64_to_pem(pubkey_b64: str) -> str` SHALL
  return an ED25519 PEM-formatted public key string using openssl's raw-to-PEM
  DER wrap (SPKI header for ed25519 = fixed 12-byte prefix `302a300506032b6570032100`).
  Deterministic; no I/O.

### Group P — spawn_pin integration

- **REQ-P1**: `SpawnSurfaceState.fixture_clean` SHALL:
  (a) generate an ephemeral ed25519 keypair via openssl at fixture setup time,
  (b) sign the pinned bytes with the ephemeral private key,
  (c) write both the pubkey (base64) and the sig (raw 64 bytes) into the fixture,
  (d) NOT hard-code the anicca-bot pubkey — fixtures use their own keypair.
- **REQ-P2**: `verify_spawn_surface` SHALL:
  (a) load `anicca-bot.pub` (base64 ed25519 pubkey),
  (b) if pubkey fails REQ-C1, return FAIL with reason "trust-anchor-invalid-ed25519",
  (c) verify the sig on pinned.json bytes using verify_bytes_ed25519,
  (d) if verify returns False, return FAIL with reason "spawn-surface-sig-invalid"
       (existing escalation_reason preserved for backwards-compat).
- **REQ-P3**: The `hashlib.sha256(final_bytes + pubkey_raw.encode())` fixture-
  protocol code path in lines 82-88 + 133-140 SHALL be REMOVED. No fallback
  fixture protocol in production.
- **REQ-P4**: A test-only fixture `fixture_ed25519_keypair(tmp_path)` SHALL
  generate a temp keypair for tests. Tests SHALL NOT hard-code
  private key bytes.

### Group A — Spec/impl alignment (FIND-006)

- **REQ-A1**: The `earn-shared-skeleton/specs/verification-architecture.md`
  Pure-layer table SHALL be updated to reference actual sprint-3 symbols:
  (a) `roi.compute_pass_row` → `lib.roi_track.roi_row`,
  (b) `passprep.compute_novelty_floor` → `lib.menu.pick_next` (with
     novelty_quota_ratio parameter; there is no separate compute_novelty_floor),
  (c) `passprep.pick_untried` → same `lib.menu.pick_next` novelty path,
  (d) `manifest.validate` → `lib.menu.load_menu` schema_version check (there
     is no separate manifest module; menu.json IS the manifest).

### Group I — Invariants

- **REQ-I1**: NO subprocess call SHALL execute a shell command constructed by
  string concatenation. All openssl invocations use `subprocess.run([...])`
  argv-list form (= no shell interpolation).
- **REQ-I2**: Private key file paths SHALL be read directly (never printed to
  stdout, stderr, logs, or exception messages).
- **REQ-I3**: OpenSSL version check: at module load time, verify openssl
  reports version ≥ 3.0 (required for `-rawin` on ed25519). If < 3.0, raise
  UnsupportedOpenSSLError.

## 4. Edge cases

| EDGE | Trigger | Expected |
|---|---|---|
| E1 | pubkey_b64 has trailing whitespace / newline | strip before base64-decode |
| E2 | pubkey_b64 is not valid base64 | is_valid_ed25519_pubkey returns False |
| E3 | Signature is 63 bytes (short) | verify returns False |
| E4 | Signature is 128 bytes (double-length) | verify returns False |
| E5 | Data is empty bytes | sign + verify still work (openssl handles empty data) |
| E6 | Data is 10 MB | sign + verify still work (openssl streams via stdin) |
| E7 | Private key file does not exist | sign raises SigningError with clear reason (path NOT in message) |
| E8 | Private key file is a directory | sign raises SigningError |
| E9 | OpenSSL exits with error (e.g. wrong key format) | sign raises; verify returns False |
| E10 | Concurrent verify calls | each opens its own subprocess; no shared state |

## 5. NFR

- **NFR-1**: verify wall-time < 100ms per call (subprocess spawn overhead dominates).
- **NFR-2**: NO new pip deps. Uses only stdlib + `openssl` binary.
- **NFR-3**: Deterministic sign for the same input+key (ed25519 signatures ARE
  deterministic by construction).

## 6. Sprint-4 handoff (documented for later)

- Add an integration test that uses the anicca-bot PRODUCTION private key from
  a documented location (e.g. `~/.openclaw/identity/anicca-bot.key`).
- Rotate the fixture protocol out of anicca-bot spawn-surface.pinned.json.sig
  if any live production instance still uses it (grep audit needed).
