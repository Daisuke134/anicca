# Connector Connpass applied bundle Item 14A plan

## Goal

Add Connpass to the existing minimal evidence chain so one parent-verified `registered` or `pending` Connpass result produces the same immutable provider receipt, actual-page PNG/SHA, exact Google Calendar readback, Telegram message/photo receipts, and `applied_bundle` contract already used by Luma and Peatix. Do not change discovery, registration, Browser Harness, runner, Calendar policy, provider order, or schedules.

## Measured product boundary

- Official Connpass search exposes date and location filters: source `connpass event search`, https://connpass.com/search/ — core text: `開催日` and `開催場所`.
- Official participant guidance says an applicable event has the exact control `このイベントに申し込む`: source `イベントに参加する`, https://help.connpass.com/participants/event-join — core quote: `「このイベントに申し込む」ボタン`.
- The same guidance requires a registered and confirmed email before application: source `イベント参加申し込み時のメールアドレスの確認`, https://help.connpass.com/participants/event-join#id6 — core quote: `メールアドレスの登録・確認が完了している必要があります`.
- Live read-only measurement found the existing owned email already had a Connpass account. Password reset and `:9222` login succeeded; no event application was submitted. Keychain persistence did not complete and is not claimed.
- Authenticated Calendar-gated discovery found exactly one current eligible candidate, event `400028`. Its join page has two participation radios, one required bounded radio question, optional fields, and the single final control `申し込みを確定する`. The existing bounded Browser Harness owns this form step.

## Ponytail full gate

- Reuse `createConnpassEvidenceStore`, the existing checkpoint/delivery/bundle schema, Calendar adapter, Telegram senders, and applied-bundle scanner.
- Add no new store, schema, queue, account manager, registration adapter, retry, schedule, or provider abstraction.
- Connpass capture uses the actual parent-verified page screenshot; it must not replace the page DOM with synthetic receipt HTML.
- Exact Connpass identity is HTTPS, no credentials/port/query/hash, Connpass root/subdomain, and the same positive event ID in event ref and `/event/<id>/` path.
- A failed identity/status/store/artifact/Calendar/Telegram boundary writes no final bundle. Existing partial checkpoints remain the only recovery mechanism.

## Implementation slice

Luna owns only:

1. `apps/mr-bot/lib/connector-minimal-evidence.test.js`
2. `apps/mr-bot/lib/connector-minimal-evidence.js`

Soft target: 2 files; production `+25–45 LOC`; tests `+40–65 LOC`.

### RED

1. Connpass `registered` with exact event ref/URL is currently rejected before evidence; add a test that requires one actual page screenshot, store receipt/artifact, Calendar create plus independent exact readback, positive Telegram message/photo IDs, and one immutable provider-specific bundle.
2. Assert Connpass capture calls `screenshot({type:"png", fullPage:true})` and never calls `setContent` or navigates away from the verified page.
3. A second exact call validates bundle/store/artifact/checkpoints/current Calendar and returns runtime `completion_disposition: reused` with screenshot/store/Calendar-create/Telegram all zero.
4. Wrong event identity, noncanonical URL variants, unsupported provider status, malformed receipt/artifact, or Calendar mismatch fails before downstream effects and bundle creation.
5. Existing Luma and Peatix positive/recovery/corruption matrices remain unchanged.

### GREEN

- Add the Connpass event/receipt descriptor and default `createConnpassEvidenceStore` instance to `createMinimalEvidenceChain`.
- Reuse the existing orchestration. Branch only provider capture: Connpass screenshots the current page directly; Luma and Peatix behavior stays byte-for-byte unchanged.
- Keep persisted bundle schema unchanged and return only the existing runtime `created|reused` disposition.

## Verify and live close

- Luna runs focused evidence RED/GREEN plus Luma/Peatix/store regression, syntax, and `git diff --check`.
- Sol runs an independent expanded suite and a fresh Sol review for exact identity, real-page evidence, checkpoint/reuse integrity, privacy, and zero non-Connpass regression.
- Update SSOT, commit, and push before live action.
- Then run official `skills/connector/run.sh` exactly once with all four schedules unloaded. Acceptance is Luma external effect zero, same owned session/target/page handoff to Connpass, real Connpass parent readback `registered|pending`, cache/direct/Harness Submit bounded with final Submit at most one, exact Connpass bundle one, positive every-wake report, and full cleanup.

## Item 14 semantics

The product invariant is cross-provider continuation after Luma produces no external effect. An artificial production failure hook would make live acceptance synthetic, so accepted Luma precursor states are bounded known-no-effect, exact existing-bundle reuse with Submit zero, or eligible-candidate exhaustion under the unchanged Calendar gate. Current measured state is ten free/open Luma events and zero Calendar-free candidates; live Item 14 therefore uses truthful Luma exhaustion followed by the real Connpass application.

## Fresh review result

- The first evidence-wiring diff passed an independent expanded `63/63`, but fresh review returned `fix-first`.
- Existing Connpass store reads did not bind saved receipt event/artifact fields back to the provider ID, and the artifact marker carried an event ref that its read contract could not authenticate.
- The evidence-wiring diff is frozen in a reversible stash. Prerequisite plan `2026-08-11-connector-connpass-evidence-store-hardening-14a0.md` closes the store in two files before this plan resumes; no code from this plan is shipped until that review passes.

## Final result

- After Item 14A0 shipped, Luna restored this two-file slice. RED reproduced the missing exact-five-field Connpass receipt gate at 27 pass / 1 fail; GREEN requires it only for Connpass and keeps the Luma/Peatix contracts unchanged.
- Connpass captures the exact current candidate page with `fullPage: true`, never calls `setContent` or `goto`, and validates identity, state, receipt, artifact, object bytes, and created-to-reused behavior before downstream effects.
- The first final review found that exact page URL validation occurred after existing-bundle scan. A second RED proved wrong event, query, hash, and `about:blank` could reuse a bundle; Luna moved the Connpass-only URL gate before the scan.
- Final production/test diff is two files, 101 insertions and 1 deletion. Independent minimal-evidence plus all provider-store regression passes 33/33; syntax and `git diff --check` pass. Fresh Sol re-review: `ship`.
