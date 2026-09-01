# Market Product Contract S11 Implementation Plan

> **For agentic workers:** Execute inline in this session. Do not dispatch subagents, add TDD ritual,
> or request review; Dais explicitly excluded those for this work.

**Goal:** Persist one validated, website-neutral `MarketProductContract` from the accepted Coconala
Storefront offer without retaining Coconala identifiers or competitor-owned content.

**Architecture:** A JSON Schema defines the portable product boundary. A small deterministic CLI loads
an already-judged contract, validates it with the repository's existing `jsonschema` dependency,
canonicalizes it, adds its SHA-256 identity, and atomically writes the canonical document. The CLI does
not derive claims from prose or make product decisions.

**Tech Stack:** Python standard library, existing `jsonschema`, JSON Schema draft 2020-12.

## Global Constraints

- S11 only; Coconala and CrowdWorks adapters remain later slices.
- No marketplace ID, URL, category ID, or form field may appear in the persisted contract.
- Capability and paid-demand evidence remain explicit references; unknown demand remains explicit.
- No new dependency, database, framework, agent, review pass, or test framework.
- Target: three repository files, less than 100 lines of production Python, one focused live validation.

---

### Task 1: Validate and persist one neutral product contract

**Files:**
- Create: `skills/earn/gig/schemas/market_product_contract.schema.json`
- Create: `skills/earn/gig/scripts/market_product_contract.py`
- Modify: `skills/earn/gig/TODO.md`
- Produce at runtime: `/Users/anicca/gig/private/storefront-bundle/contracts/market-products/ui-translation.json`

**Interfaces:**
- CLI: `market_product_contract.py --input INPUT --output OUTPUT`
- `validate_contract(value: object) -> dict`
- `canonical_contract(value: dict) -> dict`
- Output adds `contract_sha256`, computed over the canonical contract without that field.

- [ ] **Step 1: Add the exact schema**

Define required fields: `version`, `product_key`, `buyer_job`, `delivery_kind`, `inclusions`,
`exclusions`, `required_inputs`, `artifact_acceptance`, `base_price`, `recurring_support_boundary`,
`capability_evidence`, `paid_demand_evidence`, and `originality_provenance`. Use
`additionalProperties: false`; require non-empty strings/lists; represent price as
`{"amount": 4500, "currency": "JPY"}`; represent demand as
`{"status": "verified"|"unknown", "evidence": [...]}`.

- [ ] **Step 2: Add the deterministic persistence CLI**

Load the colocated schema, call `Draft202012Validator.check_schema`, validate the input, reject any
validation error with exit 1, reject serialized values containing marketplace keys
`platform`, `service_id`, `public_url`, `category_id`, or `form_field`, calculate SHA-256 over sorted
UTF-8 JSON without `contract_sha256`, and atomically replace the output via a sibling temporary file.
If the existing output is byte-identical, leave it unchanged and report `changed:false`.

- [ ] **Step 3: Persist the accepted UI-translation product**

Create a temporary input JSON from the accepted listing contract for service 4312985 and its confirmed
effect receipts. The portable contract describes UI Italian translation, adjusted screen wording and
display verification; excludes application implementation, new screen design, specialist legal/medical
review, and unspecified-device display verification; requires source text/screens, editable text or
images, layout limits, target OS/device, terminology, and deadline; accepts a translation table,
adjusted wording/images, and display-check result; sets JPY 4500; limits included revisions to three
within the agreed screens/source/display conditions; references owned `ui_translation` capability and
the accepted official offer/effect receipts; records originality as independently generated with no
competitor content incorporated. Run the CLI into the private bundle path.

- [ ] **Step 4: Run the focused acceptance check**

Run the CLI twice with the same input. Require first output `changed:true`, second output
`changed:false`; validate the persisted JSON against the schema; assert none of `coconala`,
`service_id`, `public_url`, `category_id`, or `data[Service]` occurs in its serialized content; verify
the stored SHA matches a fresh canonical calculation.

- [ ] **Step 5: Update the fixed TODO sequence**

Mark S11 complete only after Step 4. Record the output path, contract SHA, accepted source pass, and
focused idempotence result. Replace the later sequence with the user's explicit order: S12 Coconala
adapter/parity, S13 CrowdWorks adapter plus independent qualification, S14 CrowdWorks fenced canary.
Remove Lancers and Fiverr from this sequence without altering unrelated historical TODOs.

- [ ] **Step 6: Commit and publish**

Commit the schema, CLI, and TODO update; push a branch; create a PR; wait for the required Loop control
contract; merge into main; cut an immutable sparse release only if S11 is wired into a live owner.
Because this slice is a standalone contract persistence tool with no owner entrypoint change, do not
restart or reapply the four Coconala loops.
