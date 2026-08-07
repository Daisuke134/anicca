# Ashby — fenced job application

Use this recipe only for an official `jobs.ashbyhq.com/.../application` URL whose
application, private profile, answers, resume, Ledger intent, and fence already
exist. The browser is an observation and execution surface; the Ledger remains the
side-effect authority.

## Fixed tool boundary

Do not rediscover CLI help or inspect Job Hunter source. Invoke the installed
deterministic CLI as:

```text
PYTHONPATH=apps/job-search-loop python3 -m job_search_loop.ashby_apply MODE \
  --endpoint http://127.0.0.1:9222 \
  --url OFFICIAL_URL \
  --output PRIVATE_RECEIPT_PATH \
  [--answers PRIVATE_ANSWERS_JSON --resume PRIVATE_RESUME_PDF \
   --profile ~/.config/anicca/job-search/profile.json] \
  [--ledger ~/.local/state/anicca/job-search/ledger.sqlite3 \
   --intent-id INTENT_ID --fence FENCE]
```

`MODE` is exactly one of `inspect`, `fill`, `verify`, or `apply`. Run one mode per
step and inspect its private JSON receipt before advancing.

## Sequence

1. Read the application and intent from Ledger. Stop when the owner is not `agent`,
   the intent is absent/completed, or the fence differs.
2. Run `inspect`. Required controls must resolve to `fill`, `select`, `check`, or
   `upload`; unsupported controls remain repair work.
3. Resolve answers only from the private profile. A genuinely absent personal or
   legal fact becomes a Telegram question and pauses this same intent.
4. Run `fill`, then `verify`. Continue only with `pre_submit_ready`, verified
   receipts for every action, and a valid pre-submit screenshot hash.
5. Send the exact resume and every question/answer to Telegram before Submit.
6. Run `apply` once with the existing intent and fence. The CLI commits `clicked`
   immediately before the physical click and `request_started` only after observing
   an official Ashby submit mutation.
7. Classify the returned receipt; never infer success from page appearance or HTTP
   200 alone.

## Authoritative success

Mark `submitted` only when the same attempt proves all of these:

- operation `ApiSubmitSingleApplicationFormAction` or
  `ApiSubmitMultipleFormsAction`;
- GraphQL `FormSubmitSuccess` for the application and every returned survey form;
- a visible `role=status` success message semantically containing both
  `your application` and `successfully submitted`;
- no visible alert.

Ashby company wording varies. Both “Your application was successfully submitted.”
and “Your application has been successfully submitted!” satisfy the visible-text
gate when the GraphQL gate also succeeds.

## Non-success outcomes

- `recaptcha_rejected` is retryable only through the Ledger-authorized client-block
  transition before any submit request.
- `recaptcha_pending`, `silent_timeout`, `validation_rejected`,
  `no_terminal_signal`, and any `request_started` attempt without authoritative
  success are not success.
- A clicked or request-started unknown becomes `submit_unknown` and must never be
  clicked again.
- Never answer or bypass a CAPTCHA inside this recipe. A measured pre-click
  fingerprint rejection may move to the separately fenced CamoFox recipe; a clicked
  intent may not.

## Required evidence

Preserve the intent ID, fence, exact materials receipt, pre-submit screenshot hash,
click phase, transport phase, submit operation, HTTP status, GraphQL typenames,
visible-status hash, post-action screenshot hash, terminal Ledger state, and
Telegram provider message IDs. Never persist GraphQL variables or private answers in
logs or this skill.
