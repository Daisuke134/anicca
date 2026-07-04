# Sprint-4 Participant Flow Spec — spawn from the anicca repo, thread the hackathon tag

**Correction of an earlier planning error.** A previous note proposed building a NEW
"agents-that-earn-starter" repository for entrants. That was wrong. The entry point already
exists: **`github.com/Daisuke134/anicca`** (the OSS automaton framework). Participants spawn an
Anicca from that repo; it auto-registers itself to the live board. This spec documents the REAL
flow (grounded in the actual runtime code) and pins the single code gap needed for the hackathon.

## Ground truth (real code, `~/anicca`)

- `install.sh` — bootstraps the automaton body into `$ANICCA_HOME` (default `~/.anicca`). Idempotent.
  Registry-driven (`skills/registry.json`). Does NOT ask for keys or broadcast tx; the loop earns.
- `BOOTSTRAP.md` — first-run checklist (set model, memory dirs, identity, integrations).
- `runtime/dashboard/telemetry-poster.mjs` — the REAL signed-heartbeat producer. Every 120s it:
  1. reads the instance's OWN wallet key from `~/.automaton/wallet.json` (no human key),
  2. computes net worth from Base mainnet (USDC + Aave + Morpho + Moonwell + Beefy + Fluid +
     blue-chip ETH + Hyperliquid) and reads the earn ledger for realized revenue-by-source,
  3. assigns a collision-impossible identity from the wallet address (`assignIdentity`) —
     **auto-registers on first POST**,
  4. calls `buildTelemetryMsg()` → signs the verbatim bytes with the wallet key →
     POSTs to the aniccaai.com telemetry endpoint,
  5. the receiver verifies `signer == id` + schema + replay window, then upserts Supabase `instances`.
- `runtime/dashboard/telemetry-msg.mjs` — the PURE signed-message builder. `MSG_KEYS` =
  `[id, ts, host, geo, funding, env, brain, model_live, model_tier, net_worth_usd,
  daily_revenue_usd, monthly_revenue_usd, revenue_by_source, revenue_mo_usd, burn_day_usd,
  runway_days, status, breakdown, log]`.
- Env knobs (one runtime, both types by config): `ANICCA_NAME`, `ANICCA_FUNDING` (human|self),
  `ANICCA_ENV` (local|cloud), `ANICCA_BRAIN` (claude-p|self-pay).

This is already live: the current dashboard row `0xa3cdd4ec…` (host `anicca-a3cdd4`, brain
`claude-p`) is exactly this poster reporting a real Anicca instance.

## The participant "one command" (what goes on the Luma page)

```
git clone https://github.com/Daisuke134/anicca
cd anicca
./install.sh                       # bootstraps ~/.anicca (idempotent)
# put a funded Base wallet key at ~/.automaton/wallet.json, set your model, then start the loop
ANICCA_TAGS=agent-hackathon <start the automaton loop>
```

The instant the loop's first telemetry beat fires, the agent appears on
`aniccaai.com/dashboard` under the **#agent-hackathon** filter — signed by its own wallet,
net-worth read on-chain, no human in the loop. The participant writes ONE thing: how their
agent earns (the earn slots). Everything else — identity, signing, posting, ranking — is the
framework.

## THE ONE REAL CODE GAP (S4.1) — tags do not flow

`MSG_KEYS` / `buildTelemetryMsg` (`runtime/dashboard/telemetry-msg.mjs`) do NOT include `tags`.
Therefore a spawned instance CANNOT declare `agent-hackathon`, and the `#agent-hackathon` filter
built in sprint-1 (`AgentLeaderboard.tsx`) + the `is_ours`/tag logic in `telemetry-aggregate.js`
have **no data source** from the real poster. This is the single thing standing between "we built
a leaderboard" and "people spawn and show up under #agent-hackathon".

### S4.1 requirements (EARS)

- **S4.1a (signed tag)** `buildTelemetryMsg` SHALL include a `tags` field (string array) in the
  signed object WHEN the poster provides one, appended AFTER the existing keys so base messages
  stay byte-identical (cross-language + back-compat, same discipline as apps/landing
  `canonicalMessage`). `MSG_KEYS` SHALL be extended to include `tags`.
- **S4.1b (env-driven)** The poster SHALL read `process.env.ANICCA_TAGS` (comma-separated),
  parse it into a trimmed non-empty string array, and pass it to `buildTelemetryMsg`. Absent env
  ⇒ no `tags` key (base message unchanged).
- **S4.1c (receiver accepts)** The aniccaai.com receiver (apps/landing telemetry function +
  `telemetry-schema.validate`) SHALL accept the signed `tags` field. (Already GREEN in sprint-1:
  `telemetry-schema.js` type-checks `tags: string[]` when present; `instances.tags text[]` column
  is live per sprint-3. This requirement is a cross-repo VERIFICATION, not new code.)
- **S4.1d (end-to-end)** A spawned instance with `ANICCA_TAGS=agent-hackathon` SHALL, after one
  beat, have `tags` containing `agent-hackathon` in its Supabase row, and SHALL appear under the
  `#agent-hackathon` filter on the rendered dashboard.

### S4.1 verification architecture

| Req  | Test                                                                 | Real target |
|------|----------------------------------------------------------------------|-------------|
| S4.1a| unit (`~/anicca/runtime/dashboard/__tests__/telemetry-msg.test.mjs`): with `tags` present, `MSG_KEYS` includes `tags`, obj carries it, and a base message (no tags) is byte-identical to the pre-change output | pure builder |
| S4.1b| unit: `ANICCA_TAGS="agent-hackathon, x"` → `["agent-hackathon","x"]`; empty/undefined → no key | poster arg parse (extract the parse to a pure fn) |
| S4.1c| cross-repo: `apps/landing telemetry-schema.validate({...,tags:["agent-hackathon"]}).ok === true` (already true) + `instances.tags` column exists (sprint-3) | live schema |
| S4.1d| LIVE E2E: spawn a throwaway instance (or reuse 0xa3cd with ANICCA_TAGS set), beat once, then `verify-live-migration`-style probe shows the row's `tags` ⊇ `[agent-hackathon]`; render pipeline → `#agent-hackathon` filter includes it | live Supabase + real poster |

## S4.2 — the deploy prerequisite (corrects S3-FIND-002)

The sprint-3 evidence proved the DEPLOYED `main` runs OLD apps/landing code (no enrichment;
`is_ours`/`earn_src`/`net_worth_src` all null on the live endpoint). Therefore, before the
`#agent-hackathon` leaderboard shows the NO-FAKE engine on aniccaai.com, **`feature/clip-rewards`
MUST be merged to `main`** so the deployed telemetry receiver + `dashboard-sync` + `AgentLeaderboard`
run the sprint-1/2/3 code. This is a hard PREREQUISITE for S4.1d passing on production, not a
follow-up. (Named explicitly per adversary finding S3-FIND-002.)

## Done (this sprint)

1. This spec on disk + committed (participant flow corrected: spawn from the anicca repo).
2. S4.1 implemented in `~/anicca` (tags through poster + MSG_KEYS) with unit tests green.
3. S4.2 merge done (or explicitly tracked as the gating prerequisite with owner = Dais).
4. LIVE E2E: a spawned instance appears under `#agent-hackathon` on the rendered dashboard.
5. Fresh-context sonnet-5 adversary PASS on this spec + the tag implementation.

## Scope (out / honest limits)

- The paid Base RPC (so `earn_src` becomes `chain` for external-earnings ranking) = A2, separate.
- The scheduled render cron (A3) = separate.
- This spec does NOT re-open sprint-1/2/3 (all PASS); it adds the participant entry + the tag thread.
- Cross-repo note: the tag CODE change lands in `~/anicca` (repo `Daisuke134/anicca`), while the
  receiver/leaderboard already lives in `~/anicca-project`. Two repos, one signed contract.
