# Behavioral Spec — capafy-skills-landing

## Context

Instagram caption/comment URL はクリック導線にならない。`@useclaudeskills` の profile Website 1本から全 online Capafy listing へ到達できる静的 landing を用意する。listing source は既存 `select_listing.py::_fetch_agents()` と同じ seller endpoint `GET /agent/agents`。

## Requirements (EARS)

- REQ-L1: WHEN generator runs, THE SYSTEM SHALL call `CAPAFY_HTTP GET /agent/agents` and include only records whose `agentStatus` equals `online` and whose `agentId` exists.
- REQ-L2: WHEN online records exist, THE SYSTEM SHALL overwrite `site/index.html` with one dependency-free HTML document containing header, tagline, one card per online record, and footer count.
- REQ-L3: FOR EACH card, THE SYSTEM SHALL HTML-escape API text and render the exact UTM URL `https://capafy.ai/agent/{agentId}?utm_source=instagram_bio&utm_medium=bio_link&utm_campaign=capafy_marketing`.
- REQ-L4: THE SYSTEM SHALL render a mobile-first single-column list with readable type scale, two-line visible descriptions, keyboard focus, light/dark color schemes, and reduced-motion handling without external CSS, JavaScript, CDN, image, or font dependencies.
- REQ-L5: WHEN input records are unchanged, THE SYSTEM SHALL produce byte-identical HTML by deterministic name ordering and content generation.
- REQ-L6: WHEN endpoint output has no online records or invalid JSON, THE SYSTEM SHALL exit non-zero and SHALL NOT claim success.
- REQ-L7: WHEN deployed to Netlify production, THE SYSTEM SHALL expose a public URL returning HTTP 200 and at least one `capafy.ai/agent` link.
- REQ-L8: WHEN the daily IG script runs, THE SYSTEM SHALL regenerate and production-redeploy the landing every pass without changing existing cadence, posting, metrics, ledger, or safety gates.
- REQ-L9: WHEN `commercial_ok=yes` and mode is live, STEP5 BIO SHALL target the landing public URL; otherwise it SHALL leave bio untouched.
- REQ-L10: THE SYSTEM SHALL NOT add a GitHub Actions workflow.

## Purity Boundary

- Pure: record filtering, sorting, HTML escaping, card/page rendering.
- Impure: Capafy subprocess call, filesystem overwrite, Netlify deploy, Instagram bio update performed by the existing loop agent.

## Out of Scope

- Capafy listing content edits, sales/rating ranking, search/filter JavaScript, analytics scripts, new social accounts, GitHub Actions.
