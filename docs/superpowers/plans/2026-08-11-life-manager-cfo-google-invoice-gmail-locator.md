# CFO-2a3.2a — Google Invoice Gmail Locator Plan

> Workflow: Ponytail full → Superpowers TDD. Sol plans/verifies; Luna owns production/test/package edits.

**Goal:** Reuse the authenticated local `gog` transport to locate exactly one latest Google Cloud invoice PDF and
return only the private locator metadata required for the next download slice.

**Why this is the next smallest slice:** Actual local probing shows one authenticated `gog` account, ten matching
monthly invoice emails in the last 400 days, a stable `YYYY-MM-DD HH:mm` search date, exact Google Payments sender,
exact Google Cloud subject prefix, and exactly one PDF attachment on the latest message. Search results do not expose
attachment IDs; one `gmail get --format=full` call is required. No billing export or new connector is needed.

**Files and soft targets**

- Modify `apps/life-call/lib/transport/mail-gog.js` — <= 40 added production LOC.
- Create `apps/life-call/lib/cfo-google-invoice-mail.test.js` — <= 70 added test LOC.
- Modify `apps/life-call/package.json` — add the focused test filename once to `test:cfo`.
- Maximum: 3 files, <= 111 added LOC.

## Task 1: RED

Write exactly two tests:

1. from unsorted search hits, choose the newest valid exact sender/subject/date hit, perform one full-message read,
   validate exactly one safe PDF attachment, and return a frozen six-key locator without sender, subject, body, or
   account data;
2. return `null` without throw/log when account is absent, search/get JSON is invalid, all hits are invalid, PDF is
   missing/duplicated/unsafe, or a command fails. Keep these cases in one table-driven test.

Run the focused file and record the expected missing-method/contract failure.

## Task 2: GREEN

Add one method to the existing `makeGogMail` return object:

`findLatestGoogleCloudInvoice()` → frozen
`{ messageId, attachmentId, filename, size, receivedAtLocal, source }` or `null`.

Rules:

- fixed Gmail query: exact sender, exact subject phrase, PDF attachment, `newer_than:400d`;
- search maximum 10, no body request, and `--gmail-no-send` on both read commands;
- accept only hex message ID, exact `payments-noreply@google.com` address, subject prefix
  `Google Cloud Platform & APIs:`, and `YYYY-MM-DD HH:mm`; sort this fixed timestamp lexically descending;
- one `gmail get <id> -j --format=full --gmail-no-send` for the chosen hit;
- accept exactly one attachment with PDF MIME, safe `.pdf` filename, base64url attachment ID, and positive safe size;
- return only the six keys above, with `source = google_cloud_invoice_gmail`; freeze the result;
- no download, PDF parsing, persistence, hash, invoice amount, I/O path, retry, DB, OTel, scheduler, or Telegram.

Run focused, `npm run test:cfo`, and full `npm test`.

## Task 3: REVIEW AND CLOSE

Fresh Sol review checks only exact selection, command count/argv, fail-closed behavior, privacy, and YAGNI. Same Luna
fixes required findings. Sol independently reruns the focused/CFO/full suites, syntax, diff, and LOC, updates the
child/parent specs, commits, and pushes before CFO-2a3.2b starts.

