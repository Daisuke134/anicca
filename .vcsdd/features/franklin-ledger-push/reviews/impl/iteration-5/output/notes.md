# impl-review iteration 5 — fresh-context adversary notes (FINAL allowed iteration, lean impl review)

Reviewed commit: 353f6f1f (worktree `/Users/anicca/anicca/.worktrees/ledger-push`). No Bash available
to this adversary session; external test evidence accepted as reported: 223/223 (thinker-executed) --
the pre-existing `integration.test.mjs` ENOTEMPTY `/tmp` teardown race that flaked in earlier
iterations is now reported passing.

## iteration-4 findings disposition (re-verified independently, fresh-context, full file re-read)

- **FIND-001 (major, security_surface -- fill_tid string-form allowlist `SETTLEMENT_ID_VALUE`
  overly broad + redaction-exempt)**: KILLED. Read the entire `ledger-publish.mjs` (814 lines) and
  confirmed `SETTLEMENT_ID_VALUE` no longer exists anywhere as a regex constant -- only
  comment-references documenting its removal remain (lines 219-231, 345). `projectEarnField()`'s
  `fill_tid` case (line 346) is now `isFiniteNumber(value) ? value : undefined` -- no string branch
  at all. Grepped the whole file and confirmed zero remaining occurrences of the removed pattern.
  `isProfitable()`'s Hyperliquid path was independently re-read from the real source
  (`skills/_shared/lib/ledger.mjs:62`, `line.fill_tid != null`) -- presence-only, unaffected by the
  narrowing. The new regression test (`ledger-publish.test.mjs:275-293`) is genuinely non-tautological:
  it constructs BOTH an id-shaped string (`'hl-fill:12345'`) AND a secret-shaped 62-char mixed
  alphanumeric string, both of which sit inside the OLD `SETTLEMENT_ID_VALUE` regex's accepted
  charset/length (`[A-Za-z0-9:_-]{1,128}`) -- if the removed branch were ever reintroduced verbatim,
  this test would fail on both fixtures, making it a real regression guard, not a cosmetic assertion.

- **FIND-002 (minor, dead_code -- `MARKER_DEFAULTS` declared, zero call sites)**: KILLED.
  `readMarker()`'s catch-block (lines 393-399) now derives its fallback from `MARKER_DEFAULTS` via a
  defensive fresh spread-copy of each nested object (correctly avoiding a shared-object mutation leak
  across calls), rather than hand-duplicating the literal. No second, independently-maintained copy of
  the default marker shape remains.

## Amended test fixture (post GitHub secret-scanning push-protection block) — verified

The task flagged that the builder's first push was blocked by GitHub's server-side secret-scanning
push protection on a test fixture matching a Stripe-key format, then rewritten and amended. Verified
the CURRENT fixture (`ledger-publish.test.mjs:286-288`,
`'q9fB2kLmN0pQrStUvWxYz1234567890AbCdEfGhIjKlMnOpQrStUvWxYz0011'`):

- **Scanner-safe**: grepped `runtime/loop/` for every common secret-provider prefix
  (`sk_live_|sk_test_|AKIA|ghp_|gho_|github_pat_|xox[bp]-|-----BEGIN`) -- zero matches anywhere in the
  reviewed code/test tree. The fixture carries none of these recognizable prefixes, so it cannot match
  GitHub push-protection's or gitleaks' default provider-specific rules. It is also not adjacent to a
  `keyword=value`-shaped assignment (the `secretShaped` variable name sits on its own declaration line,
  several tokens away from the string literal, never a direct `secret = '...'` pattern), so gitleaks'
  generic-api-key keyword-proximity rule would not key on it either. TruffleHog's `--only-verified`
  mode (this repo's CI config, `.github/workflows/sec-scan.yml:49,57`) requires a LIVE credential
  verification call to succeed -- a random fixture string cannot verify against any real API, so it is
  structurally unflaggable by that scanner regardless of shape.
- **Still genuinely secret-shaped / meaningful**: independently character-checked the fixture against
  this feature's OWN two redaction regexes -- it contains `0` and `O`, both OUTSIDE the base58 alphabet
  `BASE58_SECRET_RUN` requires (`[1-9A-HJ-NP-Za-km-z]`), and contains many letters (g,j,k,l,m,n,o,p,q,
  r,s,t,u,w,y,z) OUTSIDE the hex alphabet `HEX_40PLUS_RUN` requires (`[0-9a-fA-F]`) -- so this fixture
  would NOT have been caught by either redaction layer even if it had been routed through them,
  which is exactly the class of gap the removed `fill_tid` string branch had (a broad alphanumeric
  shape exempt from both redaction passes). The test genuinely proves the intended property.

## Regression scan 166f4274..353f6f1f (file-content-level; no Bash/git-diff available this session)

Read `ledger-publish.mjs` and `ledger-publish.test.mjs` end to end. Cross-checked against
iteration-4's own verdict.json/notes.md, which already quoted exact line ranges for every
prior-iteration fix site. Every structural-safety test iteration-4 catalogued (leak test, shallow-clone
test, lock-held/stale tests, both divergence tests, phantom-push test, commit-failure recovery test,
streak/reachability tests, FIND-001d real-`isProfitable()` round-trips, FIND-003 sig-shape test) is
still present, unweakened, using real git against `file://` bare-repo fixtures exactly as before.
`index.mjs`'s wiring (lines 354-387, strictly post-`runOneWake()`, own try/catch, streak-based
escalation via the existing `appendHarnessFailure`) and `package.json`'s `test`/`test:unit` scripts
(lines 8-9, `ledger-publish.test.mjs` present in both) independently re-verified unchanged.
`env-filter.mjs::redactPrivateKeyPatterns` independently re-read and confirmed unmodified (still
matches its own PROP-005/006/018/020 doc comment).

## NEW GAP FOUND this iteration — FIND-001 (verification_readiness, minor)

`specs/verification-architecture.md`'s proof-obligation table row `FIND-001a (rewritten,
impl-review iter3)` was never updated for iter4's fix. Its own text --
"Also asserts a non-boolean `external`/`confirmed` and a non-number/non-string `fill_tid` are still
dropped (fail-closed)" -- misdescribes the current code: there is no longer a "non-number/non-string"
distinction to draw, since ALL strings (well-formed or not) are dropped now, not just malformed ones.
`verification-architecture.md`'s Changelog (lines 3-23) also has no iter4 entry at all, unlike
`behavioral-spec.md`'s Changelog, which DOES correctly and completely document both iter4 fixes
(lines 10-25) with accurate line citations that match the shipped code. This is an inconsistency
between the two spec documents this feature maintains, not a code defect -- but both documents ship,
as-is, to the public `github.com/Daisuke134/anicca` repo as this feature's authoritative record, and a
future reader trusting the verification-architecture.md table over the code/tests would draw a
factually wrong conclusion about what shape of `fill_tid` is accepted. Full citation trail in
`findings/FIND-001.json`.

## Test integrity spot-check (this iteration's changed test specifically)

- `test.mjs:275-293` (fill_tid four-shape matrix): every assertion checks a real
  `JSON.parse(projectEarnLine(...))` output against `'fill_tid' in <out>` -- not tautological, not
  checking an implementation detail (no internal state/mock-call inspection), genuinely exercises the
  public `projectEarnLine` contract across four distinct input shapes chosen specifically to stress the
  boundary the removed regex used to accept.

## Verdict

**overallVerdict: FAIL** (verification_readiness dimension FAILs on FIND-001 -- a real, minor,
documentation-only gap in `specs/verification-architecture.md`, not a code or test defect). All four
other dimensions PASS with positive evidence; iteration-4's FIND-001 (major) and FIND-002 (minor) are
both genuinely and verifiably closed in code and tests. No new code-level or test-level gap found this
iteration beyond the spec-document drift documented above.
