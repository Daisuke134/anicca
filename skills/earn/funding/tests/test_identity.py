import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.identity import (  # noqa: E402
    derive_solana_pubkey_from_secret,
    keypair_from_secret_string,
    normalize_evm_address,
    verify_evm_address,
    verify_solana_secret_file,
)

from solders.keypair import Keypair  # noqa: E402


def test_normalize_evm_address_lowercases_and_strips():
    assert normalize_evm_address("  0xABC  ") == "0xabc"


def test_verify_evm_address_matches_case_insensitively():
    r = verify_evm_address(candidate="0xAbC123", known_address="0xabc123")
    assert r["verified"] is True


def test_verify_evm_address_mismatch_fails_closed():
    r = verify_evm_address(candidate="0xdead", known_address="0xbeef")
    assert r["verified"] is False


def test_verify_evm_address_missing_inputs_fail_closed():
    assert verify_evm_address(candidate="", known_address="0xabc")["verified"] is False
    assert verify_evm_address(candidate="0xabc", known_address="")["verified"] is False


def test_derive_solana_pubkey_from_secret_roundtrip():
    kp = Keypair()
    secret_b58 = str(kp)  # solders Keypair __str__ is the base58 secret
    derived = derive_solana_pubkey_from_secret(secret_b58)
    assert derived == str(kp.pubkey())


def test_verify_solana_secret_file_bare_string(tmp_path):
    kp = Keypair()
    p = tmp_path / ".solana-session"
    p.write_text(str(kp))
    result = verify_solana_secret_file(path=str(p), known_address=str(kp.pubkey()))
    assert result["verified"] is True
    assert result["derived"] == str(kp.pubkey())


def test_verify_solana_secret_file_json_wrapped(tmp_path):
    kp = Keypair()
    p = tmp_path / "solana-wallet.json"
    p.write_text(json.dumps({"secret_key_base58": str(kp), "address": str(kp.pubkey())}))
    result = verify_solana_secret_file(path=str(p), known_address=str(kp.pubkey()))
    assert result["verified"] is True


def test_verify_solana_secret_file_mismatch_fails_closed_the_efpap5_case(tmp_path):
    """The exact incident this rail exists for: the key file derives a DIFFERENT address
    than the one we expected (e.g. a dashboard/proxy displayed 'Efpap5...' instead of the
    real '8Fpqd...') -- must fail closed, never send."""
    real_kp = Keypair()
    wrong_known_address = str(Keypair().pubkey())  # a different, unrelated address
    p = tmp_path / ".solana-session"
    p.write_text(str(real_kp))
    result = verify_solana_secret_file(path=str(p), known_address=wrong_known_address)
    assert result["verified"] is False
    assert result["derived"] == str(real_kp.pubkey())


def test_verify_solana_secret_file_missing_file_fails_closed():
    result = verify_solana_secret_file(path="/nonexistent/path/.solana-session", known_address="anything")
    assert result["verified"] is False


def test_verify_solana_secret_file_garbage_content_fails_closed(tmp_path):
    p = tmp_path / ".solana-session"
    p.write_text("not a valid base58 secret key at all !!!")
    result = verify_solana_secret_file(path=str(p), known_address="anything")
    assert result["verified"] is False


def test_keypair_from_secret_string_accepts_base64_fallback():
    """Regression test: ~/.anicca-founder/solana-wallet.json's `secret_key_base58` field is,
    despite its name, actually base64-encoded (verified live 2026-07-08 -- base58 decode of it
    raises InvalidChar on the '+' character). The decoder must fall back to base64 and still
    derive the correct pubkey, or every founder-wallet identity check would fail closed for
    the wrong reason (a parsing bug, not a real identity mismatch)."""
    import base64

    kp = Keypair()
    b64_secret = base64.b64encode(bytes(kp)).decode()
    assert "+" in b64_secret or "/" in b64_secret or True  # not all keys contain +/, but decode must still work
    decoded = keypair_from_secret_string(b64_secret)
    assert decoded.pubkey() == kp.pubkey()


def test_verify_solana_secret_file_json_wrapped_base64(tmp_path):
    import base64
    import json as _json

    kp = Keypair()
    b64_secret = base64.b64encode(bytes(kp)).decode()
    p = tmp_path / "solana-wallet.json"
    p.write_text(_json.dumps({"secret_key_base58": b64_secret, "address": str(kp.pubkey())}))
    result = verify_solana_secret_file(path=str(p), known_address=str(kp.pubkey()))
    assert result["verified"] is True


# --- FIND-002 (franklin-sol-base-refill impl iteration-2): verify_solana_secret_file's own
# decode-failure path is a THIRD site (alongside franklin_sol_base_refill.py's derive_pubkey
# and build_sign_submit) that consumes the same raw secret material via the same
# keypair_from_secret_string dual-decode helper, and is reached by bridge.py/
# send_to_franklin.py, both of which append to the SAME shared funding-ledger.jsonl -- its
# decode-failure `reason` string must be sanitized exactly like the other two sites.


def test_verify_solana_secret_file_decode_failure_reason_never_contains_secret(tmp_path, monkeypatch):
    """Simulate a decode library whose exception message embeds the raw input it failed to
    parse -- exactly the unresolved risk iteration-1's FIND-003 flagged for solders' own
    decode exceptions ('could not be fully resolved without running solders locally'). Injects
    the fake secret through `verify_solana_secret_file`'s actual failing path (not a tautology)
    by making the real derive step raise with the secret embedded in its message, then asserts
    no substring of it survives into the returned `reason`."""
    import lib.identity as identity

    fake_secret = "TOTALLY_SECRET_VALUE_THAT_MUST_NEVER_APPEAR_IN_ANY_REASON_9876543210"
    p = tmp_path / ".solana-session"
    p.write_text(fake_secret)

    def raising_derive(secret):
        raise ValueError(f"invalid base58 string, raw input was: {secret}")

    monkeypatch.setattr(identity, "derive_solana_pubkey_from_secret", raising_derive)
    result = identity.verify_solana_secret_file(path=str(p), known_address="anything")
    assert result["verified"] is False
    assert fake_secret not in result["reason"]
    assert "ValueError" in result["reason"]
