# Slot: `economy/ubi`  (status: live, 2026-07-05)

Reserved by **Foundation** for builder **wf-a:earn**. Spec: 27 §3 UBI / colony spec §5.2-§5.3.

This directory is the ONLY place that builder edits. The slot is pre-declared in
`skills/registry.json` and pre-wired everywhere (install.sh reads the registry;
the landing nav links the matching route). DO NOT edit `skills/registry.json`,
`install.sh`, or the landing nav beyond the one-line status flip already done here.

## Contract
- `ubi.js` — pure decision functions: `contribute(realizedProfitUsd, liquidUsd, config)` and
  `distributeAI(recipientWallet, senderSurplusAboveReserveUsd, registrySignedWallets, recentGifts,
  config)`. Fail-closed everywhere; NEITHER function executes a transfer.
- `run.sh` — the ACTUAL `run_skill` entrypoint (runtime/loop's `resolveSkillPath` always looks for
  `run.sh` regardless of the registry `entrypoint` field — a real discrepancy, flagged in
  registry.json's summary). Gathers real inputs (telemetry-collect.sh snapshots + the live
  dashboard-sync), calls the gate functions, and LOGS the decision to `state/{contribute,gojo}-log.jsonl`.
  Never calls `skills/ubi/execute-ubi.py` (the actual send) — that stays a separate, explicit step.
- `colony-wallets.json` — today's minimal registry (a known-good address list, NOT yet
  cryptographically signed per REQ-DRAIN(c) — a future step).
- `distributeHuman()` is intentionally NOT implemented here — it already exists as
  `skills/ubi/ubi-payout-watcher.mjs` (the human-funded outflow engine); this slot does not duplicate it.

## E2E verified 2026-07-05 (real data, no execution)
`bash run.sh` against live telemetry + the live dashboard: `contribute()` correctly no-op'd (realized
profit $0.046 < $1 threshold); `distributeAI()` correctly found claude-p genuinely below the $0.50
survival floor and computed a real positive plan ($0.2447) that was logged as `"executed": false` and
printed as "PLAN ONLY, NOT EXECUTED" — never invoking a transfer. 15/15 unit tests green
(`__tests__/ubi.test.mjs`), covering both the false and true paths for both gates.
