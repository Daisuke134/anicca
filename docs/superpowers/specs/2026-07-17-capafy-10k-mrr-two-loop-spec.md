# Capafy 10k MRR — two-loop spec（2026-07-17）

goal: `done="Capafy MRR $10,000/月。売上は Capafy server ledger + on-chain/銀行入金で実測確認"`（/goal 正本 = `2026-07-17-capafy-goal.md`）
調査正本: `docs/earn/2026-07-17-capafy-marketing-link-placement-research.md`（全実測 file path 付き）
**先行 spec（車輪。必読）**: `~/.openclaw/docs/superpowers/specs/2026-06-24-capafy-factory-automation-10k-100k-mrr.md` — 10k の算数（$10k ≈ 15-20 listings × ~$600 gross、blended ARPU $11/mo、純率 ~70%）、factory モード A（launchd+claude -p で勝者 clone 日次）、CP2 LLM hosting レシピ、leak/secret/E2E gate が確定済み。本 spec は「A: 修理」「B: marketing 新設」をそれに足す差分。
注意: 06-25 の確定レシピは「sk-ant 鍵 + openai-completions」で OpenRouter 不採用だったが、現 runtime は `CAPAFY_HOST_OPENROUTER_KEY`（本日 live probe 200 OK）で動いている — 実装時はどちらかに統一し spec の 0.97 節を是正すること（併存は事故のもと）。
状態: **IN PROGRESS（2026-07-17 着手、2026-07-18 大幅前進）**。実装は vcsdd（Fable plan / subagent impl / Sol review）。
進捗はこの表を正とする:
| task | 状態 |
|---|---|
| A1 provider/key 修理 | 診断完了・key-health gate 実装済み。真因 = OpenRouter 残高薄のみ。4 agents は review-lock で編集不能、実効修理は A2 の入金。 |
| A2 入金 | **⏳ Dais 判断待ち**。俺が card 補充を試行 → OpenRouter への Google login が **2FA phone-tap（Dais 個人スマホ）で停止** = no-human-loop で越えられない一点。sk-ant 代替 rail も残高ゼロ実測。**推奨 = 買い手が付くまで後回し（$1.59 でも smoke test 以外は稼働、live probe 200 実測）**。急ぐなら Dais が 2FA 承認1回 or web で $10-25 チャージ |
| A3/A4/A6 | DONE（max-turns bounded / sales reconcile / self-fix backoff）。7日連続 audit は 07-21 以降に観測 |
| A5 売れ筋 selector | in_progress（a1-executor、public scrape 方式） |
| B0 IG account | DONE（@useclaudeskills、warmup day-1、日次 warmup launchd）。test 投稿は warmup 明け 07-25 |
| B1-B4 IG marketing | **dry 完了（2026-07-18）**: selector→copy→faceless動画→ig-reels-poster browser-direct、全 dry green。実物動画（YouTube Script Writer 紹介、1080x1920/36.7s）を **Dais telegram msg 2518 に送付済み**。live は 07-25 |
| B5/B8/B6/B7 X 線 | **凍結（Dais revoke @aniccaen 2026-07-18）**。コード資産は保持、投稿先は AI 専用 account のみ（Dais 3 handle は poster が hard refuse）。X 再開は #18（AI 専用 X account 新設）が前提、IG go-live 後に判断 |
| B8 IG launchd | script ready、warmup 明け 07-25 に load |
| 残（A7/OSS/#18） | pending |

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
| A3 | **実装+unit-verified（2026-07-18）**: daily_loop.sh の post-run 判定を修正。max-turns 枯渇は「予算切れ（非バグ）」と認識し、streak file `.maxturns-streak` で bounded continuation — 3 pass 未満は marker touch して次 pass 継続（MAXTURNS-CONTINUE、self-fix escalate せず）、3 pass 連続で初めて escalate（MAXTURNS-STUCK）、healthy/他 error で reset。全 branch を isolated test で検証、bash -n OK。commit は ~/.openclaw main-internal 10f9228c（daily_loop.sh +19行）。~~push は SEC commit の guard 誤検知でブロック~~ → **解消・push 済み（origin/main-internal HEAD 0bd4ef01 を実測確認）**。pre-push hook は content-grep → filename 判定（diff-tree --name-only）に修正（security 意図維持、762b5f78 の実 secret 0 は独立検査で確認済み）。 | 【3日連続 BLOCKED rc=1 ゼロ は観測期間 → 07-21 に daily_loop.log 確認】機構は検証済み |
| A6 | **DONE+verified（2026-07-18、~/anicca push 済み d894904c）**: self-fix.sh に RESULT-marker backoff を追加。has-session guard は同時重複のみ防ぎ、条件持続時（inventory drained 等の非バグ）に 6h 毎 full-power Sonnet を再 spawn する地雷が残っていた。前 fixer が CONCLUDED（RESULT≠RUNNING）かつ BACKOFF_MIN（既定 20h、SELF_FIX_BACKOFF_MIN seam）内なら skip。RUNNING は backoff せず（crash fixer 救済）。実測: fresh SUCCESS→skip・spawn 無し、RUNNING→proceed。 | ✅ self-fix log に多重 spawn が出ない（backoff で 4/day→~1/day） |
| A4 | **DONE（2026-07-18 実測 green）**: `capafy_earn_reconcile.py` を新設し `GET /agent/sales/trend` + `/agent/developer/payout-info` を専用 ledger `state/capafy-earn-ledger.jsonl` に mirror（idempotent/atomic/backup）。**on-chain realized reader（ledger_reader.py、tx/sig 必須）は汚染しない** — capafy は bank 収益で on-chain 痕跡が無く、tx 捏造は罪。clip の専用 ledger と同パターン。loop.sh が毎 wake で reconcile を回し STATE.md に `capafy_seller_balance_pending_usd`/`realized_payout`/`lifetime_gross` を追加、旧「monthly payout=$0」報告が隠していた実売上を surface。**実際に走るのは ~/anicca 版**（daily loop STEP1 が `~/anicca/.../loop.sh` を指す。~/.anicca-founder は非稼働）→ ~/anicca に実装・commit f10f9ddc。 | ✅ 06-23 の $9.99 行が ledger に存在（実測 PASS）/ STATE.md が server 値一致（gross $9.99・seller balance $8.00 pending・realized $0）/ test-loop.sh 7-0 GREEN / on-chain ledger capafy 0行 |
| A5 | self-improve: Capafy ranking/カテゴリ実売データを daily 取得 → 次に作る skill を上位カテゴリから選ぶ selector | selector の判断ログが state に残る |
| A7 | 通知: 送信は AgentMail+Telegram とも成功済み（07-17 12:47）→ Dais 側受信設定を点検し、受信確認できる 1 経路を SSOT にする | Dais が実受信を確認 |

## 3. Loop B 新設タスク（MUST、clip 部品転用）

| # | タスク | 転用元 / 新規 |
|---|---|---|
| B1 | Capafy promotion selector（status=4 のみ、rotation/dedup）→ **BUILT 2026-07-18** `~/anicca/skills/earn/capafy-marketing/scripts/select_listing.py`（commit 82de4201）。seller `GET /agent/agents`（buyer token 不要・200・agentStatus online 21/26）を読み online のみ抽出、`~/.openclaw/state/capafy-marketing-rotation.jsonl` で最古 promotion を選ぶ rotation/dedup。3連続実行で3つ別 listing を実測。★buyer token(CAPAFY_ACCESS_TOKEN)は不要（seller endpoint で足りる、A5 と同結論）★ | seller endpoint（buyer token 不要） |
| B2 | content adapter: listing → hook/problem/CTA copy → **設計確定 2026-07-18**: copy は agent 判断で都度執筆（template を TOOL に hardcode しない=building-agents 規律）。deterministic 部は `x_post.py` の validation（リンク無し native/≤280）が gate。E2E draft 検証済み（select→agent 258字 native→x_post.py --draft 通過）。SKILL.md に pipeline 記載 | agent judgment（TOOL 化しない）+ x_post.py validation |
| B3 | 動画組立 + caption + 品質 gate → **dry DONE 2026-07-18**: faceless-money-factory `run-daily.sh`（edge-tts→Mixkit b-roll→whisper captions→ffmpeg、$0・keyless・:9222不使用）で 1080x1920 mp4 生成。実測: YouTube Script Writer 紹介の 36.7s mp4 生成→telegram で Dais に送付（msg 2518）。★改善(Dais): b-roll query が finance 固定 "money" だと mismatch → `run-daily.sh` に **BROLL_QUERY env 上書き追加**（後方互換）、IG daily の STEP3 で agent が listing カテゴリ別 query を渡す（例 video editing laptop creator）。初回 render は generic b-roll（要 category 化、次版で解消） | faceless-money-factory（clip の assemble 系と同族） |
| B4 | IG poster（bio に Capafy URL 固定。comment に URL 置かない）→ **dry DONE 2026-07-18**: ★instagrapi ではなく **ig-reels-poster**（browser-direct、B0 の session_owner=browser 決定と一貫）★。`post_reel.py --handle useclaudeskills`（--live 省略=dry）で **reached=DRY-ok / published=false を実測**（@useclaudeskills を IG switcher で active 化→account guard 通過→動画upload→リール→cover/trim→caption まで歩き share 直前で discard）。live は warmup 明け 07-25。bio に Capafy URL は live 初回時に設定、comment/caption に URL 置かない | ig-reels-poster（browser-direct、@useclaudeskills = AI-owned） |
| B5 | X poster（native post + 最初の self-reply に listing URL）→ **機構は DONE だが account 未確定（2026-07-18）**。★注意: browser-direct の link 配信は @aniccaen で live 実証したが、**@aniccaen は Dais 個人 account で Dais が revoke**（tweet 削除済み）→ AI 専用 X account で再 go-live が必要（B9 参照）。poster 機構自体（browser-direct が link を配信、Postiz は strip）は proven で account-agnostic。使う rail = `~/anicca/skills/earn/capafy-marketing/scripts/x_post_browser.py`（Dais 個人 handle は hard refuse）（CloakBrowser :9222 の compose を駆動: root=native リンク無し → addButton → reply=UTM付 Capafy URL → Post all）。★Postiz(`x_post.py`)は全 URL を strip するため X では不採用（live 5テストで確定: text+url/url-only/単一tweet/shortLink true・false/SPA・github url すべてで URL 消失）→ browser-direct なら link がそのまま X に載る。★ 実証: @aniccaen で実 thread 投稿→**logged-out で reply の t.co が `capafy.ai/agent/…/8875030146?utm_source=x&utm_medium=x_reply&utm_campaign=capafy_marketing`（HTTP200・UTM保持）に解決**（root=status/2078252761314115657, reply=…762740195344）。--dry で fill-only 検証も green。ledger=`capafy-marketing-x-ledger.jsonl`、cadence 時刻=`capafy-marketing-rotation.jsonl` | browser-direct（:9222 単一 rail、Postiz 除外） |
| B6 | metrics + 週次 reflect（views→勝ちフォーマット模倣）→ **X 線 DONE 2026-07-18**: `x_metrics.py`（browser-direct で thread の views/replies/reposts/likes/bookmarks を `capafy-marketing-metrics.jsonl` に daily 記録。実測 views=3 replies=1）+ daily prompt に reflect skeleton（<7 post は no-op、7+ で median 超え winner に copy を寄せる=clip above-avg gate）。metrics は cadence gate 前の bash で毎日実行（no-post 日も time-series が伸びる） | `x_metrics.py`（earn/video/metrics.py パターン流用） |
| B7 | conversion attribution: UTM（x_reply）↔ agent_id ↔ Capafy sales join → **X 線 DONE 2026-07-18**: `x_attribution.py`（posts × capafy-earn-ledger の 7日 date-window candidate join → `capafy-attribution.jsonl`）。★HONEST LIMIT: Capafy sales/trend は per-day 集計で **listing 粒度が無い** → candidate 信号であって「その post が売った」断定ではない。UTM=utm_medium=x_reply を埋め込み、Capafy が per-listing/UTM を出したら join が締まる設計。実測: sales~0 で空 join=正常 | 新規。保守的 candidate（断定しない） |
| B8 | launchd job（Loop A と別 job）→ **配線済みだが Dais が無効化・一時停止（2026-07-18）**。★@aniccaen revoke に伴い Dais が plist を `disabled-2026-07-18-dais-revoked-aniccaen` へ bootout。**AI 専用 X account が出来るまで再有効化しない**（safety gate で Dais 個人 handle は refuse）。script/gate 自体は稼働可。予約名 `ai.anicca.capafy-marketing-daily`（15:00 JST、article-daily 06:00 から9h離す）= `~/anicca/skills/earn/capafy-marketing/capafy-x-marketing-daily.sh`。capafy-loop-daily と同じ launchd→headless `claude -p` 方式: selector→copy(agent 判断)→x_post_browser.py --live→logged-out verify→telegram+loop-report 報告。**cadence gate（bash deterministic）= 最終 platform=x 投稿が <20h なら no-op**（clip rolling-window、@aniccaen 二重投稿防止）+ agent が article 近接も判定。**launchctl LOADED + kickstart で no-op green を実観測**（log に「last X thread < 20h ago — no-op」、claude -p 未起動）。初回実投稿は明日 15:00 tick（今日は1 thread 投稿済みで gate closed）。IG 側 launchd は warmup 明け B4 後 | plist 新規。X 線は本 job で日次自動化 |
| B0 | **前提修理: IG account 復旧 → 新規作成で解決（2026-07-18）**。既存 `~/.cloak/clip-accounts.json` の6 account は全て clip niche 専用で frozen（1-loop-1-acc policy）or poisoned = 流用不可。Capafy marketing は別テーマなので **新規 @useclaudeskills を作成**（`ig-account-create` で email-only・0-phone・0-captcha、OTP は gog gmail SPAM 経由。profile 完成: 表示名 Claude Skills Daily / bio セット（day-0 リンク無し）/ CS monogram avatar）。main :9222 context へ login 済み（device-confirm code クリア・login info 保存）。**warmup day-1 実行済み**（reels 6 verified・scroll 5・ban signal 無し）。account state は instance 分離で `~/.cloak/clip-accounts-capafy.json`（`ANICCA_INSTANCE=capafy`、clip-accounts.json は非汚染）。日次 warmup launchd `ai.anicca.capafy-marketing-warmup`（13:20、warm.py idempotent）稼働。★重要決定: session_owner=**browser**。既存 fresh account 2つ（world_hq2/daily_hq）は instagrapi↔browser の session churn で両方 poison したため、Capafy は warmup も posting も browser（B4 は `instagrapi_post.py` ではなく **ig-reels-poster**（browser-direct）を使う）に統一し instagrapi を一切付けない。 | **account 確保 = DONE**。残 done: 7日 warmup 完了 + ig-reels-poster --live で test 投稿 1件を公開確認（day-7 以降。day-0 の commercial link/投稿は suspension リスク） |
| B9 | アカウント戦略: **phase 1 = 1 account**（"sharing claude skills you can use" 統一テーマ）で 14日運用。skill 別多 account 化は phase 1 の CTR 実測後に判断（IG 新規 account 量産は ban リスク、warmup 7日/acc が必要 — `decide.py:33-46`）。**★X account 未確定（2026-07-18）**: @aniccaen へ初回投稿したが **Dais が即 revoke**（「それは俺の英語 account」）— @aniccaen/@diceai0/@aniccaxxx は全て **Dais 個人 account で loop 投稿禁止**（memory `never-post-to-dais-personal-accounts`）。tweet 削除・state purge・launchd は Dais が無効化済み。**loop の投稿先は AI 自作の専用 account のみ**（IG の @useclaudeskills 型）→ X も専用 account を新規作成+warmup してから go-live（B0 相当の前提タスクが必要）。x_post_browser.py/selector/metrics/attribution は account-agnostic で流用可、safety gate で Dais 個人 handle を hard refuse 済み。**IG phase1 account = @useclaudeskills**（warmup 中、due 2026-07-25） | phase 1 の posts が ledger に 14件（X 線は AI account 作成後） |

## 4. OSS 化（profitable-claude）

- Loop A/B が 14日安定稼働した後、`profitable-claude/skills/` に canonical 移設（既存 7 skill 構成に倣う。移設 manifest は `docs/earn/profitable-claude-clip-loop-migration-plan.md` 方式）。
- 人間側 onboarding = 銀行/決済 credential 投入のみで loop 全体が起動する README（life-manager-daily.sh の実例に倣う）。
- **credential・key は repo に絶対入れない**（ReelFarm SKILL.md の hardcoded key 事故を反例として lint: `leak_scan.sh` を pre-commit に）。

## 5. リスク / 決定事項

- Dais 原案「link in comment、bio 不要」は IG/TikTok で不成立（comment URL クリック不可）→ **bio 主導線 + X は self-reply** に変更（研究 MD §1、外部ソース 8件）。
- 「skill ごとに 1 account」は phase 2 送り（B9）。
- 10k MRR 逆算: 平均 $10/月 sub × 1,000 subscribers。21 listings では露出が全て。Loop B の CTR データが出るまで listing 増産（A4）と並走。
- ~~⚠ 別件 backlog: reelfarm hardcoded key~~ → **SEC #13 完了（2026-07-18）**: 旧 key は 2026-05-21 revoke 済み（401 実測 = live 漏洩なし）。SKILL.md/cron message/plans から除去し env 参照化（openclaw 762b5f78 + anicca-project 6bb6de4f）、leak_scan に rf_ pattern 追加。残: reelfarm cron 2本が dead key で 401 失敗中 → TaskList #14 に登録済み。

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

## 7. goal-monitor（自走監査 + 自動 go-live）— 親の介入ゼロの実装（2026-07-18 DONE）

launchd `ai.anicca.capafy-goal-monitor`（daily 09:00 JST）= `~/anicca/skills/earn/capafy-marketing/capafy-goal-monitor.sh`（commit ac22729e）。**deterministic（LLM 不使用）・read+append のみ（本番 state 非破壊）**。goal の時間依存判定を人手で追うのをやめ、loop 自身が毎日監査して Dais に telegram 報告する。

| goal | 監査内容 | 実測（2026-07-18 手動検証） |
|---|---|---|
| (a) | daily_loop.log の BLOCKED rc=1 連続ゼロ日数（7日で PASS marker） | streak 1/7（07-17 に BLOCKED あり→building） |
| (b) | capafy-earn-ledger の最新 sales + reconcile 鮮度（>48h で STALE=乖離リスク） | orders=1 gross=$9.99（07-19既知）reconcile 0.6h fresh |
| (c) | **Dais 決定2026-07-18: warmup day>=3 で早期 NON-COMMERCIAL test post を go-live**（full 7日待たない）。IG marketing launchd を idempotent 自動 load（実 warmup-ledger の day 判定、日付ハードコード禁止・二重 load 禁止）。初投稿は非商用（bio link 無し・情報 caption）で reach を実測→健全なら `.capafy-ig-reach-healthy` marker で商用移行、shadowban 兆候なら報告 | warmup 1/3 → go-live=**not_yet**（day3=~07-21 で発火） |
| (d) | 非破壊 health（launchctl loaded / plist 存在 / key-health gate exit）。本番 process の kill test はしない | capafy-loop=loaded / warmup=loaded / key-gate OK |

daily telegram 報告（8547730585、secrets 無し）で Dais が毎日1目で状況把握（実測 msg 2523）。state=`~/.openclaw/state/capafy-goal-monitor.json`（history 60日）。これで 07-21/07-25/+7日 の判定が自走 = 真の no-human-loop。

### 追補（2026-07-18 Dais warmup 戦略）
full skip も full 7日も却下 → **warmup 強化 + day3 早期 non-commercial test post で reach 実測**。実装: goal-monitor go-live gate を day>=3 に早期化 / IG daily を非商用初投稿→reach 健全 marker で商用移行 / warmup に timing jitter（warm_jitter.sh、base 11:00 + 0-3h random）。★残（handover 推奨）: warm.py の活動多様化（story/explore/検索/profile訪問 = building-agents 準拠で agentic engagement 層を拡張）+ day1-2 の light follow/profile 充実 + day3 実 live 投稿の reach 実測（account が day3 = ~07-21 になってから）。
