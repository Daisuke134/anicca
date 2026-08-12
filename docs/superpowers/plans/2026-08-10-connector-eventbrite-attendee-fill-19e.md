# Connector Eventbrite attendee same-frame fill plan (Item 19E-D4b2b)

## Goal

観測済みEventbrite attendee exact4 controlsのうち選択された未完了1 fieldをsame-event child frameでexact 1回fillし、同じfieldの`completed=true`を再観測する。final Register、checkbox、provider final effect、evidenceは0件。

## Ponytail gate / size

- 既存attendee inspector、private resolver、`operatePageControl`、same-event frame bindingを再利用する。新規file/service/action typeは作らない。
- Harness production/test 2 filesのみ。soft targetはproduction 35–50 LOC、test 35–50 LOC、total 70–100 LOC。
- 4 fieldsを一括fillするhelperやprovider final stateは作らず、既存fallbackのone-action-per-step契約へ合わせる。

## Exact action contract

1. Eventbrite attendee control tokenは`eventbrite_attendee_(first_name|last_name|email|confirm_email)_<eventId>`をcase-sensitive exact matchし、candidate canonical/event refと同じevent ID、observation exact4 controls内の一意required incomplete inputだけを受理する。
2. attendee inspectorは全契約成立後だけ、4 DOM elementsへ対応tokenを`data-lm-connector-control`としてbindする。validation失敗時はbind 0。
3. actionはexact `{purpose:"fill", method:"ax_fill", control}`。wrong method/purpose/provider/token、completed control、missing private valueはresolve/operate 0。
4. private value解決後・operation直前に、同一Frame objectのattendee DOM exact4を再検査し、parent canonical、official child frame total exact1、same eid、同一Frame identityを再確認する。DOM/page/frame/eid driftはoperate 0。
5. `operatePageControl`はsame frame内のexact token locator count1だけを1回fillする。top pageや別frameへfallbackしない。
6. fill成功後、parent/frame identityを維持したままattendee exact4を再観測し、選択fieldだけ`completed=true`になればsuccess。value本文や他private値は返さない。postcondition不成立はfailed。
7. marketing checkbox、login button、primary `eds-modal__primary-button`をbind/operateしない。final effect/readback/evidenceは開始しない。

## TDD / verification

1. RED: exact first-name actionがresolve1/fill1/completed trueになる期待に対し現行failed/operate0を確認する。
2. email/confirm-email同値、wrong action、completed、missing value、duplicate/hidden/unknown required、DOM drift、page/frame/eid drift、locator 0/2、postcondition falseを最小fail-closed回帰にする。
3. GREEN: attendee field predicate、validated DOM binding、operate直前再検査、post-fill確認だけを実装する。
4. Harness focused、Eventbrite workflow/minimal production/operations/registry/native adjacent、syntax、`git diff --check`、exact2-file scope、private literal scan、cleanを確認する。

## Deferred

fallback full four-field sequence live acceptance、final Register control/click、registered readback、factory/runFallback/native provider order、evidence/Telegram、schedule load。
