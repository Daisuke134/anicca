# earn/video — self-improving faceless-finance money loop

A LOCAL earn slot: one IG account posts a fresh faceless finance short every day, with a crypto-affiliate link in
bio; it self-improves toward MORE MONEY with zero humans in the loop. `run.sh` does ONE bounded transition per wake
(create → warmup(7d, niche) → affiliate-link@day7 → post → record → measure). You (the running agent) are the brain:
deterministic tools live in this dir; every JUDGMENT is yours, expressed in natural language (AI-agnostic — no
hardcoded model/provider, no regex deciding content).

## The loop (what fires each wake)
`bash run.sh` reads slot state and runs the one transition `decide.py` returns. It is idempotent and fail-closed:
warmup advances only on ≥3 REAL distinct niche reels watched; a post is "done" only with a verified `post_url`;
earnings record ONLY on-chain-confirmed USDC to the dedicated wallet. Nothing is ever faked.

## ★ YOUR JOB each wake before a post (the self-improvement) ★
Before today's video is generated, DECIDE the script — and make it BETTER than the last one if results were weak:

1. Read performance: `python3 selfimprove.py summary --handle <h>` → `{total_usdc_earned, recent:[{views,likes,comments,script_hook}], guidance}`.
2. Judge it yourself (no fixed rule):
   - The metric that ULTIMATELY matters is `total_usdc_earned`. Views/likes are the leading indicator.
   - If recent posts got low views/likes, OR earned $0 while getting views → CHANGE something concrete for the
     next script: a sharper hook (first 1.5s), a different money sub-topic, a clearer CTA to the bio link, a
     tighter 25–35s structure. Keep whatever correlated with higher views AND money; drop what didn't.
   - If a hook is working (rising views + money), do MORE of that angle.
3. Write today's script to a file and pass it as `EARN_VIDEO_SCRIPT` to run.sh. The script is plain narration text
   the $0 generator (faceless-money-factory / moneyprinterturbo-style: stock b-roll + TTS + captions) turns into a
   1080×1920 mp4. Always end with a spoken + caption CTA: "link in bio to swap crypto" (the ChangeNOW affiliate).

## Niche & audience (warmup)
Warmup watches REAL finance reels (money hashtags) so the algo learns the niche and the account becomes the target
audience. Niche is config (`EARN_VIDEO_NICHE_TAGS`), not hardcoded judgment — set it to the account's topic.

## Money rail
Bio link = ChangeNOW crypto-affiliate referral (`MONEY_AFFILIATE_URL`). Commissions pay in crypto → withdraw as
USDC (Base) to the DEDICATED receive wallet `~/.cloak/earn-video-wallet.json` (ONLY affiliate money lands there →
clean attribution). `onchain.py` detects inflows; `record_earn` records ONLY on-chain-confirmed USDC. Default $0.

## Files
| file | role |
|---|---|
| `run.sh` | slot entrypoint — one transition/wake (the loop calls this) |
| `decide.py` | pure state machine → which transition |
| `onchain.py` | Base USDC inflow detector + on-chain confirm (real-money gate) |
| `record_earn.py` | INV-7 record gate (verified external USDC only) |
| `metrics.py` | read a post's real views/likes/comments (eval measurement) |
| `selfimprove.py` | record_post / measure_due / performance_summary (the loop's memory) |
| `state_io.py` | atomic state + .bak recovery |
| audit | `~/.cloak/earn-video-audit-<h>.jsonl` — append-only per-wake trail (provably not faked) |

## Scale
This recipe (account + niche warmup + daily faceless short + crypto-affiliate + on-chain eval + self-improve) is
cloneable: spawn more accounts/niches (money, Buddhism/monk, affirmations, app-link) by copying the slot with a new
handle + niche tags + affiliate link. Same loop, different persona. The agent picks the highest-ROI action.
