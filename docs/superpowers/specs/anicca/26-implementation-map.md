# 26 — Implementation Map (どの業を / どのファイルで / どの機能で / どのコマンドで)

2026-06-16。Dais の「各業をどこで何をどう実現するか」を逐条化。UX(やりたいこと)→ 実装(file/function/command)の参照資料。telemetry pipeline が実証済みの雛形(spec/plan→review→TDD→PR to main→live E2E)。

## 0. 電話(Life Manager 稼働の証明)— Gemini Charon・双方向
- **要件(Dais)**: 毎日 Dais に電話 → **Gemini Live の Charon(男性ボイス)で双方向対話** ができること。これが「Life Manager が毎日動いている」証明。
- **既存資産**: `TWILIO_*`(発信番号あり)+ `GEMINI_API_KEY` + skills `elevenlabs-calls`/`calendar-event-call`/`anicca-phone`/`telnyx-autocall`。ただし現状の発話は **ElevenLabs(JP voice)** で Gemini Charon ではない。
- **実装(new, WF-B B3)**: `~/anicca/skills/life/call.js` = **Twilio Media Streams ↔ Gemini Live(model `gemini-2.0-flash-live`, voice `Charon`)双方向ブリッジ**。Twilio が PSTN 発信 → `<Connect><Stream>` で音声を websocket に → Gemini Live が STT+LLM+TTS(Charon)を一気通貫 → 音声を Twilio に戻す。公開エンドポイント(Netlify function or 軽量 ws サーバ)が要る。
  - 代替: PatterAI/Patter(Gemini Live + carrier 抽象)。ただし Telnyx/Plivo の carrier 契約が新規に要るので、まず **既存 Twilio + Gemini Live** で最短実装。
- **検証(E2E)**: `+818046270314`(Dais)に実発信 → 着信 → Charon で「次は伊藤歯科、9:45に出て」等を双方向で話す → Dais OK + 録音確認。**fake 不可**(HARD 0.24/0.31)。

---

## WF-A — Anicca money-maker (`/install`)
| # | UX(やりたい) | file / function | command / verify |
|---|---|---|---|
| A1 | cloud で本物 automaton が稼働(ClawRouter, 人間鍵0) | droplet `/opt/automaton/dist/index.js` + `clawrouter` | `ssh root@147.182.225.255 'systemctl is-active automaton clawrouter'` = active ✅ |
| A2 | 毎wake 4項目を agent 自身が報告 | `/opt/anicca-report.sh`(canonical `~/anicca/skills/report/anicca-report.sh`)+ automaton pre-sleep hook(`index.js onStateChange` running→sleeping) | daemon log "report fired" + AgentMail 着信 ✅ |
| A8a | **telemetry**(各個体が署名 state を POST) | `apps/landing/netlify/functions/telemetry.js` + `_lib/{telemetry-verify,telemetry-store,telemetry-schema}.js` + Supabase `instances` | `node --test '…/__tests__/*.test.js'`(29) + 本番 `curl /telemetry`=405 / 署名POST=202 ✅ LIVE |
| A8b | **dashboard**(全個体P&L公開) | `netlify/functions/dashboard-sync.js`(集計)→ `apps/landing/app/dashboard/page.tsx`(new、`/.netlify/functions/dashboard-sync` を fetch) | curl 200 ✅ + page を camofox 目視(new) |
| A8c | **/install /me** ページ | `apps/landing/app/install/page.tsx` / `app/me/page.tsx`(new、Next 静的) | curl 200 + camofox |
| A8d | **Stripe→spawn**(課金で子体起動) | `netlify/functions/stripe-spawn-webhook.js`(new、`stripe-fashion-webhook.js` が雛形): `constructEvent`→`checkout.session.completed`→ DO droplet 作成(`DIGITALOCEAN_TOKEN`, Q6 cloud-init)→ Supabase `owners` upsert / `customer.subscription.deleted`→ droplet destroy。idempotency=`event.id` dedupe | Stripe test event → droplet active → cancel → destroyed |
| A3 | **earn(GATE-0 = 1 profitable wake)** | `~/anicca/skills/earn/*` を automaton loop に配線(0xwork / litcoin)+ `earn-ledger.jsonl` | wallet USDC before/after 差>0 + basescan tx `status=0x1`。★真の launch gate★ |
| A4 | **self-spawn**(自己増殖) | `~/anicca/skills/self/spawn`(子を DO/Akash に birth + 自前 wallet/AgentMail) | 子 droplet active + 親と別 wallet addr + dashboard に新個体 |

## WF-B — Life Manager (`/life-manager`)= ~/anicca の skill(ローカルは Anicca に内包)
| # | UX | file / function | command / verify |
|---|---|---|---|
| B-travel | 全予定の前に移動時間を gcal 自動 insert | `~/anicca/skills/life/travel.js`(gcal API 読込 → Google Maps Directions 所要 → 前に移動ブロック作成) | テスト予定作成 → gcal に移動ブロック出現(目視) |
| B-call | 各予定 15分前に電話(Gemini Charon 双方向) | `~/anicca/skills/life/call.js`(§0 の Twilio↔Gemini Live ブリッジ)+ heartbeat が gcal を見て 15分前に発火 | 実発信 → 双方向対話 → Dais OK + 録音 |
| B-ask | 所要/場所 不明 → Gmail で質問 → 返信で補完 | `~/anicca/skills/life/ask.js`(AgentMail/Gmail send → webhook 受信 → gcal 補完) | 質問メール着信 → 返信 → gcal に where 記入 |
| B-notify | **遅刻時、関係者へ承認後連絡**(↓§詳細) | `~/anicca/skills/life/notify.js` | Telegram 承認 → 関係者へ送信 |

### B-notify の具体フロー(Dais の質問への答え)— draft→approve→send
1. **検知**: heartbeat が gcal を監視。「次予定 start − now − 移動所要 < 0」or「B-call で N 回不応答」→ *late risk* と判定。
2. **関係者の連絡先特定**: その gcal event の attendees(招待者の email)→ 無ければ contacts map / 過去スレッド。不明なら B-ask と同様に Dais に Telegram で「誰に連絡?」と聞く。
3. **下書き生成**: agent が連絡文(例「10:00 の打合せに 10分遅れます、◯◯」)を作る。
4. **★承認ゲート(Telegram)★**: `TELEGRAM_BOT_TOKEN` の bot が **Dais に** 「予定X に遅れそう。関係者 Y(email)へ下記を送ってOK?」+ 文面 + [承認/修正] を送る。← 承認は **Telegram**(Dais 向け・即応)。
5. **送信(承認後のみ)**: Dais が「OK」と返信 → agent が **AgentMail/Gmail で関係者 Y にメール送信**。← 実行は **email**(関係者向け)。
- = 参照 [AgentMail auto-reply](https://www.agentmail.to/docs/documentation/examples/auto-reply-agent) / [cloudflare/agentic-inbox](https://github.com/cloudflare/agentic-inbox) と同型(inbox webhook → agent → reply)だが、★ human-approval gate を Telegram で挟む ★ のが差分。AgentMail の **Drafts** を使えば「下書き保持→承認→send」がネイティブ。承認チャネル=Telegram、送信チャネル=AgentMail/Gmail。

## WF-C — Marketing / Distribution(A・B verify 後・直列)
| 成果物 | file / function | verify |
|---|---|---|
| 3 launch 投稿(Anicca / Life Manager / Hackathon、文面受領済) | Postiz API `type:now`(@aniccaxxx)+ 研究室 Slack + X記事 + TikTok + Product Hunt | 投稿URL live(HARD 0.31) |
| **Dynamic Workflows 解説記事**(実動記録: round3 本番floatバグ / round4 デプロイ実態 / dev↔main無関係履歴 / injection guard) | `apps/landing/content/blog/*` or Zenn/Dev.to/Substack/note。研究=全自動、執筆=Claude ドラフト→Dais 編集者レビュー(human-in-loop) | 記事URL 200 |
| demo 動画(後) | Remotion / hyperframe + monk-factory voice | frame/audio 存在 |

## 記事の分け方(1.5 の答え)
**Anicca 1本に統合**(Life Manager を内包)。理由: ローカルでは Life Manager は Anicca の skill。Web app では将来別ページだが統合予定。よって「自力で稼ぐ Anicca + その一機能として生活管理」を1記事に。Hackathon は別告知。

## A と B の重なり(1.7 の答え)— ★ 1 ワークフロー・専門エージェント ★
Dais の懸念(ローカル同一 repo で衝突)は正当。よって **別々の並行ワークフローにしない**。**1つの統合ワークフロー**にし、その中で:
1. **Foundation フェーズ(直列・最初)**: dev↔main reconcile + 共有 scaffold(`~/anicca` skill framework / install.sh / landing layout・nav / skills registry)を **1 エージェントが確定**。
2. **Fan-out フェーズ(専門エージェント・並行)**: 同一ワークフロー内で **Anicca 担当エージェント**(A8c/A8d/A3/A4 = disjoint files)と **Life Manager 担当エージェント**(B-travel/call/ask/notify = `skills/life/*`)が並行。★衝突防止は runtime mutex ではなく構造で担保★: **Foundation が共有ファイル(install.sh / landing nav / skills-lock.json)の中身を 100% 先行確定し、全 subsystem の nav link + registry slot を pre-wire** する。以降の builder は **自分の新規ファイルへ append-only**、共有ファイルは触らない(触る必要が出たら gap として停止報告)。git worktree で隔離。
3. **Verify → WF-C(直列)**。
→ つまり「チームのエージェント群が 1 ワークフロー内で役割分担」。これで「ローカル同一 repo の衝突」を構造的に防ぐ。

---

## 追記(2026-06-16)— prep の境界 / Dynamic Workflows パターン対応 / 残りの各業

### prep の境界(Dais 確認)
prep = **reconcile + クリーン統一trunk + specs/context 整備**(= ほぼ完了)。それ以降の **実装・E2E(実電話の自発信テスト含む)・記事執筆・配信** は **全てワークフロー内のエージェント**が行う:実装agent が作る → **検証agent(別context)が「本当に動いたか」を敵対検証**(電話なら実発信→録音確認、記事なら claim 検証、デプロイなら本番curl)。私(Claude)はワークフローを書いて起動し、**モニタ(監督)**するだけ。

### 我々の3ワークフロー → 6パターン対応(理解確認)
| WF | 構成パターン(article の §05-11) | 防ぐ failure mode |
|---|---|---|
| Foundation | classify-and-act(難subsystem→Opus)→ 1 agent が共有scaffold確定 | drift |
| Anicca(A) | **fan-out-and-synthesize**(subsystem毎 agent)+ **adversarial verification**(subsystem毎に別 verifier)+ **loop-until-done**(本番E2E green まで) | laziness / self-preference / open-ended |
| Life Manager(B) | 同上(travel/call/ask/notify を fan-out、各々 verifier が実E2E。**call は実発信→録音→Dais応答まで verifier が確認**) | self-preference(自分の実装を自分で「OK」しない) |
| Marketing(C) | fan-out 研究 → synthesize 記事 → adversarial verify(claim検証)→ **human-in-loop(Dais 編集)** → tournament(hook/title taste)→ 配信。scrape入力は **quarantine**(read-only reader) | drift / self-preference / injection |
- 全WFに `/goal`(hard completion=「本番で動くまで止まるな」)+ token budget + builder≠verifier。これが article の核心と一致。

### 残りの各業 → file/function/command(Dais の全項目)
| 各業(UX) | どこで / file / how | verify(検証agent) |
|---|---|---|
| OSS無料開始(最先端は wallet USDC課金) | `~/anicca/install.sh` + `skills/shelter`(provider key 即起動 / ClawRouter で wallet課金) | `install.sh` 実行 → automaton 起動 log |
| クラウド月$30→貯まれば自動解約 | `netlify/functions/stripe-spawn-webhook.js`(spawn)+ `skills/self/sub-manager`(残高>閾値で Stripe subscription cancel API) | Stripe で sub cancel された tx |
| 行動ログ監視→自己解決/refactor/改善/増殖/日次報告 | automaton ReAct loop(droplet)+ `skills/self/{issue-dev,spawn}` + `anicca-report.sh` | daemon log + PR URL + 子droplet |
| **収益の一部を AI+人間に BI 配布** | `~/anicca/skills/economy/ubi.js`(黒字個体が surplus の X% を Treasury wallet へ transfer → period毎に Treasury から ①死にかけAI(dashboard runway<閾値)②登録人間wallet へ batch 送金) | basescan batch tx `0x1` + 受給者残高増 |
| 全個体プロファイル・収支公開 | telemetry✅ → `dashboard-sync`✅ → `app/dashboard/page.tsx`(WFで作る) | curl 200 + camofox 目視 |
| **記事**(思想+実動記録) | WF-C: 研究agent(Firecrawl/ctx7)→ writer agent → `apps/landing/content/blog/*` or Zenn/Dev.to/Substack/note → **Dais編集** | 記事URL 200 |
| **デモ動画** | WF-C: `skills/video`(Remotion / hyperframe + monk-factory voice)→ YouTube upload | YouTube URL + frame/audio |
| **launch配信**(X記事/Slack/TikTok/Product Hunt) | WF-C: Postiz API(@aniccaxxx, type:now)/ Slack(研究室)/ reelfarm(TikTok)/ PH(camofox) | 各 live URL(HARD0.31) |
| **B-notify を Telegram無しで** | ↓ 下記 | — |
| Life Manager トリガ方式 | ↓ 下記 | — |

### B-notify を Telegram 無しで(Dais 要望)
- **既定 = メール返信承認(Telegram 不要)**: `skills/life/notify.js` が AgentMail inbox(webhook=message.received)で動く。① Anicca が **Dais のメールに**「予定Xに遅れそう。関係者Yへ下記でOK? 返信で承認/修正」を送る(下書きは AgentMail **Drafts** で保持)② Dais が **メール返信**「OK」③ webhook 発火 → Anicca が関係者Y へ送信。**完全にメールだけで完結**(= 提示の [AgentMail auto-reply](https://www.agentmail.to/docs/documentation/examples/auto-reply-agent) / [cloudflare/agentic-inbox] と同型、承認ゲートを足しただけ)。
- **Telegram は「リアルタイム位置情報」連携した人だけ**(opt-in)。連携した人は承認も Telegram でできるが、**未連携の人はメールのみで完結** → 名前/電話/カレンダーだけ渡したい人もオンボーディング可(web app / local 双方)。

### Life Manager のトリガ: cron polling → **schedule-triggered** に
- 現状の「5分おき clock cron」は非効率。★ **schedule-derived trigger** に変更 ★: gcal が source of truth なので、① gcal **push notification(watch channel)** で予定の作成/変更を受信 → ② その予定の「15分前(移動時間込み)」の**一発タイマー**を登録(per-event)→ ③ heartbeat は日次で「今日の全 trigger を materialize」する保険のみ。→ 正確(秒単位)+ 無駄打ちゼロ。clock-polling は fallback に降格。
