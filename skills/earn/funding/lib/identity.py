"""Recipient/sender identity verification -- the money-safety rail that fixes the "Efpap5
incident" (2026-07-08, docs/loop-engineering/10-STATUS-verified.md TODO#2 note: "franklin
proxy 直近再起動で wallet を `8Fpqd` でなく `Efpap5` 表示 = identity 要確認"). A dashboard/proxy
can DISPLAY a different address after a restart; trusting that display string instead of the
actual key material could misdirect real funds. This module always derives the recipient's
PUBLIC address from its OWN key/session file and cross-checks it against a known-good address
from config -- never trusts a banner/label alone.

Everything here is either pure (no I/O) or reads only a local key file to derive a PUBLIC
address; it never returns or logs the secret itself.
"""
from __future__ import annotations

from typing import Optional, TypedDict


class IdentityCheck(TypedDict):
    verified: bool
    reason: str
    derived: Optional[str]


def normalize_evm_address(addr: str) -> str:
    return (addr or "").strip().lower()


def verify_evm_address(*, candidate: str, known_address: str) -> IdentityCheck:
    """Simplest, strongest form of this rail for EVM: the candidate address must match the
    address we already know out-of-band (config), case-insensitively."""
    if not candidate or not known_address:
        return {"verified": False, "reason": "missing candidate or known_address", "derived": candidate}
    ok = normalize_evm_address(candidate) == normalize_evm_address(known_address)
    return {
        "verified": ok,
        "reason": "matches known address" if ok else f"{candidate} != known {known_address}",
        "derived": candidate,
    }


def keypair_from_secret_string(secret: str):
    """Decode a Solana secret-key STRING into a `solders.keypair.Keypair`, trying base58 first
    (the format Franklin's own `~/.blockrun/.solana-session` genuinely uses -- verified live,
    88 chars, no padding characters) and falling back to base64 (the format that
    `~/.anicca-founder/solana-wallet.json`'s `secret_key_base58` field ACTUALLY contains,
    despite its name -- verified live 2026-07-08: it decodes as base64, not base58, and the
    result correctly re-derives the known BF9v... address). This dual-decode is a deterministic
    parse of a fixed machine format (not a judgment call), so a plain try/fallback is
    appropriate here (see rules/building-effective-ai-agents.md distinction between judgment
    regex and fixed-format parsing)."""
    from solders.keypair import Keypair  # local import: keep this module importable without solders

    secret = secret.strip()
    try:
        return Keypair.from_base58_string(secret)
    except Exception:
        import base64

        raw = base64.b64decode(secret)
        return Keypair.from_bytes(raw)


def derive_solana_pubkey_from_secret(secret_b58: str) -> str:
    """Decode a Solana secret key (base58 or base64, see `keypair_from_secret_string`) and
    return the PUBLIC key it derives. Requires `solders` (already an installed project
    dependency, see skills/earn/sol-to-usdc.py)."""
    kp = keypair_from_secret_string(secret_b58)
    return str(kp.pubkey())


def verify_solana_secret_file(*, path: str, known_address: str) -> IdentityCheck:
    """Read a base58 secret-key file at `path`, derive its pubkey, and confirm it equals
    `known_address`. Fails closed (verified=False) on ANY read/decode error or mismatch --
    this is the direct fix for the Efpap5 incident: never send because a banner said so,
    only because the key material itself proves the address."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read().strip()
        # Accept either a bare base58 string (.solana-session) or the wallet.json shape
        # ({"secret_key_base58": "..."}) -- try bare first, then JSON.
        secret = raw
        if raw.startswith("{"):
            import json

            secret = json.loads(raw)["secret_key_base58"]
        derived = derive_solana_pubkey_from_secret(secret)
    except Exception as e:  # noqa: BLE001 -- any failure here must fail closed, not raise
        return {"verified": False, "reason": f"could not derive pubkey from {path}: {e}", "derived": None}

    if derived != known_address:
        return {
            "verified": False,
            "reason": f"{path} derives {derived}, expected {known_address}",
            "derived": derived,
        }
    return {"verified": True, "reason": "session pubkey matches known address", "derived": derived}
