# Resolution Notes — iteration-6 spec review findings (FIND-501..504)

**feature**: anicca-agent-spawn · **mode**: strict · **date**: 2026-07-07

Iteration-6's Phase 1c spec review FAILed with 4 findings (1 critical, 2 major, 1 minor). This note
records exactly what changed, per finding, with line ranges in the two spec files as they stand after
this revision (`specs/behavioral-spec.md`, `specs/verification-architecture.md`, both now labeled
"iteration 6, revised").

---

## FIND-501 (critical — the most serious defect found across all six spec-review iterations)

**Root cause confirmed independently**: a full read of the real, live
`/Users/anicca/anicca/skills/earn/lib/resolve-identity.mjs` and its own test suite
(`/Users/anicca/anicca/runtime/loop/__tests__/resolve-identity.test.mjs`) proves
`resolveEvmPrivateKey`/`resolveSolanaSecret` gate their legacy-fallback resolution on
`effectiveHome === path.join(HOME, '.anicca')` (EVM) / `path.join(HOME, '.blockrun')` (Solana) —
deliberately returning `null` for any `HOME`/`ANICCA_HOME` value that isn't EXACTLY each citizen's own
real, distinct root. `install.sh:26` confirms automaton's real default is `$HOME/.anicca`. A live
filesystem check of this coordinator host (2026-07-07, file EXISTENCE only, key CONTENT never
read/printed) additionally confirmed the real, on-disk locations: automaton's EVM key lives at
`/Users/anicca/.automaton/wallet.json` (the LEGACY `$HOME/.automaton/wallet.json` path); Franklin's
Solana secret lives at `/Users/anicca/.blockrun/.solana-session` (the LEGACY `$HOME/.blockrun/
.solana-session` path). With the prior bare-`$HOME` (`/Users/anicca`) seed value, NEITHER of
`resolve-identity.mjs`'s own legacy gates (`.anicca` / `.blockrun` suffix) ever matches — both citizens
would have resolved `null` for every chain.

### Edits made

| File | Location | What changed |
|---|---|---|
| `behavioral-spec.md` | header, line 4 | `revision` bumped from "iteration 5" to "iteration 6"; findings list extended with "AND spec review iteration-6 findings FIND-501..504 resolved". |
| `behavioral-spec.md` | new section, lines 81-98 | New `## Changelog (iteration 5 spec review → iteration 6)` table added, summarizing all 4 findings (FIND-501..504) and their resolutions, following the exact pattern of every prior iteration's changelog. |
| `behavioral-spec.md` | line 45 | The iteration-3 changelog row (FIND-202+FIND-205) that originally asserted "Both today's citizens legitimately share the same `homeDir`... expected, not a bug" is left as an honest historical record (changelogs are append-only in this spec's convention) but gets a new parenthetical: "**[iteration 6 correction, FIND-501]**: this framing was itself found factually incompatible with `resolve-identity.mjs`'s real resolution semantics — see the iteration 6 changelog and REQ-105/REQ-403 below for the corrected, DISTINCT `homeDir` values." |
| `behavioral-spec.md` | REQ-105 section (`### REQ-105`, now lines 535-692), `homeDir` field definition | Rewrote the field definition to remove the "e.g. `/Users/anicca`" example and the "both share the identical value... expected, not a bug" framing. Added a new "**Corrected, resolves FIND-501**" paragraph explaining the co-located ≠ same-`homeDir` distinction, citing `install.sh:26`, `resolve-identity.mjs`'s own legacy-fallback gate, and the test suite's own "foreign spawn... does NOT inherit... -> null" cases for both chains. |
| `behavioral-spec.md` | REQ-105 seed JSON | `"homeDir": "/Users/anicca"` → `"homeDir": "/Users/anicca/.anicca"` for `anicca-a3cdd4` (automaton) and → `"homeDir": "/Users/anicca/.blockrun"` for `Franklin`. |
| `behavioral-spec.md` | REQ-105, paragraph immediately after the seed JSON | Rewrote to state the corrected values are each citizen's REAL, DISTINCT resolved root, remove the "legitimately share the identical `homeDir`... expected, not an error" claim, and add the live filesystem-existence confirmation (file paths, non-null resolution, content never read/printed) that proves the corrected values actually resolve real key material via `resolve-identity.mjs`'s own legacy-fallback branch. |
| `behavioral-spec.md` | REQ-403 section (`### REQ-403`, now lines 1656-1758), after the existing "Scoping correction" paragraph | New "**Seed-data correction (resolves FIND-501 — critical)**" paragraph: explains why the live-comparison half is only a genuine proof under corrected `homeDir` values, gives the exact real resolution derivation for both citizens, and explicitly confirms REQ-101/REQ-402's balance-lookup design (public-RPC `readCitizenBalances`, keyed on `walletAddress`, never `homeDir`) is UNAFFECTED by this correction — closing off the residual-doubt question the finding raised. |
| `behavioral-spec.md` | REQ-403 Acceptance Criteria | New bullet added: "**(resolves FIND-501)**" — states the exact expected resolved paths for today's two real citizens under the corrected seed data (`/Users/anicca/.automaton/wallet.json`, `/Users/anicca/.blockrun/.solana-session`), both confirmed present on disk 2026-07-07, both non-null. |
| `verification-architecture.md` | header, lines 5-32 | `revision` bumped to "iteration 6, revised"; findings list and change-summary prose extended for FIND-501..504. |
| `verification-architecture.md` | Purity Boundary Map, `citizens.json` row (line 39) | Inserted a "**corrected, resolves FIND-501 (critical)**" clause giving the corrected, distinct `homeDir` values and restating the co-located ≠ same-`homeDir` distinction. |
| `verification-architecture.md` | Purity Boundary Map, `resolve-identity.mjs` row (line 45) | Appended a "**Corrected, resolves FIND-501**" clause with the exact real resolved file paths for both citizens under the corrected seed data, confirmed present on disk 2026-07-07. |
| `verification-architecture.md` | `PROP-403b` (Proof Obligations table) | Rewrote the Description to require the corrected, distinct `homeDir` values; rewrote the Tool/Method column to give the full derivation (legacy-fallback branch, exact real file paths, confirmed present, non-null) and to state explicitly what the prior bare-`$HOME` value would have produced (`null` for both citizens, vacuous). |
| `verification-architecture.md` | Gate item (1a) (REQ-105 end-to-end read) | Added a clause requiring the adversary to confirm each entry's `homeDir` is the real, distinct `ANICCA_HOME` root (not the shared bare `$HOME`), citing the corrected values and the live-resolution proof. |
| `verification-architecture.md` | Gate item (11) (REQ-403 audit) | Added a clause requiring the adversary to confirm each citizen's corrected `homeDir` actually resolves real, non-null key material (never `null`, which the prior seed value would have produced for both citizens on every chain). |

---

## FIND-502 (major — funding-route citation over-attribution)

**Root cause confirmed by direct read**: `/Users/anicca/anicca/skills/self/spawn-child/config.json`
line 7's literal `funding_route` value is exactly `"solana/8453 -> noble-1 -> osmosis-1 -> akashnet-2
(Skip API smart_relay, 4-hop)"` — no mention of Jupiter/SOL/USDC. The Jupiter SOL→USDC step is
`/Users/anicca/anicca/skills/self/spawn-child/SKILL.md` lines 61-67's own separate, documented
numbered sequence.

**"solana/8453" ambiguity investigated with live evidence, not a guess**: a live query against Skip
API's own public `/v2/info/chains` endpoint (`api.skip.build`, 2026-07-07,
`?include_evm=true&include_svm=true`) confirmed `8453` is Skip API's own real, valid Base-mainnet
`chain_id` (`{"chain_name":"Base","chain_id":"8453","chain_type":"evm"}`), distinct from and alongside
`{"chain_name":"Solana","chain_id":"solana","chain_type":"svm"}`. A live `POST
api.skip.build/v2/fungible/route` query, sourcing from Base-native USDC
(`0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`, the exact address this codebase's own
`skills/economy/gig/lib/escrow.mjs::USDC_BASE_MAINNET` already uses) to `uakt` on `akashnet-2`,
returned a real, computable route: `chain_ids: ["8453","noble-1","osmosis-1","akashnet-2"]`, first hop
a `cctp_transfer` (Circle CCTP, Base→`noble-1`), no Jupiter step. A symmetric query from Solana-native
USDC confirmed the identical back-half (`chain_ids: ["solana","noble-1","osmosis-1","akashnet-2"]`,
first hop also a `cctp_transfer`). Conclusion: `"solana/8453"` names TWO real, independently valid
first-hop entry points into the SAME shared back-half — not a stray/conflated label — meaning EITHER
of the colony's two current citizens (Franklin via Solana+Jupiter, automaton via Base+CCTP, no Jupiter)
can independently enter this documented route.

### Edits made

| File | Location | What changed |
|---|---|---|
| `behavioral-spec.md` | REQ-304 section (`### REQ-304`, now lines 1287-1375), "AKT funding route correction" paragraph | Split into two paragraphs: (1) corrected citation attribution — `config.json`'s literal field quoted verbatim for the 4-hop bridge; `SKILL.md`'s own step 1-4 sequence cited separately for the Jupiter pre-step, explicitly stated as two separate artifacts never merged; (2) new "**The `\"solana/8453\"` first-hop ambiguity, investigated**" paragraph with the full live Skip API evidence (both endpoint queries, exact response fields, exact addresses/chain IDs), concluding with the confirmed dual-entry-point finding. |
| `behavioral-spec.md` | REQ-304 Acceptance Criteria | New bullet: "**(resolves FIND-502)**" — requires citing `config.json`/`SKILL.md` separately, and requires the funding-transfer code to enter the route at whichever citizen's own real first hop applies (`"solana"` or `"8453"`), never hardcoding Solana-only. |
| `verification-architecture.md` | `PROP-304d` (Proof Obligations table) | Rewrote Description to split the citation exactly as above; rewrote Tool/Method to require confirming the two-source citation is never merged. |
| `verification-architecture.md` | new `PROP-304e` (Proof Obligations table, inserted immediately after PROP-304d) | New proof obligation recording the confirmed dual-entry-point capability, Tier 0, citing the exact live Skip API queries/responses (chain registry + route-planning endpoint) and requiring Phase 2 to support whichever entry chain matches the actually-funding citizen. |
| `verification-architecture.md` | Verification Strategy, Tier 0 list | Added "AND its Base-native-entry Skip API route confirmation (PROP-304e, resolves FIND-502)" after the REQ-304 no-human-funded-source mention. |
| `verification-architecture.md` | Gate item (7) (REQ-304 funding-source) | Rewrote the multi-hop-route clause to cite the two sources separately, and added a new clause requiring the adversary to confirm both real entry points (`"solana"`, `"8453"`) are supported, not a hardcoded Solana-only path. |

---

## FIND-503 (major — dual-chain fail-closing granularity)

### Edits made

| File | Location | What changed |
|---|---|---|
| `behavioral-spec.md` | REQ-101 section (`### REQ-101`, now lines 219-376), "Dual-chain balance handling" paragraph | New "**Per-chain independent fail-closing (resolves FIND-503)**" paragraph added immediately after the existing dual-chain-summing paragraph: states each populated chain fails closed INDEPENDENTLY of the other, gives the exact mixed-outcome contribution formula (`0` for the failed chain + the real value for the successful chain), and cross-references the `ethPrice()`/`solPrice()` per-fetch fail-closed precedent. |
| `behavioral-spec.md` | REQ-101 Edge Cases | New bullet: "**(resolves FIND-503)**" — states the mixed success/failure sub-case explicitly, distinguishing it from the pre-existing "one chain is empty" (both succeed, one is zero) sub-case directly above it. |
| `behavioral-spec.md` | REQ-101 Acceptance Criteria | New bullet: "**(resolves FIND-503)**" — the concrete fixture requirement (one chain fails, other succeeds with a real nonzero value → total equals only the successful chain's value, never `0`). |
| `verification-architecture.md` | new `PROP-101g` (Proof Obligations table, inserted immediately after PROP-101f) | New proof obligation: Tier 1/2, unit/integration test with a fixture dual-wallet citizen where exactly one chain's query fails while the other genuinely succeeds with a real, independently-verifiable nonzero value (and the symmetric case) → assert the returned total equals only the successful chain's own normalized value. |
| `verification-architecture.md` | Verification Strategy, Tier 1 list | Added "AND its per-chain-independent fail-closing fixture for a dual-wallet citizen with exactly one chain failing (PROP-101g, resolves FIND-503)" to the REQ-101 entry. |
| `verification-architecture.md` | Verification Strategy, Tier 2 list | Added "AND its per-chain-independent fail-closing check (PROP-101g, integration half, resolves FIND-503)" to the REQ-101 entry. |
| `verification-architecture.md` | Gate item (1d) (REQ-101 dual-chain handling) | Added a clause requiring the adversary to confirm the mixed-fixture behavior (PROP-101g) — one chain fails, other succeeds, total equals only the successful chain's value, never `0` for the whole citizen. |

---

## FIND-504 (minor — no captured CLI evidence transcript)

### Evidence captured

Both cited CLIs were confirmed installed on this coordinator host (`/opt/homebrew/bin/provider-services`,
version `v0.11.1`; `/opt/homebrew/bin/nosana` via npm global `@nosana/cli@1.0.131`) and invoked live,
2026-07-07. The complete, raw, dated transcript (both `--help` outputs in full, plus `which`/version
output, a UTC+local timestamp header, and hostname) is written to:

```
reviews/spec/iteration-6/evidence/cli-help-2026-07-07.txt
```

### Edits made

| File | Location | What changed |
|---|---|---|
| `behavioral-spec.md` | Nosana/Akash re-verification table (lines ~178-179) | Both rows' evidence column rewritten to point at the captured evidence file path, with the "New finding" annotation extended to "evidence captured to disk, resolves FIND-504". |
| `behavioral-spec.md` | Purity boundary table, "Akash job deploy" row (line ~204) and "Nosana job deploy — post-boot secrets-injection" row (line ~206) | Both `lease-shell --help`/`job ssh --help` citations extended with "raw transcript captured at `reviews/spec/iteration-6/evidence/cli-help-2026-07-07.txt` — resolves FIND-504". |
| `behavioral-spec.md` | REQ-302 section, "Post-boot secrets-injection channel" paragraph (line ~1107) | `nosana job ssh --help` citation rewritten to quote the raw captured output and point at the evidence file. |
| `behavioral-spec.md` | REQ-303 section, "Post-lease secrets-injection step" paragraph (line ~1211) | `provider-services lease-shell --help` citation rewritten to quote the raw captured output and point at the evidence file. |
| `verification-architecture.md` | Purity Boundary Map, post-lease/post-job secrets-injection row (line 59) | Citation extended to point at the evidence file. |
| `verification-architecture.md` | `PROP-302c`, `PROP-303e` (Proof Obligations table) | Both Tool/Method columns extended to cite the captured evidence file path alongside the `--help` flag name. |

---

## Cross-cutting

- Both spec files' revision headers were bumped from "iteration 5" to "iteration 6" and their
  changelog/summary prose extended to list FIND-501..504 as resolved, following the exact pattern
  every prior iteration already established.
- No changes were made to any REQ/PROP outside what each finding required; no new features were
  introduced beyond the two new proof obligations (`PROP-304e`, `PROP-101g`) the findings explicitly
  called for.
- `state.json`, the review manifest, and verdict files were NOT touched, per the task's explicit
  instruction — only `specs/behavioral-spec.md`, `specs/verification-architecture.md`, this
  RESOLUTION-NOTES.md file, and the new evidence file were written.
