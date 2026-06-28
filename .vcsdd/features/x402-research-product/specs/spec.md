# Behavioral Spec — x402-research-product (lean)

Date: 2026-06-28 · Builder: main agent (me) · Mode: lean · Worktree: ~/anicca-human-funded

## Goal (provable)
A `$0`, zero-credential, universal web-research product the x402 seller serves: a buyer's query →
real curated web research digest. Works on ANY fresh install (no twitterapi, no firecrawl key, no Dais
creds) — only free tools: **Wikipedia opensearch + HN Algolia search + Jina Reader (`r.jina.ai`)**.
Replaces the twitterapi stub. Becomes `X402_PRODUCT_CMD` for the founder x402 seller.

`done =` R1–R7 verified by fresh evidence (real network run, no mock) AND fresh-context adversary PASS.

## Requirements (EARS)
- **R1** WHEN invoked with a non-empty query arg, the script SHALL search free, no-key, non-bot-blocked
  backends — **Wikipedia opensearch (general knowledge, any topic) + HN Algolia (tech/current)**, merged
  and deduped — and extract ≥1 real external result URL. (DuckDuckGo/Bing/Google HTML are NOT used: they
  bot-block keyless access — verified 2026-06-28. This R1 is the corrected backend per adversary FIND-001.)
  The two sources together make it UNIVERSAL (general + tech), not tech-only (adversary FIND-002).
- **R2** WHEN it has result URLs, the script SHALL fetch the top ≤3 via Jina Reader (`https://r.jina.ai/<url>`,
  free, no key) and return their cleaned content.
- **R3** The script SHALL print to stdout a single JSON object `{query, sources:[...], digest:"..."}` with
  a NON-EMPTY digest, and exit 0 on success.
- **R4** WHEN the query is empty/missing, the script SHALL exit non-zero (usage error) and write nothing
  fake to stdout.
- **R5 (invariant)** The script SHALL NOT reference or require any paid/keyed/secret service env
  (TWITTERAPI_KEY, FIRECRAWL_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, BRAVE_API_KEY, CDP_*,
  *_PRIVATE_KEY, GOOGLE_LOGIN_*, any Dais cred). $0 + zero-config only.
- **R6 (content quality, anti-fake)** WHEN Jina Reader returns a body, the script SHALL accept it ONLY
  if it is real content (≥300 chars AND not matching an error/placeholder pattern: rate-limit/429/
  auth-required/"could not be reached"). A placeholder/error body SHALL be treated as a failed source
  (skip + try next), never returned as a paid digest. If ALL sources fail/placeholder → exit non-zero
  (no fake success). (adversary FIND-003.)
- **R7 (rate-limit honesty)** WHEN Jina Reader returns 429, the script SHALL back off + retry (≤3) and,
  if still rate-limited for all sources, exit non-zero — never a partial/fake digest. (adversary FIND-006.)

## Verification architecture (no-mock)
| Req | Check | Pass |
|---|---|---|
| R1 | run with a real query; inspect `sources` | ≥1 http(s) URL, none on duckduckgo.com |
| R2 | inspect `digest` | contains content fetched via r.jina.ai (non-empty per source) |
| R3 | `node research-product.mjs "x402 agent payments"` → parse stdout | valid JSON, digest length > 200, exit 0 |
| R4 | `node research-product.mjs ""` | exit ≠ 0, empty/usage stderr, no JSON on stdout |
| R5 | static grep of the file | zero matches for TWITTERAPI/FIRECRAWL/OPENAI/BRAVE/CDP/_PRIVATE_KEY/secret env |
| R6 | unit-feed an error/placeholder body to `isRealContent` | returns false (rejected); a real ≥300-char body returns true |
| R7 | inspect `jinaRead` 429 path + run when all sources unreachable | backoff≤3 then throw; `research()` exits non-zero, never a partial digest |

## Purity boundary
- I/O (impure): the fetch calls (Wikipedia opensearch, HN Algolia, Jina Reader).
- Pure (unit-testable, no network): `isRealContent` (content-quality gate), result merge/dedup, JSON
  assembly, arg parsing.

## Out of scope
- LLM synthesis (the buying agent synthesizes; this product delivers curated raw research = $0, deterministic).
- The x402 host/facilitator wiring (separate feature x402-go-live).
