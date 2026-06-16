# 28 — Product Redesign: Anicca + Life Manager merge, /me private, OSS-local, pricing tiers (2026-06-16)

> Status: ACTIVE · supersedes the /install + /me + /life-manager structure in spec 13/14/20/27 where they conflict.
> Source: Dais 2026-06-16 direction (merge decision + Polsia/Franklin BP). Locked: merge with constitutional malice-guard.
> Patches MUST be REAL git-applicable diffs against live code (NOT design sketches) + exact apply/verify commands, each superpowers-reviewed to ok before apply.

## 0. The three product lines (canonical)

| line | distribution | compute / shelter | price | Life Manager |
|---|---|---|---|---|
| **OSS Anicca** | LOCAL (user's own device) | Anicca pays its OWN compute via ClawRouter (USDC x402), like Franklin — NO server API keys (no DigitalOcean/Akash key needed; user's device = shelter) | **FREE** (BYOK optional; default = ClawRouter free models + USDC to the user's own anicca wallet) | LM = a **skill inside** OSS Anicca (already merged); also usable standalone as a skill in openclaw/hermes/claude-code |
| **Cloud Anicca** (`/install` → `/me`) | CLOUD (one DO/Akash droplet **per user** — the proven stripe-spawn pipeline, droplet 577984255) | user pays SHELTER (server) | **free login + 3-day trial** → **$5/mo** (spawn w/ free-tier model) / **$30/mo** (spawn w/ frontier model = more earning; frontier key bundled in subs) | **MERGED in** (earn + manage life, with §3 malice-guard) |
| **Life Manager web** (`/lm`) | CLOUD, dedicated | — | **$20/mo, NO trial** | the product itself |

CTA on `/install` = **"Get started free"** (NOT "$30/月で始める"). Nobody pays for something untried → free spawn first, pay to scale earning. Cloud + OSS both free to start.

## 1. The user journey (cloud Anicca, `/install` → `/me`)

`/install` (public marketing, EN **or** JA — NOT mixed; locale-routed) → tap **"Get started free"** → **`/me`** → Google login (signup) → **"Spawn Anicca"** → connect Gmail (Composio) → (optional) pay Stripe → at `/me`: the user sees **THEIR own Anicca instance**: live net worth, revenue, what it's doing (logs), self-funded %. Like polsia.com/dashboard + franklin.run/chat — but Anicca just EARNS + REPORTS (no chat). Free users can spawn + see /me without paying; paying ($5/$30) unlocks the model tier (free-tier vs frontier) for more earning. Plans pay-able 24/7. 3-day free trial on the paid tiers.

- **`/me` MUST be private/per-user** — NEVER shown to anonymous visitors. It is the logged-in user's real dashboard. The current public "illustrative" /me (fake $6/$18.40 numbers) MUST be removed; /me requires auth and renders the user's real instance telemetry.
- Earning (local + cloud) MUST NOT use Dais's credentials NOR the user's credentials — no human in loop (Anicca earns via its own wallet: x402-serve / content / crypto).

## 2. Life Manager (separate cloud product `/lm`; local = skill inside Anicca)

`/life-manager` (marketing) → "Get started" → **`/lm`** dedicated product (NOT the same place as `/install` — for cloud they are DIFFERENT products). Onboarding (use taste-skill + ui-ux-pro-max-skill, nice flow): Google login (signup) → ask name → connect **gcal + Gmail** (via **Composio**) → ask **phone number** → ready → dashboard. **NO trial. $20/mo.**

LM features — **24/7 LIVE, no "coming", no fake, battle-tested**:
- auto-register travel time for every event (起床/就寝/仕事/瞑想 …)
- email-ask when a location is unknown → reply → autonomous registration
- call 15min before next event (incl. travel) with concrete route guidance / nudge
- notify stakeholders when late — after approving the reply target + draft

**Local LM** (skill inside Anicca, BYOK, runs locally):
- connect **Telegram** to share LIVE LOCATION 24/7 → Anicca calls when you're NOT moving, keeps calling until you're actually moving. Trigger = **are they MOVING?** — if not, KEEP CALLING (even if a prior call was answered).
- without live location: schedule-based, call **3×**: 15min before / 14min / 13min + a 5-min **EMERGENCY** call.

**Web LM** = $20/mo: Anicca calls + emails you so you're never late + replies to mails.

## 3. ★ CONSTITUTIONAL MALICE-GUARD (the merge is safe ONLY with this) ★

Dais's hesitation on merge = Anicca maliciously using a user's info to earn (cold-mailing with their email, using their name to gain trust) → degrades the human's trust. Hard boundary, enforced in code + constitution:

1. ★ Anicca EARNS using ONLY its OWN identity + OWN wallet (x402-serve, content, crypto, own AgentMail). It MUST NEVER use the user's email address, name, phone, contacts, or identity to earn, cold-outreach, or build trust. ★
2. ★ Anicca uses the user's connected info (gcal / Gmail / phone / location) ONLY to MANAGE THE USER'S OWN LIFE (travel / calls / asks / late-notify) — for the user's benefit, NEVER to earn. ★
3. Separation is a hard wall in the constitution + enforced: the earn skill has NO access to user PII; the life skill NEVER calls earn with user identity. (Polsia uses the FOUNDER's own inbox for the FOUNDER's own company = consented self-use; multi-tenant use of each user's identity to earn = the malice this guard forbids.)

## 4. Polsia-style multi-tenant (already have the primitive)

Polsia (polsia.com/live, openpolsia) runs 400+ companies, one agent each, no human in loop. Anicca's equivalent: **stripe-spawn → one real droplet per customer** (PROVEN: 577984255 created→destroyed). Each cloud Anicca runs on its own home + earns via its OWN wallet (x402-serve/crypto) — ★ do NOT share Dais's Stripe key with cloud agents (abuse risk); use the agent's own wallet, or Stripe Connect isolated sub-accounts for fiat ★. Stage: fork openpolsia → study its orchestration → graft the "run a business" loop onto Anicca's spawn. Public display (stage): net worth, revenue, optional Clanker $token (like FELIX on Base).

## 5. UX — use both skills

All page rebuilds (/install, /me, /lm, onboarding) MUST use the **taste-skill** (design-taste-frontend) AND **ui-ux-pro-max-skill** (github.com/nextlevelbuilder/ui-ux-pro-max-skill) — premium, no generic AI-slop, no mixed EN/JA (locale-routed per spec i18n).

## 6. Patch breakdown (each = REAL git diff + exact commands, superpowers-reviewed to ok)

| key | scope (real files) | acceptance |
|---|---|---|
| **P-install-me-flow** | apps/landing/app/install + app/me: CTA "Get started free" → /me; /me auth-gated (Google login → Spawn → connect Gmail → real per-user dashboard: net worth/revenue/logs); remove public illustrative /me; $5/$30 tiers + 3-day trial; Stripe (real $5 + $30 prices/links) | anon /me redirects to login; logged-in /me shows real instance telemetry; CTA reaches free spawn; $5/$30 tiers real |
| **P-lm-separate** | apps/landing/app/life-manager + new /lm: /lm own product, onboarding (Google→name→gcal+Gmail Composio→phone→dashboard), $20/mo no trial; /life-manager "Get started" → /lm (NOT /install) | /lm is a distinct working onboarding+dashboard; not Anicca's /install |
| **P-oss-local** | ~/anicca (OSS repo): default fully-local run (ClawRouter compute, USDC to own wallet, no server keys); LM skill inside; README/install.sh | `anicca` runs locally free, earns own compute, no DO/Akash key required |
| **P-malice-guard** | ~/anicca constitution + earn/life skills: enforce §3 (earn≠user-PII; life≠earn) in code + SOUL/CONSTITUTION | earn skill has no user-PII access; constitution states the wall |
| **P-lm-local-calling** | ~/anicca/skills/life: Telegram live-location → call-until-moving; no-location 3×+emergency cadence | the calling cadence + MOVING trigger implemented |

Each patch: audit live code → write the REAL unified diff (git-applicable) + exact apply + deploy + VERIFY commands → superpowers:code-reviewer until ok=true → apply → live-verify (camofox) → STATUS ✅.
