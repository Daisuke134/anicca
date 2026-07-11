# Impl-review iteration 2 notes -- franklin-ledger-push

Fresh-context adversary, zero builder context, worked entirely from `runtime/loop/ledger-publish.mjs`
(6d8eee36), `runtime/loop/__tests__/ledger-publish.test.mjs`, `runtime/loop/index.mjs`, the feature's
`specs/behavioral-spec.md` / `specs/verification-architecture.md`, and iteration-1's own
findings/verdict. No Bash tool available; relied on Read/Grep/Glob against the actual worktree files,
including `.git/config` (confirms origin = `https://github.com/Daisuke134/anicca.git`, no embedded
token) and `~/.gitconfig` (confirms auth is via the global `gh auth git-credential` helper).

## Iteration-1 findings: disposition (see verdict.json's `iteration1_findings_disposition`)

FIND-001/002/003 are genuinely, structurally killed -- I traced every `git()` call site in the file
and confirmed `repoRoot` is touched exactly once, read-only. FIND-004/005 are only partially killed:
the new tests are real (not mocked) and the new recovery function is logically sound in isolation, but
both reopen in modified form once you ask "what actually triggers divergence in THIS topology" instead
of taking the test's own artificial outside-writer trigger at face value.

## What I did NOT find a problem with

- The leak test (PROP-712) is genuinely thorough: asserts HEAD, `status --porcelain`, current branch,
  and origin's own `main` ref are all byte-identical before/after, AND that the published branch
  contains ONLY README.md + `<instance>.jsonl`. No weaseling here.
- `projectLedgerLine()`'s per-field allowlist logic (type-checked, fail-closed default) is internally
  correct -- I checked every branch against REQ-702's text.
- The two-layer redaction (private-key hex + broader base58/hex) is correctly layered and capped at
  200 chars, verified against PROP-709's own test which fabricates all three secret shapes at once.
- The mkdir-atomic lock's pid-staleness reclaim is correct; the PID-reuse ABA edge case is real but its
  worst-case impact is a skipped cycle (retried next wake), not data loss or corruption -- acceptable.
- Origin-URL/credential resolution: verified via `.git/config` + `~/.gitconfig` that the design's
  "resolve read-only from the shared checkout, push from the dedicated clone" approach is sound in
  principle, since the `gh auth git-credential` helper is host-global, not directory-scoped -- this is
  NOT a broken-auth design. (Whether the currently-configured `gh` identity actually has *write* scope
  on `Daisuke134/anicca` is outside what a file-only review can confirm -- flagged as part of FIND-005
  instead of asserted as broken.)

## The two blocking findings, in one sentence each

- **FIND-001**: the published branch can never actually prove "the balance grows" because the file it
  publishes (`state/ledger.jsonl`) never contains the money fields (`net_usdc`/`tx`/`sig`) at all --
  those live in a separate file this feature never reads.
- **FIND-002**: the divergence-recovery the redesign added only fires on a *rejected* push; a
  publish-repo that gets lost/recreated between a local commit and its later push produces a *clean*
  fast-forward instead of a rejection, so the recovery never triggers and the gap is silently marked
  as successfully pushed.

Both are reachable from the code as written, not hypothetical; both directly contradict a claim the
spec itself makes in prose (behavioral-spec.md:5-6 and :227-238 respectively).
