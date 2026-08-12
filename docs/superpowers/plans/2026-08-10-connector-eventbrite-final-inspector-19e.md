# Connector Eventbrite final-control inspector plan (Item 19E-D4c1)

## Goal

Eventbrite attendee exact4 fieldsがすべてcompletedになったsame-event frameで、実測primary final controlをread-only公開する。このsliceのfinal click、provider effect、readback、evidenceは0件。

## Ponytail gate / size

- 既存attendee inspectorとstrict visibilityを拡張し、新規file/service/workflowは作らない。
- Harness production/test 2 filesのみ。soft target production 20–35 LOC、test 25–40 LOC、total 45–75 LOC。
- final action/readbackを同時実装しない。まずDOM契約だけを確定する。

## Exact observation contract

1. 既存parent canonical、official child exact1/eid、ticket card gone、required exact4 contractを全て維持する。
2. exact4 fieldsがすべて`completed=true`のときだけfinal controlを追加公開する。1件でもincompleteならfields 4件だけでfinal control 0。
3. primary raw candidateはcase-sensitive exact `[data-testid="eds-modal__primary-button"]` total1、tag `button`、type `button`、visible、enabled、label exact `Register`を要求する。duplicate、wrong testid/tag/type/label、hidden/detached/disabledはfinal control 0。
4. marketing opt-in checkboxes `organizationMarketingOptIn`と`ebMarketingOptIn`は、存在する場合visible/enabled/optional/uncheckedでなければfinal control 0。checked、required、duplicateはfinal control 0。操作・bindはしない。
5. final tokenは`eventbrite_attendee_register_<eventId>`、kind button、label Register、required false、completed false、submittable true。primary DOMへtokenをbindしないためclick pathは0。
6. observationはprivate valuesを返さず、既存4 fields＋final controlの最大5件。101+ fail closedを維持する。
7. `performAction`はfinal tokenを引き続きfailedとし、resolve/operate/final-effect 0。

## TDD / verification

1. RED: exact4 completed＋exact primaryで5 controlsを期待し現行4を確認する。
2. incomplete、duplicate/wrong/hidden/disabled primary、marketing checked/required/duplicate、performAction0の最小table regressionを追加する。
3. GREEN: attendee inspector内のread-only final candidate判定だけを追加する。
4. Harness focused、Eventbrite/minimal/operations/registry/native adjacent、syntax、`git diff --check`、exact2 scope、cleanを確認する。

## Deferred

primary DOM binding、final click once、registered readback、effect-unknown reconciliation、factory/runFallback/native provider order、evidence/Telegram、schedule load、fresh live checkout acceptance。
