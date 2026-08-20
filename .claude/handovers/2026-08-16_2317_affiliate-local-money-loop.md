# Affiliate local money loop handover

- SSOT: `docs/affiliate-agent/AFFILIATE-AGENT-SSOT.md`; resume from `Measured planning checkpoint and next TODOs`, then `Remaining autonomous money-loop work — canonical order`.
- Development route: `/Users/anicca/anicca-project/.worktrees/affiliate-life-manager-spec`, branch `docs/affiliate-life-manager-spec`. Verified local starting HEAD/upstream refs were `0888ab4ca`, descended from required base `0a7debb58`; GitHub DNS was unavailable during the planning audit, so remote freshness and both pushes must be rechecked before execution.
- Installed runtime: `/Users/anicca/.local/share/life-manager/affiliate/current` → release `22e8876ad561eef85827a73fa9f34dc534d7e771`; `git diff <installed-release> HEAD -- skills/affiliate` was empty. Any future `skills/affiliate` change requires immutable install and real owner replay.
- Repository decision: one Life Manager implementation at `skills/affiliate/`; no Affiliate-only repo, executor, ledger, `apps/api`, or Railway runtime. Private mutable state stays under `~/.local/state/life-manager/affiliate/`. OSS is the same proven Skill packaged for a clean Mac, never a rewrite.

## Current measured truth

- Six Affiliate launchd plists exist: three keep-alive browser owners and source/composition/money jobs at 600-second intervals. CDP `9324`, `9326`, and `9327` each returned HTTP `200`; authenticated tabs showed ElevenLabs home, one exact Affiliate X status, and Impact home.
- The canonical ledger contains **13 dedicated-link placements**, **11 owned public URLs**, and **28 provider-measured clicks**. Latest click delta is `0`.
- PartnerStack/ElevenLabs is `AUTHENTICATED`; the latest official capture has `commission_row_count=0`, `NO_LIVE_ROWS`, currency display `USD`, tax registration required, and payment-provider selection required. Pending/approved/paid/reversed are therefore zero observed rows. Approved-or-paid net is **USD 0**. Unknown real costs remain unknown.
- Telegram outbox and sent ledger are both 88 rows. The latest sent receipt has a real provider message ID; no pending duplicate is visible.
- Public DNS readback from the audit shell failed, so the existing public receipts were not promoted to fresh public proof. The installed owner must close fresh owned/X readback after repair.

## Current blocker and safe resume

The current failure is **not** `XPostError`. `last-run.json` reports
`PUBLICATION_FAILED / FileNotFoundError` because the allowed owned-publication
checkout `/Users/anicca/anicca-project/.worktrees/affiliate-foundation-prod` is
missing. Two dedicated-link rows have no owned public URL. Historical ambiguous X
effects are already fenced and must never be republished.

The next execution slice is P0: restore/reconcile that checkout through the
existing ownership contract, trigger the existing launchd owner, resume the same
durable jobs, obtain owned and X public readback, and replay without a duplicate.
If a fresh `XPostError` appears, reconcile its exact effect fingerprint before any
publish retry. Do not create a parallel executor or manually publish.

## Ordered route to completion

1. P0: restore the real publication trajectory and close the two non-public rows.
2. E1-H/P1: ingest the first official provider transaction/settlement ID, currency, status and attribution; join one exact placement; replay safely; preserve pending/approved/paid/reversed/reversal lineage; send one natural Telegram receipt.
3. P2: join known real billed costs, preserve unknown, and build the canonical rolling-30-day approved-or-paid net view.
4. P3: turn the existing `@selawmqt` Repost loop into the bounded English Affiliate acquisition arm under one X effect owner; join every credited action through X exposure → owned article → provider click → transaction.
5. P4: execute the admission-dependent three-provider target: HubSpot USD 4,680 gross, Semrush USD 4,200, and ElevenLabs USD 3,621.86 per rolling 30 days. This USD 12,501.86 gross target closes USD 10,000 net only when official approved/paid rows minus observed reversals and known real billed costs prove it. Unapproved providers contribute zero.
6. P5: allocate 80% only from mature approved-net evidence and 20% exploration; turn newly observed failures into bounded same-job `SELF_HEALED` trajectories.
7. P6: continue unattended until the ledger proves at least **USD 10,000 approved-or-paid net in one rolling 30-day period**, after reversals and known real billed costs. Pending, estimates, clicks, screenshots, tests, mocks, dry runs, model output, and unknown costs never count.
8. P7: only after local proof, ship the same `skills/affiliate/` as a secret-free one-command macOS install with verifier, update/rollback/uninstall, redacted fixtures, and one scratch-Mac unattended reproduction. Public language never guarantees that users can “print money.”

This handover records a planning-only turn. No harness repair, owner kickstart,
manual publication, provider write, or ledger mutation was performed.

Fresh `@selawmqt:9326` read-only revalidation of X's canonical Article route
returned `Page not found` with zero editor controls. This is a current capability
observation, not a permanent claim; Writer's working X Article belongs to the
separate `@diceai0` identity and is not proof for the Affiliate account.
