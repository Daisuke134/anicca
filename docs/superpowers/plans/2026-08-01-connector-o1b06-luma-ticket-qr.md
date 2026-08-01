# Connector O1B-06 Luma Ticket QR Implementation Plan

> Status: 実行中。O1B-04/O1B-05と同一の`Engineer BAR` ticketだけをQR artifactへ結ぶ。

**Goal:** 照合済みGmail confirmationからguest-specific ticketをmemory内だけで取得し、Daisが会場で開ける実QR PNGをtenant/job/eventへboundして保存する。

## Constraints

- guest key、ticket URL、mail本文、cookie、tokenをlog、spec、evidence、job payloadへ保存しない。
- exact O1B-05 Gmail message、event URL、tenant、job、attemptのbindingを外さない。
- guest keyはGmailから同一processのmemoryへ読み、平文fileへ永続化しない。
- QRはPNG signature、最小size、content hash、tenant ownershipを検証する。
- Luma公式ticket pageにprovider生成QRがある場合は、そのpayloadを推測して自作しない。
- O1B-06ではTelegram送信を先取りしない。送信はO1B-07でpositive message IDまで検証する。

### Task 1: Provider ticket inspection

- [ ] 既存CloakBrowser `:9222`の同一sessionで`マイチケット`を開く。
- [ ] provider生成QRの有無と取得可能なartifact形を、secretを表示せず実測する。

### Task 2: Exact extraction and QR artifact

- [ ] 同一event以外、異なるguest key、guest key欠落を拒否するfixture testをRED→GREENにする。
- [ ] guest-specific ticketをopaque secretとしてmemory内だけで扱う。
- [ ] 実QR PNGをtenant/job/event bound objectとして保存・再読出しする。

### Task 3: Proof and handoff

- [ ] secretなしlive evidenceを保存する。
- [ ] O1B-06完了、spec更新、commit、push。
- [ ] O1B-07へ実QR artifact refだけを渡す。
