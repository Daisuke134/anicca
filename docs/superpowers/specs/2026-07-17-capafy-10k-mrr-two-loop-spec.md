# Capafy 10k MRR — two-loop spec（2026-07-17）

goal: `done="Capafy MRR $10,000/月。売上は Capafy server ledger + on-chain/銀行入金で実測確認"`（/goal 正本 = `2026-07-17-capafy-goal.md`）
調査正本: `docs/earn/2026-07-17-capafy-marketing-link-placement-research.md`（全実測 file path 付き）
**先行 spec（車輪。必読）**: `~/.openclaw/docs/superpowers/specs/2026-06-24-capafy-factory-automation-10k-100k-mrr.md` — 10k の算数（$10k ≈ 15-20 listings × ~$600 gross、blended ARPU $11/mo、純率 ~70%）、factory モード A（launchd+claude -p で勝者 clone 日次）、CP2 LLM hosting レシピ、leak/secret/E2E gate が確定済み。本 spec は「A: 修理」「B: marketing 新設」をそれに足す差分。
注意: 06-25 の確定レシピは「sk-ant 鍵 + openai-completions」で OpenRouter 不採用だったが、現 runtime は `CAPAFY_HOST_OPENROUTER_KEY`（本日 live probe 200 OK）で動いている — 実装時はどちらかに統一し spec の 0.97 節を是正すること（併存は事故のもと）。
状態: **IN PROGRESS（2026-07-17 着手）**。TaskList 登録済み 13件（A1/B0 = in_progress）。実装は vcsdd（Fable plan / subagent impl / Sol review。※この session の subagent env は gpt-5.6-sol 固定と実測済み）。
進捗はこの表を正とする:
| task | 状態 |
|---|---|
| A1 provider/key 修理 + resubmit | 診断完了・gate 実装済み / **真因 = OpenRouter 残高薄（$1.59）、stale key でも provider 名でもない**。4 agents は under_review で editable でない（触れない）、orphan は後継 online で abandon → 実効修理は A2 の残高補充。CP2 作業は 0件（全 review-lock）。2026-07-18 実測 |
| B0 IG account 復旧 | **account 確保 DONE（2026-07-18）**: 新規 @useclaudeskills 作成（既存6 account は全て clip niche 用で frozen/poisoned のため流用不可）。profile 完成・main :9222 login 済み・warmup day-1 実行済み・日次 warmup launchd 稼働。残: 7日 warmup 完了 → browser test 投稿 1件公開確認（B0 の done 到達）。詳細は §3 B0 行 |
| 他 11件 | pending（TaskList 参照） |

## 0. 現実（2026-07-17 実測）

| 事実 | 出典 |
|---|---|
| online listings 21 / **実売上 $9.99 gross（1件、06-23）、seller 取り分 $8.00 未出金（realized payout=$0）** | Capafy live API（研究 MD §3c-0） |
| ~~reconcile 欠落バグ（local ledger $0）~~ → **A4 で修理済み（2026-07-18）**: `capafy-earn-ledger.jsonl` に 06-23 $9.99 行 + payout snapshot、loop.sh が STATE に pending $8.00 を surface。実装は ~/anicca（実稼働 copy）commit f10f9ddc | 本 spec A4 |
| bottleneck = discoverability（21 listings で 3ヶ月 1件 = 露出不足） | `capafy-loop/state/STATE.md:5-10` + sales/trend |
| rejected の現況: 4件は再提出済み manual review 中、真 rejected は orphan 1件のみ（self-fix が 07-17 に自走修理済み） | 研究 MD §3c-0 |
| billing error 真因【2026-07-18 確定】= **OpenRouter 残高薄（remaining $1.59）**のみ。stale key 説は FALSE（旧 key==新 key、同一 `sk-or-v1-5598...7b26`）。provider 名 `publisher_openai_official` は cosmetic（vendor_id=79=OpenRouter で routing 正常、live probe 200）。→ 実効修理は残高補充（A2）。gate `key_health_gate.sh` 実装済み | 研究 MD §3c 訂正節 + lessons.md |
| retry 停止の直接原因 = headless CP1 driver の max-turns(60) 枯渇 | `daily_loop.log` 07-17 19:45 |
| 通知は AgentMail + Telegram 両方送信成功（07-17 12:47）。Dais 未受信は受信側設定の疑い | 研究 MD §3c-0 |
| verify-loops-audit（6h）が self-fix を反復 spawn する地雷 | 研究 MD §3c-0 |
| marketing loop = 全休眠（clip のみ稼働、それも実投稿 07-14 停滞） | 研究 MD §3b |
| IG/TikTok comment URL = クリック不可 → bio 主導線。X = self-reply 主導線 | 研究 MD §1 |

## 1. アーキテクチャ（2 loop、どちらも claude-p、zero-human-loop）

```
[Loop A: build+publish]  既存 capafy-autopublish を修理・強化
  daily 08:10 launchd（既存）
  inventory → publish/retry → verify Test Run green → reconcile ledger
  + self-heal: key-health gate / max-turns fallback
  + self-improve: 売れ筋カテゴリを server data から学び、次に作る skill を選ぶ

[Loop B: marketing]  clip engine 部品を転用して新設
  daily 1 post × platform（IG Reels + X。TikTok は bio link 解禁後）
  online(status=4) listing を rotation 選択 → 紹介動画/post 生成 → 投稿
  → bio/self-reply に Capafy URL → metrics 計測 → 週次 reflect（勝ち post を模倣）
```

## 2. Loop A 修理タスク（MUST、優先順）

| # | タスク | done 条件 |
|---|---|---|
| A1 | ~~provider 名不整合を修理 + CP2 で key 入れ直し + resubmit~~ → **2026-07-18 是正**: provider 名は cosmetic、stale key 無し、真因は残高薄のみ。4 agents は under_review で editable でなく CP2 不可（review-lock、`"The current version is not editable"`）。orphan 2485008254 は後継 7686597754 online で abandon。**実装したのは fail-closed の `key_health_gate.sh`（prepare/finish に配線）** = 残高不足の口座へ publish しない。実効修理（残高補充）は A2。 | 【done 条件は Capafy の人手 review 待ちで A1 単独では到達不能】gate が green + 4 agents が balance 補充後の review を通過 or 再 reject 時に fresh-key resubmit |
| A2 | OpenRouter 残高補充（$10-25）。gate は実装済み（A1 で `key_health_gate.sh` を prepare/finish に配線、閾値 $2 fail-closed）。**2026-07-18 実測: 代替 rail の sk-ant 鍵（CAPAFY_HOST_ANTHROPIC_KEY）も "credit balance too low" で死亡 — 06-24 spec の auto-refill 記述は現在 FALSE。実効修理 = 入金のみ。** rail 候補: (a) Dais が OpenRouter へ card 補充 $10-25【stop point、Dais 判断】 (b) ~~Capafy payout → crypto~~ **2026-07-18 実測で棄却**: payout method は `wire_transfer` のみ（api-docs 00_overview.md:343、crypto rail 無し・銀行設定は結局 Dais 口座・遅い）→ **即効修理は (a) 一択** | gate green（remaining >= $2）+ 4 agents が review 通過 |
| A3 | max-turns 枯渇対策: 1 pass = 1 agent に制限（貪欲 retry 禁止）。60 turns 超過時は state 保存して次 pass 継続 | 3日連続で BLOCKED rc=1 ゼロ |
| A4 | **DONE（2026-07-18 実測 green）**: `capafy_earn_reconcile.py` を新設し `GET /agent/sales/trend` + `/agent/developer/payout-info` を専用 ledger `state/capafy-earn-ledger.jsonl` に mirror（idempotent/atomic/backup）。**on-chain realized reader（ledger_reader.py、tx/sig 必須）は汚染しない** — capafy は bank 収益で on-chain 痕跡が無く、tx 捏造は罪。clip の専用 ledger と同パターン。loop.sh が毎 wake で reconcile を回し STATE.md に `capafy_seller_balance_pending_usd`/`realized_payout`/`lifetime_gross` を追加、旧「monthly payout=$0」報告が隠していた実売上を surface。**実際に走るのは ~/anicca 版**（daily loop STEP1 が `~/anicca/.../loop.sh` を指す。~/.anicca-founder は非稼働）→ ~/anicca に実装・commit f10f9ddc。 | ✅ 06-23 の $9.99 行が ledger に存在（実測 PASS）/ STATE.md が server 値一致（gross $9.99・seller balance $8.00 pending・realized $0）/ test-loop.sh 7-0 GREEN / on-chain ledger capafy 0行 |
| A5 | self-improve: Capafy ranking/カテゴリ実売データを daily 取得 → 次に作る skill を上位カテゴリから選ぶ selector | selector の判断ログが state に残る |
| A6 | verify-loops-audit の self-fix 反復 spawn 抑止（result marker 確認 + backoff） | self-fix log に多重 spawn 痕跡が出ない |
| A7 | 通知: 送信は AgentMail+Telegram とも成功済み（07-17 12:47）→ Dais 側受信設定を点検し、受信確認できる 1 経路を SSOT にする | Dais が実受信を確認 |

## 3. Loop B 新設タスク（MUST、clip 部品転用）

| # | タスク | 転用元 / 新規 |
|---|---|---|
| B1 | Capafy promotion selector（status=4 のみ、rotation/dedup） | 新規（`published.jsonl` は mixed status のため remote 確認必須） |
| B2 | content adapter: listing → hook/problem/demo/CTA script | `faceless-money-factory/SKILL.md:10-31` の topic 部差替え |
| B3 | 動画組立 + caption + 品質 gate | `assemble.sh` / `burn-captions.sh` / `verify_clip.sh` そのまま |
| B4 | IG poster（bio に Capafy URL 固定。comment に URL 置かない） | `instagrapi_post.py` + `run.sh` 3分岐 ledger |
| B5 | X poster（native post + 最初の self-reply に listing URL） | 新規（`anicca-x-marketing-skill` disabled job を土台に再設計可） |
| B6 | metrics + 週次 reflect（views/clicks→勝ちフォーマット模倣） | `selfimprove.py` / `metrics.py` + `marketing-self-improve/run.sh` の advisory を自動 action 化 |
| B7 | conversion attribution: UTM（instagram_bio / x_reply）↔ agent_id ↔ Capafy subscriber join | 新規 |
| B8 | launchd job `ai.anicca.capafy-marketing-daily`（Loop A と別 job） | plist 新規、instance 分離は `_instance_paths.sh` 方式 |
| B0 | **前提修理: IG account 復旧**。`~/.cloak/clip-accounts.json:3-58` は全 account 非-ready（aiclipsvault=`poisoned_manual_backup`）= 既存 clip loop も投稿不能。Capafy marketing 用 account を ready にする（既存復旧 or `ig-account-create`+warmer で新規、warmup 7日） | ready account >= 1 が clip-accounts.json に実在 + テスト投稿 1件公開確認 |
| B9 | アカウント戦略: **phase 1 = 1 account**（"sharing claude skills you can use" 統一テーマ）で 14日運用。skill 別多 account 化は phase 1 の CTR 実測後に判断（IG 新規 account 量産は ban リスク、warmup 7日/acc が必要 — `decide.py:33-46`） | phase 1 の posts が ledger に 14件 |

## 4. OSS 化（profitable-claude）

- Loop A/B が 14日安定稼働した後、`profitable-claude/skills/` に canonical 移設（既存 7 skill 構成に倣う。移設 manifest は `docs/earn/profitable-claude-clip-loop-migration-plan.md` 方式）。
- 人間側 onboarding = 銀行/決済 credential 投入のみで loop 全体が起動する README（life-manager-daily.sh の実例に倣う）。
- **credential・key は repo に絶対入れない**（ReelFarm SKILL.md の hardcoded key 事故を反例として lint: `leak_scan.sh` を pre-commit に）。

## 5. リスク / 決定事項

- Dais 原案「link in comment、bio 不要」は IG/TikTok で不成立（comment URL クリック不可）→ **bio 主導線 + X は self-reply** に変更（研究 MD §1、外部ソース 8件）。
- 「skill ごとに 1 account」は phase 2 送り（B9）。
- 10k MRR 逆算: 平均 $10/月 sub × 1,000 subscribers。21 listings では露出が全て。Loop B の CTR データが出るまで listing 増産（A4）と並走。
- ⚠ 別件 backlog: `~/.openclaw/skills/reelfarm/SKILL.md:554-559,609-614` hardcoded key → rotate + 除去。

## 6. TODO 表（順序の正本）

| 順 | item | phase |
|---|---|---|
| 1 | A1 provider 名修理 + key 入れ直し + resubmit | vcsdd |
| 2 | A2 残高補充 + key-health gate | vcsdd |
| 3 | A4 sales reconcile バグ修理（$9.99 見落とし再発防止） | vcsdd |
| 4 | A3 max-turns 対策 + A6 self-fix 反復抑止 | vcsdd |
| 5 | B0 IG account 復旧（clip loop 停止の真因でもある。warmup 7日 = 最長 lead time なので早期着手） | vcsdd |
| 5b | B1-B4 IG marketing 最小 loop | vcsdd |
| 6 | B5 X poster | vcsdd |
| 7 | B6-B7 self-improve + attribution | vcsdd |
| 8 | A5 売れ筋 selector | vcsdd |
| 9 | B8-B9 launchd + account 戦略実測 | vcsdd |
| 10 | A7 通知受信 SSOT（Dais 確認要） | 随時 |
| 11 | §4 OSS 移設 | 14日安定後 |
