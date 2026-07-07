# Spec Review Verdict — anicca-agent-spawn — iteration 12 (FRESH-CONTEXT ADVERSARY)

**Overall verdict: FAIL**

## Prior-iteration finding reconfirmation (FIND-1001, FIND-1002)

Both were re-verified against the REAL, current source, fresh, with zero carryover assumptions from any prior pass.

**FIND-1001 (critical, atomic bootstrap exclusive-create) — GENUINELY RESOLVED.**
`~/anicca/skills/economy/gig/lib/lock.mjs::tryCreateLockFile` (lines 108-117) really is:
```js
async function tryCreateLockFile(file) {
  try {
    const handle = await fs.open(file, "wx");
    await handle.close();
    return true;
  } catch (e) {
    if (e.code === "EEXIST") return false;
    throw e;
  }
}
```
No separate `existsSync`/`stat` check precedes this call anywhere in `tryCreateLockFile`, `acquire()`, or `reclaimStaleLock()`. REQ-105's corrected bootstrap step (behavioral-spec.md:714-752) mirrors this shape exactly, one atomic `fs.open(CITIZENS_REGISTRY_PATH, 'wx')` call, `EEXIST` → write nothing, read-only. PROP-105l's structural half (verification-architecture.md:250) correctly binds this to "mirroring `lib/lock.mjs::tryCreateLockFile`'s own exact shape." Resolved.

**FIND-1002 (major, purity boundary) — GENUINELY RESOLVED.**
The Purity Boundary Map row for `registry-path.mjs` (verification-architecture.md:90) is now labeled "Effectful Shell," matching `CITIZENS_REGISTRY_PATH`'s dependency on the already-Effectful `resolveStateDir` and `COORDINATOR_HOME`'s dependency on a real `os.homedir()` read. PROP-105m's Tier-2 design — launch a real child process with a *different* real `HOME`, assert that process's own `COORDINATOR_HOME` equals *its own* `os.homedir()` output — genuinely catches both a hardcoded-literal implementation (mismatch against the child's distinct HOME) and a `process.env.HOME`-substitute implementation (caught separately by PROP-105m's own Tier-0 structural check, which explicitly bans that substitution). Each spawned child process gets a fresh module registry with zero shared JS-heap state with the parent, so this design is sound for the property it claims to prove. Resolved.

## New findings (full fresh pass, entire spec, both files read end-to-end)

### FIND-1101 (CRITICAL, NEW) — REQ-102 vs REQ-305 cooldown-timer contradiction; two approved PROPs cannot both be satisfied

REQ-102's own EARS clause and edge case (behavioral-spec.md:494-500, 530-533) state, unambiguously, that the cooldown clock is measured "since the colony's last spawn attempt (**success OR failure** — see REQ-305)" and that this is "a hard gate regardless" — i.e. a failed attempt DOES reset the cooldown exactly like a success. REQ-102's own pinned `decideColonySpawn` signature (behavioral-spec.md:541-543) has a single scalar `lastSpawnAttemptMs` and **no parameter capable of counting or listing recent failed attempts**.

REQ-305, by contrast, states (behavioral-spec.md:1777, 1838-1841) that "REQ-102's SPAWN_COOLDOWN_DAYS timer SHALL NOT be considered 'consumed' by a failed attempt," explicitly calling this a "cooldown-exemption," and mandates a cap-of-3-failed-attempts-per-window mechanism where a 4th attempt within the same window IS rate-limited but the first 3 are not.

These are mutually exclusive at the level of two *approved, binding* proof obligations in the same table: **PROP-102b** (verification-architecture.md:230 — huge surplus + `lastSpawnAttemptMs` inside the window ⇒ always `rate_limited`) and **PROP-305c** (verification-architecture.md:294 — 3 failures within one window must all return `eligible:true`, only the 4th is blocked). If failures update `lastSpawnAttemptMs` (REQ-102's own literal reading), the *second* of PROP-305c's "3 failures within one window" is already blocked by PROP-102b's own rule — the fixture as specified cannot occur. If failures don't update it (REQ-305's reading), PROP-305c's cap-of-3 mechanism has no parameter in REQ-102's own pinned signature through which to be implemented at all.

This is a genuine architectural regression from this feature's own cited prior art: `~/anicca/skills/self/spawn/lib/spawn-decision.js::decideSpawn` (confirmed by direct read) uses an *array* scan over `children[].spawned_ms`, not a scalar "last attempt" timestamp — a strictly richer shape that could naturally support exactly what REQ-305 wants. REQ-102's collapse to a bare scalar is what makes REQ-305's own binding proof obligation unimplementable as specified. Routed to Phase 1a.

### FIND-1102 (MAJOR, NEW) — REQ-304's multi-citizen sequential co-funding success path has zero proof obligation

REQ-304's own edge case (behavioral-spec.md:1743-1749) explicitly promises that a spawn CAN succeed via "two SEPARATE single-signer transfers to the SAME child wallet" when no single citizen alone holds enough surplus but multiple citizens' surplus together does ("sequential individual transfers are allowed"). No proof obligation anywhere in verification-architecture.md exercises this success path: PROP-304b only bounds a single transfer's ceiling, PROP-304c only tests the *blocked* no-single-citizen-suffices case, and PROP-304a/PROP-304d/PROP-304e cover unrelated concerns (human-funded-wallet exclusion, Akash's AKT bridge route). A Phase-3 implementation that never attempts a second sequential transfer at all — silently contradicting REQ-304's own "OR once the colony has more than one surplus-holding citizen able to co-fund" promise — would pass every currently-specified PROP-304 obligation. Routed to Phase 1a.

## Evidence base for this pass

Full end-to-end read of `behavioral-spec.md` (2253 lines) and `verification-architecture.md` (696 lines), plus fresh reads of: `~/anicca/skills/economy/gig/lib/lock.mjs`, `~/anicca/skills/_shared/lib/is-self-funded.mjs`, `~/anicca/skills/self/spawn/lib/{state-path.js,child-spec.js,ledger.js,spawn-decision.js}`, `~/anicca/skills/economy/gig/lib/ensure-agent-id.mjs`, `~/anicca/skills/earn/lib/resolve-identity.mjs` (grep-targeted), and a directory-level confirmation of the ERC-8004 registry addresses cited in REQ-204.

No positive summary is offered for the requirements not implicated by FIND-1101/1102 beyond the specific evidence cited above and in FIND-1001/1002's reconfirmation — those specific citations were independently re-verified against real, current source this pass, not assumed carried-over from prior iterations.
