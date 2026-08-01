# Agent Registry verification — 2026-08-01

## Scope

This evidence closes the 12 deliverables in
`docs/superpowers/specs/2026-08-01-life-manager-agent-registry-design.md`.
The pre-existing 133 unchecked items in the Dais five-phase program are not
claimed complete by this slice.

## Requirement audit

| # | Requirement | Evidence | Result |
|---:|---|---|---|
| 1 | Dedicated design spec | `docs/superpowers/specs/2026-08-01-life-manager-agent-registry-design.md` | proven |
| 2 | JSON Schema | `agents/agent-registry.schema.json` | proven |
| 3 | One canonical registry | `agents/registry.json`, 16 unique roles, one root | proven |
| 4 | Validator | `scripts/validate-agent-registry.mjs` | proven |
| 5 | Agent/capability/job boundary | `docs/agent-classification.md` | proven |
| 6 | Evidence-backed initial roster | every active entry has existing source and evidence refs; planned entries have spec refs | proven |
| 7 | 399-job relationship | runtime-family refs are validated against `runtime-inventory.json.jobs[].target_adapter` | proven |
| 8 | README overview | marker-bounded generated sections in `README.md` and `README.ja.md` | proven |
| 9 | Detailed catalog | generated `docs/agent-catalog.md` | proven |
| 10 | Existing-spec references | five-phase and portable finance/marketing specs link to the dedicated SSOT | proven |
| 11 | Chat projection contract | `docs/chat-agent-projection-contract.md` | proven |
| 12 | Tests, verification, commit, push | focused/OSS evidence below; implementation commit local/remote SHA matched | proven |

## Fresh focused verification

Command:

```bash
npm run test:agents && npm run validate:agents && npm run check:agents && git diff --check
```

Observed:

```text
tests 24
pass 24
fail 0
{"valid":true,"agents":16}
{"current":true,"agents":16}
git diff --check: exit 0
```

The tests include valid input, duplicate IDs, missing parents, parent cycles,
active/planned evidence, absolute paths, parent traversal, secret-shaped and
unknown fields, malformed schema, one-root enforcement, cross-registry skill /
adapter / runtime-family refs, missing repo paths, effect vocabulary, stable
ordering, Japanese rendering, one-row-per-agent catalog rendering, marker
preservation, and drift detection.

## Deterministic generation proof

Commands:

```bash
node scripts/render-agent-catalog.mjs
shasum README.md README.ja.md docs/agent-catalog.md
node scripts/render-agent-catalog.mjs
shasum -c <first-run-sha-file>
node scripts/render-agent-catalog.mjs --check
```

Observed: all three generated files retained the same hashes on the second
render, and `--check` returned `{"current":true,"agents":16}`.

## Repository boundary checks

Command:

```bash
npm run test:oss
```

Observed: 11 tests, 11 pass, 0 fail.

`npm run verify:oss` still exits 1 with the same six outbound-runtime findings
on both the untouched `main` checkout and this feature worktree:

```text
forbidden_source_root    apps/life-manager/lib/outbound-event-job.test.js
personal_runtime_default apps/life-manager/lib/outbound-event-job.test.js
forbidden_source_root    apps/life-manager/lib/outbound-evidence.test.js
personal_runtime_default apps/life-manager/lib/outbound-evidence.test.js
forbidden_source_root    apps/life-manager/README.md
forbidden_source_root    skills/self/outbound-runtime-healthcheck.sh
```

These six findings were present before Agent Registry work began and no Agent
Registry file appears in the failure list. They remain a separate outbound
baseline defect; this document does not describe the whole repository as OSS
verification-clean.

## Counts after this slice

```text
Agent Registry roles:          16
  live:                         4
  legacy_live:                  5
  shadow:                       1
  planned:                      6

Agent Registry deliverables:   12 complete / 0 remaining
Five-phase unchecked work:    133 remaining
```

## Remote proof

Branch: `feat/agent-registry`

Implementation commit local SHA:

```text
e876b1c94df77980bbd1eec81ab5c4555e346a9f
```

Observed immediately after push:

```text
e876b1c94df77980bbd1eec81ab5c4555e346a9f refs/heads/feat/agent-registry
```

The documentation-closure commit that checks deliverable 12 is pushed after
this evidence update; final handoff independently compares the branch tip with
`git ls-remote`.
