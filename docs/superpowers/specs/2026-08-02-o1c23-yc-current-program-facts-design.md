# O1C-23 YC Current Program Facts Design

## Objective

Replace the stale program facts carried by the legacy-compatible `yc-w26.json` identity with fresh official facts for the current YC program. Prove the batch, deadline state, investment amount, and application URL from current YC-owned pages without reviving the deprecated answer/form/browser contract or performing any application write.

## Current State

The active legacy runtime file is `~/.openclaw/skills/apply-to-funder/funders/yc-w26.json`. Its stable identifier and filename are still consumed by old launch/runtime state, but its name says `W26`, its `next_deadline` is the unsupported date `2026-09-15`, and its amount range incorrectly permits `$125,000` to be interpreted as the whole investment. The same file also contains old Anicca answers, a deprecated browser profile, and form-driving knowledge that O1C-21 replaced with the repository-owned `yc-application` provider.

Fresh YC-owned sources observed on 2026-08-02 JST state:

- `https://www.ycombinator.com/apply`: Fall 2026, October through December in San Francisco; the on-time deadline was July 27 at 8pm PT; late applications remain open; the application link is `https://apply.ycombinator.com/home`.
- `https://www.ycombinator.com/deal`: total investment `$500,000`, consisting of `$125,000` for a fixed 7% and `$375,000` on an uncapped MFN safe.

The agent owns the semantic reading of those full official surfaces. Deterministic code may verify provenance, source integrity, excerpt containment, chronology, arithmetic, and projection into configuration; it must not decide current program meaning through keywords or regexes.

## Approaches Considered

### A. Edit only the external legacy file

This changes the currently installed runtime but leaves no versioned source of truth, validator, or reproducible evidence. A later install can silently restore the stale values. Rejected.

### B. Repository fact manifest, closed validator, and bounded legacy synchronization

Add a compact repository-owned `apps/life-manager/config/yc-w26.json` containing only current program facts and compatibility identity. Add a pure receipt builder that validates official source observations plus an agent-owned assessment, proves the fact projection and arithmetic, and emits a privacy-minimal content-addressed receipt. After the versioned artifact is verified, update only the corresponding fact fields in the installed legacy file and prove all unrelated content is byte-equivalent under a deterministic masked comparison. Selected.

### C. Copy the complete legacy funder spec into the repository

This would preserve stale Anicca answers, old local file paths, deprecated browser ownership, ambiguous form locators, and submit logic. It conflicts with O1C-21 and expands O1C-23 into O1C-24 through O1C-26. Rejected.

## Versioned Fact Manifest

`apps/life-manager/config/yc-w26.json` remains named after the compatibility identifier but is not a form specification. It has a closed schema:

- `schema_version = 1`
- `legacy_config_id = "yc-w26"`
- `program_id` and agent-owned `program_name`
- `official_url` and `application_url`
- `verified_at`
- `batch`: label, start month, end month, and location
- `deadline`: status, official display text, exact interpreted instant, timezone, and late-open boolean
- `investment`: currency, total amount, the fixed-safe amount/equity, and the uncapped MFN-safe amount
- two source receipts containing only official URL, retrieval URL, observation time, body length, and SHA-256
- the content-addressed fact receipt digest

The manifest contains no company answer, founder fact, traction value, media path, credential reference, browser profile, locator, application ID, save control, or submit control.

## Receipt Builder

`buildYcCurrentProgramFactsReceipt(input, options)` accepts:

1. Two official source observations, one for YC Apply and one for YC Deal. Each carries the full fetched body in memory, declared SHA-256, retrieval time, and every outbound link found on that surface.
2. An agent-owned assessment with exact source-bound excerpts for batch, deadline, late status, application URL, total amount, fixed-safe amount/equity, MFN-safe amount, and a bounded rationale.
3. The candidate fact manifest.
4. An injected or real wall clock.

The builder fails closed unless:

- source roles are complete and unique;
- official URLs are exact HTTPS YC-owned pages and retrieval URLs are either the same official URL or the Jina reader projection of that URL;
- declared source digests and byte lengths match the full in-memory bodies;
- observations precede `verified_at`, are no more than fifteen minutes apart, and `verified_at` is no more than five minutes old;
- every selected excerpt is non-empty, bounded, contained in its named full source, and contains the agent-selected value;
- the application URL is an exact HTTPS `apply.ycombinator.com/home` link observed on the Apply source;
- the interpreted deadline instant is a valid offset-bearing RFC3339 instant and the configured display/timezone/status/late-open values exactly match the assessment;
- investment amounts are safe positive integers, fixed plus MFN equals total, the fixed equity percentage is finite and positive, and the config exactly mirrors the assessment;
- input and nested schemas contain no unknown fields;
- the output contains no raw body, excerpt, rationale, cookie, header, credential, browser endpoint, company answer, or application ID.

The code does not hardcode `Fall 2026`, `July 27`, `$500,000`, or the selected status. These values are the agent's current reading and live in data. Exact origins and fixed machine paths are deterministic protocol validation, not semantic judgment.

## Bounded Legacy Synchronization

The installed legacy JSON keeps its stable filename, `id`, pages, answers, and current transport fields until their numbered migration items execute. O1C-23 changes only these program-fact projections:

- human-readable batch name;
- official and application URLs;
- structured current batch;
- structured deadline and the flat compatibility deadline fields;
- exact total investment range and structured standard deal;
- fact verification timestamp, source receipts, and receipt digest.

A before/after masked digest removes exactly those allowed paths and requires the remainder to match. This proves O1C-23 did not silently edit answers, browser configuration, form fields, or submission behavior. No runtime command, page navigation, save, or submit occurs.

## Failure and Privacy Behavior

Any stale source, source substitution, wrong origin/path, unobserved application link, missing/mismatched excerpt, malformed deadline, amount arithmetic drift, config/assessment mismatch, unknown field, or legacy out-of-scope drift aborts without changing the installed file. Only hashes, lengths, selected public facts, source URLs, timestamps, and test/review metadata are committed. Full fetched bodies and excerpts remain in memory and are not persisted.

## Verification

The implementation is complete only when:

1. TDD demonstrates the focused test fails before the builder exists and passes after implementation.
2. Adversarial tests cover provenance, body substitution, excerpt/value binding, chronology/freshness, application-link observation, deadline format, amount arithmetic, config drift, unknown fields, and output privacy.
3. The repository manifest validates against a fresh two-source official read.
4. The installed legacy file has the same current facts and its masked non-fact digest is unchanged.
5. Focused, outbound, runtime-up, and full Life Manager test suites pass.
6. Independent review has zero remaining Critical or Important findings.
7. The canonical spec records 54 completed items, 89 remaining, and O1C-24 as next.

## Scope Boundary

O1C-23 proves only current official program facts and their bounded projection into the legacy-compatible configuration identity. O1C-24 owns browser transport migration, O1C-25 owns current application/company/media preview, O1C-26 owns any exactly-once submission effect, and O1C-27 owns reply/interview monitoring.
