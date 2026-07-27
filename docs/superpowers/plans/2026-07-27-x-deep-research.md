# X Deep Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and superpowers:verification-before-completion. Implement task-by-task in the isolated worktree.

**Goal:** Create one tracked, read-only X research skill that safely searches through the authenticated daily-driver, fetches full X Articles through a pinned upstream tool, and is shared by Claude and Codex.

**Architecture:** A Python browser adapter owns safe search-tab selection and bounded scrolling. A separate Python fetch adapter owns the pinned `x-tweet-fetcher` subprocess boundary. A small CLI exposes `search` and `fetch`, while `.agents/skills` remains the canonical skill tree and `.claude/skills` points to it with a symlink.

**Tech Stack:** Python 3.11+, Playwright, pytest, uv/uvx, x-tweet-fetcher commit `085b931f53557da9e25c0d2e6aa5b3b980513125`.

## Global Constraints

- Read-only: no post, reply, like, delete, draft, or publish command.
- Never navigate an existing `/compose` or `/articles/edit` page.
- Do not expose credentials or browser storage.
- Return `complete=false` for bounded partial retrieval; never relabel it as complete.
- Preserve Writer §22.6 ordering; this tool is independent and does not migrate the Marketing Loop.
- Use the exact pinned upstream commit.

---

### Task 1: Safe browser page selection

**Files:**
- Create: `.agents/skills/x-deep-research/scripts/browser_search.py`
- Test: `.agents/skills/x-deep-research/tests/test_browser_search.py`

**Interfaces:**
- Consumes: a list of Playwright-like page objects exposing `.url`
- Produces: `classify_page(url: str) -> str` and `choose_search_page(pages: Sequence[PageLike]) -> PageLike | None`

- [ ] **Step 1: Write the failing tests**

```python
from browser_search import choose_search_page, classify_page


class Page:
    def __init__(self, url: str):
        self.url = url


def test_article_editor_is_never_selected_for_search():
    editor = Page("https://x.com/compose/articles/edit/2081491516254830592")
    assert choose_search_page([editor]) is None


def test_existing_search_page_wins_over_editor_and_blank():
    editor = Page("https://x.com/compose/articles/edit/2081491516254830592")
    blank = Page("about:blank")
    search = Page("https://x.com/search?q=agents&src=typed_query")
    assert choose_search_page([editor, blank, search]) is search


def test_blank_page_is_safe_fallback():
    blank = Page("about:blank")
    assert choose_search_page([blank]) is blank


def test_messages_and_settings_are_protected():
    assert classify_page("https://x.com/messages") == "protected"
    assert classify_page("https://x.com/settings/account") == "protected"
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
uv run --with pytest pytest -q .agents/skills/x-deep-research/tests/test_browser_search.py
```

Expected: collection fails because `browser_search` does not exist.

- [ ] **Step 3: Implement the minimal selection policy**

```python
PROTECTED_MARKERS = (
    "/compose",
    "/articles/edit",
    "/intent/",
    "/settings",
    "/messages",
)


def classify_page(url: str) -> str:
    if any(marker in url for marker in PROTECTED_MARKERS):
        return "protected"
    if url.startswith("https://x.com/search"):
        return "search"
    if url == "about:blank":
        return "blank"
    return "other"


def choose_search_page(pages):
    for kind in ("search", "blank"):
        for page in pages:
            if classify_page(page.url) == kind:
                return page
    return None
```

- [ ] **Step 4: Run the tests and verify GREEN**

Run the Step 2 command. Expected: `4 passed`.

- [ ] **Step 5: Commit and push**

```bash
git add .agents/skills/x-deep-research/scripts/browser_search.py \
  .agents/skills/x-deep-research/tests/test_browser_search.py
git commit -m "feat(x-research): protect X editor tabs"
git push -u origin research/self-improving-ai-20260727
```

### Task 2: Bounded deep search and completeness

**Files:**
- Modify: `.agents/skills/x-deep-research/scripts/browser_search.py`
- Modify: `.agents/skills/x-deep-research/tests/test_browser_search.py`

**Interfaces:**
- Consumes: `query`, `mode`, `count`, `max_scrolls`, `cdp_url`
- Produces: `SearchReport.to_dict()` with unique results and completeness metadata

- [ ] **Step 1: Add failing behavior tests**

```python
from browser_search import dedupe_results, stop_reason


def test_duplicate_status_urls_keep_one_result():
    rows = [
        {"url": "https://x.com/a/status/1", "text": "one"},
        {"url": "https://x.com/a/status/1", "text": "one repeated"},
        {"url": "https://x.com/b/status/2", "text": "two"},
    ]
    assert dedupe_results(rows) == [
        {"url": "https://x.com/a/status/1", "text": "one"},
        {"url": "https://x.com/b/status/2", "text": "two"},
    ]


def test_requested_count_marks_complete():
    assert stop_reason(result_count=20, requested_count=20, scrolls=4, max_scrolls=30, stagnant=0) is None


def test_stagnation_is_explicit_partial_reason():
    assert stop_reason(result_count=8, requested_count=20, scrolls=7, max_scrolls=30, stagnant=3) == "stagnant_after_3_scrolls"


def test_scroll_cap_is_explicit_partial_reason():
    assert stop_reason(result_count=18, requested_count=20, scrolls=30, max_scrolls=30, stagnant=0) == "max_scrolls_reached"
```

- [ ] **Step 2: Verify RED**

Run the Task 1 test command. Expected: import failures for `dedupe_results` and `stop_reason`.

- [ ] **Step 3: Implement helpers and live adapter**

Implement:

```python
def dedupe_results(rows):
    unique = {}
    for row in rows:
        url = row.get("url", "").split("/analytics", 1)[0]
        if url and url not in unique:
            unique[url] = {**row, "url": url}
    return list(unique.values())


def stop_reason(result_count, requested_count, scrolls, max_scrolls, stagnant):
    if result_count >= requested_count:
        return None
    if stagnant >= 3:
        return "stagnant_after_3_scrolls"
    if scrolls >= max_scrolls:
        return "max_scrolls_reached"
    return "insufficient_results"
```

Add Playwright orchestration that:

1. connects to CDP;
2. records all protected page URLs before navigation;
3. uses `choose_search_page`, or creates one page only when no safe page exists;
4. navigates only that page;
5. collects `article[data-testid="tweet"]` rows after every scroll;
6. exits at count, stagnation, or cap;
7. verifies protected page URLs are unchanged before printing JSON.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
uv run --with pytest pytest -q .agents/skills/x-deep-research/tests
```

Expected: `8 passed`.

- [ ] **Step 5: Live read-only smoke**

Run:

```bash
uv run --with playwright .agents/skills/x-deep-research/scripts/browser_search.py \
  '"loop engineering" OR "eval engineering"' \
  --mode top --count 20 --max-scrolls 30
```

Expected: exit 0, 20 unique status URLs or an explicit partial reason, and both
pre-existing Article editor URLs unchanged.

- [ ] **Step 6: Commit and push**

```bash
git add .agents/skills/x-deep-research/scripts/browser_search.py \
  .agents/skills/x-deep-research/tests/test_browser_search.py
git commit -m "feat(x-research): add bounded deep X search"
git push
```

### Task 3: Pinned full-post and X Article fetch

**Files:**
- Create: `.agents/skills/x-deep-research/scripts/x_fetch.py`
- Create: `.agents/skills/x-deep-research/tests/test_x_fetch.py`

**Interfaces:**
- Consumes: one canonical `https://x.com/<handle>/status/<id>` URL
- Produces: normalized JSON envelope with `source`, `kind`, `complete`, `raw`, and error fields

- [ ] **Step 1: Write failing tests**

```python
import pytest

from x_fetch import build_command, normalize_payload, validate_url


def test_rejects_non_x_url():
    with pytest.raises(ValueError, match="canonical X status URL"):
        validate_url("https://example.com/status/1")


def test_command_pins_reviewed_upstream_commit():
    assert build_command("https://x.com/a/status/1") == [
        "uvx",
        "--from",
        "git+https://github.com/ythx-101/x-tweet-fetcher.git@085b931f53557da9e25c0d2e6aa5b3b980513125",
        "xtf",
        "--url",
        "https://x.com/a/status/1",
    ]


def test_article_payload_is_marked_complete():
    raw = {"article": {"title": "T", "content": "full body"}}
    got = normalize_payload("https://x.com/a/status/1", raw)
    assert got["kind"] == "article"
    assert got["complete"] is True


def test_empty_article_body_is_not_complete():
    raw = {"article": {"title": "T", "content": ""}}
    got = normalize_payload("https://x.com/a/status/1", raw)
    assert got["complete"] is False
    assert got["error_code"] == "empty_article_body"
```

- [ ] **Step 2: Verify RED**

Run:

```bash
uv run --with pytest pytest -q .agents/skills/x-deep-research/tests/test_x_fetch.py
```

Expected: collection fails because `x_fetch` does not exist.

- [ ] **Step 3: Implement the subprocess boundary**

Implement exact URL validation, the pinned command, `subprocess.run` with a
60-second timeout, JSON parsing, and normalization. Preserve the complete
upstream object under `raw`. Map timeout, non-zero exit, malformed JSON, and
empty body to distinct error codes.

- [ ] **Step 4: Verify GREEN**

Run all skill tests. Expected: all tests pass.

- [ ] **Step 5: Live six-URL benchmark**

Run `x_fetch.py` for the six specified URLs and assert:

```text
complete=true for 6/6
kind=article for 6/6
non-empty article content for 6/6
```

- [ ] **Step 6: Commit and push**

```bash
git add .agents/skills/x-deep-research/scripts/x_fetch.py \
  .agents/skills/x-deep-research/tests/test_x_fetch.py
git commit -m "feat(x-research): fetch complete X Articles"
git push
```

### Task 4: Shared skill contract and final verification

**Files:**
- Create: `.agents/skills/x-deep-research/SKILL.md`
- Create: `.agents/skills/x-deep-research/references/tool-evaluation.md`
- Create symlink: `.claude/skills/x-deep-research`

**Interfaces:**
- Consumes: natural-language X research requests from Claude or Codex
- Produces: one documented invocation contract for search and fetch

- [ ] **Step 1: Write the skill contract**

The skill must instruct the agent to:

- use `browser_search.py` for keyword/topic discovery;
- use `x_fetch.py` for every selected status URL before quoting or summarizing;
- preserve `complete` and `partial_reason`;
- cite canonical X URLs;
- use Firecrawl only as an optional second-source check;
- never use the research skill for writes;
- never call the depleted official API until a health check succeeds.

- [ ] **Step 2: Create the Claude symlink**

Run:

```bash
ln -s ../../.agents/skills/x-deep-research .claude/skills/x-deep-research
```

- [ ] **Step 3: Verify the shared layout**

Run:

```bash
test "$(readlink .claude/skills/x-deep-research)" = "../../.agents/skills/x-deep-research"
test -f .agents/skills/x-deep-research/SKILL.md
```

Expected: exit 0.

- [ ] **Step 4: Run the complete verification matrix**

Run:

```bash
uv run --with pytest pytest -q .agents/skills/x-deep-research/tests
uv run --with playwright .agents/skills/x-deep-research/scripts/browser_search.py \
  '"loop engineering" OR "eval engineering"' --mode top --count 20 --max-scrolls 30
```

Then run the six `x_fetch.py` live fixtures. Confirm no Writer publication file
changed and no protected browser URL changed.

- [ ] **Step 5: Self-review**

Check:

- no placeholder text;
- no write command;
- no credential output;
- pinned upstream hash;
- editor-tab protection test;
- partial retrieval remains explicit.

- [ ] **Step 6: Commit and push**

```bash
git add .agents/skills/x-deep-research .claude/skills/x-deep-research
git commit -m "feat(x-research): share deep X research across agents"
git push
```

