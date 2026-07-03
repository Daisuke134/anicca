#!/usr/bin/env python3
"""Print the ON-CHAIN Base USDC balance (decimal string) for an address. Exit 1 on any failure.
Usage: usdc-balance.py 0xADDRESS   [env: BASE_RPC_URL]"""
import json
import os
import sys
import urllib.request

USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
RPC = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")

def main():
    addr = sys.argv[1].lower().replace("0x", "").rjust(64, "0")
    body = {"jsonrpc": "2.0", "id": 1, "method": "eth_call",
            "params": [{"to": USDC, "data": "0x70a08231" + addr}, "latest"]}
    req = urllib.request.Request(RPC, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "User-Agent": "anicca-spawn/1.0"})
    r = json.load(urllib.request.urlopen(req, timeout=30))
    if "result" not in r:
        print(f"usdc-balance: rpc error: {r}", file=sys.stderr)
        sys.exit(1)
    print(f"{int(r['result'], 16) / 1e6:.6f}")

if __name__ == "__main__":
    main()
