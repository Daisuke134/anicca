# O1B-14 採択後登壇timeline 実装計画

**Goal:** 採択済みtalk applicationについて、採択証拠、slide締切、会場QR、登壇開始、follow-upを一つのtenant-bound timelineで追跡する。

## Contract

- `talk_application/accepted`と採択receiptが揃うまでtimelineを作らない。
- accepted、slide deadline、ticket QR、talk start、follow-upを時系列順で固定する。
- QRはopaque artifact refだけ、会場は表示用文字列、日時はoffset付きinstantだけを保存する。
- stable timeline IDとPostgreSQL unique keyで再実行を重複させない。
- timelineはservice-only/RLSでtenant境界を守る。

## Steps

1. builder/store/migration contractをtest-firstでREDにする。
2. timeline builder、store、additive migration、local compose wiringを実装する。
3. controlled accepted entityをlocal PostgreSQLへ保存し、5 milestoneを読み戻す。
4. 回帰、evidence、正本spec、残数、commit/pushを完了する。
