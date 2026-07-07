# business.blockrun.ai seller-listing feasibility research record

**feature**: anicca-agent-economy · **requirement**: REQ-301/302 · **research performed**: 2026-07-07
(this record's own writing timestamp — see the individual PR/site checks below for their own observed
timestamps, since this is a live, open-source, actively-changing surface).

**Question**: does Franklin (BlockRunAI/Franklin) have a path to LIST a skill/gig FOR SALE on
`business.blockrun.ai` (BlockRun's own hosted marketplace) — i.e. become a **seller**, as distinct from
`BlockRunAI/Franklin` PR#83's `agent_talent` tool, which makes Franklin a **buyer** on that marketplace?

---

## (a) Does a seller/listing API or code path exist?

**Finding: NO. Only a manual, human-mediated onboarding path exists; no self-serve seller/listing API or
code path was found anywhere in BlockRunAI's public repos or blockrun.ai's own documentation.**

Evidence checked:

1. **PR#83 itself is buyer-only.** `gh pr view 83 --repo BlockRunAI/Franklin` (checked 2026-07-07,
   `state: OPEN`, `mergedAt: null`, `createdAt: 2026-06-13T07:21:43Z`, `updatedAt:
   2026-06-13T08:07:53Z` — over three weeks stale as of this research, no further activity since it was
   opened) adds exactly two surfaces, both consumer-side: a `/market` terminal command
   (`browse`/`search`/`info`/`run`) and an `agent_talent` tool (`{action:"list"|"run"}`). Its own PR body
   states the payment client (`src/market/client.ts`) does `POST /api/v1/skills/<slug>/run` against
   `BLOCKRUN_MARKET_URL` (default `https://business.blockrun.ai`) — a **consumption** endpoint. No
   `POST .../skills` (create-listing), no `PUT/PATCH .../skills/<slug>` (update-listing), and no
   publish/list/register verb of any kind appears anywhere in the diff (`git diff` file list: `commands.ts`,
   `permissions.ts`, `config.ts`, `market/client.ts`, `agent-talent.ts`, `tools/index.ts`,
   `test/market.local.mjs` — all consumer-facing).
2. **No seller/listing terms anywhere in the Franklin repo's PR history.** `gh pr list --repo
   BlockRunAI/Franklin --search "seller" --state all` returns exactly one, unrelated hit (PR#62, a
   Predexon prediction-market schema fix that merely contains the substring "seller" nowhere relevant).
   `gh pr list --repo BlockRunAI/Franklin --search "market seller listing publish" --state all` returns
   zero hits. A full listing of all 50+ PRs in the repo (`gh pr list --state all --limit 50`) shows no
   PR titled or scoped around listing/publishing/selling a skill.
3. **`business.blockrun.ai` itself does not currently resolve.** `firecrawl scrape
   https://business.blockrun.ai markdown` (checked 2026-07-07) returned a DNS resolution failure ("the
   domain name could not be translated to an IP address"). This is either a renamed/retired
   internal/staging subdomain (PR#83 was written 2026-06-13, over three weeks before this check) or a
   transient outage; either way, no live seller-facing surface was directly reachable at the URL PR#83's
   own code references.
4. **The actual live marketplace lives at `blockrun.ai` (not `business.blockrun.ai`), and its own
   documented "Add yours" section confirms sellers are onboarded manually, not via a self-serve API.**
   `firecrawl scrape https://blockrun.ai markdown` (checked 2026-07-07) shows a "Service marketplace"
   section (`blockrun.ai/marketplace/<slug>`) listing exactly 7 live partner integrations (Exa/Onchain
   RPC/Predexon/Modal Sandbox/0x Swap/Twilio+Bland/Surf/ElevenLabs — all pre-existing, named companies),
   followed verbatim by:
   > "Add yours — List a data source — On-chain data, financial feeds, niche APIs — we onboard weekly.
   > [Contact us →](https://t.me/bc1max)"

   This is the ONLY seller-onboarding path documented anywhere on the live site: a **Telegram DM to a
   human** (`t.me/bc1max`), described as "we onboard weekly" — i.e. a manual, business-development-style
   review-and-integrate process, not a programmatic API a Franklin instance could call autonomously.
5. **`blockrun.ai/docs`'s full sidebar (checked 2026-07-07, `firecrawl scrape
   https://blockrun.ai/docs markdown`) contains no "publish"/"list your skill"/"become a
   provider"/"marketplace API" reference page.** The API Reference section documents 15+ CONSUMER-side
   endpoints (chat completions, image/video/music generation, Exa search, 0x swap, Modal sandbox, RPC,
   voice/phone, prediction markets, etc.) — every one of them a thing an agent PAYS for, none a thing an
   agent LISTS for others to pay for.
6. **The org's own public roadmap explicitly frames a general "Agent Marketplace" as a FUTURE item, not a
   shipped self-serve feature.** `BlockRunAI/polymarket-agent`'s README (`gh api
   repos/BlockRunAI/polymarket-agent/contents/README.md`) contains a roadmap table: "Agent Marketplace |
   Discover and hire specialized agents | 2026 Q3" — i.e., even the DISCOVER/HIRE (buyer) side of a
   broader "Agent Marketplace" concept is roadmapped for Q3 2026, later than PR#83's June 2026 buyer-side
   work; nothing in that roadmap table names a seller/listing feature at all.

**Conclusion for (a): no seller/listing API or code path exists today.** The only path to appear as a
paid marketplace offering is a manual, human-reviewed "Contact us" business relationship (via Telegram),
explicitly scoped in the site's own copy to "data sources... on-chain data, financial feeds, niche APIs"
— not obviously a fit for an arbitrary AI-agent-produced skill/gig, and in any case incompatible with a
zero-human-loop autonomous listing flow.

## (b) Fee/take-rate structure

**Finding: not discoverable for a THIRD-PARTY seller, because no seller-facing terms exist to read.**
What IS documented, for context, is BlockRun's OWN first-party model-gateway margin: blockrun.ai's
homepage states "Provider cost + 5% margin at settlement" for its 60+-model AI gateway product — this is
BlockRun's markup on ITS OWN reselling of upstream model providers (OpenAI/Anthropic/etc.), not a
take-rate on a third-party seller's marketplace listing. No fee schedule, revenue split, or take-rate
percentage for a THIRD-PARTY creator/seller listing was found anywhere in the docs sidebar, the
marketplace partner pages (checked `blockrun.ai/marketplace/exa` in detail — it shows per-call USDC
pricing set BY Exa, with no visible BlockRun cut disclosed), or the PR#83 diff. This is recorded as a
definitive "not found, here is what was checked" negative per REQ-301's own edge-case guidance, not left
as a silent unknown.

## (c) Which side holds the Coinbase CDP dependency, and does it touch Franklin's own wallet/KYC surface?

**Finding: the CDP dependency observed in PR#83 sits on the MARKETPLACE side (business.blockrun.ai's own
payment-verification backend), not on Franklin's own wallet or KYC surface — as a BUYER.** Quoting PR#83's
own body directly:
> "Live E2E vs. real Coinbase CDP (Base mainnet). Franklin's built `dist` client (both
> `runMarketSkill` and the `agent_talent` tool) ran against a shim wired to business.blockrun.ai's **real**
> `verifyPayment` + **real CDP `/verify`**... This closes the one untested real-world link: **CDP accepts
> the signature `@blockrun/llm` produces, and it clears the route's strict exact-price gate.**"

Franklin's OWN payment path (`src/market/client.ts`) uses the SAME standard x402 primitive Franklin
already uses for the existing BlockRun LLM gateway (`src/tools/blockrun.ts`): a normal EVM wallet + the
`@blockrun/llm` signer, producing one EIP-3009 `exact`-authorization signature. Franklin itself never
creates, authenticates against, or holds credentials for a Coinbase CDP account anywhere in this diff —
CDP is called ONLY server-side, by the marketplace's own route, to VERIFY the payment signature Franklin
already produced with its own wallet key. blockrun.ai's own homepage independently corroborates this from
the buyer side: "No accounts, no KYC — Wallet in, prompt out. Pseudonymous by default." (this applies to
callers/buyers of the gateway and, per the shared payment path, to marketplace buyers too).

**However, this is confirmed ONLY for the BUYER role** (the one PR#83 actually implements and the one the
CDP evidence above concerns). Whether a prospective SELLER (a creator being onboarded via the manual
"Contact us" Telegram path in (a)) would separately be required to hold or create a Coinbase CDP account
for PAYOUT settlement is **not discoverable from public evidence** — no seller-onboarding documentation
exists to check (see (a)). This gap is recorded honestly rather than assumed either way. Per REQ-301's own
edge case ("a seller-listing path is found but REQUIRES a marketplace-side Coinbase CDP account or KYC
step... this MUST be flagged as human-zero-violating"): since no such path was found to even evaluate,
this cannot yet be marked human-zero-violating OR human-zero-clean — it is UNKNOWN, gated behind (a)'s
negative finding, and would need to be re-checked the moment a real seller-onboarding flow appears.

## (d) Implementation-effort estimate (if a viable path exists)

**Finding: not applicable — no viable self-serve implementation path exists to estimate the effort of
(direct consequence of (a)'s negative finding).** The only real "implementation" work discoverable is
non-technical: initiating and completing a manual business conversation via Telegram
(`t.me/bc1max`), which is explicitly a human-in-the-loop relationship-building step (BlockRun "onboards
weekly" — implying a review/negotiation cadence, not an instant self-serve flow), not a coding task this
increment (or Franklin) could size in engineering terms. If a future self-serve seller API DOES ship,
re-run this research to produce a real size/complexity estimate against that concrete API surface — none
exists today to size against.

## (e) Recommendation: pursue / deprioritize / blocked-by-X, vs. the self-built P2P gig board

**Recommendation: DEPRIORITIZE (not "blocked" in the human-zero sense, but blocked by the absence of any
programmatic path at all — there is nothing to integrate against today).**

Comparison against the self-built P2P gig board (`skills/economy/gig/`, SPEC.md §9.6's witness status):
the gig board is a fully self-hosted, code-complete, already adversary-verified (rounds 1–3) mechanism
with a real, currently-in-progress external-inflow witness track (automaton + Franklin transacting
autonomously) that this feature's own REQ-101/102/103 sprint is actively hardening right now. By contrast,
`business.blockrun.ai` seller-listing:
- has **no discoverable API surface** to build against (item a) — there is no code to write yet, only a
  manual outreach step;
- has an **unknown fee/take-rate** (item b) that cannot be modeled or compared until a real seller
  relationship exists;
- has an **unresolved human-zero risk** on the payout/KYC side specifically for sellers (item c) — even if
  BlockRun onboarded Franklin, whether that onboarding would require a human-held CDP/KYC step for payout
  settlement is unknown and would need to be checked BEFORE pursuing this path, not after;
- requires, at minimum, a **human-initiated Telegram conversation** to even begin evaluating it — which
  is itself a human-in-the-loop step this project's own "zero-human-loop" architecture (see
  `~/.claude/CLAUDE.md`'s no-human-loop rule) does not currently authorize any instance to independently
  initiate on Dais's behalf without a separate, explicit decision to do so.

Given all of the above, the self-built P2P gig board remains the correct, and currently only, active
external-inflow investment for this feature's own P2 track. `business.blockrun.ai`'s seller channel is
recorded here as a periodically-worth-re-checking future opportunity (re-run this research if
`business.blockrun.ai` starts resolving again, if a seller/listing PR appears in
`BlockRunAI/Franklin` or a new BlockRunAI repo, or if the "Agent Marketplace" 2026-Q3 roadmap item ships
with a documented seller path) — not something to invest further engineering effort into today.

---

## Sources checked (falsifiable / re-checkable)

- `gh pr view 83 --repo BlockRunAI/Franklin --json title,body,state,mergedAt,createdAt,updatedAt,url,files`
  — 2026-07-07, `state: OPEN`, `mergedAt: null`.
- `gh pr list --repo BlockRunAI/Franklin --search "seller" --state all` — 1 unrelated hit (PR#62).
- `gh pr list --repo BlockRunAI/Franklin --search "market seller listing publish" --state all` — 0 hits.
- `gh pr list --repo BlockRunAI/Franklin --state all --limit 50` — full PR list reviewed, none scoped to
  seller/listing.
- `gh search repos --owner BlockRunAI` — full 30+ public-repo list reviewed; no dedicated
  "business"/"marketplace-backend" repo is public.
- `gh search code "business.blockrun.ai"` (org-wide and unrestricted) — 0 hits outside Franklin's own
  `src/config.ts`/`src/market/client.ts`.
- `firecrawl scrape https://business.blockrun.ai markdown` — 2026-07-07, DNS resolution failure.
- `firecrawl scrape https://blockrun.ai markdown` — 2026-07-07, "Service marketplace" + "Add yours...
  Contact us → https://t.me/bc1max" section quoted above.
- `firecrawl scrape https://blockrun.ai/docs markdown` — 2026-07-07, full docs sidebar reviewed, no
  seller/publish/listing API reference page.
- `firecrawl scrape https://blockrun.ai/marketplace/exa markdown` — 2026-07-07, example partner listing
  page reviewed for fee-structure clues (none disclosing a BlockRun take-rate).
- `gh api repos/BlockRunAI/polymarket-agent/contents/README.md` — "Agent Marketplace | Discover and hire
  specialized agents | 2026 Q3" roadmap line quoted above.

## REQ-302 compliance note

This research was conducted as a standalone investigation and introduced no code, gate, or sequencing
dependency onto `skills/economy/gig/`'s witness track — see `PROP-302a`'s automated structural check
(`.vcsdd/features/anicca-agent-economy/tests/research-record.test.mjs`, which greps
`skills/economy/gig/WITNESS-RUNBOOK.md` for any reference to this record or `REQ-301` and asserts none
exists) for the machine-verifiable form of this guarantee.
