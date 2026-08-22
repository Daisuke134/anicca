---
name: mercor
description: "Mercor provider lane for Life Manager: safe Google/Gmail authentication, resume/profile maintenance, grounded applications, and verified earnings. Use for Mercor jobs, assessments, applications, and the Life Manager job loop."
---

# Mercor

Mercor is a provider lane of Life Manager's existing Job Hunter system. Use this skill for provider policy and routing; `apps/job-search-loop/` remains the sole owner of browser and application side effects.

## Canonical owners

- Candidate truth and resume variants: `skills/job-hunter/` and `~/.config/anicca/job-search/profile.json`
- Browser/application runtime: `apps/job-search-loop/`
- Cadence: `loops/job-hunter/`
- Private Mercor state: `~/.local/state/anicca/job-search/mercor/`
- Integration spec: `docs/superpowers/specs/2026-08-22-mercor-life-manager-consolidation.md`

## Authentication hard stops

1. Use ordinary Google sign-in and inject the Keychain password only into the isolated UI. Never print or persist the secret.
2. Never click a browser Google 2FA button with accessible name `はい`; the user alone approves `はい` inside the Gmail iOS app.
3. Never use account recovery, reset, registration, recovery-email, or recursive alternate-method paths.
4. On any recovery/reset/wait screen, record the URL and visible text and stop.
5. Never use another site's tab or the trusted daily-driver browser.

## Application policy

- Reconcile an existing in-progress Mercor application before discovering a new listing.
- Apply only with verified profile facts and a read-back-verified resume artifact.
- Do not impersonate interviews or assessments. Unsupported questions, CAPTCHA, and ambiguous attestations become `needs_human`.
- Count earnings only from an authoritative Mercor Earnings/contract settlement read-back; never count views, invitations, estimates, or pending offers.

## Loop contract

The existing hourly `job-hunter` acquisition loop is the only loop. Do not create a second Mercor executor. The provider adapter must acquire the existing pass lease, deduplicate listings, submit at most the bounded per-wake quota, record evidence, and release the lease in a finally path.
