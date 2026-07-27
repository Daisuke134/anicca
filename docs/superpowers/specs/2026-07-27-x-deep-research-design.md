# X Deep Research — Claude/Codex Shared Skill Design

## Goal

Build one repository-tracked X research skill that Claude and Codex can both
use to:

1. search X through the already-authenticated daily-driver without consuming
   X API credits;
2. read a known X post or X Article in full without login or an API key; and
3. never navigate an X Article editor, composer, or publication tab.

The skill is a research/read plane only. Existing Writer publishers remain the
write plane.

## Evidence behind the design

| Decision | Source | Core quote |
|---|---|---|
| Reuse a general browser/tool surface instead of inventing a private API client | [The Anatomy of an Agent Harness](https://www.langchain.com/blog/the-anatomy-of-an-agent-harness) | “Bash + code exec is a big step towards giving models a computer.” |
| Keep filesystem state and code versioned | [The Anatomy of an Agent Harness](https://www.langchain.com/blog/the-anatomy-of-an-agent-harness) | “Git adds versioning to the filesystem so agents can track work, rollback errors, and branch experiments.” |
| Use the existing authenticated browser only for search | [x-search-cdp](/Users/anicca/.agents/skills/x-search-cdp/SKILL.md) | “reuses the real logged-in browser session” |
| Use FxTwitter reconstruction for known X Article URLs | [x-tweet-fetcher](https://github.com/ythx-101/x-tweet-fetcher) | “Fetch X/Twitter tweets, replies, timelines, lists, and articles — no login, no API keys.” |
| Pin the upstream implementation | [x-tweet-fetcher commit](https://github.com/ythx-101/x-tweet-fetcher/commit/085b931f53557da9e25c0d2e6aa5b3b980513125) | “restore acknowledgments and footer from v1” |
| Do not make Firecrawl the X retrieval authority | Live benchmark, 2026-07-27 | FxTwitter returned full Article bodies for 6/6 specified URLs; Firecrawl returned a full body for only 1/3 sampled URLs. |
| Keep official X API as a later adapter | [X Search Posts](https://docs.x.com/x-api/posts/search/introduction) | “Full-archive search is available to pay-per-use and Enterprise customers.” |
| Keep real X Article publishing in the official write plane | [X Articles API](https://docs.x.com/x-api/articles/introduction) | “programmatically create draft long-form Articles … then publish them to X.” |

The configured official X API currently returns `402 credits depleted`.
Therefore it cannot be the no-human research path until credits are restored.
Purchasing credits is outside this implementation.

## Existing system and defect

The current local script at
`/Users/anicca/.agents/skills/x-search-cdp/x_search.py` selects the first page
whose URL contains `x.com`, then calls `goto()` on it. The Writer currently has
live X Article edit tabs at `/compose/articles/edit/...`. A research invocation
can therefore replace an editor tab and destroy unsaved work.

The existing script also stops after three scrolls and returns only handle,
visible text, and URL. It does not have a stable completeness contract or a
known-URL full-text path.

## Architecture

```text
                         read-only request
                                |
                +---------------+----------------+
                |                                |
          search <query>                     fetch <X URL>
                |                                |
     daily-driver CDP :9222            pinned x-tweet-fetcher
                |                                |
  dedicated /search tab only          FxTwitter Draft.js blocks
                |                                |
 scroll -> dedupe -> metrics          normalized post/article JSON
                +---------------+----------------+
                                |
                    common JSON + Markdown
```

### Browser search adapter

The adapter follows this page-selection policy in order:

1. reuse an existing `x.com/search` page;
2. reuse an existing `about:blank` page;
3. create one new page in the authenticated browser context;
4. never reuse a URL containing `/compose`, `/articles/edit`, `/intent/`,
   `/settings`, or `/messages`.

The adapter scrolls until one of these deterministic terminal conditions:

- `count` unique status URLs collected;
- `max_scrolls` reached;
- three consecutive scrolls add no new unique status URL.

Every result records the canonical status URL, visible text, author label, and
visible engagement labels. The top-level result records:

- `requested_count`;
- `result_count`;
- `scrolls`;
- `complete`;
- `partial_reason`;
- `page_reused`;
- `page_created`.

`complete=false` is not converted to success.

### Known-URL fetch adapter

The adapter invokes the upstream package at the exact reviewed commit:

```text
uvx --from git+https://github.com/ythx-101/x-tweet-fetcher.git@085b931f53557da9e25c0d2e6aa5b3b980513125 xtf --url <url>
```

It returns upstream JSON unchanged under `raw` and adds a small stable envelope:

- `source = "x-tweet-fetcher/fxtwitter"`;
- `url`;
- `kind = "post" | "article"`;
- `complete`;
- `error_code`;
- `fetched_at`.

No browser fallback is silently attempted. A failed upstream fetch is a
machine-readable failure.

### Skill sharing

The canonical tracked skill lives at:

```text
.agents/skills/x-deep-research/
```

Claude receives the established repository symlink:

```text
.claude/skills/x-deep-research -> ../../.agents/skills/x-deep-research
```

Codex already discovers project skills from `.agents/skills`. There is no
second copied implementation.

## Boundaries

| In scope | Out of scope |
|---|---|
| X keyword search through authenticated CDP | Purchasing X API or Xquik credits |
| Safe dedicated search page | Changing Writer publication state |
| Deep known-URL/X Article fetch | Posting, replying, liking, deleting |
| Common JSON and Markdown output | Replacing current X Article browser publisher |
| Claude/Codex shared skill | Moving the full Marketing Loop before T13 |
| Live read-only E2E | Claiming complete reply coverage without a cursor/API |

## Failure policy

| Failure | Result |
|---|---|
| CDP unavailable | exit 2, `browser_unavailable` |
| No authenticated context | exit 2, `authenticated_context_missing` |
| Search produces fewer than requested | exit 0 with `complete=false` and explicit `partial_reason` |
| X DOM contract absent | exit 3, `dom_contract_changed` |
| FxTwitter/upstream unavailable | exit 4 with upstream error code and stderr summary |
| Invalid/non-X URL | exit 2, `invalid_input` |
| Any write-intent subcommand | unsupported; CLI has no write commands |

## Acceptance criteria

| ID | Done condition |
|---|---|
| AC1 | Unit test proves an Article editor page is never selected when it is the only X page. |
| AC2 | Unit test proves an existing search page is preferred over editor/composer pages. |
| AC3 | Live search returns at least 20 unique status URLs from the current authenticated daily-driver without changing either Article editor URL. |
| AC4 | The six user-specified X Article URLs return complete full text through the pinned fetch adapter. |
| AC5 | Repeated status URLs are deduplicated and partial results expose the stop reason. |
| AC6 | `.agents` is canonical and the Claude path is a symlink, not a copy. |
| AC7 | The full test suite passes and a live read-only smoke exits 0. |

## Self-review

- No implementation modifies Writer state or opens a publication path.
- No credential value is read into output.
- The upstream package is pinned, not fetched from a moving branch.
- “Deep” is bounded and observable; reply completeness is not fabricated.
- The design does not depend on replenishing paid API credits.

