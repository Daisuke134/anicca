#!/usr/bin/env python3
"""Print the REAL on-chain Base USDC balance (decimal string) of an address. Fail => exit 1.
Usage: usdc-balance.py 0xADDRESS   (env: BASE_RPC_URL)
Deterministic tool — reads a number, decides nothing (spawn-auto-seed REQ-2).
"""
import json, os, sys, urllib.request

USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # Base USDC

def main():
    addr = sys.argv[1].lower().replace("0x", "")
    rpc = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_call",
                       "params": [{"to": USDC, "data": "0x70a08231" + addr.rjust(64, "0")}, "latest"]}).encode()
    req = urllib.request.Request(rpc, data=body, headers={"Content-Type": "application/json", "User-Agent": "curl/8.6.0"})
    r = json.load(urllib.request.urlopen(req, timeout=20))
    print(int(r["result"], 16) / 10**6)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"usdc-balance: {e}", file=sys.stderr)
        sys.exit(1)
