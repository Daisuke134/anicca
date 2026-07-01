---
feature: spawn-pin-real-ed25519
phase: 5
mode: lean
generated_at: 2026-07-01
---

# Verification Report — spawn-pin-real-ed25519

## Proof Obligations

Lean; 13 required:true PROPs. All proved via test harness.

| PROP | Status |
|------|--------|
| PROP-C1-pubkey-validation | proved (parametrized 5 invalid + 1 valid + newline strip + None) |
| PROP-C2-sign-roundtrip | proved (hello, 1MB) |
| PROP-C3-verify-wrong-sig-false | proved (bit-flip rejection) |
| PROP-C3-verify-wrong-pubkey-false | proved (sign A verify B) |
| PROP-C3-verify-wrong-length-sig | proved (63 + 128 byte rejection) |
| PROP-C3-exit-code-only (FIND-002 spec) | proved (test_verify_source_does_not_parse_stdout_for_english + FIND-002 impl fix confirmed by grep) |
| PROP-C4-pem-format | proved (openssl round-trip accepts our PEM + DER tail matches raw pubkey) |
| PROP-P1-fixture-uses-ephemeral | proved (fixture_clean now generates ed25519 keypair + writes pubkey; no hard-coded key) |
| PROP-P2-verify-real-ed25519 | proved (test_prop_p2 asserts import + call site) |
| PROP-P3-no-fixture-sha256-in-prod | proved (test_prop_p3 4 regex patterns ban old sha256 fixture code) |
| PROP-A1-spec-symbol-alignment | proved (test_prop_a1 asserts earn-shared-skeleton spec references roi_track.roi_row + menu.pick_next + menu.load_menu) |
| PROP-I1-no-shell-injection | proved (grep source for shell=True + os.system → 0) |
| PROP-I2-privkey-path-not-logged | proved (test_signing_error_message_does_not_leak_privkey_path uses recognizable path fragment) |
| PROP-I3-openssl-version-check | proved (_openssl_version_ok raises at import if < 3.0; UnsupportedOpenSSLError class exists) |

## Summary

Trajectory:
- Phase 1c spec: 4→0 (2 iter; 1 high stdout coupling + 3 medium)
- Phase 2a RED: 2 modules ModuleNotFoundError
- Phase 2b GREEN: 372→395→398 (+3 grep invariants for FIND-001 close)
- Phase 3 impl: 2→0 (2 iter; 2 medium sign tmp location + grep invariant coverage)
- Phase 5 hardening: this + security + purity + grep audit

Key security wins:
- Real ed25519 sign/verify via openssl subprocess (no PyNaCl dep)
- Fixture sha256 protocol REMOVED (fail-closed)
- Verify success = exit code ONLY (FIND-002 spec anti-pattern eliminated)
- Sign uses tempfile.TemporaryDirectory (no artifacts near private key)
- Private key paths never leak into exception messages

## Sprint-4 carry (per behavioral-spec §6 and §7.3)
- Provision production anicca-bot ed25519 private key at documented location
  (~/.openclaw/identity/anicca-bot.key)
- Add integration test that signs a real spawn surface with the production key
- Post-deploy audit re-run to confirm 0 lingering sha256-fixture .sig files
