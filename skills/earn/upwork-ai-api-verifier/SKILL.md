---
name: upwork-ai-api-verifier
description: Use when independently verifying an Upwork AI or API deliverable against an accepted contract before marketplace submission.
metadata:
  version: 1.0.0
  risk: medium
---

# Upwork AI/API Verifier

Independently decide whether an artifact produced for an accepted Upwork AI/API contract satisfies
the frozen acceptance evidence. This Skill verifies; it never discovers jobs, writes proposals,
changes scope, repairs the artifact, submits delivery, or marks payment.

## Required evidence

Require the immutable contract/source hash, client acceptance criteria, artifact/provenance hashes,
execution instructions, declared dependencies, cost/latency bounds and builder Skill identity. Return
`undeterminable` when the evidence is missing; never replace missing acceptance criteria with guesses.

## Verification judgment

Choose checks from the actual contract rather than a fixed keyword route. Exercise the public setup
path in a clean temporary workspace and inspect the real outputs. For AI/API work, normally consider:

- request/response schema, documented error behavior and acceptance examples;
- authentication and tenant isolation, including negative cross-tenant attempts;
- idempotency for mutating ingestion, feedback or retry paths;
- malformed input, timeout, provider failure, cost ceiling and abstention behavior;
- deterministic fixtures or bounded live checks for model-dependent behavior;
- secret absence, dependency pinning, startup instructions and rollback viability;
- contract-specific ranking, classification, summarization, image or integration acceptance metrics.

Do not require an irrelevant check merely because it appears in this list. Do not waive a contract
requirement because another check passes.

## Receipt

Return a hash-bound `PASS`, `FAIL`, or `undeterminable` receipt containing contract hash, artifact
hashes, verifier Skill hash, exact commands, exit codes, measured acceptance results and unresolved
failures. `PASS` requires every frozen acceptance invariant to have direct evidence. The builder cannot
author or alter this receipt. A failed or undeterminable receipt blocks delivery but preserves the
project for revision.

Marketplace delivery remains owned by the Upwork effect fence and requires its own official submission
readback. This Skill's PASS is necessary evidence, never proof that delivery or payment occurred.
