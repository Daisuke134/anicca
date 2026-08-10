# CFO-2a3b.2 — Real Provider Dimension Source Acquisition Plan

> Workflow: Ponytail full → Superpowers GLVS. Sol performs guarded browser/source observation and writes the
> observed-schema plan. Luna writes parser/test code only after a real source exists.

**Status:** BLOCKED ON ONE-TIME GOOGLE CLOUD CONSOLE REAUTHENTICATION. No password or approval payload is requested;
Dais signs in directly in the existing CloakBrowser `daily-driver` profile.

**Goal:** Acquire one real, unfiltered official Cost Table CSV for the same billing account/invoice month as the
confirmed CFO-2a3 receipt, prove its default total matches that invoice, and only then define the smallest parser.

## Ponytail full decision

1. Do not create a fake CSV, parser guessed from documentation, private Console API client, BigQuery dataset/export,
   DB, scheduler, retry service, or Telegram path before one real source is observed.
2. Reuse the guarded `interactive:dais` CloakBrowser profile, existing gcloud account discovery, private local CFO
   state conventions, exact allocation contract, and existing hourly loop.
3. Browser acquisition is one owner-created tab under `browser-guard.sh acquire interactive:dais`; other tabs are
   untouched. The tab is closed and lease released on every terminal path.
4. A downloaded source is private: temporary/final directories `0700`, file `0600`, no filename/account/project/SKU/
   amount printed, and no repository copy.

## Unblock and execution gates

0. Dais signs in once to Google Cloud Console in CloakBrowser `daily-driver`. This is the only human step and shares
   no password with the agent.
1. Sol acquires the browser lease, creates one own Cost Table tab for the open billing account, and proves the page is
   authenticated and the selected invoice month matches the existing confirmed receipt without printing either ID.
2. Reset all report filters to defaults. Select the required official columns: invoice header/period/currency/total,
   project ID or number, service ID, SKU ID, cost type, and exact cost fields. Choose no grouping or the smallest
   provider-documented flat setting that preserves every row.
3. Download one CSV once to a private caller-owned directory. Prove MIME/extension/positive bytes, regular-file mode,
   source hash, observed header names, row count, and absence of formulas or executable content. Never print row
   values.
4. Independently exact-sum all provider rows and require equality with the confirmed invoice before parser work.
   On mismatch, retain no allocation and record only a fixed redacted blocker.
5. Sol updates this plan with the actual observed schema and a two-file/LOC budget. Luna then writes RED/GREEN parser
   code for only those observed columns. No implementation is authorized from documentation-only fixtures.
6. On parser PASS, run immutable dedupe and real allocation E2E, update specs, commit/push, and report one milestone.

## Current measured blockers

- Local candidate CSV: `0`.
- Relevant Gmail Cost Table/invoice CSV: `0` (three unrelated Google-domain CSVs excluded).
- Existing BigQuery dataset/export table: `0/0`.
- Public supported account-cost/export API: none in Cloud Billing discovery.
- Cloud Console: known account, password reauthentication required, no saved candidate available.

The next command after reauthentication is the guarded browser Cost Table read/download; it is not parser code.
