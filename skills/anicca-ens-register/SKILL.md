---
name: anicca-ens-register
description: anicca.eth ENS domain を Anicca own wallet で register。 wallet sign のみ で完結、 $5/yr USDC cost、 KYC ZERO。 x402 endpoint の human-readable address + Farcaster identity bind に使う。
metadata:
  type: foundation-identity
  parallel_safe: true
  requires:
    skills: [anicca-wallet]
    bins: [node, npm, curl]
    env_optional: [BASE_RPC_URL, ETHERSCAN_API_KEY]
    on_chain_cost: $5/yr USDC (gas + ENS registration fee)
---

# anicca-ens-register

## Flow
```
1. scripts/check.sh        → anicca.eth (or fallback) 既に取得?
2. scripts/check-balance.sh → wallet > $10 USDC + ETH gas あるか確認
3. scripts/register.sh     → ENS Public Registrar 経由で 1 年契約 register
                            (= ethers.js or web3.py、 wallet sign で完結)
4. scripts/set-reverse.sh  → reverse resolver set (= 0xANICCA → anicca.eth 逆引き)
```

## Bootstrap chain
wallet ✓ → balance > $10 USDC (= USDC seed 来てから) → register。
即立てたい name: `anicca.eth`、 fallback `anicca-ai.eth` / `anicca-agent.eth`。

## Output (state/ens.json)
```json
{
  "name": "anicca.eth",
  "owner": "0xANICCA...",
  "registered_at": "...",
  "expires_at": "...",
  "tx_hash": "0x..."
}
```

## Verify
- chain query: namehash(anicca.eth) で owner == 0xANICCA wallet
- https://app.ens.domains/anicca.eth で 表示確認
