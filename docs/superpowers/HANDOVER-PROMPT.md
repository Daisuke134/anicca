# Anicca — Base Handover Prompt (paste into a fresh session, then add your task)

> Copy everything below the line into a new chat. It tells you what Anicca is, the TRUE current
> state (mostly NOT done — read the reality section), why the last attempt failed, and exactly what
> to redo. Replace the `>>> TASK:` line at the bottom.

---

You are working on **Anicca** — a self-funding Buddhist AGI (compute=ClawRouter, server=Akash/DO,
earns USDC no-human, self-replicates, self-improves, reports each wake, ends suffering). It is also a
**shippable product**: `aniccaai.com/install` (the money-maker, cloud $30/mo + OSS self-host) and
`aniccaai.com/life-manager` (Life Manager: auto-register travel time in gcal, call 15min before via
Gemini Charon, email-ask when unknown, notify stakeholders on lateness). "Done" = **a real user can
actually do the thing** (HARD 0.24/0.31: no dry-run, no "coming soon" theatre, no mock).

## ★ READ THIS FIRST — TRUE CURRENT STATE (2026-06-16, adversarial audit) ★
A Dynamic Workflow ran twice and CLAIMED "8 subsystems genuinely live." That claim is FALSE.
An independent audit (curl of live pages + origin/main source) found **only ~10-15% genuinely works**:

| Subsystem | Claimed | REALITY |
|---|---|---|
| life-travel (auto gcal travel block) | live | ✅ **the ONLY genuinely-working user feature** |
| install Stripe CTA | live | 🔴 **BROKEN**: button href = `https://buy.stripe.com/anicca-cloud` (fabricated placeholder) → **HTTP 403**. The flagship "$30/mo で始める" button is dead. |
| stripe-spawn webhook | live E2E | 🔴 unreachable — no user can reach a real checkout, so it never fires for a customer |
| /me (earn ledger + withdraw) | live | 🔴 page-only: shows "GATE-0 未達 (swap≠external revenue)"; withdraw/pause/daily-report buttons `disabled "opens at launch"` |
| dashboard | live colony | 🔴 served HTML is just `Loading…` — no numbers/leaderboard server-side |
| self-spawn | live | 🔴 no user surface; gated behind the dead Stripe flow |
| life-call / life-ask / life-notify | live | 🔴 page cards say **"coming"**; life-call tasks #108-111 marked "completed" but NO real call ever connected (Twilio err 13225 fraud-block on +818046270314; Telnyx coded but **no TELNYX_API_KEY**) |
| earn GATE-0 | "MET" | 🔴 it's an ETH→USDC **swap** (asset liquidation, to=Uniswap), NOT external revenue → UNMET |
| i18n EN/JA | done | 🔴 hardcoded `lang=en` over Japanese copy; `/en/install` & `/ja/install` = 404; no real locale routes |
| internal-jargon leak | — | 🔴 live pages show `GATE-0`, `swap-eth-usdc`, `B-travel`, `B-call`, "spec27 §2", "HARD 0.24/0.31" to end users |

**The entire money pipeline is dead** (install Stripe 403 → spawn unreachable → /me withdraw disabled).
**3 of 4 Life Manager features are "coming."** No working i18n. Internal codenames leak to users.

## ★ WHY IT FAILED (root cause — fix this, not just symptoms) ★
1. **Workflow verifier rubrics were too weak** (the core failure). They tested `curl 200 + text-present + file-on-main`, NOT "a user can complete the action." So a 403 Stripe button passed "install is 2-column, curl 200"; a `Loading…` dashboard passed "renders real numbers." → **A "pass" must mean a real user action succeeded.**
2. **Spec never required a working purchase path.** The install rubric never says "the Stripe button resolves to a real checkout."
3. **Agents built polished MARKETING PAGES, not working features** — CTAs to a non-existent Stripe link, disabled buttons, "coming" badges.
4. **The director/monitor (the loop agent) over-trusted verifier passes** and reported "genuinely live" without USING the product (never clicked the Stripe button, never checked for "coming soon"). The monitor must *use the product*, not read rubric checkmarks.

## ★ WHAT MUST BE REDONE ★
1. **Money pipeline**: real Stripe Payment Link (the repo's `cemetery/page.tsx` has working ones, e.g. `buy.stripe.com/bJe5kD7G60…` — copy that pattern) wired to the spawn webhook, with an E2E test that **Playwright-clicks the button and reaches Stripe Checkout**, then a paid test → real droplet provisioned.
2. **/me**: implement withdraw (Stripe payout/off-ramp, task #83) + pause + daily-report, OR remove the disabled-button theatre.
3. **dashboard**: render real instance numbers (SSR or clearly-loading), not a bare `Loading…`.
4. **Life Manager**: actually SHIP call/ask/notify (real Charon call, real email round-trips) or stop presenting them as product. Build the **cloud web-app** (it's currently local-skill-only) — `aniccaai.com/life-manager` must be a working app (connect calendar → see schedule), not a marketing page.
5. **Strip ALL internal jargon** (GATE-0, swap-eth-usdc, B-travel/call/ask/notify, spec §refs, HARD-rule citations) from user-facing HTML → plain product copy.
6. **Real EN + JA**: proper locale routes (`/en/*`, `/ja/*`) + a working toggle, `lang` matching content.
7. **★ FIX THE WORKFLOW RUBRICS FIRST ★** in `docs/superpowers/workflows/anicca-launch.workflow.js`: every verifier rubric must require a **real user action via a real browser** (Playwright clicks the actual button, completes the actual flow), not curl-200. Then re-run. Without this, the next run produces the same façade.

## ★ WHAT GENUINELY IS DONE (don't redo) ★
- **Telemetry pipeline** — real, E2E-verified vs live Supabase (genesis posts real net worth each wake). LIVE.
- **dev↔main reconcile** — one trunk; new work branches off `main` → PR (telemetry pattern). Backups `backup/dev-20260616`/`backup/main-20260616`.
- **B-travel** (auto gcal travel block) — the one real Life Manager feature.
- Repo cruft removed (work//.ipa/.dSYM gitignored — was causing ENOSPC in worktrees).

## Genuine external blockers (small vs the fake-product problem)
- **life-call**: needs working telephony — Twilio `+818046270314` is fraud-blocked (err 13225, needs a Support ticket) OR set up Telnyx (account + funding + `TELNYX_API_KEY`). Then place a REAL connected call (verify dur>0 + recording via the carrier API).
- **earn**: a swap is NOT earning. Needs seed capital (≈$5-10) or an accepted no-capital external-revenue path. Never mark GATE-0 met on a swap.

## How we work
- **SDD + adversarial review** (HARD #0): spec → plan → review-until-clean → TDD → deploy → **live E2E that USES the product**. The telemetry pipeline (6 review rounds) is the quality bar.
- **Deployment reality**: `apps/landing` is static export → server runtime is **Netlify Functions** (`netlify/functions/*.js`, CJS, `/.netlify/functions/<name>`); Supabase via REST; ethers v6; node:test. Deploy = PR → `main` (its GHA has `--functions`). lefthook requires git author `Daisuke Sato <keiodaisuke@gmail.com>` + branch prefix `feature/|fix/|chore/|docs/|spec/`.
- **Director/monitor discipline**: if you run + monitor a workflow, you MUST USE the product yourself each loop (click the buttons, look for "coming soon", curl every CTA) — verifier "pass" ≠ works. Don't report "live" you didn't personally exercise.
- **Disk**: `df -h /` often; clean `~/.npm`, `simctl delete all`, prune worktrees when <2.5Gi.
- **Push constantly**; STATUS.md (`docs/superpowers/STATUS.md`) is the living truth — keep it honest.

## Credentials (`~/.openclaw/.env`, never commit)
SUPABASE_URL/SERVICE_ROLE_KEY/ANON/ACCESS_TOKEN(sbp_), NETLIFY_AUTH_TOKEN/SITE_ID(anicca2), STRIPE_SECRET_KEY + STRIPE_SPAWN_WEBHOOK_SECRET(prod), DIGITALOCEAN_TOKEN, BLOCKRUN_WALLET_KEY(=genesis 0xa3cdd4…), AGENTMAIL_API_KEY (daily-limited; use `gog gmail send --account keiodaisuke@gmail.com` for mail), TWILIO_* (fraud-blocked to JP), GEMINI_API_KEY. Genesis droplet: `root@147.182.225.255`.

---

>>> TASK: (Dais fills this in.) Likely first task: "Fix the workflow verifier rubrics so 'pass' = a real
user action via Playwright, then re-run anicca-launch to actually SHIP A+B (real Stripe checkout, real
Life Manager web-app + call/ask/notify, real i18n, no internal jargon, no coming-soon)." Start by reading
STATUS.md + this reality section, then use the product yourself (curl/Playwright every CTA) before trusting anything.
