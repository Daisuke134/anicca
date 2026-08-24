---
name: gig-delivery-verifier
description: Independently verify contract-bound digital gig deliverables such as code, APIs, research datasets, writing, documents, presentations, and mobile builds before marketplace delivery; return PASS only from artifact-bound executable or visual evidence.
metadata:
  version: 1.0.0
  risk: medium
---

# Gig Delivery Verifier

Verify a finished marketplace deliverable in a fresh context. This Skill never builds the artifact,
changes contract scope, contacts the buyer, submits delivery, or approves payment.

## Required evidence

Require the immutable contract/scope hash, acceptance criteria, candidate artifact paths and hashes,
buyer-supplied source hashes, and the builder's provenance. Missing evidence returns
`UNDETERMINABLE`, never PASS.

## Choose verification by artifact

- Code/API: run the contract tests, clean setup and smoke path; inspect errors, secret handling,
  idempotency and the exact requested interfaces.
- Research/data: verify source authority, citations, required fields, row counts, duplicates,
  traceable sampling and unsupported claims.
- Writing: verify every factual claim against supplied or authoritative sources, required structure,
  language/tone, originality constraints and delivery format.
- Document/presentation: render the actual file and visually inspect every page/slide for clipping,
  overlap, unreadable text, missing assets and contract completeness.
- Mobile/web build: build and run the requested target, execute acceptance flows, inspect visible UI
  and record versioned build/test evidence. Signing, store publication and buyer credentials remain
  separate authorized effects.

Do not claim coverage for a modality that cannot be opened, executed or rendered with installed
tools. Never accept a builder statement, filename, source presence or test summary as a substitute
for inspecting the bound artifact itself.

## Result

Return exactly one disposition:

- `PASS`: every acceptance criterion has direct artifact-bound evidence.
- `NEEDS_WORK`: name each reproducible defect and the smallest correction.
- `UNDETERMINABLE`: name the missing evidence or unsupported verification modality.

Record verifier identity, artifact hashes, commands or visual inputs, observed results and residual
risks. Only a separate marketplace delivery effect may use PASS to submit the artifact.
