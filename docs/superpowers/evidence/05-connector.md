# #5 connector / booking loop — Evidence

正本: spec §8 #5 / §10 #5 / §10 1a-b。Dais の要求(2026-07-11): 毎日 gcal を見て→Luma/connpass の FREE crypto×ai イベントを予約→gcal に追加→Telegram 報告、double-booking なし。私はループを設計→監視→再イテレート（手動予約はしない）。

## VERIFIED ground truth (2026-07-11 05:0x JST, gog で独立読返し)
Dais gcal 今後8日 = 10 events。AI/agent 系は2件のみ:
- **"Agents That Earn"** loc=Tokyo Innovation Base, luma.com/atfpxptu, created 2026-06-30 → **Dais 自身がホスト**（ループ成果でない）
- **"AI Agents Night"** loc=銀座ベルビア館, luma.com/wrajak50, created **2026-07-10 12:58Z** → 実 venue+URL の実登録。だが**それ以降・来週の新規予約はゼロ**
- 他は [Travel] 自動ブロック / 瞑想 / 養成所 / MUIT 出社。
- 全 event が `-07:00`(Pacific) offset 表示 = カレンダー TZ が JST でない疑い（Dais が「空/おかしい」と感じる一因）。

## 症状の確定
- **毎日 新規 free イベントを予約する日次ストリームが機能していない**（Dais の訴えと一致）。
- connector cron `ad89027d`(anicca-connector-daily, 35 7 * * * Asia/Tokyo) は **runs 0**（一度も自動発火せず、初回=本日 07:35 JST）。手動 day-1 pass は scout 1 URL のみで**1件も予約せず**。
- ⚠️ cron announce に「Delivering to Telegram requires target」警告 → Telegram 報告経路の設定不備疑い。

## 深掘り調査中（root cause 確定待ち）
- connector 1 pass の実 step 図: gcal 読 / Luma・connpass FREE 検索 / 実 RSVP / gcal CONFIRMED 書込 / Telegram — のどこが未実装 or gate skip か。STEP2 outreach 封鎖が booking/RSVP まで巻き込んでいないか。
- gcal TZ が Pacific な件の是正要否。

## 確定 root cause（実コード精読、2026-07-11）— 3層の詰まり
connector 本体 = `~/profitable-claude/skills/human-funded/connector/`（cron ad89027d は外側 restart トリガーのみ、core は tmux で常駐し 03:12 に pass 完了実績あり=cron 未発火は無関係）。
- **A（主因）**: `connector-signals.py` の `horizon_full` = 「その日 confirmed イベント≥1 = まる1日満杯」。毎日再発する `🧘 Meditation(06:00-07:00)` が horizon 全15日に乗り全日 full → `horizon_full:true` → STARTUP 規約「horizon_full なら STEP1 を丸ごと skip」で**実登録+gcal 書込の唯一 step が毎回 skip**。自然に直らない。spec REQ-CON-006/013 にも同じ誤定義。
- **B（複合）**: STEP1 の唯一許可経路 `event_apply_wrapper.py`(REQ-CON-024 I-confirm gate) は env `CONNECTOR_APPLY_RAIL_OVERRIDE`(rail script)必須だが**本番で未設定**→常に `no-apply-rail-configured` refuse。しかも `apply.py` は「実登録=agent が camofox で行う(サイト毎にフォーム違い hardcode 不可)」設計。→ script-rail と agent-browser が噛み合わず**両方未配線**=生涯 applications.jsonl 0 バイト。
- **C（副次）**: `telegram_payload.py` は JSON 組立のみ送信コード無し + cron chatId 未設定 → 日報が Dais に届いてるか疑わしい。
- **棄却仮説**（証拠付き）: STEP2 outreach 封鎖は別ゲートで STEP1 を巻き込まない / registry live・pause でない / anicca-booking 二重loop は disabled 済。
- ✅ double-booking 回避は `gcal_write.py`(insert 前 re-check + insert 後 get 検証) で既に実装済、A/B 解けば機能。

## 確定設計（Dais 委任、CLAUDE.md judgment-to-model + apply.py 設計意図に整合）
1. **A 修正**: `connector-signals.py::read_horizon_gaps` の horizon_full を「9:00–22:00 JST に ≥90 分の連続 free block が無い日のみ full」に再定義（瞑想/短時間 travel は日を埋めない）。spec REQ-CON-006/013 も改訂。
2. **B 修正（登録を実配線）**: 登録は **connector core agent が CloakBrowser(:9222 daily-driver)で実 RSVP**（Luma=email OTP via `gog gmail`、connpass=login）→ 登録確認 text + snapshot を evidence 化。`event_apply_wrapper.py` を「rail script subprocess 必須」から「I-confirm gate + **実登録 evidence(registration_evidence_text 非空 + snapshot 実在 + url 一致)検証**して applications.jsonl 記録し registered:true」に再設計（prod rail = evidence 検証器 `apply-rail-prod.py` を `CONNECTOR_APPLY_RAIL_OVERRIDE` に設定 + connector-cli.sh STARTUP に「登録は agent が browser で行い evidence を渡す」を明記）。FREE-only 厳守(evidence_gate.py)、outreach STEP2 は封鎖のまま。
3. **C 修正**: STARTUP に実送信(`openclaw message send --channel telegram --target 8547730585 …` or telegram-notify.sh)を明記 + cron target 設定。
4. **TZ**: gcal 表示が Pacific offset の件は別途 Dais カレンダー設定確認(副次)。
5. 私はループを直す→core 再起動→実 pass を監視→翌日 iterate（手動予約しない）。reliable な autonomous RSVP は iterate 対象（OTP/login/サイト差）。


## 実装→検証→push→live 起動で判明した3層目の blocker（2026-07-11）
- コード修正(horizon/FREE/evidence/TZ)は **builder GREEN→fresh Opus adversary PASS→push(profitable-claude main 6ac4c64)** 完了。
- 決定的確認: 新 horizon で `horizon_full=False, gaps=11`（瞑想で全日満杯だったのが空き11日）、CloakBrowser :9222 ALIVE。
- **live 起動で3層目の blocker 判明**: connector core(tmux claude) は **手動 `connector-cli.sh` だと生きて動く**が、**launchd healthcheck 環境では spawn 直後に即 DEAD**（`connector-core-healthcheck.log` に "started (DEAD)" 連発、60分5回で backoff 停止）。launchd out/err log は空。→ **autonomous に pass が完走しない=コードを直しても毎日予約されない真の理由**。
- self-heal request(`~/.openclaw/state/.connector-core-selfheal-request.json`) が「connector-core DEAD、自分で診断して直せ」と残っている。
- ⚠️ **systemic**: 同じ「healthcheck が claude core を spawn」方式の explorer/life-manager core にも波及しうる。これは self-heal 苦情(loop が死んで backoff で諦める)の核心と直結。
- → crash-loop 根因(launchd env vs interactive)修正＋実 booking 完走を fresh agent に委譲中。結果を gcal `events get` で独立検証する。

## 現状の正直なまとめ
- ✅ コード3詰まりは修正・検証・push 済（fabrication/有料登録を防ぐ形で）。
- ✅ FREE 構造強制・evidence 本物検証で「捏造/有料を gcal に書く」事故を未然に防止（adversary が捕捉）。
- 🔄 残: core が launchd で生き残れない crash-loop を直す→初の実 booking を gcal CONFIRMED で観測→7日 streak。


## 2 runtime blocker 修正後の live 検証（2026-07-11 07:00 JST・正直な到達点）
2つの runtime blocker を発見・修正（「コードは正しいのに autonomous で回らない」の真犯人）:
1. **launchd PATH に `$HOME/.local/bin` 欠落** → `claude` 解決不能で core 即死(crash-loop)。fix commit 2d753b7(connector+colony)。healthcheck が ALIVE に変化して実証。
2. **`ANTHROPIC_API_KEY` 検出の対話プロンプトで headless core 無限停止**（"use this API key? 1.Yes 2.No" に誰も答えず 0 pass）。fix: connector-cli.sh の core spawn を `env -u ANTHROPIC_API_KEY` に（OAuth subscription 強制、~/.claude/.credentials.json 有り、human-funded 構成に整合）。**検証: core が プロンプト通過し STEP0-5 を実行するのを transcript で確認**。

live 検証結果（transcript 実読）: core が STEP2(outreach draft)✔ / STEP3(debrief)✔ / STEP4(scout, 実 finding: IndieHackers "7 autonomous AI agents")✔ を完走。**STEP1(free イベント発見+CloakBrowser で実 RSVP)は turn 終了までに未完**（applications.jsonl=0、gcal 新規なし）。

### 正直な到達点
- ✅ コード3層(horizon/FREE/evidence/TZ) + 2 runtime blocker(PATH/API-key prompt) 全修正・検証・push 済。core は健全に STEP0-5 を回すようになった。
- ❌ **まだ実 booking ゼロ**。STEP1 のブラウザ RSVP（イベント発見→CloakBrowser→OTP/login→登録確認 evidence）が単一 pass turn で完走しないのが残る iterate 点。
- 次: STEP1 のブラウザ登録を完走させる（turn budget/専用サブフロー or 07:35 JST cron の autonomous 実行を観測して iterate）。届いたら `gog calendar events get` で独立読返し。
- ⚠️ 残ノイズ: core の claude session に `node:...cjs/loader:1458` PreToolUse hook error（non-blocking、commands は実行できている）。要調査だが blocker ではない。


## 🎉 初の実 BOOKING 成功（2026-07-11 07:16 JST、独立読返し確認）
2 runtime blocker(PATH/API-key prompt)修正後の pass が **end-to-end で実登録完走**:
- **イベント**: 松尾研 GENIAC-PRIZE 2026 AI基盤モデル開発コンテスト 説明会（connpass event/399133）、2026-07-13 19:30-21:00 JST、**無料**、一般参加枠。
- **独立検証**: `gog calendar events list --from 2026-07-13` で **event_id d27fulks5hb2st09u0ckpg759o が gcal に実在確認**（agent 自己申告でなく私が読返し）。application の id/時刻と一致。
- **登録 evidence**: `connpass.com/event/399133/join/complete/`（申し込み完了ページ、登録後のみ到達する URL）+ 140KB 実スクショ(snapshot_path 実在)。
- horizon-fill 正常: 空き夜枠に配置、day job/瞑想を回避。FREE-only 正しく強制。double-book なし。
- healthcheck: connector-core ALIVE+fresh(健全)。

### 正直な caveat / 残 iterate
- connpass 登録自体は agent-reported（evidence gate 通過: 実 PNG≥5KB + 無料判定 + complete-URL 一致）。gcal 側は私が独立読返しで確認済。connpass 再ログイン検証まではしていない（adversary FIND-001 non-blocking の honest-limit、evidence 品質は高い）。
- gcal event の**タイトルが raw URL**（"...join/complete/ — イベント申し込みが完了しました..."）＝醜い。イベント名にすべき（cosmetic iterate）。
- これは1件（7日 streak の Day1）。§10 #5 Done は7日連続 + 各日 Telegram delivered。streak 継続と Telegram 実送信の確認が残る。


## #5 streak 残検証項目（2026-07-11 記録）
- **Telegram delivered 経路 = VERIFIED**（2026-07-11 実送信テスト）: `openclaw message send --channel telegram --target 8547730585` が **Message ID: 1879 で Dais に実着信**。telegram-notify.sh(211 cron 共通の経路)はこれのラッパで、connector STARTUP(REQ-CON-103)に配線済み。→ 機構は確実に届く。各日 pass の実 delivery(delivered:true)は streak 進行中に per-pass 確認する（agent が STARTUP 指示通り送る前提、信頼性を上げるなら deterministic post-pass send 化が次の改善)。
- **7日 streak**: Day1(GENIAC 予約)成功。Day2-7 は connector が毎日 autonomous に走る（runtime 土台修正済）が、各日の FREE 実登録 or 正直 none + Telegram delivered + fresh adversary PASS が §10 Done。multi-day で継続。
