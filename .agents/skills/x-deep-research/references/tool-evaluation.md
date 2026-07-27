# X Research Tool Evaluation — 2026-07-27

## Decision

The production target is a three-plane design:

| Plane | Preferred adapter | Current usable adapter |
|---|---|---|
| Deep search, replies, quotes, cursors | Xquik | Authenticated CDP search |
| Known URL / complete X Article read | x-tweet-fetcher/FxTwitter | x-tweet-fetcher/FxTwitter |
| Posts and true X Article publishing | Official `xurl` / X API | Existing Writer browser publisher |

The shared skill implements the two free, live read adapters. It intentionally
does not replace the Writer publisher.

## Live benchmark

### Complete X Article fetch

The pinned x-tweet-fetcher revision returned `complete=true` for all six
specified URLs:

| URL | Title | Full-text characters |
|---|---|---:|
| [ArchiveExplorer](https://x.com/archiveexplorer/status/2080621294979023358) | LOOP → GRAPH → HARNESS | 7,838 |
| [Vtrivedy10](https://x.com/vtrivedy10/status/2079976006644072796) | Towards Automating Eval Engineering | 5,541 |
| [0xCodila](https://x.com/0xcodila/status/2079597821511020996) | Graph Engineering: 1000+ agent loops | 10,999 |
| [Argona0x](https://x.com/argona0x/status/2080626046903157126) | Graph Engineering: layer between prompts and product | 12,283 |
| [beamnxw](https://x.com/beamnxw/status/2081022966645535079) | Harness vs Loop vs Graph | 15,256 |
| [beamnxw AgenticRAG](https://x.com/beamnxw/status/2079523981363692005) | AgenticRAG | 4,074 |

The same benchmark sampled through Firecrawl returned a full Article body for
one of three URLs and preview/visible-comment content for two of three. That is
why Firecrawl is not the authority for X Article completeness.

### Authenticated search

The safe CDP adapter returned 20 unique status URLs after eight scrolls for:

```text
("loop engineering" OR "eval engineering" OR "self-improving agent")
since:2026-07-01 min_faves:20 -filter:replies
```

It reported:

```json
{
  "result_count": 20,
  "scrolls": 8,
  "complete": true,
  "partial_reason": null,
  "page_reused": true,
  "page_created": false
}
```

Both pre-existing X Article editor URLs remained unchanged.

## Candidate comparison

| Tool | Auth/cost | Search depth | Replies/quotes/Article | Writes | Decision |
|---|---|---|---|---|---|
| Xquik | API key/OAuth, pay as you go from $10 | Cursor pagination, advanced operators, bulk export | Thread, replies, quotes, Article body | Posts, replies, media, 25k Note Tweet; not true Article publishing | Best future deep-search plane |
| x-tweet-fetcher | No key for single URLs | Search depends on Nitter/browser | Threaded replies and complete X Article reconstruction | None | Adopt known-URL plane |
| x-research-skill | X Bearer Token and API credits | Recent search, up to five pages | Conversation search, no Article-body adapter | None | Existing but credits depleted and incomplete |
| x-cli | Five official credentials and API credits | Recent plus full archive pagination | No dedicated thread/Article adapter | Post/reply/quote | Useful official CLI, not the single research plane |
| xurl | Developer app/OAuth and API credits | Raw access to any v2 endpoint | Official API objects | True X Article draft/publish | Best future write plane |
| Firecrawl | Existing credits | URL scrape, no reliable X search corpus | Inconsistent Article depth | None | Secondary check only |

## Sources

ソース: [Xquik Search Tweets](https://docs.xquik.com/api-reference/x/search-tweets)  
核心の引用: “Large `limit` pulls are resumable.”

ソース: [Xquik Tweet Replies](https://docs.xquik.com/api-reference/x/tweet-replies)  
核心の引用: “Reply visibility can be incomplete.”

ソース: [Xquik pricing](https://xquik.com/en#pricing)  
核心の引用: “Pay as you go from $10.”

ソース: [x-tweet-fetcher](https://github.com/ythx-101/x-tweet-fetcher)  
核心の引用: “Fetch X/Twitter tweets, replies, timelines, lists, and articles — no login, no API keys.”

ソース: [x-research skill](https://github.com/rohunvora/x-research-skill/blob/main/SKILL.md)  
核心の引用: “currently uses recent search (last 7 days).”

ソース: [x-cli](https://github.com/Infatoshi/x-cli)  
核心の引用: “Add `--all-pages` to follow pagination.”

ソース: [xurl](https://github.com/xdevplatform/xurl)  
核心の引用: “raw curl-style access to any v2 endpoint.”

ソース: [X Articles API](https://docs.x.com/x-api/articles/introduction)  
核心の引用: “programmatically create draft long-form Articles … then publish them to X.”

ソース: [X API pricing](https://docs.x.com/x-api/getting-started/pricing)  
核心の引用: “Posts: Read $0.005 per resource.”

## Known limitations

| Limitation | Consequence |
|---|---|
| CDP search uses the rendered DOM | X can change selectors; a zero-result query must distinguish no-results from contract breakage |
| Virtualized timeline | Results must be accumulated after every scroll |
| No cursor in free CDP route | `complete=true` means requested count reached, not total-corpus completeness |
| Replies are not enriched in the current free route | Do not claim complete conversation coverage |
| x-tweet-fetcher depends on FxTwitter for single URLs | Keep the pinned revision and surface upstream failures |
| Official credits depleted | Full archive and official write API are unavailable until externally funded |

