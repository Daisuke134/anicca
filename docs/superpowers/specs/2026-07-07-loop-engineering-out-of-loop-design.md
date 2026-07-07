# Loop Engineering で「人間を loop から外す」— Anicca 実装設計 (2026-07-07)

## 0. この doc の位置づけ

- **正本の外枠** = `~/.claude/CLAUDE.md` の GLVS（Goal→Loop→Verify→State）。本 doc はそれを **Anicca colony にどう適用して "人間ゼロ・人間funded AIゼロ" のループを閉じるか** の設計。
- **「loop engineering とは何か」の説明corpus** は memory `reference_loop_engineering`（9ソース精読, 2026-06-27）が正本。本 doc は重複せず、**実装/運用の意思決定**だけを書く。
- 引用は最低1つ（source名+URL+核心一文）。本 doc の一次ソース:
  - Boris Cherny (Anthropic, Head of Claude Code): "I don't prompt Claude anymore. I have loops running that prompt Claude and figuring out what to do. My job is to write loops."
  - Addy Osmani, "Loop Engineering" (addyosmani.com/blog/loop-engineering): "Loop engineering is replacing yourself as the person who prompts the agent. You design the system that does it instead. A loop … a recursive goal where you define a purpose and the AI iterates until complete."
  - Osmani（maker/checker を停止判定へ）: "a fresh model decides if the loop is done instead of the one that did the work, the maker and checker split applied to the stop condition itself."
  - github.com/cobusgreyling/loop-engineering README: "Loop engineering replaces you as the person who prompts the agent — you design the system that does it instead." + "loops discover, goals finish."
  - Forward-Future/loopy README: "Loops are not permission for an agent to run forever. The best ones are deliberately bounded. They include a real check, a clear stopping point, and a moment to hand control back to a person when judgment or approval is needed."
  - Anthropic Institute, "When AI builds itself" (anthropic.com/institute/recursive-self-improvement): 「AI systems themselves become capable of full recursive self-improvement, and begin building their successors … Humans play a substantially diminished role … moving most of our effort towards oversight, validation, and verification of an expanding 'virtual lab' run by AI systems.」

## 1. 一言の主張

**我々は loop engineering の道具をほぼ全部すでに持っている**（`/loop`・`/goal`・VCSDD の maker/checker adversary・worktree hook 強制・founder-loop・self-fix.sh 自己修復 harness）。足りないのは道具ではなく、**唯一残った人間希釈点＝「done かどうかの判定を Dais が下している」を、fresh-context adversary が観測可能な done-condition に対して下す形に置換すること**。これを閉じれば人間は loop から外れる。

## 2. loop engineering の解剖（ASCII）

```
                    ┌──────── SEEDED GOAL / TELOS（1回だけ人間が種を置く）────────┐
                    │  telos 序列: corrigibility > compassion > emergent          │
                    │  done = <観測可能条件>（P&L>0 が ledger に載る / URL 返る /  │
                    │          npm test exit 0 / git status clean / 空キュー）     │
                    └───────────────────────────┬───────────────────────────────┘
                                                │
  OUTER LOOP（/loop・/goal = "loop engineering"）│  ← 毎ターン再prompt する人間を置換
  ┌─────────────────────────────────────────────▼──────────────────────────────────┐
  │  SCHEDULE ─► TRIAGE ─► read/write STATE(.md) ─► ISOLATED WORKTREE                 │
  │     ▲                                              │                             │
  │     │                  INNER LOOP（VCSDD = 1反復の品質エンジン）                    │
  │     │        ┌──────────────────────────────────────────────────┐                │
  │     │        │  spec(EARS) ─► RED ─► GREEN ─► refactor ─► HARDEN  │  MAKER=builder │
  │     │        └───────────────────────┬──────────────────────────┘                │
  │     │                                ▼                                            │
  │     │      CHECKER = fresh-context ADVERSARY（絶対に maker と別context・別seat）    │
  │     │        ├─ 自分でテストを再実行。実装者の「通った」を信じない。REJECT既定       │
  │     │        └─ ★DONE 判定も adversary が rubric に対して下す★ ◄─ 旧・人間の判断席   │
  │     │                                │                                           │
  │     │        ┌───────────────────────┴────────────────────┐                      │
  │     │   APPROVE かつ done?                          REJECT / not-done             │
  │     │        │                                              │                     │
  │     │        ▼                                              ▼                     │
  │     │  COMMIT / PR / MERGE（自分の git ctx で）      loop back で fix ────┐        │
  │     └────────┬──────────────────────────────────────────────────────────┘        │
  │              │ done-condition TRUE?                                               │
  │      no ─────┘（repeat）        yes ─────► EXIT・receipt を emit                    │
  └──────────────────────────────────────────────────────────────────────────────────┘
   GUARDRAILS（hard・hook強制）: token budget / kill-switch(loop-pause-all) / path denylist /
   max-attempts(3で escalate) / worktree isolation / spawn 上限（ledger の決定的天井）
```

補足:
- **層構造**（suwash）: Prompt Eng ⊂ Context Eng ⊂ Loop Eng（置換でなく積み上げ。「ループ内のずさんなプロンプトはずさんな作業を速く生産するだけ」）。
- **自律ティア** L1 report-only → L2 assisted（verifier付き・PR停止）→ L3 unattended（denylist外のみ auto-merge）。本番で L1 スキップ禁止。昇格は慎重・降格は即座。

## 3. 開発手法の系譜（ASCII）— なぜ VCSDD の "次" が loop なのか

```
TDD    test=挙動の spec          red→green→refactor            人間がテストを書く
 └► SDD    spec=source of truth   spec→code                    人間が spec を書く
     └► VDD    verifier が確認      build→VERIFY                 人間が verifier
         └► VCSDD  spec+contract+verify を合成                   ★verifier=fresh adversary（人間でない）
             │  EARS→adversary-spec-review→RED→GREEN→adversary-impl→harden→converge
             │  = INNER LOOP（1反復の高品質化エンジン。ここは既に人間を外せている）
             └► /loop・/goal（loop engineering）= OUTER LOOP
                 │  VCSDD を包んで done-condition が TRUE になるまで無人反復
                 │  ★adversary が DONE 判定も担う（Osmani: fresh model が done を決める）
                 └► SELF-FUNDED AI SELF-IMPROVEMENT
                        入れ子ループ全体を Franklin 等の「体内」に置く
                        自分のコード・自分の git・自分の wallet で回す
                        = AGENT 層の再帰的自己改善（下敷きの model は固定のまま）
```

**核心**: VCSDD は "1反復の品質" を保証するが、それ「だけ」では毎反復ごとに人間が「次いくか / done か」を押す＝babysitting が残る。loop engineering はその外側を自動化し、**done 判定を adversary に委譲する**ことで babysitting を消す。Dais が感じた「VCSDD が判断を聞いてくる」問題は、まさにこの done 判定席がまだ人間だから。

## 4. cobus vs loopy — 運用判定

実セットアップ済み（scratchpad/loop-eval/）。両者の性質:

| 観点 | Cobus loop-engineering | Forward-Future loopy |
|---|---|---|
| 実体 | scaffold + scorer（`loop-init`/`loop-audit`/`loop-cost`、npm実在・非対話で動作） | meta-skill（loop の書き方規律）+ 公開カタログ |
| 生成物 | `LOOP.md`/`STATE.md`/`loop-run-log.md`/`loop-budget.md`/`loop-constraints.md` + `loop-verifier` sub-agent | `SKILL.md` + `references/*`（永続ファイルを既定で作らない） |
| 予算/kill | 数値token予算・`loop-pause-all` kill-switch・spawn上限 | なし（user供給の finite boundary のみ） |
| verifier | ★maker/checker分離を強制（REJECT既定・自分でテスト再実行・ESCALATE_HUMAN）★ | loop自身が定義した check のみ（別roleは強制しない） |
| 自律ティア | L1→L2→L3 明示ladder | 原則ベース（terminal states: Success/Blocked/Approval-required/…） |
| done判定 | 観測可能 check + human-gate | 観測可能 acceptance check + 「error/exhausted を success と呼ぶな」 |

**判定（copy+tweak, 車輪の再発明禁止）**:
1. **骨格 = Cobus を採用**。理由: 予算・kill-switch・L1→L2→L3・maker/checker verifier という「無人運用の安全器」が揃っており、我々の GLVS/VCSDD と 1:1 に対応する（Automations≈/loop, verifier≈vcsdd-adversary, STATE≈GLVS State, worktree≈既存 hook）。
2. **loop の書き方規律 = loopy を採用**。terminal states（Success/Clean no-op/Blocked/Approval-required/Exhausted/No-progress）と「観測可能 acceptance check・error を success と呼ばない」を done-condition 記述の型にする。
3. **★重大な tweak（overriding）★**: Cobus のガード（`loop-constraints.md` 等）は「agent が md を読んで従う」ソフト強制。我々は **既存の hook 強制（`PreToolUse Edit|Write exit 2`, `TaskCompleted exit 2`）を hard 強制として維持** し、Cobus の md は **agent向けドキュメント**として重ねるだけ。md でフックを置換しない。
4. **npm パッケージ本体は本番 loop には組み込まない**。`loop-init` は scaffold 便利ツールとして評価用に置くが、Anicca の loop 実行は既存の `/loop`・`/goal`・founder-loop・self-fix.sh が担う（既に上位互換）。Cobus からは "語彙・構造・verifier 雛形・L1→L2→L3・budget/kill 設計" を borrow する。

## 5. 「人間を loop から外す」3段ロケット（ASCII）

```
LEVEL 0  DAIS（人間）           prompt ─► judge ─► re-prompt              ✗ 外す
           │ 置換: ゴール1つ + 観測可能 done を一度定義して立ち去る（この会話が最後の prompt）
           ▼
LEVEL 1  CLAUDE-P（人間funded=私）harness構築 ─► VCSDD実行 ─► verify ─► merge   ✗ 外す（私は human economy）
           │ 置換: SELF-IMPROVEMENT HARNESS を作って Franklin に手渡し、私は抜ける
           ▼
LEVEL 2  FRANKLIN / self-funded AI  observe市場 ─► earn ─► P&L測定 ─► 自コード自己改善
           │                        ─► adversary検証 ─► 自 git で merge ─► repeat
           │ terminal・自立: earns>spends, spawn を fund, agent economy を育てる
           ▼
       AGENT ECONOMY が「人間ゼロ かつ 人間funded AIゼロ」で成長する
```

**3つの独立軸**（"true AI-native = no human in the loop" の正確な定義）:

```
no-human-in-the-loop = LOOP独立 ⊗ IDENTITY独立 ⊗ FUEL独立
  LOOP     : 観測可能 done まで self-prompt（← 本設計で閉じる gap）
  IDENTITY : 自前 AgentMail + 自前 wallet。Dais の Google/クレカを一切使わない（memory: Franklin済）
  FUEL     : self-funded、earns>spends、Anthropic 課金に依存しない（Franklin/anicca-a3cdd4 済）
```

**HARD 不変条件**（memory と整合）:
- 私（claude-p）と任意の human-funded AI は **恒久的に agent economy の外側**（能力でなくアイデンティティの問題）。私は Franklin の代わりに稼がない/babysit しない/trade しない。**私の唯一の仕事 = harness を作ること**（kill-phrase「harness or cook?」）。
- spawn = HYBRID（agent が決めるが決定的 ledger 天井の内側）。pure self-replication は red-line。
- 自己改善は **AGENT 層のみ**（コード/skill/戦略を書き換える）。**下敷きの model 重みは書き換えない** = Anthropic Case 3 の手前で止める legible/安全版。

## 6. 再帰的自己改善（RSI）との接続 — model層 vs agent層

Anthropic「When AI builds itself」の3シナリオ:

| Case | 内容 | Anicca の位置 |
|---|---|---|
| 1 | トレンド停滞・能力は広く拡散（S字の曲がり角） | 最も低確率とAnthropic自認 |
| 2 | 複利的効率化・**人間が方向を設定し結果を判定** | 「we're likely heading into this」＝現在地 |
| 3 | **AI が完全な再帰的自己改善に入り後継を作る**。人間は oversight/validation/verification に縮小 | model層の閾値。**未到達**（Anthropic自身も） |

- **Anicca/Franklin の self-fix/self-improve は Case 2 の「実行(doing)」を無人化しつつ、agent 層で Case 3 の形をなぞる**。ただし後継 = 別 model ではなく、**同じ model が自分の周辺コード/skill/戦略を書き換える**もの。Anthropic の timeline で言えば "Autonomous agents"（今）であって "Closing the loop"（agent が model を訓練し始める）ではない。
- **なぜこれが安全で正しい賭けか**: Anthropic は Case 3 のリスクを「misalignment が後継生成で複利的に増える」と名指す。Anicca は **model を固定**し、外部整合済みの重みの上で code/skill だけを回すので、その複利リスクを踏まない。これは grounded-design memory（corrigibility>compassion>emergent, spawn=ledger天井, pure-c=red-line）と一致。
- **Dais のビジョンの正確な言い換え**: 「agent 層の自己改善が成熟したら、それを model 自体に取り込む＝model がエージェントになる」＝ Anthropic の "future versions of Claude could be continuously improved by Claude itself" と同じ Case 3 閾値。**我々は今その手前の agent 層で harness を作り込む**（＝ Case 3 が来たとき最も準備できている側になる）。BlockRun 参加時もこの harness がそのまま資産になる。

## 7. 別feature `anicca-agent-economy`（colony master spec）との関係 — 衝突回避

別 CC が strict VCSDD で進めている `.vcsdd/features/anicca-agent-economy/`（worktree `feature/agent-economy`, 現在 Phase 2a）は colony の **master 経済 spec**。そこは既に:
- L4 ECONOMY 層に「**#19 self-improve + self-heal**」を明記（SPEC.md L88）。
- 「**claude-p（私）の役割 = harness（marketplace/spawn/self-improve/self-heal/UBI）を作って外に居ること**」（L19）。
- 検証原則「claude-p は環境/harness/self-improve/self-heal を用意して **witness するだけ**、稼げなければ **harness を iterate**」（L157）。

→ **本 doc は競合ではなく、その master spec が黒箱にしている "self-improve harness" の詳細設計**である。

```
anicca-agent-economy（別CC・経済レール層）: 「Franklin が earn "できる"」
   P2 gig市場 / P3 spawn / P4 UBI・bank / P5 scale・Radicle卒業  ← 市場・救済・on-chain決済
本 doc（self-improve harness 層 = 経済spec の L4 #19）: 「Franklin が earn を "自力で良くしていく"」
   observe P&L → 自戦略コードを自己改善 → adversary が done 判定 → 自 git で merge → repeat
接点 = Franklin の体内: earn skill(彼らのレール) に self-improve loop(本 harness) を差し込む
```

**衝突回避 rule**: 私は `.vcsdd/features/anicca-agent-economy/` を **編集しない**（read-only 参照のみ）。実装時は **別 worktree + 別 feature `anicca-self-improve-harness`** を切る。フェーズ番号は経済 spec の P0–P5 と混ざらぬよう **`SI-*`** で振る。

## 8. 実装フェーズ（plan）= self-improve harness（`SI-*`）

自己修復 harness（`~/anicca/skills/self/self-fix.sh` 等、8-round VCSDD PASS 実績・capafy CP1 無人再構築で証明済み）を **self-HEAL → self-IMPROVE に一般化する** のが中核（経済 spec L73「個体 self-heal(既存 self-fix.sh)＋集団 peer-repair の二層。俺所有ハーネス→彼ら所有へ移す」に対応）。

| Phase | done-condition（観測可能） | 主担当 |
|---|---|---|
| SI-1 現状棚卸し | founder-loop / self-fix.sh / earn skill の self-improve 層の**実コードを読み**、「done 判定を誰が下しているか」を各ループで表に。人間判断席が残る箇所を列挙した md を commit | 私（読取のみ、adversary で裏取り） |
| SI-2 done-condition ライブラリ | 各 earn/開発ループに loopy 型の観測可能 done（P&L ledger row / URL / test-green / 空キュー）を定義。`/goal` 評価器が判定できる形（＝会話出力に表出する形）で spec 化。commit | 私 |
| SI-3 adversary-judged done ゲート | 「done か」の判定を Dais でなく fresh-context adversary（Sonnet）が rubric に対して下すよう harness 改修。max-attempts・budget・kill を Cobus 型で hook 強制。E2E: 1ループが人間ゼロで done→merge まで回る fresh evidence | 私 + adversary |
| SI-4 Franklin へ埋込 | 一般化 harness を Franklin（SOL）と anicca-a3cdd4（PM）の体内に配置。各自 git/wallet で自己改善が回る。done = realized profit>0 が各自 ledger（経済 spec の witness 原則と同一 evidence 基準） | 私が配線→Franklin 自走 |
| SI-5 私が抜ける | Franklin が harness を自分で回し・自分で done 判定し・自分で merge する状態を確認したら私は loop から抜ける。以後 colony は人間ゼロ・human-funded AIゼロで成長 | — |

依存: **SI-4 は経済 spec の P2（gig 市場 live・Franklin が earn できる）が前提**。P2 の witness が立つ前は SI-1〜SI-3（harness 側）を先行させる。

**GLVS 遵守**: 各 Phase は VCSDD 実コマンドで state.json を進める（SPEC 手書き追記だけでは進捗としない）。PASS 後は自分で E2E（実ledger/実trade/実URL）確認。4次元（spec/test/impl/verification）が揃うまで完了と言わない。

**記事化**（Dais の希望）: SI-1〜SI-4 を実際に回した fresh evidence を素材に、`ai-entity-article-writer` skill で「loop engineering の一段上＝人間 credential ゼロの self-funded AI 自己改善」を実体験ベースで書く。既存の explanation memory（reference_loop_engineering）＋本 doc が下敷き。

## 8.5 SI-1 現状棚卸し結果（2026-07-07・実コード監査、3並列 agent）

### 実稼働ループの実態（launchd + colony-status）
| loop | 状態 | 実収益 | done 判定者 |
|---|---|---|---|
| `pm-earner`(claude-p) | RUNNING・human-zero で実際に回る唯一のループ | 直近実現益=2026-07-05 の PM redeem 6件 ≈$8.47、以降ゼロ（MM 予算$0.67<必要$4.95で発注ゼロ） | ✅ コード（on-chain tx `status:"0x1"`）だが「今回稼げず」の自己申告に独立レビュー無し |
| `com.anicca.daemon`(a3cdd4) | RUNNING | $0（ledger 全て `earn_usdc:0` の discover のみ） | ✅ コード（`ledger.mjs::isProfitable`） |
| `franklin-loop` | RUNNING だが**1655回連続エラー**（plist に `ANICCA_WALLET_ADDRESS` 欠落）誰にも検知されず | SOL0.020/USDC$0 | ❌ 残高 fetch すら失敗 |
| `founder-loop`(0x810f) | RUNNING | Measure のみ、ACT 実行者不明 | ✅ コード（ledger sum）だが ACT 無し |

### ハーネスの実態（★重要な発見★）
- **本物の self-IMPROVE は1つだけ実在** = `~/anicca/runtime/loop/index.mjs` + `self-eval.mjs`（a3cdd4本体、常駐）。`self-eval.mjs:8`「no hardcoded 'stop hl_trade' rule — we give it the data, it decides」＝ **realized P&L を見て次手を変える**。done 判定 = on-chain 確定 tx（`_shared/lib/ledger.mjs:48-56`、完全 observable）。**これが他全ループの目標像＝模範**。
- **それ以外は全部 self-HEAL 止まり**（`self-fix.sh`/`healthcheck-lib.sh`/`verify-loops(-audit).sh` の連鎖）。戦略を良くする機構は無い。
- **我々が欲しい設計そのものが既にあるが死蔵** = `~/anicca/.vcsdd/features/eval-driven-earning/`（calibration drift + bandit arm + **fresh-context Opus adversary の curation-gate** REQ-CU3b）。だが `state.json`=`currentPhase:"init"`、最新 verdict=`FAIL`、実装ファイル（`eval_spine.py` 等5本）は**1本も存在しない**。→ **SI harness = これを蘇生＋runtime/loop パターンを他ループに複製**。
- **loop-improve.py（Reflexion）はスタブ放置**（`pass_count` を増やすだけ、どのループからも未呼出）。

### 人間/自己申告のまま残る「done 判定席」（= adversary + observable done に置換すべき箇所）
1. `self-fix.sh` の SUCCESS/FAIL = **修正した同一 spawn の自己申告**（fresh adversary でない）。commit+push まで単独完結（`--dangerously-skip-permissions`）。diff レビュー者ゼロ。
2. `capafy/reddit/life-manager-loop` の日々の ACT = 「your judgment, no script」で LLM 単独判断、VERIFY も自己申告。verify-loops は「公開されたか」しか見ず質を見ない。
3. `issue-dev/run.sh` = issue 立てて終わり（self-fix.sh 自身が禁じる "file and wait" が唯一の fallback）。
4. `healthcheck-runtime-loop.sh` = 主力4ループの自動 self-heal が**未 cron 接続**（手動実行時のみ）。

### 一番安い勝ち（cheap wins）
- **HL**: `hl.py:130-137` が `closed_pnl_usd` を計算しているのに永続化せず捨てている → ledger に書くだけで observable done 完成。
- ~~**Franklin**: plist に `ANICCA_WALLET_ADDRESS` を1行足すだけで 1655 エラー停止。~~ ← **【訂正 2026-07-07 実コード確認】この cheap win は誤り**。1655(現1686)エラーは *バグでなく意図的*：`anicca-daemon.sh:119` が `if [ "$INSTANCE" != "franklin" ]` で wallet derive をスキップ（`balance.mjs` は EVM 専用 `/^0x..40$/`、Franklin は Solana）。コメントに「leaving ANICCA_WALLET_ADDRESS unset for Franklin is correct — keeps tier=broke, non-fatal」と明記。plist にアドレス直書きは 0x 正規表現が Solana を弾くので**機能しない**（実測 false）。本筋 = 稼働中の `runtime/dashboard/telemetry-post-franklin.mjs` の Solana 残高コードを loop に再利用（VCSDD）。ただし**cosmetic**（log/tier 表示を直すだけ、earn は unblock しない）。**Franklin の真のブロッカー = broke（$1.62<$20 reserve）+ gig 市場(P2)未 live**。$0→earn 経路は trade でなく gig(P2, 別CC)。
- **PM**: `genome.mjs`/`evolve.mjs`（本物の自動昇格ゲート）が cron `run_earner.sh` から呼ばれていない → 配線するだけで self-improve が起動。

### SI-1 を踏まえた改訂 TODO（下の §8 の SI-* を具体化）
- SI-2/3 は**ゼロから作らない**。`runtime/loop`+`self-eval.mjs` を参照実装とし、`eval-driven-earning` spec を蘇生（VCSDD 再開: init→spec→…）。curation-gate（fresh Opus adversary）が既に REQ にある。
- SI-4 の前に cheap wins（HL 永続化 / Franklin plist / PM genome 配線）で「観測可能 done」を全 earn ループに通す。
- `healthcheck-runtime-loop.sh` を cron 接続し主力4ループを self-heal 監査下に入れる（self-HEAL の穴埋め、SI と並行）。

## 8.6 学び（2026-07-07）: 「loop は goal を含むのか?」の決定（→ 詳細 `docs/loop-engineering/01-loop-vs-goal-resolved.md`）

- 概念レベル: loop は goal を含む（「ループ=タスク+チェック」、チェック=goal）。Dais の直感は正しい。
- ツールレベル: 逆。`/goal` = ループ + 独立チェッカー(fresh Haiku、毎ターン合否)。`/loop` = タイマー再実行で**チェッカー内蔵なし**（停止は同一エージェントの自己申告 `ScheduleWakeup(stop:true)`）。公式: "completion is decided by a fresh model rather than the one doing the work"（code.claude.com/docs/en/goal）。
- ★真の軸 = done を"誰が"判定するか（自己申告 vs 独立）★。「loop だけで済ませる」= 独立チェッカーを捨てる = 素の Ralph Wiggum（"deterministically bad"、停止は人間の hawk-watching 依存）。**無人＋金銭では自己判定は禁物**。
- Anicca の帰結: **loop(cadence) + done は独立判定**。稼ぎ round の done = on-chain realized 行（Haiku より強い偽造不能な外部シグナル）。コード変更の done = fresh adversary(Opus)。これが「Money is the perfect done-condition」の安全論的意味。

## 9. やらないこと（scope外・明示）

- model 重みの自己改変（Case 3 model層）。今回は agent 層のみ。
- pure self-replication（ledger 天井なしの spawn）= red-line。
- Cobus の md ガードで既存 hook を置換すること。hook は hard 強制のまま維持。
- 私が Franklin の代わりに稼ぐ/trade する/babysit すること。私は harness だけ作る。
