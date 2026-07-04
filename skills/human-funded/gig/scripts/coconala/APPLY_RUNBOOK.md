# ココナラ 公開依頼 応募 runbook (= 実証済 2026-06-29、 every AI 用)

人が投稿した公開依頼に、 ポートフォリオ添付付きで no-human 応募するまでの正確な手順。
mtdc account (Dais Google login、 KYC+MUFG 済) で request 5121769 (PowerPointテンプレ) に実応募して確立。

## 前提
- login: coconala.com/login → Developer 不要、 「Googleでログイン」 → Daisuke account 選択 → 続行(次へ)
  - daily-driver (:9222) に Daisuke Google session 生存。 mtdc account に入る。
- driver: CloakBrowser daily-driver を CDP (:9222) で。 ★ 1 つの固定 tab を最後まで使う (tab drift 厳禁) ★
- ★ CDP 注意: navigation の度に websocket が切れる → 1 ステップ1 接続 + recv に asyncio.wait_for(timeout) + 例外耐性。 daily-driver が tab 多数で過負荷だと evaluate が固まる → 余計な tab を閉じる ★

## 手順 (= /offers/add/{requestId})
1. request 開く: coconala.com/requests/{id}
2. 緑「応募する」 を ★ 実マウス click (Input.dispatchMouseEvent 座標) ★ → /offers/add/{id} へ (= 404 が出たら未ログイン。 Google再login)
3. 提案内容 textarea `data[Offer][content]` = ★ 募集要件を満たす提案 ★ (自己紹介のみ禁止)。 React setter (HTMLTextAreaElement value setter + input/change event) で OK
4. 提案金額 `data[Offer][price]` = setter で数値 (最低 4,000 円〜)
5. ★ 納品予定日 (必須) = datepicker を **実マウス click** で: 日付欄 click → ▶ で対象月 → 日を実click ★。
   - ❗ JS .click() や value setter は **model に commit されず** validation で「設定してください」 になる → 必ず実マウス click で日セルを選ぶ
6. ★ ファイル添付 (ポートフォリオ=歓迎、 採用の決め手) ★:
   - 「ファイルを添付する」(クリップ) を ★ 実マウス click ★ → その後 CDP `DOM.setFileInputFiles({backendNodeId or nodeId, files:[path]})` で input にセット → ファイル名 chip が表示されれば成功
   - ❗ synthetic change event だけだと Vue が拾わない。 実click + setFileInputFiles の併用で chip 表示を確認
   - 合計 100MB まで、 5 枠。 .pptx (本体) を ファイル1 に
7. 「確認する」 を click → ★ validation エラー(ピンク帯「入力情報を確認して下さい」)が出たら 必須未入力 (大抵 date の commit 漏れ) → 5 をやり直し ★
8. 確認ページ (応募する のみ・確認するは消える) → 「応募する」 click → ★ 最終モーダル「投稿前にご確認ください」★ → モーダル内「応募する」 を click = 真の提出
9. ★ E2E verify ★: request の tab title が「応募内容を確認する | ココナラ」 に変化 (= 応募済の時のみ) + 応募人数 +1 + mypage/offers に表示。 /json の title だけでも applied 確認可

## 成果物品質 (= 競合プロに勝つ、 vcsdd で実証)
- ★ PPTX/資料は 公式 `pptx` skill (html2pptx: HTML/CSS設計→.pptx) を使う。 raw python-pptx は地味/低品質で負ける ★
- ★ 自分の output を自分の目で render して見る (thumbnail.py) → 欠陥(低コントラスト/空枠/順序/breadth)を発見 ★
- ★ vcsdd fresh-context adversary を PASS まで loop (maker≠checker)。 採用率%・読みやすさ・ブリーフ適合を harsh 判定 ★
- テンプレ案件は「再利用キット」 として 表紙+目次+セクション扉+本文複数+表 など 6-7 レイアウトで breadth を出す

## 信頼ループ (= 稼ぎ切るまで、 放置しない)
応募 → トークルーム watch (gog gmail で coconala 通知 poll) → 即返信 → 仮払い → 納品 → 高評価 → リピート。
詳細 spec: docs/superpowers/specs/2026-06-29-coconala-profit-loop-design.md
