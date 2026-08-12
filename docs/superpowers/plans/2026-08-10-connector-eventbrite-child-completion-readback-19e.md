# Connector Eventbrite child completion readback plan (Item 19E-D4d2)

## Goal

最終Register exact1後にofficial checkout childへ表示される実completionを`registered`としてreadbackする。既にfinal clickは1回発行済みで、再clickは0。保持中の実pageをread-only再判定してsuccess proofを得る。

## Measured effect

- parent URL/canonical relはcandidate exact、parent CTAは残るため旧parent-only readbackは`absent`。
- direct childはofficial `https://www.eventbrite.com/checkout-external?...&eid=1997468673573` exact1でparentはcandidate detail。
- direct child本文は`Thanks for your order!` exact1、`YOU'RE GOING TO` exact1、final `Register` 0、required invalid 0。
- nested checkout descendantsが2件あるがcompletion 0。readbackはmain-frame direct childだけを対象にする。
- screenshotとsafe DOM countで実registration済みを確認。再click禁止。

## Ponytail gate / size

- Eventbrite workflow production/test exact 2 files。production 35–60 LOC、test 50–90 LOC。
- 既存`readProviderState`へsafe booleanを追加するだけ。receipt parser、別service、DB、screenshot OCR、retryは作らない。

## Exact contract

1. default readerはpage URL exactと既存parent canonical/CTA summaryに加え、`page.mainFrame()`のdirect childrenだけをboundedに読む。
2. official child identityはHTTPS、host `www.eventbrite.com`、port/user/password/hashなし、path exact `/checkout-external`、query `eid` exact1/candidate event ID一致。
3. direct official checkout child 0なら既存parent absent/registered判定を使う。1件ならidentity一致を必須にする。2件以上、wrong/duplicate eid、wrong parentはambiguousで`unavailable`。
4. exact child内で`Thanks for your order!` exact1、`YOU'RE GOING TO` exact1、label exact `Register` button 0のときだけ`checkout_completion=true`。本文・email・order IDはparentへ返さない。
5. parent canonical rel exact1＋checkout_completion=trueだけを`registered`とする。completion 0/2、片方のみ、Register残留、evaluate errorはregisteredにしない。
6. click/action/fill/marketing/factory/native/evidence作用0。このsliceはread-only。

## TDD / verification

1. RED: real-shape frame tree（main→direct official completion→nested official blank2）でregistered期待。現行はparent CTAによりabsent。
2. wrong eid、duplicate direct official、nested-only completion、thanks-only、going-only、Register残留、frame evaluate errorはunavailableまたは非registered。
3. pre-registration parent exact＋direct checkout form completion0はabsentを維持する。
4. Eventbrite workflow focused、Harness/minimal-production adjacent、syntax/diff/exact2 scope、schedule unloaded。
5. fresh Sol review Critical/Important 0後にpushし、保持中の実registered pageへworkflowを再実行して`registered`を確認する。final click 0追加。

## Deferred

factory/runFallback/native provider order、Calendar creation、PNG/evidence/Telegram `applied_bundle`、schedule load。
