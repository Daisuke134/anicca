# Apply Music-Production Prohibition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent Coconala Apply from proposing work whose required deliverable is music or produced/edited audio.

**Architecture:** Extend the existing model-owned semantic feasibility policy with one prohibition class and two canonical boundary examples. Reuse the current exact-evidence contract; add no deterministic category or keyword gate.

**Tech Stack:** Python 3, pytest, existing model planner.

## Global Constraints

- Apply only; do not modify Paid, Reply, Storefront, browser, submission, or historical effects.
- No regex, category filter, new dependency, schema, service, or state.
- Music/audio production is prohibited even when prompting or generative tools could produce it.
- Music-adjacent code, research, writing, and design remain eligible when audio is not the required deliverable.

---

### Task 1: Add the semantic Apply prohibition

**Files:**
- Modify: `skills/earn/gig/scripts/application_planner.py`
- Test: `skills/earn/gig/tests/test_application_planner_focus.py`
- Modify: `skills/earn/gig/TODO.md`

**Interfaces:**
- Consumes: `common_marketplace_feasibility_policy() -> str` and `planner_prompt(envelope: dict) -> str`.
- Produces: a `music_or_audio_production` hard-prohibition class available to the existing model planner.

- [ ] **Step 1: Write the failing prompt-contract test**

```python
def test_prompt_prohibits_music_production_but_not_music_adjacent_software():
    planner = load_planner()
    prompt = planner.planner_prompt({"request_details": []})

    assert "music_or_audio_production" in prompt
    assert "generated or prompted music/audio" in prompt
    assert "music software" in prompt
```

- [ ] **Step 2: Run the test and verify RED**

Run: `python3 -m pytest -q skills/earn/gig/tests/test_application_planner_focus.py::test_prompt_prohibits_music_production_but_not_music_adjacent_software`

Expected: FAIL because the new prohibition text is absent.

- [ ] **Step 3: Add the minimal semantic policy**

Add `music_or_audio_production` to `HARD_PROHIBITION_CLASSES`, state the prohibition once in `common_marketplace_feasibility_policy()`, and add two short canonical boundary examples to `planner_prompt()`. Do not add parsing or execution code.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `python3 -m pytest -q skills/earn/gig/tests/test_application_planner_focus.py`

Expected: all tests pass.

- [ ] **Step 5: Update the Apply TODO and verify the diff**

Record the prompt version, deterministic test evidence, model evaluation evidence, deployment SHA, natural pass, and loaded release readback. Run `git diff --check` and confirm only owned files changed.

- [ ] **Step 6: Commit and push**

```bash
git add docs/superpowers/specs/2026-08-28-apply-no-music-production-design.md docs/superpowers/plans/2026-08-28-apply-no-music-production.md skills/earn/gig/scripts/application_planner.py skills/earn/gig/tests/test_application_planner_focus.py skills/earn/gig/TODO.md
git commit -m "fix(gig): prohibit music production applications"
git push -u origin fix/apply-no-music-prompts
```
