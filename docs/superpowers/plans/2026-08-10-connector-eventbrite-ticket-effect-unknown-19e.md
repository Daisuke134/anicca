# Connector Eventbrite ticket effect-unknown plan (Item 19E-D4c3)

## Goal

Eventbrite ticket-step `Register` をexact 1回操作した後、30秒以内にticket card消失を確認できない場合を通常failedではなく`effect_unknown`へ固定する。遅延したattendee遷移が後から起きても同じticket actionを再実行しない。final attendee `Register`、provider readback、factory/native/evidenceはこのsliceでは0件。

## Ponytail gate / size

- 既存`waitForEventbriteTicketStep`、`performAction`、adapterの既存`safe_reason=effect_unknown`伝播を再利用する。新service、retry manager、timer、state fileは作らない。
- Harness production/test exact 2 files。production 1–4 LOC、test 20–45 LOCをsoft targetにする。
- timeoutを成功扱いにしない。DOMを再操作しない。待機時間を伸ばさない。

## Exact contract

1. exact ticket controlのpre-operation identity/page/frame/eid/semantic検査は不変。pre-operation failureはclick 0、通常`failed`のまま。
2. `operateControl`が`success`を返した後、ticket card消失が500ms安定すれば従来どおり`{status:"success"}`。
3. `operateControl`が`success`を返した後、`waitForEventbriteTicketStep`がfalseなら`{status:"failed",safe_reason:"effect_unknown"}`。これは「clickは発行済みだが外部effectを確認できない」を表す。
4. effect-unknown pathのticket clickはexact 1。postcondition待機中およびreturn後に2回目の`operateControl`を呼ばない。
5. final attendee Register、Calendar、evidence、Telegram作用は0。

## TDD

1. RED: exact ticket actionがsuccessを返すがticket cardが残り続けるfixtureをfake timersでtimeoutまで進め、結果`failed/effect_unknown`、operate count 1を期待する。
2. 既存success fixtureは`success`、operate count 1を維持する。
3. pre-operation paid/duplicate/disabled/page/frame/eid driftは`failed`、operate count 0、safe_reasonなしを維持する。
4. focused Harness test、Eventbrite/minimal-production/adapter adjacent、syntax、`git diff --check`、exact 2-file ownership、4 labels unloadedを検証する。
5. fresh Sol reviewでCritical/Important 0後にstableへ統合し、SSOTへlive観測由来の理由とretry禁止境界を記録する。

## Deferred

final attendee Registerのclick-once、official registered/pending readback、Eventbrite workflow injection、factory/runFallback/native provider order、実`applied_bundle`、evidence/Telegram、schedule load。
