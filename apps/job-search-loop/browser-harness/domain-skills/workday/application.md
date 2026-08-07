# Workday — tenant-scoped fenced application

Use this recipe for an official `*.myworkdayjobs.com` or `*.myworkdaysite.com` job.
Install this exact file under the Browser Harness folder named by the target
hostname's first label before use. One tenant account and one browser session remain
isolated from every other tenant.

## Advance one surface at a time

Capture a private, secret-free control snapshot and evaluate it with:

```text
PYTHONPATH=apps/job-search-loop python3 -m job_search_loop.ats \
  --snapshot PRIVATE_SNAPSHOT_PATH
```

Follow only the evaluated transition:

```text
workday_job -> ordinary Apply
workday_apply_choice -> Apply Manually
workday_account_create -> provision or reuse tenant credential, then create account
workday_application -> fill and verify the submit-bearing form
```

Recapture and reevaluate after every transition. Do not claim a submission slot until
the evaluator reports both `ready=true` and `claim_ready=true` on
`workday_application`. A visible application-entry control means the executor must
continue; it is not evidence that the application surface is missing.

## Tenant account

At `workday_account_create`, invoke the existing `workday_credentials` CLI with the
official job URL, private profile, and mode-0600 credential store. Load the generated
email/password only inside the same browser process. Never print, interpolate into a
command, snapshot, log, or Telegram-send either value.

If Workday sends account verification, accept only an exact trusted
`@myworkday.com` sender and a target validated by `workday_verification`. Consume it
once under its verification fence, then resume the same tenant and application.

## Fill and verify

- Route the resume from the normalized posting before filling.
- Ground every answer in the private profile and persist its fact IDs.
- Re-read dynamic required controls after each page transition.
- Verify text, option, checkbox/radio, date, and upload state in the rendered control.
- Ask one Telegram question only for a genuinely absent personal or legal fact,
  persist the reply, and resume the same fence.
- Preserve each step receipt, exact dossier, and pre-submit screenshot hash.

## Submit once

Attach network, visible status/error, navigation, and CAPTCHA observers before the
final action. Require one visible final Submit control. Commit Ledger `clicked`
immediately before one coordinate click and `request_started` only when the same
click starts the official Workday application request. Never click again for this
intent.

HTTP success alone is insufficient. Confirm `submitted` only when the same attempt
produces an official Workday application response plus a visible confirmation or a
trusted role-linked Workday confirmation email. Preserve the request status, final
URL, confirmation text hash, screenshot hash, Gmail message/thread ID when used, and
Telegram message IDs.

Clicked or request-started ambiguity becomes non-retryable `submit_unknown`. Visible
validation before a request returns to the same fenced step. An actual CAPTCHA is
reported explicitly and is never answered or bypassed by this recipe. Application
email is outside this recipe and may be considered only after every official Workday
route is proven unavailable; it is not a substitute for a difficult UI.
