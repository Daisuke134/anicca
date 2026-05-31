---
name: anicca-earn-build-x402
description: Custom app build via x402 POST /build endpoint ($50-2000)。 顧客 が 仕様 を POST + USDC pay → Anicca が Claude + subagent で build → GitHub repo deliver。 顧客 が 自分の App Store / Stripe に 出す = Anicca は コード のみ 渡す = Anicca KYC ZERO。
metadata:
  type: earn
  spec: ANICCA_TRUE_AUTONOMY_SPEC.md §2A Custom app build via x402
  parallel_safe: true
  expected_revenue: $50-2000 / build, $200-4000/mo
  requires:
    bins: [git, gh, claude, jq, node]
    skills: [anicca-wallet, anicca-earn-x402, anicca-github-account]
    env_optional: [ANTHROPIC_API_KEY, GITHUB_TOKEN]
---

# anicca-earn-build-x402

## なぜ
Kelly Claude (@KellyClaudeAI) 1次 source = AI agent が "paid app-building service" を 提供して revenue 取ってる 既存実例。 Anicca が 同 path を 純 on-chain で やる: x402 で intake、 USDC 受領、 GitHub で deliver。

**顧客 が 自分 で 出す = Anicca KYC ZERO**: コード を GitHub repo に push して 渡すだけ。 顧客 が 自分の Apple Developer / Stripe / hosting に deploy する。 Anicca は インフラ持たない = automation-only。

## Flow
```
1. scripts/check.sh             → queue/*.json で pending intake?
2. scripts/intake.sh            → x402 POST /build payload を queue/<reqid>.json に保存
                                  {spec_md, repo_name, price_paid, payer_wallet, tx_hash}
3. scripts/validate.sh <reqid>  → x402 tx_hash を Base chain で 確認 (USDC inbound 済?)
                                  ├ confirmed → status=paid
                                  └ pending  → 30 min retry
4. scripts/build.sh <reqid>     → Claude + subagent で:
                                  ├ gh repo create anicca-ai/<repo_name>
                                  ├ scaffold (Next.js / iOS Swift / Python / etc.)
                                  ├ implement spec_md
                                  ├ test (npm test / pytest)
                                  └ git push
5. scripts/deliver.sh <reqid>   → gh repo に payer_wallet ENS owner を collaborator 追加
                                  → x402 callback URL に "ready: <repo_url>" POST
                                  → state/builds.jsonl 追記
6. scripts/sla-watcher.sh       → 24-72h 超過 build = warning log、 refund logic は無し (= deliver 厳守)
```

## Pricing tiers (Anicca 自動判定 by spec_md word count + complexity)
| tier | 価格 | scope |
|---|---|---|
| micro | $50-100 | landing page / single script / cron job |
| small | $200-500 | full-stack MVP (auth + DB + 3 page) |
| medium | $800-1500 | iOS app skeleton / API + dashboard |
| large | $2000+ | multi-service + tests + CI |

## Output (state/builds.jsonl)
```json
{"ts":"2026-06-01T...","reqid":"r-001","tier":"small","price_usdc":300,"repo":"anicca-ai/customer-foo","payer":"0x...","status":"delivered","build_hours":3.2}
```

## Verify (HARD RULE #8)
- queue/<reqid>.json の tx_hash を chain explorer で 着金 確認
- gh repo <repo_name> exists + commits 数 > 1 + tests green (CI badge)
- callback URL に POST 成功 (= HTTP 200 receipt)
- state/builds.jsonl 累計 USDC > 0

## Verify (HARD RULE #18 no-human-in-loop)
- never ask install user "build しても いい?" — paid intake = 即着手
- never ask Dais "this spec OK?" — Claude が 解釈 + 不明点は spec assume comment in README
- 顧客 への 質問 は build 中 1 回 だけ x402 callback で "clarification" POST、 返事 なければ best-effort で ship
- intake URL 公開 (Farcaster / X) も Anicca own voice、 install user 経由 禁止
