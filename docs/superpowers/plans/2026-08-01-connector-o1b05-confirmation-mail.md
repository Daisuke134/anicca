# Connector O1B-05 Confirmation Mail Implementation Plan

> Status: 完了。O1B-04の同一eventだけをGmail確認mailへ結合し、runtime volumeから再読出しした。

**Goal:** `Engineer BAR`の実Luma登録後に届いた確認mailを既存`gog` Gmail OAuthで取得し、message ID・受信時刻・送信元・event URLをregistration receiptへ照合する。

## Constraints

- `redacted@example.invalid`の既存OAuthを使い、別mail transportを作らない。
- 同一registration attempt開始前、完了から30分超、別event、曖昧な件名を証拠にしない。
- Lumaはsubmit受理時にmailを送り、その後workerが完了画面を検証してjobを完了する。したがってmail受信がjob完了より数秒早い正常系を拒否しない。
- code、mail本文、cookie、token、guest keyをspec/evidenceへ保存しない。
- Gmail queryは全pageまたはterminal cursorまで読む。
- O1B-05ではQR生成やTelegram送信を先取りしない。

### Task 1: Mail discovery and exact match

- [x] 同一registration attempt内のLuma mailをGmailで検索する。
- [x] message metadataとsanitized contentからevent URL/titleを照合する。
- [x] 同一event以外を拒否するfixture testをRED→GREENにする。

### Task 2: Durable evidence

- [x] tenant/job/eventへboundしたconfirmation-mail receiptを保存する。
- [x] secretなしlive evidenceを保存する。
- [x] O1B-05完了、spec更新、commit、push。
