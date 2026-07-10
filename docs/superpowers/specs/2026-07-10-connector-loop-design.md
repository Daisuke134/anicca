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
   ├ [judgment] tmux Sonnet core 1 pass:
   │    TELOS + people.jsonl + signals を読み「今日 Dais の理想に最も効く
   │    接続行動」を決定（イベント応募/intro/cold mail/follow-up/何もしない）
   │    + competitor-scout 1件（agent-reach/firecrawl → scouts.jsonl）
   ├ [action rails 決定的]
   │    a. event-apply: anicca-booking + meetup-talk-applier（camofox 実応募）
   │    b. outreach: gog gmail（Anicca 自身の inbox）
   │       draft 常時作成 → risk 評価 → 低 risk: I-confirm gate 経由で send /
   │       高 risk: Telegram inline 承認 → draft send（Clira queue 方式）
   │       double-opt-in: 相手の合意受信（3-tier 分類）→ 本 intro → gcal 配置
   │    c. gcal: gcal-policy.sh（location 必須+conflict 再検証+PROPOSED 経由）
   │    d. report: Telegram 日報（応募/会うべき人/intro 文面/scout 1件+試すリンク）+ mail
   ├ [flywheel] イベント/intro 後に Telegram debrief 質問 → debriefs.jsonl → 次 pass 必読
   └ [ledgers] people/opportunities/applications/intros/outreach/debriefs/scouts/lessons.jsonl
        │ 学び（具体的 product 要求）→ life-manager feedback→issue gate → 実 issue
        ▼
   将来: cloud Life Manager の connector module（tenant 分離+課金 thesis 確定後）
```

安全設計: 送信は全て Anicca 自身の名義（Dais の Gmail から他人へ送らない）。intro は double-opt-in（Boardy 式）。risk≥95 絶対承認天井。fake 禁止・evidence 必須は会社共通規約に従う。

**イベント応募の鉄則（Dais 2026-07-10 追加、interim の OpenClaw cron にも適用）:**
1. **FREE イベントのみ**。価格表記のあるイベント（Eventbrite の有料 ticket 等）は応募も calendar 記載も禁止。有料で価値が高いものは Telegram で提案のみ（予約しない）。無料判定は実ページの価格表示で確認（推測禁止）
2. **実登録が先、calendar は後**。サイト上の実登録 evidence（connpass「参加者への情報」表示 / Luma の参加確定表示 / 確認メール）を取得してから gcal に CONFIRMED で書く。**登録なしの PROPOSED を calendar に残さない**（2026-07-10 に未登録 PROPOSED 2件を削除して是正済み — うち1件は有料 Eventbrite で二重に違反していた）
3. 登録試行が失敗したら calendar には何も書かず lessons に記録

## 5. 配置の決定: 正式な家 = claude-p（profitable-claude）、OpenClaw は interim（Dais 質問 2026-07-10 への回答）

- **正式**: connector loop は profitable-claude の CEO 配下（self-heal/self-improve/lessons/evidence gate/VCSDD tests/CEO 評価の harness が全部ここにあり、core は Sonnet）
- **理由**: OpenClaw 側は ①live store 乖離で 6/7-6/22 に silent outage（実証済み）②cron agent が弱モデル（deepseek-v4-flash が37秒で浅い discovery をした実例）③テスト/adversary gate なし — 自己修復・自己改善の器として不適
- **interim**: 修復済み OpenClaw cron 8本（booking/meetup/connpass/night-fill 等）は connector loop の E2E done まで動かし続ける（discover 結果は connector の signal 源として流用）。connector done 後に OpenClaw 側イベント cron を disable（07-08 spec の OpenClaw 退役方針と整合）

## 5b. 既存資産の再利用（車輪の再発明禁止）

- `anicca-booking`（~/.openclaw、E2E 実績あり、**6/22 から沈黙 = 修理対象**）+ `anicca-meetup-talk-applier`（connpass/AI Tinkerers、discover は稼働中・apply 停滞）= event rail
- `gcal-policy.sh` = calendar 書込の唯一経路 / `gog` = gmail·gcal / OpenClaw cron delivery = Telegram（to: 8547730585、配線済み）
- profile.json の anti_goals（平日9-17保護）は既存。**土日ショシク 11-13時は profile.json に追記するが、空き判定自体は gcal 直読が正**

## 6. Life Manager 製品との関係

connector は独立 loop として dogfood → 検証済みの機構だけが cloud Life Manager（Daisuke134/life-manager）へ移る。移行条件は 07-08 spec の boundary rule（product module 境界・tenant 分離・per-tenant cost ledger・machine-checkable outcome）。dogfood 中の学びは `lm:source:dogfood` issue として蓄積する。

## 7. 検証（VCSDD、会社規約準拠）

feature 名 `connector-loop`（profitable-claude、mode: lean、全 phase 実行）。E2E 完了条件: 実イベント応募≥1（実 URL）/ 実 gcal 書込+get 検証 / 実 Telegram 日報着信 / 実 outreach draft→承認→送信 1往復 / debrief 1件が次 pass の入力に実際に載る / registry enforce（paused 拒否）動作 / 収益・成果の捏造ゼロ。

## 8. MASTER TODO（順序が正。ここ以外に TODO の正本を置かない）

| # | 状態 | 作業 | 完了条件（machine-checkable） |
|---|---|---|---|
| 0 | ✅ 済 | CEO 会社基盤（registry/budget/enforcement/ledgers/ceo-status/start-all）+ LM loop Phase A + explorer LIVE + ccteams 導入 | profitable-claude main `190b077`、54/54 tests、5 loop ALIVE |
| 1 | ⬜ | **土台修理**: camofox :9377/firecrawl 疎通 → anicca-booking-daily 復活（6/22沈黙）→ meetup-applier apply 側復旧 → affiliate IG 取り違え解消 → profile.json に土日ショシク追記 | booking の次 run が実 gcal 書込を produce / affiliate が実投稿 1件 |
| 2 | ⬜ | **connector-loop VCSDD 立ち上げ**: init→spec（本ファイル §4-7 を EARS 化）→ fresh adversary spec-review PASS | state.json phase 進行 + verdict.json |
| 3 | ⬜ | **rails vendor**: lean-intros scorer verbatim / Clira pre-filter+draft-queue の gog 移植 / I-confirm gate / OwnPilot autonomy·risk·approvals 移植 / Telegram inline 承認 / TELOS.md template + Dais 初期値 / directives.json / pulse-rules（signals pre-pass） | tests green（各 rail の TMPDIR test）+ skills.lock 記帳 |
| 4 | ⬜ | **pass 実装（TDD RED→GREEN）**: cli/healthcheck/launchd/ledger 8本/STARTUP prompt（judgment=agent）/ competitor-scout 同梱 / registry live 登録 | run-all green + registry entry + ceo-status 表示 |
| 5 | ⬜ | **実 E2E dogfood 開始**: 初回 pass で実応募・実 gcal・実 Telegram 日報 → 7日間 dogfood → debrief flywheel 実証 | 実 URL/gcal id/日報着信の evidence + adversary PASS |
| 6 | ⬜ | **CEO 仕上げ**: bounty/affiliate/gig の cost 記録接続（core 再起動で新 prompt 反映）/ LM cron の launchd 恒久化 / CEO 初 decision 観測 / hl の honest 化・article runtime 表記修正・external budget 設定 | cost-events に 3 loop の行 / ceo-decisions ≥1行 |
| 7 | ⬜ | **article loop 有効化**: profitable-article-writer の VCSDD 完走（2c→3→5→6）→ Zenn 抜き v1（Note+Substack-ja / dev.to+X-Articles+Substack-en）→ Mode A 品質確認 1本 → 新 cron 配線 + article-metrics.jsonl + V4（実売上）gate | 実 publish URL + metrics ledger + registry live 化 |
| 8 | ⬜ | **LM Phase B**: 実 action 解禁（calendar/phone/marketing/Telegram intake）— connector の実証済み rail を流用 | spec Phase B の Done 条件 |
| 9 | ⬜ | **製品化**: connector module を cloud Life Manager へ（tenant 分離 + per-tenant cost + 課金 thesis 確定後）。Dot/Yohana の死因分析を pricing 設計に反映 | 別 spec を起こす |

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

## 9. Non-Goals（本 run で明示的にやらない）

Dais の Gmail 名義での対外送信 / 承認なしの高 risk 送信 / 静的な空き時間 config / MyCortex コード転写（license 無し）/ MAIN·Agent Economy への接触 / 製品課金の実装（#9 まで）。
