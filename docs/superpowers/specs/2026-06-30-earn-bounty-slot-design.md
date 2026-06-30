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

## UPDATE 2026-06-30: GATE implemented + verified (TODO-1 done)
run.sh `gate` mode does (a) funder-not-withdrawn (b) no-existing-PR (c) real-repo≥50★ + excludes
test/throwaway/farm repos. VERIFIED: top-25 open Algora bounties → only **1** passes (Scottcjn/Rustchain
#2239, 460★). Reality: the genuinely fresh×uncontested×real intersection is ~1 right now. NEXT (TODO-2):
deep-verify that survivor is REAL money (not a Clanker/token farm) + agent-doable, then /attempt + PR; if
fake/blocked, report honestly (like drizzle) — never force.

## UPDATE 2026-06-30 (2): Rustchain#2239 = token-farm; current real-USD inventory = 0
The 1 gate-survivor was deep-verified FAKE: RTC self-token (not USD), algora.io 404, AutoJanitor bot
auto-merge, AI-agent farm. Added gate filter (d) USD-not-token. ★ HONEST: top-25 open Algora bounties →
0 real-payable-uncontested-agent-doable right now. ★ The verify-first discipline caught 3 dead/fake leads
in a row (47-live=closed, drizzle=dead-funder, Rustchain=token) — this is the system WORKING, not failing.
The bounty loop + gate are built + correct; they will attempt the moment a real USD bounty appears. Inventory
(like clip per-view campaigns) is demand-thin. NEXT: bounty-cli core (daily discover+gate; attempt only when
a survivor passes ALL gates incl. USD) + widen discover beyond Algora if a second real platform emerges."
git add docs/superpowers/specs/2026-06-30-earn-bounty-slot-design.md
git commit -q -m "spec(earn/bounty): UPDATE-2 — Rustchain=token-farm, real-USD inventory=0 now; verify-first caught 3 fakes; loop+gate correct, demand-thin"
git pull --rebase origin main 2>&1 | tail -1; git push 2>&1 | tail -1
## UPDATE 2026-06-30 (3): keystatic#340 withdrawn; full-48 gate → 0 real; verify caught 4/4
Full gate over all 48 open Algora bounties → 1 real-repo survivor (keystatic#340) → deep-verify = DEAD
(withdrawn: ~~strikethrough~~ algora comment; community-funded not team; undesigned roadmap, maintainer
declined). Gate upgraded: detect strikethrough-withdrawn + require an ACTIVE algora bounty comment.
★ CONCLUSIVE: current real-payable Algora inventory = 0. Verify-first caught 4/4 fakes (closed/dead/
token/withdrawn) BEFORE any wasted PR. ★ The loop + gate are correct + battle-tested; they will attempt
the moment a genuinely-live USD bounty appears. The honest constraint is DEMAND (no real open bounties
now), not the loop. NEXT: build the back-half anyway (attempt mode + record-earn + bounty-cli core) so
the loop can act autonomously the instant inventory appears; widen sources beyond Algora."
git add docs/superpowers/specs/2026-06-30-earn-bounty-slot-design.md
git commit -q -m "spec(earn/bounty): UPDATE-3 — keystatic withdrawn, full-48 gate=0 real, verify caught 4/4; demand is the constraint not the loop"
git pull --rebase origin main 2>&1 | tail -1; git push 2>&1 | tail -1