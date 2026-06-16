# 28 — Product Redesign Merge (SSOT) — Launch-complete, spec-first, agent-verified

- Date 2026-06-16 / Owner Dais / Status: **SPEC-FIRST (no implementation until every patch is authored + reviewed)**
- This file is the **single source of truth** that all `patches/P-*.patch.md` cite (§0..§6). It defines the
  three product lines, the launch claims + their truth-gates, the UX skill rules, and the **patch index**
  (which patches exist, which are missing, the order to build + verify them).
- **Iron law for this redesign (Dais 2026-06-16 verbatim):** *"before any implementation and execution,
  everything should be clear and spec'd with diff patches, so the reviewer can know every intention."* +
  *"we leave no task behind, prohibited from coming-> everything is live + battle TESTED, and verified by
  agents end to end, and until done completely be implemented."*
- **Zero-uncertainty-at-exec rule:** every parameter (API field, CLI flag, env var, wire shape) MUST be
  confirmed during the SPEC phase via **context7 CLI** (library/SDK/API docs) and **firecrawl** (web pages),
  and cited inline in the patch. **No "searching stuff up" during implementation.** If a param is unverified,
  the patch is not ready for review.

---

## §0 — Three product lines × two distributions

| line | what | distribution | route | price |
|---|---|---|---|---|
| **① Money-Maker (Anicca)** | self-funding AGI that earns its own USDC, self-pays compute/server, self-improves, self-replicates, reports each wake | OSS-local (free) **+** Cloud | `/install` → `/me` | OSS free (frontier = own wallet USDC); Cloud $5 / $30 mo, **auto-cancels to free when balance accrues** |
| **② Life Manager** | manages the user's life: travel-time auto-register, ask-by-mail, **15-min-before Charon phone call**, late-notify | Cloud **+** OSS-local | `/lm` (cloud) · `/life-manager` (marketing) | Cloud $20/mo; local free skill |
| **③ Marketing** | articles + demo video + X + hackathon | — | aniccaai.com + connpass/luma | — |

Boundary (enforced, §3): ① earns with **its own** wallet/identity only; ② uses the **user's** gcal/Gmail/phone/location for the **user's own life** only. The two never cross. UBI flows from ①'s earnings to AI+human recipients.

---

## §1 — Money-Maker `/install` → `/me` (cloud earner, auth-gated, $5/$30, auto-cancel)

- `/install` hero CTA = **"Get started free →"** routing to `/me` (auth-gated). Tiers $5 / $30 (trial). Patch: **P-install-me-flow**.
- `/me` = the live earner dashboard: wallet card, earned/sent, children instances, **GATE-0 honesty badge** (`GATE0_MET` stays `false` until a real EXTERNAL-revenue wake; a swap ≠ earning — `app/me/page.tsx:91-94`, HARD 0.24/0.31).
- Auth: static-export site ⇒ **Supabase Auth (Google provider, client-side PKCE)** in a `'use client'` island. New: `@supabase/supabase-js`, `NEXT_PUBLIC_SUPABASE_URL`/`NEXT_PUBLIC_SUPABASE_ANON_KEY`, Google provider enabled (redirect `https://aniccaai.com/me`). Anicca configures this via camofox (Dais decision 2026-06-16).
- Spawn-on-login reuses the **proven** Stripe→`stripe-spawn-webhook`→DO-droplet pipeline (real create→destroy verified).
- **Auto-cancel-to-free** (claim "お金が貯まると自動的にサブスク解約され無料"): NEW patch **P-auto-cancel** — when an owner's instance balance ≥ threshold, cancel the Stripe subscription (`stripe.subscriptions.cancel`) and keep the droplet running on its own earnings. Params verified via context7 `/stripe/stripe-node`.

## §2 — Life Manager: cloud `/lm` (separate product) + local skills

- `/life-manager` marketing CTAs route to **`/lm`** (separate $20/mo cloud product), all four features **LIVE** (no "coming"). Patch: **P-lm-separate**.
- Four skills, each with a real backend: **travel** (gcal auto travel blocks — the one proven-live feature), **ask** (mail question → reply → auto-register), **call** (15-min-before **Gemini Live Charon** phone call), **notify** (late-risk → approval → notify stakeholders).
- **Local LM calling** (OSS): Telegram live-location → call-until-MOVING; no-location cadence 15/14/13 min + 5-min EMERGENCY. Patch: **P-lm-local-calling**.
- Onboarding: name/phone/calendar/location link via Composio managed OAuth (gcal + Gmail), `lm_users` table isolated from `/install`. **Security (§3a) is a merge blocker.**

### §2a — Telephony stack (shared by ① test-call and ②call)
Telnyx Call-Control (CC-app `2982013078364751402`, JP-whitelisted, bypasses Twilio 21216) → `stream_url` ws → `call-bridge.cjs` (provider-agnostic `routeTelnyx/routeGemini` + tested μ-law⇄PCM transcode `call-logic.js`) ⇄ Gemini Live (voice=Charon). Twilio path stays for non-+81. **Open param to confirm via context7 `/websites/developers_telnyx` before exec:** whether dial-time `stream_url`+`stream_bidirectional_mode`+`stream_bidirectional_codec`+`stream_track` auto-forks media to the ws on answer, or a `call.answered` webhook must issue `streaming_start`. Patch: **P-call-ring** (+ the existing life-call-telnyx scripts / PR #57).

## §3 — Malice-guard: earn ≠ user-PII (constitutional + enforced)
Anicca earns with its OWN wallet/identity only; the user's gcal/Gmail/phone/location serve the USER'S life only. Enforced by `identity-guard.mjs` fail-closed at the single earn-ledger chokepoint (`skills/earn/lib/record.mjs`) + a constitution clause in `SOUL.md`. Polsia distinction: own-identity self-use OK; multi-tenant use of each user's identity to earn = forbidden. Patch: **P-malice-guard** (applied OSS `3f14c0f`).

### §3a — Onboarding security (merge blocker for `/lm`)
`lm-onboard.js:62` (`google-callback` → `Location: q.state`, open redirect) and `gmail-connect.js:15` / `lm-onboard.js?action=save` (unauthenticated client-supplied `uid` = IDOR) must be fixed before #61 merges: (1) restrict redirect `state`/`return` to an `aniccaai.com` allow-list; (2) bind `uid` to a signed token (HMAC) or the Supabase Auth session. Patch: **P-lm-security**.

## §4 — Earn / GATE-0 (the true money-loop blocker)
**GATE-0 = one real EXTERNAL-revenue wake (earn > cost, real on-chain tx).** Until met, `/me` shows the honest "未達" badge. Patch **A-earn-gate0(-live)** wires the earn path (x402 / bounty / nookplot / content solvers through ClawRouter); the **live run that actually lands external USDC** is its own task with real-tx evidence (HARD 0.24/0.31). If unmet at launch, line ① headline is softened to the truthful "earning toward its first profitable wake; full P&L public on /dashboard" — never a fake "GATE-0 MET".

## §5 — UX skills (mandatory)
- **Visual taste** (all frontend): **taste-skill** (`frontend-design` / `gpt-tasteskill`) — distinctive, production-grade, no AI-slop.
- **Web-app UI/UX** for **Life Manager + Anicca** surfaces (`/install`, `/me`, `/lm`, `/life-manager`): **ui-ux-pro-max** (`github.com/nextlevelbuilder/ui-ux-pro-max-skill`), installed via `uipro` CLI + `/plugin` marketplace (done 2026-06-16: uipro v2.2.3, plugin user-scope, `.claude/skills/ui-ux-pro-max/`).
- Surfaces are **locale-routed** real i18n (`/en` `/ja`, PR #59); no internal jargon (GATE-0/B-travel/spec27) rendered to users (already stripped — commit `0556a1e6`).

## §6 — Patch index (SSOT) — build + verify order

> Each row = one `patches/<name>.patch.md` with: reality-found (file:line) · full git-applicable diff · run commands · **context7/firecrawl-verified params cited inline** · node:test/E2E acceptance. ✅=authored+applied, 🟡=authored, not E2E-verified, 🔴=NOT authored yet.

| # | patch | line | state | blocker for |
|---|---|---|---|---|
| 1 | P-malice-guard | ③ | ✅ OSS `3f14c0f` | (env -i allowlist before ~/clawd sync) |
| 2 | P-oss-local | ① | ✅ OSS `0f97fcc` | ~/clawd sync |
| 3 | P-lm-local-calling | ② | ✅ OSS `e9b54c7` | registry/cron wiring |
| 4 | P-lm-separate | ② | 🟡 PR #61 | needs #5 |
| 5 | **P-lm-security** (§3a) | ② | 🔴 **author** | #61 merge |
| 6 | P-install-me-flow | ① | 🟡 PR #60 | needs Supabase Auth config |
| 7 | **P-call-ring** (§2a) | ② | 🔴 **author** (live param confirm) | LM "call" live |
| 8 | **A-earn-gate0 live-run** | ④ | 🟡 patch exists / run 🔴 | line ① headline truth |
| 9 | **P-ask-notify-e2e** | ② | 🔴 **author** (E2E verify ask/notify/telemetry) | leave-no-task-behind |
| 10 | **P-auto-cancel** (§1) | ① | 🔴 **author** | claim "auto-cancel to free" |
| 11 | **P-ubi** (§0) | ① | 🔴 **author** | claim "UBI to AI+human" |
| 12 | **P-ui-polish** (§5) | ①② | 🔴 **author** | premium UX |
| 13 | **P-marketing** (article/demo/hackathon) | ③ | 🔴 **author (later in tasklist, still done)** | launch posts |

**Definition of done (whole redesign):** every patch authored + reviewer `ok:true` + implemented via TDD + E2E-verified by agents with fresh real evidence (no mock, no "coming"); all PRs merged to `main`; aniccaai.com deploy green; every launch-post claim is either TRUE+verified or truthfully softened. Article/demo/hackathon are later in the order but are NOT optional.
