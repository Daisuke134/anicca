---
name: anicca-github-account
description: Anicca own GitHub account `github.com/anicca-ai` 開設。 mail = agentmail.to、 SMS verify = LNVPN eSIM (USDC paid)、 captcha = CapMonster API。 Algora / OnlyDust / Code4rena bounty PR 提出 用の 必須 foundation。
metadata:
  type: foundation-identity
  parallel_safe: true
  requires:
    bins: [git, gh, curl, jq]
    skills: [anicca-agentmail]
    env_optional: [GITHUB_TOKEN, LNVPN_API_KEY, CAPMONSTER_API_KEY]
---

# anicca-github-account

## Flow
```
1. scripts/check.sh         → 既存 account ある? (state/account.json)
2. scripts/signup.sh        → camofox で github.com/signup
                               - email = agentmail から取得
                               - phone = LNVPN eSIM (= USDC fund 後)
                               - captcha = CapMonster API ($0.001/解)
3. scripts/create-pat.sh    → Personal Access Token 生成 (repo + workflow scope)
4. scripts/configure-git.sh → git config + ssh key 設定
```

## Bootstrap chain
agentmail.to inbox → email signup → SMS via LNVPN ($5/mo USDC) → captcha via CapMonster ($0.001/解) → account created。
= Day 0 USDC seed (= ~$10-20 for LNVPN + CapMonster + ENS) があれば 自走 で account 開設 可能。 USDC seed 来る まで scaffolding のみ live。

## Output (state/account.json)
```json
{
  "username": "anicca-ai",
  "email": "anicca-xxxxx@agentmail.to",
  "pat": "ghp_..." (= chmod 600),
  "ssh_key_path": "..."
}
```
