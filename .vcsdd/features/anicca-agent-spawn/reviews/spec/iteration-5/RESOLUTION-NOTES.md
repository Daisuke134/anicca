# Resolution Notes — anicca-agent-spawn spec review iteration-5

**Findings addressed**: FIND-401 (critical), FIND-402 (critical), FIND-403 (major), FIND-404 (critical),
FIND-405 (major). All 5 were confirmed genuinely present by re-reading the real, current source before
writing any fix (see "What was verified" per finding below). Edits were made to `specs/behavioral-spec.md`
and `specs/verification-architecture.md` only; `state.json`, review manifests, and verdict files were not
touched, and nothing was committed/pushed.

---

## FIND-401 + FIND-402 (resolved together — the deep architectural fix)

### What the architect's brief got right (verified independently)

- `~/anicca/skills/self/spawn-child/SKILL.md` (read in full): confirmed it is exactly what the brief
  describes — a narrow, read-only Akash funding-READINESS gate + a corrected SDL template, explicitly
  documented as sitting in front of `../spawn/run.sh --host=akash`, and explicitly documented as NOT
  itself deploying or moving money ("It never moves money").
- `~/anicca/skills/self/spawn/scripts/cloud-init.sh` (read in full): its own header comment — "SECURITY:
  NO secret VALUES in user_data (DO metadata is readable). Secrets are SCP'd to /opt/anicca.env after
  boot and loaded via EnvironmentFile=." — confirmed verbatim.
- `~/anicca/skills/self/spawn-child/sdl/child.yaml` and `~/anicca/skills/self/spawn/scripts/
  deploy-akash.sh`'s inline default SDL (both read in full): confirmed NEITHER sets any secret/key
  material in their `env:` block — both boot via a bare `git clone + install.sh` with zero secret
  channel, exactly as FIND-401 describes.
- `~/anicca/skills/self/spawn-child/config.json` + `lib/akt-cost-gate.js` (read in full, including its
  own unit test file): confirmed the real, already-tested `computeSpawnGate({balanceAkt, costAkt,
  bufferAkt}) → {ready, reason, thresholdAkt, shortfallAkt}` function and the real config values
  (`spawn_cost_akt: 25`, `buffer_akt: 1`, `funding_route: "solana/8453 -> noble-1 -> osmosis-1 ->
  akashnet-2 (Skip API smart_relay, 4-hop)"`).

### What I additionally verified myself (beyond the architect's brief)

- **`provider-services lease-shell --help`** (installed CLI, run live in this session, 2026-07-07):
  confirmed the real primitive exists: `Usage: provider-services lease-shell <service-name> <command>
  [flags]`, with `--dseq`, `--gseq` (default `1`), `--oseq` (default `1`), `--provider`, `--from`, and
  `--stdin` ("connect stdin") all present as real, documented flags. This is the exact Akash exec-into-
  running-container primitive FIND-401 identified as needed but unconfirmed.
- **`nosana job ssh --help`** and **`nosana job --help`** (installed CLI, run live in this session,
  2026-07-07): confirmed `nosana job ssh [options] <job> [port]` — "Open an SSH shell into a running
  job" — a real, present, genuine SSH-based exec channel into a running Nosana job. This was NOT part of
  the architect's original brief (which only asked me to flag a Nosana-side gap as a known limitation if
  I could not verify a mechanism) — I found a real, concrete Nosana equivalent and used it, rather than
  leaving REQ-302 with an unresolved wallet-injection gap.
- **Honesty check on the DO path** (explicitly requested by the brief): `grep -rn "scp\|SCP" ~/anicca/
  skills/self/spawn/ ~/anicca/skills/self/spawn-child/` returns ONLY the `cloud-init.sh` header COMMENT
  itself — **no actual `scp` invocation exists anywhere in `run.sh`'s DO path**. The brief's framing
  ("already-proven DO path") is therefore only half-right: the SECURITY PATTERN (boot secretless, inject
  post-boot) is genuinely established and cited correctly as precedent, but the DO path's own
  IMPLEMENTATION of that pattern is incomplete/undocumented-in-code, not "already proven." This is
  reported honestly in the spec (Scope section + REQ-303's new paragraph) rather than silently assumed.
  Since DO is not one of this feature's two cloud targets (REQ-302/303 are Nosana/Akash only), this gap
  is correctly out of scope for this feature and is not fixed here — only accurately described.
- **`node:22-bookworm` default `HOME`**: I attempted to verify live via `docker run --rm node:22-bookworm
  sh -c 'echo $HOME'` but the local Docker daemon is not running in this environment, so this could NOT
  be independently confirmed by executing a container in this session. The spec's `HOME=/root` value is
  based on the well-known fact that the official Node.js Docker images do not set a `USER` directive
  (root is the default user, and Debian's root user has `HOME=/root` per `/etc/passwd`) — this is stated
  in the spec as the documented default, not as a live-verified fact from this session. Flagged here so
  Phase 2 implementation re-confirms it against a real running container before relying on it.

### The fix

`behavioral-spec.md`:
- Scope section (`behavioral-spec.md:129-135`, new paragraph "Also reconciled, iteration 5"): cites
  `spawn-child/` as reused prior art for REQ-303's funding-readiness check and REQ-304's funding-route
  citation.
- REQ-201 (`~line 628`, new edge case): generated key material must be delivered ONLY via REQ-302/303's
  post-boot injection channel, never written into any boot-time artifact.
- REQ-301 (EARS clause, rewritten): "immediately relocated" is corrected to mean relocated via the
  post-boot injection channel the moment the lease/job is confirmed running — never synchronously at
  generation time (no channel exists before boot).
- REQ-302 (`behavioral-spec.md:1025-1040`, new paragraph "Post-boot secrets-injection channel"): adds the
  Nosana-side fix via `nosana job ssh <job> [port]`, with an explicit honesty caveat that the exact
  non-interactive invocation shape is not independently re-verified beyond `--help` output in this
  revision and must be confirmed at Phase 2 against the actually-installed CLI.
- REQ-303 (`behavioral-spec.md:1086-1160`, three new paragraphs: "Funding-readiness gate reuse",
  "Child-specific SDL variant — explicit HOME", "Post-lease secrets-injection step"): the core fix.
  Specifies `computeSpawnGate` reuse (distinguishing it from REQ-102's colony-wide threshold), the new
  `HOME=/root` SDL line (FIND-403, folded in here since it's the same artifact), and the new
  `provider-services lease-shell ... --stdin` post-lease-active injection step, with exact flag names and
  an honest note that `deploy-akash.sh`/`akt-treasury.sh` stay byte-identical while this new step is new
  orchestration code.
- REQ-304 (`behavioral-spec.md:1212-1225`, new paragraph "AKT funding route correction"): replaces the
  false single-signer/single-transaction claim for Akash specifically with the real, documented multi-hop
  route from `spawn-child/config.json`, while preserving that claim's accuracy for same-chain transfers
  (gas-seed, Nosana-side same-chain funding).
- Purity boundary analysis table (`~line 147-152`): updated "Akash job deploy" row, added new rows for
  the readiness-gate reuse, the Nosana secrets-injection step, and updated the shelter-cost-funding row.

`verification-architecture.md`:
- Purity Boundary Map (`~line 42-52`): mirrors the same additions/corrections.
- New PROP IDs: PROP-201d (private key never in boot artifact), PROP-303d (`computeSpawnGate` reuse),
  PROP-303e (post-lease secrets-injection), PROP-302c (Nosana post-boot secrets-injection), PROP-304d
  (AKT multi-hop route). PROP-303a's scope corrected to exclude the new SDL variant/injection step.
- Verification Strategy tier lists and Gate items (6a), (7) updated to require the adversary confirm
  these new mechanisms and the corrected scope of "unmodified reuse."

### Known limitations left honestly unresolved (not silently assumed)

1. The exact non-interactive invocation shape of `nosana job ssh` for a single `cat > /opt/anicca.env`
   payload delivery (as opposed to an interactive shell) is confirmed only via `--help` output in this
   revision, not by an actual successful invocation — Phase 2 must confirm this against the real,
   installed `@nosana/cli` version before relying on it.
2. `node:22-bookworm`'s default `HOME=/root` is asserted from well-known Docker image convention, not
   from a live container run in this session (Docker daemon unavailable) — Phase 2 must re-confirm.
3. The DO path's own SCP step (cited only as security-pattern precedent) is confirmed, by direct read of
   `run.sh`, to not actually exist in code yet — this is explicitly out of scope for this feature (DO is
   not a REQ-302/303 target) and is reported here only for honesty, not fixed.

---

## FIND-403 (SDL HOME env — folded into the REQ-303 fix above)

**What was verified**: direct reads of `~/anicca/skills/self/spawn-child/sdl/child.yaml` (lines 6-11) and
`~/anicca/skills/self/spawn/scripts/deploy-akash.sh`'s inline default SDL (lines 56-59) confirm neither
sets `HOME`/`ANICCA_HOME` — both list only `AUTOMATON_GOAL=earn` and `ANICCA_CHILD_ID=${CHILD_ID}`.

**Fix**: `behavioral-spec.md:1105-1118` ("Child-specific SDL variant — explicit `HOME`") specifies a new,
small SDL variant adding exactly one `env:` line, `HOME=/root`, and explicitly scopes PROP-303a's
"zero source modification" claim away from this new variant.
`verification-architecture.md`: new PROP-303f; PROP-203c's Method column (`~line 173`) corrected to test
the ACTUAL rendered SDL post-fix, not the original template (which is now confirmed, by direct read, to
fail this criterion).

---

## FIND-404 (dual evm+solana balance handling)

**What was verified**: direct read of REQ-101's existing Edge Cases (only 2 balance shapes previously
enumerated: failed RPC query, native-token-only) and REQ-202/REQ-305 (confirming every Nosana-path child
legitimately carries both `walletAddress.evm` and `walletAddress.solana`) — confirming the gap was real
and not already covered elsewhere in the spec.

**Fix**: `behavioral-spec.md:265-278` (new paragraph "Dual-chain balance handling") specifies the SUM
rule explicitly as a deliberate design decision, plus a new edge case and acceptance criterion.
`verification-architecture.md`: new PROP-101f; the `readCitizenBalances` Purity Boundary Map row and
Gate item (1d) updated to require the adversary confirm this is a stated decision, not an ambiguity.

---

## FIND-405 (REQ-402 ledger-write ambiguity recurrence)

**What was verified**: direct read of `~/anicca/skills/self/spawn/lib/ledger.js` (re-confirmed it exports
exactly `{readChildren, appendChild}`, no update/upsert primitive) and REQ-402's own existing text
(confirmed the phrase "in that SAME ledger row" and "flips... to bootstrap_failed" never explicitly
stated the appendChild/last-write-wins mechanism the way REQ-101/REQ-305 already do for their own writes).

**Fix**: `behavioral-spec.md:1464-1476` (REQ-402 EARS clause) and the Acceptance Criteria bullet
(`~line 1281` region) rewritten to explicitly state the relabeling is an `appendChild` of a new row,
cross-referencing REQ-101's last-write-wins reduction by name — the identical clarification pattern
FIND-301 already established for REQ-101/REQ-305.
`verification-architecture.md`: the `ledger.js` Purity Boundary Map row, PROP-402a's description, and
Gate item (10) all updated to require the adversary confirm the appendChild mechanism explicitly, not
infer it.

---

## Files touched

- `/Users/anicca/anicca-project/.vcsdd/features/anicca-agent-spawn/specs/behavioral-spec.md`
- `/Users/anicca/anicca-project/.vcsdd/features/anicca-agent-spawn/specs/verification-architecture.md`
- This file (new)

No other files were touched. `state.json`, review manifests, and verdict files are untouched, and no
commit/push was performed, per instructions.
