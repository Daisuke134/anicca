"""Real ed25519 sign/verify using openssl subprocess.

Sprint-3 #29 fix for earn-shared-skeleton FIND-015 critical (fake sha256
signature protocol). openssl >= 3.0 required for `-rawin` on ed25519.
No PyNaCl dep. All openssl calls use subprocess.run with argv list form.
"""
from __future__ import annotations
import base64
import binascii
import re
import subprocess
from pathlib import Path
from typing import Optional, Tuple

# ed25519 SPKI DER prefix (RFC 8410). 12 bytes:
#   30 2a         SEQUENCE (42 bytes)
#     30 05       SEQUENCE (5 bytes)
#       06 03 2b 65 70   OID 1.3.101.112 (id-Ed25519)
#     03 21       BIT STRING (33 bytes)
#       00        unused bits = 0
#     [32-byte raw pubkey]
_ED25519_SPKI_PREFIX = bytes.fromhex("302a300506032b6570032100")


class SigningError(Exception):
    """REQ-C2/EDGE-E7-E9: openssl sign failure or bad key path."""


class UnsupportedOpenSSLError(Exception):
    """REQ-I3: openssl version < 3.0 detected."""


def _openssl_version_ok() -> bool:
    """Verify openssl reports version >= 3.0 (required for -rawin ed25519)."""
    try:
        r = subprocess.run(
            ["openssl", "version"],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    if r.returncode != 0:
        return False
    m = re.search(r"OpenSSL\s+(\d+)\.(\d+)", r.stdout or "")
    if not m:
        return False
    major = int(m.group(1))
    return major >= 3


# REQ-I3: enforce at import.
if not _openssl_version_ok():
    raise UnsupportedOpenSSLError(
        "openssl >= 3.0 required for ed25519 -rawin"
    )


def is_valid_ed25519_pubkey(b64: Optional[str]) -> bool:
    """REQ-C1: base64 decodes to exactly 32 bytes."""
    if not isinstance(b64, str):
        return False
    try:
        raw = base64.b64decode(b64.strip(), validate=True)
    except (binascii.Error, ValueError):
        return False
    return len(raw) == 32


def pubkey_b64_to_pem(pubkey_b64: str) -> str:
    """REQ-C4: wrap 32-byte raw ed25519 pubkey in SPKI DER + PEM.

    Deterministic, no I/O.
    """
    if not is_valid_ed25519_pubkey(pubkey_b64):
        raise ValueError("invalid ed25519 pubkey")
    raw = base64.b64decode(pubkey_b64.strip(), validate=True)
    der = _ED25519_SPKI_PREFIX + raw
    body = base64.b64encode(der).decode()
    # Standard PEM: 64-char lines
    lines = [body[i:i + 64] for i in range(0, len(body), 64)]
    return (
        "-----BEGIN PUBLIC KEY-----\n"
        + "\n".join(lines)
        + "\n-----END PUBLIC KEY-----\n"
    )


def generate_test_keypair(tmp_dir: Path) -> Tuple[Path, str]:
    """Test-only: generate an ephemeral ed25519 keypair for CI fixtures.

    Returns (private_key_pem_path, pubkey_b64). NOT for production keys.
    """
    tmp_dir = Path(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    priv_path = tmp_dir / "test-ed25519-priv.pem"
    r = subprocess.run(
        ["openssl", "genpkey", "-algorithm", "ed25519", "-out", str(priv_path)],
        capture_output=True, timeout=10,
    )
    if r.returncode != 0 or not priv_path.exists():
        raise SigningError("openssl genpkey failed (rc=" + str(r.returncode) + ")")
    # Extract raw pubkey (last 32 bytes of DER SPKI)
    r2 = subprocess.run(
        ["openssl", "pkey", "-in", str(priv_path), "-pubout", "-outform", "DER"],
        capture_output=True, timeout=5,
    )
    if r2.returncode != 0 or len(r2.stdout) < 32:
        raise SigningError("openssl pubkey extract failed")
    raw_pub = r2.stdout[-32:]
    pub_b64 = base64.b64encode(raw_pub).decode()
    return priv_path, pub_b64


def sign_bytes_ed25519(data: bytes, privkey_pem: Path) -> bytes:
    """REQ-C2: real ed25519 sign via openssl pkeyutl -sign -rawin.

    Returns raw 64-byte signature. Raises SigningError on failure.
    IMPORTANT: never includes privkey path in raised exception messages.
    """
    priv_path = Path(privkey_pem)
    if not priv_path.is_file():
        raise SigningError("private key not found (path scrubbed)")
    # Write data to temp file (openssl -rawin reads from -in file)
    data_path = priv_path.parent / f".signdata-{id(data):x}.tmp"
    sig_path = priv_path.parent / f".sigout-{id(data):x}.tmp"
    try:
        data_path.write_bytes(data)
        r = subprocess.run(
            ["openssl", "pkeyutl", "-sign",
             "-inkey", str(priv_path),
             "-rawin",
             "-in", str(data_path),
             "-out", str(sig_path)],
            capture_output=True, timeout=10,
        )
        if r.returncode != 0:
            raise SigningError(f"openssl sign failed rc={r.returncode}")
        if not sig_path.exists():
            raise SigningError("openssl produced no sig file")
        sig = sig_path.read_bytes()
        if len(sig) != 64:
            raise SigningError(f"unexpected sig length {len(sig)}")
        return sig
    finally:
        for p in (data_path, sig_path):
            try:
                if p.exists():
                    p.unlink()
            except OSError:
                pass


def verify_bytes_ed25519(data: bytes, sig: bytes, pubkey_b64: str) -> bool:
    """REQ-C3: real ed25519 verify. Returns True IFF openssl exits 0.

    FIND-002 fix: exit code is the ONLY predicate — no stdout/stderr parsing.
    """
    # (i) reject non-ed25519 pubkey
    if not is_valid_ed25519_pubkey(pubkey_b64):
        return False
    # (ii) reject wrong-length sig
    if not isinstance(sig, (bytes, bytearray)) or len(sig) != 64:
        return False
    # Materialise pubkey PEM to tmp file
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        pem_path = td_path / "pub.pem"
        data_path = td_path / "data.bin"
        sig_path = td_path / "sig.bin"
        try:
            pem_path.write_text(pubkey_b64_to_pem(pubkey_b64))
        except ValueError:
            return False
        data_path.write_bytes(data)
        sig_path.write_bytes(bytes(sig))
        # (iii) invoke openssl. shell=False (default). No stdout parsing.
        r = subprocess.run(
            ["openssl", "pkeyutl", "-verify",
             "-pubin", "-inkey", str(pem_path),
             "-rawin",
             "-in", str(data_path),
             "-sigfile", str(sig_path)],
            capture_output=True, timeout=10,
        )
        # (iv) FIND-002: exit code is the sole predicate. Stdout/stderr NOT parsed.
        return r.returncode == 0
