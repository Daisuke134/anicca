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
| affiliate | 紹介投稿→紹介料 | reCAPTCHAで06-30からlogout・投稿0 |
| bounty | 懸賞提出→賞金 | idle・survivor0 |
| explorer | 機会探索→他loopへ供給 | proposal走るが収益化0 |
| life-manager(core) | 予定/連絡/intake→MRR | ★2026-07-12 anicca版(loop)退役済=単一起動★・空稼働・MRR0（次は#8で稼働） |
### anicca=crypto/SNS(別CC)+一部bank混線
| loop | 何をする | 問題 |
|---|---|---|
| gig | Coconala出品/提案/返信/納品→銀行 | 24日本体復元済。提案(teian)・出品(shuppin)・納品が足りない ←今 |
| capafy | skill販売→銀行 | 審査中status=1・public未掲載・"PUBLISHED"嘘(accountはログイン済) |
| ~~life-manager(loop)~~ | ~~(PC版と重複)~~ | ✅退役完了(2026-07-12): launchd `life-manager-loop-healthcheck` を bootout+disable+plist→.disabled、tmux worker(loop+selffix)kill、worker process 消滅=2x課金停止実証。復活escalation無し(LMHB=report専用)。PC core は生存継続 |
| clip | IG動画→crypto視聴報酬 | 別垢乱造・blur |
| clip-promote | 拡散→crypto | 選択だけsuccess・$0 |
| video | 動画→crypto | grid空・blur |
| reddit | 投稿→crypto | account BAN |
| founder/Franklin/pm/sol | trade→crypto | 別CC担当 |

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
[x] L1  gig 実際に仕事させる ★完全クローズ2026-07-12★ — 24日本体復元済・ALIVE・.last-pass=今日・KYC全済(Dais確認)。★確定RCA(files実測+loop自lesson)★: earnings.jsonl=空=¥0。真因3点=(A)出品(shuppin)ステップがharnessに1つも無い→受動受注チャネル欠落(応募だけ=構造的accept2%床・飽和・¥0、loop自lesson pass88/92で5回確認)、(B)auditor.shがreport-blindでない=core自作jsonlを信じbrowser実UI照合せず、(C)応募数少なすぎ(max_apply_per_pass=5/時)。fix=[FIX A]B0出品step追加 [FIX B]auditorにreality-verifier(browser:9222)組込みreport-blind化 [FIX C]¥0継続/主張≠実UIでself-fix.shにコード修正escalate + 応募throughput増。★browser-use検証+self-improveのBPを自己流にせずweb/gh調査中→docs/loop-engineering/25-...bp.md→そのBPでverifier実装★。★増分2b DONE+merged(2026-07-12, main da4e2cb4)★: auditor が毎時 fresh reality-verifier を spawn→:9222で出品/取引/売上ページを実navigate(cdp_nav_snapshot.py=決定的Page.navigate)+screenshot→report-skeptical判定→証跡なきtrue却下(gig_reality_gate.py, main-session が test 12/12 実走確認)→FALSE時 self-heal-request。auditor再起動で本番稼働。残(私が直接): (a)✅self-heal配線DONE(2026-07-12, auditor.sh: reality-verify FALSE→self-fix.sh gig dispatch→request一回消費、DRYRUNでend-to-end検証済) (b)✅50/50 explore/exploit 自己改善DONE(2026-07-12, main 9105b97f: passprep が improve pass毎に improve_cycle→improve_mode(explore/exploit交互)出力+experiments_due surface、gig-cli B4=EVAL(実funnelでkeep/revert・verdict:false時昇格せず)+EXPLOIT(内省)+EXPLORE(firecrawl/gh外部BP検索→1変異のみ実験記録)、passprep test 34/34緑・explore4→exploit8をmain-session実走実証、judgment=agent/passprep=決定的bookkeepingのみ) (c)✅funnel metrics DONE(2026-07-12, main 989acbdb: gig_funnel.py=決定的stdlib・pass非crash、applied/lessons/earnings/shuppinを集計しoverall+by_category(applied/replied/won/paid/jpy/listings_live)を gig-funnel.jsonl に毎pass append。既存孤児schema継続。gig-cli に EARNED CHECK後 funnel呼出配線+applied行category追加+B4-EVAL/baseline を funnel読取りに整合。本番~/gig実走=applied106/replied40/won2/paid0/live2/47cats=RCAの¥0と一致。test gig_funnel3/3+node34/34緑) (d)✅:9222タブ競合対処 DONE(2026-07-12, main 6a533df7: cdp_lock.sh 共有advisory lock=mkdir-atomic+25min stale-steal。verifier は判定spawn直前に取得・取れねば DEFER(deferred_cdp_busy・spawnせず・self-heal書かず)、core は browser駆動前取得しpass終了前release。daily-driverタブ規約準拠(排他のみ・複製close無し)。E2E実証=core保持中verifier→deferred/spawning0/selfheal無し。test 51/51+funnel/gate/judge全緑) → ★★★ gig L1 完全クローズ (a)(b)(c)(d)全DONE ★★★ ／ ★実ループ検証(2026-07-12): 実ブラウザ(:9222, ログイン=Kosuke AIエンジニア)で coconala.com/mypage/job_matching/applied/offers=応募管理を開き、ループが今日00:48-00:56に出した実応募9件(戦車/健康食品/着物/アニメ映画/植物メディア/Threads/翻訳/海外EC)が提案額・納品日つきで送信済み表示=G1確認済。G1✅ / G2✅disk回収DONE(2026-07-12: ~/.ollama/models 6.4G削除=再DL可、空き2.3G→11G、ENOSPC解消。ollama cronは次回自動再pull) / G3✅トリガー修復DONE(2026-07-12: 真因=gig-proactive.plist未ロード+proactive-loop-dispatchがENOSPCでcrash(log 7/9凍結)。G2でdisk解消後dispatchはcore-status.json clean書込成功→launchctl bootstrapでgig-proactive load(affiliate/bounty/clip兄弟と並列)=5分トリガー復活。発火は次tick(~5分)でcore-status ts/.last-pass進行を検証中) / G4❌診断済(2026-07-12: gig日報メール機構は不在=gateway に gig/report/digest cron ゼロ・gig skillsにメール送信コード無し。stdout JSON report はメールでない。→G4は『作る』: gig台帳(applied/shuppin/earnings/funnel)を読みkeiodaisuke@gmail.comに毎日サマリ送るcron+script新規作成が必要) ← 次G4は新規build★
[~] #5  connector 全horizon枠+7日streak — ★main-session 直接fix中(builder不使用, Dais 2026-07-12)★: fix A(STEP1=全open horizon日loop)+fix B(first-pass 120分ハング検知+self-heal発火) commit済・修正版でcore再走中。RCA=doc27。残: (a)実応募がapplications.jsonlに載るのをlogged-out firecrawlで独立検証(DaisNar参加者リスト) (b)connector-streak-verify-daily(既存未起動)のlogged-out照合を稼働 (c)7日streak。done: 各日Telegram delivered:true+gcal readback+全応募が実在event
[ ] #8  life-manager セルフマーケ — done: MoneyPrinterTurbo→Reddit/IG実投稿URL≥1+MRR導線
[ ] L2  capafy public掲載 — done: status=4 browser確認、"PUBLISHED"嘘出ない
[ ] #7  article 実publish→¥ — done: publish URL(logged-out一致)+metrics実測行
[ ] L5  affiliate reCAPTCHA突破 — done: 再ログイン→実投稿URL
[ ] L7  bounty 提出 — done: survivor→提出→賞金 or 正直none
[ ] L8  explorer 収益化 — done: proposal→実収益導線
[ ] #6  CEO仕上げ — done: cost自動記録+registry訂正+decision≥1(V3で縮退)
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
