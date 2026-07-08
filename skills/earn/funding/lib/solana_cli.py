"""Thin wrapper around the OFFICIAL Solana `spl-token` CLI (already installed on this Mac at
~/.local/share/solana/install/active_release/bin/) for SPL token transfers -- reuses the
audited, maintained CLI instead of hand-rolling raw SPL instruction bytes (no reinvention,
per project policy). The only original code here is converting this repo's base58-secret
wallet formats (`.solana-session`, `solana-wallet.json`'s `secret_key_base58`) into the CLI's
own JSON-array keypair format via `solders`, in a chmod-600 temp file that is always deleted.
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
from typing import Optional

SPL_TOKEN_BIN = os.path.expanduser(
    os.environ.get(
        "SPL_TOKEN_BIN", "~/.local/share/solana/install/active_release/bin/spl-token"
    )
)


def keypair_file_from_base58(secret_b58: str) -> tuple[str, str]:
    """Write a temp Solana-CLI-format keypair file (JSON array of 64 ints, via solders'
    `to_json()`, which IS that exact format) from a base58-OR-base64 secret (see
    lib/identity.keypair_from_secret_string -- this repo's wallet files are inconsistently
    named/encoded, verified live 2026-07-08). Returns (temp_path, derived_pubkey). Caller MUST
    delete temp_path when done (see spl_transfer's `finally`) -- never leave a plaintext key
    material file lying around."""
    from lib.identity import keypair_from_secret_string

    kp = keypair_from_secret_string(secret_b58)
    fd, path = tempfile.mkstemp(prefix="anicca-funding-kp-", suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(kp.to_json())
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        os.remove(path)
        raise
    return path, str(kp.pubkey())


def spl_transfer(
    *,
    secret_b58: str,
    mint: str,
    amount_tokens: float,
    recipient: str,
    rpc_url: str,
    fund_recipient: bool = False,
    timeout: int = 90,
) -> dict:
    """Execute a REAL SPL token transfer via `spl-token transfer`. Returns
    {ok, signature|None, sender, raw, error?}. Never logs/returns the secret. The temp keypair
    file is removed in a `finally` even if the subprocess itself fails."""
    keypair_path, sender_pubkey = keypair_file_from_base58(secret_b58)
    try:
        cmd = [
            SPL_TOKEN_BIN,
            "transfer",
            mint,
            str(amount_tokens),
            recipient,
            "--owner",
            keypair_path,
            "--fee-payer",
            keypair_path,
            "--url",
            rpc_url,
            "--output",
            "json",
        ]
        if fund_recipient:
            cmd.append("--fund-recipient")
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if proc.returncode != 0:
            return {
                "ok": False,
                "signature": None,
                "sender": sender_pubkey,
                "error": (proc.stderr or proc.stdout).strip()[:500],
            }
        signature: Optional[str] = None
        raw: dict
        try:
            raw = json.loads(proc.stdout)
            signature = raw.get("signature")
        except Exception:  # noqa: BLE001 -- fall back to raw text, don't crash on odd CLI output
            raw = {"raw_stdout": proc.stdout.strip()[:500]}
        return {"ok": bool(signature), "signature": signature, "sender": sender_pubkey, "raw": raw}
    finally:
        try:
            os.remove(keypair_path)
        except OSError:
            pass
