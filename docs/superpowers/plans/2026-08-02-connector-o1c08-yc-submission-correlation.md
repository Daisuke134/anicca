# O1C-08 YC提出receipt照合計画

**Goal:** YC home、確認mail、append-only ledger、Telegram ACKを一つのFall 2026 submissionへ照合する。

## Contract

- exact draft UUID、YC `In review`、公式sender、exact subject/body、DKIM/SPF/DMARC passを要求する。
- Gmail message/thread IDとinternalDateを保存し、recipient/body全文や認証headerはledgerへ保存しない。
- receiptはtenant-bound、append-only、idempotent exact replayのみ許可する。
- 日本語Telegramを一通だけ送り、positive provider message IDがある場合だけ配信済みにする。
- O1C-07の提出effectを再実行しない。

## Steps

1. home/mail相関、spoof拒否、store、TelegramをRED testで固定する。
2. receipt builder、store、migration、Telegram deliveryを実装する。
3. 実Gmail/homeをledgerへ記録し、既存Dais targetへ一通送る。
4. 全回帰、evidence、spec、残数、commit/pushを完了する。
