# Connector O1B-05 Confirmation Mail Implementation Plan

> Status: 実行中。O1B-04の同一eventだけをGmail確認mailへ結ぶ。

**Goal:** `Engineer BAR`の実Luma登録後に届いた確認mailを既存`gog` Gmail OAuthで取得し、message ID・受信時刻・送信元・event URLをregistration receiptへ照合する。

## Constraints

- `keiodaisuke@gmail.com`の既存OAuthを使い、別mail transportを作らない。
- 登録完了時刻より前のmail、別event、曖昧な件名を証拠にしない。
- code、mail本文、cookie、token、guest keyをspec/evidenceへ保存しない。
- Gmail queryは全pageまたはterminal cursorまで読む。
- O1B-05ではQR生成やTelegram送信を先取りしない。

### Task 1: Mail discovery and exact match

- [ ] 登録時刻以降のLuma mailをGmailで検索する。
- [ ] message metadataとsanitized contentからevent URL/titleを照合する。
- [ ] 同一event以外を拒否するfixture testをRED→GREENにする。

### Task 2: Durable evidence

- [ ] tenant/job/eventへboundしたconfirmation-mail receiptを保存する。
- [ ] secretなしlive evidenceを保存する。
- [ ] O1B-05完了、spec更新、commit、push。
