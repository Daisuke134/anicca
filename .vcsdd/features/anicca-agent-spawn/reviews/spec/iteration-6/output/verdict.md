# Spec Review Verdict — anicca-agent-spawn — iteration 6 (Phase 1c)

**Overall verdict: FAIL**

Fresh-context review, zero prior conversation history. Every citation below was independently
re-read from the real, current file at the path given (not inferred from the spec's own prose).
Tool note: this review session had Read/Write/Edit/Grep/Glob only -- no shell/exec tool was
available, so the manifest's explicit instruction to independently *run* `provider-services
lease-shell --help` / `nosana job ssh --help` could not be literally discharged this iteration
(see FIND-504). Everything else the manifest asked for was independently re-verified against real,
current source files.

## Part 1 — Verification of the 5 prior findings (FIND-401..405)

All 5 are **genuinely resolved on the specific claim each one made**, confirmed by directly
re-reading the real source files the spec cites:

| Finding | Verdict | Key confirming evidence |
|---|---|---|
| FIND-401 (no secrets-injection channel) | Resolved | `akt-cost-gate.js` signature, `deploy-akash.sh`'s `AKASH_SDL_TEMPLATE` mechanism, and `cloud-init.sh`'s SCP-claim-vs-`run.sh`'s-real-DO-path honesty note are all independently confirmed real. The two-phase boot-then-inject sequence's readiness-polling mechanism is concretely specified (reuses `deploy-akash.sh`'s existing `ACTIVE`/`SENT` poll loops for Akash; Nosana's own `--wait` flag) — this resolves the manifest's explicit readiness-polling question. Live CLI `--help` re-execution itself could not be repeated this session (FIND-504). |
| FIND-402 (spawn-child prior art + multi-hop route) | Resolved (core claim) | `config.json`'s `spawn_cost_akt:25`/`buffer_akt:1` and the multi-hop bridge conclusion are correct. A residual citation-precision gap in exactly this area is filed as new FIND-502. |
| FIND-403 (HOME=/root SDL addition) | Resolved | Neither real SDL artifact sets HOME. Independently traced the fix's interaction with `install.sh:26`'s `ANICCA_HOME=${ANICCA_HOME:-$HOME/.anicca}` default: a freshly-booted child with `HOME=/root` correctly derives `ANICCA_HOME=/root/.anicca`, distinct from both existing citizens' real roots — no conflict (resolves manifest checklist item (b)). |
| FIND-404 (dual evm+solana summing) | Resolved for the case specified | `is-self-funded.mjs::hasOwnWallet()` tolerates the dual-true shape with no double-counting risk (reserve is subtracted once per citizen regardless of chain count). An adjacent, unaddressed edge case (partial per-chain query FAILURE, not just zero balance) is filed as new FIND-503. |
| FIND-405 (bootstrap_failed cross-reference) | Resolved | REQ-402 now explicitly, by name, cross-references REQ-101's last-write-wins reduction; `ledger.js` reconfirmed `{readChildren, appendChild}` only. |

## Part 2 — Fresh full-spec pass: 4 new findings (FIND-501..504)

### FIND-501 (CRITICAL, verification_readiness + spec_fidelity) — REQ-403's "money-safety" audit cannot reach either real citizen's real key

This is the most serious defect found across all 6 iterations of this feature. REQ-403's live
wallet-collision audit is specified to invoke `resolve-identity.mjs`'s resolvers using REQ-105's
`homeDir` registry field as the `HOME`/`ANICCA_HOME` input. REQ-105 seeds this field with the
**identical, bare `$HOME` value `/Users/anicca` for BOTH of today's real citizens**, explicitly
calling this "expected, not a bug."

A fresh read of `resolve-identity.mjs` and its own pre-existing, already-passing test suite
(`runtime/loop/__tests__/resolve-identity.test.mjs`) proves this cannot work: automaton's real root
is `$HOME/.anicca` and Franklin's is `$HOME/.blockrun` (both independently confirmed by that test
suite's own named test cases, and by `install.sh:26`'s own `ANICCA_HOME` default computation). The
SAME test suite explicitly proves the negative case that matters: any `HOME`/`ANICCA_HOME` value
that is not EXACTLY a citizen's own real root resolves to `null` — by design, to prevent a foreign
spawn from inheriting another instance's key. Feeding the bare, shared `/Users/anicca` value into
these resolvers (as REQ-403 literally specifies) will resolve to `null` for **both** real citizens
today — never their actual signing keys. The audit would therefore either report a vacuous "no
collision" between two nulls (a false sense of security for a requirement whose own text calls this
a fail-closed security-incident-response gate), or, if nulls are special-cased, still never prove
genuine pairwise inequality of real key material.

This gap survived two prior review rounds that touched this exact field (FIND-202 added `homeDir`
to REQ-105; FIND-303 scoped REQ-403's live check to co-located instances) without either round
checking the field's literal seeded VALUE against the resolver's own real, already-tested
semantics — evidence that was available and readable during every one of the 5 prior iterations.

### FIND-502 (major, spec_fidelity) — REQ-304's funding-route citation over-attributes SKILL.md prose to config.json's field

`config.json`'s real `funding_route` field literally reads `"solana/8453 -> noble-1 -> osmosis-1 ->
akashnet-2 (Skip API smart_relay, 4-hop)"` — it never mentions Jupiter/SOL/USDC, and its own
`"solana/8453"` label ambiguously conflates the Solana chain name with Base's own EVM chain ID. The
"Jupiter SOL→USDC" first hop the spec attributes to "config.json's own funding_route field" actually
appears only as prose in a separate file, `SKILL.md`'s numbered list. The multi-hop conclusion
remains correct; the specific field-attribution is imprecise, in exactly the area this feature has
already had to correct once for a related false-attribution reason (FIND-402).

### FIND-503 (major, spec_fidelity) — dual-chain balance summing never addresses a per-chain query FAILURE (only zero balance)

REQ-101's dual-chain edge case explicitly covers "one chain is zero," but neither it nor
PROP-101c/PROP-101f address one chain's RPC query genuinely FAILING while the other succeeds with a
real balance, for the same dual-wallet citizen (the expected shape for every Nosana-path child).
The two plausible readings (per-chain fail-close vs. whole-citizen fail-close) produce materially
different colony-surplus numbers, and no fixture exercises the mixed-failure case.

### FIND-504 (minor, verification_readiness) — live CLI re-execution could not be performed this session

This session's tools were Read/Write/Edit/Grep/Glob only; no shell/exec tool was available, so the
manifest's explicit instruction to independently run `provider-services lease-shell --help` /
`nosana job ssh --help` could not be discharged. Disclosed honestly as a review-process limitation,
not evidence against those primitives. Recommend a captured, dated `--help` transcript be committed
as an evidence file so a future Read-only adversary pass can verify it without shell access.

## Convergence assessment

This is the 6th consecutive FAIL iteration (30+ cumulative findings across iterations 1-6). All
findings through iteration 5 are reconfirmed genuinely resolved on their own terms — the resolution
discipline itself remains sound. But this iteration's fresh, full-file, real-artifact pass again
surfaced a new, evidenced, critical defect (FIND-501) that is arguably more fundamental than any
prior single finding in this feature's history: it falsifies the one requirement (REQ-403) whose
entire stated purpose is preventing a real, catastrophic wallet-collision failure mode, using
evidence that was sitting in this exact codebase, readable, during every one of the 5 prior
iterations. Convergence has not occurred.
