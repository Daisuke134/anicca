# O1B-15 登壇応募ledger 実装計画

**Goal:** talk applicationごとのsubmitted、accepted、rejected、presentedを、外部receiptに束縛したappend-only ledgerへexactly-onceで記録する。

## Contract

- talk applicationの正規transitionだけからledger entryを作る。
- 4 statusはすべて外部receipt必須。silenceや推測でaccepted/rejected/presentedへ進めない。
- ledger IDはtenant、entity、version、status、receiptから決定し、exact replayだけ成功させる。
- 一つのapplication/status、一つのreceiptはtenant内で一度だけ。
- RLS、service-role SELECT/INSERT onlyで更新・削除を通常runtimeへ公開しない。

## Steps

1. entry builder、store、migrationをtest-firstでREDにする。
2. rejected receipt gateを既存state machineへ追加し、append-only ledgerを実装する。
3. local PostgreSQLでsubmitted→accepted→presentedと別rejected応募を保存・再読出しする。
4. 全回帰、evidence、正本spec、残数、commit/pushを完了する。
