# CLOUD-01 — Detailed travel and online reminder display

Owner-approved scope: Cloud daily launch only, following the 2026-09-05 revision in PR #4149 of `2026-08-28-life-manager-cloud-telegram-product-ux-design.md`. Local operations, loop migrations, alternative billing, and agent-framework changes are excluded.

This is the display-only amendment to AC-21/AC-22 of `2026-08-26-life-manager-cloud-on-time-core-design.md`. All other existing runtime, consent, tenant, claim, receipt, privacy, and deployment requirements remain binding. CLOUD-02, not this change, owns departure calculations and Calendar/call timing consistency.

## Current launch status — verified snapshot 2026-09-06

**IN PROGRESS / NOT READY FOR FRIEND BETA OR GENERAL RELEASE.** This is an evidence snapshot, not a live monitor or a claim that all existing Cloud features are broken.

- Scope PR [#4149](https://github.com/Daisuke134/life-manager/pull/4149) is merged as `f54a1c8010e11614c06aae4d905f28ce0cb098be`. The launch uses the existing Life Manager runtime and Stripe. ElizaOS / Eliza Cloud / `@elizaos/plugin-life-manager` are not adopted; local operations and later loop migrations remain the local Codex workstream.
- Observed `main`: `551c27b1b22102d355b579b1e28b717cce68589c`. Implementation PR [#4150](https://github.com/Daisuke134/life-manager/pull/4150) is open and unmerged. Its observed source/CI head before this documentation update is `0ea45f8f4f5a8122cf4c9cde398ca1b28dbf82c6`.
- At that observed head, [Cloud reminder contracts run 33975119139](https://github.com/Daisuke134/life-manager/actions/runs/33975119139) completed successfully. This status was read back; no new application test execution is claimed for this documentation-only update.
- At the same head, [Security Scan run 33975119140](https://github.com/Daisuke134/life-manager/actions/runs/33975119140) failed in gitleaks, PII shapes, OSS self-contained boundary, and Loop control contracts. TruffleHog, Python syntax/tests, shell syntax, and startup context checks succeeded. A failing scanner is not by itself proof of a live credential leak, but the failures are not waived.
- [CodeRabbit review 5120764121](https://github.com/Daisuke134/life-manager/pull/4150#pullrequestreview-5120764121) reviewed head `dd33c89db99d1c12bae4ad5174105c12ba6dc9da` and reported one actionable documentation finding: the recorded verification head was older than the reviewed document. It is a completed review of that head, not approval of later changes. The historical TDD evidence below is now explicitly separated from this newer CI observation.
- CLOUD-01 merge, exact-service deployment, actual delivery of this new formatter, provider-receipt/replay verification, and fresh-user acceptance remain unverified. A documentation merge or successful unrelated Railway service status proves none of these.

Record future evidence against the exact source commit and, where relevant, the prospective merge commit and deployed service SHA. A later documentation commit does not retroactively change which revision an earlier workflow tested. Do not label all checks green or launch complete from a focused CI result.

## Display contract

1. Render provider walking legs and rides in their original order. Render geographic access/egress walking summaries only when the respective detailed edge walking step is absent. Do not sum access and egress into a purported total that omits transfer walking.
2. Use each walking leg's valid timestamps to derive its duration; round positive partial minutes up. Missing, negative, or invalid walking duration must not become an invented zero. Preserve known endpoints and label an unknown duration.
3. Keep line, headsign, ride times, stations, supplied platforms, transfers, and supplied fare. Do not invent distances, entrances, exits, cars, crowding, or live service alerts. This slice adds no provider or fetch.
4. An online event uses a computer icon and a locationless event a reminder icon; neither displays departure, arrival, route errors, or a stale route. Existing Calendar interpretation remains authoritative and online routing stays zero.
5. A standalone HTTPS URL from the online location may be shown as `イベント詳細`, not asserted to be a meeting-room URL. Reject credentials in URLs, insecure/unsafe schemes, malformed URLs, and embedded whitespace. Escape rendered text for Telegram HTML. This is URL rendering only, not fetching.
6. Display a physical route's provider arrival when valid; never label Calendar start as the route arrival. A failed physical route displays the event, start, destination, and explicit unavailability, without fabricated departure/arrival. Timing computation is unchanged pending CLOUD-02.
7. Keep one message per existing claim. Bound escaped text conservatively to 4096 characters without cutting an HTML entity or Unicode code point, and mark truncation explicitly. Do not split into independently sent messages.
8. Preserve existing claim → send → receipt, positive message-ID validation, unknown-delivery reconciliation, and replay fences byte-for-byte outside the formatter area.

## Code and tests

- Production: `apps/life-manager/lib/travel-reminder.js` (formatting only).
- Existing snapshots: `apps/life-manager/lib/travel-reminder.test.js` (only the two intentionally changed display expectations).
- Regression coverage: `apps/life-manager/lib/travel-reminder-detail.test.js` (14 tests, including real parser/projection with injected external IO).
- Credential-free CI: `.github/workflows/cloud-reminder.yml` (read-only token, locked dependency install, no production credentials).

Run from `apps/life-manager`:

```bash
node --test lib/travel-reminder.test.js lib/calendar-interpreter.test.js lib/events.test.js lib/transit.test.js lib/travel-transit-wire.test.js lib/route-cache.test.js
node --test lib/travel-reminder-detail.test.js
```

## Historical TDD evidence — 2026-09-05, not current release approval

- Implementation branch: `fix/cloud-01-detailed-reminder-20260905`; PR #4150.
- Original base: `7e10f5348f757eb103d1365bb5fd8aa7a0c94bb7`.
- RED head: `36cb54a349578e9f457e36e28e932841f882bd8a`; Actions run `33957886608`, job `101284414308`. Existing contracts 84/84 passed; new display suite 1/14 passed, 13 failed on the old behavior.
- Historical GREEN head: `1a185c27a6f6d64ac07171db7c68a268987b5e55`. Actions run `33958578988`, job `101286278624`, tested prospective merge `9a57abfec5a0fc8f4bf383c40c00d2f012d7d341` against then-main `ff1a5ab4d6566762b2c3df640873ee37160b6efa`.
- That GREEN run passed existing contracts 84/84 and new regressions 14/14, failures 0, skipped 0. Node 22.23.2, locked install completed. The full application suite was not run in that verification. These counts belong to that run and are not a claim about an unexecuted later revision.
- The historical source diff excluded the scheduling/effect function; a transient duplicate guard was removed. The existing release-claim assertion was restored; only intended formatter snapshots differed.
- No production credential, Calendar event, Telegram send, phone call, or payment was used for those tests. Tests with injected external IO do not prove real delivery or a real new user's onboarding.

## Immediate TODO — finish CLOUD-01 before advancing

- [ ] Compare the failing verification results against their exact tested base and current relevant source. Record each cause and owner. Fix Cloud-introduced failures; separately route unrelated local failures without changing local runtime. Resolve or explicitly adjudicate findings through the normal review process; do not disable checks, loosen secret/PII checks, or bypass branch protections. Unresolved material security or tenant-isolation findings block release.
- [ ] Reconcile the documentation review finding with the exact newer CI evidence, verify any later source/workflow changes, and record the final review/check decision. A review request is not an approval.
- [ ] Run required checks on the actual merge candidate; merge through the normal path only when its applicable gates are satisfied. Then read back the exact target Cloud service SHA and health.
- [ ] With an authorized test tenant, observe one real physical and one online reminder; correlate the actual Telegram message ID with the durable receipt and verify no duplicate on replay. Do not send test messages to uninvolved friends or publish private provider payloads.
- [ ] Update the primary progress ledger with actual observations, then advance to CLOUD-02. Do not mark this item shipped from unit tests, an open PR, or deployment metadata alone.

## Remaining launch TODO — summary of the canonical UX spec §8

The ordered acceptance contract remains [the product UX spec](2026-08-28-life-manager-cloud-telegram-product-ux-design.md), §§0/8. This table summarizes the current launch gates; it does not create a second architecture or assert that unverified existing features are unimplemented.

| Order | Launch item | Current acceptance status and next proof |
|---|---|---|
| CLOUD-01 | 詳細な乗換・オンライン通知 | 実装PRと関連CIあり。上記のレビュー/検査判定、merge、対象Cloudのdeploy、実通知receipt/replayを閉じる。 |
| CLOUD-02 | 出発・到着・通知時刻 | 出荷条件として未完了。同じ採用経路のdoor出発・到着・Calendar・電話を整合し、出発T-5、1日3移動、予定変更/取消、重複なしを検証。 |
| CLOUD-03 | QR/リンクからの初回設定 | 出荷条件として未完了。`/lm`と`/life-manager`からTelegram、本人のGoogle consent、基準地点、通知設定、Readyまで。iPhone/Android、中断再開、電話skipを検証。 |
| CLOUD-04 | Cloud単独稼働・ユーザー分離 | 出荷条件として未完了。新規tenantでMac mini/local credentials依存0、他tenantのread/write 0、Cloud再起動後の設定/receipt保持を証明。 |
| CLOUD-05 | 設定・停止・復旧 | 出荷条件として未完了。通知ON/OFF、住所変更、位置共有、Calendar再接続、電話opt-in、問い合わせ/解除/削除案内、障害時の連投防止を検証。 |
| CLOUD-06 | 実ユーザーE2E・友達beta | 出荷条件として未完了。本人以外のiPhone/Android利用者が自分のCalendarを接続し、実移動通知と3日間の利用を確認。合成actorを実機の代用にしない。 |
| CLOUD-07 | 既存Stripe・3日trial | 出荷条件として未完了。trial一度だけ、期限、成功/失敗/重複/更新/解約とserver利用権をtest mode優先で検証。実請求は別途許可。 |
| CLOUD-08 | 公開ページ・README・公開判定 | 出荷条件として未完了。QRと同じスマホ用tap link、実通知例、料金、privacy/support、Cloud対応範囲を実物と一致させる。 |

Friend-beta acceptance closes with CLOUD-01–06; paid general-release acceptance additionally requires CLOUD-07–08. Controlled tester invitations are not a claim of general availability. Do not publicly claim that anyone can use the product until that person's own onboarding and notification path is verified.

Success means a non-developer can open the QR or tap link, start Telegram, grant their own Calendar access once, finish setup without a developer editing their database, and receive their own correct reminders using only a phone. Google consent and optional phone opt-in remain real user actions. Later local-loop migration and agent-economy funding do not block this launch.

## Primary contracts consulted

- Transit OpenAPI: https://api.transit.ls8h.com/api/openapi.json — geographic `accessWalkSecs`/`egressWalkSecs`, walking leg times, and optional platforms.
- Telegram Bot API: https://core.telegram.org/bots/api#sendmessage — message length and HTML entity boundary.
- Existing current parser, event projection, transport, and delivery tests in this repository.
- Measured history: `../../../.superpowers/sdd/2026-08-26-life-manager-cloud-on-time-core/progress.md`. Preserve older valid receipts; this status update does not invent a new deployment or delivery.
