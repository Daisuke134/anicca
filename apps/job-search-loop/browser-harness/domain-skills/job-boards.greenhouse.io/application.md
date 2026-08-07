# Greenhouse — fenced embedded application

Use this recipe for official `job-boards.greenhouse.io/{board}/jobs/{job_id}`
applications. The Ledger owns Submit authority. Browser Harness operates the official
embedded form; it never uses an employer's private Job Board API key.

## Inspect without rediscovery

1. Parse `board` and `job_id` from the canonical URL.
2. Read the public job definition and questions from
   `https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{job_id}?questions=true`.
3. Observe the rendered application form with Accessibility and DOM controls. Treat
   the API question list as structure, not permission to bypass the official form.
4. Produce an exact plan containing field key, question, control kind, answer,
   private-profile fact IDs, and resume hash. Do not include Submit in the plan.

Greenhouse's official documentation says its direct application POST requires the
employer's secret Job Board API key and encourages use of the embedded form. Never
request, infer, or expose that key.

## Fill and verify

- Fill only from the supplied private profile and material files.
- Verify text by current value, select/combobox by its committed displayed option,
  checkbox/radio by checked state, and upload by filename plus source SHA-256.
- Re-read required controls after dynamic questions expand. A required field without
  a grounded answer pauses the same intent and asks one Telegram question.
- Preserve a private fill receipt and pre-submit screenshot hash.
- Send the exact resume and every question/answer to Telegram before Submit.

## Submit once

1. Confirm the Ledger intent and fence are still active and the application owner is
   `agent`.
2. Attach Network request/response observers and visible status/alert observers
   before touching the button.
3. Require exactly one visible button named `Submit application`.
4. Commit Ledger click phase `clicked` immediately before one coordinate click.
5. When the same click starts the official Greenhouse application request, commit
   transport phase `request_started`. Never log its multipart body or answers.
6. Wait for the first terminal response, visible validation error, CAPTCHA result, or
   bounded timeout. Never click again in this intent.

## Receipt classification

HTTP 2xx alone is not success. Mark `submitted` only when the same click has both an
official Greenhouse application response without an application error and a visible
confirmation state that says the application was received/submitted. Preserve the
response status, final URL, visible-status hash, screenshot hash, and later Gmail
match.

If the click occurred but these signals do not agree, record `submit_unknown` and
forbid retry. Visible validation rejection before a submit request returns to the
same fenced fill step. An invisible reCAPTCHA frame is observation, not failure; an
actual challenge is reported explicitly and is never answered or bypassed here.

## Required terminal report

Send Telegram the company, role, official URL, exact dossier message IDs, click and
transport phases, terminal classification, receipt evidence when present, failure or
unknown reason, and remaining quota. Silent failure is not a terminal outcome.
