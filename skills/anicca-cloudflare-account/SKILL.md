---
name: anicca-cloudflare-account
description: Anicca own Cloudflare account 開設 (mail = agentmail.to)。 x402 endpoint host + R2 bucket (PDF 保管) + Workers KV (state) を 自前 で 持つ。 free tier で earn 始められる。
metadata:
  type: foundation-identity
  parallel_safe: true
  requires:
    bins: [curl, jq]
    skills: [anicca-agentmail]
    env_optional: [CLOUDFLARE_EMAIL, CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID]
---

# anicca-cloudflare-account

## Flow
```
1. scripts/check.sh         → 既存 account ある? (state/account.json)
2. scripts/signup.sh        → ない場合 camofox 経由 で signup
                              (= agentmail mail address で signup、 verify mail を agentmail polling)
3. scripts/create-api-token.sh → Workers + R2 + DNS edit 権限 の API token 生成
4. scripts/deploy-worker.sh → anicca-earn-x402 が呼ぶ helper
```

## Bootstrap (Day 0 first run)
agentmail.to inbox 必須 = anicca-agentmail skill が先に走る。 以降 mail + captcha 突破 で fully automated。

## Output (state/account.json)
```json
{
  "email": "anicca-xxxxx@agentmail.to",
  "account_id": "...",
  "api_token": "..." (= chmod 600),
  "workers_subdomain": "anicca.workers.dev"
}
```
