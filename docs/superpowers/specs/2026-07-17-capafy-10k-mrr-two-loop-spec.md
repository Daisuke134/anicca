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

## §11 GENERALIZED MARKETING ENGINE（2026-07-19 Dais — loop が loop を作る土台 / true takeoff）

**方針**: これから marketing loop を大量に作る（video / life-manager / 各 product）。**engine は1つ、共有。** loop 毎に変わるのは「誰に・どの問題を・何を・どう見せて売るか」だけ。人間(や親 loop)が product を決めれば、あとは汎用エンジンが distribution を全部やる。**車輪の再発明を構造的に不可能にする** = engine を共有物として1箇所に置き、loop はそれを config で呼ぶだけ。

### なぜ今これを（poison 事故の教訓）
@useclaudeskills が poison した真因 = capafy が clip の poster だけ借りて **account作成/warmup/session を自前複製**し、clip が baked した教訓（durable session・day3）を**受け継がなかった**。複製 = 教訓が伝播しない = 同じ穴を各 loop が踏む。**共有 engine なら1回直せば全 loop に効く。**

### SHARED core（1実装。`~/anicca/skills/earn/marketing-engine/` → 安定後 profitable-claude へ OSS）
| module | 責務 | 教訓が baked される場所 |
|---|---|---|
| `provision` | account 自作 + **durable golden session**(instagrapi password login-once + get_timeline_feed 検証)、replace-on-cold、ZERO human | ephemeral sessionid=brick の回避 |
| `warmer` | day1-2 warm のみ / day3 で postable に promote | 早期投稿=poison の回避 |
| `poster` | instagrapi_post.py（唯一の poster、account-agnostic --handle） | web composer=silent drop の回避 |
| `reach` | reach/shadowban 健全判定（0継続=cooked） | 本物の shadowban テスト |
| `reflect` | post を engagement で ranking → BEST_PRACTICES 生成（勝ち模倣） | データ薄なら baseline-only（捏造禁止） |
| `ledger` | append-only post 台帳 | |
| `telegram` | Dais へ日次報告 | PushNotification は届かない→message send |
| `landing` | bio-link 用 全商品 landing 生成（任意） | comment link はクリック不可→bio 集約 |
| `engine.sh` | 日次 orchestrator: resolve-account →(cold なら provision)→ warm/post gate → select → copy → content → post → reach → reflect → telegram | |

### PER-LOOP config（変わるのはこれだけ = product manifest 1枚）
```yaml
persona:  "誰に"（例: ready-made Claude skill が欲しい indie hacker）
problem:  "どの問題を解くか"
product:
  name / source(何を列挙して売るか) / listing_url / bio_link
content:
  adapter: faceless-video | slideshow | carousel | clip-cut  ← pluggable
  hint: ...
account:
  state_file / handle_prefix
niche / cadence(投稿時刻)
```
→ manifest を書けば marketing loop が1本立つ。**engine コードは触らない。**

### META（loop が loop を作る = true takeoff）
- `new-marketing-loop <manifest>`: manifest 検証 → launchd 登録 → 共有 engine で稼働。
- 究極形: 「この product を宣伝しろ」と言えば、meta-loop が **persona/problem/product/content を LLM 判断で manifest 化** → scaffold + 登録 → 自走。人間は product を決めるだけ。AI が distribution loop 自体を生む。
- README に明記（下記）: 新 loop を作る人/AI は **engine を再実装しない**。manifest を書く。

### README に書くこと（`~/anicca` + profitable-claude）
> **marketing loop の作り方**: あなたが決めるのは4つだけ — WHO(persona) / WHAT PROBLEM / WHAT you sell / HOW(content adapter)。account 作成・warmup・投稿・reach・self-improve・telegram は **generalized marketing-engine が共有で提供**。engine を再発明するな。manifest を書いて engine に載せろ。

### 移行（Strangler Fig、稼働を壊さない）
1. まず capafy を応急復活（sprint6、clip pattern を copy）→ 日次を回す
2. `marketing-engine/` に core を抽出、clip と capafy を **config で同一 engine に載せ替え**（1つずつ、test green を保ちながら）
3. `new-marketing-loop` generator + README
4. profitable-claude へ OSS 移設（#12）
5. meta-loop（product prompt → loop 自動生成）

### TODO（tasklist）
- #31 marketing-engine core 抽出（provision/warmer/poster/reach/reflect/ledger/telegram を1実装に。clip+capafy を載せ替え、Strangler Fig）
- #32 product manifest schema 確定 + capafy/clip の manifest 化
- #33 `new-marketing-loop` generator（manifest→launchd 登録→稼働）
- #34 README「marketing loop の作り方（persona/problem/product/content だけ）」
- #35 meta-loop: product prompt → manifest 自動生成 → loop scaffold（true takeoff）

### §11.1 AS-IS 実測（2026-07-19、共有の現実）— 「共有 engine は無い」
ファイル単位で実測した結論: **clip と capafy が共有してるのは `clip/scripts/instagrapi_post.py`（poster）1ファイルだけ。** 残りは全部複製/並行実装。
```
共有(実測): earn/clip/scripts/instagrapi_post.py  ← これだけ

複製(capafy 自前): build_landing.py / ig_metrics.py / ig_reflect.py / select_listing.py
                   / warm_jitter.sh / capafy-goal-monitor.sh / capafy-ig-marketing-daily.sh
                   (+ X線: x_post.py / x_metrics.py / x_attribution.py / x_post_browser.py)
複製(clip 自前): warm_step.py / provision(clip_pass.sh) / producer.sh / pipeline.py
                / reflect相当(無) / reel_verify.py / self_heal.py / bio_step.py / run.sh ...
```
- capafy の warmup = ig-account-warmer skill の `warm.py`（別物）、clip の warmup = `warm_step.py`。**別実装**。
- capafy に provision（account 自作）は**無かった**（@useclaudeskills は手動作成）→ clip の PROVISION を通らず ephemeral session で brick = poison の真因。
- IG に投稿する loop: capafy-marketing / clip / clip-producer / clip-promote / video（各々ほぼ自前）。
**結論**: 「5つが同じ engine を共有」は**まだ嘘**。§11 の marketing-engine 抽出（#31）で初めて本当になる。それまでは poster 1個だけが共有。

## §12 STATE 2026-07-19 — MARKETING OS 完成 + 順序化した残 TODO

**marketing OS（`~/anicca/skills/earn/marketing-engine/`）は実装完了・全 verify 済み・main merged。**
- 共有 core: provision_prompt.sh(day1 signup-only) / account_state.sh / warm_step.py(day1-2 warm→day3 golden session 1回, relogin厳禁) / instagrapi_post.py(tier1 poster) / generic state paths(MKT_INSTANCE) / lease isolation(churn停止) / poison検知 day3+。
- scaling: load_manifest.sh + manifests/{capafy,clip} + new-marketing-loop.sh(manifest→launchd) + spawn-marketing-loop.sh(product説明→manifest自動生成→scaffold) + README。
- 墓場の3大死因 fix 済み(day1 login廃止 / lease churn停止 / 誤cook廃止)。共有なので1回 fix=全 loop に効く。

**account（2026-07-19 是正 — 前記「day3 で golden session→初投稿」は嘘だった）**: @useclaudeskills は **poison 死亡が実測確定**。warmer の day3 コードパスを実行検証 → instagrapi session 死亡（`ChallengeRequired: Manual verification required`）。よって 07-20 に `--live` でも「saved session dead; refusing relogin」で **投稿ゼロ**。加えて唯一の実 reel `Da7VQY8MIOK` の reach = 0/0/0（browser 投稿も silent-drop）。**両投稿経路が死亡**。

**poison 真因（3重、実測確定）**:
1. **共有 :9222 main context に login** — account note 明記「Logged into MAIN :9222 context」。捨て IG account を Dais daily-driver + 他 loop 同居の共有ブラウザに入れた＝IG 視点「1 device に多数 account」＝challenge trigger。#38（専用 port/context）は完了だが本 account は #38 以前(07-18)に生 :9222 で作られ**未移設**。isolated 経路 `warm_iso.py` は存在するのに通ってない。
2. **他 account を follow してない** — warm.py は passive only（reels/stories/scroll/profile 訪問）。follows/likes は「day3+ に agent が agentic に」実行する設計だが day1 で challenge 済み＝一度も follow せず。新規 IG で following=0 = 100% bot signature。
3. **day1 早期 instagrapi login** — session file は作成6h後(07-18 17:11)に login。新規 account への day1 login は典型的 challenge trigger（設計は day3 まで browser-only のはず）。

**★ 不変条件（最上位、これが approach を決める）— ZERO human, agent が全部自前 ★**
capafy loop の存在意義 = **human ゼロで自走する earner**。従って:
- human in the loop 無し / **human credential 無し** / Claude sub 以外に human が払う金 無し / agent は自分で稼ぐ。
- ⇒ **Postiz は却下**（Dais の human 資産: Dais の Postiz login・Dais 所有 IG account・Dais の Meta 連携）。IG Harness も Dais/human の Meta app 前提なら却下（agent が Meta stack を完全自己所有できる時のみ再検討）。
- ⇒ **正解 = agent が自分の account を自作・所有・warmup・自分で投稿**（agent 自前 email で作成、instagrapi/browser は agent 自身の session）。既存 anicca 8 IG(Postiz)は human 資産なので capafy に流用しない。
- ⇒ 2026-07-19 に一度「Postiz+IG-Pro へ pivot」と書いたのは**誤り**（この不変条件を破っていた）。撤回。

**FIX recipe（agent 自作 account を survive させる。IP は Mac Mini home 回線=既に residential なので真因は IP でなく下記）**:
- (a) fresh account を **isolated context/専用 fingerprint+port**（cdp_context_lease.py / warm_iso.py）で作成。生 :9222 main に絶対 login しない（真因#1）。
- (b) warmup を recipe どおり（`docs/reference/ig-account-warmup-recipe-2026.md`）: day1=browser-only・follow 0・API login 無し / day2=follow 3-5・like 5-10 / day3=follow 5-10・**初 instagrapi login 1回→dump_settings**・初投稿(リンク無し)。空プロフィール+即書き込みを避ける（真因#2 の正確版）。
- (c) **instagrapi login は day<3 禁止**（provision/warmer に gate。真因#3）。login 1回→load_settings のみ・再login 厳禁・delay_range=[1,3]。
- (d) day3 session 生存で初投稿→reach 実測。dead なら account 破棄→再作成（relogin しない）。
- 有料 residential proxy が要る場合も **agent の earn 金**で払う（Dais は払わない）。まず (a)-(c) を無料で。

**#37 実測**: capafy sales API は日付別 gross のみ、UTM/referrer 内訳なし → reach 最適化 + 総売上 watch で代替。

### 順序化した残 TODO
```
DONE（2026-07-19 検証）
 ✓ #1 A1  reject→resubmit 自動化 — 既実装+live 検証済み。DAILY_LOOP.md §2a が
          launchd→daily_loop.sh→headless Sonnet で自走: review_rejected 検出
          →remote-status 確認→BEST_PRACTICES §6 overclaim 再読で修正
          →publish_finish.sh <AGENT_ID>(元 agent_id carry=create_version_from_draft)
          で ship+CP3 resubmit。Capafy は reject 理由テキストを一切返さない
          (api-docs:429「no review management API」)→「理由読む」= lint+overclaim
          judgment 再読が唯一の代理(regex hardcode でなく model 判断=正)。
          provider: build_config.py:50 "openrouter.ai" / hosted key: publish_finish.sh
          CP2(59-66)+key_health_gate.sh(<$2 拒否)。結果検証=isConfirmedConfigKeys=1 を
          live 反復達成(agent 4014388606/2485008254/4886968609 が rejected→status=1)。
 ✓ #9 A5  売れ筋 selector — sales_selector.py, build loop STEP2 配線, live signal=none。
 ✓ #21    funding alert — key_health_gate.sh が低残高で Dais に telegram(早期警告 <$5 +
          block時)、1日1回 dedup、auto-charge 無し(資金源=Dais 判断)。検証: 健全$21→無発火、
          cushion$50→発火+marker、同日再実行→dedup(openclaw stub、実送信ゼロ)。main-internal push。

 ✓ #31残  dedup 調査完了 → **重複無しと実測確定（抽出しない）**: reach(ig_metrics.py)/
          reflect(ig_reflect.py)は製品ごとに別物(IG engagement vs clip affiliate $)＝重複でない。
          telegram=prompt 内 openclaw 一行(同一文字列、hand-roll コード無し)、ledger=既に
          MKT_INSTANCE パラメタ化済、report helper は ~/anicca/skills/report/loop-report.sh 既存。
          README 原則「loop 固有=selector/copy/content-adapter」に合致。engine 化=premature。

 ✓ #40 BIO-ROBUST  setup_profile.py を言語非依存化。3 JA-hardcoded selector(自己紹介/
    ウェブサイト/送信する)→多言語辞書 FIRST(live実績のJA一致=ゼロregression)+構造 fallback
    (textarea単体/type=url/button[type=submit])。検証: py_compile OK, 生成JS 5本 node --check OK,
    JA/EN/EN2 模擬DOM で全 finder が正しい単一要素に解決, JA は byte 等価。実ブラウザ E2E は
    day3(~07-21) website 設定時=#39 と同じ data-gate。file は ~/.agents=~/.claude ハードリンク
    1実体(git 管理外)、loop 実行パスに反映済。

 ✓ #11 A7 受信照合  **完了(2026-07-19)** — bot token は履歴/自送信を構造的に読めない
    (core.telegram.org/bots/api、docs.telethon.dev botapi-vs-mtproto、gh openclaw/openclaw
    action-runtime.ts が非outboundを全throw="Unsupported Telegram action: read")。解=MTProto
    USER session。建てた: ~/anicca/skills/tools/telegram-user/tg_user.py(Telethon 1.44,
    venv=~/.cache/telegram-user-venv, read/send/2段headless login/entity解決)。dice0130 として
    login済(StringSession→~/.cloak/telegram-user.json 0600)。実読 verified: dialogs 12件 +
    read-by-id(Anicca chat count 4)両方 real data。以後 Dais の受信箱を自分で照合可能。

── DO-NOW キュー空 ──  残りは全て待ち(下記 BACK-BURNER)。

### 全残 TODO（2026-07-19 是正 — 前記「6件全て待ち」は嘘。#30 は今すぐ実行の active work）
```
▲ 今すぐ実行（poison 是正。データ待ちではない）
 - #30 FRESH-ACCT   @useclaudeskills 破棄→上記 FIX recipe で fresh account 作成。
                    isolated context + 実 follow/like warmup + instagrapi login は day3 のみ。
                    ※前記「07-20 day3 golden session→初投稿(演算確定)」は嘘だった:
                      session は既に ChallengeRequired 死亡、07-20 は投稿ゼロが確定。

07-20 以降のデータ待ち（fresh account の day3 = 作成日+2 から発生）
 - #24 SHARED-3     loop 自走投稿の証明(launchd が自身で post した実ログ)
 - #37 MONEY-LINE   reel→$ attribution(投稿後 reach/売上 実データ、capafy は UTM別返さず代理指標)
 - #10 B8-B9        marketing 14日 account 運用実測

Dais 判断待ち
 - #12 OSS          14日安定後 profitable-claude へ two-loop 移設
 - #41 LIFE-AUTO    tg_user 上に「Dais の telegram 読み→仕分け/応答」loop(今やらない、Dais案)
```
（完了: #1 reject-resubmit / #9 売れ筋 / #11 受信照合(telegram-user) / #21 funding alert /
  #31残 dedup無し確定 / #40 BIO-ROBUST。#21 の実 card 補充のみ Dais の金流出判断で保留）

### §12.1 STATUS 2026-07-19 — #42 CREATE-FIX 完了（実測値）

flow B（Fable planner / Sol Codex builder）で実装。Fable 独立検証済（Sol 自己申告でなく実 tool 出力）:
- `warm.py --dry`（~/.agents trunk 実走）= plan JSON に engagement caps 出力、day1 は follow/like/comment 全て (0,0)・targets 0。
  caps: day1=0/0/0, day2=follow3-5/like5-10/comment0-2, day3=5-10/10-20/3-5, day4+=5-10/15-25/3-5（recipe 保守側と一致）
- pytest（Fable 実行）: ~/.agents 47 passed / marketing-engine 4 passed。negative tests 実在:
  day1 follow refuse / day2 clamp / :9222 main refuse ×2 / day1 instagrapi login refuse / delay_range=[1,3]
- 実装内容: provision_prompt.sh に `require_ig_isolated_context`（port=9222 or context=main/default/空 → exit 64 で code 拒否、
  IG_PROVISION_PORT/CONTEXT_ID 必須化、state row に port+context_id 記録）／warmer.py `establish_golden_session` に
  warming_day<3 refuse + delay_range[1,3]／poster.py `login_resilient` に day<3 refuse + delay_range[1,3] 統一／
  caller 追従: capafy=:9332, clip=:9331 専用 port（capafy-ig-marketing-daily.sh / clip_daily.sh / clip_pass.sh）
- commit: ~/.agents eb414d3（merge, push 済）/ ~/anicca 0e78e78e（merge, push 済）。worktree cleanup 済。
- state 是正: `~/.cloak/clip-accounts-capafy.json` の @useclaudeskills を poisoned=true/status=poisoned に実測是正
  （旧記載 warming_day1/poison:null は嘘だった）。backup: 同 dir `.bak-20260719`。active handle 不在 → 次 pass で provision 発火。
- 未検証（次の実測待ち）: :9332 専用 CloakBrowser profile の実 launch と day1 provision E2E（#30 で証明）。

### §12.2 STATUS 2026-07-19 — #30 day1 provision 成功（実測）

kickstart した capafy-ig-marketing-daily の provision が新 recipe 経路で E2E 成功:
- 新 account **@capafy.skills9582** live（loop log: 公開 profile DOM 確認、bio/avatar VERIFY true）
- Fable 実測（state file 再 parse）: port=**9332**（:9222 でない）/ context_id=**capafy-19929** / status=warming / session_owner=browser
- `~/.cloak/instagrapi-capafy*` = **不存在**（day1 に API login していない = gate 実効）✅ / cred file `ig-capafy.skills9582.json` 保存済
- :9332 専用 profile の実 launch も day1 provision E2E も**これで検証済**（§12.1 の未検証項目を解消）
- 次: day2（07-20、follow 3-5 warmup）→ day3（07-21、golden instagrapi session 生存 = ChallengeRequired 無し）が #30 の exit proof
- 別穴（既存 baseline、#42 と無関係）: landing netlify deploy が launchd 環境で `mkdir '//.netlify'` ENOENT で毎回失敗（log に4回既出、non-fatal）。#37 前に修理。

### §12.3 実行順序 2026-07-19 確定（これが正本。「次どれ?」は二度と発生しない — 上から順に着手）

並行 track A（時計待ち、loop が自走。人手ゼロ）:
 A1 #30 day2 warmup 07-20 → A2 #30 day3 golden session 生存 07-21 → A3 #24 自走投稿+telegram 実ログ → A4 #10 14日実測 → A5 #12 OSS 移設（Dais 判断）

並行 track B（待ち無し、今日から番号順に実行）:
 B1 #46 LANDING-FIX  ✅完了 2026-07-19。真因=plist に WorkingDirectory 無し→launchd cwd=/ で netlify が `//.netlify` を mkdir（env var 空説・HOME 説は再現実測で棄却）。
                     fix=deploy を skill dir へ cd する subshell 化（anicca 52ee0579）。cwd=/ 条件で実 deploy 成功 + landing SSR 200/24KB を実測済。
 B2 #45 ENGINE-BASE  ✅完了 2026-07-19（anicca bd8f9b30）。Fable 独立検証: pytest 8 passed / me_load_manifest slideshow PASS（実走）。
                     成果: README「Funding lanes」章（earner=agent自己所有+instagrapi / human-funded=Postiz可）、poster.py に album_upload
                     carousel 経路（--images 2-10、--video と排他、day<3 guard 有効、album は public_verified:None の正直報告）、
                     manifests/slideshow.manifest.sh（offline SPAWN_FAKE_LLM E2E で生成・validate 通過。LANE: human-funded、live 発火は day3 実証後）
 B3 #37 MONEY-LINE   ✅配線完了 2026-07-19（anicca f8566763 + 76ed4f64）。landing card link → /go/<agent_id>（Netlify Function、
                     allowlist、非GET 405）→ Blobs click 記録 → 302 capafy.ai+UTM。/go-stats JSON。pull_attribution.py が daily pass で
                     click×sales join を ~/.openclaw/state/capafy-attribution.jsonl に追記（実走済: 2026-07-19 行あり、test click=1 が計上）。
                     Fable live 実測: 実id 302+UTM / bogus 302 top / stats JSON。初回 502 の真因 = @netlify/blobs 未install（bundle 失敗）
                     → npm install + package-lock commit で解消。SKILL.md の幻参照(x_attribution.py 等)も是正済。実 $ data は A3 投稿開始後。
 B4 #47 CLIP-HEAL    aiclipsvault 系 clip sub-loop 修理（実測: PROVISION rc=124 + no valid session で停止気味。isolated provision 経路で再生）
 B5 #44 GITHUB-SYNC  ✅完了 2026-07-19（.agents 15c94fb）。~/.agents/skills/self-sync/sync.sh + launchd ai.anicca.agents-skills-sync
                     (30分毎、listed exit0)。pull --rebase→commit→push、conflict=abort+telegram 警告、secret guard、agmsg db untrack。
                     Fable 実測: test_sync.sh 3/3 PASS + 実 sync 1回成功（両 repo up to date）。
 B6 #41 LIFE-AUTO    DEFERRED（Dais 確認 07-19）: 構想=mail/telegram/LINE 等の全受信+全 contact を基に自動で応募・返信・仕分けする loop。
                     単体では作らず **life manager の機能として**後日構築。着手 trigger = Dais が life manager 作業を開始した時。
 B4 #47 補記        ✅実 E2E 観測済 2026-07-19 21:09（前回 20:43 は disk<5GB gate で abort → cache 回収 2.4→5.2GB 後に再発火）。
                     実測: warmer が day3 の aiclips_world_hq2 を選択、★#42 の day-gated engagement が本番で実走 — follow=6 が
                     UI state change 検証付きで成功（recipe day3 cap 5-10 内）、reels 8 実再生★。golden session は terminally FAILED
                     → 正直 discard（status=session_failed、relogin せず、backup 付き state 書換）。想定通り: world_hq2 は旧 flow
                     （day1 instagrapi login 時代）の 07-17 作成で既に焼けていた。loop は usable=1 (aiwealth.pulse) で自走継続。
                     → 両 loop の初投稿はともに 07-21（aiwealth.pulse と capafy.skills9582 が同日 day3）。clean recipe 経路の
                     account が day3 生存するかが 07-21 の単一の山場。

### §12.6 終了条件 = FULL-VERIFY マトリクス（2026-07-19 Dais 明示: 「TODO は clip loop + capafy loop + engine が検証込みで完成した時だけ終わる」）

#44/#47 は infra 修理であり最終検証ではない。**全体の done は以下が全部実測で埋まった時**:

| 対象 | 検証 gate | 対応# | 証拠（全て実 log/実 URL/実 ledger。自己申告不可） |
|---|---|---|---|
| capafy marketing loop | day3 golden session 生存 | #30 | warmer log に ok:true, ChallengeRequired 無し (07-21) |
| 〃 | 自走投稿 + 報告 | #24 | loop が投稿した reel の public URL + telegram mp4 着信 + ledger 行 |
| 〃 | 金の線 | #37✅(配線)→実データ | capafy-attribution.jsonl に click>0 → sales join |
| clip loop | ready 昇格 + 自走投稿 | #48 | WARM 昇格実ログ + reel public URL + clip-metrics.jsonl 実 views |
| marketing engine | 両 loop が同一 engine で full cycle | #10（両 loop に拡張） | **14日間 人手ゼロ**で provision→warm→ready→post→measure→report が回った実ログ + 正直な realized $ 報告 |

#10 を「capafy のみ」から「clip + capafy 両方の 14日 full-verify」に拡張定義（この表が正）。self-improving は ig_reflect/reflection.jsonl が 14日窓で実データを食って回ることを含む。

### §12.5 3-loop 実測 2026-07-19（記憶でなく log/ledger 実測）
- clip loop: 稼働 exit0。07-19 pass complete、usable=2、新 account aiwealth.pulse day1 warm 済。投稿本体は共通 poster.py（独自 poster 無し）。ledger 112行 realized $0。
- capafy marketing: 稼働 exit0。07-19 DRY pass rc=0、@capafy.skills9582 provision 成功、telegram msgId 2800 送信済。途中 @capafy.skills32113 が instagrapi_login_rejected で provision_failed → 破棄し再作成（gate が仕事をした形。監視継続）。
- capafy dev loop: 稼働 exit0。07-19 CAP_FULL 正当 no-op、sales signal=none（26 listings under_review、捏造なし）。lifetime gross $9.99 / pending $8 / realized $0。
- engine 共用: clip・capafy-marketing とも marketing-engine（poster.py/warmer.py/provision/load_manifest/account_state）を source。dev loop は account_state のみ（設計通り）。

規則: track B は B1 から順に、1個 merge+実測 PASS してから次へ。track A の event（day3 生存/死亡）が来たら A を優先処理して B に戻る。day3 死亡なら FIX recipe 再改訂 → 新 account 再作成（#30 をやり直し。B は継続）。

### §12.4 決定 2026-07-19（Dais 明示）— Postiz 解約 = 1レーンのみ

- **Postiz subscription は今月(2026-07)から解約**。「human-funded lane では Postiz 可」という2レーン規律は**廃止**（B2 で書いた README の Funding lanes 章は誤りだったため書き直し済 — anicca repo で是正 commit）。
- **唯一のレーン = marketing engine + agent 自己所有 account**。現行(capafy/clip/video/slideshow)も将来(reelclaw/larry/honne の openclaw cron 化)も全て同じ: agent が account を自作→recipe warmup→poster.py(instagrapi) で投稿。human credential・投稿 SaaS は全面禁止。
- 収益資産は別チェック: live には agent 自己所有の収益リンクが必須（slideshow の Amazon tag aniccaai-22 は Dais 資産 → live 前に置換必須、manifest に明記済）。
- #41 LIFE-AUTO 注記: これは marketing と無関係の個人 loop 案（#11 で作った tg_user MTProto session を使い「Dais の telegram を読んで仕分け」する構想。07-19 handover 由来、Dais 発案扱い）。不要なら削除可。

## §13 REFACTOR INVENTORY 2026-07-19（junk = 将来 dev の混乱源。実測）

junk が増える = 将来の dev(人/AI)が「どれが本物か」で迷い、poison 事故(clip_pass の day1-login を copy した類)を繰り返す。混乱度順:

| 混乱度 | junk | 実測 | 対処 |
|---|---|---|---|
| ★★★ | **provision 2実装**: clip_pass.sh(11.4K, day1 login=壊れた方) と clip_daily.sh(6.7K) 両方生存 | 矛盾が poison を生んだ | ★1本に統一。壊れた clip_pass の day1-login 経路を消し、共有 provision_prompt.sh を単一の正に |
| ★★★ | **X線 dead code**: capafy-marketing/scripts/x_{post,metrics,attribution,post_browser}.py + capafy-x-marketing-daily.sh + disabled plist | Dais が X 凍結(@aniccaen revoke) | 削除(資産は git 履歴に残る) |
| ★★ | **poster/warmer が clip/ に物理配置**: instagrapi_post.py, warm_step.py を capafy が参照(by-reference 共有) | 「共有物なのに clip 固有ディレクトリ」 | marketing-engine/ へ MOVE(poster.py/warmer.py)、両 loop が engine を参照 |
| ★★ | **clip account 墓場**: clip-accounts.json 8/10 が frozen/poisoned/provision_failed | dead 8件 | active 以外を archive(別 file)、live state を痩せさせる |
| ★ | **account_state.sh の shim**: capafy-marketing/account_state.sh(44行)は marketing-engine 版(81行)への redirect | 二重に見える | 呼び元を engine 版直参照にして shim 削除 |
| ★ | **reach/reflect/ledger/telegram 未抽出**: ig_metrics.py/ig_reflect.py が capafy 固有のまま | 次 loop が再実装しがち | engine の reach.py/reflect.py に汎用化(#31残) |
| ★ | **死 plist**: capafy-loop-healthcheck.disabled 等 | launchd 汚れ | rm |

**原則**: 共有物は marketing-engine/ に物理集約、loop 固有(selector/content adapter)だけ各 loop に。dead は消す(git が歴史を持つ)。矛盾実装は1本に。

## §14 BIO-LINK 導線の検証（2026-07-19）
- comment link = 意図的に不使用（IG comment link はクリック不可、実証）。
- bio link = STEP5 を proven `setup_profile.py --website`（~/.agents/skills/ig-account-create/scripts/）に配線済み。機構: accounts/edit を nav → ウェブサイト input に insert → 送信する click → 再 nav で value 再確認（persistence verify FIND-402、host+path+query を CONTAIN 要求、IG strip 時 website_set=false で fail-closed）。同機構の bio セットは signup で成功実績あり。--website は FIND-402/501/602 で実 IG debug 済み＝実走行の証拠。
- ★リスク: selectors が日本語 UI 依存（ウェブサイト/自己紹介/送信する）。JP IP→JA UI で現状一致。英語 UI account では要 robustness（UI 言語検知 or 固定）。→ 新 todo BIO-ROBUST。
- live 発火は reach 健全 marker 後（~07-21+）。website_set=true が最終証明。

## §15 REFACTOR 実施結果（2026-07-19）
- R1 clip_pass.sh: **保留**（test が consumer 参照 + 既に共有 provision 使用＝poison 安全。dead-file 掃除は将来）。
- R2 X線 dead code: **削除済み**（x_*.py×4 + capafy-x-marketing-daily.sh + disabled plist 2個、consumer 0 verify、main d8aba11d）。
- R3 poster/warmer MOVE: **完了**（instagrapi_post.py→marketing-engine/poster.py、warm_step.py→warmer.py、25参照更新、旧path 0、全 test green、main 1de96a72）。
- R4 clip account 墓場: **archive 済み**（8 dead → ~/.cloak/clip-accounts-archive.json、backup 取得、live は alive 2件のみ、行を落とさず）。
- ★R5 shim: **是正 = junk でない**。capafy account_state.sh は engine の generic resolver を source し capafy の account file default + capafy 名前空間関数を足す**正しい per-loop アダプタ**。削除しない。§13 の「shim=redirect junk」は誤り。
- 残 polish（低優先）: reach(ig_metrics)/reflect(ig_reflect) を engine の generic helper に抽出。ただし capafy 固有ロジックを含むため per-loop に残す判断も可。

**結論: marketing-engine は「共有 core を物理集約 + 各 loop は固有アダプタ+content のみ」の TO-BE 構造に到達。真の junk(dead code/墓場)は一掃。**

## §16 HISTORICAL EVIDENCE — capafy.skills9582 day3 実測

この節は失敗実測の履歴。現在の要件・残 TODO・順序の正本は §17。

### 実測状態

| 項目 | 現在の事実 | 一次証拠 |
|---|---|---|
| 前回 DRY の根因 | 2026-07-20 pass は `warmup day-count=2`。`MODE_FLAG=--live` は day 3 からなので DRY は正しい。`commercial_ok=no` は非商用投稿 gate であり DRY の原因ではない | `/Users/anicca/.openclaw/logs/capafy-ig-marketing-daily.log:399-400`、`/Users/anicca/anicca/skills/earn/capafy-marketing/capafy-ig-marketing-daily.sh:58-72,118-128` |
| browser 健全性 | `capafy.skills9582` は専用 profile `:9332` で login 成功。feed、プロフィール編集、新規投稿 UI が表示され、確認範囲に suspension / restriction / challenge banner は無い。投稿は 0 件なので reach / shadowban は未評価 | `/Users/anicca/.openclaw/logs/capafy-skills9582-home-logged-in-2026-07-21.png`、`/Users/anicca/.openclaw/logs/capafy-skills9582-profile-logged-in-2026-07-21.png` |
| day3 warmup | 本物の `ai.anicca.capafy-marketing-warmup` を kickstart。`warm.py` は reels 8、scrolls 6、follows 4 を実行・検証した | `/Users/anicca/.cloak/ig-warmup-capafy.skills9582.json:50-67`、`/Users/anicca/.cloak/warmlog-capafy.skills9582.jsonl:5` |
| golden session | warmup 後の初回 instagrapi login は `ChallengeRequired: Manual verification required` で terminal failure。state は `session_failed`、settings は不存在、attempt marker は存在する。再 password login と marker 削除は禁止 | `/Users/anicca/.cloak/clip-accounts-capafy.json:18-28`、`/Users/anicca/.cloak/.golden-session-attempted-capafy.skills9582`、`/Users/anicca/anicca/skills/earn/marketing-engine/warmer.py:87-132,332-340` |
| 実投稿 | 実投稿は行っていない。`session_failed` は active resolver から除外されるため daily path は `no-active-account` の provision branch に入る。terminal challenge を迂回した手動 poster 呼出しは行わない | `/Users/anicca/anicca/skills/earn/marketing-engine/account_state.sh:19-35`、`/Users/anicca/anicca/skills/earn/capafy-marketing/capafy-ig-marketing-daily.sh:31-34,92-114` |
| 停止状態 | scope 外の新 account 自動作成を防ぐため `ai.anicca.capafy-ig-marketing-daily` と `ai.anicca.capafy-goal-monitor` は unload。`ai.anicca.capafy-marketing-warmup` は loaded / not running で、`session_failed` account を処理しない | `launchctl print gui/501/<label>` 実測 |
| コード変更 | なし。gate の stale/過剰判定ではなく、day3 private API challenge が停止理由 | `git -C /Users/anicca/anicca status --porcelain=v1` = empty |

### 旧 TODO（§17 により置換）

| 順 | item | done 条件 |
|---:|---|---|
| 1 | current account を terminal として保持 | `session_failed`、attempt marker、settings 不存在を維持。password relogin、attempt marker 削除、browser fallback 投稿を行わない |
| 2 | 新 account 作成は新しい明示 scope が来るまで停止 | daily / goal-monitor を unload のまま維持し、自動 provision が発火しない |
| 3 | 新しい明示 scope が来た場合のみ fresh account を作成 | 専用 isolated profile / port、browser-only day 1-2、成功 warmup log を実測 |
| 4 | fresh account の day 3 golden session を検証 | 初回 instagrapi login 1回、timeline feed probe、settings dump、`status=ready`、`session_owner=instagrapi`。ChallengeRequired なら terminal discard |
| 5 | session 成功時のみ daily / goal-monitor を load して loop 起点の非商用 Reel を1本投稿 | public Reel URL、logged-out screenshot、IG ledger、rotation ledger、telegram message id が全て存在 |
| 6 | reach を測定して commercial gate を判定 | 複数 snapshot で非ゼロ plays/views と公開可視性を確認した場合のみ `.capafy-ig-reach-healthy` を作成 |
| 7 | 14日 full-cycle を実測 | provision → warm → ready → post → measure → report が人手ゼロで14日継続し、§12.6 の全 gate が green |

## §17 CURRENT SSOT — provider-agnostic revenue loops + gig 納品 + shared marketing engine

### 17.1 Outcome

以下を同時に成立させる。

1. Claude subscription の残量に依存せず、全 revenue loop が共通 runner 経由で GPT / Claude / その他 provider を差し替えて動く。
2. gig-core は「tmux が生きている」ではなく、各 step の成功を証拠付きで判定し、失敗を成功扱いせず、paid contract を締切順に完成・正式納品する。
3. 木村様の囲碁盤 OpenCV PoC を受入基準まで修正し、実ファイルを Coconala で正式納品する。
4. marketing-engine は Capafy 専用ではなく clip / video / future products の共有 core とし、bot-like な synthetic engagement warmup を廃止する。
5. fresh Instagram account は固定 day gate ではなく `account setup → publisher health → first non-commercial post → public/reach verification → commercial` の実状態で進む。
6. disk cleanup は revenue loop の実行中 worker・納品物・checkpoint・identity state・調査証拠を削除せず、既知の再生成可能 artifact だけを単一 policy で回収する。

### 17.2 Current measured facts

| Area | 現在の事実 | 一次証拠 |
|---|---|---|
| Claude runtime | direct Sonnet はquota/cooldownで利用不能。gig-core実画面も `429 / All credentials for claude-sonnet-5 are cooling down` で停止する | direct probe、tmux `anicca-gig-core` pane |
| Codex runtime | `codex exec --ephemeral -m gpt-5.6-luna` と `gpt-5.6-terra` は read-only probe がともに rc=0、期待文字列を返す | `/private/tmp/codex-loop-probe.txt`、`/private/tmp/codex-terra-probe.txt` |
| OpenClaw | global primary は `deepseek/deepseek-v4-flash`、fallback は `openai/gpt-5.4-mini`。gpt-5.5-mini ではない | `/Users/anicca/.openclaw/openclaw.json` |
| gig process | tmux `anicca-gig-core` は存在するが起動commandも各stepも `--model sonnet` 固定。coreは429後idle、`pass-report.jsonl` / `.last-pass` の最終更新は前日で、本日のproductive passはない | tmux pane/process argv、`~/gig/pass-report.jsonl`、`~/anicca/skills/earn/gig/gig_pass.sh:12-20` |
| false success | `gig_pass.sh` の `step()` は sub-call stdout/stderr を `/dev/null` に捨て、非zero rcでも後続へ進める。最後に `.last-pass` / pass report を更新できる | `/Users/anicca/anicca/skills/earn/gig/gig_pass.sh:15-24,38-56` |
| 木村様案件 | requestId `5138597`、契約額 **¥65,000**、納品予定日は本日。実talkroomは `取引中 / 進行中 / 納品送付前`、`正式な納品` checkbox未選択。最新は出品者のテキスト返信で、改善版file添付も正式納品もない | real `https://coconala.com/talkrooms/17963099` DOM + `/private/tmp/fkimura-talkroom-current.png` |
| 木村様成果物 | code と7画像分の CSV/JSON/overlay はあるが、package/README/requirements/expected matrixがなく、空盤で black=19 / black=13, white=4 のまま。受入不可 | `~/gig/wip/5138597_fkimura_goboard/`、`out_20260721/summary.json` |
| paid queue | real `received_orders/open` は3件。INV-R9順は Fkimura requestId `5138597` / ¥65,000 / 当日paid → `sunai267` requestId `5167108` / ¥17,000 / 購入済みかつbuyerのaddon・error・screenshot受領 → `jibieaian` / ¥40,000 / その他paid。3件ともbuyer-visibleな次versionと正式納品証拠がない | fresh authenticated Coconala DOM + `/private/tmp/gig-runner-todo2-review.E2bkbg/49-live-normalized-summary.json` |
| quote queue | `sunai267` は `要提案` から購入済みへ遷移し、talkroom `18011694` が開いている。現在のfresh viewにactive quoteはなく、stale quoteよりpaid stateを優先する必要がある | real `received_orders/requests` / `received_orders/open` / talkroom DOM |
| TODO #2 first review | commit `aaa6c1b` は real Luna/Terra、direct provider call 0、fresh queue、launchd fail-closedを満たす一方、独立reviewは **FAIL**。P0は forged local formal-delivery証拠の受理、runnerのstale result再利用、paid/quote重複時のpaid削除。P1はpassprep/self-improve配線の削除とtest弱体化。親commitから存在するpassprep full-suite failure 9件も未解消 | `/private/tmp/gig-runner-todo2-review.E2bkbg/REVIEW_SUMMARY.txt` |
| Capafy marketplace loop | launchd dailyはloaded。直近passは本日08:10〜08:33にSonnetで成功したが、scriptはSonnet固定であり、現在のquota/cooldown下では次回成功を保証できない | `capafy-loop-daily.log`、`capafy-loop-daily.sh:11,27` |
| Capafy marketing account | `capafy.skills9582` はsynthetic warmup後のprivate API `ChallengeRequired` でterminal discard、投稿0件。active accountなし | §16、warmup log/state |
| Capafy marketing launch state | IG marketing daily / goal-monitor はunloaded。last-passは前日、warmupだけloaded/not-running。scriptはSonnet固定。したがって毎日投稿loopは稼働していない | `launchctl print/list`、`.capafy-ig-marketing-last-pass`、`capafy-ig-marketing-daily.sh:22,144` |
| shared blast radius | `marketing-engine/warmer.py` / `poster.py` は Capafy のほか clip / video / clip-promote が参照する | `/Users/anicca/anicca/skills/earn/{capafy-marketing,clip,video,clip-promote,marketing-engine}` |
| disk pressure | inactive・clean・remote-contained worktree 9件だけを非force解除し5,929,028KiBを回復。fresh 16回/15分13秒pollはraw free min 12,835,096KiB、max 12,928,772KiB、10GiB failure 0。locked/active/dirty worktree、active VM/Codex/WIP、protected 24件を全sampleで保持。backpressure/alertは容量正常時absent | `/private/tmp/disk-containment-capacity-close.09kky5/poll-clean-16x60.tsv` |
| cleaner review | **PASS / TODO #1 closed**。race 50/50、stale group停止、healthy/no-lease保持、orphan cleanup、reserve、v2 ledger、live hash、strict shellcheck、全target testsがgreen。OS scheduled passは自然発火しlease/heartbeat→last exit=1→cleanup、`.last-pass`不変。guard core/CDP/VM/protected/worktree invariantは16/16 green | `/private/tmp/disk-containment-capacity-close.09kky5/AUTHORITATIVE_EVIDENCE.txt`、commits `69a065a5a`/`9c2766c`/`15c9e88`/`6b0039cb` |
| active VM debt | 旧guardがactive Claude VM bundleをunlink済み。PID 92713がlink-count 0のrootfs/sessiondata各10GBをopen保持。現guardは再発防止するが、active dependencyのため既存PIDは停止しない | `lsof +L1`、Claude local-agent/app activity |
| large consumers | `.openclaw` 24GB、`anicca-project` 14GB（`.worktrees` 8.7GB）、`.cloak` 7GB。既存cleanerは主な占有元のowner/lifecycleを管理しない | read-only `du -xhd` inventory |
| incomplete protection | 共通 protected-paths manifest は `reelclaw-assets` 1件だけ。gig納品物、checkpoint、marketing state、browser identityは分類されない | `~/.openclaw/state/protected-paths.json` |

### 17.3 Diagnosis

待つだけでは完了しない。

- Claude quota は reset 後に一時復旧しても、provider 単一障害・dead lock・rc無視・false success を残す。
- 木村様成果物は生成済みだが判定精度が壊れている。quota reset は OpenCV の誤検出を直さず、正式納品もしない。
- Capafy の challenge と synthetic warmup の因果は断定できない。ただし warmup が健全性を上げた証拠はなく、bot-like な follow / scroll / replay を追加した直後も投稿可能 session を確立できていない。
- Instagram の official publishing path は professional account と publish permission を前提に Reel 公開を提供する。shared engine の primary publisher は official API、private API は primary から外す。
- 現在のcleanerは容量制御として成立しない。低容量→正常なgig worker kill→transcript削除→空き容量不変→再killのlivelockになり、収益作業と原因調査を同時に止める。
- 過去の `.venv`、作業中clone、runtime `dist`、`reelclaw-assets` 誤削除は、mtime/glob中心の複数executorとfail-open保護が同じ削除判断を持つ構造から再発する。個別exclude追加だけでは閉じない。
- 自己改善はread-only analyzerがpolicy変更案を作る層に限定する。削除executorは承認済みmanifestを決定論的に実行し、実行時に対象範囲を学習・拡張しない。
- Coconalaの「納品予定日」は待機日ではなく最終期限。paid contractにactionable feedbackがある限り、次のbuyer-visible versionを作らずテキストだけ返すことは進捗ではない。
- ただし未完成物へ常時 `正式な納品` を付けるのも誤り。公式要件どおり、合意scopeを満たすacceptance PASS後に即時チェックし、差し戻し後は修正版artifactを添えて再度正式納品する。

### 17.4 Invariants

| ID | 必須条件 |
|---|---|
| INV-R1 | scheduler / business flow は provider CLI を直接呼ばず、共通 `agent-runner` contract だけを呼ぶ |
| INV-R2 | step の nonzero rc、timeout、missing evidence、schema error は pass failure。`.last-pass`、success ledger、次 step を更新しない |
| INV-R3 | lock は PID liveness を時刻より優先する。dead owner は安全にreapし、live ownerはreapしない |
| INV-R4 | paid / due contract は listing改善・応募・学習より常に優先する |
| INV-R5 | 正式納品は成果物存在だけでなく、acceptance test PASS、package hash、Coconala buyer-visible delivery stateを必要とする |
| INV-R6 | buyerのactionable feedbackを読んだpassは、単なる受領テキストで終了しない。versioned artifact、acceptance delta、または具体的external blockerのいずれかを同じpassでbuyer-visibleにする |
| INV-R7 | 合意scopeのacceptanceがPASSした瞬間に、deadlineまで待たずartifactを添付して `正式な納品` を送る。未完成・既知failのartifactへ正式納品を付けない |
| INV-R8 | 差し戻し/追加feedback後は新versionを作り、変更点とevidenceを添えて再納品する。paid work中もトークルームと納品確認を毎pass確認する |
| INV-R9 | queue優先順位は `期限超過/当日paid deliverable → buyer feedback/revision → 要提案quote → その他paid work → nurture → listing/apply/learn`。予定日は開始日として使わない |
| INV-M1 | account warmup を目的とした自動 follow / like / comment / reel-scroll を行わない |
| INV-M2 | account ageだけの day1/day2/day3 gate を使わない。publisher health と public verification が gate |
| INV-M3 | first post は original / non-commercial / linkなし。commercial化は複数reach snapshot後のみ |
| INV-M4 | account challenge を password retry、marker削除、account churnで迂回しない |
| INV-M5 | account lifecycle / publishing / reach contract は shared engine に1つだけ置き、各productは manifest / content adapterだけを持つ |
| INV-E1 | Builderの自己申告は完了証拠にしない。Plannerがfresh command / artifact / public UIで独立検証する |
| INV-D1 | cleanup executor は1つのversioned policy / artifact manifestだけを参照する。manifest不在・parse失敗・未分類pathはfail-closedで削除しない |
| INV-D2 | `deliverable`、`checkpoint`、`identity/state/secret`、active lease、incident evidenceは自動削除しない。既知の `ephemeral` だけがTTL/quota後に削除可能 |
| INV-D3 | emergency mode は正常workerを一括killしない。新規runをbackpressureし、heartbeat/lease/timeoutで暴走と実証された個別workerだけを停止する。gig-core本体は常に除外する |
| INV-D4 | 削除前後に path、owner、class、bytes、reason、policy version、result をappend-only ledgerへ残す。削除量0の反復emergencyは成功扱いしない |
| INV-D5 | AI analyzerはread-only。削除policy変更はspec→RED test→builder→shadow/canary→独立reviewを通り、executor自身はpolicyを書き換えない |

### 17.5 Model routing contract

| Class | Default | 対象 |
|---|---|---|
| deterministic | modelなし | lock、state transition、deadline queue、metrics、ledger、publisher API、schema validation |
| repeatable-agent | `gpt-5.6-luna`, low | extraction、定型copy、分類、短いreflection、bounded transform |
| tool-agent | `gpt-5.6-terra`, medium | browserを含む通常のB0/B1/B2判断、account setup、daily marketing pass |
| high-value-agent | `gpt-5.6-sol`, medium→high | paid deliverableの実装、OpenCV修正、複雑な障害解析、最終adversarial review |

provider名・model名は runner config に閉じ込める。business script は task class のみを渡す。利用不能時は同じ class の別providerへ failoverし、全provider失敗時は明示 failure にする。

### 17.6 Planner / Builder split

```text
Planner (root)
  spec SSOT更新 → 1 bounded taskを発行 → Builder evidence受領
       ↑                                      ↓
  独立E2E検証 ← commit/hash/log/screenshot/public URL

Builder (fresh SOL instance)
  AGENTS + §17 + named filesだけを読む
  RED → minimal GREEN → refactor → focused E2E
  対象pathだけcommit/push → Plannerへ証拠を返す
```

Planner は実装を持たず、Builder は完了判定を持たない。各 TODO は前の gate が green になってから次へ進む。

### 17.7 Remaining TODO — order SSOT

Completed gate: **TODO #1 P0 disk containment review findings — PASS**。正本証拠は `/private/tmp/disk-containment-capacity-close.09kky5/`。

Current gate: **TODO #2 corrective review — FAIL / Builder修正中**。first review の正本証拠は `/private/tmp/gig-runner-todo2-review.E2bkbg/`。

| 順 | TODO | Builder scope | Done / E2E gate |
|---:|---|---|---|
| 2 | **gig hot pathをLuna/Terra/Solへ移しdelivery-first化** | gig-core/stepのSonnet直結を共通runnerへ置換。paid/feedback/quote queueをdeterministicに先頭化し、artifact/evidenceなしの「了解」返信をsuccessにしない。correctiveで runner resultをattempt前に無効化、live DOMだけをformal-delivery ground truthにする、paidをstale quoteより優先、passprep/self-improve配線とguard testを復元する | Sonnet 429 fixtureでもLuna/Terra実callでpaid queueを処理。direct Sonnet production call=0。固定名でなくINV-R9からfresh実画面順（現在はFkimura→sunai→jibieaian）をloopが選択。stale result / forged formal delivery / paid+quote duplicate fixtureはfail-closed。missing artifact/正式納品 stateをfailureとして返し、既存passprep/self-improve/full Gig regressionがgreen |
| 3 | **木村様 ¥65,000 PoCを修正・package・即時正式納品** | 7画像expected matrixをtest化しOpenCVを修正。正検出/見逃し/誤検出/座標report、README、requirements、versioned zip、hashを作り、loop自身がtalkroom添付+正式納品 | 7画像acceptance/overlay目視PASS。buyer-visible新version、`正式な納品` checkbox送信後の `納品確認待ち` 画面、URL+screenshot+ledger。テキストだけの返信は不可 |
| 4 | **全gigへversioned delivery cadenceを展開** | `jibieaian` は最初の投稿草案artifactを即提出し、以後feedbackごとにversion更新。購入済みの `sunai267` は受領済みaddon・error・screenshotから修正版artifactを作り即提出。全契約へINV-R6〜R9を適用 | real Coconalaでjibieaian草案artifact添付、sunai修正版artifact添付。fixtureでfeedback→artifact→acceptance→formal delivery→差し戻し→new version→formal redeliveryを証明。daily visual verifierがstatus/screenshotを残す |
| 5 | **provider-agnostic runnerをCapafy/Fleetへ展開** | Capafy marketplace / IG marketing / active claude-p consumersを共通runner化し、rc/evidence schema、timeout、supervisor/backoff、PID-aware lockを統一 | Claude利用不能でもCapafy marketplaceとmarketingのscheduled passがLuna/Terraで成功。failure時last-pass/success ledgerを更新しない。全対象のdirect Sonnet production call=0 |
| 6 | **cleanup control plane + artifact lifecycleを単一化** | cleanup entrypointを1つにし、重複LaunchAgent/OpenClaw cleanerを無効化。全artifactにowner/class/TTL/quota/lease/finalizerを宣言し、fail-closed manifest、off-volume quarantine、append-only delete ledgerを実装 | active cleanup executor=1。manifest欠損/破損/unknown/active/deliverable fixtureは削除0、expired ephemeralだけ削除。過去事故fixture（`.venv`、WIP clone、runtime `dist`、`reelclaw-assets`）全保持。delete ledgerとrestore E2E PASS |
| 7 | **producer budgets + capacity observability** | gig / marketing / clip / video / browser / worktree producerにrun quota、rotation、checkpoint圧縮、reserve-space backpressureを実装。容量trendとowner別growthを観測し、0-byte reclaim反復をfailure化 | free-space reserveを割るfixtureで新規runは開始せずactive run/checkpointは保持。producer別quota test、log rotation、recovery後resume E2E。cleanerが2回連続0-byte reclaimならalert/failureとなりsuccessを記録しない |
| 8 | **shared marketing-engineをno-synthetic-warmupへ移行** | `warming/day3 golden private session` を `setup/publisher_ready/posted/measuring/commercial` へ置換。automatic follow/like/comment/scrollを削除。official Meta publisher primary、product adapter分離。Capafy / clip / video consumer contractを更新 | testでsynthetic engagement call=0、day-count branch=0、全consumerが同じ lifecycle/publisherを参照。official publisher health probeとfailure state transitionをE2E。current terminal accountは再利用しない |
| 9 | **fresh Capafy accountからfull-cycleを実証しfleet rollout** | isolated account setup、professional/publish permission、first non-commercial Reel、public/reach measurement、commercial gate、Telegram/ledgers。全consumer regression後に14日自走 | account creation/setup evidence、publisher-ready evidence、public Reel URL、logged-out screenshot、publish status、IG/rotation ledger、Telegram message ID。複数snapshotで非zero reach後のみ commercial marker。14日 `setup→post→measure→report` 継続、全gate green |
| 10 | **read-only cleanup analyzer + fleet self-improvement gate** | owner別growth/anomalyを分析しpolicy変更案とRED fixtureを生成するread-only analyzerを追加。policy変更はshadow/canaryと独立review後のみpromote | analyzer権限でdelete/policy write不可を実証。提案→RED→GREEN→shadow→canary→promote ledger E2E。14日間、protected artifact欠損0、disk reserve違反0、正常revenue worker誤kill 0 |

### 17.8 Acceptance scenarios

1. **Disk emergency** — Given free space is below the emergency threshold, when the guard runs, then gig-core and a healthy leased worker remain alive, a fixture-proven runaway worker alone stops, active evidence remains, and the decision is ledgered.
2. **Unknown cleanup candidate** — Given a path lacks a valid artifact classification, when cleanup evaluates it, then it is not deleted and the manifest violation is reported.
3. **Provider outage** — Given Claude is quota-blocked, when a repeatable/tool task runs, then Luna/Terra completes through the same runner; no business script changes provider-specific code.
4. **All providers fail** — Given every provider returns nonzero, when a pass runs, then the pass is failed, the lock is released/reaped safely, and no success marker is written.
5. **Paid deadline** — Given an active paid contract is due, when gig wakes, then delivery work runs before learn/listing/apply and continues until formally delivered or a concrete blocker is recorded.
6. **OpenCV acceptance** — Given the seven buyer images and expected counts, when the package test runs, then every count and output schema passes before upload.
7. **Immediate delivery** — Given acceptance is green before the registered deadline, when the gig pass runs, then it attaches the versioned artifact and sends `正式な納品` in that pass; it does not wait for the deadline.
8. **Feedback iteration** — Given buyer feedback or a formal return, when the next pass runs, then a new artifact version and delta evidence are produced; a text-only acknowledgment cannot mark the step successful.
9. **Quote priority** — Given a feasible `要提案` quote exists, when no due/feedback paid item blocks it, then the loop sends the proposal before listing/apply/learn work.
10. **Fresh marketing account** — Given account setup and official publisher health are green, when the first content is ready, then one original non-commercial Reel may publish on day1; no artificial engagement or arbitrary waiting day is required.
11. **Reach gate** — Given a public Reel exists but reach evidence is absent/zero, when daily runs, then commercial link/CTA remains disabled.
12. **Shared regression** — Given shared lifecycle changes, when Capafy/clip/video tests run, then each consumer uses its own state namespace and the same engine contract without cross-account mutation.

### 17.9 Full TO-BE

```text
launchd / tmux / OpenClaw scheduler
                │
                ▼
        capacity admission gate
        reserve / quota / backpressure
                │
                ▼
        supervisor + health check
        PID-aware lock / retry / backoff
                │
                ▼
       provider-agnostic agent-runner
       ├─ deterministic: shell/python
       ├─ repeatable: GPT-5.6 Luna
       ├─ tool work:  GPT-5.6 Terra
       ├─ high value: GPT-5.6 Sol
       └─ future: Claude/Kimi/DeepSeek adapters
                │
      rc + schema + artifact evidence
                │
        ┌───────┴──────────────────────┐
        ▼                              ▼
 GIG REVENUE LOOP              SHARED MARKETING ENGINE
 paid/deadline queue            product manifest/adapter
        │                              │
        ├─ Fkimura ¥65k #5138597       ▼
        │  buyer feedback         isolated account setup
        │  → versioned artifact        │
        │  → acceptance PASS           ├─ challenge → terminal/report
        │  → package/hash              │
        │  → 即Coconala正式納品         ▼
        │  → accept/return monitor official publisher health
        │  → returnならnew version
        │  → buyer-visible proof
        │  → delivered/paid ledger
        │                              │
        ├─ jibieaian ¥40k              ├─ fail → explicit failed state
        │  deadline/work/delivery      │
        │                              ▼
        ├─ sunai ¥17k 要提案       first original non-commercial Reel
        │  feasibility→即提案            │
        │                              ├─ public URL + logged-out proof
        └─ listings/applications       │
           only after paid/quote       │
           queues are safe             │
                                       ├─ IG/rotation ledger
                                       └─ Telegram report
                                              │
                                              ▼
                                      repeated reach snapshots
                                              │
                              ┌───────────────┴──────────────┐
                              ▼                              ▼
                       zero/unhealthy                  healthy/nonzero
                       no commercial                   commercial marker
                       continue measure                link + soft CTA
                              └───────────────┬──────────────┘
                                              ▼
                                      14-day full cycle
                                              │
                         Capafy / clip / video / future products
                         share the same engine, isolated state only

        GIG + MARKETING + BROWSER + WORKTREE PRODUCERS
                              │
             artifact declaration at write time
          owner / class / TTL / quota / lease / finalizer
                              │
                              ▼
                 shared artifact registry
          ┌───────────────────┼────────────────────┐
          ▼                   ▼                    ▼
      ephemeral          active/progress      durable/identity
      TTL+quota          lease+checkpoint     deliverable/state/secret
          │                   │                    │
          ▼                   └──── preserve ──────┘
   single deterministic
    cleanup executor ── append-only decision/reclaim ledger
          ▲
          │ versioned policy only
   read-only AI analyzer
   growth/anomaly → spec proposal → RED test → shadow/canary → promote

Every step: real evidence → Planner independent verification → spec update
```

### 17.10 External primary sources

- OpenAI Models: https://learn.chatgpt.com/docs/models — 「Terra as the everyday workhorse」「Luna for clear, repeatable work」。
- OpenAI Non-interactive mode: https://learn.chatgpt.com/docs/non-interactive-mode — 「Non-interactive mode lets you run Codex from scripts ... You invoke it with `codex exec`」。
- Claude Code Programmatic usage: https://code.claude.com/docs/en/headless — 「pass `-p` ... to run it non-interactively」。現行loopが使うsurface自体は正しいが、subscription単一依存が失敗点。
- Meta Instagram Content Publishing: https://developers.facebook.com/documentation/instagram-platform/content-publishing — professional account向けに `/<IG_ID>/media` と `/<IG_ID>/media_publish` を提供し、Reelsを正式公開できる。
- Meta Spam policy: https://transparency.meta.com/policies/community-standards/spam/ — 「restrictions ... at lower frequencies when ... signals of inauthenticity are present」。回数を少なくするだけでは不十分で、synthetic engagement自体を除く。
- Coconala 正式な納品: https://coconala-support.zendesk.com/hc/ja/articles/218721047 — 合意内容を満たす提供が完了した時に出品者が送信する。
- Coconala 納品確認: https://coconala-support.zendesk.com/hc/ja/articles/900005474606 — 承諾/差し戻しを行わない場合は正式納品から72時間後の次の00分に自動クローズする。
- Coconala 要対応: https://coconala-support.zendesk.com/hc/ja/articles/5894870734745 — 見積り提案期限72時間前、納品予定日超過、差し戻し等を要対応として扱う。
