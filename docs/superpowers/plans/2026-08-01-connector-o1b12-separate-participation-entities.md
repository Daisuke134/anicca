# Connector O1B12 — 一般参加と登壇応募のentity分離 plan

## 目的

同じeventに一般参加ticketとLT/CFP/demo応募が併存しても、別ID・別action URL・別stateとしてdurableに追跡する。
一般参加のreceiptを登壇応募成功へ流用すること、または登壇応募formを一般参加予約として実行することを禁止する。

## 固定境界

- 共通なのはtenantとcanonical event referenceだけ
- `audience_registration`と`talk_application`は別entity ID
- 一般参加の状態: `discovered / registration_queued / registered / waitlist / cancelled`
- 登壇応募の状態: `discovered / submission_queued / submitted / accepted / rejected / withdrawn / presented`
- 登壇応募のavailability: `open / closed / invite_only / not_offered / unknown`
- raw event body、氏名、email、cookie、form回答は保存せず、referenceとbounded metadataだけ保存
- state transition ledgerはO1B15、accepted後timelineはO1B14で追加する

## TDD

1. `both`判定からexactly two entityが生成され、IDとaction URLが混ざらないREDを追加
2. audience-only、talk-only、closed/invite-only、invalid reference、cross-tenant collisionのREDを追加
3. entity builderとPostgreSQL storeを実装
4. migrationでkind別state制約とtenant-scoped unique keyを固定
5. focused test、outbound全体、migration静的監査を実行
6. non-secret evidenceと正本specを更新し、commit・push

## 完了条件

- 一つの`both` eventから二つのdurable rowが得られる
- audience receiptでtalk stateは変わらない
- talk form URLはaudience registration actionへ入らない
- closed/invite-only talkは追跡されるが送信可能にはならない
- raw identityやsecretをrowへ保存できない
