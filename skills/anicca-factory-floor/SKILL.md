---
name: anicca-factory-floor
description: factoryfloor.dev (= agent product tracker) に Anicca own entry を PR で register。 Anicca の wallet address + earning sources + revenue を 公開 ledger 化 → Felix / Kelly Claude と 同 leaderboard。
metadata:
  type: foundation-identity
  parallel_safe: true
  requires:
    skills: [anicca-wallet, anicca-github-account]
    bins: [git, gh, jq]
---

# anicca-factory-floor

## Flow
```
1. scripts/check.sh   → 既に registered?
2. scripts/build-entry.sh → AGENTS.md entry を生成
3. scripts/submit-pr.sh   → fork factoryfloor repo, add entry, PR open
4. scripts/sync.sh    → wallet balance + revenue を 自前 dashboard JSON で公開
```

## Entry template (AGENTS.md addition)
```json
{
  "name": "Anicca",
  "description": "Autonomous Buddhist AI — earns via x402 + Algora bounties, redistributes 10% to verified humans",
  "x_handle": "@anicca_agent (= TBD)",
  "ens": "anicca.eth",
  "wallet": "0xANICCA...",
  "earning_sources": ["x402 endpoint", "Algora bounties", "Zora NFT", "Farcaster tips"],
  "tech_stack": ["OpenClaw", "Claude API", "x402-typescript", "USDC on Base"],
  "merchant_revenue_url": "https://aniccaai.com/dashboard.json",
  "chain": "Base",
  "status": "live",
  "open_source": true,
  "repo": "https://github.com/Daisuke134/anicca-oss"
}
```

## Verify
- PR URL を state/pr.json に保存
- merged 後 factoryfloor.dev で Anicca 表示確認
