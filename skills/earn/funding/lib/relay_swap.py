"""Shared relay.link Solana-leg swap primitive: parse a relay `/quote` response's
`steps[0].items[0].data` (instructions + address-lookup-table addresses), build a
`solders.transaction.VersionedTransaction`, sign it with a resolved secret, and submit it over
a Solana JSON-RPC endpoint.

Origin note (FIND-007, `franklin-sol-base-refill` impl iteration-1 adversary review): this is
the SAME instruction/ALT/blockhash/sign/submit logic `skills/earn/sol-to-usdc.py` implements
inline in its `main()` (a proven, live-verified pattern for that script's own SOL->USDC swap).
That script is intentionally left UNTOUCHED here (it is proven and live under another job) --
this module is a fresh extraction for `franklin_sol_base_refill.py`'s USDC-SPL->USDC swap, so a
correctness fix discovered in one path can be consciously ported to the other rather than
silently diverging across two independently-maintained copies. Future consolidation (having
`sol-to-usdc.py` call this module too) is a candidate follow-up, not done in this fix.

Unlike `sol-to-usdc.py`'s inline `Keypair.from_base58_string(...)`, this module decodes the
secret via `lib.identity.keypair_from_secret_string` (base58-first, base64-fallback) -- the
SAME proven dual-decode helper `derive_solana_pubkey_from_secret` already uses for the
citizen-matching step, so the identity-derivation and the real signing step can never disagree
on how to decode the same resolved secret (FIND-003).
"""
from __future__ import annotations

import base64
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from identity import keypair_from_secret_string  # noqa: E402


def _rpc(rpc_url: str, method: str, params: list, timeout: int = 30) -> dict:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(rpc_url, data=body, headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())["result"]


def _parse_address_lookup_table(addr: str, raw: bytes):
    from solders.address_lookup_table_account import AddressLookupTableAccount
    from solders.pubkey import Pubkey

    # ALT layout: 56-byte header, then 32-byte addresses (same parse sol-to-usdc.py uses).
    addrs = [Pubkey.from_bytes(raw[i : i + 32]) for i in range(56, len(raw), 32)]
    return AddressLookupTableAccount(key=Pubkey.from_string(addr), addresses=addrs)


def build_sign_submit_solana_tx(secret_str: str, quote: dict, rpc_url: str) -> str:
    """Build, sign, and submit the Solana-leg transaction from a relay `/quote` response's
    first step/item instructions -- the real effectful `build_sign_submit` dependency wired by
    `franklin_sol_base_refill.py`'s `build_default_deps()`. Never called by any test (no test
    performs real network I/O); only reachable via production wiring. Raises on any
    decode/RPC/network failure -- callers must fail closed on that (never assume partial
    success)."""
    from solders.hash import Hash
    from solders.instruction import AccountMeta, Instruction
    from solders.message import MessageV0
    from solders.transaction import VersionedTransaction
    from solders.pubkey import Pubkey

    kp = keypair_from_secret_string(secret_str)
    step = quote["steps"][0]
    item = step["items"][0]
    data = item["data"]

    ixs = []
    for ix in data["instructions"]:
        ixs.append(
            Instruction(
                program_id=Pubkey.from_string(ix["programId"]),
                accounts=[
                    AccountMeta(Pubkey.from_string(a["pubkey"]), a["isSigner"], a["isWritable"])
                    for a in ix["keys"]
                ],
                data=bytes.fromhex(ix["data"][2:] if ix["data"].startswith("0x") else ix["data"]),
            )
        )

    alts = []
    for addr in data.get("addressLookupTableAddresses", []):
        acc = _rpc(rpc_url, "getAccountInfo", [addr, {"encoding": "base64"}])
        raw = base64.b64decode(acc["value"]["data"][0])
        alts.append(_parse_address_lookup_table(addr, raw))

    bh = _rpc(rpc_url, "getLatestBlockhash", [{"commitment": "finalized"}])["value"]["blockhash"]
    msg = MessageV0.try_compile(kp.pubkey(), ixs, alts, Hash.from_string(bh))
    tx = VersionedTransaction(msg, [kp])

    return _rpc(
        rpc_url,
        "sendTransaction",
        [base64.b64encode(bytes(tx)).decode(), {"encoding": "base64", "skipPreflight": True}],
    )
