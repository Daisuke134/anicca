# ココナラ 公開依頼 応募 runbook (= 実証済 2026-06-29、 every AI 用)

人が投稿した公開依頼へ、ポートフォリオ添付付きでno-human応募する手順。
接続済みcredentialを持つ実accountでE2E確認済み。

## 前提
- login: 接続済みcredentialからauthenticated daily-driver sessionを復元する。
- driver: CloakBrowser daily-driver を CDP (:9222) で。 ★ 1 つの固定 tab を最後まで使う (tab drift 厳禁) ★
- ★ CDP 注意: navigation の度に websocket が切れる → 1 ステップ1 接続 + recv に asyncio.wait_for(timeout) + 例外耐性。 daily-driver が tab 多数で過負荷だと evaluate が固まる → 余計な tab を閉じる ★

## 手順 (= /offers/add/{requestId})
1. request 開く: coconala.com/requests/{id}
2. 緑「応募する」はクリックしない。Vue event 経由は実測で無反応になることがあるため、同じ lease の ws を使い、code-owned helper で正規 route `/offers/add/{id}` を直接開く:
   `python3 "$GIG_DIR/scripts/cdp_nav_snapshot.py" open-application --ws "$WS" --request-id "$REQUEST_ID" --screenshot "$EVIDENCE_DIR/gig-${PASS_ID##*-}-B2-${REQUEST_ID}-form.png" --evidence "$EVIDENCE_DIR/gig-${PASS_ID##*-}-B2-${REQUEST_ID}-form.json"`
   `ok=true` かつ `form_verified=true`（提案内容・価格・納品予定日・確認するの4 control）を確認してから入力へ進む。404/login/field欠落は応募成功ではない。
3. 提案内容 textarea `data[Offer][content]` = ★ 募集要件を満たす提案 ★ (自己紹介のみ禁止)。 React setter (HTMLTextAreaElement value setter + input/change event) で OK
4. 提案金額 `data[Offer][price]` = setter で数値 (最低 4,000 円〜)
5. ★ 納品予定日 (必須) = datepicker を **実マウス click** で: 日付欄 click → ▶ で対象月 → 日を実click ★。
   - ❗ JS .click() や value setter は **model に commit されず** validation で「設定してください」 になる → 必ず実マウス click で日セルを選ぶ
6. ★ ファイル添付 (ポートフォリオ=歓迎、 採用の決め手) ★:
   - 「ファイルを添付する」(クリップ) を ★ 実マウス click ★ → その後 CDP `DOM.setFileInputFiles({backendNodeId or nodeId, files:[path]})` で input にセット → ファイル名 chip が表示されれば成功
   - ❗ synthetic change event だけだと Vue が拾わない。 実click + setFileInputFiles の併用で chip 表示を確認
   - 合計 100MB まで、 5 枠。 .pptx (本体) を ファイル1 に
7. ★ 入力後は確認・応募ボタンを手動で押さない ★。同じ leased ws を渡して code-owned helper を実行:
   `python3 "$GIG_DIR/scripts/cdp_nav_snapshot.py" submit-application --ws "$WS" --request-id "$REQUEST_ID" --screenshot "$EVIDENCE_ROOT/gig-$PASS_ID-B2-${REQUEST_ID}-submitted.png" --evidence "$EVIDENCE_DIR/gig-${PASS_ID##*-}-B2-${REQUEST_ID}-submitted.json"`
   helper が「確認する」→確認ページ「応募する」→最終モーダル `js_ignite-submit`「応募する」を実マウスで順に押す。validation error、ボタン消失、別URLは失敗。
8. ★ E2E verify ★: `/mypage/job_matching/applied/offers` への遷移と画面内「応募しました」を両方確認した時だけ `ok=true, submit_verified=true, applied_page_verified=true`。その後にだけ submitted.png を作る。モーダルのスクショを submitted と命名してはいけない。
9. 親passも独立して応募履歴を再読し、台帳の `applied_page_verified=true` を付ける。helper証跡・親readback・台帳の3点が揃って初めて実応募。

## 成果物品質 (= 競合プロに勝つ、 vcsdd で実証)
- ★ PPTX/資料は 公式 `pptx` skill (html2pptx: HTML/CSS設計→.pptx) を使う。 raw python-pptx は地味/低品質で負ける ★
- ★ 自分の output を自分の目で render して見る (thumbnail.py) → 欠陥(低コントラスト/空枠/順序/breadth)を発見 ★
- ★ vcsdd fresh-context adversary を PASS まで loop (maker≠checker)。 採用率%・読みやすさ・ブリーフ適合を harsh 判定 ★
- テンプレ案件は「再利用キット」 として 表紙+目次+セクション扉+本文複数+表 など 6-7 レイアウトで breadth を出す

## 信頼ループ (= 稼ぎ切るまで、 放置しない)
応募 → トークルーム watch (gog gmail で coconala 通知 poll) → 即返信 → 仮払い → 納品 → 高評価 → リピート。
詳細 spec: docs/superpowers/specs/2026-06-29-coconala-profit-loop-design.md
