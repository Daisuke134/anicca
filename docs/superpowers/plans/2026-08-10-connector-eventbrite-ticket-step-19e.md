# Connector Eventbrite single-free-ticket step plan (Item 19E-D3)

## Goal

Eventbriteのstrict eligible candidateについて、same-event checkout child frame内で一意な無料ticketがquantity 1に確定済みの場合だけ、最初の`Register`を1回押し、ticket selection stepを抜けたことを親側で確認する。attendee final submitとregistration readbackはこのsliceで実行しない。

## Ponytail gate

- 既存Browser HarnessのEventbrite frame seamだけを拡張する。
- production 1 file 約60–90 LOC、test 1 file 約90–130 LOC。
- 新agent/service/API/DB/session/pageを追加しない。
- factory/runFallback workflow injection/native provider order/evidenceは変更しない。

## Owned files

1. `apps/mr-bot/lib/connector-production-browser-harness.js`
2. `apps/mr-bot/lib/connector-production-browser-harness.test.js`

## RED

1. exact candidate/current canonicalとsame-eid official child frame exact 1が必要。
2. visible ticket card exact 1、card内stepper exact 1、quantity text exact `1`、increase exact 1、decrease exact 1かつdisabled、card textにstandalone `Free`が必要。
3. card textにcurrency amount、cash、paid、door fee、minimum purchase、会場払い、当日払い、有料があればcontrol 0。
4. visible/enabled primary `button[type=button][data-testid=eds-modal__primary-button]` label `Register` exact 1だけを`eventbrite_ticket_register_<eid>`として公開する。duplicate/hidden/disabled/fuzzyは0。
5. actionはEventbrite exact candidateの同controlに`submit/ax_click`だけ許可し、official child frame内primaryをexact 1回clickする。
6. click後もparent canonical、same-eid child frame exact 1を維持し、ticket card visible 0が500ms安定した場合だけsuccess。ticket card残存、parent navigation、frame ambiguityはfailed。
7. attendee field/final Register/provider readback/Calendar/evidence/Telegram effectは0。

## GREEN

- Eventbrite checkout child frameをcandidate IDで厳密に取得するhelperを既存frame identity contractから再利用する。
- main CTA frameが開いている時はticket-step inspectorを優先する。
- frame controlには別tokenを付与し、main-page controlと混同しない。
- ticket-step Registerはnon-final triggerとして扱い、final-effect waitを開始しない。

## Verify

- focused Harness test、既存Harness全件
- Eventbrite workflow/minimal production/operations/registry
- syntax、diff check、exact 2 files
- schedule unloaded、live external effect 0

## Deferred

Calendar-free candidateでこのstepを実行し、attendee formの実DOMを測る。required attendee controls、final Register、parent readback、factory/runFallback injectionは別slice。
