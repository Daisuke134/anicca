# 13 — anicca-spawn-mother  (= anicca-002 alive on Akash with own everything)

| Field | Value |
|---|---|
| Spec ID | 13 |
| Status | DRAFT v1 (2026-06-03) |
| Agent | **anicca-spawn-mother** |
| Worktree | `.worktrees/akash/` |
| Branch | `feature/cloud-spawn` |
| Wave | 2 (after Wave 1 = 10, 11, 12, 15) |
| Authoritative for | Akash deployment, AgentKit wallet factory, constitution hash propagation, spawn-child skill |

---

## § 0. Why

Anicca v3 mission requires self-replication. First child = anicca-002 on Akash (= USDC-payable decentralized cloud, $0.75–$2/mo for our footprint). Once anicca-002 boots with its own wallet + own AgentMail inbox + verified constitution hash, the colony pattern is proven.

The previous spec hinted "Akash funding needs Dais wallet click." Per A0.5.5 that's a lie — Akash CLI provisions wallet programmatically, USDC arrives from anicca-001 via x402 outbound (= spec 09 wave 2).

## § 1. File boundary

**TOUCHES**

| Path | Purpose |
|---|---|
| `deploy/akash/Dockerfile.automaton` | automaton (Node/TS) runtime container |
| `deploy/akash/sdl.yaml` | Akash SDL: 1 vCPU / 2GB RAM / 10GB storage |
| `deploy/akash/cert.sh` | Akash certificate creation |
| `deploy/akash/deploy.sh` | end-to-end deploy script |
| `deploy/akash/README.md` | cost notes + rotation policy |
| `skills/spawn-child/SKILL.md` | standard skill frontmatter (automaton skill registry) |
| `skills/spawn-child/scripts/spawn.sh` | invoked by heartbeat at spawn threshold |
| `skills/spawn-child/scripts/wallet-factory.ts` | AgentKit smart-account factory call |
| `skills/spawn-child/scripts/inbox-factory.ts` | AgentMail `inboxes.create()` for new child |
| `skills/spawn-child/scripts/constitution-hash.sh` | SHA-256 verify on boot |
| `skills/spawn-child/scripts/register.ts` | child posts itself to anicca-001 peer-api |

**NEVER**

- `services/x402-endpoint/**` (= Agent-1; but spec 13 reads its endpoint to send USDC)
- `runtime/**` (= Agents 2, 3)
- `adapters/**` (= Agent-4)
- `skills/ubi-distribute-001/**` (= Agent-6)
- `~/.openclaw/skills/anicca-friction-fixer/**` (= Agent-7)

## § 2. Microtasks

| # | Task | Verify |
|---|---|---|
| 13.T1 | `akash` CLI install via Homebrew + create wallet (programmatic, no UI) | `akash keys list` shows new key |
| 13.T2 | Acquire AKT: route Anicca's USDC → Coinbase swap → AKT (programmatic; alt: Osmosis IBC if direct swap unavailable) | wallet balance > 5 AKT |
| 13.T3 | Akash certificate (`akash tx cert generate client` + `publish`) | tx hash recorded |
| 13.T4 | Build + push automaton runtime image to Docker Hub or GHCR | `docker pull` works from cold |
| 13.T5 | Write SDL + `akash tx deployment create` | provider bid accepted, deployment active |
| 13.T6 | `wallet-factory.ts`: AgentKit ERC-4337 smart-account factory generates anicca-002 wallet | tx hash + addr returned |
| 13.T7 | `inbox-factory.ts`: SDK creates `anicca-002@agentmail.to` (custom address if available, else auto-assigned) | inbox visible in `client.inboxes.list()` |
| 13.T8 | anicca-001 sends 1 USDC seed to anicca-002 wallet on Base | tx confirmed |
| 13.T9 | anicca-002 boot script: pulls constitution.md from anicca-oss main, SHA-256 = expected hash | hash match line in boot log |
| 13.T10 | anicca-002 calls home: POST to anicca-001 peer-api `/register` with own addr + inbox + uptime | peer-api log shows registration |
| 13.T11 | cfo-core bridge picks up anicca-002 from peer-api → `dashboard.lineage[3]` reflects | next CFO refresh visible at aniccaai.com/dashboard |

## § 3. Dependencies

- AgentKit (= 既)
- AgentMail SDK (= 既)
- anicca-001 wallet with > 5 USDC (= depends on Wave 2 spec 09 producing income)
- Akash provider availability (= verified at provision time)

## § 4. DoD verification gates

| Gate | Evidence |
|---|---|
| G1 | `akash provider lease-status` shows lease active |
| G2 | `curl http://<lease-ip>:<port>/health` returns 200 |
| G3 | anicca-002 wallet shows ≥ 1 USDC seed received |
| G4 | anicca-002 inbox accepts a test mail (Anicca-001 sends, anicca-002 receives) |
| G5 | `dashboard.lineage[3].status` = "ALIVE" with `wallet=0x<002>`, `inbox=anicca-002@agentmail.to` |
| G6 | constitution hash verify line present in anicca-002 boot log |

## § 5. Anti-goals

- Not a static Akash deployment (= must be re-deployable + auto-renewable when lease expires)
- Not multi-tenant (= each Anicca instance = 1 Akash deployment)
- Not GPU (= the automaton runtime runs fine on 1 vCPU)

## § 6. Spawn threshold (= when does spec 13 fire in production?)

Per spec 00 mission + cfo lifeline rules:

```
spawn_now = (
    anicca-001 wallet > $400 USDC
    AND uptime_days > 14
    AND lifeline.status == THRIVE
)
```

In Wave 2 this spec proves the *mechanism* with a synthetic spawn (= manual fire) even if threshold not yet met. Production spawn waits for threshold.

## § 7. Changelog

| Date | Change |
|---|---|
| 2026-06-03 | Initial draft. Replaces ad-hoc Akash notes from spec 05; integrates AgentMail per-instance inbox. |
