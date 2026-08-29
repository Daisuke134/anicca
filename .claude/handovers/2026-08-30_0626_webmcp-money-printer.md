# WebMCP Money Printer handover

- Spec SSOT: `/Users/anicca/Projects/life-manager-main/.worktrees/webmcp-handover-20260830/docs/superpowers/specs/2026-08-28-webmcp-challenge-winning-contract.md`; remaining order is Section 14 `Submission critical path` and Section 17 `Exhaustive uncertainty register`.
- Product authority: public `main` and Railway worker are exact SHA `cb8c391779c120ba3c8dabe6e80ff5aa96e6bb6d`; `/health` is 200 and capabilities are `money-printer.scout,general-agent.work`.
- Spec branch: `/Users/anicca/Projects/life-manager-main/.worktrees/webmcp-handover-20260830`, `docs/webmcp-handover-20260830`, upstream `origin/docs/webmcp-handover-20260830`, verified spec commit `715cc1dafbeedad31dc40c4e272b1d3b72d73fb3`.
- Do not write the shared worktree `/Users/anicca/Projects/life-manager-main/.worktrees/webmcp-money-printer`; it is clean but remains on merged/deleted branch `fix/webmcp-human-sql-regex` at `254c2ca1b`.
- Current item: close live HumanTask creation/answer/same-job resume. PRs #3114/#3117/#3118 are merged and deployed, but `lm_human_tasks` has 0 rows. Latest exact failure is Mercor job `goal:606cd5052e174d63954d19de71f5387b44c825f2a0cc30f64b3baa36102fd433`, created `2026-08-29T20:56:51Z`, dead-lettered `CAPABILITY_EXECUTION_FAILED` at `20:57:03Z` on deployed SHA `cb8c3917`. Never blind-retry that row.
- Natural proof: 16:00Z cycle `money-printer-scout:be9cb0c3…` completed on attempt 2 and created three opportunities; 00:00Z and 08:00Z cycles remain. Lancers application receipt `27863414` is verified application evidence, never revenue; `Paid & verified` remains zero.
- Public/Devpost: `https://aniccaai.com/money-printer` is live; Devpost project `1404362` is version 3 with correct website/repo but `video_url=null` and `submitted_at=null`.
- Capacity: at handover free is 2.7 GiB and swap 10 GiB. Before any model/browser/build, recover to >=8 GiB using the proven owner-aware idle-browser/build-volume procedure; Mac restart is last resort.
- First safe resume action: fresh-fetch `origin/main`, create the assigned implementation worktree, reproduce the exact HumanTask failure from current code/DB without an external effect, then make the smallest root-cause fix and live-read back open task → versioned answer → the same job completed.

