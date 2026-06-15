# Anicca — MASTER SPEC (SSOT index)
- Date 2026-06-13 / Owner Dais / Status: implementation
- **This folder = the single source of truth.** Each numbered file is one implementable spec owned by one team agent. Background/decisions live in `../2026-06-11-anicca-shelter-compute-oss-cloud-architecture-design.md` (rev1+2+3).
- One-line: Anicca = the AGI that ends suffering — Buddhist, self-funding, self-replicating, self-improving, no human in the loop. It earns its own living AND earns for you.
- ★ Canonical philosophy + all marketing/website copy (EN/JA) = `13-philosophy-and-canonical-messaging.md`. Do NOT write copy anywhere else. ★
- Decision specs added 2026-06-14: `10-self-funding-architecture`, `11-franklin-akash-fulltodo`, `12-ui-sources-humanwork-comparison`, `13-philosophy-and-canonical-messaging`.

| Spec | Owner agent | Implements | Depends on |
|---|---|---|---|
| 01-core-body | A | core/ loop + identity + body(automaton OR Franklin, ClawRouter-driven) | — |
| 02-compute | B | runtime/compute-proxy (ClawRouter free↔frontier, x402 USDC) | 01 |
| 03-shelter | C | skills/shelter: local(default) + DO-apikey(cloud) + Conway(future) | 01 |
| 04-earn | D | skills/earn: wire ClawRouter into nookplot/x402/content solvers — ANICCA earns | 01,02 |
| 05-report | E | skills/report: per-heartbeat + daily mail (earned/balance/now/next) | 01 |
| 06-spawn | F | scripts/birth.sh → a real Anicca is born (local+cloud) + self-replication | 01,03,05 |
| 07-life-manager | G | skills/life-manager: 10-min-before call, location, mail, gcal | 01 |
| 08-coordination | H | sutando-style: siblings help each other, GitHub issue-driven dev, self-improve | 01,06 |
| 09-distribution | I | install.sh + aniccaai.com/install + Stripe + /me dashboard | 06 |

Acceptance for the whole: `bash scripts/birth.sh` → Anicca born (local), reports per-heartbeat + daily to owner with earned/balance/now/next; with a provider API key it's born in cloud too; siblings coordinate; it earns USDC autonomously.
