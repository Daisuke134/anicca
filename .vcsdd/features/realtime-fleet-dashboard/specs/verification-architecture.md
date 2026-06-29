# Verification Architecture — realtime-fleet-dashboard

## Purity boundary (isolate pure core from I/O so it's testable without network)

### PURE (deterministic, unit-tested with fixtures — the heart)
Module `registry-core` (TS, no imports of fetch/supabase/fs):
- `deriveStatus(row, nowMs) -> 'alive'|'stale'|'dead'` (REQ-4).
- `isSelfFundedEconomic(row) -> boolean` (REQ-5).
- `computeTotals(rows, nowMs) -> {assets, revenue30d, net, counts:{alive,stale,dead}, self_funded_pct, frontier_pct}` (REQ-6).
- `normalizeLogKind(kind) -> enum|'info'` (REQ-3).
- `toCardModel(row, nowMs) -> {badges, wallet, assets, revenue, burn, net, statusDot, ...}` (REQ-8 view-model).
These have NO side effects → 100% unit coverage, table-driven, edge cases enumerated.

### EFFECTFUL (thin I/O shell, integration-tested / E2E; kept minimal)
- `registry-client` (node): `register()`, `heartbeat()`, `log()` → Supabase upsert/insert via least-privilege creds (REQ-1/2/3/11/12). Pure payload-builders separated from the network call.
- `dashboard data source` (page): server fetch of rows+logs; client Supabase Realtime subscription (REQ-7/9). Realtime/polling is an adapter behind one interface so the page is testable with a fake source.
- `chain read` (optional): wallet_usdc from chain — stubbable; not required for PASS.

## Test plan
| Layer | What | How |
|---|---|---|
| Unit | deriveStatus, isSelfFundedEconomic, computeTotals, normalizeLogKind, toCardModel | node:test, fixtures, RED first |
| Edge | no last_heartbeat; exactly 90_000ms; burn_day=0 (div-by-zero guard); empty fleet; status='dead'; negative net | enumerated in unit tables |
| Integration | register→heartbeat→log roundtrip; staleness flips >90s | against Supabase test rows (id prefix `test-`), cleaned by snapshot-diff (delete only what the test created) |
| E2E (mine, post-adversary) | /dashboard renders live this instance + a log within 5s; no fallback | real browser screenshot + DOM check |

## Key-safety proof obligation (REQ-12)
A test/grep gate asserts no private-key / service-role-key string ever reaches an `instances`/`instance_logs`
payload; client uses only the public wallet address + least-privilege creds.

## Done (4-D convergence)
spec ✓ + tests ✓ (RED→GREEN, pure core + integration) + impl ✓ + verification ✓ (adversary PASS on disk +
MY browser E2E green showing live this-instance row + live log, not fallback). NO-MOCK E2E required before "done".
