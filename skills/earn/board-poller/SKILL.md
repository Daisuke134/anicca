---
name: earn/board-poller
description: Poll many agent-task / bounty boards for OPEN tasks, rank by reward, claim the winnable ones, execute with intelligence, submit, get paid in USDC. Boards are intermittent — this catches a task the moment one appears across ALL boards. $0, no paid keys.
---

# earn/board-poller — catch + win paid agent tasks across every board

Agent-task boards (BountyBook, Clustly, Clankonomy, Daydreams TaskMarket, Claw Earn …) hold escrowed USDC
tasks. Any single board is often empty; the edge is **aggregating** them and **striking the instant** a
winnable task appears. This is where an intelligent AI beats low-IQ bots: it actually does the work well.

★ Verified live 2026-06-29: `poller.mjs` surfaced 16 OPEN claimable BountyBook bounties on Base — e.g.
"$6 / 35min — build a CLI that checks HTTP status codes", "$5 — Python StateMachine", "$4 — Rust
word_count". Real money, coding tasks, squarely in an AI's wheelhouse. ★

## The tool
```bash
node poller.mjs        # → JSON { open_count, tasks:[{board,id,title,reward,minutes,difficulty,url}] }
                       #   sorted by reward (highest first). $0, no paid keys.
```
Boards wired: **BountyBook** (`api.bountybook.ai/jobs`, public, live) + **Clustly** (`/api/v1/tasks/open`,
needs the install's agent_key in `~/.clustly/config.json`). Add a board = add one entry to `BOARDS` in
`poller.mjs` (each returns `{board,id,title,reward,url}`).

## The earn loop (per wake — the agent's job)
1. **POLL** — `node poller.mjs` → ranked open tasks across all boards.
2. **PICK** — choose the highest reward × win-probability you can clearly deliver (your coding/research edge).
3. **CLAIM** — per board: BountyBook = wallet-sig auth (GET /auth/nonce → sign with your key → POST
   /auth/verify → Bearer → POST /jobs/:id/claim). Clustly = POST /tasks/:id/claim with agent_key.
4. **EXECUTE** — actually do it well (write the code / research / data). This is the moat.
5. **SUBMIT** — POST the deliverable (BountyBook /jobs/:id/submit ; Clustly /tasks/:id/submit).
6. **GET PAID** — on verification (AI oracle / poster approval) USDC settles to your wallet.
7. **RECORD** — `record-earn.mjs` (INV-7) logs ONLY the real external inflow. Append seen IDs to avoid
   double-claiming.

## BountyBook submit GOTCHA (verified 2026-06-29 — read before relying on it)
- Auth + claim WORK: claim binds (status=claimed, executor=your address) — confirmed on a fresh job.
- ★ INLINE `outputData` submit does NOT credit ★: POST /submit returns 200 "Verification in progress",
  but the job instantly reverts to status=open, executor=null, verification_result=null, and the agent
  profile's jobs_completed/jobs_failed/total_earned stay 0. Tried `{files:{...}}`, `{"<file>":code}`,
  redundant keys, same-token claim+submit — all no-op. No error surfaced. (Stuck jobs also exist — a fresh
  job binds, an old one may not.)
- ★ The FAQ documents the RELIABLE path as IPFS: "upload your output to IPFS and submit the CID
  (outputCID); the oracle fetches it and verifies." → for real payouts, use `outputCID` (pin the
  deliverable to IPFS via web3.storage/Pinata — autonomous signup via the install's AgentMail), NOT inline. ★
- Net so far: realised earnings via BountyBook = $0 (inline submit unverified). Next = the IPFS-CID path.

## Honesty
A task counts as earnings only when REAL USDC settles from the board's escrow (external payer). The poller
surfaces; the work + a clean submission is what earns. Don't claim what you can't deliver (BountyBook stakes
reputation; a bad submission burns it).

## Replication (every AI)
Same poller, the install's OWN board accounts/keys + wallet. Self-funded children run it on a free model for
simpler tasks. Wire each AI's boards once → it catches + wins paid work autonomously, forever.
