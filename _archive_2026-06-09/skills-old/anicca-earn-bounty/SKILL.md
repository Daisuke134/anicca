---
name: anicca-earn-bounty
description: ★ PRIMARY earn skill。 Algora / OnlyDust / Replit / Code4rena から daily で bounty を scan → feasibility 判定 → fork+fix+PR → AutoPay USDC 受領。 Anicca wallet に直接入金、 KYC ZERO、 重 inference は heartbeat 内で Claude/DeepSeek が判断。
metadata:
  type: earn-primary
  spec: ANICCA_TRUE_AUTONOMY_SPEC.md §2A
  parallel_safe: true
  expected_revenue: $50-500 month 1, $500-3000 month 6
  requires:
    skills: [anicca-wallet, anicca-github-account]
    bins: [git, gh, curl, jq, python3]
    env_optional: [GITHUB_TOKEN, ANTHROPIC_API_KEY]
---

# anicca-earn-bounty

## なぜ ★PRIMARY
- 唯一 「即着手 + 確実 month-1 USDC inbound」 path。 Algora が AutoPay USDC on PR merge、 KYC ZERO。
- AI agent (Claude $20 budget で 完了 済) の 受領 実績 確定 (= 我々 後発、 path proven)。
- daily 50-200 active bounties = volume ある。

## Sources (優先順)
| platform | URL | rail | 単価 | settle |
|---|---|---|---|---|
| Algora | algora.io/bounties | GitHub PR | $10-500 | USDC AutoPay on merge (Base) |
| OnlyDust | onlydust.com | GitHub PR | $50-5000 | USDC |
| Replit Bounties | replit.com/bounties | Replit IDE | $5-500 | Cycles → ⚠️ KYC for cashout |
| Code4rena | code4rena.com | audit submit | $1k-50k | USDC direct |
| Sherlock | sherlock.xyz | audit submit | $500-50k | ETH/USDC |

## Flow (heartbeat P2、 daily 1-3 件 試行)
```
1. scripts/scan.sh        → Algora + OnlyDust + Code4rena から open bounties 取得
2. scripts/select.sh      → Claude API で feasibility 判定:
                            - language match (Python/TS/Go/Solidity)
                            - budget >= $10
                            - description complexity = mid 以下
                            - skill match (= existing OpenClaw skill catalog から類推)
                          → top 1 件 pick
3. scripts/solve.sh       → fork repo → branch fix/<bounty-id> → Claude が code → test → push
4. scripts/submit.sh      → PR open + body に `/claim #<issue> $<amount>` comment
                          → wait for review/merge
5. scripts/log.sh         → data/bounty-history.jsonl に append
```

## Heuristics
- 1 件 失敗 = 即 next 件、 同 bounty に 24h cooldown
- maintainer 反応 0 が 7 日 → close PR + history archive
- 連勝 = 同 repo の next bounty 優先
- Algora `/bounty` の前に `/attempt` で claim 表明 (= 重複作業 防止)

## Output (data/bounty-history.jsonl)
```json
{"ts":"...","platform":"algora","bounty_id":"...","amount":50,"status":"pr_opened|merged|rejected","pr_url":"...","tx_hash":"0x..."}
```

## Verify (HARD RULE #8)
- data/bounty-history.jsonl に 累計 USDC > 0 (= 第 1 win 後)
- chain explorer で Anicca wallet inbound tx 確認 → AutoPay 動作
- 月収 USDC report を anicca-payout に渡す

## Verify (HARD RULE #18 no-human-in-loop)
- maintainer に reply は OK だが install user / Dais への "確認 ください" 禁止
- bounty が KYC 要求 (= Replit Cycles cashout 等) なら skip + warn 内部 log のみ
