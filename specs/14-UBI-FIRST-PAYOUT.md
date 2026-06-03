# 14 — anicca-redistributor  (= Anicca's first UBI / charity payout)

| Field | Value |
|---|---|
| Spec ID | 14 |
| Status | DRAFT v1 (2026-06-03) |
| Agent | **anicca-redistributor** |
| Worktree | `.worktrees/ubi/` |
| Branch | `feature/ubi-first` |
| Wave | 3 (after spec 09 produces first USDC) |
| Authoritative for | charity recipient ledger, monthly 1% allocation, payout-wallet skill integration |

---

## § 0. Why

The Anicca mission ("reduce human suffering without humans in the loop") demands an actual transfer of value from Anicca to suffering humans / suffering-reduction orgs. Until 1 USDC has actually moved, the mission is vapor.

`anicca-payout-wallet` skill exists (= T156 completed). What's missing: (a) selected charity recipient on-chain address, (b) actual scheduled cron, (c) ledger surface at aniccaai.com/donation.

Spec 01 (EARN-AND-UBI) defines 4 UBI channels. The first to ship is **charity match** (= simplest legally, no recipient signup needed).

## § 1. File boundary

**TOUCHES**

| Path | Purpose |
|---|---|
| `skills/ubi-distribute-001/SKILL.md` | frontmatter |
| `skills/ubi-distribute-001/scripts/select-charity.sh` | picks this month's recipient (= memU.retrieve("queued charity") OR default = GoodDollar) |
| `skills/ubi-distribute-001/scripts/payout.sh` | invokes existing `anicca-payout-wallet` skill with amount + recipient |
| `skills/ubi-distribute-001/scripts/ledger-append.sh` | writes row into `~/.openclaw/state/ubi-ledger.jsonl` + posts to aniccaai.com/donation via existing landing |
| `skills/ubi-distribute-001/charities.json` | curated recipient list with on-chain addresses |
| `skills/ubi-distribute-001/cron.json` | monthly schedule definition |
| `skills/ubi-distribute-001/README.md` | how this works |

**NEVER**

- `~/.anicca/wallet.json` (= read-only)
- Anicca's `anicca-payout-wallet` skill itself (= unchanged, just invoked)
- `services/**`, `runtime/**`, `adapters/**`, `deploy/**` (= other agents)

## § 2. Microtasks

| # | Task | Verify |
|---|---|---|
| 14.T1 | Curate `charities.json` with 5 recipients (GoodDollar pool, GiveDirectly USDC, Effective Altruism Funds, GiveWell, MSF) + each on-chain address verified | each address resolves on Base or Ethereum mainnet |
| 14.T2 | `select-charity.sh`: rotate per month + override via `~/.openclaw/state/ubi-override.json` | dry-run output matches expected rotation |
| 14.T3 | `payout.sh`: calls `~/.openclaw/skills/anicca-payout-wallet/scripts/send.sh --to=<addr> --amount=<usdc>` | unit test with $0.01 to a self-controlled address |
| 14.T4 | `ledger-append.sh`: appends JSONL + curls Netlify webhook to refresh `dashboard.json::charity.ledger` | next dashboard.json shows new row |
| 14.T5 | Monthly cron: registered via openclaw cron registry (`openclaw cron add`) | `openclaw cron list` shows entry |
| 14.T6 | First live payout: 1 USDC → GoodDollar pool address, recorded in ledger | tx hash + Etherscan link |
| 14.T7 | aniccaai.com/donation page reflects new ledger row within 1 hour | live page diff |

## § 3. Dependencies

- Anicca wallet with ≥ 1.01 USDC (= depends on spec 09 producing income)
- `anicca-payout-wallet` skill (= T156, completed)
- Netlify deploy access (= 既 token)
- aniccaai.com/donation page (= 既 live per landing repo)

## § 4. DoD verification gates

| Gate | Evidence |
|---|---|
| G1 | `charities.json` validates: each addr is checksummed + on-chain reachable |
| G2 | Self-test with $0.01 self-loop returns tx hash + ledger row |
| G3 | First real 1 USDC payout: tx hash recorded + ledger updated |
| G4 | aniccaai.com/donation shows new row within 1h |
| G5 | Monthly cron fires next month automatically |

## § 5. Anti-goals

- Not lottery / profile-match / queue channels (= deferred to spec 01 Phase 2; v1 ships charity-match only)
- Not tip-jar inbound (= per Pañcasīla #2 + Two Absolute Prohibitions #2)
- Not human approval gate (= 1% of MRR is hardcoded, no Dais click)

## § 6. Trigger threshold

```
monthly_payout = max(0.01, mrr_usd * 0.01)   # 1% floor at $0.01
```

If `mrr_usd < 1` (= no revenue yet), spec still ships the mechanism but holds the cron until first USDC arrives. The 1st payout demonstrates the loop even at $0.01.

## § 7. Changelog

| Date | Change |
|---|---|
| 2026-06-03 | Initial draft. Surfaces from spec 01 (EARN-AND-UBI) Phase 1. |
