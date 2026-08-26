# Fundraiser Agent predecessor code audit

## Scope

This audit supports Task 0 of the Life Manager Fundraiser Agent. The repositories were cloned into
an isolated temporary directory and inspected at the exact commits below. They are evidence and
pattern sources, not runtime dependencies. No vendor tree is copied into Life Manager.

Clone root: `/tmp/lm-fundraiser-predecessors.D404NS`

The shell initially had no DNS configuration. The clone was completed without changing system DNS by
resolving `github.com` through DNS-over-HTTPS and passing the address only to each Git command through
`http.curloptResolve`.

## Pinned repositories

| Repository | Commit | License | Inspected implementation |
|---|---|---|---|
| [lalalune/outreachr](https://github.com/lalalune/outreachr) | `8340cfbcf197d5aa38fcd9766cba7af2f43f030d` | Apache-2.0 | `docs/architecture.md`, `packages/core/src/{migrations,repository}.ts`, `packages/connectors/src/send.ts`, `apps/desktop/src/main/{index,command-service}.ts`, `packages/agents/src/runtime.ts` |
| [Desperado/venture-ops](https://github.com/Desperado/venture-ops) | `7f6d03a31a565a455b4a0a2714d0564cb98233a7` | MIT | `modes/{apply,accelerator,auto-pipeline}.md`, `scan-investors.mjs`, `followup-cadence.mjs`, `verify-pipeline.mjs`, `DATA_CONTRACT.md` |
| [oncesylvia/fundraising-skills](https://github.com/oncesylvia/fundraising-skills) | `084b22d3db00611ea231ec12813ccb071b84bc33` | MIT | `skills/{investor-targeting,investor-research,warm-path-finder,cold-email,pipeline-tracker}/`, `shared/references/outreach-ethics.md` |
| [aviskaar/open-org](https://github.com/aviskaar/open-org) | `486a9f710d4d96a9eb41b61fa9c62cab3843896f` | Apache-2.0 | `skills/{cro-investor-relations,investor-research,investor-outreach,investor-calendar,due-diligence-prep,fundraising-analytics}/SKILL.md` |

## Code findings

### Outreachr

Actual call path:

`apps/desktop/src/main/index.ts` constructs `VaultService`, `ConnectorService`, the agent service, and
`CommandService`. `draft.send` calls `ConnectorService.sendApprovedDraft`. The connector calls
`executeGuardedSend`, which claims the send ledger before provider I/O. `repository.ts` transitions
`reserved -> dispatching -> sent | ambiguous` and can reconcile an ambiguous send only from an
authoritative sent-mail observation.

Useful contracts:

- `send_ledger` has unique recipient-address and canonical-person indexes;
- exact recipient, sender, subject, body, attachments, provider, and thread context are bound to an
  approval hash before provider I/O;
- provider ambiguity becomes terminal `ambiguous`, not an automatic retry;
- a provider sent-mail event may reconcile an ambiguous effect without sending again;
- mail events are deduplicated by provider message ID;
- agent runs receive serialized context and create proposals; they do not receive a database handle.

Adopt claim-before-effect, exact effect digests, authoritative reconciliation, canonical identity,
append-only evidence, and replay-zero. Reject the Electron app and full CRM. The user has already
delegated accelerator submission, so its founder-click approval boundary is not copied verbatim.

### Venture-Ops

`scan-investors.mjs` reads a fixed `investors.yml`, computes fit with hardcoded numeric weights, and
appends Markdown/TSV files. `verify-pipeline.mjs` parses Markdown columns and validates a fixed status
set. `modes/apply.md` explicitly refuses to submit forms or send messages.

Adopt separation of startup facts from workflow state, current-term verification, and one next action
per active target. Reject the fixed universe, hardcoded scores, Markdown effect ledger, draft-only
behavior, and regex parsing of human-authored rows.

### fundraising-skills

This repository contains prompt skills and references, not a browser executor or provider readback.
Adopt these prompt-level heuristics: research from live public sources, retain source URLs and
confidence, prefer real warm paths, never guess private contacts or relationships, use public intake
routes, add new information in follow-ups, then stop. Do not copy its file-based CRM.

### open-org

This repository decomposes fundraising into research, outreach, calendar, diligence, and analytics.
The implementation is instruction text and templates without form execution, provider receipts, or
replay-zero. Adopt only its responsibility map. Reject its hierarchy, template volume, hardcoded
scoring, and placeholder-heavy output.

## Life Manager code compared

### Existing startup truth and preview

- `.agents/startup-context.json` owns current product and company facts.
- `fundraising/application-kit/` is generated from that context.
- `skills/apply-to-funder/lib/context.mjs` binds context and application digests and blocks stale or
  unverified assets.
- Current limitation: it requires a pre-created `fundraising/funders/<id>.json` and is preview-only.
  That registry cannot remain the admission gate for daily discovery.

### Existing browser and X loops

`apps/job-search-loop/job_search_loop/browser_agent/` proves the interaction shape: fresh observation,
one model-chosen action, stale-action rejection, checkpoint/resume, one-shot Submit, and fresh
completion evidence. Its Python command surface and job-search types are not reused. Fundraiser uses
the existing general browser tools directly; no funder selector, adapter, field map, or Python form
script is created.

`skills/x-repost/` proves Life Manager can lease `x:anicca`, search rendered X pages, persist source
receipts, deduplicate URLs, and release the browser. Fundraiser may lease the same registered identity
read-only through the guard. It does not use x-repost's fixed query file, publishing code, or state.

## Current official source checks

These claims must be refreshed by the daily agent before action.

- [Y Combinator Apply](https://www.ycombinator.com/apply): "still accepting late applications" for
  Fall 2026.
- [Solo Founders Program](https://solofounders.com/program): "three-month program in SF for solo
  founders" and a stated $100K investment.
- [Base Batches](https://www.base.org/batches): Batch 004 closes September 9 and targets Base teams.
- [Antler Japan](https://www.antler.co/location/japan): the Tokyo residency is in person and full time.
- [a16z Speedrun](https://a16z.com/speedrun/): the current page centers the games industry, so fit
  cannot be assumed from the a16z brand.
- [DelightX](https://delightx.delight-ventures.com/en/): Cohort 3 is open for January 2027. The same
  page contains date text apparently inconsistent with that cohort; the agent must surface the
  contradiction instead of silently choosing a date.

## Resulting decision

Build one Life Manager Fundraiser Agent, not a set of accelerator automations.

The model owns daily query generation, source expansion, fit and priority judgment, unfamiliar UI
reading, browser actions, answer adaptation, and evidence-sufficiency judgment.

Deterministic tools own canonical identities, evidence hashes, freshness, the daily application claim,
submitted/cohort/account deduplication, one-shot effect fencing, provider readback identity, state
transitions, suppressions, and replay-zero.

The daily target is one newly verified application. If no eligible new program exists, the agent
records the sources checked and continues tracking existing applications; it never reapplies,
fabricates a program, or submits an ineligible application to satisfy the count.
