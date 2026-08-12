# Connector Peatix optional privacy control plan

## Goal

実Peatix formで主催者privacy checkboxが表示されない場合も、private attendee profileの
`accept_organizer_privacy: true`を維持したまま、final confirm直前まで安全に進める。

## Measured failure

- official wake: `wake-f75b5ddac08c7f35ff9f6a46`
- account dashboard readback: attending ticket count 0
- event `5086816` form: required visible name 1、email 1、unknown 0、privacy control 0
- direct outcome: `unavailable / privacy_control_unavailable`
- final confirm click、Calendar、PNG、applied bundle: 0

## Ponytail scope

- change files soft target: 2
- production LOC soft target: 5以下
- test LOC soft target: 15以下
- reuse: existing Peatix form parser、profile consent、control helper、TDD fixture
- defer: Browser Harness拡張、safe reason persistence、recovery、他provider

## TDD slice

1. RED: privacy control 0、name/email各1のformがconfirm stepまで進み、final click後のregistered fixtureを返すcontractを追加する。
2. GREEN: profile consent `true`は必須のまま、privacy control 0を許可する。1なら既存check、2以上はfail-closed。
3. Regression: invalid profile、unknown required field、missing/duplicate name/email、複数privacy、cross-event confirm、ambiguous readbackでfinal effect 0を維持する。
4. Verify: focused provider/workflow/native/minimal production回帰、syntax、diff check。
5. Fresh review後だけofficial foreground runnerを再実行する。dashboard ticket count 0をpreconditionとし、scheduleはunloadedを維持する。

## Live acceptance

同一official runner lineageでPeatix parent readback `registered`、Calendar独立readback、full-page PNG/SHA、
provider receipt、Telegram message/photo positive IDs、immutable applied bundleを得る。どれか欠けたら成功にしない。
