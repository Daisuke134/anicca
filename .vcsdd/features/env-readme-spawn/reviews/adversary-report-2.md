# Adversary Report 2 — env-readme-spawn (fresh-context, read-only)

Verified against `origin/main` HEAD = `d74e888` (README.md, 145 lines). Spec: `.vcsdd/features/env-readme-spawn/specs/spec.md` (DONE 1-5 + ADDENDUM R8-R12). Cross-referenced `docs/superpowers/specs/2026-07-03-anicca-colony-architecture-design.md` §17.1/§35/§38/§41/§43/§44, `gh api repos/BlockRunAI/Franklin/readme`, and on-chain data (polygonscan, tx receipts fetched via firecrawl after blockrun RPC returned payment errors).

## VERDICT: FAIL (1 blocking finding, everything else PASS)

## Original DONE (1-5)

| # | Check | Verdict |
|---|---|---|
| 1 | 3 spawn commands present + Franklin matches `@blockrun/franklin` official README | **PASS** — `franklin setup solana` + `franklin balance` match BlockRunAI/Franklin's own Quick Start (`franklin setup base # or: franklin setup solana`, `franklin balance`) verbatim. |
| 2 | Today's evidence numbers/tx are real, not exaggerated | **FAIL — see CONFIRMED FINDING below.** |
| 3 | 5 self-* + swarm self-experiment + dashboard eval + UBI + works-anywhere all present | **PASS** — self-monitoring/healing/improving/replicating/information-sharing (L102), swarm section (L104-106), dashboard eval (L106, L117), UBI (L3, L99), works-anywhere covered thinly but present ("local or cloud" registering to one dashboard, L61). |
| 4 | MISSION matches §38 correction (financial independence only requirement, model auto, no forced-free) | **PASS** — L38: "Financial independence is the only requirement; each type autonomously chooses its own model (free when idle, frontier when a task or its balance warrants it)." No forced-free language anywhere. |
| 5 | Markdown intact, pushed, readable from origin | **PASS** — 10 fences (even), headings well-formed, readable via `git show origin/main:README.md`. |

## ADDENDUM (R8-R12)

| # | Check | Verdict |
|---|---|---|
| R8 | Type framework unified to one (automaton/Franklin/claude-p), old "2 ways/2 instance types/3 colony types" competing framing gone | **PASS** — grep for `two instance types`, `2 ways to KICKSTART`, `three colony types` → 0 matches. Single "## The three types" section (L36). |
| R9 | No duplicate automaton spawn command across two sections | **PASS** — "Running Anicca"/"Spawn one" headers gone (0 matches). Quick start (claude-p brain) and the automaton type entry share the `git clone`+`install.sh` boilerplate but are different commands for different types, not a literal duplicate. |
| R10 | Earn content reflects reality (PM/SOL/HL trading + cook + redeem), old clip/affiliate/video/gig/tmux language gone | **PASS** — grep for `tmux`, `clip`, `affiliate`, `gig work` → 0 matches. "How it earns" table (L65-77) lists exactly Polymarket/Solana/Hyperliquid/cook. |
| R11 | Personal residue removed (Dais's bank, PayPay, Binance/GMO Aozora Japan-local mermaid) | **PASS** — grep for `Dais's bank`, `PayPay`, `GMO Aozora` → 0 matches. Sole remaining "Binance" mention (L136) is generic exchange advice ("any exchange (Coinbase, Binance, etc.)"), not the flagged personal mermaid diagram. The loop diagram (L82-100) is fully generic ASCII with no Japan-specific institutions. |
| R12 | Dead-simple 30-second kickstart near the top | **PASS** — "## Quick start (30 seconds)" (L20) sits right after "Why this exists", one 3-line copy-paste block using claude-p as the easiest on-ramp. |

## CONFIRMED FINDING (blocking) — honesty regression on the $8.24 claim

The current README (L114, from commit `d74e888`) reads:

> "**Proven live 2026-07-05** — an instance *placed and won* a Polymarket bet on its own (settle tx `0x7662a88b…`, status 0x1) **and realized +$8.24 USDC**. The loop now also **redeems its own wins autonomously** — verified 2026-07-05: it collected a $5.99 win with no human running the command (redeem tx `0xd33b09c8…`, status 0x1)."

Three independently verified facts contradict this:

1. **On-chain: tx `0x7662a88b` is not the $8.24 event.** Fetched the receipt from polygonscan (block 89644078, 2026-07-04): the actual token transfers in that tx are ~$1.01 / ~$0.79 / ~$1.78 / ~$0.01 — a small order match, nowhere near $8.24. The README cites this tx as "evidence" for realizing $8.24 USDC, which it did not produce.
2. **Spec §35 (EARN-1) says the real $8.24 came from three different, uncited redeem txs** (`0x803a4056`/`0x3c502713`/`0x0822b088`, Wimbledon Flavio +3.90 / Morocco +2.99 / Canada-Morocco +1.35 = +8.24). None of these three hashes appear anywhere in the current README.
3. **Spec §35 explicitly confesses that redemption was human-triggered (meddling), not autonomous:** *"redeem を実行したのは team-lead の subagent = 人間/Claude がループに入った = meddling... 金は本物だが「AI 自身が回収」ではない。"* The prior README revision (`eabf17c`, per adversary FAIL2 in §41) correctly disclosed this: *"Collecting the winnings realized +$8.24 USDC (three redeem txs, all status 0x1). Honestly: that first collection was human-triggered — wiring the loop to redeem its own wins autonomously is in progress."* Commit `d74e888` (the very latest, made after the genuinely-autonomous $5.99 redeem in §44) **deleted this disclosure** and replaced it with wording that reads as if the *whole* $8.24 (bet, win, and realization) happened "on its own," under the row heading "First real earnings, no human in the loop."

The $5.99 autonomous-redeem claim is real and correctly verified (on-chain receipt for `0xd33b09c8...`: block 89667011, exact match to spec §44's block number, 5.991763 USDC.e → wallet `0x904B50d2...`). That part is accurate and should stay. But it does not retroactively make the *first* $8.24 collection autonomous, and the README's current wording conflates the two events and drops the honesty caveat that a previous adversary pass had already forced in. This is the exact FAIL2 exaggeration pattern recurring after being "fixed" — a regression, not a new issue.

**Required fix:** keep the $5.99 autonomous-redeem claim (accurate), but for the $8.24 either (a) drop the "settle tx 0x7662a88b" citation entirely since it doesn't evidence that figure, or (b) cite the three actual redeem txs, and in either case restore an explicit note that the first $8.24 collection was human-triggered while the $5.99 collection was the loop acting alone — otherwise "First real earnings, no human in the loop" as a row title is not true of the $8.24 portion.

## Not checked (out of scope per task)
Push/commit/on-chain writes were not performed (read-only). No file was edited other than this report.
