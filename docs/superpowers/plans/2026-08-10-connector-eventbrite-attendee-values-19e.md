# Connector Eventbrite attendee private-value plan (Item 19E-D4b2a)

## Goal

観測済みEventbrite attendee exact4 controlsへ、既存frozen attendee profileのgiven/family/emailをexact対応する。ブラウザfill、checkbox、final Register、provider effect、evidenceはこのsliceで0件。

## Ponytail gate / size

- 新しいprofile/env/secret reader/provider serviceは作らず、既存`createPrivateValueResolver`と`readPeatixProfile` boundaryを再利用する。
- Harness production/test 2 filesのみ。soft targetはproduction 10–20 LOC、test 20–35 LOC、total 30–55 LOC。
- 汎用name inferenceやlabel fuzzy matchを追加しない。

## Ownership

- `apps/mr-bot/lib/connector-production-browser-harness.js`
- `apps/mr-bot/lib/connector-production-browser-harness.test.js`

## Exact contract

1. `provider === "eventbrite"`かつexact labelだけを対応する: `First name`→`given_name`、`Last name`→`family_name`、`Email` / `Confirm email`→同じ`email`。
2. controlは既存`safeControl`を通り、kindは`input`、required true、completed false、submittable falseでなければnull。
3. attendee profileはobjectかつ該当値がtrim済みnon-empty bounded stringでなければnull。resolverは値をtrim・分割・推測・case変換しない。
4. wrong provider、unknown/fuzzy/case variant label、checkbox/radio、completed field、missing profile/valueはnull。
5. private値をlog、error、observation、test name、specへ出さない。テスト値はfixtureだけを使う。
6. 既存Peatix/Connpass/Luma resolver behaviorは変えない。

## TDD / verification

1. RED: fixture profileでexact4 mapping、confirm-email equality、case/fuzzy/unknown/completed/missing fail closedを追加し旧実装のgiven/family誤対応を確認する。
2. GREEN: Eventbrite exact branchをresolverへ最小追加する。
3. Harness focused、native-entrypoint/minimal-production adjacent、syntax、`git diff --check`、exact2-file scope、private literal scan、cleanを確認する。

## Deferred

same-frame operation、TOCTOU再検査、post-fill completed確認、final Register、registered readback、factory/runFallback/native provider order、evidence/Telegram、schedule load。
