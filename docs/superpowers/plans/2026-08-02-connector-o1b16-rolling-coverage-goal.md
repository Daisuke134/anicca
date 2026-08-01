# O1B-16 rolling 21日coverage goal 実装計画

**Goal:** 実行時点のTokyo暦日を起点に今日〜20日後を毎回作り直し、現在証拠がない日をopenへ戻す21日coverage goalを実装する。

## Contract

- `now`をAsia/Tokyoへ変換したlocal dateをwindow startにする。
- 連続21暦日を生成し、endはstart+20日。JST 00:00で一日rollする。
- current observationだけからcovered_existing / covered_new / unavailableを置き、残りはopenを導出する。
- status observationは証拠ref必須。explicit open、重複日、未知statusは拒否する。
- completeは21日のopenが0の時だけtrue。

## Steps

1. JST日跨ぎ、月跨ぎ、再計算、cancel→open、集計をtest-firstでREDにする。
2. pure rolling goal builderを実装しoutbound suiteへ固定する。
3. current時刻と翌JST日でcontrolled readbackし、windowが一日進むことを証拠化する。
4. 全回帰、正本spec、残数、commit/pushを完了する。
