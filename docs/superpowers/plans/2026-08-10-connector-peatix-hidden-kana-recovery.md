# Connector Peatix hidden Kana recovery plan

## Goal

Meetupより前のPeatixで実測した`peatix_kana_control_unavailable`三連続failureを、保存済みPeatix attendee profileを再入力しない最小変更で修復する。同じofficial wakeがPeatixを安全に完了または継続し、Meetup discoveryへ到達できる状態に戻す。

## Ponytail full gate

- 新module、provider abstraction、profile store、selector cache、retry、scheduleを追加しない。
- 既存`submitPeatixOnPage`とfocused testだけを変更する。
- private Kana値、display text、account IDをstate/log/test fixtureへ追加しない。
- hidden fieldを強制表示・fill・clickしない。既存form validationとparent readbackを再利用する。

## Live evidence

- official wake `wake-c86028333ac947edb19541de`はLuma、Connpass、Peatixまで進み、Peatix三候補で同じ`peatix_kana_control_unavailable`、failure count 3、circuit-open、Telegram positive ID `11375`。Meetup audit 0、bundle delta 0、process/owned target cleanup済み。
- 実候補三件のconfirm pageは`#confirm-form`、exact `[name="lastname_edit"]`と`[name="firstname_edit"]`を各1件持つ。
- 両fieldは親`.field-bundle { display:none }`内で0x0。既存profile displayの編集用controlであり、required=false。
- 三件とも`jQuery(#confirm-form).valid()`はtrue。したがって値欠落ではなく、visible-only locatorが保存済みcontrolをunavailableへ誤分類している。

## TDD slice

Ownership: `apps/mr-bot/lib/peatix-browser-provider.js`とmatching testの2 filesだけ。Production soft target 15–30 LOC、test 50–90 LOC。

RED first:

1. exact family/given各1件が両方hidden、confirm form validのfixtureはKana fill 0でfinal confirmへ進み、parent registered readbackを要求する。
2. visible exact pairは従来どおりparent-owned profile値を両方fillする。
3. zero、片側だけ、duplicate、visibility mismatch、disabled/non-fillable visible pairは`kana_control_unavailable`でfinal click 0。
4. hidden exact pairでもform invalidなら`confirm_validation_failed`でfinal click 0。

GREEN:

- exact pairのcountを先に検証する。
- visibilityが両方trueなら既存fillを行う。
- visibilityが両方falseならsaved valueを再入力せず既存jQuery validationへ進む。
- visibility mismatchとidentity/count ambiguityはfail closedを維持する。

## Verification

- focused Peatix browser provider RED/GREEN
- Peatix workflow、production Harness、minimal runner/productionのadjacent tests
- changed JS syntax、`git diff --check`
- fresh Sol review Critical 0 / Important 0
- commit/push後、schedule unloadedのofficial foreground wake exact 1回。Peatix同safe reason解消、Meetup audit到達または次exact safe boundary、Telegram positive ID、process/target cleanupを確認する。

## Follow-up D0b: confirmed settlement

Hidden Kana fix後のofficial wakeは三候補すべてでconfirm操作を越えた。候補`5086816`だけが約2秒後にstrict same-event `/sales/event/5086816/confirmed`へ遷移し、後続canonical pageのvisible same-event ticket linkとticket page QR shellで実registeredをread-only確認した。前二候補はconfirmed遷移もticketもない。

同じ2 filesで次のRED/GREENを追加する。

1. final click後のstrict `https://peatix.com/sales/event/<same-id>/confirmed`をboundedに待つ。wrong event、auth、query/fragment/credential/port、unrelated pathは受理しない。
2. exact confirmed後だけ同じpageでcanonical event URLへnavigateし、既存parent `readPeatixRegistrationStateOnPage`のsame-event ticket-link/marker readbackを行う。confirmed URL単独ではregisteredにしない。
3. confirmedが来ないfixtureはprovider submitを再実行せず、従来どおりsafe unavailable。wrong-event transitionもregisteredにしない。
4. delayed exact confirmed→canonical registeredのfixtureをREDにし、Submit/final click exact 1、registered exact 1を証明する。

実装結果: Luna REDはproduction未変更でfocused 22件中9 failureとなり、8ms delayed exact confirmedが旧即時readbackで`readback_unavailable`になること、malformed/missing confirmedがcanonical readbackへ進めないことを再現した。GREEN commit `e9f953eac`はproduction/testの同じ2 filesだけで、strict same-event confirmedを30秒bounded waitし、exact confirmed後だけ同じpageをcanonical eventへ戻して既存parent readbackを行う。final clickはexact 1、timeout/malformed/wrong/authは再click 0、confirmed単独は成功0。Luna focused 22/22、Harness 55/55、runner 36/36、minimal production 12/12、Sol独立expanded 125/125、syntax/diff checkがPASS。fresh Sol reviewはCritical 0 / Important 0で`ship`。PlaywrightのURL objectで同一authority/pathへ正規化される明示default port・empty credential・dot-segmentは別URL受理ではなく、click失敗時waiterは外部作用0・same-event限定・30秒回収と確認した。実装/review中のbrowser/provider/Calendar/evidence/Telegram/state/schedule作用0。
