# Connector Eventbrite bounded listing pagination 19E Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and subagent-driven-development. Luna writes production/tests; Sol reviews and verifies.

**Goal:** Production Eventbrite discoveryがpage 1だけでなく、実測で14日内の既登録候補が存在するpage 3まで同じowned pageで探索する。

**Measured live failure:** Official wake `wake-8fb25d522faf88565a7316b0` reached Eventbrite but audit was `80/0/0/0/0`. Default reader navigates only the base listing URL. Isolated real-site read-only measurement of exact URLs found page1=`80 cards/exact event 0`, page2=`80/0`, page3=`28/exact event 4`; every requested URL remained exact and the diagnostic page was closed. Registration/Calendar/evidence effect 0。

**Architecture:** Existing `defaultReadListingBindings`だけをbounded 3-page same-page loopへ変える。Exact URLs are base, `?page=2`, `?page=3`; each navigation must remain exact after `goto`. Existing exact card selector, row shape, 500-row contract, canonical dedupe, detail eligibility、Calendar gate、audit schemaを再利用する。New browser/session/provider serviceは作らない。

**Estimated change:** 2 files。production 15〜30 LOC、test 35〜70 LOC。

## Constraints

- Modify only `apps/mr-bot/lib/connector-eventbrite-workflow.js` and matching test.
- Use one supplied owned page; create/close page、context、browser 0。
- Navigate exact bounded list `[LIST_URL, LIST_URL?page=2, LIST_URL?page=3]` in order; no page 4 and no inferred link click。
- Any navigation URL drift、goto/evaluate error、non-array page result fails the entire discovery with existing safe listing code; partial page rows are not returned。
- Exact selector and safe row fields unchanged; raw body/private data not collected。
- Existing dedupe/detail/free/Tokyo/window/Calendar/readback/action contracts unchanged。
- Implementation/review中official wake 0、4 labels UNLOADED。

## Task 1: Read three exact Eventbrite listing pages

1. Extend the current default-reader test to expect all three exact navigations and page-specific rows; run RED showing only page1 is read。
2. Add URL list and bounded same-page loop, concatenating only validated arrays after all pages succeed。
3. Add URL drift and page-read failure regressions proving partial rows never escape。
4. Run Eventbrite focused, minimal production, Harness, operations, syntax, `git diff --check`。
5. Exact two-file ownership、commit without amend。fresh Sol review SHIP後にpush。

## Completion gate

- Default discovery reads pages1–3 on one page and preserves exact navigation/selector contract。
- Partial/error/4th-page behavior fails closed or remains unreachable。
- Focused/adjacent PASS、fresh Sol review Critical/Important 0。

## Deferred

Push後official wake exact 1回でpage3 candidateのregistered pre-readback、final Submit 0、Calendar/evidence/Telegram applied bundleを受け入れる。
