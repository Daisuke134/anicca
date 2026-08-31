# Connector Doorkeeper listing DOM repair 19D Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and subagent-driven-development. Luna writes production/tests; Sol reviews, live-verifies, and updates the SSOT.

**Goal:** Official Doorkeeper Tokyo listingの現行DOMからevent rowsを取得し、誤った`discovered_count: 0`を解消する。

**Measured cause:** [`https://www.doorkeeper.jp/prefectures/tokyo/events`](https://www.doorkeeper.jp/prefectures/tokyo/events) は「東京のイベント情報一覧」を返し、2026-08-11の取得ではcanonical event link 50件を持つ。現行HTMLは各eventが`.global-event.events-list`で、その子が`.events-list-items-wrap`。production parserは最初の`.events-list-items-wrap`を全体rootと誤認し、その子の`.events-list-item, li`を探すため0行になる。東京prefecture pageは9 event links、global events pageは50 event linksを返した。GitHub code search 3件では再利用可能な同DOM parserは見つからなかった。

**Architecture:** listing row rootだけを現行公式`.global-event.events-list`へ修正する。既存のcanonical URL、exact Tokyo venue、listing date、pagination、detail JSON-LD、free/open、Calendar conflict、audit contractsは再利用し変更しない。

**Estimated change:** 2 files。production 1〜5 LOC、test 5〜20 LOC。

## Constraints

- Modify only `apps/mr-bot/lib/connector-doorkeeper-workflow.js` and matching test.
- RED uses a current-DOM fixture: event root `.global-event.events-list` containing `.events-list-items-wrap`, title/date/venue descendants. The current parser must return 0 before the fix.
- Do not add broad `li` or arbitrary anchor fallback. Exact event root, canonical group event URL, date, and Tokyo venue remain required.
- Pagination/page limit, detail parser, eligibility, Calendar, registration, Harness, factory, native runner, audit schema, and live state are unchanged.
- No official wake during implementation; four labels remain UNLOADED.

## Task 1

1. Convert/add the default listing DOM fixture to the measured current structure and run RED.
2. Select all exact `.global-event.events-list` roots and reuse existing row extraction unchanged.
3. Run Doorkeeper workflow focused tests, minimal production/Harness adjacent tests, syntax, and `git diff --check`.
4. Confirm two-file scope, commit without amend, push, fresh Sol review.

## Live completion gate

After reviewed integration, run one official foreground wake with schedule unloaded. Doorkeeper `discovered_count` must be greater than zero or a new safe failure must identify the next exact boundary; process/lock/target cleanup and Telegram positive receipt remain mandatory.

## Result

Luna changed only the Doorkeeper workflow and its focused test. The current-DOM fixture produced RED `14/15` with actual `[]`; selecting exact `.global-event.events-list` roots produced GREEN `15/15`, while minimal production + Harness remained `87/87`.

Fresh Sol review returned SHIP with Critical/Important 0. Sol independently repeated focused `15/15`, adjacent `87/87`, syntax, diff, ownership, remote equality, and four-label unloaded checks. Reviewed commit `0faf0c6fe` was fast-forwarded into stable. No live wake or external effect occurred during implementation.
