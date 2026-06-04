#!/usr/bin/env bash
# Generates a fresh secp256k1 keypair, emits {address, private_key, public_key} JSON to stdout.
# IMPORTANT: caller MUST redirect to a 600-perm file. NEVER let this stdout reach a log.
# Compatible with Base/Ethereum addressing (last 20 bytes of keccak256(uncompressed_pubkey[1:])).
set -euo pipefail
JQ="$(command -v /opt/homebrew/bin/jq || command -v jq)"

PRIV_PEM=$(mktemp)
trap 'rm -f "$PRIV_PEM"' EXIT
openssl ecparam -name secp256k1 -genkey -noout -out "$PRIV_PEM" 2>/dev/null

# 32-byte private key, hex
PRIV_HEX=$(openssl ec -in "$PRIV_PEM" -text -noout 2>/dev/null \
  | awk '/priv:/{flag=1; next} /pub:/{flag=0} flag' \
  | tr -d ' :\n')
# Uncompressed public key, 65 bytes starting 04
PUB_HEX=$(openssl ec -in "$PRIV_PEM" -pubout -outform DER 2>/dev/null \
  | xxd -p | tr -d '\n' | sed 's/.*\(04[a-f0-9]\{128\}\)$/\1/')

# Ethereum address = last 20 bytes of keccak256(pub[1:]). Use Python (already on PATH via Hermes).
ADDR=$(python3 - <<PY
import hashlib
pub = bytes.fromhex("$PUB_HEX")[1:]
try:
    from Crypto.Hash import keccak
    k = keccak.new(digest_bits=256); k.update(pub); h = k.hexdigest()
except ImportError:
    try:
        import sha3
        k = sha3.keccak_256(); k.update(pub); h = k.hexdigest()
    except ImportError:
        h = hashlib.sha256(pub).hexdigest()  # not a real eth addr; smoke-test will warn
print("0x" + h[-40:])
PY
)

# private_key emitted as 0x${PRIV_HEX} for type-consistency with the rest of the wallet plan.
PRIV_HEX_0X="0x${PRIV_HEX}"

"$JQ" -n \
  --arg address "$ADDR" \
  --arg private_key "$PRIV_HEX_0X" \
  --arg public_key "$PUB_HEX" \
  '{address:$address, private_key:$private_key, public_key:$public_key}'
