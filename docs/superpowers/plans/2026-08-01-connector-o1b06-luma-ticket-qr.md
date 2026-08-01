# Connector O1B-06 Luma Ticket QR Implementation Plan

> Status: 完了。O1B-04/O1B-05と同一の`Engineer BAR`公式QRだけを検証・保存・再読出しした。

**Goal:** 照合済みGmail confirmationからguest-specific ticketをmemory内だけで取得し、Daisが会場で開ける実QR PNGをtenant/job/eventへboundして保存する。

## Constraints

- guest key、ticket URL、mail本文、cookie、tokenをlog、spec、evidence、job payloadへ保存しない。
- exact O1B-05 Gmail message、event URL、tenant、job、attemptのbindingを外さない。
- guest keyはGmailから同一processのmemoryへ読み、平文fileへ永続化しない。
- QRはPNG signature、最小size、content hash、tenant ownershipを検証する。
- Luma公式ticket pageにprovider生成QRがある場合は、そのpayloadを推測して自作しない。
- O1B-06ではTelegram送信を先取りしない。送信はO1B-07でpositive message IDまで検証する。

### Task 1: Provider ticket inspection

- [x] 既存CloakBrowser `:9222`の同一sessionで`マイチケット`を開く。
- [x] provider生成QRの有無と取得可能なartifact形を、secretを表示せず実測する。

実測: Lumaは200×200 SVGの公式QRを表示する。decode payloadはイベントURLではなく
`https://luma.com/check-in/<opaque>?pk=<guest key>`で、確認mail内guest keyとSHA-256が一致した。
したがって旧specの「event URLを自前QR化」は採用せず、公式SVGをPNG captureして検証する。

### Task 2: Exact extraction and QR artifact

- [x] 同一event以外、異なるguest key、guest key欠落を拒否するfixture testをRED→GREENにする。
- [x] guest-specific ticketをopaque secretとしてmemory内だけで扱う。
- [x] 実QR PNGをtenant/job/event bound objectとして保存・再読出しする。

### Task 3: Proof and handoff

- [x] secretなしlive evidenceを保存する。
- [x] O1B-06完了、spec更新、commit、push。
- [x] O1B-07へ実QR artifact refだけを渡す。
