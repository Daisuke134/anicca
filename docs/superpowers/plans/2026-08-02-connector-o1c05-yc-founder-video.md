# O1C-05 YC founder video 検証・upload計画

**Goal:** application-kitの58秒英語founder videoだけをFall 2026 draftへuploadし、保存後readbackする。

## Contract

- sourceは`application-kit://videos/Anicca_intro_EN.mp4`に限定する。
- durationは0秒超60秒以下、sizeは100,000,000 bytes以下、MP4/H.264/AAC、video/audio各1本以上を要求する。
- artifact SHA-256とprobe factsをupload planへ束縛する。
- 現行`:9222`の既存contextでfile inputへ一度だけ設定し、`Save & back`だけを押す。Submitは押さない。
- fresh video pageでrequired状態が消え、保存済み動画が存在する場合だけ完了する。

## Steps

1. 適格58秒版と、79秒・151MB・codec/source不正をRED testで固定する。
2. founder video upload plan builderを実装する。
3. 実draftへ一度upload/saveし、fresh pageでreadbackする。
4. 全回帰、evidence、spec、残数、commit/pushを完了する。
