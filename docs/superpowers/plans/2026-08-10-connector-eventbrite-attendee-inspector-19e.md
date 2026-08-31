# Connector Eventbrite attendee inspector plan (Item 19E-D4b1)

## Goal

実Eventbrite attendee frameで測定した必須4 fieldsだけを、same-event checkout child frameから安全なcontrol tokenとして観測する。このsliceのfill、checkbox mutation、final Register、provider effect、evidenceは0件。

## Ponytail gate / size

- 既存`inspectPageControls`、same-event frame binding、strict visibility、`safeControl`を再利用する。新規file・service・profile・selector libraryは作らない。
- production/test各1 fileのみ。soft targetはproduction 30–45 LOC、test 30–45 LOC、total 60–90 LOC。
- 既知4 fields以外のrequired fieldが1件でもあれば全controls 0。任意marketing checkboxは観測対象外で操作しない。

## Ownership

- `apps/mr-bot/lib/connector-production-browser-harness.js`
- `apps/mr-bot/lib/connector-production-browser-harness.test.js`

## Exact observation contract

1. parent URLはcandidate canonical exact、official `/checkout-external` child frame total exact 1、`eid` exact 1かつcandidate event ID一致を既存bindingで要求する。
2. ticket cardがvisible 0のattendee stateだけを対象にする。ticket cardが残る、101+ inspected controls、locator/evaluation例外はcontrols 0。
3. visible/enabled required inputsはexact 4:
   - `input[type=text][name="buyer.N-first_name"]`
   - `input[type=text][name="buyer.N-last_name"]`
   - `input[type=email][name="buyer.N-email"]`
   - `input[type=email][name="buyer.confirmEmailAddress"]`
4. 各fieldはexact 1。duplicate、wrong tag/type/name、hidden/detached/disabled、unknown required input/select/textarea/checkboxは全controls 0。
5. control tokenはevent IDをbindしたcase-sensitive exact 4個。labelは`First name`、`Last name`、`Email`、`Confirm email`。`required=true`、`completed`はtrimmed non-empty boolean、`submittable=false`。
6. `eds-modal__primary-button`と任意marketing checkboxは公開しない。private valueやinput value本文は返さず、completed booleanだけを返す。
7. `performAction`のEventbrite field操作はこのsliceで引き続きfailed/0 mutation。

## TDD / verification

1. RED: ticket card gone＋exact4 fieldsで4 controlsを期待し旧実装0を確認する。
2. duplicate、unknown required、hidden/disabled、wrong type/name、101+、primary/marketing非公開、completed booleanだけの最小fail-closed回帰を追加する。
3. GREEN: same frame内の最小inspectorを追加し、既存ticket inspectorを壊さない。
4. Harness focused、Eventbrite workflow/minimal production/operations/registry adjacent、syntax、`git diff --check`、exact2-file scope、worktree cleanを確認する。

## Deferred

private value resolve、frame fill、confirm-email equality、post-fill再観測、final Register、registered readback、factory/runFallback/native provider order、evidence/Telegram、schedule load。
