# AE-ZERO-START-1 — Evidence

**Status: DRAFT — offline evidence complete after adversary round 2 fixes, live E2E PENDING.**
Spec: `docs/superpowers/specs/2026-07-30-ae-zero-start-1-design.md`
Plan: `docs/superpowers/plans/2026-07-30-ae-zero-start-1.md`
Branch: `feature/ae-zero-start-1` · Worktree: `~/anicca-project/.worktrees/ae-zero-start-1`
Implementation: Opus 5 subagent, 2026-07-30. Live E2E (§7): Fable, after merge.

Everything under "Offline evidence" was produced by commands actually run in the
implementation session and the output is quoted verbatim. Everything under
"Live E2E" is **not done** and is left empty on purpose — a filled-in value there
without a real run would be exactly the fabricated evidence this slice exists to
make impossible.

---

## 1. What shipped

| # | Component | File |
|---|---|---|
| 1 | Solana agent wallet (ed25519, base58) | `apps/life-manager/lib/agent-wallet-solana.js` |
| 2 | Tenant wallet columns + anti-plaintext-key CHECKs | `apps/life-manager/migrations/2026-07-30-lm-tenant-agent-wallets.sql` |
| 3 | Per-tenant 0600 key custody | `apps/life-manager/lib/tenant-wallet-store.js` |
| 4 | Zero-start job adapter (`wallet.zero-start`) | `apps/life-manager/lib/zero-start-job-adapter.js` |
| 4b | Measured Solana balance reader | `apps/life-manager/lib/solana-balance.js` |
| 5 | Inflow watch adapter (`wallet.inflow.watch`) | `apps/life-manager/lib/wallet-inflow-job-adapter.js` |
| 6 | Self-heal sweep (the only enqueue point) | `apps/life-manager/lib/wallet-sweep.js` |
| 6b | Capability registration | `apps/life-manager/config/loop-adapters.json`, `apps/life-manager/scripts/runtime-up.js` |

Commits (`1f1c458cb..de7348024`), oldest first:

```
9773c0893 docs: AE-ZERO-START-1 implementation plan
a12b7174a docs(spec): AE-ZERO-START-1 inflow kind = financial_deposit
b1f28b844 feat(life-manager): Solana agent wallet module for AE-ZERO-START-1
db6661358 feat(life-manager): tenant agent wallet columns with schema-enforced no-plaintext-key
ec17fe7e8 feat(life-manager): per-tenant 0600 wallet custody with non-clobbering atomic writes
3e9244f59 docs(spec): atomic write = tmp+fsync+link(2), not rename
7f002e02f feat(life-manager): wallet.zero-start adapter + measured Solana balance reader
31639604c docs(spec): inflow amount encoding + receipt-based cursor
0d4f3e47b feat(life-manager): wallet.inflow.watch adapter records inflows as capital, revenue 0
515b835ae docs(spec): zero-start enqueue = self-heal sweep only
de7348024 feat(life-manager): register wallet capabilities and the self-heal sweep
```

---

## 2. Offline evidence (RUN, verbatim)

Node `v25.6.1`, run from `apps/life-manager`.

### 2.1 Full suite — `npm test`

Re-run after every adversary round-1 fix, twice (the second run because an
external cleanup process deleted `node_modules` mid-session, see §2.8):

```
NPM_TEST_EXIT=0
TOTAL tests=1876 pass=1876 fail=0
```

46 `node --test` segments, zero segments with a nonzero `ℹ fail`. `npm test`
chains with `&&`, so exit 0 means every segment ran and passed. (Before the
round-1 fixes this read 1824/1824 — also all green, which is exactly why the six
money defects got through; see §2.9.)

### 2.2 Focused money slice — `npm run test:money-slice`

```
ℹ tests 290
ℹ pass 290
ℹ fail 0
```

The money segment previously inlined in the `test` script is now the named
`test:money-slice` script (one source of truth, called from `test`). Baseline
before this slice was 132 tests; 158 have been added (106 in the first pass, 40
hostile-payload tests in round 1, 12 more plus the drain invariants in round 2).

### 2.3 Other suites touched

| Suite | Result |
|---|---|
| `npm run test:runtime-up` | `tests 26 / pass 26 / fail 0` |
| `npm run test:runtime-adapters` | `tests 76 / pass 76 / fail 0` |
| `node --test test/tenant-isolation.test.js` | `tests 12 / pass 12 / fail 0` (9 pre-existing + 3 new wallet isolation) |
| `npm run test:tenant-agent-wallets:postgres` | `PASS mode=docker provisioned_tenants=2 refusals=15 key_material_rows=0` (re-run after the fixes) |

### 2.4 New test files

| File | Tests |
|---|---|
| `lib/agent-wallet-solana.test.js` | 13 |
| `lib/agent-wallet-migration.test.js` | 8 |
| `lib/tenant-wallet-store.test.js` | 18 |
| `lib/solana-balance.test.js` | 9 |
| `lib/zero-start-job-adapter.test.js` | 18 |
| `lib/wallet-inflow-job-adapter.test.js` | 22 |
| `lib/wallet-sweep.test.js` | 11 |
| `lib/wallet-capability-wiring.test.js` | 7 |
| `lib/wallet-sweep.test.js` | 23 (11 + 12 added in round 1) |
| `lib/wallet-capability-wiring.test.js` | 16 (7 + 9 added in round 1) |
| `lib/secret-provider.test.js` | +6 colony-provider tests (existing file) |
| `test/postgres/tenant-agent-wallets.integration.sh` | 15 engine-level refusals |
| **Total** | **146 unit/contract + 1 integration script** |

### 2.5 §5.3 proven by the engine, not by text matching

`npm run test:tenant-agent-wallets:postgres` — real PostgreSQL 18 (docker
`postgres:18-alpine`), migration applied twice to prove idempotence:

```
tenant-agent-wallets: PASS mode=docker provisioned_tenants=2 refusals=15 key_material_rows=0
```

The 15 refusals the database actually performed: a raw `0x` EVM private key as a
key ref; a bare 64-hex key; a base58 Solana secret key; a private key smuggled
inside a well-formed `secret://` ref (both rails); a filesystem path; a bare path
with no scheme; a scheme with no path; an EVM address in the Solana column; a
base58-illegal address; an over-long address; a Solana address in the EVM column
(REPORT-1's CHECK still working); and three cross-tenant claims (tenant-b trying
to take tenant-a's Solana address, base key ref, and Solana key ref).

### 2.6 Secret scan

`gitleaks detect --log-opts 1f1c458cb..HEAD` over the whole branch, and again over
just the round-1 fix commits (`bacdb6d18..HEAD`):

```
no leaks found
```

`gitleaks protect --staged` was also run and clean before each of the six
implementation commits. Test fixtures use the published RFC 8032 §7.1 ed25519
vectors and published Ethereum private-key-1/2 vectors, marked as such in the
files; no 88-character base58 secret literal exists anywhere in the repo (the
Solana test builds it at run time from the hex vector).

### 2.7 Invariant → where it is proven

| Spec invariant | Proven by |
|---|---|
| §5.1 keys never in DB/receipt/TG/log/error | `agent-wallet-solana.test.js` (non-enumerable secret, static error messages), `tenant-wallet-store.test.js` ("no thrown error carries key material into a log"), `zero-start-job-adapter.test.js` ("nothing secret reaches the message, the receipt, or the database columns") |
| §5.2 `assertNoSecret` on every receipt + TG payload | applied in both adapters; asserted in both adapter test files |
| §5.3 DB rejects key-shaped strings | `test/postgres/tenant-agent-wallets.integration.sh` (real engine, 15 refusals) + `agent-wallet-migration.test.js` (predicate pinned, every regex behaviour-tested) |
| §5.4 key collision hard-stops, never overwrites | `tenant-wallet-store.test.js` ("a key file that disagrees with the database hard-stops and is never overwritten", "a database address with no key file hard-stops") |
| §5.5 gitleaks/PII gates green | §2.6 |
| "a `$0.00` that was not measured is a lie" | `zero-start-job-adapter.test.js` ("a balance that could not be measured stops the message"), `solana-balance.test.js` (8 unclean-answer cases all throw; a JSON-rounded lamport value is refused) |
| never fabricates a send | `zero-start-job-adapter.test.js` (`BLOCKED_NO_CHAT`; provider answer with no `message_id` is a failure; refusal retryable vs dead transport reconciled) |
| inflow exactly-once, revenue 0 | `wallet-inflow-job-adapter.test.js` (replayed window refuses the second write; kind asserted against the real `rollUpMonth`: `counted_rows 0`, `excluded_rows 1`, `net_usd_micros "0"`) |
| tenant A/B cross-contamination 0 | `test/tenant-isolation.test.js` (3 new tests, two real tenants), `tenant-wallet-store.test.js`, plus DB-level partial unique indexes |

### 2.8 Environment caveat, recorded for the next reader

`apps/life-manager/node_modules` was deleted by an external cleanup process six
times during this work, twice only partially (e.g. `@noble/hashes` removed while
`@scure/base` survived), which surfaces as a misleading `MODULE_NOT_FOUND`. The
repository itself was never affected and `npm ci` restores it in ~5s. Every count
in §2 was taken with the dependency tree verified present immediately beforehand,
and the two headline numbers (full suite, money slice) were each measured twice.
One money-slice run reported `28 pass / 18 fail` purely because the tree vanished
between two commands; re-measured immediately after reinstall it is 278/278.

### 2.8b Round 2 — and why example tests were replaced by invariants

Round 2 re-verified all eight round-1 fixes as HELD under fresh hostile payloads, and
re-measured every offline number independently with all of them matching. It then
found **four new MAJOR defects in the fix code, all in the same class, and all
passing 1876 green tests** — the second consecutive round where that happened.

Spec §12.1 supplied the clause that was missing from §10:

> What has already been processed is also a fact, and it must be re-derived from the
> events themselves — never from the provider's idea of "newest".

A cursor is not a bookmark the RPC hands you; it is a claim that everything behind it
is booked. All four new defects were that claim being false while the receipt
reported success.

**The durable output of round 2 is two drain-invariant tests**
(`lib/wallet-drain-invariants.test.js`), which name no payload at all:

| Invariant | What it asserts |
|---|---|
| Scan drain | For a synthetic chain far larger than one wake's budget, spanning both rails, with several events per block and per signature and unreadable entries: running to no-progress books every event **exactly once**, and any unbooked event **must** be admitted by a receipt (`truncated` or `needs_operator_attention`). Silence with unbooked events fails the test. |
| Sweep drain | For five different permanent-failure patterns (none, one, the whole first page, every other tenant, all-but-one): every healthy tenant is watched within a bounded number of passes. |

Both were verified to actually catch their defect rather than merely pass:

- Putting the ordering query back to successes-only makes the sweep invariant report
  `40 healthy tenants were never watched within 4 passes`.
- The scan invariant caught a defect in **its own fixture**: the signature generator
  `(index * 7 + position * 13) % 58` has period 58, so signature 58 collided with
  signature 0 and silently overwrote a transaction, making two events unproducible.
  Measured: 60 indices yielded 58 unique signatures. Fixture uniqueness is now
  asserted, not assumed — the round's own defect class appearing inside the harness.

### 2.9 What the first round of tests did NOT catch

Recorded because it is the most transferable finding here: **1824/1824 tests passed
with one blocker and six money defects present.** Unit tests written by the builder
encode the builder's assumptions, so they confirmed that the code did what its
author believed. Only hostile-payload probing — an RPC that ignores its own filter,
two transfers in one transaction, a reordered balance array, an unfinalized head, a
tenant the shared worker was never built for — found them.

Consequently every round-1 fix landed with a test that feeds the hostile payload,
never the happy one, and the RED state was observed for each before the fix:

| ID | The hostile payload that proved it |
|---|---|
| BLOCKER-1 §9.1 | a job for `tenant-b` on a worker pinned to `tenant-a` |
| §9.2 / MAJOR-5 §11 | a chatless tenant across 40 sweeps, then a chat linked on day 30 |
| MAJOR-2 | two USDC transfers to one wallet inside one transaction |
| MAJOR-3 §9.3 | 60 watchable tenants against a per-pass cap of 50 |
| MAJOR-4 | a log addressed to another tenant, an Approval event, a counterfeit token contract |
| MAJOR-6 | `latest`=5000 with `finalized`=4000; a `removed === true` log |
| MAJOR-7 | pre/post token balances listed in opposite orders (T16b), both directions |
| MINOR-12 | a wake whose row budget was already spent |

### 2.10 Schema limits measured, not assumed (§11)

Both reap options §9.2 offered are refused by the shipped schema. Probed in real
PostgreSQL 18 against `migrations/20260729_runtime_jobs.sql`:

| probe | engine's answer |
|---|---|
| second job row, same `effect_key`, generation-suffixed `job_id` | `duplicate key value violates unique constraint "lm_runtime_jobs_tenant_id_effect_key_key"` |
| `DELETE` the terminal job row | `violates foreign key constraint "lm_runtime_job_receipts_job_id_tenant_id_fkey"` |
| delete its receipts first | `runtime job receipts are immutable` |
| reset `attempt=0`, re-claim, complete | `runtime receipt conflict` (receipt PK is `(job_id, attempt)`) |
| status → `queued`, `attempt` untouched | **works** — receipts preserved as `1:blocked_no_chat, 2:started` |
| `max_attempts` above 20 | `violates check constraint "lm_runtime_jobs_max_attempts_check"` |

So a zero-start row has a lifetime budget of 20 runs and can never be replaced,
which is why waiting for a Telegram link must cost zero attempts (§11.3) and why
the re-activation, not the enqueue, carries the gate.

---

## 3. Live E2E — PENDING-E2E (Fable, after merge)

None of the following has been run. **Do not fill any of these in from
inference — each line needs a real observation.** Spec §7 is the checklist.

### 3.1 PENDING-E2E — two real test tenants provisioned on the live local runtime

- tenant A uid: _pending_
- tenant B uid: _pending_
- provisioning wake receipt (`lm_runtime_job_receipts`, `kind=tenant_zero_start`): _pending_

### 3.2 PENDING-E2E — real Telegram message per tenant

| tenant | `message_id` | Base address | Solana address | measured Base USDC | measured SOL |
|---|---|---|---|---|---|
| A | _pending_ | _pending_ | _pending_ | _pending_ | _pending_ |
| B | _pending_ | _pending_ | _pending_ | _pending_ | _pending_ |

Explorer links must be present in the delivered message body
(`https://basescan.org/address/<base>`, `https://solscan.io/account/<solana>`).

### 3.3 PENDING-E2E — a real worker wake at balance 0 emitting `started`

- scheduler/`launchctl` evidence: _pending_
- receipt `status`: _pending_ (must be `started`)
- receipt `started_rails`: _pending_ (must be exactly the three §4.4 rails)

### 3.4 PENDING-E2E — a real inflow recorded exactly once

- tx hash of the tiny real USDC transfer to tenant A's Base address: _pending_
- `lm_agent_earnings` rows for A with `entry_key = inflow:base:<tx>`: _pending_ (must be exactly 1)
- rows for B: _pending_ (must be 0)
- `kind`: _pending_ (must be `financial_deposit`)
- revenue totals before/after: _pending_ (must be identical)
- second wake over the same window: _pending_ (must report `duplicates: 1, recorded: 0`)

### 3.5 PENDING-E2E — key file modes on the live host

- `stat` of `${LM_DATA_ROOT:-~/.anicca}/wallets/<uid>/base.json`: _pending_ (must be `600`)
- `stat` of `.../solana.json`: _pending_ (must be `600`)
- `stat` of the tenant directory: _pending_ (must be `700`)

### 3.6 PENDING-E2E — live secret scan

- scan of the live DB rows + delivered TG payloads for key material: _pending_ (must be 0)

### 3.7 PENDING-E2E — SSOT row

- `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md` §0.4.6 row 2
  updated to done with pointers to this file: _pending_

---

## 4. Decisions recorded during implementation

Each was measured, escalated to the planner, and folded back into the spec — none
was improvised.

| Finding | Resolution | Spec commit |
|---|---|---|
| `capital_in` is not a ledger kind (`normaliseEntry` and the table CHECK both reject it) | ledger kind `financial_deposit` (already in `EXCLUDED_KINDS`), `capital_class: "capital_in"` as the receipt label | `a12b7174a` |
| `rename(2)` overwrites, so it cannot satisfy "refused if pre-existing" | atomic write is tmp + fsync + `link(2)` + unlink(tmp); `link` fails `EEXIST` | `3e9244f59` |
| `amount_atomic` rows are hard-gated to `currency === "USD"`, so lamports cannot be recorded atomically; converting them needs a price feed | native SOL recorded as `amount_minor` lamports with `currency "SOL"` and `meta {unit, decimals}`; no conversion invented | `31639604c` |
| no cursor table exists and §4.1 adds none | cursor persisted in the job's own receipt (`next_cursor`) and read back from the last completed receipt — the pattern `runtime-up.js` already uses for marketing video history | `31639604c` |
| `lm-onboard.js` cannot enqueue: the runtime queue is the local Postgres (`LM_RUNTIME_DATABASE_URL`), the migration has no GRANT/RLS, and no Netlify function references it | enqueue is the self-heal sweep only; `lm-onboard.js` left untouched, and a wiring test fails if anyone adds queue access to it | `515b835ae` |

Two placement choices, spec-neutral and noted for review: the Solana balance
reader is its own file (`lib/solana-balance.js`) mirroring the existing EVM split
of `agent-wallet.js` / `base-usdc-balance.js`, which keeps the module that
handles secret material free of network calls; and USDC amounts print at full
six-decimal precision when they are not a whole number of cents (`$1.234567`)
rather than being rounded in either direction, while exact cents render `$1.23`
and zero renders `$0.00`.

One pre-existing test was updated: `lib/loop-adapter-registry.test.js` pinned
`manifest.adapters.length === 5` with positional index assertions, so the two new
adapters were **appended** (indices 0-4 keep their meaning), the length bumped to
7, and positional assertions added for indices 5-6.

## 5. Adversary round 1 — dispositions

All rulings in spec §9, §10 and §11 are implemented. Root cause the planner named,
and the thing to remember: **chain data was being copied into an append-only money
ledger without re-deriving the facts that decide an amount or an owner.** MAJOR-2,
4, 6 and 7 were four faces of that one defect.

| ID | Disposition | Commit |
|---|---|---|
| BLOCKER-1 §9.1 colony bot token | fixed — `createColonySecretProvider`, no tenant binding, allowlist that refuses `secret://lm-agent-wallet/**` at construction | `498b68a9f` |
| §9.2 / MAJOR-5 announce recoverable | fixed per §11 — deferred `blocked_no_chat` receipt, re-activation gated on the chat appearing | `8e26d36b8` |
| MAJOR-3 §9.3 sweep starvation | fixed — least-recently-watched ordering + paged tenant read | `00efcb331` |
| MAJOR-4 trusted RPC filter | fixed — recipient, event and token contract re-derived from the payload | `18fa20164` |
| MAJOR-2 `entry_key` granularity | fixed — `inflow:base:<tx>:<logIndex>`, `inflow:solana:<sig>:<accountIndex>` | `c40a95305` |
| MAJOR-6 finality | fixed — finalized/safe head, `removed` dropped, Solana `finalized` | `e7c4def35` |
| MAJOR-7 Solana pairing | fixed — paired by `accountIndex`, every token account counted | `38158b8bb` |
| MINOR-8 CLI enqueue surfaces | fixed by removal | `31d4786d3` |
| MINOR-9 `assertNoSecret` comment | fixed — it is a field-name guard, not a shape scanner | `31d4786d3` |
| MINOR-11 keychain comment | fixed — kept deliberately, no longer claims to guard a running path | `31d4786d3` |
| MINOR-12 empty-`taken` guard | fixed — cursor stays put | `31d4786d3` |
| MINOR-10 `agent-wallet.js` sealing | REJECTED by the planner; the production payout path reads `privateKey` and that module is outside §2 scope. Recorded as a known input to AE-CLOUD-CUSTODY-1. Verified still byte-identical to the merge base. |

## 6. Adversary round 2 — dispositions

All §12 rulings implemented. Class extended by §12.1: progress state is a fact too.

| ID | Disposition | Commit |
|---|---|---|
| NEW-1 Solana cursor overran unprocessed signatures | fixed — `before`-paging until `until` is genuinely reached; ordered `(slot, signature)` cursor; bound hit ⇒ cursor unmoved + `truncated` + operator attention | `56b899563` |
| NEW-2 Base cursor was block-only | fixed — `(block, log_index)`, mid-block resumable, exact first-unprocessed position | `56b899563` |
| NEW-3 `null` `getTransaction` treated as empty | fixed — unreadable, cursor held, bounded retries, then moved past while named in `needs_operator_attention` | `56b899563` |
| NEW-4 ordering advanced only on success | fixed — advances on ATTEMPT; decisions extracted to `lib/wallet-sweep-receipts.js` so the invariant drives the real query | `56b899563` |
| NEW-5 `uiTokenAmount.decimals` trusted | fixed — present, whole, equal to `USDC_DECIMALS`, equal across paired pre/post | `386501eed` |
| NEW-6 `log.data` unbounded | fixed — exactly `0x` + 64 hex before it is read as money | `386501eed` |
| NEW-7 `removed !== true` | fixed — safe polarity: only `false` or absent accepted | `386501eed` |
| NEW-8 Solana balance at `confirmed` | fixed — `finalized`, and not a caller option | `386501eed` |
| NEW-9 `parsed.uid \|\| tenantId` | fixed — an absent uid fails closed instead of trusting the requester | `386501eed` |
| provider asymmetry | fixed — colony method renamed `getColonySecret(ref)`; both crossed wirings now throw at construction | `386501eed` |
| §12.2 drain invariants | shipped — `lib/wallet-drain-invariants.test.js` | `56b899563` |

Scope re-verified against the merge base (`249d6a819`): 31 files changed, **zero
outside `apps/life-manager/` + `docs/`**, `lib/agent-wallet.js` and `lm-onboard.js`
both byte-identical.
