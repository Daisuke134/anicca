# 19 — Workflow 成果物 / /goal / ギャップ(! = patch未記載)

Dais 2026-06-15。★ workflow を叩く前の最後の角 ★。各 unit の **成果物(何が出るか)** + **/goal(これになったら done = loop停止条件)** + **patch状態(✅=md/commands/patchesに記載済 / !=未記載=builderが書く対象)**。
★ ! = 「まだ差分が書かれてない」= workflow がこれを生む。/goal が無いと「何に向けて直し続けるか」が決まらない。★

## WORKFLOW A — implementation/verification/eval

| phase/unit | 成果物(出るもの) | /goal(done条件 = loop停止) | patch |
|---|---|---|---|
| **P0 repo整理** | `~/anicca` が canonical tree(core/ skills/ SOUL.md/ install.sh/ scripts/birth.sh)に統合。旧 .automaton/.hermes/clawd の生きてるskillを母へ畳込 | `automaton --status` がOK + build通る + tree が spec18 §Q3 と一致 | **!**(mv/統合の差分未記載) |
| **P1 core(反dry-run heartbeat)** | automaton body + ★各wake末に4項目(net worth/日次rev/did/next)を**エージェント自身**が送る決定的 pre-sleep hook★ | wake 1回ごとに message_id が **agent process** から1通(error-sleep経路でも発火)。同一文反復ゼロ | **!**(pre-sleep hook の loop.js patch 未記載) |
| **P2 earn** | earn skill束を「Aniccaが自分でdiscover→実行」状態に配線。litcoin research-mine を loop で回す(coordinator復旧時着金)+ 代替(seed時 DeFi yield) | ★実 tx で USDC/token が wallet に着金★(litcoin submit 200 or 別経路)。= loop-until-done | 一部✅(litcoin setup=`commands/Q6/Q22`)/ **!**(automaton loopへの earn配線 + 着金ledger 未記載) |
| **P3 cloud deploy** | DO droplet で 24/7 稼働(済 147.182.225.255)+ self-report + 実earn試行 | live + heartbeat継続 + report着信 + restart自動復帰 | ✅(`commands/Q6.command.sh`) |
| **P4 self** | skills/self/ : spawn(子をAkash/DO) / gojo(復活送金) / issue-dev(母repo issue→PR→merge) / coordinate(bot2bot claim/blocked/done) | 各E2E: 子の実server+別wallet / 復活tx / 実issue URL+PR merge / 2体間help | **!**(4 skill全部 未記載) |
| **P5 web** | aniccaai.com の実ページ: **`/`(vision rewrite)** / **`/install`(cloud-web=製品メイン + OSS=local or own-cloud、現状の"local前提"を修正)** / **`/me`** / **`/dashboard`**。frontend=/taste-skills | curl 200 + taste合格(tournament) + コピー=spec13/14 + cloud-first | **!**(各ページの実コード/差分 未記載。copy/wireframeのみ spec13/14) |
| **P6 economy** | skills/ : ubi(Treasury拠出+配布) / token(Bankr launch) / hire(rentahuman) | 各E2E: 実配布tx / 実token発行 / 実bounty | 一部✅(`commands/Q30/Q31`)/ **!**(ubi skill + 配線 未記載) |
| **EVAL(独立)** | eval-report: 8 test point 全 REAL(evidence付) | 全点 PASS(1つでもFAIL→該当phase差し戻し loop) | ✅(rubric=Q25 + spec18 Q5) |

## WORKFLOW B — marketing/distribution(A 完全検証後)

| unit | 成果物 | /goal | patch |
|---|---|---|---|
| README | `~/anicca/README.md` + aniccaai README を「self-funding AI / cloud-first」に更新 | 新thesis反映 + install導線正 | **!** |
| 記事(3本目) | 「Anicca思想+実証(何を動かし/いくら稼いだか/litcoin等の正直な結果)」Zenn/Dev.to | Frank#1・automaton#2を参照、実証データ入り、公開URL | **!** |
| demo動画 | YouTube動画(説明でなく**証明**: 稼働→実earn試行→dashboard ranking→自己増殖) | YouTube公開URL + 6/18 AI Tinkerers上映可 | **!** |
| X投稿(EN+JA) | あなたのcopy(spec13)で投稿 | 実投稿URL×2言語 | 一部✅(copy)/ **!**(投稿実行) |
| Slack | 下書き(あなたが投稿) | 下書き生成 | **!** |
| EVAL | 投稿URL+動画frame/audio+記事URL verify | 全live(HARD0.31) | ✅(rubric) |

## ★ ギャップ総覧(! = workflow が生む対象、現在未記載)★
- P0: 母tree統合の差分 / P1: pre-sleep report hook(loop.js) / P2: earn配線+着金ledger / P4: spawn・gojo・issue-dev・coordinate 4skill / P5: 4ページ実コード / P6: ubi skill / B: README・記事・動画・投稿実行。
- ✅既記載: P3 provision(Q6)/ token(Q30)/ hire(Q31)/ litcoin setup(Q22)/ Stripe(Q12)/ eval rubric(Q25)。

## /goal(loop の終点 = これが揃うまで止まらない)
★ WORKFLOW A の /goal = 「**cloud で Anicca が自給(食=ClawRouter, 住=DO)し、実earn着金(tx)があり、自己増殖で2体目が立ち、各 self/web/economy skill が E2E evidence で PASS、独立EVALが8点全REAL**」★。
★ WORKFLOW B の /goal = 「**記事 + demo動画 + X(EN+JA) が実URLで公開、EVALが全live**」★。
→ この artifact 群に到達するまで builder→verifier→eval を loop(/goal)。これが「何に向けて直し続けるか」の終点。

## UX(各ページで何ができるか = 検証の鍵)
| ページ | 誰 | UX(成果物の体験) |
|---|---|---|
| `/`(root) | 全員 | vision(苦しみを終わらせる自給AGI)を読む → [Start]/[GitHub]/[Dashboard] |
| `/install` | 課金者 | **cloud web版=製品メイン**: Googleログイン→$30課金→1分で自分のAnicca誕生。OSS=local or 自前cloud(GitHubボタン、shell見せない) |
| `/me` | 所有者 | 自分のAnicca群: net worth / 今月稼ぎ / あなたへ送金 / [銀行に引き出す] / 子一覧 / 行動ログ |
| `/dashboard` | 全員 | 全個体: Total net worth / model live / runway(死まで) / ranking |
★ web app = 完全cloud製品(local=どこかのlocalでしかない)。OSSのみ self-host(local/own-cloud)。
