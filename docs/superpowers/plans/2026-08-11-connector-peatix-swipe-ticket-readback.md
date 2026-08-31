# Connector Peatix swipe-ticket readback plan

## Goal

PeatixのQR型ではないswipe ticket pageをsame-event registration proofとしてparent readbackし、canonical pageにmarker/ticket linkがない既登録eventを次wakeで再Submitしない。

## Measured production evidence

- official wake `wake-97558353b86abced2440ac33`はdirect 4,417msで`/tickets → /billing → /confirm → /confirmed → canonical`を完走し、Browser Harness 0を実証した。
- canonical `/event/5101994`はticket link 0、registration marker 0、checkout control 0で、existing readerは`readback_unavailable`。runnerのD0c guardがfailure count 1の`effect_unknown`で即停止し、次candidate/Harness/evidence 0。positive Telegram ID `11411`。
- exact `/event/5101994/ticket`はauth redirectなし、`body.webticket=1`、`section.ticket=1`。旧QR selectorは0だが、swipe variantのvisible `.ticket_cover`、`.ticket_event`、`.ticket_event-name`、`.ticket_summary`が各exact 1。confirmation value/text/private ticket dataは読まない。
- current readbackがこのticket pageを認識しないため、前回登録済みeventを次wake directで再申込し得る。live wakeはこのreadback修復まで禁止する。

## Ponytail full gate

- 新store、receipt schema、provider abstraction、retry、scheduleを追加しない。
- 既存`readPeatixRegistrationStateOnPage`のexact same-event ticket page shellへQR variant OR swipe variantを追加する。
- `submitPeatixOnPage`のpre-submitとpost-confirm canonical unavailableだけ、同じowned pageでexact `/event/<same-id>/ticket`をread-only probeする。registeredなら即returnしSubmit 0。証拠不成立ならcanonicalへrestoreして既存flowを継続する。
- ticket text、confirmation number、ticket ID、attendee/private valueは読取・保存・log 0。wrong event/auth/malformed/duplicate/hidden/zero-sizeはregistered 0。

## TDD slice

Ownershipは`apps/mr-bot/lib/peatix-browser-provider.js`とmatching testの2 filesだけ。Production soft target 25–45 LOC、test 60–100 LOC。

RED:

1. exact ticket URL + QR 0 + swipe visible exact shellがregisteredとなるreadback fixture。
2. missing/duplicate/hidden/zero-size swipe component、wrong event/auth/malformed ticket URLはregistered 0。
3. initial canonical unavailable→exact ticket swipe registeredはticket probe 1、final click 0、registered。
4. ticket proof不成立はcanonical restore後に既存tickets/form/confirm flowへ進む。
5. post-confirm canonical unavailable→ticket swipe registeredはfinal 1、ticket probe 1、registered。

GREEN:

- existing visibility helperでQR shellまたはswipe shellのexact counts/visibilityをboolean proofにする。
- private text/valueをreturn objectへ加えない。
- helperはcanonical exact pageからticket exact URLへgoto/readbackし、不成立時はcanonical exact URLへrestoreする。navigation failureはsafe unavailable。

## Verification

- focused provider RED/GREEN
- Peatix workflow、minimal runner/production/evidence、Harness adjacent
- syntax、`git diff --check`
- fresh Sol review Critical 0 / Important 0
- push後official wake exact 1回でsame-event pre-readback registered、provider Submit/Harness 0、evidence bundle、Meetup audit到達または次exact safe boundaryを確認する。

実装結果: Luna REDはfocused provider 25/29で、swipe shell未認識、pre-submit ticket回収なし、unproven canonical restoreなし、post-confirm ticket回収なしの4 failureを再現した。GREEN commit `f05fb785d`はprovider/test 2 filesだけで、QR OR exact visible swipe shell proofとcanonical→ticket read-only probe/restoreをpre/postへ接続した。wrong marker/auth/malformedはprobe 0、registeredならSubmit 0、unprovenならcanonical exact restore、新event flowを維持。private text/value/confirmation number読取・保存0。Luna focused 29/29・adjacent 136/136、Sol独立expanded 165/165、syntax/diff check PASS。workflow 1 failureは既知の日付依存。fresh Sol reviewはCritical 0 / Important 0で`ship`。実装/review中のbrowser/provider/Calendar/evidence/Telegram/state/schedule作用0。
