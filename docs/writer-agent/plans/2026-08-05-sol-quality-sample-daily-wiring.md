# Sol quality-sample daily review wiring

## Goal

`done="the canonical editorial gate automatically registers every first current-hash Terra PASS, invokes a selected Sol sample exactly once, persists its verdict, and cannot skip an interrupted or failed audit"`

## Boundary

- `editorial-gate.sh` is the sole daily integration owner because every initial and recovery prompt already invokes it for each language.
- Register sample eligibility only after a current-hash Terra PASS. A Terra FAIL cannot bind a stale draft into the Sol sample ledger.
- The expected language alone can create the sample receipt.
- A same-hash retry reuses the persisted Sol verdict without another provider call.
- A Sol FAIL returns non-PASS and persists bounded fixes. The next changed draft receives the normal Terra review; it cannot spend a second Sol receipt.
- If the sample receipt was bound or claimed but no matching Sol verdict exists, fail closed as interrupted infrastructure; do not silently skip the audit.
- Ordinary runs and the non-selected language make zero Sol provider calls.

## Verification

1. RED integration fixture: fifth JA Terra PASS must cause one Sol call; ordinary and EN paths must not.
2. RED interruption/replay fixture: same bytes reuse the verdict, changed bytes after recorded FAIL proceed through Terra only, and a missing audit after binding fails closed.
3. GREEN minimal wrapper plus editorial-gate call site.
4. Existing editorial, model-runner, sample producer, quality-self-heal, and full-suite regression.
5. Isolated real provider E2E, live-branch promotion, and live focused verification.
