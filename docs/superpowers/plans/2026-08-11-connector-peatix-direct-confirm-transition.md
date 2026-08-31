# Connector Peatix direct-to-confirm transition plan

## Goal

Peatixのticket Next後にattendee formを省略してsame-event confirmへ直行する実variantをdirect providerで処理し、Browser Harnessを使わず既存confirmed settlementとcanonical parent readbackへ接続する。

## Measured production evidence

- official wake `wake-145a8e4a4f58e9239f113b3f`のhistoryはcandidate `5101994`で`/tickets → /billing → /confirm`が1秒以内、34秒後にHarness actionで`/confirmed`へ遷移した。
- provider directは30,857msで失敗し、その後Browser Harness 33,983ms、terminal `effect_unknown`。D0c guard対象の`peatix_readback_unavailable`ではなく、Next後に`form`だけを待つ`peatix_form_navigation_failed`だった。
- external click 0のtemporary owned pageで`/billing`を開くとsame-event `/confirm`へ遷移し、required field 0、`#confirm-button` exact 1、`#form-submit-button` 0。pageはexact cleanupしbaseline 1へ復帰した。
- Harness clickで実`/confirmed`へ到達しているため、次wakeはcanonical pre-readbackでregisteredを回収し得るが、新規eventでもdirect-onlyにするためtransition contractを修復する。

## Ponytail full gate

- 新module、billing form handler、provider abstraction、retry、cache、state、scheduleを追加しない。
- Next後にstrict same-event `form|confirm`のどちらかをbounded waitする。`billing`はtransientとして成功扱いしない。
- `form`なら既存field/form-submit処理、`confirm`ならそのblockだけを省略し、既存confirm identity/Kana/validation/final/confirmed/canonical readbackを再利用する。
- wrong event、auth、unrelated、query/fragment/credential/port、billing停留はfail closed。final clickはexact 1。

## TDD slice

Ownershipは`apps/mr-bot/lib/peatix-browser-provider.js`とmatching testの2 filesだけ。Production soft target 15–35 LOC、test 35–65 LOC。

RED:

1. Next click後にsame-event billingを経由し、8ms後にsame-event confirmへ遷移するfixtureを追加する。
2. 旧providerがform待ちで`form_navigation_failed`となることを再現する。
3. expectedはform inspect/fill/form-submit 0、confirm identity/validation、final 1、exact confirmed settlement、canonical parent registered。
4. billing停留、wrong-event confirm、malformed confirmはfinal 0。

GREEN:

- bounded waitの戻り値をexact `form|confirm|null`にする。
- `form`だけ既存form blockを実行し、common confirm blockへ合流する。
- existing form path、hidden Kana、settlement、pre-readback no-opを変更しない。

## Verification

- focused provider RED/GREEN
- Peatix workflow、production Harness、minimal runner/production/evidence、native contract adjacent
- syntax、`git diff --check`
- fresh Sol review Critical 0 / Important 0
- push後official wake exact 1回。registered candidateのpre-readback/evidence bundleまたはdirect-to-confirm→bundle、Meetup audit到達、Submit重複0を確認する。

実装結果: Luna REDはfocused provider 23/24で、billing→8ms same-event confirmの新規fixtureだけが旧form-only waitの`form_navigation_failed`を再現した。GREEN commit `967ff73c3`はprovider/test 2 filesだけで、Next後のstrict same-event `form|confirm`をbounded waitし、form時だけ既存attendee block、confirm時はcommon confirm/Kana/validation/final/confirmed/canonical readbackへ合流する。billing停留、wrong event、auth、query/hash、credential/port、unrelatedはfinal 0。Luna focused 24/24・adjacent 158/158、Sol独立expanded 160/160、syntax/diff check PASS。workflow 1 failureは既知の日付依存。fresh Sol reviewはCritical 0 / Important 0で`ship`。実装/review中のbrowser/provider/Calendar/evidence/Telegram/state/schedule作用0。
