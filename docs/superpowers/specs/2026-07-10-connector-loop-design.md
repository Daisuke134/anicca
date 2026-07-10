# Connector Loop（super-connector）設計 — SOURCE OF TRUTH（2026-07-10）

このファイルが connector loop の**唯一の正本**。関連 spec（2026-07-08 loop-verification / 2026-07-10 life-manager-autopilot）は本件についてここを参照する。Master TODO も本ファイル §8 が正。

## 1. 目的（Dais 2026-07-10 口頭指示の固定）

イベント応募 bot ではない。**Dais の理想（AGI 構築・agent economy・全生命の苦しみを終わらせる・AI/crypto/AGI 環境・podcast/共同創業人脈）を保持し、適切な人と適切なタイミングで Dais を接続し続ける proactive loop**。イベント応募・cold mail・intro・calendar 配置・Telegram 報告はすべて手段。Dais は Google Calendar / Luma / connpass / X / Maps を自分で見る必要がなくなる。

- CEO 配下のフラット並列 manager loop の1つ（life-manager loop とは別事業。将来 cloud Life Manager 製品の connector module として吸収）
- local-first dogfood → 学びは feedback→issue gate 経由で `Daisuke134/life-manager` の具体的 issue になる
- 空き時間の静的設定は持たない — **Google Calendar 直読が唯一の真実**（Dais 明示）

## 2. 競合ランドスケープ（実スクレイプ 2026-07-10、詳細 = memory `reference_proactive_life_manager_competitive_landscape_2026_07_10`）

- 空白確定: ①人生理想を保持して長期 steering する製品ゼロ ②イベント×人脈 connection curation ゼロ ③JP native consumer life manager ゼロ
- 死亡2社（Dot=new.computer 2026-10-05 終了 / Yohana=Panasonic 閉鎖）→ 製品化時は課金 thesis を先に固定（Poke: $19-199/月・推論原価 ~$50/月、Duckbill: $49-350/月が生存例）
- 盗む機構: Poke（messaging-native / email-as-external-memory / 人格層と実務層の分離）、Boardy（double-opt-in intro / debrief 学習 / intro 上限 3/日）、Lunchclub（post-meeting feedback flywheel）、Duckbill（「approve nothing, just get told it's done」）、Martin（proactivity 自体が課金価値である証明）

## 3. OSS code 深読みの vendor 決定（3チームで実 clone・実 code 読解済み。clone は scratchpad/oss-study/ に保持）

| 部品 | 出典（file 単位） | License | 決定 |
|---|---|---|---|
| ideals store schema | danielmiessler/Telos `personal_telos.md`（PROBLEMS/MISSION/NARRATIVES/GOALS/CHALLENGES/IDEAS/PREDICTIONS/WISDOM/METRICS/LOG） | MIT | **copy-verbatim**。LifeOS の TELOS/PRINCIPAL 分割+自動生成は不採用（生成機構が過剰）。1枚を手保守 |
| pulse cycle（gather→rule評価→signal無ければ LLM 呼ばず→agent が tool で実行→report→log） | OwnPilot `packages/gateway/src/autonomy/{engine,evaluator,context}.ts` | MIT | **アーキテクチャ再実装**（python/bash ~150行）。8 rule 関数+severity 重み（info=10/warn=25/crit=50）+urgency 式は値ごと copy |
| directives config（disabledRules/blockedActions/customInstructions/ruleThresholds/actionCooldowns） | OwnPilot `autonomy/types.ts` | MIT | **schema copy** → connector/config/directives.json |
| autonomy 5段階 + risk 因子表 + 承認 flow（pending/remembered/timeout） | OwnPilot `autonomy/{types,risk,approvals}.ts`（score≥95 は FULL でも承認必須の絶対天井） | MIT | **verbatim 移植**（pure data+関数）。既定 = SUPERVISED 相当 |
| Telegram inline-keyboard 承認（approve:<id>/deny:<id>、timeout→deny、chatId 防御） | OwnPilot `channels/plugins/telegram/approval-handler.ts` | MIT | **flow copy**、実装は Telegram Bot API 直（grammy 不要） |
| trigger 3-loop（schedule poll / condition poll / event subscribe）+ triggers schema | OwnPilot `triggers/engine.ts` + `db/.../001_initial_schema.sql` | MIT | **schema 1:1 copy**（sqlite/jsonl）。cron 計算は croniter/launchd（brute-force matcher は不採用） |
| 決定的 mail pre-filter（own-msg/blocklist/allowlist/label 順序） | Clira `src/lib/email/emailFilterService.ts` | MIT | **near-verbatim 移植**（gog 版） |
| Gmail-draft-as-queue（AI draft = 実 Gmail draft、承認 = その draft を send） | Clira `prisma GeneratedDraft` + `api/queue/route.ts` | MIT | **pattern verbatim**: `gog gmail draft create` → Telegram inline 承認 → `draft send`。独自 draft store を作らない |
| planner/style 分離（facts に source enum 必須、style 段は事実追加禁止） | Clira `schemas.ts` + `styleAgentPrompt.md` | MIT | pattern copy + **独自追加**: entity-diff 検査（style 出力の固有名詞/数値 ⊆ planner 集合）— Clira はコード検証を持たない（実測） |
| 送信の魔法文字列 gate（`confirm == "I confirm"` 以外は拒否、作成は常に DRAFT） | gtm-mcp `src/gtm_mcp/tools/smartlead.py:777` | MIT宣言(pyproject)だが LICENSE file 無し | **idiom を verbatim 採用**（コード転写ではなく慣用句） |
| 返信分類 3-tier（regex→thread 再取得→LLM は残余のみ） | gtm-mcp `.claude/skills/reply-classification/SKILL.md` | 同上（prose） | **prose copy**、SmartLead→gog 置換 |
| warm-intro スコア（work/school overlap、~140行 pure 関数） | lean-intros `app.py:6532-6673` | MIT（LICENSE 実在） | **verbatim vendor**。※README の seniority 記述は実装に無い（実測）。**判断 gate にせず agent への feature 入力**（no-hardcode 規約） |
| scheduler→agent-loop callback / SQLite facts+KG schema | MyCortex | **License 無し** | **pattern のみ**（コード転写禁止） |

## 4. アーキテクチャ

```text
        CEO LOOP ── registry enforce（他 loop と同一骨格、特別扱いなし）
             │
   CONNECTOR LOOP（skills/human-funded/connector/）
   ├ [ideals] state/TELOS.md（Telos schema、手保守+会話で追記）
   ├ [signals 決定的 pre-pass] connector-signals.py:
   │    gcal 直読（空き/直近イベント）/ 未 debrief / 停滞人脈 /
   │    未返信 intro / 今日の discover 結果(luma·connpass·aitinkerers) /
   │    inbox 新着（Clira pre-filter 通過分のみ）
   │    → signals.json（0件なら core を起こさず終了 = token 節約、OwnPilot 式）
   ├ [judgment] tmux Sonnet core 1 pass — 毎日全 rail 実行（選択制ではない、Dais 2026-07-10）:
   │    STEP0 = gcal 直読が常に最初（double-booking 絶対禁止、仕事/養成所回避）
   │    毎日必須: ①horizon 全体（今日〜14日+）の空き枠を FREE イベント実登録で先埋め
   │    （早期応募ほど当選率が高い。当日応募は原則機能しない — 明日・来週・来月の gap を埋め続ける）
   │    （AI/AGI/crypto infra 重点 — Dais は crypto を学びたい。LT/hackathon/meetup）
   │    ②intro/cold mail = **scope 内だが当面 DISABLED**（Dais 2026-07-10: 評判リスク、
   │      まだ危険。directives.json の blockedActions:["outreach_send"] で機械的に封鎖。
   │      draft 生成と people.jsonl 蓄積までは可、送信は一切しない。解禁は Dais の指示で）
   │    ③未 debrief 回収 ④competitor-scout 1件
   │    「新規登録なし」が許されるのは horizon 全体が既に埋まっている時のみ（gcal 証跡つき）
   ├ [action rails 決定的]
   │    a. event-apply: anicca-booking + meetup-talk-applier（camofox 実応募）
   │    b. outreach: **Dais の送信 identity**（gog gmail = keiodaisuke@、Dais の声/文体）
   │       — AI 名義は不採用（Dais 2026-07-10:「誰が AI に返信する」）
   │       **承認 UX ゼロ**: draft 承認なし・Telegram approve なし・Dais は何もしない
   │       （Duckbill 式「approve nothing, just get told it's done」— 事後報告のみ）
   │       I-confirm gate はツール内の決定的誤爆防止として維持（agent が渡す、human 無関与）
   │       double-opt-in = 相手の返信が opt-in（3-tier 分類）→ 会う日程を gcal 確定配置
   │    c. gcal: gcal-policy.sh（location 必須+conflict 再検証+PROPOSED 経由）
   │    d. report: Telegram 日報（応募/会うべき人/intro 文面/scout 1件+試すリンク）+ mail
   ├ [flywheel] イベント/intro 後に Telegram debrief 質問 → debriefs.jsonl → 次 pass 必読
   └ [ledgers] people/opportunities/applications/intros/outreach/debriefs/scouts/lessons.jsonl
        │ 学び（具体的 product 要求）→ life-manager feedback→issue gate → 実 issue
        ▼
   将来: cloud Life Manager の connector module（tenant 分離+課金 thesis 確定後）
```

安全設計: 送信は Dais の identity・Dais の声（Dais 2026-07-10 明示指示で旧「Anicca 名義」を上書き。事前承認なし・事後報告のみ = no human dilute）。intro は double-opt-in（相手の返信が gate、Dais 無関与）。ツールレベルの決定的 gate（I-confirm・FREE 判定・entity-diff・gcal conflict）は維持 — これらは human-loop ではなく誤爆防止。fake 禁止・evidence 必須は会社共通規約。

**イベント応募の鉄則（Dais 2026-07-10 追加、interim の OpenClaw cron にも適用）:**
1. **FREE イベントのみ**。価格表記のあるイベント（Eventbrite の有料 ticket 等）は応募も calendar 記載も禁止。有料で価値が高いものは Telegram で提案のみ（予約しない）。無料判定は実ページの価格表示で確認（推測禁止）
2. **実登録が先、calendar は後**。サイト上の実登録 evidence（connpass「参加者への情報」表示 / Luma の参加確定表示 / 確認メール）を取得してから gcal に CONFIRMED で書く。**登録なしの PROPOSED を calendar に残さない**（2026-07-10 に未登録 PROPOSED 2件を削除して是正済み — うち1件は有料 Eventbrite で二重に違反していた）
3. 登録試行が失敗したら calendar には何も書かず lessons に記録

## 5. 配置の決定: 正式な家 = claude-p（profitable-claude）、OpenClaw は interim（Dais 質問 2026-07-10 への回答）

- **正式**: connector loop は profitable-claude の CEO 配下（self-heal/self-improve/lessons/evidence gate/VCSDD tests/CEO 評価の harness が全部ここにあり、core は Sonnet）
- **理由**: OpenClaw 側は ①live store 乖離で 6/7-6/22 に silent outage（実証済み）②cron agent が弱モデル（deepseek-v4-flash が37秒で浅い discovery をした実例）③テスト/adversary gate なし — 自己修復・自己改善の器として不適
- **interim 廃止（Dais 2026-07-10）**: 同じ仕事に2 loop は禁止 → OpenClaw イベント cron 9本は**disable 済み**（booking/meetup×3/connpass/night-fill/event-bot/life-notify/comedy-en、live enabled 63→55 実測）。イベント接続は connector loop が最初から唯一のオーナー。skill 実体（booking/meetup-applier の scripts）は connector が rail として vendor する
- **訂正（2026-07-10）: larry / reelclaw は claude-p loop 内に存在しない**（Dais 質問への答え = **NO**）。OpenClaw cron としてのみ稼働（larry×17 + reelclaw×18 + lm-video×3 + watercolor×3、live 実測）。claude-p の clip/video/affiliate は別物。現象: **metrics を見ず同一内容を同一時刻に投稿し続けている = self-improve 不在**（OpenClaw に評価 harness が無い）。**→ #9.5 で claude-p manager loop 化必須**（目的 = mobile app スケーリング、§11 の3層バー装着で「伸びない投稿の反復」を機械検出→戦略変更）。当面 OpenClaw で稼働継続、移行は connector E2E 後
- OpenClaw 完全削除は 07-08 spec の gate（state/ledger push 確認 + Dais 明示 go）を満たしてから

## 5b. 既存資産の再利用（車輪の再発明禁止）

- `anicca-booking`（~/.openclaw、E2E 実績あり、**6/22 から沈黙 = 修理対象**）+ `anicca-meetup-talk-applier`（connpass/AI Tinkerers、discover は稼働中・apply 停滞）= event rail
- `gcal-policy.sh` = calendar 書込の唯一経路 / `gog` = gmail·gcal / OpenClaw cron delivery = Telegram（to: 8547730585、配線済み）
- profile.json の anti_goals（平日9-17保護）は既存。**土日ショシク 11-13時は profile.json に追記するが、空き判定自体は gcal 直読が正**

## 6. Life Manager 製品との関係

connector は独立 loop として dogfood → 検証済みの機構だけが cloud Life Manager（Daisuke134/life-manager）へ移る。移行条件は 07-08 spec の boundary rule（product module 境界・tenant 分離・per-tenant cost ledger・machine-checkable outcome）。dogfood 中の学びは `lm:source:dogfood` issue として蓄積する。

## 7. 検証（VCSDD、会社規約準拠）

feature 名 `connector-loop`（profitable-claude、mode: lean、全 phase 実行）。E2E 完了条件: 実イベント応募≥1（実 URL）/ 実 gcal 書込+get 検証 / 実 Telegram 日報着信 / 実 outreach draft→承認→送信 1往復 / debrief 1件が次 pass の入力に実際に載る / registry enforce（paused 拒否）動作 / 収益・成果の捏造ゼロ。

## 8. MASTER TODO（順序が正。ここ以外に TODO の正本を置かない。更新 2026-07-10 夜）

| # | 状態 | 作業 | 完了条件（§10 の done 条件に従う） |
|---|---|---|---|
| 0 | ✅ | CEO 会社基盤 + LM Phase A + explorer LIVE + ccteams | main `190b077`、54/54、5 loop ALIVE |
| 1 | ✅ | 土台修理: booking scan buffer 修正（25/25→5/5）+ OpenClaw cron live-store 事故解明 + イベント cron を connector に一本化（9本 disable、二重 loop 禁止）+ 未登録 PROPOSED 2件削除（うち1件有料） | commit `120e863` + memory 固定 + gcal 実測 0 PROPOSED |
| **2** | 🔄 | **connector-loop VCSDD 立ち上げ**: init → spec EARS 化（§4 毎日全STEP・horizon 先埋め・STEP2 DISABLED・FREE only・登録先行 / §11.1 8機構の PROP 化 / 9 source vendor 表）→ fresh adversary spec-review PASS | state.json phase 進行 + verdict PASS |
| 3 | ⬜ | rails vendor: ①Telos schema ②OwnPilot pulse/directives/autonomy ③Clira pre-filter ④gtm-mcp I-confirm+返信3-tier ⑤lean-intros scorer ⑥Boardy flow ⑦Duckbill UX ⑧booking/meetup scripts ⑨評価8機構 — 全て skills.lock 記帳 | 各 rail TMPDIR test green |
| 4 | ⬜ | pass 実装（TDD RED→GREEN）: cli/healthcheck/launchd/ledger 8本/signals pre-pass/STARTUP prompt/scout 同梱/registry live | run-all green + ceo-status 表示 |
| 5 | ⬜ | 実 E2E dogfood 7日: 毎日 FREE 実登録（horizon 先埋め）+ gcal CONFIRMED 読返し + Telegram 日報実着信 + debrief flywheel。STEP2 は封鎖のまま | §10 connector 行 + 7日 streak + adversary PASS |
| 6 | ⬜ | CEO 仕上げ: bounty/affiliate/gig cost 自動記録（core 再起動）+ LM cron launchd 化 + CEO 初 decision + hl/article registry 正誤 + external budget | cost-events 3 loop 行 + ceo-decisions ≥1 |
| 7 | ⬜ | article loop 有効化: profitable-article-writer VCSDD 完走 → Zenn 抜き v1 → Mode A 品質1本 → 新 cron + metrics + V4 別 gate | 実 publish URL + registry live |
| 8 | ⬜ | LM Phase B: 実 action 解禁（connector rail 流用） | LM spec Phase B done |
| 9.5 | ⬜ | SNS factory 移行: larry/reelclaw/lm-video/watercolor を claude-p manager loop 化（§11 バー装着で self-improve 開始）→ OpenClaw 退役（state push + **Dais 明示 go** 後に削除） | live cron 0 + launchd 依存 0 + go 記録 |
| 9 | ⬜ | 製品化: connector module → cloud Life Manager（課金 thesis 確定後、別 spec） | — |

## 10. DONE CONDITIONS（自己欺瞞防止、Dais 2026-07-10 指示。宣言には「実行コマンド+出力」の記録必須）

**共通原則**: done = ①実世界の結果を**独立経路で読み返せる**（gcal は `gog calendar events get <id>`、応募はサイト実ページ/確認メール、送信は message id、売上は on-chain/Stripe 実記録）②1回きりでなく **cadence streak** で判定 ③fresh adversary（Opus）が evidence を読み返して PASS ④「PROPOSED を書いた」「draft を作った」「enqueue した」は done ではない。evidence の無い done 宣言 = 罪。

| TODO# | loop/作業 | DONE の機械検証条件 | NOT done の例（禁止される言い方） |
|---|---|---|---|
| 1a-b | anicca-booking 復旧 | ①scan buffer 修正 commit 済（`120e863` ✅）+ cron live store 復旧済（8本 ✅）②**定時 cron 2連続 run で FREE イベントに実サイト登録**（connpass「参加者への情報」/ Luma 参加確定 / 確認メール）③登録済イベントのみ gcal CONFIRMED（`gog events get` 読返し）④Telegram delivered:true ⑤有料イベント予約ゼロ・未登録 calendar 記載ゼロ | 手動発火1回で「復旧」/ PROPOSED 書込だけで「応募した」 |
| 1c | meetup-applier apply 側 | 新規実応募1件が data/applications/ に記録され、応募先実ページ or 確認メールで独立検証 | discover が動いてるだけで「動いてる」 |
| 1d | affiliate 投稿再開 | @aishigoto.labo への実投稿 URL を browser 実読で確認 + queue 減少 + commission-watermark 更新継続 | deck 生成だけで「稼働」 |
| 2-4 | connector-loop 構築 | VCSDD 全 gate PASS（state.json）+ tests/run-all green + registry live + ceo-status 表示 | コードが書けただけ（E2E 前）で「完成」 |
| 5 | connector 実 E2E | ①実イベント応募≥1（実 URL + 登録証跡）②gcal 書込を event id の get で読返し ③Telegram 日報が実着信（delivered:true + Dais が見られる）④outreach 1往復（draft→承認→送信 message id→返信分類）⑤debrief 1件が次 pass の入力ログに実出現 ⑥**7日連続 streak** ⑦fresh adversary PASS | 初回1 pass 成功で「dogfood 完了」 |
| 6 | CEO 仕上げ | cost-events.jsonl に bounty/affiliate/gig の行が**自動**追記される（core 再起動後の実 pass 由来）+ ceo-decisions ≥1行 + その decision が registry に反映され enforcement 実挙動で観測 | 手で cost 行を書く / decision 0行のまま「CEO 稼働」 |
| 7 | article 有効化 | ①実 publish URL（logged-out fetch で本文 token 一致）②article-metrics.jsonl に実測 views 行 ③cadence: 週1以上×2週連続 ④V4=実売上は**別 gate**（¥0 なら「publish まで done、売上 not yet」と分けて報告） | 「公開できる状態」で「有効化済み」/ 売上未確認で「稼げてる」 |
| 8 | LM Phase B | 実 action（calendar/phone/marketing/Telegram intake）が per-action で本表と同型の独立読返し evidence を持つ | Phase A の planning 出力で「動いてる」 |
| 稼働中 loop 共通 | gig/bounty/pm/capafy/LM/explorer | 07-08 spec の cadence contract 表 + evidence gate（`none:<reason>` 形式）に準拠。「earned」宣言は realized 実収益が ledger + on-chain/入金記録で照合できた時のみ | funnel 途中経過で「稼いだ」 |

## 11. 各 loop の評価バー（BROKEN / STANDARD / IMPROVE — 全て結果ベース、Dais 2026-07-10）

3層で判定する。**BROKEN と STANDARD は決定的**（healthcheck/cadence contract/evidence gate が機械判定）、**IMPROVE は agent の週次 evaluator**（「先週より今週」を ledger 比較で機械確認、何を改善するかの判断は agent）:

| 層 | 意味 | 誰が判定 | 発火するもの |
|---|---|---|---|
| BROKEN | 当日 cadence 未達 or 実在検証失敗 or ledger 破損 | healthcheck（決定的、21:00 JST 締め） | self-fix.sh 自動 escalate |
| STANDARD（bare minimum） | 実世界の結果が独立読返しで存在する | evidence gate（決定的） | 未達 = 「修理が必要」。これ未満で「動いてる」と言うの禁止 |
| IMPROVE（上限なし） | north-star metric が前週比で伸びる | 週次 evaluator + search-driven self-improve（agent） | 伸びない = 戦略変更（BP 検索→次 pass 反映）。CEO は3層全部を読んで配分 |

| loop | BROKEN | STANDARD（これが bare minimum） | IMPROVE（north star、前週比） |
|---|---|---|---|
| **connector** | 当日 pass なし / signals 放置 / 応募失敗の握りつぶし | **毎日**: gcal 直読→**horizon（今日〜14日+）の空き枠**に FREE イベント実登録（サイト証跡、早期応募優先）+ gcal CONFIRMED + Telegram 日報。**horizon に空きがあるのに新規登録 0 の日 = STANDARD 未達**（horizon 全体が埋まっている時のみ免除、証跡つき） | **成立した接続の数と質**: 双方 opt-in intro 成立数 → 実会話/実会合になった数 → 開いた扉（podcast 出演・紹介の連鎖・共同作業）→ debrief 満足度 |
| gig | 当日応募 0 / ledger 無更新 | N 応募/日 + funnel 更新（実ページ検証） | 返信率 → 受注数 → 入金¥（現状 270応募/17返信/受注0 = ここが改善対象） |
| bounty | 巡回なし | checked 増/日 | survivors → 提出 → 賞金$ |
| affiliate | queue 滞留 + 投稿 0 | 1 投稿/日（実 URL browser 検証） | views → commission¥ |
| life-manager | pass なし / ledger 破損 | feedback→issue が実 URL で回る + CEO 報告（mrr 正直） | 解決 issue → verified user outcome → MRR$ |
| explorer | pass なし | 1 検証/日（実 evidence。ABANDON も正当な結果） | proposal → CEO 採用 → loop 化 → その loop の実収益 |
| article | — | 週1 実 publish（logged-out 本文検証） | views → 有料販売¥（V4） |
| pm / hl | pass 停止 | pass 稼働 + ledger | realized PnL 週次↑ |
| CEO | decision 不能 / registry 破壊 | 週次 decision ≥1 + enforcement 実反映 + cost/評価の読取 | **会社全体の実収益**と loop portfolio の質が自分の配分変更後に改善（CEO 自己検証、悪化は rollback） |

### §11.1 評価バーに追加する機構（BP 調査 2026-07-10、出典付き。全 loop に適用）

調査結論: 同型3層の既製 OSS は今回の調査では見つからなかった — **これは「我々が先行」を意味しない。我々は常に後発であり、alpha を探し続けるのが仕事**（Dais 2026-07-10）。盗む機構は以下 — 実装は connector から始めて全 loop に展開:

| # | 機構 | 出典 | 実装 |
|---|---|---|---|
| 1 | BROKEN 判定は guardrail 型（同期・決定的・数ms・blocking）に限定、LLM judge を同期路に入れない | Hamel Husain (hamel.dev/blog/posts/evals-faq)「Guardrails are inline safety checks... Evaluators run after」 | healthcheck は現行のまま決定的を維持 |
| 2 | **cascade 評価**: stage1(出力ある?タイムアウト?)→stage2(schema 妥当?)→stage3(LLM judge north-star) 段階 gate、timeout は例外でなく metric 行 | OpenEvolve `evaluator.py` `_cascade_evaluate()`（pm で既運用） | 各 loop の self-check を3段化 |
| 3 | **God-Evaluator 禁止**: 週次 evaluator は次元別 boolean（cadence_ok / schema_ok / evidence_ok / north_star_delta_ok）を別々に ledger へ | Eugene Yan (eugeneyan.com/writing/product-evals)「anti-pattern is a single God Evaluator」 | loop-evaluations.jsonl の行 schema に4 boolean 追加 |
| 4 | **burn-rate 警報**: 閾値だけでなく直近 k 週の傾き（3点 delta）を見て「N 週後に BROKEN に到達する速度」で早期発火 | Google SRE error budget（rickpollick.com/blog/error-budgets-over-deadlines）「The balance tells you where you are. The burn rate tells you where you are going」 | 週次 evaluator に slope 欄追加 |
| 5 | lessons.jsonl を**構造化 verdict**に統一 `{issue_type, severity, fix_suggestion, confidence, pattern_detected}` — 次 pass が `pattern_detected:"persistent_regression"` を grep してから動く | BetterForAll L2 + Reflexion（use_memory が効くのは構造化 feedback の持越し） | lessons writer/reader の schema 統一 |
| 6 | **suite-promotion gate**: self-fix が閉じた failure は per-loop の恒久 regression テストに昇格し、週次 evaluator が毎回再実行（「一度捕まえた failure は永遠に捕まえる」） | auto-harness 3-step gate + Braintrust online→offline loop | `tests/regression/<loop>/` に failing case 蓄積 |
| 7 | **fix の採点は fixer 以外**: BROKEN/STANDARD/IMPROVE の判定は fresh-context spawn が ledger+lessons のみを読んで下す。loop の自己申告「直りました」は入力にしない | DGM（held-out benchmark を超えた rewrite だけ採用）+ 我々の adversary 原則の運用適用 | 週次 evaluator を fresh spawn 化（要確認: 現状 同一 context なら修正） |
| 8 | **遷移故障行列**: 3 step 以上の loop は「最後に成功した state × 最初に失敗した state」の行列を週次で ledger から機械生成 → どの遷移を直すか一目 | Hamel Husain transition failure matrix | 週次 evaluator に行列出力追加 |

anti-gaming の核 = #6 + #7（自己採点 benchmark は腐る — BetterForAll 実測: 固定 benchmark で 90-100% の agent が adversarial suite で 62-66%）。

## 9. Non-Goals（本 run で明示的にやらない）

Dais の Gmail 名義での対外送信 / 承認なしの高 risk 送信 / 静的な空き時間 config / MyCortex コード転写（license 無し）/ MAIN·Agent Economy への接触 / 製品課金の実装（#9 まで）。
