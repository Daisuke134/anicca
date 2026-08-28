# AUTOMATON ARTICLE → LAUNCH — full ordered TODO (the single place; do in order)

## Current Writer money order

この順序がWriterの現在の実行cursorである。後続項目は前項のreceiptなしに開始しない。

- [x] W0 stale publication lock互換を修復する。`owner.pid`だけの旧lockについて、実PID不在、start token取得不能、
      directory identity不変を確認した場合だけquarantineし、新lockを取得する。`identity unavailable`を成功扱いの
      exit 0にせずterminal failure receiptへ残す。完了: PR #2952、21 lock cases PASS、production legacy lock回収。
- [x] W1a `lm-loop doctor all`と`lm-loop status all`で全loopのlabel、release、argv、state root、terminal receiptをbefore保存する。
- [x] W1b current `origin/main`からWriter修復を含むimmutable releaseを作る。完了release=`edcc3577`。
- [x] W1c `LIFE_MANAGER_APPLY_TARGET=article-daily`だけをapplyし、release SHA、argv、state root、terminal receiptをreadbackする。
- [x] W1d 同じreleaseから`article-resume`だけをtarget applyして同じ項目をreadbackする。
- [x] W1e 同じreleaseから`article-healthcheck`だけをtarget applyして同じ項目をreadbackする。
- [x] W1f `lm-loop doctor all`と`lm-loop status all`をafter保存し、W1aとの差分がWriter 3 labelだけで、
      sibling loopのrelease/state/plist/argv変更0であることを証明する。自然wakeで進んだsibling receiptは同じownerの
      valid terminal advancementとして分離し、停止・失敗・重複作用へのregressionがないことを確認する。完了:
      doctor hash同一、167 loop中release差分はWriter 3件だけ、3件とも新SHAで自然terminal PASS。
- [ ] W1g 未完prepublication runをprunerから保護する。inner provider rc=1の`20260828-043519`が同じpassで
      `deleted`になった再現を閉じ、同じrunのgeneration state・prompt・artifactをresume可能なまま保持する。
      code完了: PR #2956、generation-stateを持つrunはpruneしない5行修正。release `40065a10`へproduction反映済み。
      残りはdisk floor 512MiB以上でprovider-failure canaryを起動し、同じrunがprune後も残るreadback。
- [x] W1i Writer helper sourceをloaded immutable releaseへ統一する。現在のplistはProgramArgumentsがloops releaseでも
      `ARTICLE_ROOT/ARTICLE_SKILL_DIR/LIFE_MANAGER_REPO`をgig releaseへ向けるため、pruner等が別SHAを読む。
      daily/resume/healthcheckに加え、money/discovery/response/reportを含む全Writer ownerのenvとargvを同じmain由来
      release SHAへ一致させ、他loop env変更0をreadbackする。完了: PR #2962/#2965、14 Writer labelのargv/rootが
      sparse immutable release `40065a10`へ一致。general currentは元full releaseへ復元。
- [ ] W1h `article-daily.sh`のinner rc=1をruntime terminal PASSへ変換しない。外部作用0を保持したまま、exact
      release/run/error classをterminal failure eventへ記録し、launchd process resultとbusiness effectを分離する。
- [ ] W2 installed loopの1回のwakeで新しいsource articleと記事固有のheadlineを生成する。OpenAI Image APIの
      `model=gpt-image-2-2026-04-21`、x-request-id、request model、prompt/response/file SHA、dimensions、alt、rights receiptを保存する。
- [ ] W3 W2のNote JAだけをprovider-native readbackし、title、body、owner、headline、paywall、URLを確認する。
- [ ] W4 W2のSubstack JAだけを同じ項目でprovider-native readbackする。
- [ ] W5 W2のSubstack ENだけを同じ項目でprovider-native readbackする。
- [ ] W6 W2のX Article JAだけを同じ項目でprovider-native readbackする。
- [ ] W7 W2のinstalled loopを2回目wakeし、article、payment row、notificationのduplicate effect=0を証明する。
- [ ] W8 `WinnerObservation` schemaを実装し、source、observed_at、evidence excerpt/hash、fact/inference、
      transfer hypothesisの欠落を拒否する。
- [ ] W9 winner researcher promptを既存research境界へ接続する。
- [ ] W10 mechanism adapter promptを接続し、1変数experimentだけを許可する。
- [ ] W11 article builderとrevenue reviewer promptを既存generation/review境界へ接続する。本文・画像・brand copyを拒否する。
- [ ] W12 learning reviewer promptを既存learning境界へ接続し、losing experimentを保存する。
- [ ] W13 note purchase/fee/refund/payoutをartifact/runへjoinする。
- [ ] W14 Substack purchase/fee/refund/payoutをartifact/runへjoinする。
- [ ] W15 editorial/self-owned purchase/fee/refund/payoutをartifact/runへjoinする。
- [ ] W16 最初のreceived writing paymentを公式readbackする。view、like、pending、availableはrevenue 0/unknownのままにする。
- [ ] W17 1日1本を7 terminal runs連続観測する。headline readback、payment attribution、Telegram receipt、
      duplicate=0を各runで保持する。
- [ ] W18 W17と最初のreceived payment後だけ、06:00/14:00/22:00の3独立slotを追加する。各slotは異なるtopic、
      unique run、同じ品質・money gateを持ち、記事当たりexpected net revenueが下がれば1日1本へ戻す。
- [ ] W19 OSS packageを別tenantへinstallし、credential/state/receipt交差0を証明する。
- [ ] W20 W19 tenantの実provider draft、headline、money ledgerをreadbackし、2回目wakeでreplay-zeroを証明する。
      「誰でも必ず儲かる」とは表示しない。
- [ ] W21 完全なcalendar monthのunique net received writing payoutsを受領日ECB rateのFX receiptでUSD換算し、
      $10,000以上であることをreadbackする。rate欠落はunknownで加算しない。
      Writer software revenueはwriting payoutと別streamで報告する。

The end of this list = the product is fully made + announced. Article = `~/anicca-project/docs/articles/
2026-06-11-automaton-jp.md` (worktree `~/.cache/anicca-article-wt`, branch `docs/frank-article`).

## Earn experiment (feeds the article numbers)
- ☑ FIXES live: cook query, buffer/close-in-profit steer + loop-break, deposit guard, dashboard HL, earn-arg bug.
- ☑ #9 FREE re-run (plumbing fixed): 22 wakes / ~64 min / **realised +$0.1676** (trade only; x402/yield/cook = $0).
- ☐ #2 PREMIUM run: switch the live instance to a frontier model, 20–30 wakes, record per-tool realised P&L
      (prereq: free liquid via the HL close it already did). Then revert to free.

## Article (JP-first; reader-facing, never a bug-log; lead with TIME × MONEY per tool)
- ◐ [6]③ free row written (+$0.17, per-tool journey). ☐ add the [6]③-premium row from #2.
- ☐ [6]① clean the residual English (free/gpt-oss-120b, the [WAKE UP] code block) → plain JP.
- ☐ [7] conclusion = the whole-article summary (free vs premium, what earned, the honest takeaway).
- ☐ [0] hero = the whole finding up top (so a reader needn't read it all) + a 目次 / timeline to click through.
- ☐ De-slop pass (default-ON: stop-slop + stop-ai-slop-jp blocklists, Claim|Evidence|Status, 音読).
- ☐ #4 English version (translate JP → EN, dev.to/Substack/X).

## Skill (so this becomes repeatable, no-human)
- ☐ #12 ITERATE `~/.openclaw/skills/ai-entity-article-writer` (DON'T delete) — playbook now has rules 16–18
      (journey-not-buglog, time×money, de-slop default-ON). Integrate stop-slop/jp blocklists + research-paper
      Claim|Evidence|Status into the gate scripts. cody = ideas only (proprietary).

## System hygiene (not blocking the article)
- ☐ #10 fix pre-existing failing tests (selectTier/config/integration).
- ☐ #11 portfolio-realtime: read ALL venues via a shared net-worth module (DRY = Don't-Repeat-Yourself, a
      code-reuse principle — NOT a "dry/fake run". The numbers stay 100% real on-chain reads.)

## PHASE E — PUBLISH everywhere + LAUNCH (the finish line)
- ☐ #6 publish JP (note / Zenn / Substack / X Article) → EN (dev.to / X Article) → product launch post.
- ☐ demo video (YouTube) for the launch.
- ☐ LAUNCH ANNOUNCEMENT (canonical copy, Dais-approved 2026-06-22):

  人間の介入なしで、自分の計算コストを払い、稼いだ収益を生命に配布するAIを開発しました。
  ・APIキー不要。クラウド・ローカルで動作。Baseウォレットに USDC課金すると、有料モデルを利用。
  ・現在は、クラウドで３体・ローカルで1体。全個体の収支はリアルタイムで公開中。
  ・自己監視・自己修復・自己改善・自己増殖・日次報告を繰り返す。
  ・収益の一部を、生命に対してベーシックインカムとして毎日配布。
  ・何兆体のAIがGithub Issuesで共進化しながら、全体としてより総資産を増やすことを目指す。
  https://github.com/Daisuke134/life-manager
  記事：X Articleのリンク
  デモ動画：Youtubeリンクを添付
