#!/usr/bin/env python3
# Sign a newborn child's FIRST telemetry heartbeat (EIP-191 personal_sign), byte-identical to the
# contract the live /.netlify/functions/telemetry endpoint verifies (telemetry-verify.js verifyMessage,
# canonicalMessage field ORDER). Signing with the child's OWN key makes signer==id, so the child shows
# up on the dashboard under its own (parent-distinct) address.
#
# Reads the child private key from env CHILD_PRIVKEY (NEVER an argv/log). Emits {"message","signature","id"}
# JSON to stdout. Fail-closed: a missing key or signing error exits non-zero with no output.
import json
import os
import sys

try:
    from eth_account import Account
    from eth_account.messages import encode_defunct
except ImportError:
    sys.stderr.write("sign-telemetry: python eth_account not installed — cannot sign child telemetry\n")
    sys.exit(1)

priv = os.environ.get("CHILD_PRIVKEY", "").strip()
if not priv:
    sys.stderr.write("sign-telemetry: CHILD_PRIVKEY env missing\n")
    sys.exit(1)

host = os.environ.get("CHILD_HOST", "do")
geo = os.environ.get("CHILD_GEO", "US")
now = int(os.environ.get("CHILD_TS", "0")) or int(__import__("time").time())

try:
    acct = Account.from_key(priv)
except Exception as e:  # noqa: BLE001
    sys.stderr.write(f"sign-telemetry: invalid CHILD_PRIVKEY: {e}\n")
    sys.exit(1)

# Field ORDER is load-bearing: the verifier recovers the signer from the verbatim string and the genesis
# client serializes in EXACTLY this order. A newborn runs on the free/BYOK tier until it earns its way up.
payload = {
    "id": acct.address.lower(),
    "ts": now,
    "host": host,
    "geo": geo,
    "model_live": "auto",
    "model_tier": "free",
    "net_worth_usd": 0,
    "revenue_mo_usd": 0,
    "burn_day_usd": 0,
    "runway_days": 999,
    "status": "alive",
}
# match JS JSON.stringify (no spaces, insertion order preserved by dict)
message = json.dumps(payload, separators=(",", ":"))
try:
    signed = Account.sign_message(encode_defunct(text=message), private_key=acct.key)
except Exception as e:  # noqa: BLE001
    sys.stderr.write(f"sign-telemetry: signing failed: {e}\n")
    sys.exit(1)

sig = signed.signature.hex()
if not sig.startswith("0x"):
    sig = "0x" + sig

sys.stdout.write(json.dumps({"message": message, "signature": sig, "id": payload["id"]}))
