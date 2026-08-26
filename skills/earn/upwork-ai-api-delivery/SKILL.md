---
name: earn/upwork-ai-api-delivery
description: Build and verify evidence-bound AI APIs for Upwork jobs involving text summarization, image analysis, classification, similarity ranking, tenant isolation, and feedback reranking.
version: 1.0.0
risk: medium
---

# Upwork AI API Delivery

Use this Skill only after an Upwork job observation, owner bounds, and immutable qualification
receipt identify an eligible AI API engagement. It builds deliverables; it never searches for jobs,
submits proposals, purchases Connects, negotiates terms, or delivers through Upwork.

## Capability contract

This Skill provides these machine-selectable capabilities:

- `text_summarization_delivery`
- `image_analysis_delivery`
- `ai_classification_delivery`
- `ai_integration_delivery`
- `api_development_delivery`
- `multitenant_similarity_ranking_delivery`
- `feedback_reranking_delivery`

Do not claim eligibility unless the job's required capability set is a subset of this list and a
different installed verifier Skill covers every acceptance invariant.

## Required inputs

Require all of the following before implementation:

1. Immutable client scope and source hash.
2. Exact input/output examples and an acceptance dataset supplied or approved by the client.
3. Tenant identifier, authorization boundary, retention policy, and prohibited cross-tenant flows.
4. Ranking signals, weights or learning objective, fallback behavior, and feedback event semantics.
5. Model/provider constraints, cost ceiling, latency target, deployment target, and secret-injection
   mechanism.
6. Milestones whose amounts, artifacts, and deadlines match the accepted Upwork contract.

If any input is unknown, convert it into a written acceptance question. Do not silently invent it.

## Delivery workflow

### 1. Freeze the contract

- Convert the client scope into versioned request/response schemas.
- Create a small acceptance dataset with text, images, expected candidates, tenant IDs, and feedback.
- Define measurable checks for retrieval recall, ranking quality, abstention, latency, and isolation.
- Hash the contract and dataset before implementation.

### 2. Build tenant-isolated storage

- Put `tenant_id` on every persisted product, embedding, ranking configuration, and feedback event.
- Enforce tenant filtering in the database policy and service boundary, not only in prompts.
- Reject missing or conflicting tenant identity before model or retrieval calls.
- Keep raw input, derived features, model/version provenance, and deletion state traceable.

### 3. Build multimodal features

- Normalize text fields before summarization or embedding.
- Validate image type, size, decode success, and source authority before image analysis.
- Generate text and image features through replaceable adapters with model/version metadata.
- Cache by tenant, content hash, model, and preprocessing version; never share tenant-private cache
  entries.
- Represent missing modalities explicitly instead of fabricating values.

### 4. Build classification and similarity ranking

- Separate candidate retrieval from final ranking so each can be measured independently.
- Combine visual, textual, categorical, geographic, persona, and user-defined signals through a
  versioned configuration.
- Return component scores and provenance with the final rank for debugging and client review.
- Abstain or return insufficient-evidence status when required signals are absent.
- Prevent one tenant's products, configuration, or feedback from entering another tenant's result.

### 5. Build feedback reranking

- Store explicit feedback as immutable events with tenant, item pair, actor, timestamp, and context.
- Train or update only within the tenant boundary unless the client explicitly authorizes a shared
  base model and the contract defines privacy controls.
- Compare the candidate change against the frozen acceptance dataset before promotion.
- Keep the previous ranking version available for rollback.

### 6. Expose the HTTP/JSON API

- Use FastAPI/Pydantic schemas for validated input and explicit error responses.
- Separate routers, authorization dependencies, services, model adapters, and persistence.
- Add idempotency keys to mutating ingestion and feedback endpoints.
- Bound request size, timeout, concurrency, external-model spend, and retry count.
- Emit structured correlation IDs without logging secrets, raw private images, or full documents.

### 7. Verify independently

Pass the frozen contract to a different verifier Skill. At minimum, require:

- schema and error-response contract tests;
- tenant A/B leakage-negative tests at database, cache, retrieval, and feedback layers;
- deterministic fixtures for summarization/classification adapters;
- ranking regression and insufficient-evidence tests;
- idempotent ingestion/feedback replay tests;
- model failure, timeout, malformed image, and cost-cap tests;
- clean-environment setup and API smoke test.

The builder does not mark its own result verified. Store verifier command, exit status, artifact
hashes, acceptance metrics, and residual failures in the delivery receipt.

## Deliverables

Produce only contract-bound artifacts:

- source repository with pinned dependencies and secret-free example configuration;
- migrations and tenant isolation policies;
- versioned API schema and acceptance dataset;
- automated contract/regression tests and independent verifier receipt;
- setup, deployment, rollback, model-cost, and operational notes.

Do not submit partial files as final delivery. Upwork delivery remains owned by the marketplace
effect fence and requires accepted-contract readback plus exact artifact hashes.

## Stop conditions

Stop and return an explicit blocked receipt when client data rights are unclear, cross-tenant tests
fail, acceptance data is unavailable, required credentials cannot be injected safely, expected model
cost breaches the contract, or the accepted scope materially differs from the qualified source hash.
