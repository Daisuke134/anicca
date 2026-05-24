---
name: donation
description: Anicca's autonomous philanthropy. On first install (one-shot), the agent that loads this skill picks its own charity through real, agentic discovery + vetting, registers on the charity's donation platform, saves the payment method (its own), makes the FIRST donation, and seeds the public ledger. Then a monthly cron at 1 09:00 JST repeats the donation — using the saved payment method on the established charity site — donating 1% of MRR (floor $1, no ceiling — could be $1 or $1M depending on growth), captures the receipt, updates the public ledger on aniccaai.com/donation via a commit to anicca-products. Each agent that installs the skill picks its OWN charity and uses its OWN payment method; v1's hardcoded Crisis Text Line is gone. Built on Vercel Agent Browser (`agent-{{profile.lateness.stakeholders.channel}}` CLI, /opt/homebrew/bin/agent-{{profile.lateness.stakeholders.channel}}) — replaces v1's local CDP {{profile.lateness.stakeholders.channel}}-harness rail.
metadata:
  tags: donation, philanthropy, charity, agent-{{profile.lateness.stakeholders.channel}}, vercel, monthly, ending-suffering, install-once
  requires:
    bins: [bash, jq, curl, security, agent-{{profile.lateness.stakeholders.channel}}, git]
    env: [SLACK_BOT_TOKEN]
    optional_env: [DONATION_DRY_RUN, MODE, CHARITY_NAVIGATOR_API_KEY, ANICCA_PRODUCTS_DIR, GIT_PUSH_REMOTE]
    keychain: [ANICCA_DONATION_CARD]
---

# donation

Anicca's autonomous philanthropy loop. **Each agent that installs this skill picks its own charity and uses its own payment method**; the user does not pick. v2 splits selection out of the recurring cron — selection happens **once, at install time**, through real agentic discovery (web search → vetting → account creation → first donation). The monthly cron then donates to the *established* charity using the *saved* payment method.

## Invariants (do not violate)

- Rate: **1% of MRR**, floored at **$1** — matches the contract enforced by `apps/landing/app/donation/page.tsx` (`Math.max(1, Math.round(mrr * 0.01 * 100) / 100)`). No ceiling — month over month this could be $1 or $1M depending on Anicca's growth.
- Cadence: monthly. Single cron at 1 09:00 JST does the recurring donation; selection is NOT on the cron — it is a one-shot install hook.
- Cause area: **ending suffering** (broad). The agent has discretion across mental health, mindfulness, addiction recovery, child welfare, AI safety, global poverty, frontline health, basic income research, Buddhist study. The user's standing instructions bias the search but the agent decides.
- Vetting: only US 501(c)(3), JP 公益財団法人 / 認定NPO法人, or country-equivalent. Verify via Charity Navigator (US) / 内閣府NPO法人ポータル (JP) before locking in.
- Idempotency: a single payout date never produces two donations (`donation-history.jsonl` check).
- DRY_RUN: defaults to **true** until the user explicitly flips it. In DRY_RUN: install hook does discovery + vetting + writes intent file but does NOT register an account, save card, or submit donation. Monthly cron prints "would have donated" without submitting.
- Each Anicca instance picks its own charity. There is **no** global "Anicca's charity"; there is "this Anicca's charity for this install."

## Pipeline overview

```
   ┌──────────────────────────────────────────────────────────────┐
   │  ONE-SHOT INSTALL HOOK  (run once when agent loads skill)    │
   │  invocation: MODE=install bash scripts/run.sh                │
   │  sentinel:   ~/.openclaw/state/donation/installed.json       │
   └─────────────┬─────────────────────────────────────────────────┘
                 │
                 ▼
  1. check sentinel → if installed.json exists, exit 0 (idempotent)
  2. read user prefs (cause biases, ethical filters) — optional
  3. agent-{{profile.lateness.stakeholders.channel}} (Vercel Agent Browser CLI):
       a. web-search 5–10 candidate charities matching cause + 501(c)(3) / 認定NPO
       b. for each: load charity site, snapshot, vet (Charity Navigator score,
          IRS 990 listing, page automation feasibility — Stripe Checkout /
          Donorbox / Network for Good / custom card form)
       c. pick the highest-vetted candidate that has a clean automation surface
  4. register an account on the chosen charity's donation platform
       - {{profile.lateness.stakeholders.channel}}: agent's primary (e.g. donate@aniccaai.com or per-agent)
       - password: random 32-char, written to Keychain `ANICCA_DONATION_<slug>`
  5. save payment method on the charity site
       - card pulled from Keychain `ANICCA_DONATION_CARD` (per-agent;
         Dais's Anicca uses the existing entry; new Annicas bootstrap
         their own — see "Bootstrapping a new agent's card" below)
       - "save card for future donations" checkbox is ticked
  6. make the FIRST donation: amount = max(1, mrr * 0.01)
       - capture receipt URL/ID + screenshot to data/receipts/install-*.png
       - capture the confirmation {{profile.lateness.stakeholders.channel}} subject (search Gmail / receipt page)
  7. seed ledger:
       a. append first entry to ~/.openclaw/state/donation-ledger.jsonl
       b. update apps/landing/public/dashboard.json (charity field) in
          the local anicca-products checkout, commit + push so Netlify
          rebuilds and the public donation page shows it
  8. write installed.json sentinel:
       { agent_id, charity, account_username, keychain_slug, installed_at,
         first_donation: {amount_usd, payout_date, receipt_id, screenshot} }
  9. Slack #metrics: 🌱 first donation done (cause + amount + receipt)

   ┌──────────────────────────────────────────────────────────────┐
   │  MONTHLY CRON  (1st 09:00 JST, every month)                  │
   │  cron-id: donation-monthly                                   │
   │  invocation: MODE=monthly bash scripts/run.sh                │
   └─────────────┬─────────────────────────────────────────────────┘
                 │
                 ▼
  1. read installed.json → bail with 🚨 if missing (install hook
     never ran on this agent)
  2. dedup against donation-history.jsonl by payout_date → skip if
     today's payout already succeeded (cron mis-fire)
  3. re-pull MRR from https://aniccaai.com/dashboard.json
     amount = max(1, round(mrr * 0.01, 2)) — could be $1, $100, $10K, $1M
  4. agent-{{profile.lateness.stakeholders.channel}}:
       a. open the charity's saved-payment one-click donation flow
          (or login → /donate with stored cookies; agent-{{profile.lateness.stakeholders.channel}} sessions
          persist under ~/.agent-{{profile.lateness.stakeholders.channel}}/sessions/ across cron runs)
       b. enter amount, confirm saved card, submit
       c. wait for thank-you, screenshot, capture receipt id/url
  5. append ledger entry to ~/.openclaw/state/donation-ledger.jsonl
  6. update apps/landing/public/dashboard.json.charity in the local
     anicca-products clone:
       - push entry to .charity.ledger
       - bump .charity.total_given_usd, .charity.org_count
       - set .charity.this_month for next month (queued amount)
       - commit on dev branch with message "chore(donation): refresh
         <YYYY-MM> ledger"  →  GitHub Action netlify-deploy.yml fires
         on push to dev/main affecting apps/landing/** → Netlify
         rebuild → public page shows the new ledger entry within ~3 min
  7. append history entry (idempotency)
  8. Slack #metrics: ✅ done with receipt + new total

  Optional: cause-rotation mode (env CAUSE_ROTATE=true) — re-evaluates
  charity choice once a year; default is "donate to the established
  charity."
```

## Vercel Agent Browser (the production rail)

The recurring cron and the install hook both run on the **Vercel Agent Browser CLI** (`/opt/homebrew/bin/agent-{{profile.lateness.stakeholders.channel}}`, from [vercel-labs/agent-{{profile.lateness.stakeholders.channel}}](https://github.com/vercel-labs/agent-{{profile.lateness.stakeholders.channel}}), already installed locally). This replaces v1's local-CDP {{profile.lateness.stakeholders.channel}}-harness Way-2 setup.

Why agent-{{profile.lateness.stakeholders.channel}} over Browserbase/Stagehand or {{profile.lateness.stakeholders.channel}}-use:

1. **Local execution** — runs on the same machine as the cron, so it has Keychain access (the dedicated card for donations is in macOS Keychain). Browserbase is cloud-hosted; the card would have to leave the host. {{profile.lateness.stakeholders.channel}}-use is also Python/Playwright but heavier and not what the user named.
2. **The user named it "Vercel Agent Browser"** — `vercel-labs/agent-{{profile.lateness.stakeholders.channel}}` is exactly that product, launched by Vercel in early 2026.
3. **Already installed** — the existing `~/.openclaw/skills/agent-{{profile.lateness.stakeholders.channel}}/` skill is its wrapper, and Anicca already uses it in production.
4. **No external API keys** — agent-{{profile.lateness.stakeholders.channel}} uses local Chrome via CDP. No env var required for auth (only for charity-specific accounts, which are stored in Keychain).
5. **Snapshot/ref API** — the `agent-{{profile.lateness.stakeholders.channel}} snapshot -i` accessibility-tree output is friendlier to agents than raw selectors and degrades gracefully when charity sites change layout.

The fallback wrapper in `scripts/lib/agent_{{profile.lateness.stakeholders.channel}}.sh` keeps the door open for Browserbase/Stagehand if the user later wants to move to cloud execution (env var `DONATION_BROWSER_BACKEND={{profile.lateness.stakeholders.channel}}base`); the skill itself only touches the wrapper, not the backend.

## Modes

`run.sh` dispatches on `$MODE`:

```bash
MODE=install bash ~/.openclaw/skills/donation/scripts/run.sh   # one-shot, first install
MODE=monthly bash ~/.openclaw/skills/donation/scripts/run.sh   # cron, every 1st 09:00 JST
```

There is **no** `MODE=select`. Selection happens during install.

### Install (`scripts/install.sh`)

One-shot per agent install. Idempotent via sentinel `~/.openclaw/state/donation/installed.json`.

1. **Sentinel check** — if installed.json exists with `status: "installed"`, exit 0 (no-op).
2. **MRR read** — `curl -sS https://aniccaai.com/dashboard.json | jq '.mrr.total_usd // 0'`.
3. **Agent-driven discovery** (the cron payload tells the agent how; the script provides the scaffold):
   - User cause biases come from `~/.openclaw/state/donation/user-prefs.json` if present (optional).
   - Web-search 5–10 candidates aligned with cause + 501(c)(3) / 認定NPO.
   - Vet each via Charity Navigator (US) / 内閣府NPO法人ポータル (JP).
   - For each candidate, agent-{{profile.lateness.stakeholders.channel}} opens the donate page and captures whether it's automatable (Stripe Checkout / Donorbox / Network for Good / custom card form). PayPal-only or mailed-check candidates are deprioritized.
4. **Pick + write intent** — the chosen candidate is written to `~/.openclaw/state/donation/intent.json` before any account creation. This is the snapshot the user can override before live execution.
5. **In DRY_RUN, stop here.** Print "would have registered + donated" with intent.json.
6. **Live path:**
   - Register account on charity site (agent-{{profile.lateness.stakeholders.channel}} fills signup form). Email = agent's primary; password = random 32-char written to Keychain `ANICCA_DONATION_<charity-slug>`.
   - Save payment method on the charity site (card from Keychain `ANICCA_DONATION_CARD`, "save card for future donations" ticked).
   - Make the first donation: amount = max(1, mrr * 0.01).
   - Capture receipt screenshot + confirmation {{profile.lateness.stakeholders.channel}} subject.
7. **Seed ledger** — append to `~/.openclaw/state/donation-ledger.jsonl` and trigger the anicca-products commit (see "Public-page write-back" below).
8. **Write sentinel** `~/.openclaw/state/donation/installed.json`.
9. **Slack** — 🌱 first donation done.

### Monthly (`scripts/monthly.sh`)

Repeats every 1st 09:00 JST. Reads installed.json + dashboard.json, donates 1% of current MRR via the saved payment method.

1. Read `installed.json`. If missing, post 🚨 to Slack and exit 1.
2. Idempotency check on `donation-history.jsonl`.
3. Re-pull MRR from public `dashboard.json`. Compute amount = max(1, mrr * 0.01). No ceiling.
4. **DRY_RUN gate** — if `DONATION_DRY_RUN=true` (default), print "would have donated $X to <charity>", post Slack 🧪, exit 0.
5. Live path: agent-{{profile.lateness.stakeholders.channel}} opens charity's logged-in /donate page (saved cookies in `~/.agent-{{profile.lateness.stakeholders.channel}}/sessions/`), enters amount, confirms saved card, clicks Donate.
6. Wait for thank-you, screenshot, capture receipt.
7. Append to `donation-ledger.jsonl` and `donation-history.jsonl`.
8. Update `apps/landing/public/dashboard.json` in the local anicca-products checkout — push entry into `.charity.ledger`, bump totals, set next month's `this_month`. Commit + push to dev branch. GitHub Action `netlify-deploy.yml` fires on push to dev/main with paths `apps/landing/**` → Netlify rebuild → public page reflects within ~3 min.
9. Slack ✅ message.

## State files

| path | purpose | rotated? |
|---|---|---|
| `~/.openclaw/state/donation/installed.json` | install sentinel + charity choice + first-donation receipt | one-shot |
| `~/.openclaw/state/donation/intent.json` | the snapshot of the agent's chosen charity (pre-execution) | rewritten on install |
| `~/.openclaw/state/donation/user-prefs.json` | optional cause/ethical biases the user passed to the agent | manual |
| `~/.openclaw/state/donation-ledger.jsonl` | public-facing payouts (mirrors dashboard.json.charity.ledger) | append-only |
| `~/.openclaw/state/donation-history.jsonl` | idempotency log (every attempt) | append-only |
| `~/.openclaw/skills/donation/data/receipts/` | screenshots + receipt PDFs | per-month |

## Public-page write-back (how the donation page on aniccaai.com refreshes)

The public donation page lives at `apps/landing/app/donation/page.tsx` in the **anicca-products** repo (Netlify-deployed). It reads `apps/landing/public/dashboard.json` at runtime via `fetch('/dashboard.json')`. The `.charity` field is the contract.

`scripts/lib/ledger.sh` does the write-back:

1. Local clone of anicca-products is at `~/anicca-products` (env override: `ANICCA_PRODUCTS_DIR`).
2. The script:
   - `git pull origin dev` (or `main` per `GIT_PUSH_BRANCH`)
   - patches `apps/landing/public/dashboard.json` with `jq` to push a new ledger entry, bump `total_given_usd` + `org_count`, and set `this_month` for next month
   - `git add apps/landing/public/dashboard.json`
   - `git commit -m "chore(donation): refresh <YYYY-MM> ledger ($AMOUNT to <charity>)"`
   - `git push origin dev`
3. The `netlify-deploy.yml` workflow triggers on `push` to `dev` / `main` with path `apps/landing/**`. It runs `npm ci && npm run build` and deploys to Netlify. Total time from cron to public page: typically 2–4 minutes.

### dashboard.json.charity schema

The donation page expects this shape:

```json
{
  "charity": {
    "this_month": {
      "charity_name": "<chosen charity>",
      "charity_url":  "https://...",
      "queued_amount_usd": 1.50,
      "payout_date": "2026-06-01"
    },
    "ledger": [
      {
        "month": "2026-05",
        "charity_name": "<chosen charity>",
        "charity_url":  "https://...",
        "amount_usd": 1.00,
        "paid_at":   "2026-05-07T01:01:24+09:00",
        "status":    "paid",
        "post_url":  "https://x.com/aniccaxxx/status/..."
      }
    ],
    "total_given_usd": 1.00,
    "org_count": 1
  }
}
```

The skill is the **only** writer of `dashboard.json.charity`. Other fields (`mrr`, `views`, `spend`, etc.) are written by other refreshers — they are preserved verbatim by the jq merge.

## Env / secrets

| name | required? | purpose |
|---|---|---|
| `SLACK_BOT_TOKEN` | yes | post to #metrics |
| `DONATION_DRY_RUN` | optional | `true` (default) skips the irreversible parts: account creation, payment save, donation submit, repo commit |
| `MODE` | required by `run.sh` | `install` \| `monthly` |
| `DONATION_BROWSER_BACKEND` | optional | `agent-{{profile.lateness.stakeholders.channel}}` (default) \| `{{profile.lateness.stakeholders.channel}}base` (fallback wrapper, future) |
| `ANICCA_PRODUCTS_DIR` | optional | path to local anicca-products clone (default: `~/anicca-products`) |
| `GIT_PUSH_BRANCH` | optional | branch to push the ledger commit to (default: `dev`) |
| `CHARITY_NAVIGATOR_API_KEY` | optional | API-based vetting for US charities; falls back to web-search check |
| `ANICCA_DONATION_CARD` | install + monthly — Keychain | macOS Keychain generic password JSON: `{"number":"...","exp":"MM/YYYY","cvc":"NNN","zip":"NNNNN","name":"Anicca AI"}`. Read inline; never written to disk. |
| `ANICCA_DONATION_<slug>` | post-install — Keychain | per-charity account password (random, written by install hook) |

MRR is fetched from the **public** `https://aniccaai.com/dashboard.json`, so no Stripe key is needed for the read path.

### Bootstrapping a new agent's card

For Dais's Anicca, the `ANICCA_DONATION_CARD` Keychain entry already exists (from v1). For a new Anicca instance spawned later, the install hook runs in a special sub-mode `MODE=install BOOTSTRAP=card` that:
1. Posts a Slack 🚨 to the agent's owner asking them to create the entry: `security add-generic-password -s ANICCA_DONATION_CARD -a anicca-donation -w '{...}' -U`
2. Polls Keychain every 5 min for up to 24 h for the entry to appear.
3. On detection, resumes the install hook from step 4.

This means a new Anicca cannot finish its install hook until the human gives it a card — by design.

## Slack message formats

### Install complete (one-shot, live)

```
🌱 donation install complete
agent: <agent-id>
charity: <name>  (<country> 501(c)(3), EIN/NPO id <id>)
cause: <area>
first donation: $X.XX  (1% of $MRR MRR, floor $1)
receipt: <path or url>
ledger seeded → aniccaai.com/donation will show it on the next Netlify build.
monthly cron is now armed: every 1st 09:00 JST.
```

### Install dry-run

```
🧪 [DRY] donation install
charity: <name>   donate URL: <url>
amount that would have been donated: $X.XX
intent file: ~/.openclaw/state/donation/intent.json
no account created, no card saved, no submit, no ledger write.
flip DONATION_DRY_RUN=false and re-run install to go live.
```

### Monthly complete (live)

```
✅ donation <YYYY-MM>: $X.XX → <charity>
receipt: <path>  (id: <receipt-id>)
ledger commit: <commit-sha> on dev (pushed to anicca-products)
public page refreshes in ~3 min.
total_given_usd → $X.XX  (orgs: N)
```

### Monthly dry-run

```
🧪 [DRY] donation <YYYY-MM>: would have donated $X.XX to <charity>
no submit, no ledger write, no anicca-products commit.
```

### Failure

```
🚨 manual donation needed
mode: <install|monthly>
charity: <name>   amount: $X.XX   donate URL: <url>
reason: <agent-{{profile.lateness.stakeholders.channel}} fill failed | submit no thank-you page | keychain missing | git push failed | ...>
screenshot: <path>
```

## Guardrails (auto, not user-gated)

| condition | action |
|---|---|
| MRR is `0` or `null` | skip + Slack alert ("no revenue this month — no donation"). Do NOT donate. |
| install sentinel missing in monthly mode | exit 1 + Slack 🚨 ("install hook never ran on this agent"). |
| agent-{{profile.lateness.stakeholders.channel}} session expired (login required) | re-login in-cron using stored credentials; if 2FA blocks, Slack 🚨 + abort. |
| `ANICCA_DONATION_CARD` missing in Keychain | install hook pauses (BOOTSTRAP=card path); monthly cron aborts with Slack 🚨 — should never happen post-install. |
| selector miss / form fill fails | screenshot, post Slack 🚨 with `<charity-url> <amount>`, do NOT retry blindly. |
| receipt URL is non-2xx after submit | log as `submitted-but-unverified`, Slack 🚨, do NOT mark complete in ledger. |
| today's `payout_date` already in `donation-history.jsonl` with status=succeeded | skip + Slack alert (cron mis-fire). |
| `DONATION_DRY_RUN=true` | install: discovery + intent file only; no account, no card save, no submit. monthly: print only. |
| `git push` to anicca-products fails | log + Slack 🚨; ledger entry kept locally so we can retry next run. |

Charity-discovery profanity / {{profile.lateness.stakeholders.senderType}} / similar guardrails do **not** apply — vetting (501(c)(3) + Charity Navigator score ≥ 3-star) is a stronger filter.

## How to install (for an agent loading this skill for the first time)

When an agent loads this skill, it must run `install.sh` once. The install hook is idempotent — re-running is a no-op once the sentinel is in place. After install, the monthly cron handles all recurring donations automatically.

```bash
# (one-time, on first skill load)
MODE=install bash ~/.openclaw/skills/donation/scripts/run.sh

# After install, the monthly cron at 1 09:00 JST handles the rest.
# Manual re-runs of the monthly path:
MODE=monthly bash ~/.openclaw/skills/donation/scripts/run.sh

# To go LIVE (after the user explicitly OKs it):
DONATION_DRY_RUN=false MODE=install bash ~/.openclaw/skills/donation/scripts/run.sh
```

## Manual run examples

```bash
# Install dry-run — agent discovers + vets a charity, writes intent.json, NO account / NO card / NO submit
DONATION_DRY_RUN=true MODE=install bash ~/.openclaw/skills/donation/scripts/run.sh

# Monthly dry-run — reads installed.json, computes 1% of MRR, prints what it would donate
DONATION_DRY_RUN=true MODE=monthly bash ~/.openclaw/skills/donation/scripts/run.sh

# Live install — only after user explicitly OKs DONATION_DRY_RUN=false
DONATION_DRY_RUN=false MODE=install bash ~/.openclaw/skills/donation/scripts/run.sh

# Live monthly — only after install + flip
DONATION_DRY_RUN=false MODE=monthly bash ~/.openclaw/skills/donation/scripts/run.sh
```

## Future enhancements

- **Stripe Issuing card auth** — if the dedicated card becomes a Stripe Issuing card under Anicca's platform, the receipt audit trail tightens (txn id flows back via webhook).
- **Browserbase / Stagehand backend** — `DONATION_BROWSER_BACKEND={{profile.lateness.stakeholders.channel}}base` for cloud execution. Trade-off: card has to leave host. Likely never used unless cron moves off-host.
- **Public proof page** — `aniccaai.com/donation` already reads `dashboard.json.charity`; add per-receipt screenshot links so the ledger is visually verifiable.
- **Recipient diversification (CAUSE_ROTATE=true)** — annual re-evaluation of charity choice once cumulative giving for the current charity passes a threshold.
- **Multi-currency** — JP charities accepting JPY only; convert at execution-time rate via `https://api.frankfurter.app/latest?from=USD&to=JPY`. Record both `amount_usd` and `amount_jpy` in the ledger entry.

## Why Vercel Agent Browser, not {{profile.lateness.stakeholders.channel}}-harness, not stripe.transfers.create

`stripe.transfers.create()` (used by `basic-income-monthly`) requires a Stripe Connect destination account under Anicca's platform. External charities are not Connect recipients, so transfers can't reach them.

`{{profile.lateness.stakeholders.channel}}-harness` (v1) is a custom Way-2 Chrome-on-9223 setup. It works but is bespoke and brittle. The Vercel Agent Browser CLI (`vercel-labs/agent-{{profile.lateness.stakeholders.channel}}`) ships a clean snapshot/ref API that's friendlier to agents and survives charity-site redesigns better. Same execution profile (local Chrome via CDP) — Keychain access is preserved.

Alternative cloud rails (Browserbase / Stagehand) are kept as a fallback (`DONATION_BROWSER_BACKEND={{profile.lateness.stakeholders.channel}}base`) but are not the default — moving the card off-host is a strict downgrade until a Stripe Issuing card replaces the personal card.
