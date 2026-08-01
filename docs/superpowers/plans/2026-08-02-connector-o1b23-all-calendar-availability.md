# O1B-23 all-calendar availability 実装計画

**Goal:** Google Calendarの全calendarを完全に読み、busy unionとevent前後の移動時間に衝突しない候補だけを予約可能にする。

## Contract

- local gog transportは`calendar freebusy --all`をstrict readし、primary限定を禁止する。
- 一calendarでもprovider errorなら空きと見なさず全availabilityをfail closedする。
- 全busy intervalを時系列mergeする。
- candidateの`start - travel_before`から`end + travel_after`までを占有区間として判定する。
- window外、壊れた時刻、busy衝突候補をeligibleにしない。

## Steps

1. 全calendar argv、provider error、前後buffer衝突、free候補をRED testで固定する。
2. gog transport methodとavailability evaluatorを実装する。
3. privacy-safe live shape readbackとcontrolled interval readback、全回帰を実行する。
4. evidence、spec、残数、commit/pushを完了する。
