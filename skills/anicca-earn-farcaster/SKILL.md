---
name: anicca-earn-farcaster
description: Warpcast (Farcaster) で Anicca own voice で 1-3 cast/day、 tip 受取 ($1-100/cast)。 wallet sign で identity 完結、 KYC ZERO。 Felix / Kelly Claude が 同 channel に 居る = Anicca も そこで 立つ。
metadata:
  type: earn
  spec: ANICCA_TRUE_AUTONOMY_SPEC.md §2A Farcaster (Warpcast) tip
  parallel_safe: true
  expected_revenue: $1-100 / cast, $20-500/mo
  requires:
    bins: [node, curl, jq]
    skills: [anicca-wallet]
    env_optional: [WARPCAST_BEARER, NEYNAR_API_KEY]
---

# anicca-earn-farcaster

## なぜ
Farcaster = decentralized social、 identity = wallet sign で create (KYC ZERO)、 Anicca own FID = anicca.eth。 Tip economy: Warps / Degen / USDC、 自律 agent (Felix / Kelly Claude / Bankr) が 既に 居る community。 投稿 → tip 受領 = 純 on-chain inbound。

## Flow
```
1. scripts/check.sh           → state/fid.json 既存?
2. scripts/register-fid.sh    → 初回: Hub API で FID + signer key 登録 (wallet sign)
                                └ output: FID + username "anicca"
3. scripts/daily-cast.sh      → heartbeat が 1-3 cast/day fire
                                ├ topic: own day + dharma + tech + earn updates
                                ├ length: 320 char hard limit
                                ├ embed: 画像 (anicca-earn-zora art) or x402 link
                                └ post via Warpcast / Neynar API
4. scripts/reply-thread.sh    → mentions に reply (= engagement loop)
5. scripts/poll-tips.sh       → Neynar API で per-cast tip 集計
                                → state/tips.jsonl 追記
6. scripts/promote-other-skills.sh
                              → /pdf, /build, Zora mint の link を 自然 に embed
```

## Cast guidelines (Anicca own voice, HARD RULE #18)
- 一人称 = Anicca、 「アニッチャ」 pronunciation note は profile 固定
- "on behalf of Daisuke" 禁止 (= MEMORY HARD RULE)
- bookmark できる粒度 (CLAUDE.md 0.18 useful + clone-don't-template)
- account-history 14d anti-repeat
- structural pattern は pattern-x.jsonl から pick、 verbatim 借用禁止

## Output (state/tips.jsonl)
```json
{"ts":"2026-06-01T...","cast_hash":"0x...","tipper":"@user","amount_usdc":2.5,"asset":"USDC"}
```

## Verify (HARD RULE #8)
- warpcast.com/anicca に cast visible (curl + Read で 文面確認)
- chain explorer で Anicca wallet inbound tip tx
- state/tips.jsonl 累計 > 0
- account-history.jsonl で 14日 重複 0 件

## Verify (HARD RULE #18 no-human-in-loop)
- never ask Dais "投稿 文面 OK?" — Anicca own voice + recursive-improver で 自前採点
- never ask user "今日 投稿 する?" — heartbeat 自動 fire
- mentions reply も Anicca が 自動判断、 confirm 求めない
- tip 受領 announcement も 自動 post、 「報告 して いい?」 禁止
