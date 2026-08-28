# General Agent Capability Manifest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Declare one Lancers application capability in the existing public provider registry while keeping actual authorization private and defaulting every public action to unknown.

**Architecture:** Extend `provider-capabilities.public.json` instead of creating another registry, schema, loader, or provider brain. The public entry describes the required transport, authorization state, human-only ceremonies, and official receipt type; `provider_authorization.py` remains the only runtime authority and private receipts remain outside Git.

**Tech Stack:** JSON, Python 3, pytest, existing `provider_authorization.py`, existing `provider-capabilities.public.json`.

## Global Constraints

- Do not modify Coconala code, state, browser, owner, tests, or documentation.
- Do not store an account, evidence hash, receipt hash, credential, selector, URL, proposal content, price, margin, ranking, or scheduler rule in the public manifest.
- Public state remains `unknown`; only an exact unexpired private receipt may return `approved_browser` at runtime.
- Declare one capability only: `marketplace.application` with action `submit_proposal` and transport `cloak_browser`.
- Reuse the existing `application_receipt` readback contract.
- Change one config file and one existing test file; add no production code or dependency.

---

### Task 1: Add one safe-default Lancers application capability

**Files:**
- Modify: `skills/earn/gig/config/provider-capabilities.public.json`
- Test: `skills/earn/gig/tests/test_provider_authorization.py`

**Interfaces:**
- Consumes: existing public catalogue version 1 and private `authorize(provider, account, action, transport, now)` runtime contract.
- Produces: `catalogue["providers"]["lancers"]["capability"]` with an exact closed JSON shape.

- [ ] **Step 1: Extend the failing public-catalogue contract test**

In `test_public_catalogue_defaults_every_action_to_unknown`, add `"lancers"` to the expected provider set, then append:

```python
    assert catalogue["providers"]["lancers"] == {
        "state": "unknown",
        "actions": ["submit_proposal"],
        "capability": {
            "id": "marketplace.application",
            "action": "submit_proposal",
            "transport": "cloak_browser",
            "authorization": {
                "receipt_required": True,
                "required_state": "approved_browser",
            },
            "human_only_when_required": ["captcha", "identity", "tax", "payout"],
            "readback": {"record_type": "application_receipt"},
        },
    }
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q \
  skills/earn/gig/tests/test_provider_authorization.py
```

Expected: FAIL because the provider set lacks `lancers`.

- [ ] **Step 3: Add the exact manifest entry**

Add this provider beside the other public entries in
`skills/earn/gig/config/provider-capabilities.public.json`:

```json
    "lancers": {
      "state": "unknown",
      "actions": ["submit_proposal"],
      "capability": {
        "id": "marketplace.application",
        "action": "submit_proposal",
        "transport": "cloak_browser",
        "authorization": {
          "receipt_required": true,
          "required_state": "approved_browser"
        },
        "human_only_when_required": ["captcha", "identity", "tax", "payout"],
        "readback": {"record_type": "application_receipt"}
      }
    },
```

- [ ] **Step 4: Run focused authorization tests and JSON validation**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q \
  skills/earn/gig/tests/test_provider_authorization.py
python3 -m json.tool skills/earn/gig/config/provider-capabilities.public.json >/dev/null
git diff --check
```

Expected: all focused tests PASS and both validation commands exit 0.

- [ ] **Step 5: Commit and push the manifest slice**

```bash
git add skills/earn/gig/config/provider-capabilities.public.json \
  skills/earn/gig/tests/test_provider_authorization.py
git commit -m "feat(gig): declare Lancers application capability"
git push
```

### Primary-only closeout

After fresh Step 4 evidence, the primary agent changes only the GA-03 row in
`docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md` from `TODO` to `DONE`, records the commit and focused test count, and marks the five plan checkboxes complete. It does not begin GA-04 in the same commit.
