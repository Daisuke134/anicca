# Coconala Product Adapter S12 Implementation Plan

> **For agentic workers:** Execute inline without subagents, TDD ritual, or review.

**Goal:** Render the shared `MarketProductContract` through one thin Coconala adapter with exact
accepted-offer parity and no product judgment in the adapter.

**Architecture:** The portable contract remains product truth. The latest accepted Storefront listing
contract is a Coconala presentation binding. A deterministic CLI verifies product SHA, capability-family
binding, and JPY price, then copies the accepted binding's presentation fields unchanged into a hashed,
atomic adapter output.

**Tech Stack:** Python standard library and the S11 validation module.

## Constraints

- S12 only; no CrowdWorks code or external publication.
- No model call, text generation, semantic classifier, category invention, or new dependency.
- Coconala identifiers exist only in adapter binding/output, never in `MarketProductContract`.
- Do not restart or serialize the four Coconala loops.

### Task 1: Render and verify the accepted Coconala binding

**Files:**
- Create: `skills/earn/gig/scripts/coconala_product_adapter.py`
- Modify: `skills/earn/gig/TODO.md`
- Produce: `/Users/anicca/gig/private/storefront-bundle/contracts/adapters/coconala/ui-translation.json`

**Interfaces:**
- CLI: `coconala_product_adapter.py --product PRODUCT --binding BINDING --output OUTPUT`
- `render(product: dict, binding: dict) -> dict`
- Output contains `adapter`, `product_key`, `product_contract_sha256`, `binding`, `fields`, and
  `adapter_sha256`.

- [ ] Load and validate the S11 product through `market_product_contract.validate_contract`; require
  its stored SHA to match a fresh `canonical_contract` calculation.
- [ ] Validate the binding as version 1/platform `coconala`, require numeric service identity, exact
  official public URL, SHA-256 listing version, non-empty accepted offer fields, JPY price equal to the
  portable base price, and `generated_from_family` referenced by portable capability evidence.
- [ ] Copy `outcome`, `inclusions`, `deliverables`, `required_inputs`, `base_price_jpy`, and `options`
  unchanged into `fields`; keep service identity, listing version, and public URL under `binding`.
- [ ] Canonicalize/hash/atomic-write the adapter output; identical replay reports `changed:false`.
- [ ] Run once with a temporary extract of the latest accepted 4312985 listing contract and once again;
  assert first `changed:true`, replay false, `fields` equals the accepted `offer` byte-for-value after
  canonical JSON loading, and product SHA equals S11.
- [ ] Mark S12 complete with adapter path, SHA, binding version, and replay result. Leave S13 next.
- [ ] Commit, push, create a PR, pass the required check or use authorized admin merge for unrelated
  main-only fixture drift, and merge to main. No loop release/apply is required because no owner
  entrypoint changes.
