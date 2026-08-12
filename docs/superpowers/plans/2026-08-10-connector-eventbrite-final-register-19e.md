# Connector Eventbrite final Register plan (Item 19E-D4d)

## Goal

Eventbrite attendee exact4 fields完了・既知marketing全OFF後の最終`Register`をsame official checkout frameのsame original buttonへexact 1回だけ発行し、既存Eventbrite `readProviderState`がofficial parent detailから`registered`を確定した場合だけsuccessにする。click後の不明状態は`effect_unknown`として再送を禁止する。

## Ponytail gate / size

- 既存attendee inspector、event-bound token、stable ElementHandle、`startFinalEffectWait`、Eventbrite workflow readbackを再利用する。新service/DB/queue/retry manager/selector fallbackは作らない。
- Harness production/test exact 2 files。production 55–90 LOC、test 90–150 LOCをsoft targetにする。不可逆clickのidentity/race/readback境界だけを実装する。
- factory/runFallback/native provider order/evidenceは次sliceへdeferし、このsliceのlive acceptanceは明示的なisolated Harness 1回だけにする。

## Exact observation and identity contract

1. parent URLはcandidate canonical exact、official child frameはorigin/path/eid一致のexact1、attendee required controlsは既知4件exact・全completed、known marketing inputsは0/1 each・全optional/visible/enabled/unchecked、unknown required 0。
2. final primary raw candidateは`data-testid=eds-modal__primary-button` exact1、`button[type=button]`、label exact `Register`、visible/enabled/connected。これ以外、duplicate/fuzzy/hidden/disabled/detached/101+はfinal control 0。
3. final control tokenは`eventbrite_attendee_register_<sameEventId>`。上記全条件成立時だけprimaryへbindする。
4. attendee final observationはexact4 completed attendee controls＋final exact1、marketing action control 0。他control混入はfinal action不可。

## Exact action contract

1. final tokenは`purpose=submit / method=ax_click`だけを許可する。private resolverは0。
2. operation直前にsame parent canonical、same official child frame/eid、same exact4 completion、marketing all OFF、final exact1を再inspectする。
3. operatorはfinal token＋testidを持つlocatorからElementHandle exact1を一度取得し、same handleのtoken/testid/tag/type/text/visible/enabled/connectedを検証する。locator count exact1とsame handle再検査後、same handleのPlaywright `click()`をexact1回だけ呼ぶ。lazy locator click、coordinate/keyboard submit、DOM click/property assignmentは0。
4. readback loopはclick開始直前に既存`startFinalEffectWait`をarmedにし、Eventbrite workflow `readProviderState`をparent page/candidateへpollする。`registered`だけをsuccessとしてprovider_stateを返す。
5. click throw/non-success、parent/frame/button drift after arming、readback absent/unavailable/error/timeoutは`failed / safe_reason=effect_unknown`。click再実行0。pre-operation failureはclick 0・通常failed。

## TDD

1. RED: exact final observationがactionableとなり、same original handle click1、resolver0、readback registeredでsuccess/provider_stateを返す。
2. RED: click後readback absent/unavailable/timeoutはeffect_unknown、click1。operator throw/non-successもreadbackがregisteredならsuccess、未確定ならeffect_unknown。
3. token/testid/tag/type/text/visibility/enabled/connected/handle/count/page/frame/eid/DOM drift、decoy swap、duplicate primary、marketing re-check、attendee incompleteはpre-operation click0。
4. final handle clickで別ticket/label/marketing/decoy controlのeffect 0を回帰化する。runFallback/factory/native/evidence作用0。
5. focused Harness、Eventbrite/minimal-production/adapter adjacent、syntax、`git diff --check`、exact 2-file ownership、4 labels unloadedを検証する。
6. fresh Sol review Critical/Important 0後にstableへ統合する。

## Live acceptance

1. 実Google Calendarでconflict 0を再確認した既知Eventbrite candidateだけを使う。
2. production Harnessでtop CTA→ticket→exact4 fill→marketing OFF→final Registerを順に行う。ticket timeout/effect_unknown時は再clickせず、同じframeの遅延attendee遷移を待つ。
3. final click exact1後、official readbackがregisteredを返すこと、completion marker、Calendar/evidence/Telegramはこのsliceではまだ作らないことを記録する。
4. owned diagnostic pageだけをcleanupし、unrelated pagesを閉じない。schedule 4 labelsはUNLOADEDを維持する。

## Deferred

Eventbrite workflow injection、full runFallback、native `DEFAULT_PROVIDERS`、Calendar creation、PNG/evidence/Telegram、実`applied_bundle`、schedule load。
