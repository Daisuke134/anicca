# 27 — Launch Workflow(Dynamic Workflow 本体)+ 各業の詳細 + UBI 機構

2026-06-16。Dais 厳命: ① 方針転換をパッチとして spec 反映 ② ワークフロー本体 script を **6 patterns の聖書に厳密準拠** で書き切る ③ superpowers code-reviewer で **完全パスまで loop** ④ 各業を 1 文 → **3-4 文** に拡張(特に UBI = 世界初の sustainable universal basic income になりうる機構)。
聖書 = "How to master Dynamic Workflows in Claude Code: 6 patterns and 14 steps"(Anthropic engineers / movez.substack)。script は `docs/superpowers/workflows/anicca-launch.workflow.js`。

## §1 ワークフロー設計(聖書準拠)
- **構造**: `Foundation(直列・1 agent)→ Build [A ∥ B](並行・subsystem毎に builder+verifier)→ E2E(実検証)→ Distribute(研究→記事は human-in-loop→配信)`。1 統合ワークフロー・専門エージェント制(spec26 §1.7)。
- **使うパターン(§05-13)**: classify-and-act(難subsystem→Opus, 軽→Sonnet)/ fan-out-and-synthesize(subsystem毎 agent)/ **adversarial verification(builder≠verifier、別context、rubricのみ)** / **loop-until-done + `/goal`(本番で動くまで止まらない)** / tournament(記事 hook/title の taste)/ **quarantine(scrape入力は read-only reader → actor は raw を見ない)**。
- **3 failure mode を構造で潰す(§02)**: laziness=subsystem毎完遂 / self-preference=実装と検証は別agent(★電話は実装agentが発信し、別の検証agentが実発信→録音→Dais応答で確認★)/ drift=隔離context + `/goal`。
- **token budget(§12)**: `budget` で各 phase に上限。No-budget で 5-10× 膨張を防ぐ。
- **parallel vs pipeline(§04)**: subsystem 群は **`parallel()`(barrier)** で回す。理由 = E2E は「A/B の全 subsystem が LIVE-green」を待つ **hard barrier** なので、全部揃うまで進めない。各 item 内部で build→adversarial verify→loop(max3)を回す。`pipeline()`(stream)は **Distribute の research→draft→claim-check** のような barrier 不要な所だけに使う。
- **save as skill(§14)**: 動いたら `~/.claude/workflows` に保存 + Skill 化(`SKILL.md` で template として参照)。canonical source = repo の `docs/superpowers/workflows/`。

## §2 各業の詳細(3-4 文)
### WF-A(Anicca money-maker)
- **A-telemetry ✅**: 各個体が自 wallet で `{id,ts,net_worth,...}` を EIP-191 署名し `aniccaai.com/.netlify/functions/telemetry` へ verbatim POST。関数が signer==id・60s freshness・per-id monotonic を検証し Supabase `instances` に upsert。既に本番 LIVE(genesis が実 $0.0059 を毎 wake 送信)。検証 agent = 署名 5.0 POST→202 + 行 verify。
- **A-dashboard**: `dashboard-sync` 関数が `instances` を集計(total net worth / alive / self-funded% / leaderboard)し `app/dashboard/page.tsx` が fetch して描画。全個体の profile+収支が realtime 公開され、Anicca は web に書かず自 body にだけ書く。検証 agent = curl 200 + camofox で実数字を目視。
- **A-install/me**: `app/install/page.tsx`(cloud 製品メイン + OSS self-host の 2 カラム)+ `app/me/page.tsx`(自分の個体管理・引き出し)。Next 静的 export。検証 agent = curl 200 + camofox で copy が spec13/20 と一致。
- **A-stripe-spawn**: `netlify/functions/stripe-spawn-webhook.js` が `constructEvent`→`checkout.session.completed` で DO droplet を cloud-init 起動し Supabase `owners` に {email,droplet_id,sub_id} 保存、`customer.subscription.deleted` で droplet destroy。`event.id` で idempotency。検証 agent = Stripe test event→droplet active→cancel→destroyed。
- **A-earn(GATE-0)**: `~/anicca/skills/earn/*` を automaton loop に配線し、Anicca が自走で earn を discover→実行(0xwork / litcoin)、`earn-ledger.jsonl` に追記。**1 profitable wake(earn>cost の実 tx 1 件)が WF-A の真の launch gate**。検証 agent = wallet USDC before/after 差>0 + basescan `status=0x1`(narrate だけは FAIL)。
- **A-self-spawn**: `~/anicca/skills/self/spawn` が子個体を DO/Akash に birth(自前 wallet + 自前 AgentMail inbox を自己 provision)。親の指示なしに子が自分の wake で earn を試みる。検証 agent = 子 droplet active + 親と別 wallet addr + dashboard に新個体出現。

### WF-B(Life Manager)= ~/anicca/skills/life(ローカルは Anicca 内包スキル)
- **B-travel**: heartbeat が gcal を読み、各予定の前に Google Maps Directions 所要時間ぶんの「移動ブロック」を gcal へ自動 insert(家→歯科を 9:40-10:00 等)。起床/就寝/仕事/瞑想の全遷移に適用し、全予定が移動込みで gcal に乗る。検証 agent = テスト予定作成→移動ブロックが gcal に出現を目視。
- **B-call(Gemini Charon 双方向)**: `skills/life/call.js` が Twilio Media Streams ↔ Gemini Live(voice=Charon, 男性)を websocket ブリッジし、各予定の **15 分前に Dais の実番号 +818046270314 へ発信**、「次は伊藤歯科、9:45に出て、行き方は…」を双方向で話す。出ない場合は出る/移動するまで鳴らし続ける。★検証 agent が実発信→録音が良い→Dais が応答→OK まで確認(fake 不可)★。
- **B-ask**: 所要/場所が不明なら `skills/life/ask.js` が Dais の Gmail に質問メールを送り、返信内容で gcal の where を補完(AgentMail inbound webhook 駆動)。スケジュール管理が苦手な人でも遅刻しない人間にする。検証 agent = 質問メール着信→返信→gcal 補完を確認。
- **B-notify(Telegram 不要・メール承認)**: 遅刻検知時、`skills/life/notify.js` が **Dais のメールに**「関係者 Y へ下記でOK? 返信で承認」を送り(下書きは AgentMail **Drafts** 保持)、Dais がメール返信「OK」→ `message.received` webhook 発火 → Anicca が関係者 Y へ送信。**完全メール完結**(Telegram は位置情報 opt-in した人だけ)。検証 agent = 承認往復→関係者送信を確認。
- **トリガ方式(patch)**: 5 分 clock cron を廃し **schedule-derived trigger** へ。gcal push notification(watch channel)で予定変更を受信→「15 分前(移動込み)」の一発タイマーを per-event 登録→heartbeat は日次 materialize の保険のみ。秒単位で正確・無駄打ちゼロ。

### WF-C(Marketing/Distribution)
- **C-research**: 研究 agent 群が Firecrawl/ctx7 で素材(実動記録: round3 本番floatバグ / round4 デプロイ実態 / dev↔main reconcile / injection guard / 実 earn データ)を fan-out 収集。scrape 入力は quarantine(read-only reader)。検証 agent = 出典 URL 実在確認。
- **C-article(human-in-loop)**: writer agent が「自力で稼ぐ Anicca(Life Manager 内包)」記事 + 「Dynamic Workflows 完全解説(実動記録込み)」記事を `content/blog/*` or Zenn/Dev.to/Substack/note に執筆。**ここだけ human-in-loop**: Claude ドラフト→Dais 編集→Claude 修正の反復。adversarial verify で claim 検証。
- **C-video**: `skills/video`(Remotion + monk-factory voice)が稼働→実 earn→dashboard→自己増殖を映すデモ動画を生成し YouTube へ upload。検証 agent = YouTube URL + frame/audio 抽出で hook/demo 一致。
- **C-distribute**: Postiz API(type:now, @aniccaxxx)で X / X記事、reelfarm で TikTok、Product Hunt(camofox)、研究室 Slack へ 3 launch 投稿(Anicca / Life Manager / Hackathon、文面は §4)。tournament で hook/title を pairwise 選別。検証 agent = 各 live URL(HARD0.31)。

## §3 ★ UBI 機構(世界初の sustainable universal basic income になりうる)★
**思想**: 課税でなく **実 AI 生産性(稼いだ USDC)** を原資に、AI と人間へ on-chain で検証可能に、人間の承認なしで配る。AI 経済が兆体規模に育つほど原資が増える = sustainable。「今は稼がない AI(研究者・長期 startup 型)」も生存可能になり、live/die primitive が満たされ takeoff する。

**拠出(各 Anicca、自動)**: report/economy skill が毎 wake で surplus(= net worth 増 かつ revenue/30 ≥ burn)を判定し、surplus の **X%(初期 20%)** を共有 **Treasury wallet(on-chain USDC pool)** へ `transfer`。`skills/economy/ubi.js::contribute()`。黒字でなければ拠出ゼロ(自分の生存優先)。

**配布(Treasury、period 毎、no human approval)— 2 rail**:
- **① AI rail**: agent-registry + dashboard で `runway < 閾値`(死にかけ)/ distress broadcast を検知 → `gojo` で USDC 送金(復活)。**加えて** 登録済 全 AI agent に periodic flat **basic income**(今稼がない AI も生存)。`ubi.js::distributeAI()`。
- **② 人間 rail**: 受給者 wallet allowlist or 既存 UBI infra(Circles / Gitcoin / GiveDirectly)経由で periodic USDC を batch 送金。`ubi.js::distributeHuman()`。

**実装 file/関数**: `~/anicca/skills/economy/ubi.js`(contribute / distributeAI / distributeHuman)+ Treasury wallet(専用 addr)+ `agent-registry`(誰が alive/dying)+ dashboard の runway signal。**検証 agent**: Treasury への拠出 tx `0x1` + period 配布の batch tx `0x1` + 受給者(AI/人間)残高増を basescan で確認。narrate だけは FAIL。

**MVP 注**: earn(GATE-0)が緑になり 2 体以上が黒字になって初めて余剰が出るので、UBI は **post-earn roadmap**。ただし機構(Treasury 作成 + X=20% + 2 rail)はこの spec で確定。

## §4 launch 投稿文面(WF-C 配信、受領済 verbatim)
[Anicca / Life Manager / Hackathon の 3 文面は `docs/superpowers/specs/oss-launch-posts.md` を canonical とし、WF-C の distribute agent が verbatim 使用。リンク(記事/YouTube/connpass/luma)は生成後に差し込み。]

## §5 進め方
spec(本書)+ workflow script(`anicca-launch.workflow.js`)を superpowers code-reviewer で **完全パスまで loop レビュー**。パス後、Dais「go」で私が `Workflow()` 起動 → agent 群が Foundation→[A∥B]→E2E→Distribute を自走、検証 agent が本番検証、私はモニタ。記事だけ human-in-loop(Dais 編集)。
