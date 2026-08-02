# O1C-25 YC Full Preview Design

## Objective

Read and assess the current Fall 2026 YC application across exactly five scopes—company facts, founder profile, the founder video, demo, and progress—without changing a field, choosing an option, attaching a file, saving an update, or submitting anything. Produce a privacy-minimal, source-bound preview receipt whose completion status is independent from its submit-readiness verdict.

## Verified starting state

- The Fall 2026 application is already submitted and is `In review`; O1C-07 is the only application-submit receipt and is a required content-bound preview source.
- The read-only application still presents the old Anicca pitch, including the old company description, product narrative, URL, cofounder story, and progress answers. It does not present the current Life Manager product facts.
- The repository README and agent registry now define Life Manager as one product with local/self-hosted and cloud/Web execution surfaces, with Anicca as the company name only.
- A 2026-07-31 Life Manager answer draft exists and explicitly supersedes the old pitch, but it covers only 18 answer fields and contains facts that require current-source review.
- The founder profile is structurally marked complete. Its identity, role, equity, education, and work-history sections are populated, while several narrative answers remain generic or stale and the live education end date differs from older kit prose.
- The remotely hosted founder video is present and playable at 57.856 seconds, H.264/AAC, 720 by 1280. Its local source is 57.835 seconds and has SHA-256 `34881787eb93e240049f92ea72d471f3d457f00ddb4e228b1b8c1729fa0e5fe6`.
- The demo page has no remote video. The read-only application also says no demo video was uploaded.
- The progress page contains the old Anicca product link and old narrative answers and exposes `Submit update`, not `Save changes`.
- The O1C-21 provider manifest describes pre-submission main/progress save routes. The current submitted application exposes a read-only application plus separate progress, founder-video, demo, and team update routes, so the old write manifest must not be treated as current executable knowledge.

## Alternatives

### A. Treat the submitted application as the preview source

Rejected. This would faithfully read the remote state but would endorse materially obsolete company and product claims as current Life Manager facts.

### B. Treat the 2026-07-31 answer draft as the complete preview

Rejected. It is much closer to the current product, but it omits required company/team/progress fields, has no demo binding, and contains time-sensitive founder and product claims that cannot be promoted without current readback.

### C. Build a closed five-scope observation and assessment receipt

Selected. Agent-owned semantic assessment compares the current repository facts and draft snapshot with fresh, read-only YC observations. Deterministic code validates the closed schema, artifact hashes, chronology, observation coverage, zero-effect boundary, preview outcome, and submit gate. It never decides whether prose is true or whether a mismatch is material.

## Architecture

```text
current repository facts -----+
Life Manager answer draft ----+----> agent semantic assessment
application-kit/video --------+          |
fresh YC read-only pages ------+          v
                                   five scope verdicts
                                   company / founder / video
                                   demo / progress
                                            |
                                            v
                               deterministic closed receipt
                               preview_complete = true
                               submit_ready = false when any blocker exists
                               all mutation effects = 0
```

## Five-scope contract

Each scope is observed exactly once in the receipt and contains only bounded status, source references, hashes or media metadata, an agent-authored currentness verdict, and machine-readable issue codes.

| Scope | Required observation | Current assessment rule |
|---|---|---|
| Company facts | submitted read-only application plus current repo/draft digests | `current` only if the visible pitch agrees with current Life Manager facts and every required field has a current source |
| Founder profile | live profile completeness and bounded section inventory | structural completeness and semantic currentness are separate; personal contact and birth-date values are never persisted |
| Founder video | remote media readiness/duration/dimensions plus local artifact digest/codec metadata | present only when remote media is playable, duration is at most 60 seconds, and local bytes/digest match the bound source artifact; identical-byte remote upload is not claimed from URL metadata alone |
| Demo | remote media presence plus a source-bound current demo artifact | absent is an explicit blocker; an unrelated marketing/founder video cannot be relabelled as a product demo |
| Progress | current update-page field hashes plus present product/revenue/user facts | current only when source-backed product, user, revenue, and traction claims match the visible update values |

The receipt may declare `preview_complete: true` while declaring `submit_ready: false`. `preview_complete` means all five scopes were observed and assessed. It does not mean their contents are current, correct, or ready to submit.

## Semantic and deterministic responsibility

The agent owns all judgments about which source is authoritative, whether prose describes the current product, whether a founder answer is stale, whether an artifact is a real product demo, and whether an issue blocks submission. These judgments are supplied as explicit structured inputs.

The JavaScript boundary owns only exact keys, enumerations, source-role uniqueness, SHA-256/byte validation, timestamp chronology, media bounds, issue/result consistency, zero effects, canonical digest generation, and recursive freezing. It contains no keyword, regex, scoring, or hard-coded prose rule for deciding semantic truth.

## Submit-safety boundary

- O1C-25 performs read-only navigation on an owned temporary page and closes only that page.
- Form fields, custom controls, upload inputs, save controls, and submit controls are never exercised.
- Cookies, authentication tokens, signed media URLs, email, phone, birth date, raw application answers, and raw profile narratives are not stored.
- `navigation_reads` may be non-zero. Field writes, selections, file attachments, saves, update submissions, application submissions, and browser closes must all be zero.
- Because O1C-07 already submitted the Fall 2026 application once, O1C-26 must never issue a second application submission. Any later external effect must be a separately typed update and may run only when this preview's `submit_ready` gate is true.
- A missing demo, stale company/progress facts, incomplete source coverage, provider-route drift, or a privacy violation closes the submit gate.

## Evidence and privacy

The public evidence contains:

- application and profile identities as existing non-secret UUID references;
- repository-relative source paths or bounded logical external references;
- hashes, byte counts, field counts, answer lengths, and media metadata;
- currentness/readiness enums and bounded issue codes;
- sanitized final origins/paths, never query strings or signed media paths;
- exact zero-effect counts and test results.

It does not contain raw YC answers, raw draft answers, personal contact data, authentication material, full media URLs, cookies, headers, DOM bodies, or full browser/process environments. A digest proves stable structure and accidental-tamper detection, not source authenticity; same-run readbacks and Git history remain the evidence for observations.

## Failure behavior

- Missing or duplicate scope, artifact, issue code, or observation fails closed.
- Unknown keys, invalid digest/byte count, non-canonical timestamp, stale observation, or chronology inversion fails closed.
- A claimed present founder video without valid remote readiness/duration/dimensions and local artifact metadata fails closed.
- A claimed present demo without both remote observation and a dedicated source artifact fails closed.
- `blocking_issue_codes` is an agent-selected subset of observed issues, but deterministic safety policy requires observed company-facts staleness, provider-route drift, founder-source conflict, missing demo, and progress staleness to remain blockers. Any required/selected blocker with `submit_ready: true`, or any non-zero mutation effect, fails closed. The agent owns whether those observed conditions apply; code owns the post-judgment gate.
- Each scope accepts only its exact required source-role set; substituting another known source fails closed.
- The historical submit count is derived from the content-bound O1C-07 receipt, not a caller assertion.
- Any attempt to claim a second application submit fails closed independently of readiness.
- Input mutation after construction cannot mutate the frozen receipt.

## Verification

1. Write focused tests first for the five-scope happy path and every contradiction above.
2. Implement the minimal closed receipt builder and validator.
3. Perform fresh read-only observations of the application, profile, video, demo, and progress pages using the authenticated daily-driver.
4. Bind the current README, registry, draft, kit, founder-video, and provider-manifest digests without copying their sensitive prose into evidence.
5. Run focused, outbound, runtime-up, and full tests; validate JSON, digests, chronology, worktree cleanliness, and zero mutation effects.
6. Obtain independent read-only review before closing the canonical item.

## Scope boundary

O1C-25 proves only that all five preview scopes were inspected and honestly classified. It does not update the YC application, create a missing demo, repair the provider manifest, submit an update, resubmit the application, retrieve confirmation mail, or track replies. Those actions require later numbered work and the submit gate defined here.

## Self-review and approval

- Placeholder scan: no TBD, TODO, or unresolved choice remains.
- Truthfulness: preview completeness and submit readiness are separate, so negative findings cannot be hidden behind a completed checkbox.
- Safety: all YC mutation effects remain exact zero and a second application submit is forbidden.
- Privacy: public evidence stores only bounded metadata, hashes, enums, and sanitized paths.
- Approval: Dais explicitly requested sequential execution with no human in the loop; the agent approved this bounded design on 2026-08-02 and proceeded without a human review pause.
