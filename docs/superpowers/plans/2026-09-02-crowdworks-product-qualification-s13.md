# CrowdWorks Product Qualification S13 Implementation Plan

> **For agentic workers:** Execute inline without subagents, TDD ritual, or review.

**Goal:** Render and independently qualify the shared product for CrowdWorks using current official
CrowdWorks evidence, without inheriting Coconala demand or hardcoding product judgment.

**Architecture:** The existing Account 2 proposal agent receives the neutral product plus three hashed
official CrowdWorks observations and returns one strict adapter/qualification contract. A deterministic
CLI validates marketplace facts, product identity, fee representation, originality, canonical hash,
and atomic idempotent persistence. CrowdWorks transport is `application`, because official evidence
shows a job-search/application marketplace rather than a worker storefront publish flow.

**Tech Stack:** Existing agent runner, Python standard library, JSON Schema draft 2020-12.

## Constraints

- S13 only; no application is submitted.
- Official CrowdWorks evidence is independent from all Coconala evidence.
- The model decides qualification and mapping; deterministic code only validates and persists.
- Unknown and missing evidence stays explicit; no invented sales, reviews, fees, credentials, or IDs.
- Lancers remains excluded because a separate owner handles it.

### Task 1: Produce one CrowdWorks adapter and qualification receipt

**Files:**
- Create: `skills/earn/gig/schemas/crowdworks_product_qualification.schema.json`
- Create: `skills/earn/gig/scripts/crowdworks_product_adapter.py`
- Modify: `skills/earn/gig/TODO.md`
- Produce: `/Users/anicca/gig/private/storefront-bundle/contracts/adapters/crowdworks/ui-translation.json`

**Interfaces:**
- Agent output and CLI input use the qualification schema.
- CLI: `crowdworks_product_adapter.py --product PRODUCT --input INPUT --output OUTPUT`
- Output adds `qualification_sha256`; identical replay reports `changed:false`.

- [ ] Define strict fields for product identity, `transport=application`, official category, current
  comparable observations, fee schedule, mapping, qualification status/reason, unknowns, evidence
  URLs/hashes, and originality provenance.
- [ ] Invoke `storefront-proposal-agent` on Account 2 with the neutral contract and facts from official
  fee, category 159, and job 12941894 pages. Require only evidence-backed output.
- [ ] Validate that product key/SHA equal S11, all evidence URLs use `https://crowdworks.jp/`, all hashes
  are SHA-256, category is 159, currency is JPY, fee tiers reproduce official 20%/10%/5% boundaries,
  no Coconala evidence appears, and competitor content is not incorporated.
- [ ] Canonicalize, hash, and atomically persist. Run twice; require first `changed:true`, replay false,
  Account 2 model receipt success, and independent CrowdWorks evidence retained.
- [ ] Mark S13 complete. Rewrite S14 transport as one fenced CrowdWorks application through an installed
  Apply owner, with official sent/readback and replay-zero; do not claim a nonexistent storefront.
- [ ] Commit/push/PR/admin-merge. Do not release or restart Coconala loops because no owner entrypoint
  changes in S13.
