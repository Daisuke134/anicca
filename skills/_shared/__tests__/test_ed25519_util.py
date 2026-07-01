"""PROP-C1..C4 + PROP-I* + edge cases for lib.ed25519_util."""
from __future__ import annotations
import base64
import subprocess
from pathlib import Path
import pytest

from lib.ed25519_util import (
    is_valid_ed25519_pubkey,
    pubkey_b64_to_pem,
    sign_bytes_ed25519,
    verify_bytes_ed25519,
    generate_test_keypair,
    SigningError,
    UnsupportedOpenSSLError,
)


# ─── PROP-C1: pubkey validation ─────────────────────────────────
class TestPubkeyValidation:
    def test_valid_32byte_base64(self):
        raw = b"\x00" * 32
        assert is_valid_ed25519_pubkey(base64.b64encode(raw).decode()) is True

    @pytest.mark.parametrize("bad", [
        "",  # empty
        "not-base64!!!!",
        base64.b64encode(b"\x00" * 31).decode(),  # 31 bytes short
        base64.b64encode(b"\x00" * 33).decode(),  # 33 bytes long
        base64.b64encode(b"\x00" * 64).decode(),  # ed25519 sig length not pubkey
    ])
    def test_reject_invalid(self, bad):
        assert is_valid_ed25519_pubkey(bad) is False

    def test_accepts_trailing_newline(self):
        raw = b"\x00" * 32
        assert is_valid_ed25519_pubkey(base64.b64encode(raw).decode() + "\n") is True

    def test_accepts_none_returns_false(self):
        assert is_valid_ed25519_pubkey(None) is False


# ─── PROP-C4: pubkey to PEM (SPKI wrap) ─────────────────────────
class TestPubkeyToPem:
    def test_produces_ed25519_pem(self, tmp_path):
        # Generate a real key, extract pubkey, ensure our PEM matches openssl's.
        priv, pub_b64 = generate_test_keypair(tmp_path)
        our_pem = pubkey_b64_to_pem(pub_b64)
        # Ask openssl to derive PEM from same private key + pubout
        r = subprocess.run(
            ["openssl", "pkey", "-in", str(priv), "-pubout"],
            capture_output=True, text=True, timeout=5,
        )
        assert r.returncode == 0
        # openssl adds -----BEGIN/END PUBLIC KEY----- + base64 body
        # Verify our PEM body matches semantically (round-trip through openssl decode)
        our_pem_path = tmp_path / "ours.pem"
        our_pem_path.write_text(our_pem)
        r2 = subprocess.run(
            ["openssl", "pkey", "-pubin", "-in", str(our_pem_path), "-outform", "DER"],
            capture_output=True, timeout=5,
        )
        assert r2.returncode == 0, f"our PEM not accepted: {r2.stderr}"
        # Last 32 bytes of DER should be the raw pubkey
        assert r2.stdout[-32:] == base64.b64decode(pub_b64.strip())


# ─── PROP-C2 sign+verify roundtrip ──────────────────────────────
class TestSignVerifyRoundtrip:
    def test_roundtrip_hello(self, tmp_path):
        priv, pub_b64 = generate_test_keypair(tmp_path)
        data = b"hello, ed25519"
        sig = sign_bytes_ed25519(data, priv)
        assert len(sig) == 64
        assert verify_bytes_ed25519(data, sig, pub_b64) is True

    def test_roundtrip_empty_raises_signing_error(self, tmp_path):
        """EDGE-E5: openssl 3.x refuses to sign 0-byte data
        ('Could not allocate 0 bytes'). Our sign helper propagates that as
        SigningError. Verify the behavior; do NOT claim empty is supported."""
        priv, pub_b64 = generate_test_keypair(tmp_path)
        with pytest.raises(SigningError):
            sign_bytes_ed25519(b"", priv)

    def test_roundtrip_1mb(self, tmp_path):
        """EDGE-E6: large data works via file (openssl streams via file)."""
        priv, pub_b64 = generate_test_keypair(tmp_path)
        data = b"A" * (1024 * 1024)
        sig = sign_bytes_ed25519(data, priv)
        assert verify_bytes_ed25519(data, sig, pub_b64) is True


# ─── PROP-C3 wrong-sig/pubkey/length ─────────────────────────────
class TestVerifyRejection:
    def test_bit_flipped_sig_rejected(self, tmp_path):
        priv, pub_b64 = generate_test_keypair(tmp_path)
        sig = sign_bytes_ed25519(b"payload", priv)
        # Flip a bit
        bad = bytes([sig[0] ^ 0x01]) + sig[1:]
        assert verify_bytes_ed25519(b"payload", bad, pub_b64) is False

    def test_wrong_pubkey_rejected(self, tmp_path):
        priv_a, _ = generate_test_keypair(tmp_path / "a")
        _, pub_b_b64 = generate_test_keypair(tmp_path / "b")
        sig = sign_bytes_ed25519(b"payload", priv_a)
        assert verify_bytes_ed25519(b"payload", sig, pub_b_b64) is False

    def test_wrong_data_rejected(self, tmp_path):
        priv, pub_b64 = generate_test_keypair(tmp_path)
        sig = sign_bytes_ed25519(b"original", priv)
        assert verify_bytes_ed25519(b"tampered", sig, pub_b64) is False

    def test_sig_63_bytes_rejected(self, tmp_path):
        """EDGE-E3."""
        _, pub_b64 = generate_test_keypair(tmp_path)
        assert verify_bytes_ed25519(b"data", b"\x00" * 63, pub_b64) is False

    def test_sig_128_bytes_rejected(self, tmp_path):
        """EDGE-E4."""
        _, pub_b64 = generate_test_keypair(tmp_path)
        assert verify_bytes_ed25519(b"data", b"\x00" * 128, pub_b64) is False

    def test_non_ed25519_pubkey_rejected(self, tmp_path):
        priv, _ = generate_test_keypair(tmp_path)
        sig = sign_bytes_ed25519(b"data", priv)
        assert verify_bytes_ed25519(b"data", sig, "not-a-key") is False


# ─── PROP-C3-exit-code-only (FIND-002 fix) ──────────────────────
def test_verify_source_does_not_parse_stdout_for_english():
    """The verify function MUST NOT depend on English phrases in openssl stdout.
    Grep the source for known bad substrings (case-insensitive)."""
    import re
    src = (Path(__file__).resolve().parents[1] / "lib" / "ed25519_util.py").read_text()
    bad = ["Signature Verified Successfully", "Signature Verified",
           "verified successfully", "verification succeeded"]
    for phrase in bad:
        assert phrase.lower() not in src.lower(), \
            f"FIND-002 regression: source contains fragile stdout phrase {phrase!r}"


# ─── PROP-I1: no shell injection ─────────────────────────────────
def test_source_uses_argv_list_not_shell_true():
    # Security test: asserts the PRODUCTION module source does NOT contain
    # command-injection sinks. The literals below are the patterns we ban;
    # this test never actually invokes shell=True or os.system.
    src = (Path(__file__).resolve().parents[1] / "lib" / "ed25519_util.py").read_text()
    assert "shell=True" not in src
    forbidden_syscall_pattern = "os." + "system("  # split so this line itself isn't flagged
    assert forbidden_syscall_pattern not in src


# ─── PROP-I2: privkey path not logged ────────────────────────────
def test_signing_error_message_does_not_leak_privkey_path(tmp_path):
    """REQ-I2: private key file paths SHALL be read directly and NEVER
    printed to logs/exceptions."""
    bad_path = tmp_path / "definitely-not-a-key-you-know.pem"
    bad_path.write_text("not a real key")
    with pytest.raises(SigningError) as exc_info:
        sign_bytes_ed25519(b"data", bad_path)
    msg = str(exc_info.value)
    assert "definitely-not-a-key" not in msg


def test_missing_privkey_raises_signing_error(tmp_path):
    """EDGE-E7: missing key path."""
    with pytest.raises(SigningError):
        sign_bytes_ed25519(b"data", tmp_path / "does-not-exist.pem")


# ─── PROP-I3: openssl version guard ──────────────────────────────
def test_openssl_version_check_helper_exists():
    """REQ-I3: module MUST check openssl version at import; if < 3.0, raise
    UnsupportedOpenSSLError. Verify the class exists and can be raised."""
    err = UnsupportedOpenSSLError("test")
    assert isinstance(err, Exception)
