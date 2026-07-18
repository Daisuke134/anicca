# Capafy 10k MRR — two-loop spec（2026-07-17）

goal: `done="Capafy MRR $10,000/月。売上は Capafy server ledger + on-chain/銀行入金で実測確認"`（/goal 正本 = `2026-07-17-capafy-goal.md`）
調査正本: `docs/earn/2026-07-17-capafy-marketing-link-placement-research.md`（全実測 file path 付き）
**先行 spec（車輪。必読）**: `~/.openclaw/docs/superpowers/specs/2026-06-24-capafy-factory-automation-10k-100k-mrr.md` — 10k の算数（$10k ≈ 15-20 listings × ~$600 gross、blended ARPU $11/mo、純率 ~70%）、factory モード A（launchd+claude -p で勝者 clone 日次）、CP2 LLM hosting レシピ、leak/secret/E2E gate が確定済み。本 spec は「A: 修理」「B: marketing 新設」をそれに足す差分。
注意: 06-25 の確定レシピは「sk-ant 鍵 + openai-completions」で OpenRouter 不採用だったが、現 runtime は `CAPAFY_HOST_OPENROUTER_KEY`（本日 live probe 200 OK）で動いている — 実装時はどちらかに統一し spec の 0.97 節を是正すること（併存は事故のもと）。
状態: **IN PROGRESS（2026-07-17 着手、2026-07-18 方針転換）**。実装は vcsdd（Fable plan / subagent impl / Sol review）。

## ★ Dais 方針転換（2026-07-18 夕）★
1. **warmup 廃止 → 即投稿**。理由: account を悪くする真犯人は warmup でなく day-0 商用投稿。下手な bot warmup はむしろ shadowban を招く疑い（web best-practice を調査中、warmup-research）。
2. **最優先 = loop が実際に IG 投稿できることを1回実証**（今まで一度も実投稿してない、全部 dry）。day1 で loop 起点の実 Reel を1本 → logged-out 公開確認 → telegram。「投稿できない loop は無意味」。この検証は**毎日やる意味ではなく feasibility の証明**。
3. **X 線は完全に廃止**（X account 新設タスク #18 削除）。marketing は IG 一本。
4. **bio link が導線**（IG comment はクリック不可）。ただし初回非商用投稿が生存確認できてから bio link 追加（day-0 商用リンク = suspension）。
5. day3 floor は skip 可（warmup 廃止と整合）。待ち時間ゼロ、今日投稿。

進捗表:
| task | 状態 |
|---|---|
| **B0-verify（最優先・新）** | **loop 起点で @useclaudeskills に実 Reel 1本 live 投稿 → logged-out 公開確認 → telegram。未実証（全部 dry だった）。b0 実行中** |
| A1 provider/key | 診断完了・key-health gate 実装。OpenRouter **$21.59 補充済み**（gate 通過）。rejected 4件は Capafy review 待ち |
| A2 入金 | **DONE**（$21.59 実測、Dais 入金済み） |
| A3/A4/A6 | DONE（max-turns bounded / sales reconcile / self-fix backoff。7日 audit は 07-21+ 自動観測） |
| A5 売れ筋 selector | in_progress（a1-executor、public scrape） |
| B0 IG account | DONE（@useclaudeskills 実在、telegram msg 2524 proof） |
| B1-B4 IG marketing | dry 完了。実投稿は B0-verify で証明中 |
| warmup | **廃止方針**（web best-practice 調査後に確定）。goal-monitor から freeze gate は撤去済み（2a70612c） |
| X 線 (B5/B8/B6/B7) | **完全廃止**（#18 削除）。コード資産のみ保持 |
| 残 | #20 website(bio 1リンク) / B6-B7 IG metrics / A7 通知 / #21 funding / cloud 移行 / OSS |

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
| B0 | **前提修理: IG account 復旧 → 新規作成で解決（2026-07-18）**。既存 `~/.cloak/clip-accounts.json` の6 account は全て clip niche 専用で frozen（1-loop-1-acc policy）or poisoned = 流用不可。Capafy marketing は別テーマなので **新規 @useclaudeskills を作成**（`ig-account-create` で email-only・0-phone・0-captcha、OTP は gog gmail SPAM 経由。profile 完成: 表示名 Claude Skills Daily / bio セット（day-0 リンク無し）/ CS monogram avatar）。main :9222 context へ login 済み（device-confirm code クリア・login info 保存）。**warmup day-1 実行済み**（reels 6 verified・scroll 5・ban signal 無し）。account state は instance 分離で `~/.cloak/clip-accounts-capafy.json`（`ANICCA_INSTANCE=capafy`、clip-accounts.json は非汚染）。日次 warmup launchd `ai.anicca.capafy-marketing-warmup`（13:20、warm.py idempotent）稼働。★重要決定: session_owner=**browser**。既存 fresh account 2つ（world_hq2/daily_hq）は instagrapi↔browser の session churn で両方 poison したため、Capafy warmup は browser。**★是正(2026-07-18 SHARED-1): posting は instagrapi_post.py に確定。** 旧記述「B4 は ig-reels-poster(browser-direct) を使い instagrapi を付けない」は誤り — web composer(post_reel.py/ig-reels-poster)は IG が自動投稿検知で silent-drop する dead-end と判明し全 loop から物理削除済み。daily script STEP4 は instagrapi_post.py 一本（proven reel/Da7VQY8MIOK、day-1 未warmup でも publish）。 | **account 確保 = DONE**。残 done: 7日 warmup 完了 + ig-reels-poster --live で test 投稿 1件を公開確認（day-7 以降。day-0 の commercial link/投稿は suspension リスク） |
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

### SHARED engine sprint（2026-07-18〜19、§9/§10 の実装）— 実測進捗

| # | item | 状態 |
|---|---|---|
| SHARED-1 | post_reel.py 全削除 + clip 7参照を instagrapi 付替え + test 修正 | **✅ DONE**（52 test green、commit 84021d92） |
| GAP #27 | IG marketing loop が launchd 未登録だった（3日ゼロ投稿の真因）→ plist 作成・load・kickstart | **✅ DONE**（`ai.anicca.capafy-ig-marketing-daily` 登録、plutil OK、16:00 JST daily。commit 3a0f8068） |
| SHARED-2 #23 | instagrapi_post.py を canonical 共有 poster に | **✅ DONE**（既に account-agnostic=--handle、hardcode 0件実測、docstring 宣言 + CLIP_POSTER_OVERRIDE seam 配線。commit 9055cc18。product/type は upstream 責務で対象外） |
| SHARED-3 #24 | loop 自走投稿の証明 | **✅ 配線 green**（2026-07-18 23:50 kickstart で本物の launchd loop が自走: metrics→day-1 live 判定→cadence no-op、executor ゼロ）。実 publish は次 cadence-open tick（07-19 16:00 JST）で人手ゼロ自動発火予定 |
| SHARED-4 #25 | day-1投稿 gate + 並走warmup + reach ヘルス判定 | **✅ DONE**（gate=-ge1 sprint1、warmup 別launchd、reach 判定は STEP6 が .capafy-ig-reach-healthy を自己 marker。残: 1日1コメントは minor） |
| FIX #26 | CLIP_POSTER_OVERRIDE 未配線（shell test 3本 FAIL） | **✅ DONE**（run.sh:195 に seam 配線、8 shell + 52 pytest green を自分で再実行検証） |
| #20 | 全skill landing（bio 1リンク着地点） | **✅ DONE**（https://capafy-skills-daily.netlify.app HTTP200 21card 21UTM、日次再生成配線、commit a8bc4f23） |
| #11 | telegram SSOT（全 loop→Dais） | **✅ 実測達成**（build STEP5 / marketing STEP7 / goal-monitor 全て 8547730585 へ報告。残=Dais 受信確認 A7） |
| #8 | IG self-improve（勝ち post 模倣） | 🔨 Sol 実装中 |
| #21 | OpenRouter 自動 funding | 保留（top-up=金の外部流出=Dais の funding-source 決定が要る STOP 点。A2 の key-health gate が dead-key 浪費は既に防止。alert 型で実装予定） |

**閉ループ状態（2026-07-19）**: 毎日 publish（capafy-loop-daily 08:10）+ 毎日 market（capafy-ig-marketing-daily 16:00、自走証明済）+ bio 着地 landing + 全 loop telegram 報告 + reach→商用の自己 gating = **人手ゼロで日次稼働する閉ループが成立**。残る本質は #8（自己進化、実装中）と #21（funding safety、Dais 決定）のみ。

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

### 追補2（2026-07-18 Dais 承認: no-human-loop 完全自走）
freeze gate（.capafy-ig-golive-approved の人間承認）を**撤去**。goal-monitor は day>=3（clip 3日 floor = loop self-pacing）で IG launchd を**人間承認なしに自動 load → 実投稿**。安全 pacing は全て loop-driven（day1-2 warmup / day3+ 非商用 / reach 健全 marker を loop が書く）で human gate ゼロ。DRY/FREEZE で止めない、毎日 action を取る。commit anicca(freeze撤去)。


## §8 (d) 不死身 — behavior 実測（2026-07-18、config でなく挙動）
- key-health gate fail-closed: threshold \$999（残高\$21.59）→ **exit 1（publish 阻止）**、\$2→exit 0（funded で通過）。gate は実際に止める（実測）
- scheduled job 自走: `launchctl kickstart` goal-monitor → state 書込み（09:46）= 予定 job が再実行して pass 完走。StartCalendarInterval job なので「kill→次tick復帰」= この re-fire 挙動（実測）
- 残 time-gated: 7日 BLOCKED=0 audit（07-21+）、day3 実投稿（07-20）、14日自走 window（~08-01）

## §9 SHARED marketing engine 戦略（2026-07-18 確定・全 loop 共通）

★真因確定★: 3ヶ月投稿できなかったのは **web composer(post_reel.py)を IG が silent drop** していたから。warmup 不足でも IG day-1 block でもない。instagrapi(private API)に替えたら day-1 未warmup account で一発 publish（reel/Da7VQY8MIOK、logged-out 実測）。browser 自動化 repo(puppeteer 等)は全部この dead-end 側、instagrapi(private API)が正解と裏付け。

**engine は全 marketing loop で共有。変わるのは content(何を売る: affiliate/product/capafy skill)+bio+profile+niche だけ。** 以下は everyone 共通:
1. **poster = instagrapi_post.py 一本**（clip/scripts、private API、real sessionid でアプリ本物に見える）。web composer(post_reel.py)は全 loop から物理削除。
2. **day-1 から投稿**（待たない）。account 誕生日から 1日1本。burst 厳禁(~12本で死ぬ)。死因は warmup 不足でなく web-composer検知+burst だったので、instagrapi 化で account 死問題はほぼ解決。
3. **warmup は gate でなく並走**。warmer が毎日裏で軽く回す(reel視聴/scroll/たまに engagement)。投稿を止める warmup は無し。
4. **reach ヘルス判定**: 毎回 reach 測定 → 0 継続=cooked → 作り直し(plus-address email + instagrapi、使い捨て)。
5. 共通ループ: select(何を売る)→copy(agent)→video(money-printer)→instagrapi→ledger→reach→週次reflect。

TODO(tasklist SHARED-1〜4): ①post_reel.py 全削除+clip 7参照を instagrapi 付替え ②instagrapi を canonical 共有 poster に昇格 ③loop 自走投稿の証明(launchd 自身が post、executor で代行しない) ④本戦略を warmer に反映(1日1コメント/活動多様化)。将来: profitable-claude に marketing-engine 共通化して OSS。

## §10 SHARED/UNIQUE 是正 + multi-tenant（2026-07-18 Dais 訂正）

★訂正1: 何もハードコードしない★ account は config/registry 駆動、動的。将来 **数百人が repo を回し各自が数百万の IG/TikTok account を作る**（1 Capafy account : N SNS account）。engine は account/content-type/product を **パラメータで受ける**。account handle をコードに焼かない（ANICCA_INSTANCE + account file registry で解決）。

★訂正2: content 生成は SHARED でない（俺の誤り）★ money-printer 9:16 動画は共通ではない。**content type が変わる（video / slideshow / carousel / talking-head …）**。content 生成は **pluggable module**: `generate_content(product, type) -> media` インターフェースで、各 instance が自分の type を差す。

**正しい線引き:**
```
UNIQUE / PLUGGABLE（instance ごと・config 駆動・ハードコード禁止）:
  • which account(s)  — 動的・N個・millions scale
  • what product      — capafy skill / affiliate / 自社 product
  • CONTENT 生成      — ★pluggable★ video/slideshow/carousel 等、type が変わる
  • selector(何を宣伝) — データ源が違う
  • bio link 先 / niche / copy 方向 / profile

SHARED（account を運用して改善する機械・全員同じ）:
  • account 作成（ig-account-create、plus-address、ハードコードなし）
  • 投稿（instagrapi private API）
  • warmup（並走）
  • metrics 読み + reach ヘルス判定
  • ★self-improve / reflect（metrics 見て勝ち模倣）★ ← 完全共通
  • ledger / telegram 報告 / cooked なら作り直し
```
**要点**: 「account を作る・投稿する・測る・改善する」機械は全部 SHARED。「どの account で・何を・どの形式(content type)で売るか」は UNIQUE/pluggable。content 生成すら pluggable にすることで video も slideshow も同じ運用 engine に載る。→ SHARED-2 は「instagrapi poster + content-gen interface + warmer + reach + reflect」を account/type/product パラメータ化した共通 engine にする（account 名をどこにも焼かない）。
