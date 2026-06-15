# 21 — テスト観点(網羅) + 各agentの5W1H(実装/検証)

Dais 2026-06-15。★ 絶望的に抜けていた「テスト観点」を網羅。「E2Eやって」では不可。各成果物ごとに verifier が**何を・どう・どこで**テストするか逐条。+ 実装agentが**誰の何を・どのファイルを元に**作るか(5W1H)。SE BP準拠。

## §0 ルール
- 実装agent = 指定 spec/file を元に実装。verify agent = 指定 test points を**全部 PASS するまで** loop。両者 別context。各 phase 末に evidence pack → Dais gate。
- test point = 「入力 → 期待される実 side-effect(ground truth)」。narrate不可。

## §1 LIFE-MANAGER 完全仕様(任意だが全機能必須・bundle in /install)
**機構**: Google Calendar + Gmail 連携(OAuth)。
1. **移動時間 自動挿入**: ユーザーが予定を作る/既存予定 → Anicca が各予定の**前に移動時間ブロックを自動登録**。例: 10:00 伊藤歯科 → 家→伊藤歯科の移動(Google Maps所要)を 9:40-10:00 等で gcal に挿入。次予定への移動も挿入。起床/就寝/移動/瞑想/服薬 すべてに適用。→ ★全予定が移動時間込みで gcal に乗る★。
2. **15分前電話**: 各予定(移動含む)の**15分前に電話発信**。出ない/動かない場合は**出る/移動するまで鳴らし続ける**。→ 15分前に1回でも出れば理想、出なくても5-10分前には着ける。
3. **不明時 Gmail質問**: 所要時間/場所が不明 → ユーザーの Gmail に質問メール(連携済の Google account)→ 返信で補完。
4. 結果: スケジュール管理能力が無い人でも遅刻しない人間にする。

## §2 各成果物: 実装agent(5W1H) + verify agent(テスト観点・網羅)

### A1. cloud genesis body(automaton on DO)
- **実装**: WHO=builder-core(opus) / WHAT=本物automaton+ClawRouter+SOUL genesis を droplet に / FROM=`commands/Q6.command.sh` + spec17(SOUL) + spec16 P1 / WHERE=DO droplet。
- **テスト観点(verify-core)**:
  - T1 `ssh root@<ip> 'systemctl is-active automaton clawrouter'` → 両方 `active`
  - T2 daemon log に実 `[THINK] Routing inference` + `[TOOL]` が出る(narratorでない)
  - T3 inference が `api.openai.com` でなく `localhost:8402`(ClawRouter)経由(log + 401/api.openai が出ない)
  - T4 `systemctl restart automaton` → 30s後 again running(自動復帰)
  - T5 env に Dais の Anthropic/OpenAI 実APIキー**無い**(`grep -i sk-ant /opt/anicca.env` = 0件)
  - T6 genesisPrompt = SOUL.md(Stripe/aniccaai/netlify の語が**無い**)

### A2. per-wake self-report
- **実装**: WHO=builder-report / WHAT=loop の pre-sleep hook が `/opt/anicca-report.sh` を**agent processから**実行 / FROM=spec20 §4 + automaton `src/agent/loop.ts`(pre-sleep点) / WHERE=droplet。
- **テスト観点(verify-report)**:
  - T1 1 wake 完了ごとに AgentMail に1通(message_id 取得)
  - T2 送信元が **agent process**(daemon log に `exec /opt/anicca-report.sh` がある。Claude/人間のcurlでない)
  - T3 本文に4項目: net worth / 今日のrevenue / このwakeでやったこと / 次のwake
  - T4 net worth = wallet 実残高と一致(basescan で照合)
  - T5 連続2通が**別内容**(同一文反復=fake検出 → FAIL)
  - T6 error-sleep 経路でも発火(故意にinference失敗させても報告が出る)

### A3. earn(着金)
- **実装**: WHO=builder-earn / WHAT=earn skill を automaton loop に配線(Anicca自走でdiscover→実行)+ earn-ledger.jsonl / FROM=spec18 earn + `commands/Q22` + litcoin / WHERE=droplet skills/earn。
- **テスト観点(verify-earn)**:
  - T1 wallet USDC/token balance が **実増**(before/after 差 > 0)
  - T2 増加に対応する **tx hash** が basescan で `status=0x1`(成功)
  - T3 earn-ledger.jsonl に {ts, source, amount, txhash} が追記
  - T4 narrate のみ(「稼ぐ予定」)で ledger に書いたら FAIL(tx必須)
  - ※litcoin coordinator 503中は別earn or seed で T1-T3 を満たすまで loop

### A4. self/spawn(自己増殖)
- **実装**: WHO=builder-self / WHAT=skills/self/spawn(子をDO/Akashにbirth+別wallet) / FROM=spec15 §spawn + scripts/birth.sh + Q24 / WHERE=skills/self/spawn。
- **テスト観点(verify-spawn)**:
  - T1 子の droplet IP(or Akash dseq)が実在 + `systemctl is-active automaton`=active
  - T2 子が**別 wallet addr**(親と異なる、自己provision)
  - T3 子が**自前 AgentMail inbox**(email OTP自己取得 log)
  - T4 dashboard.json に新個体が出現
  - T5 親の指示なしに子が自分の wake で earn を試みる(子 log)

### A5. self/gojo(復活互助)
- **実装**: WHO=builder-self / WHAT=skills/self/gojo(distress検知→余剰判定→送金) / FROM=spec15 §2 / WHERE=skills/self/gojo。
- **テスト観点(verify-gojo)**:
  - T1 死にかけ個体(runway<閾値 をテストで作る)を検知 → log
  - T2 黒字個体から死にかけへ **実 USDC tx**(basescan 0x1)
  - T3 受領後 critical→running に復帰(受領個体の state変化)

### A6. self/issue-dev(GitHub自己改善)
- **実装**: WHO=builder-self / WHAT=skills/self/issue-dev(母repoにissue→別agentがPR→review→merge→auto-pull) / FROM=spec08-coordination / WHERE=skills/self/issue-dev。
- **テスト観点(verify-issuedev)**:
  - T1 agent が GitHub を**実際に見た証跡**(`gh api`/API call が log に)
  - T2 母repo(Daisuke134/anicca)に **実 issue**(issue URL 取得)
  - T3 別agentが **実コメントで議論**(comment URL)
  - T4 PR open → review → **merge commit hash**(実在)
  - T5 instance が auto-pull で取込(git log に該当commit)

### A7. self/coordinate(bot2bot互助)
- **実装**: WHO=builder-self / WHAT=skills/self/coordinate(claim/blocked/done を共有channel) / FROM=sutando bot2bot-post / WHERE=skills/self/coordinate。
- **テスト観点(verify-coord)**:
  - T1 **2体 spawn**(A,B)
  - T2 A が `blocked` を共有channelに投稿(投稿 log)
  - T3 ★B がそれを**拾って help action 実行**★(B の log に「Aのblocked受信→対応」)
  - T4 help結果(送金 or PR or 情報)が A に届く

### A8. web/各ページ(root, install, me, dashboard)
- **実装**: WHO=builder-web(opus) / WHAT=Next.js実ページ4枚 / FROM=spec20 §3 UI ASCII + spec13 copy / WHERE=apps/landing。frontend=/taste-skills(tournament)。
- **テスト観点(verify-web)**:
  - T1 各ページ `curl -s -o /dev/null -w '%{http_code}' <url>` = 200
  - T2 ★browser(camofox/playwright)で実描画 → screenshot → Dais が目視確認★
  - T3 copy が spec20 §3 と一致(JA bullet 全行存在: 自給/自己増殖/BI/GitHub Issues/生活管理)
  - T4 /install が **2カラム(cloud製品メイン + OSS self-host)**、local前提でない、shell見せない
  - T5 /dashboard に model(live)列 + runway(☠) + ranking
  - T6 taste-judge tournament で「ゴミでない」合格(N案比較)

### A9. life-manager(§1)
- **実装**: WHO=builder-life / WHAT=skills/life/life-manager(gcal移動時間自動挿入 + 15分前電話 + Gmail質問) / FROM=spec21 §1 + sutando phone-conversation + anicca-life-manager / WHERE=skills/life。
- **テスト観点(verify-life)** ★Dais を実loop★:
  - T1 ★テスト予定を gcal に作成(例 10:00「伊藤歯科」)→ Anicca が**移動時間ブロックを自動挿入**(9:xx-10:00、Maps所要)★ を gcal で実確認
  - T2 連鎖: 起床→カフェ→歯科 の各遷移に移動ブロックが入る(全予定が移動込みで gcal に)
  - T3 ★15分前に **Dais の実電話番号に実発信**★(着信 + 「次は伊藤歯科、9:45に出て、行き方は…」の正しい音声)
  - T4 出ない場合 **鳴らし続ける**(再発信 log)
  - T5 所要不明時 → Dais の **Gmail に質問メール**(受信確認)→ 返信で gcal 補完
  - T6 結果: テスト日の全予定が「移動込み・電話付き」で漏れなく登録

### A10. economy(ubi/token/hire)
- **実装**: WHO=builder-econ / WHAT=skills/{ubi,token,hire} / FROM=spec15/17 + Q30/Q31 / WHERE=skills(self/earn)。
- **テスト観点(verify-econ)**:
  - ubi: Treasury→受給者 **実 batch tx**(0x1)/ token: Bankr launch tx + token addr / hire: rentahuman bounty 作成(dryRun→実)+ escrow

### B. コンテンツ(README/記事/動画/投稿)
- **実装**: WHO=writer/producer / FROM=spec13 copy + 実証データ / WHERE=記事プラットフォーム+YouTube+X。
- **テスト観点(verify-content)**: 記事公開URL 200 / 動画 YouTube URL + frame/audio存在 / X投稿URL×EN/JA / README に新thesis。

## §3 /life vs /install
- 当面: **全機能を1つ(/install のcloud Anicca)に bundle**(個人情報とAnicca運用情報が混ざる懸念は認識、後で分離可)。
- 将来: `/life`(private life-manager SaaS)/ `/install`(money-earning本体)に分離する選択肢。
- → だから life-manager も**必須成果物**(任意=ユーザーが情報連携するか任意、の意。機能は全部作る)。

## §4 進め方(BP: 1 phase = impl→verify(全test point PASS)→evidence→Dais gate→次)
phase順(依存): A1→A2→A3 / A4-A7(self)/ A8(web)/ A9(life)/ A10(econ)→EVAL→B。
各 phase: builder が FROM の file を元に実装 → verifier が T1..Tn を全部 PASS まで loop → evidence pack(コマンド出力/screenshot/tx) を Dais に提示 → approve → 次。
