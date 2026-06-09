#!/usr/bin/env bash
# E2E: wallet_lib.load_signer() returns the canonical Anicca address
# WITHOUT printing the private key. Asserts on stdout, then greps for leak.
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

OUT=$(python3 -c "
import sys
sys.path.insert(0, '$SKILL_DIR/scripts')
import wallet_lib
addr, _signer = wallet_lib.load_signer()
print(addr)
")

EXPECTED="0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21"
if [ "$OUT" != "$EXPECTED" ]; then
  echo "FAIL: expected $EXPECTED, got $OUT"; exit 1
fi

# Verify no 0x-hex-64 (private key shape) leaked to stdout
if echo "$OUT" | grep -Eqi '^0x[a-f0-9]{64}$'; then
  echo "FAIL: stdout looks like a 64-hex private key — possible leak"; exit 1
fi
echo "PASS"
