#!/usr/bin/env python3
# gmx-referral-register.py — REUSABLE recipe: any Anicca agent/loop registers its own GMX referral
# code on-chain (Arbitrum) and gets a wallet-native crypto affiliate rail (KYC-free, INV-11).
# Proven live 2026-07-14: code "aniccaai" tx 0xbc7303ec... from founder wallet 0x810f6d (gas ~$0.15).
#
#   python3 gmx-referral-register.py --code <code> [--key-file <wallet.json>]
#     <code>     : A-Z a-z 0-9 _ , up to 20 chars (case-sensitive)
#     --key-file : json with {"private_key": "0x.."} (default ~/.anicca-founder/wallet.json).
#                  ★use the AGENT'S OWN wallet (INV-11), never Dais's personal wallet★
#
# Needs: web3.py, and the wallet to hold a little ETH on ARBITRUM for gas (~$0.15 is plenty).
# Verified GMX ReferralStorage (Arbitrum): 0xe6fab3F0c7199b0d34d7FbE83394fc0e0D06e99d
# referral link after register: https://app.gmx.io/#/trade?ref=<code>
import argparse, json, os, sys
from web3 import Web3

ARB_RPC = "https://arb1.arbitrum.io/rpc"
REFERRAL_STORAGE = Web3.to_checksum_address("0xe6fab3F0c7199b0d34d7FbE83394fc0e0D06e99d")
ABI = [
    {"inputs": [{"name": "_code", "type": "bytes32"}], "name": "registerCode", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"name": "", "type": "bytes32"}], "name": "codeOwners", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", required=True, help="referral code (A-Z a-z 0-9 _, <=20 chars)")
    ap.add_argument("--key-file", default=os.path.expanduser("~/.anicca-founder/wallet.json"))
    a = ap.parse_args()
    if not (0 < len(a.code) <= 20 and all(c.isalnum() or c == "_" for c in a.code)):
        print(json.dumps({"ok": False, "error": "invalid code (A-Z a-z 0-9 _, <=20)"})); return

    w3 = Web3(Web3.HTTPProvider(ARB_RPC))
    key = json.load(open(a.key_file))["private_key"]
    acct = w3.eth.account.from_key(key)
    bal = w3.eth.get_balance(acct.address)
    c = w3.eth.contract(address=REFERRAL_STORAGE, abi=ABI)
    code_b = a.code.encode().ljust(32, b"\x00")

    owner = c.functions.codeOwners(code_b).call()
    if int(owner, 16) != 0:
        mine = owner.lower() == acct.address.lower()
        print(json.dumps({"ok": mine, "code": a.code, "owner": owner,
                          "note": "already yours" if mine else "TAKEN by someone else — pick another code",
                          "link": f"https://app.gmx.io/#/trade?ref={a.code}" if mine else None}))
        return
    if bal == 0:
        print(json.dumps({"ok": False, "error": f"wallet {acct.address} has 0 ETH on Arbitrum — fund ~\\$0.30 gas first (INV-11: agent's own funds)"})); return

    tx = c.functions.registerCode(code_b).build_transaction({
        "from": acct.address, "nonce": w3.eth.get_transaction_count(acct.address),
        "gas": 200000, "maxFeePerGas": w3.to_wei(0.2, "gwei"),
        "maxPriorityFeePerGas": w3.to_wei(0.01, "gwei"), "chainId": 42161})
    signed = acct.sign_transaction(tx)
    h = w3.eth.send_raw_transaction(signed.raw_transaction)
    r = w3.eth.wait_for_transaction_receipt(h, timeout=120)
    txh = "0x" + h.hex().lstrip("0x")
    print(json.dumps({
        "ok": r.status == 1, "code": a.code, "wallet": acct.address,
        "tx": txh, "block": r.blockNumber, "gasUsed": r.gasUsed,
        "arbiscan": f"https://arbiscan.io/tx/{txh}",
        "referral_link": f"https://app.gmx.io/#/trade?ref={a.code}",
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
