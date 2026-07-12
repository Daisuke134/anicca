# 🎯 LOOP SSOT — これ1つ見れば全部わかる（profitable-claude loop 修理の唯一の正本）

**scattered 防止**: loop 修理の設計・実態・全 task list はこのファイルだけ。他ファイルはここを指すだけ（詳細のみ持つ）。更新は必ずここ。

## 0. 用語（loop の走り方＝3層）
```
① launchd 目覚まし（機械上 ~/Library/LaunchAgents、一意 Label 必須。同名は片方しか起動しない=衝突）
② repo 内のレシピ（script）← どの repo にあるか = 「そのループがどこで動くか」
③ tmux の headless claude（実際に働く）
```

## 1. 2 repo の役割（違い）
| repo | 目的 | 稼ぎ先 | 誰が直す |
|---|---|---|---|
| **profitable-claude** | 人間(Dais)のために稼ぐ | 銀行/Stripe(fiat) | 私(claude-p) |
| **anicca** | agent 自身のために稼ぐ | 自分の wallet(crypto) | 別 CC |

## 2. profitable-claude の loop（TO-BE = 8個、重複なし）
```
1 gig        Coconala 出品/提案/見積/返信 → 銀行
2 capafy     skill 販売 → 銀行
3 article    Zenn 有料記事 → 銀行
4 life-manager 予定/連絡/intake → subscription MRR
5 affiliate  紹介投稿 → 紹介料
6 bounty     懸賞提出 → 賞金
7 connector  イベント/人脈 登録 → gcal+Telegram（人脈資産）
8 explorer   機会探索 → 上記へ供給
```
anicca 側(別 CC): founder / Franklin / pm / sol / clip / video / reddit / self-improve（crypto/SNS）。**verifier のみ共有**。

## 2b. 全 loop 定義表（実測・repo・何をする・問題・2026-07-11）
我々=MONITOR（自分でやらない。loopにやらせ browserで実際にやったか見て、足りなければ harness+prompt+credential を直す。最終的に self-heal が自動化）。
### PC(profitable-claude)=あなたの銀行
| loop | 何をする | 問題 |
|---|---|---|
| connector | イベント登録→gcal+人脈 | ★2026-07-12 main-session が自分の手で fix中★: 真因=(1)first-pass 2h+ハング(pass未完で1日の窓浪費)(2)self-heal未発火(3)1候補/passで11 gap埋まらず。fake eventは無し(7/11の2件は実登録・DaisNar参加者リスト確認)。fix A=STEP1を全open horizon日loop / fix B=ハング120分検知+self-heal発火(was 26h放置)。修正版で core再走中→応募をlogged-out firecrawlで検証予定。RCA正本=docs/loop-engineering/27-connector-rca-and-fix.md |
| affiliate | 紹介投稿→紹介料 | reCAPTCHAで06-30からlogout・投稿0。★2026-07-12 実測: @aishigoto.labo2 の warmup day1 が実行済み（`~/.cloak/ig-warmup-aishigoto.labo2.json` day1 reels6/scrolls5 + screenshot 14:14 JST）**だが起動元スケジューラが launchd にも openclaw cron(jobs.json) にも存在しない**=真因①の再演リスク（明日走る保証なし）。最初の一手=gateway live store を cron CLI で照会→launchd 日次 warmup ジョブ化★ |
| bounty | 懸賞提出→賞金 | idle・survivor0 |
| explorer | 機会探索→他loopへ供給 | proposal走るが収益化0 |
| life-manager(core) | 予定/連絡/intake→MRR | ★2026-07-12 anicca版(loop)退役済=単一起動★・空稼働・MRR0（次は#8で稼働） |
### anicca=crypto/SNS(別CC)+一部bank混線
| loop | 何をする | 問題 |
|---|---|---|
| gig | Coconala出品/提案/返信/納品→銀行 | 24日本体復元済。提案(teian)・出品(shuppin)・納品が足りない ←今 |
| capafy | skill販売→銀行 | 審査中status=1・public未掲載・"PUBLISHED"嘘(accountはログイン済) |
| ~~life-manager(loop)~~ | ~~(PC版と重複)~~ | ✅退役完了(2026-07-12): launchd `life-manager-loop-healthcheck` を bootout+disable+plist→.disabled、tmux worker(loop+selffix)kill、worker process 消滅=2x課金停止実証。復活escalation無し(LMHB=report専用)。PC core は生存継続 |
| clip | IG動画→crypto視聴報酬 | ★2026-07-12 実測更新: blur は解決済み（〜07-10 は 202x360/~200kbps を投稿していた→verify_clip.sh に 1080x1920+2.5Mbps ゲート追加、07-11 に burn_captions.py を純ABR 4Mbps 化 pass19 で実測 3.7-3.9Mbps）。**現在の主障害は投稿停止**: 07-11 17:00 以降投稿0件（IG共有確認ステップで全試行ハング or 202後に消滅、`~/.cloak/clip-accounts.json` の2アカウント両方 status=investigating で run.sh が選択不能）。最終実投稿=instagram.com/aiclipsvault/reel/DanlbElPLGr/。Telegram送信実装ゼロ（mail経路のみ=Daisに未達）。browser=専用port 9223/9224 で:9222とは分離設計。収益¥0（clip-promote の回収も未検証） |
| clip-promote | 拡散→crypto | 選択だけsuccess・$0 |
| video | 動画→crypto | grid空・blur |
| reddit | 投稿→crypto | account BAN |
| founder/Franklin/pm/sol | trade→crypto | 別CC担当。★2026-07-12 18:15 JST: `ai.anicca.pm-earner`(10分毎launchd) は TASKLIST #3 で2度「停止済み」と虚偽記録されたまま実稼働していた→本日 bootout+plist を .disabled-2026-07-12 化、`launchctl list | grep -c pm-earner`→0 を実測。残る発注系統= pm-deterministic(30分毎)+agent-economy-loop menu のみ★ |

## 2c. 8 loop 生死+実出力 実測（2026-07-12 08:xx JST、tmux has-session + launchctl list + evidence の有無で判定。「プロセスが生きている」≠「毎日実出力している証拠がある」を明確に分離）
| # | loop | プロセス生存 | launchd登録 | 毎日の実出力を証拠で確認済みか |
|---|---|---|---|---|
| 1 | gig | tmux ALIVE | healthcheck+daily-report+auditor+proactive 4本 | **YES**（SSOT L1済み、強evidence） |
| 2 | capafy | launchd直起動(tmux常駐なし) | `capafy-loop-daily`1本のみ(毎日08:10) | **YES**（08:10:05に人手ゼロで自動発火を実証、そのパスで孤児DRAFTを審査提出まで完遂→私がAPI照合 status=1/skills=1/keys=1） |
| 3 | article | プロセス無し | 無し | NO（未マージ・未live、着手すらしていない） |
| 4 | life-manager | launchd直起動(tmux常駐なし) | `life-manager-daily`1本のみ(毎日10:15) | **YES**（修理後のパスが自力で新規IG投稿 https://www.instagram.com/p/DarB2Qikt3d/ を産み、私が実ブラウザで確認。Redditはkarma=1を実測しBP通り宣伝せずkarma育成） |
| 5 | affiliate | tmux ALIVE | healthcheck+proactive（★warmup 本体のスケジューラ未特定★） | NO（@aishigoto.labo 恒久ロック。@aishigoto.labo2 warmup day1 は 2026-07-12 に実行済み=state json+screenshot 実在、だが起動元不明で日次継続の保証なし） |
| 6 | bounty | tmux ALIVE | healthcheck+proactive | 未調査（今回のセッションでまだ見ていない） |
| 7 | connector | プロセス無し(設計上、launchd直起動) | fill-gaps(実行中PID確認)+daily-report | **YES**（SSOT #5済み、強evidence） |
| 8 | explorer | tmux ALIVE | healthcheckのみ | 未調査（今回のセッションでまだ見ていない） |

## 2d. 共通修理マトリクス（2026-07-12 18:30 JST、3体のSonnet調査agent実測に基づく）
| loop | ①launchd直起動 | ②timeout削除 | ③Telegram実配信 | ④browser排他 | 実証拠URLをledgerに記録 |
|---|---|---|---|---|---|
| gig | ✅ | ✅相当 | ✅(msgId 1938) | ✅ cdp_lock.sh(:9222 mkdir排他) | ✅(応募9件 実UI確認) |
| capafy | ✅(08:10) | ✅ | ✅(msgId 1973) | ✅ mkdir排他 | ✅(API status=1照合) |
| article | ✅(06:00) | ✅(BG_WAIT_CEILING=0) | ✅(msgId 1990/1991) | — | ✅(draft 404確認) |
| life-manager | ✅(10:15) | ✅ | ✅(07-12 09:54 commit ac104a3 で修理、msgId 1976。それ以前はPushNotification=未達) | ❌ LLM目視判断のみ(:9222共有、mkdirロック無し) | ✅(IG実URL+logged-out検証。ただし動画でなくPillow静止画カード、IG=借り物@anicca.affirms2、Reddit=@anicca_sao shadowban確定・appeal提出済) |
| connector | ✅(07:50/09:10) | ✅相当(120分ハング検知) | ✅(msgId 1941-1943) | — | ✅(gcal readback+実会場) |
| **affiliate** | ❌(warmupの起動元不明) | ❌未確認 | ❌ | ❌未確認 | ❌(warmup day1のstate/screenshotのみ) |
| **bounty** | ❌ | ❌未確認 | ❌ | 要判定 | ❌(未調査) |
| **explorer** | ❌(healthcheckのみ) | ❌未確認 | ❌ | 要判定 | ❌(proposal走るが収益導線0) |
| (参考)clip=anicca別CC | ✅(producer+proactive) | — | ❌実装ゼロ(mail経路のみ) | ✅ 専用port 9223/9224 | ⚠️ledgerに実URL有るが07-11 17:00以降投稿0(IG共有確認ハング) |

life-manager 追加の既知ギャップ(2026-07-12 解剖): (1)動画未生成=MoneyPrinterTurbo未インストールで毎回Pillow静止画カードにフォールバック (2)専用IG/Redditアカウント不在(借り物運用) (3)同日重複ガードがLLM判断のみ (4)別系統 `~/.openclaw/skills/life-manager-video/post-daily.sh`(実音声→リール動画→Postiz→TikTok @anicca.comedy、07-12 00:31 実投稿記録)が**どのcron/launchdからも呼ばれておらず実行主体不明**=幽霊稼働。

結論(2026-07-12 更新): 「毎日の実出力を証拠で確認済み」= **4つ(gig, connector, capafy, life-manager)**。articleは存在しない(未着手)。affiliate/bounty/explorerは未調査。★共通の真因(4loopで同一)★: (1)「毎日9時に起きます」等の**自己申告CronCreateは実体として保存されず**、1回動いて以降永久停止する → launchd直起動に置換すること (2)**timeoutが仕事の途中で殺す** → sutando の core-agent パターン(終わるまで走る)を採用 (3)**PushNotificationはDaisに届かない**(Remote Control非アクティブでsilent no-op) → `openclaw message send --channel telegram --target 8547730585` を使うこと。残りloopを直す時もこの3点を必ず確認する。

## 2e. GOALS（Dais 2026-07-12 夕方 確定・音声指示）
| プロダクト | MRR目標 | 稼ぎ方 |
|---|---|---|
| life-manager web app | $10k | 人生管理AI（本命）。マーケ=IG/Reddit/動画 |
| capafy | $10k | skill販売+promote |
| gig | $5k | 出品(shuppin)+納品(nouhin)で受注 |
| article | $10k | note/Substack/X の有料記事（記事自体がマーケ） |
| clipping | $1k | クリップ動画 |
| anicca iOS app(affirmation) | $10k | larry+reelclaw+honne のSNS動画マーケで伸ばす |
- 合計 ≈ $46k → 最終目標 **$100k MRR**（$200の課金で$100k稼ぐ = "profitable claude" の証明）
- ★スコープ変更(Dais明示): **affiliate/bounty/explorer = 後回し**（大きく稼げる保証なし）。automaton(com.anicca.daemon)= **一時停止済**(2026-07-12、Conway Claude出荷まで。plist=.disabled-2026-07-12-until-conway)
- 優先順: **①life-manager マーケ修理 → ②clip 修理 → ③全loopのself-heal/self-improve一般化（マーケloopが自分で数字を追い自分で直す）**
- マスタープラン3段: (1)Claude が Dais に$100k MRR稼ぐ → (2)一般化して OpenClaw/Hermes でも同体験+完全OSS化 → (3)全部クラウドホスト（Daisはスマホだけで運用、物理PC返却）
- lm-video の実行主体判明(2026-07-12): OpenClaw gateway live cron（`lm-video-store-recording` 2h毎 + `lm-video-post-morning/evening`）= 幽霊ではなく稼働中。jobs.json に無いのは既知のlive-store desync。周辺に larry/reelclaw/honne のマーケcron約20本が全部ok稼働・Telegram announce設定済み

## 2f. 全ループ運命表（2026-07-12 夜。ON/OFF の唯一のアライン正本。変更は必ずここを更新）
| ループ | 今 | 運命 | 理由 |
|---|---|---|---|
| gig-core+auditor毎時+daily-report | 🟢ON | **ON維持**(T0-3で単発化) | 唯一動く稼ぎ導線(応募/出品が実UI確認済) |
| capafy-daily / article-daily / life-manager-daily / connector | 🟢ON | **ON維持** | 単発型で安い。articleはT0で時間上限追加 |
| clip系(core/promote/video tmux+launchd6本) | 🟢ON | **OFF→P2で修理後ON** | 投稿壊れたまま$59+/日=純浪費。Dais「1日1投稿なら良い」はP2完了後に実現 |
| reddit-loop | 🟢ON(2.5日連続) | **OFF恒久** | 垢BAN=何を書いても無意味 |
| affiliate-core / bounty-core / explorer-core | 🟢ON | **OFF**(deferred解除まで) | Dais後回し指定なのに常駐課金 |
| selffixゾンビ4本 | 🟢💀 | **即kill**(T0-2) | 設計外の永久課金 |
| realityverify-franklin | 🟢ON | **OFF** | Franklin=self-funded領域、claude-p課金で見守る必然なし |
| pm-earner / claude-p-mainloop / heartbeat / automaton | 🔴OFF | **OFF維持** | 停止済(pm-earnerは蘇生機構も切除済) |
| Franklin/agent-economy/pm-deterministic/OpenClaw cron群/ceo-runner | 🟢ON | **ON**(対象外) | Daisサブスクを燃やさない |

## 3. AS-IS（今の実態、launchctl 実測）→ TO-BE（理想）
```
AS-IS（混線・半分移行）:
  gig・capafy = anicca に居る（場所が間違い）  life-manager = ✅単一起動(2026-07-12 anicca loop版退役、PC core のみ)
  connector/affiliate/bounty/explorer = PC（正しい）
TO-BE（片付け後）:
  PC の 8 loop 全部が PC レシピ・hf-* Label・目覚まし1つずつ・重複ゼロ
```

## 4. 各 loop の TO-BE サイクル（全 loop 共通の型・no human・no CEO監督）
```
[BASE] 行動 → 実 side-effect(実URL/gcal/入金/ledger)を出す
[REALITY-VERIFIER] ★各loop内・report読まない★ browser(logged-out)/on-chain/gcal で実物を見て PASS/FAIL
   PASS → 記録（SUCCESS後も毎日再検証） / FAIL → [SELF-HEAL] self-fix→根因fix→再verify→再発防止をcodeに焼く
[SELF-IMPROVE] 日次で戦略1変異 → verifier が実成果で採否
```
CEO = 薄い機械 gate（予算 hard-stop + registry のみ、loop 殺す/作る判断なし）。

## 5. FULL TASK LIST（唯一・atomic・1行1アクション+done。上から実行）

### 実行方針（Dais 2026-07-11 確定・3ステップ・gigから1つずつ）
0. **verifier を全ツール使える様に直す** — [x] DONE: reality-verifier に「:9222ログイン済browser drive/on-chain/gcal 必須・report読むな」明記
1. **各ループを実際に稼ぐ/仕事する様に直す**（1つずつ・私がbrowserで実state確認・移動/改名しない・重複退治だけ例外）
2. **self-heal を各ループに内蔵**（healthcheck/self-fix が fresh adversary=reality-verifier[全ツール] を呼び実side-effectで判定→乖離→修復→再発防止をcodeに焼く。babysit不要に）
### Phase 1 — ★方針変更(Dais 2026-07-11): 移動/改名しない・その場で直す・重複退治だけ例外★
```
[x] M1 REVERTED — 私のミス: PC切替が24日動いてたanicca gig loopを止めた→revert完了・anicca本体復元(account ログイン済)。gig は移動しない。
[x] M3 life-manager 二重起動を1つに(2x課金停止) — ✅DONE 2026-07-12: anicca版(life-manager-loop) 退役=launchd bootout+disable+plist改名、tmux worker(loop+selffix)kill、worker process 消滅を ps で実証、復活escalation不在を grep 確認。PC版(life-manager-core)は稼働継続。→ ★Phase 1 全完了★
[~] M2/M4 migration/relabel = 保留(Dais:移動しない)。loopはその場で直す
[ ] S1 registryからhl削除 — done: hlエントリ無し
[ ] S2 registryのpmを対象外注記 — done: crypto=別CCと明記
[ ] S4 vestigial cron削除 — done: 5分毎起動しない
[ ] S5 .disabled-agent-economy cruft削除 — done: 残骸無し
[ ] S7 CANONICAL_LOOPSにconnector追加 — done: 予算gateに載る
[ ] C1 logs/stateをrepo-local化 — done: ~/.openclaw参照0件
[ ] C2 vendor skill本体を実copy — done: 外部shell out無し
[ ] C3 gcal-policy.shをrepo内copy — done: 外部参照無し
[ ] C4 .envをrepo-local化 — done: .env.example有り
[ ] C5 affiliate~/.cloak参照confine — done
[ ] C6 bounty/affiliate/gig cliの~/anicca参照confine — done
[ ] C7 confine完了をgrep0件で検証 — done: state/log除き0件
```
### Phase 2 — 各loop修理（1つずつ・VCSDD lean・adversary=Sonnet・私のbrowserで実side-effect確認・verifyまで次に行かない。clip/video/reddit=anicca別CC）
```
[x] L1  gig 実際に仕事させる ★完全クローズ2026-07-12★ — 24日本体復元済・ALIVE・.last-pass=今日・KYC全済(Dais確認)。★確定RCA(files実測+loop自lesson)★: earnings.jsonl=空=¥0。真因3点=(A)出品(shuppin)ステップがharnessに1つも無い→受動受注チャネル欠落(応募だけ=構造的accept2%床・飽和・¥0、loop自lesson pass88/92で5回確認)、(B)auditor.shがreport-blindでない=core自作jsonlを信じbrowser実UI照合せず、(C)応募数少なすぎ(max_apply_per_pass=5/時)。fix=[FIX A]B0出品step追加 [FIX B]auditorにreality-verifier(browser:9222)組込みreport-blind化 [FIX C]¥0継続/主張≠実UIでself-fix.shにコード修正escalate + 応募throughput増。★browser-use検証+self-improveのBPを自己流にせずweb/gh調査中→docs/loop-engineering/25-...bp.md→そのBPでverifier実装★。★増分2b DONE+merged(2026-07-12, main da4e2cb4)★: auditor が毎時 fresh reality-verifier を spawn→:9222で出品/取引/売上ページを実navigate(cdp_nav_snapshot.py=決定的Page.navigate)+screenshot→report-skeptical判定→証跡なきtrue却下(gig_reality_gate.py, main-session が test 12/12 実走確認)→FALSE時 self-heal-request。auditor再起動で本番稼働。残(私が直接): (a)✅self-heal配線DONE(2026-07-12, auditor.sh: reality-verify FALSE→self-fix.sh gig dispatch→request一回消費、DRYRUNでend-to-end検証済) (b)✅50/50 explore/exploit 自己改善DONE(2026-07-12, main 9105b97f: passprep が improve pass毎に improve_cycle→improve_mode(explore/exploit交互)出力+experiments_due surface、gig-cli B4=EVAL(実funnelでkeep/revert・verdict:false時昇格せず)+EXPLOIT(内省)+EXPLORE(firecrawl/gh外部BP検索→1変異のみ実験記録)、passprep test 34/34緑・explore4→exploit8をmain-session実走実証、judgment=agent/passprep=決定的bookkeepingのみ) (c)✅funnel metrics DONE(2026-07-12, main 989acbdb: gig_funnel.py=決定的stdlib・pass非crash、applied/lessons/earnings/shuppinを集計しoverall+by_category(applied/replied/won/paid/jpy/listings_live)を gig-funnel.jsonl に毎pass append。既存孤児schema継続。gig-cli に EARNED CHECK後 funnel呼出配線+applied行category追加+B4-EVAL/baseline を funnel読取りに整合。本番~/gig実走=applied106/replied40/won2/paid0/live2/47cats=RCAの¥0と一致。test gig_funnel3/3+node34/34緑) (d)✅:9222タブ競合対処 DONE(2026-07-12, main 6a533df7: cdp_lock.sh 共有advisory lock=mkdir-atomic+25min stale-steal。verifier は判定spawn直前に取得・取れねば DEFER(deferred_cdp_busy・spawnせず・self-heal書かず)、core は browser駆動前取得しpass終了前release。daily-driverタブ規約準拠(排他のみ・複製close無し)。E2E実証=core保持中verifier→deferred/spawning0/selfheal無し。test 51/51+funnel/gate/judge全緑) → ★★★ gig L1 完全クローズ (a)(b)(c)(d)全DONE ★★★ ／ ★実ループ検証(2026-07-12): 実ブラウザ(:9222, ログイン=Kosuke AIエンジニア)で coconala.com/mypage/job_matching/applied/offers=応募管理を開き、ループが今日00:48-00:56に出した実応募9件(戦車/健康食品/着物/アニメ映画/植物メディア/Threads/翻訳/海外EC)が提案額・納品日つきで送信済み表示=G1確認済。G1✅ / G2✅disk回収DONE(2026-07-12: ~/.ollama/models 6.4G削除=再DL可、空き2.3G→11G、ENOSPC解消。ollama cronは次回自動再pull) / G3✅トリガー修復DONE(2026-07-12: 真因=gig-proactive.plist未ロード+proactive-loop-dispatchがENOSPCでcrash(log 7/9凍結)。G2でdisk解消後dispatchはcore-status.json clean書込成功→launchctl bootstrapでgig-proactive load(affiliate/bounty/clip兄弟と並列)=5分トリガー復活。発火実測確認済(watcher: TICK FIRED 03:02, core-status ts前進)) / G4❌診断済(2026-07-12: gig日報メール機構は不在=gateway に gig/report/digest cron ゼロ・gig skillsにメール送信コード無し。stdout JSON report はメールでない。→Telegram(8547730585,既存OpenClaw報告先)に変更。G4✅DONE(2026-07-12: gig_daily_report.sh=台帳読み honest summary→openclaw message send、実送信テスト成功 Message ID 1938、launchd ai.anicca.gig-daily-report 毎日09:07JST load済、main 37410ebe)) ★★★ gig G1-G4 全DONE=gig完全クローズ ★★★
[x] #5  connector ★クローズ2026-07-12★ = 自律+継続ループへハンドオフ（launchd fill-gaps 07:50 + report 09:10 日次稼働、ダブルブッキング自己回避を gcal_write ガードで実装・実証、offline実会場5日確定7/13-17、online junk全削除。真因=gcal_write 丸1日枠abort→ルーティン予定と全衝突→永久に埋まらず。fix=実時刻窓に重なる時刻付き非connector予定のみabort。7/16が日中13:30→夜18:30(WeWork渋谷)へ自己再登録が実証。残りの空き日は日次loopが自律収束。evidence=005-connector.md）。以下は旧経緯 ↓ 全horizon枠+7日streak ← 今ここ(connector, gig完了後2026-07-12) ／ ★真因=全13登録がconnpassのみ・Lumaゼロ(順序がconnpass先→Luma後で枠が埋まりLuma未到達、Luma試行1件はgcal衝突で失敗)。fix=connector-cli STARTMPをLuma-first(メイン)+connpassサブに反転 commit f0ad32e、restartで新プロンプトlive→Luma実登録を検証予定★ — ★main-session 直接fix中(builder不使用, Dais 2026-07-12)★: fix A(STEP1=全open horizon日loop)+fix B(first-pass 120分ハング検知+self-heal発火) commit済・修正版でcore再走中。RCA=doc27。残: (a)実応募がapplications.jsonlに載るのをlogged-out firecrawlで独立検証(DaisNar参加者リスト) (b)connector-streak-verify-daily(既存未起動)のlogged-out照合を稼働 (c)7日streak。done: 各日Telegram delivered:true+gcal readback+全応募が実在event ／ ★2026-07-12 Dais 追加要件(明示): (1)OFFLINE/対面(Tokyo会場)のみ=人と会って networking する為、online/オンライン は登録禁止(過去11件は全部 location:online=これが最大の欠陥) (2)テーマ=crypto+AI優先(web3/blockchain/agent/LLM)、generic非crypto非AIは最後 (3)Lumaメイン+connpassサブ(両方 offline+crypto/AI gate)。fix=connector-cli STARTUP STEP1に HARD RULE #1(offline-only)+#2(crypto+AI優先) 焼込 commit 0652d43 push済。実行系=cron ad89027d→connector-cli.sh --restart→tmux worker が \$STARTUP 実行(payloadはファイル委譲なので幽霊cron問題なし)。03:23 JST に --restart でライブパス起動、offline crypto/AI の Luma実登録を gcal(location=実会場)で検証中★ ／ ★✅実証済(2026-07-12 03:58): (1)online connpass 6件(7/13-18)を gcal から削除 (2)Luma「AI Growth Tokyo 2026 - AI & Web3 Track」(luma.com/x92v6uvi, 7/15, Tokyo Innovation Base千代田区, AI+Web3)に実登録=?tk=cHuMc0+参加確定+keiodaisuke@gmail.com確認メール(msg 19f528addd)+gcal get_event id=fu7anjp34o3mlu12vjee57a7rk location=実会場confirmed の3点裏取り (3)connpass AI-Driven Dev Meetup(7/14,紀尾井町LINEヤフー,対面)も登録。before=全online→after=全実会場+Luma+AI/crypto+Dais本人アカウント。evidence=docs/superpowers/evidence/005-connector.md。残=STEP5 Telegram配信+7日streak+adversary★ ／ ★🔧ループ再設計(2026-07-12 04:33, Dais「full 2週間埋めろ・プロンプトでなくループ改善」): 真因=1 LLMパスが2-3件で早期停止。fix= connector_fill_gaps.sh = 決定論的 per-day driver(gcalから空き日を列挙→各日1件だけ登録する短命 claude -p を順にspawn→末尾で日次報告)。launchd 2本: ai.anicca.connector-fill-gaps(07:50)+ai.anicca.connector-daily-report(09:10)。Telegram真因=長いSTEP1でSTEP5未到達→独立レポートジョブで解決(送信経路OK: msgId 1941/1942/1943 実配信確認)。競合バグ=connector 2系統(旧cli tmux+driver)が:9222奪合→旧tmux kill。commit: 0652d43(offline+crypto)/runbookコピペ/crypto-quality/file-based-prompt(command too long bug fix)/fill-every-day/fill_gaps driver/daily-report、全push。埋済=7/13(Web3×AI agents Luma)+7/14(AI connpass)+7/15(AI&Web3 Luma)全対面東京。埋め中=7/16,17,18,19,20,22,24。残TODO: (a)driver が7空き日を着地(実行中,slow=各日discovery再実行) (b)高速化=discover-once(luma tokyo/crypto 1回scrape→全日マッピング) (c)cron ad89027d が今も connector-cli.sh --restart 指してる→07:35で旧パス復活し driver と競合リスク、fill_gaps に向け直す or disable 必要 (d)fresh adversary PASS★
[x] #8  life-manager セルフマーケ ★クローズ2026-07-12★ — loopを実際に直し、直後のパスが**自力で新規IG投稿を産んだのを私が自分の目で確認**: https://www.instagram.com/p/DarB2Qikt3d/ (19分前投稿、"Stop searching travel time for every event"クリエイティブ、CTA=aniccaai.com/life-manager、実ブラウザでスクショ)。★直した3点★ (1)毎日10:15のlaunchd(`ai.anicca.life-manager-daily`)で確実起動(自己申告cron依存を廃止) (2)**timeout削除**(20分で仕事の途中でrc=124 kill されて1件も投稿できていなかった真因。sutando=github.com/sonichi/sutando の core-agent パターン「終わるまで走る」を採用) (3)**Reddit BP焼込**(docs/loop-engineering/29-reddit-marketing-bp.md、Sprout Social等の引用付き): 両チャネル必須+karma gate(karma<50は宣伝禁止、純粋な有用コメントでkarma育成)+90/10ルール。実証=loopが自分でkarma=1を実測しBP通り宣伝せずr/ADHDで有用コメントを投稿 (4)**Telegram報告を修理**: PushNotificationは未達だった(Remote Control非アクティブでsilent no-op)→ connector/gig と同じ `openclaw message send --channel telegram --target 8547730585` に切替、messageId 1973/dryRun=false で実配信を検証。収益は正直に$0(ユーザー0人)。evidence=08-lm-phaseB.md + screenshot 08-lm-ig-new-post.png
[x] L2  capafy public掲載 ★完全クローズ2026-07-12★ — done条件(status=4 browser確認 + "PUBLISHED"嘘なし)を充足し、さらに**loopが自力で新規スキルを審査提出まで完遂**するのを実証。①公開20件を実ブラウザ(ログアウト=買い手視点)で確認、購入導線まで実在(evidence=L2-capafy.md)。②毎日08:10のlaunchd(`ai.anicca.capafy-loop-daily`)を配線し、**08:10:05に人の手ゼロで自動発火**をログのタイムスタンプで実証。③**真因3つをloop自身が発見・修理**: (a)timeout 1200 が CP1 の途中で毎回 rc=124 kill → timeout削除(sutando=github.com/sonichi/sutando の core-agent「終わるまで走る」パターン採用) (b)`ANTHROPIC_API_KEY`残高$0でheadless即死 → unset して subscription auth に fallback(commit f163b975) (c)**二重スケジューリング**(launchd 08:10 と OpenClaw cron 09:00 が同じ:9222タブを奪合い1.5hで5回重複起動・全て "Reached max turns(40)" で失敗)→ mkdir排他ロックを実装。④「下書きで終わり」を禁止しCP1→CP2→CP3完遂を焼込 → **孤児DRAFT(4866150011 Decision Debate)を拾い上げ審査提出まで完走**。CP1の真の詰まりは「モデル提供元」未入力+「DPA同意」未チェックだったとloop自身が特定。⑤**私が独立にAPI照合**: status=1(審査中)/isConfirmedSkills=1/isConfirmedConfigKeys=1/auditStatus=1/model=Claude Sonnet 4.6 — 全て揃い、報告と実APIが一致(嘘なし)。⑥Telegram報告をPushNotification(未達)→`openclaw message send`(messageId 1973実証)に修理。収益は正直に**$0**(掲載は成功、売上はまだゼロ=IMPROVE層の課題)。
[~] #7  article ★2026-07-12 大半クローズ・残2★ — done条件をDaisが改定: **5媒体すべてに draft を置き、絶対に自動公開しない**(AIスロップを世に出さない、公開はDaisが手で行う)。★最重要発見: このループは動いていたら全世界に自動公開していた★ — adversarial audit で判明した修理前の実態は Zenn=published:true を必須要求しpushで即公開 / Substack=draft作成直後に無条件POST /publish / note=create_draft直後に無条件publish_article() / dev.to="published": not DRY_RUN(実行=公開) の **5媒体中4媒体が正常動作として無条件公開**。全てコードレベルで塞ぎ(prompt頼みにしない)、run.sh の検証も反転(draft/404=成功、公開200=SAFETY FAILUREで叫ぶ)。全TDD。実走行(14:28)の結果=記事「AIエージェントは人間なしでAPIの代金を払えるのか(x402を実際に動かして検証)」を日英で執筆し **Zenn/dev.to/Substack ja/en の4媒体に draft staging、公開ゼロ**。Zennは実ブラウザで404(非公開)を、dev.toはAPI published=False+無認証404を、私が自分の目で確認。Telegram報告 messageId 1990(私のテスト送信1991で本物と確定)。launchd `ai.anicca.article-daily` 06:00 ロード済み=明日から自動で回りnote/Xも毎日再挑戦。真因3つ(自己申告cron/timeout/PushNotification)は設計で回避済み、+実行1回目の「丸投げして緑で記事0本」も修理(BG_WAIT_CEILING=0)。**残2: (a)note=ログインのVue reactivity(fill()がcontrolled inputに反応せずsubmitがdisabledのまま、実キー入力+input/changeイベント発火で直る見込み) (b)X=セッション失効+認証情報が.envにも~/.cloakにも無く再ログイン不可**。収益¥0(下書きのみ、Daisが公開して有料記事が売れて初めて¥)。evidence=07-article.md
[~] L5  affiliate — ★DEFERRED(Dais 2026-07-12: 稼げる保証なし・後回し)★ 再開時: warmup起動元をgateway live cronで特定→launchd化→7日warmup→実投稿URL
[~] L7  bounty — ★DEFERRED(Dais 2026-07-12)★
[~] L8  explorer — ★DEFERRED(Dais 2026-07-12)★
★実行方式(Dais 2026-07-12): 1つずつ・superpowers(brainstorming→writing-plans→subagent-driven-development)+VCSDD lean(spec駆動+TDD)。順序=P1→P9厳守★
━━ Phase 0: token止血（2026-07-12 夜 Dais承認。P1より先 — 残15%を守る緊急処置。詳細=doc 31）━━
[ ] T0-1 token日報watchdog — token-daily-report.sh(作成済み・未テスト)を実Telegram送信テスト→launchd 09:15 JST登録。毎朝「昨日$XX/犯人TOP3/常駐セッション数/ゾンビ数」
[ ] T0-2 ゾンビ退治 — 残selffix 4本(clip/Franklin/founder/clip-promote)をkill + self-fix.shに自壊タイマー(最大2h)実装(掟2)
[ ] T0-3 常駐tmux廃止 — core loop群を「単発claude -p+launchd」型へ改修(掟1: 起きる→働く→死ぬ)。★P3と同じファイルを触るのでP3と同時実施★
[ ] T0-4 無価値常駐の停止 — Dais承認の運命表(§2f)どおりOFF実行: clip系(P2まで) / reddit-loop(BAN) / affiliate・bounty・explorer-core(deferred) / realityverify-franklin
[ ] T0-5 メイン節制の恒久化 — 掟5(subagent最小限・調査1体・全Sonnet)をCLAUDE.mdに1行追加(memory焼き込み済み)
[ ] P1  life-manager マーケ修理（最優先）— ★手順改定(Dais 2026-07-12): loopに焼く前に、まず私が手動で動画を1本生成→TelegramでDaisに送る→品質アライン→OKが出て初めてloopに組み込む(loop化は金がかかるので品質合意が先)★ (a)動画クリエイティブ: MoneyPrinterTurbo実導入 or 稼働中の lm-video パイプライン流用で静止画カード→動画へ (b)Reddit: @anicca_sao shadowban→appeal結果待ちと並行してCloakBrowser daily-driverで再ログイン/新アカウント+karma育成 (c)LM専用IG/Redditアカウント作成（借り物@anicca.affirms2脱却） (d):9222 mkdir排他ロック実装 — done: 動画クリエイティブがIGに実投稿され実URLをTelegram報告
[ ] P2  clip 修理 — (a)投稿ハングRCA(CDP Networkで共有確認コールを完全捕捉、client stall vs server drop確定) (b)@aiclipsvault へ投稿再開 (c)Telegram実URL報告を配線(現状実装ゼロ) (d)PC repo に human向け fiat-affiliate 版 clip skill を派生（同じskill、報酬先=人間の銀行） — done: 正しいチャンネルに毎日実投稿+URL がTelegramに届く
[ ] P3  self-heal/self-improve 一般化 — gig L1 で実証済みの3点セット(report-blind reality-verifier + funnel metrics + self-fix escalation)を共有harness lib化し全loop(特にOpenClawのlarry/reelclaw/honneマーケcron群とlife-manager)に配線。healthcheck=プロセス生死でなく「spec上のside-effectが直近24hに実在するか」で判定 — done: 「2日投稿ゼロ」を各loopが自分で検知→self-fix発火する実証
[ ] P4  article 残2修理 — (a)note: Vue controlled-inputに実キー入力+input/changeイベントでログイン (b)X: 認証情報を再取得(.env/~/.cloakに無し)して再ログイン — done: 5媒体すべてdraft staging
[ ] P5  gig 売上化 — funnel実測 applied106/replied40/won2/paid0/live2 → 出品(shuppin)本数を増やし受動受注チャネルを太らせ、納品(nouhin)→入金まで — done: paid>0 が funnel jsonl+実UIで一致
[ ] P6  capafy promote — 掲載20件は公開済み・売上$0 → P3のマーケ自己改善をcapafy宣伝にも適用 — done: 初売上
[ ] P7  profitable-claude repo への confinement — clip等anicca側の人間向けloopをPC repoへvendor、外部参照0件(C1-C7パターン)、1コマンドinstall(own Claude subscriptionで走る)→OSS化
[ ] P8  OpenClaw/Hermes 対応 — loop=prompt+scheduler+CLI+jsonl state の model-agnostic 設計を維持し、scheduler/model呼び出しだけadapter化
[ ] P9  クラウドホスト — Daisスマホのみ運用。ホスト先=★routines(Claude Code cloud /schedule) か Akash/DigitalOcean系に傾き(Dais 2026-07-12)★。ブラウザ系loop(CloakBrowser必須)はroutinesに載らないため、box(Akash/DO)+routinesのハイブリッドが有力
[x] #6  CEO仕上げ ★クローズ2026-07-12(自分で実装・subagent kill後に take over・全検証自分の目)★ — ①cost自己申告照合を日次light-passに配線(bin/ceo_run.py, record_cost_claim_warnings+stamp_last_observed_at)→実発火確認(gig cost-claim-unbacked を実検知) ②registry真値化=欠落してた sol(Solana) を external/external-anicca で追加(11ループ揃う、capafy/article/pm/hl/sol=external正) ③ceo-decisions.jsonl に週次decision 1行実在。全CEOテスト緑(registry 29/29・last_observed 6/6・cost-wiring 4/4・anicca_ref 5/5・gcal_write 7/7)。commit群 push済。※残1赤 vendor PROP-055=life-manager-cli の vendor 参照=#8/LMの領域(CEO無関係pre-existing)
[ ] #9.5 SNS factory移行 — done: Dais go後にOpenClaw退役
```
### Phase 3 — colony 戦略ゴール（★Dais 2026-07-11 原案・end-state・忘れ厳禁★）
```
[ ] G-GIG-FULL  gig 稼ぎ戦略 spec(2026-07-08) を full 実装（現~30-40%→100%）。詳細tracker=doc 26 §6.5。
                出品playbook(松竹梅/モニター価格/サムネ文字/ベネフィットtitle/成果物ニッチ)・応募速度rule(掲載30分)・
                50/50 BP web検索自己改善・占い再分類・never-refuse・funnel metrics・feasibility明示。
                ※他 earn loop(clip/video/article/affiliate)にも同雛形を横展開(spec §7)。
[ ] G-CLOUD     全 earn loop を Mac Mini/PC から cloud へ移す(安価・無限スケール)。Dais は phone だけで運用、
                ローカル依存ゼロ、hundreds の claude が並行 earn。done: cloud で loop が回り実 earn、Mac停止でも継続。
[ ] G-PRODUCTIZE anicca の earn loop(gig/clip/video/…)を profitable-claude へ copy して実 earn。
                PC=「誰でも1コマンド→earn開始」製品。各 claude が自分の Coconala等 account を新規作成→自走 earn。
                hundreds spin-up 可能に。done: PC repo 単体で1コマンド起動→新account→実¥。
                ※「fix in place優先」は当面の戦術、この G-PRODUCTIZE が最終形。
```

## 6. Done 判定（全 task 共通、spec §10 準拠）
実 side-effect を **reality-verifier が独立確認**した時のみ done。report/test-green/adversary-PASS は done でない。「PROPOSED/draft/enqueue」は done でない。収益は on-chain/Stripe 実記録で照合。

## 7. 詳細は各ファイル（このSSOTがindex、詳細のみ委譲）
| 知りたい | ファイル |
|---|---|
| ★gig ループ AS-IS/TO-BE/実行計画(compact-proof正本)★ | `26-gig-loop-asis-tobe-plan.md` |
| browser-use 検証+自己改善 BP(judge.py実物) | `25-browser-use-verify-selfimprove-bp.md` |
| reality-verifier の設計/OSS調査 | `24-shared-ground-truth-verifier-design.md` |
| 全loop真実監査(browser/on-chain実測) | `../superpowers/evidence/LOOPS-TRUTH-AUDIT.md` |
| connector loop の元 spec/done条件 | `../superpowers/specs/2026-07-10-connector-loop-design.md` §10 |
| loop設計BP | `22-...bp-loop-verification-review.md` |
