# earn/bounty slot — daily Algora bug-bounty money loop (2026-06-30, VCSDD, builder=main agent)

EARN-3 (renamed from audit). Earn real $ EVERY day by doing Algora GitHub bounties: pick ONE genuinely-open
bounty → fix it → PR → TRACK the PR thread daily until MERGED → payout. The TRACK loop (not one-off) is the
whole point — Dais's past bounty attempts failed because he didn't track/iterate PRs to merge.

## Why Algora (VERIFIED 2026-06-30)
Of all code-bounty platforms, Algora (algora-pbc GitHub bot) is the ONE live, paid-on-merge survivor
(OnlyDust closed, Gitpay frozen, Gitcoin/Polar/Replit pivoted, Clanker=fake-token). `gh search` shows ~38-48
open funded issues. Real money via Stripe → bank/Wise/crypto. Claim = comment `/attempt #N`; the PR is the claim.

## North star
`done = a bounty PR we authored gets MERGED and the payout lands (real external USDC/fiat), with the loop
having TRACKED it there.` record-earn (INV-7) counts only the real inflow; discover/attempt/PR = earn 0.

## The daily loop (each piece no-human except the one honest gate)
```
① DISCOVER  gh api search commenter:algora-pbc state:open → state/bounties.json (keep-prior on empty)
② ★ PER-BOUNTY GATE ★ (the drizzle#1188 lesson — Algora "Open" lists STALE bounties):
     a. funder NOT withdrawn — scan issue comments for "removing the bounty"/withdrawal
     b. NO existing open PR already doing it — `gh pr list` on the repo for the issue ref
     c. fix NOT previously-closed / architecturally-blocked — check closed PRs + maintainer notes
     d. agent-doable + mergeable — small, well-scoped (type bug, null-check, doc, test), not a redesign
     → attempt ONLY a bounty that passes ALL four. Thin intersection → pick ONE carefully, never spray.
③ CLAIM     `/attempt #N` with a concrete plan
④ FIX (VSDD) fork → RED (failing test) → GREEN (minimal fix) → local type/test pass → PR (Closes #N)
⑤ TRACK     bounty-core polls `gh pr view --json reviews,state,comments` DAILY → iterate on reviewer
            change-requests → push → repeat until MERGED (state/attempts.jsonl tracks each open PR)
⑥ PAYOUT    merge → algora-pbc reward → Stripe Connect KYC (one-time, the one human-ish gate; crypto
            payout if offered) → record-earn (INV-7) → ledger → dashboard
```

## Earn-core (clone clip pattern, sonnet)
- run.sh: EARN_MODE=discover|attempt|track (built: discover + track; attempt-gate = TODO).
- bounty-cli.sh (daily core: discover→gate→attempt ONE fresh bounty; + frequent track of open PRs) + healthcheck launchd.
- Multiple open PRs tracked in parallel (merges take days) → attempt daily + track all → steady inflow.

## Honest expectations
Bounties are $25-500, competitive (multiple agents per issue), and the fresh×uncontested×payable×mergeable
×agent-doable intersection is THIN. Not passive income — a careful "pick one good one, do it well, track to
merge" game. Stripe-KYC is the withdrawal gate (one-time). This is the realest agent→USD path we verified.

## Status / TODO (VCSDD: spec→RED→GREEN→adversary→no-mock E2E→my verify)
- DONE: rename audit→bounty; discover (38 real open, gh-verified, keep-prior guard); track (poll PRs).
- DONE (lesson): drizzle#1188 attempt → subagent correctly opened NO PR (dead funder + dup PR #5605 +
  rejected breaking change) → proved the verify-first discipline + the need for the GATE.
- TODO-1: implement the PER-BOUNTY GATE (②a-d) in run.sh `attempt` mode (deterministic checks via gh).
- TODO-2: run the loop on ONE gate-passing fresh bounty → /attempt + real PR (E2E side-effect = live PR).
- TODO-3: bounty-cli core + healthcheck (daily attempt + track), like clip/affiliate.
- TODO-4: track to MERGE → payout → record-earn (multi-day; the loop monitors).
DONE = a gate-passed bounty PR merged + payout recorded. "PR opened" ≠ done; "merged + paid" = done.
