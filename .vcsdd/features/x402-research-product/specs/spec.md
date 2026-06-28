# Behavioral Spec — x402-research-product (lean)

Date: 2026-06-28 · Builder: main agent (me) · Mode: lean · Worktree: ~/anicca-human-funded

## Goal (provable)
A `$0`, zero-credential, universal web-research product the x402 seller serves: a buyer's query →
real curated web research digest. Works on ANY fresh install (no twitterapi, no firecrawl key, no Dais
creds) — only free tools: DuckDuckGo HTML search + Jina Reader (`r.jina.ai`). Replaces the twitterapi
stub. Becomes `X402_PRODUCT_CMD` for the founder x402 seller.

`done =` R1–R5 verified by fresh evidence (real network run, no mock) AND fresh-context adversary PASS.

## Requirements (EARS)
- **R1** WHEN invoked with a non-empty query arg, the script SHALL search DuckDuckGo HTML (free, no key)
  and extract ≥1 real external result URL.
- **R2** WHEN it has result URLs, the script SHALL fetch the top ≤3 via Jina Reader (`https://r.jina.ai/<url>`,
  free, no key) and return their cleaned content.
- **R3** The script SHALL print to stdout a single JSON object `{query, sources:[...], digest:"..."}` with
  a NON-EMPTY digest, and exit 0 on success.
- **R4** WHEN the query is empty/missing, the script SHALL exit non-zero (usage error) and write nothing
  fake to stdout.
- **R5 (invariant)** The script SHALL NOT reference or require any paid/keyed service env
  (TWITTERAPI_KEY, FIRECRAWL_API_KEY, OPENAI_API_KEY, CDP_*, any Dais cred). $0 + zero-config only.

## Verification architecture (no-mock)
| Req | Check | Pass |
|---|---|---|
| R1 | run with a real query; inspect `sources` | ≥1 http(s) URL, none on duckduckgo.com |
| R2 | inspect `digest` | contains content fetched via r.jina.ai (non-empty per source) |
| R3 | `node research-product.mjs "x402 agent payments"` → parse stdout | valid JSON, digest length > 200, exit 0 |
| R4 | `node research-product.mjs ""` | exit ≠ 0, empty/usage stderr, no JSON on stdout |
| R5 | static grep of the file | zero matches for TWITTERAPI/FIRECRAWL/OPENAI/CDP/secret env |

## Purity boundary
- I/O (impure): the two fetch calls (DDG, Jina).
- Pure: URL extraction from DDG HTML, JSON assembly, arg parsing.

## Out of scope
- LLM synthesis (the buying agent synthesizes; this product delivers curated raw research = $0, deterministic).
- The x402 host/facilitator wiring (separate feature x402-go-live).
