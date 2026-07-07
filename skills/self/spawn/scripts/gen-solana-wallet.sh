#!/usr/bin/env bash
# Generates a fresh Solana (ed25519) keypair via solana-keygen, emits {address, private_key, public_key}
# JSON to stdout. IMPORTANT: caller MUST redirect to a 600-perm file. NEVER let this stdout reach a log.
# private_key is the base58 encoding of the raw 64-byte secret key (seed+pubkey) solana-keygen's own
# JSON keypair file stores as a byte array -- the same format that CLI's own `solana-keygen pubkey
# <file>` can independently re-derive an address from, matching gen-wallet.sh's own cross-check
# discipline for its EVM counterpart.
set -euo pipefail
command -v solana-keygen >/dev/null 2>&1 || { echo "gen-solana-wallet: solana-keygen missing" >&2; exit 1; }
NODE="$(command -v node)"
JQ="$(command -v /opt/homebrew/bin/jq || command -v jq)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

KEYPAIR_FILE=$(mktemp)
trap 'rm -f "$KEYPAIR_FILE"' EXIT
solana-keygen new --no-bip39-passphrase --force --silent -o "$KEYPAIR_FILE" >/dev/null 2>&1

ADDRESS="$(solana-keygen pubkey "$KEYPAIR_FILE")"

# Base58-encode the raw 64-byte secret key array via bs58 -- the SAME dependency this repo already
# ships (node_modules/bs58), never a bespoke re-implementation.
PRIVATE_KEY="$("$NODE" -e '
  const fs = require("fs");
  const path = require("path");
  const { createRequire } = require("module");
  const req = createRequire(path.join(process.argv[1], "package.json"));
  const bs58 = req("bs58");
  const bytes = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
  process.stdout.write(bs58.encode(Buffer.from(bytes)));
' "$REPO_ROOT" "$KEYPAIR_FILE")"

"$JQ" -n \
  --arg address "$ADDRESS" \
  --arg private_key "$PRIVATE_KEY" \
  --arg public_key "$ADDRESS" \
  '{address:$address, private_key:$private_key, public_key:$public_key}'
