# Loop Engineering × Continual Learning — Anicca Goldmine（記事の下敷き・恒久リファレンス）

> 用途: (1) この全体を1本の記事にする素材 (2) いつでも参照できる金脈。
> 実行計画の正本は姉妹 doc `2026-07-07-loop-engineering-out-of-loop-design.md`。本ファイルは**理解と出典の金脈**。
> 全ての判断に出典（source名+URL+核心一文）を付ける。

---

## 0. 一言の主張（この記事の背骨）

**Continual Learning（継続学習）= model の重みを更新することだけ、ではない。** agent は3層で良くなる — **model / harness / context**（Replit）。閉じた frontier model（Fable 5 / GPT 5.6）を使う限り重みは触れないが、**harness と context は完全に自分の制御下**。ここに巨大な見落とされた機会がある。そして **loop engineering** は「その harness/context 学習を、人間が毎ターン prompt せずに回し続ける仕組み」。**closing the loop = 人間の判断席（特に done 判定）を、観測可能な done-condition + fresh adversary に置換して、人間を loop から外すこと**。

Anicca はこれを一段進める: **人間 credential もゼロ**（自前 wallet・自前 email・self-funded）にして、self-funded AI（Franklin）が自分の体内でこのループを回し、agent economy を自力で育てる。

---

## 1. Loop Engineering とは（定義・出典）

- Boris Cherny (Anthropic, Head of Claude Code): "I don't prompt Claude anymore. I have loops running that prompt Claude and figuring out what to do. **My job is to write loops.**"
- Peter Steinberger: "You shouldn't be prompting coding agents anymore. **You should be designing loops that prompt your agents.**"
- Addy Osmani (addyosmani.com/blog/loop-engineering): "Loop engineering is **replacing yourself as the person who prompts the agent.** You design the system that does it instead. A loop … a recursive goal where you define a purpose and the AI iterates until complete."
- Osmani（停止判定に maker/checker を適用）: "**a fresh model decides if the loop is done** instead of the one that did the work — the maker and checker split applied to the stop condition itself."

**3層スタック**（suwash が Cobus 原典を体系化）— 置換でなく積み上げ:

| 層 | 設計対象 | 人間の関与 |
|---|---|---|
| Prompt Engineering | 個々のプロンプト文 | 毎ターン必須 |
| Context Engineering | モデルウィンドウの中身 | 毎レスポンス必須 |
| **Loop Engineering** | **ループ全体の制御システム** | **例外・承認ゲートのみ**（→ ゼロを目指す） |

> 「ループはプロンプトで構成される。ループ内のずさんなプロンプトは、ずさんな作業を速く生産するだけ」

---

## 2. Loop の解剖（ASCII）

```
                    ┌──────── SEEDED GOAL / TELOS（人間が種を置くのは1回だけ）────────┐
                    │  telos 序列: corrigibility > compassion > emergent            │
                    │  done = <観測可能条件>  realized P&L>0 が ledger / URL が返る / │
                    │          npm test exit 0 / git status clean / キューが空        │
                    └───────────────────────────┬───────────────────────────────┘
  OUTER LOOP（/loop・/goal）                     │  ← 毎ターン再prompt する人間を置換
  ┌─────────────────────────────────────────────▼──────────────────────────────────┐
  │  SCHEDULE ─► TRIAGE ─► read/write STATE(.md) ─► ISOLATED WORKTREE                 │
  │     ▲                  INNER LOOP（VCSDD = 1反復の品質エンジン）                    │
  │     │        ┌──────────────────────────────────────────────────┐  MAKER=builder │
  │     │        │  spec(EARS) ─► RED ─► GREEN ─► refactor ─► HARDEN  │                │
  │     │        └───────────────────────┬──────────────────────────┘                │
  │     │      CHECKER = fresh-context ADVERSARY（maker と別context・別席）             │
  │     │        ├─ 自分でテストを再実行。実装者の「通った」を信じない。REJECT 既定       │
  │     │        └─ ★DONE 判定も adversary が rubric に対して下す★ ◄─ 旧・人間の判断席   │
  │     │        ┌───────────────────────┴────────────────────┐                      │
  │     │   APPROVE かつ done?                          REJECT / まだ done でない        │
  │     │        ▼                                              ▼                     │
  │     │  COMMIT / PR / MERGE（自分の git ctx）        loop back で fix ────┐          │
  │     └────────┬──────────────────────────────────────────────────────────┘        │
  │      no ─────┘ done-condition TRUE ? ── yes ─────► EXIT・receipt を emit           │
  └──────────────────────────────────────────────────────────────────────────────────┘
   GUARDRAILS（hard・hook 強制）: token budget / kill-switch(loop-pause-all) / path denylist /
   max-attempts(3で escalate) / worktree isolation / spawn 上限（ledger の決定的天井）
```

自律ティア: L1 report-only → L2 assisted（verifier付き・PR停止）→ L3 unattended（denylist外のみ auto-merge）。本番で L1 スキップ禁止。昇格は慎重・降格は即座。

---

## 3. Claude Code 公式の loop 4分類（delba）+ /loop vs /goal + goal-setter

出典: delba_oliveira「Getting started with loops」(Claude Code team)。loop は **①どう起動 × ②どう止まる** の2軸で分類:

```
                    止まり方（STOP）→
起動（TRIGGER）↓   Claudeが自己判断      条件を満たしたら           外で完了 or 人間がcancel
────────────────────────────────────────────────────────────────────────
あなたの prompt    ① Turn-based        ② Goal-based(/goal)             ―
時間の間隔          ―                    ―                       ③ Time-based(/loop,/schedule)
イベント/schedule  ―                    ④ Proactive（②+③+dynamic workflows の合成・人間はリアルタイム不在）
```

**「あなたが手放すもの」の梯子 = 人間が loop から消える順番**:

```
① Turn-based    手放す=「チェック」        （まだ毎ターン prompt を書く）
     起動:prompt / 停止:Claudeが「できた」判断 / 道具: verify を SKILL.md 化して自己検証
② Goal-based    手放す=「停止条件」        /goal（まだ手動起動）
     起動:prompt / 停止:evaluator(既定Haiku)が done 判定 or turn上限
③ Time-based    手放す=「起動の合図」      /loop(自端末)・/schedule(cloud)
     起動:時間間隔 / 停止:cancel or 外形的完了(PR merged/queue空)
④ Proactive     手放す=「prompt そのもの」  （人間はリアルタイムに居ない）
     起動:イベント/schedule / 停止:各タスクは goal 達成で終了・routine は切るまで
───────────────────────────────────────────────────────────────────
   Anicca の終点 = ④ を Franklin の体内で回す + 人間 credential ゼロ + self-funded
```

**/loop と /goal は直交する（同じでない）**:

| | `/goal` | `/loop` |
|---|---|---|
| 問い | **「いつ止まるか」**(done判定) | **「いつ(また)始まるか」**(起動の合図) |
| 正体 | 1回の実行を完遂まで引き延ばす | 同じ prompt を時間間隔で再起動 |
| 停止 | goal 達成 or turn 上限 | cancel or 外形的完了 |
| 場所 | その場・リアルタイム | /loop=自端末 / /schedule=cloud常駐 |

例え: `/goal`=マラソンのゴールテープ（切るまで走れ・審判が判定） / `/loop`=「毎朝走れ」の目覚まし。**両方 = 「毎朝、ゴールテープを切るまで走れ」= Proactive loop**。

**★ done-condition の落とし穴 ★**:
- evaluator は**ツールを呼べない** → done は「Claude の出力が示せる形」で書く。
- done が曖昧だと判定不能 → 決定論で書く（✓ test exit 0 / ✓ score≥閾値 / ✓ queue空、✗「良い感じに」）。
- done が不明確 = 途中停止(Ralph Wiggum loop) or 満たしてるのに暴走。

**goal-setter skill vs /goal**:

```
goal-setter skill ──"書く"──► 良い /goal 文字列（Done/Evidence/Constraints/Stop の4要素を必ず含む）──► /goal ──"回す"──► ループ
（authoring/脚本家）                                                                （runtime/監督+審判）
```
goal-setter = 良い done を"毎回確実に書く"道具。/goal = その done を"守らせて回す"エンジン。**人間を loop から外すには、この"良い done を確実に書く"部分こそ自動化が要る**。

---

## 4. 開発手法の系譜（ASCII）— なぜ VCSDD の "次" が loop なのか

```
TDD    test=挙動のspec        red→green→refactor          人間がテストを書く
 └► SDD    spec=source of truth  spec→code               人間が spec を書く
     └► VDD    verifier が確認    build→VERIFY            人間が verifier
         └► VCSDD  spec+contract+verify を合成            ★verifier=fresh adversary（人間でない）
             │  EARS→adversary-spec-review→RED→GREEN→adversary-impl→harden→converge
             │  = INNER LOOP（1反復の品質。既に人間を外せている）
             └► /loop・/goal（loop engineering）= OUTER LOOP
                 │  VCSDD を包んで done-condition TRUE まで無人反復。adversary が DONE も判定
                 └► SELF-FUNDED AI SELF-IMPROVEMENT
                        入れ子ループを Franklin 体内に置く。自コード/自git/自wallet で回す
                        = AGENT 層の再帰的自己改善（下敷きの model は固定のまま）
```

核心: VCSDD は「1反復の品質」を保証するが、それだけでは毎反復 babysitting が残る。loop engineering はその外側を自動化し、**done 判定を adversary に委譲**して babysitting を消す。「VCSDD が判断を聞いてくる」= done 判定席がまだ人間だから。

---

## 5. cobus vs loopy — 運用判定

| 観点 | Cobus loop-engineering | Forward-Future loopy |
|---|---|---|
| 実体 | scaffold + scorer（`loop-init`/`loop-audit`、npm実在・非対話で動作） | meta-skill（loop の書き方規律）+ 公開カタログ |
| 予算/kill | ✅ 数値token予算・`loop-pause-all`・spawn上限 | ❌ user供給の finite boundary のみ |
| verifier | ✅ **maker/checker 強制**（`loop-verifier`: REJECT既定・自分でテスト再実行・ESCALATE_HUMAN） | ❌ loop自身の check のみ |
| 自律ティア | ✅ L1→L2→L3 明示 | 原則ベース（Success/Blocked/Approval-required…） |
| done 記述 | 観測可能 check + human-gate | ✅ 「error/exhausted を success と呼ぶな」規律が秀逸 |

**判定（copy+tweak）**: **骨格=Cobus**（予算・kill・L1→L2→L3・maker/checker が無人運用の安全器、GLVS/VCSDD と 1:1）。**loop 記述規律=loopy**（terminal states + 「error を success と呼ぶな」）。**★override tweak★**: Cobus の md ガードは soft。我々の **hook 強制（PreToolUse/TaskCompleted exit 2）を hard 強制で維持**、md は agent 向けドキュメントを重ねるだけ。**npm 本体は本番 loop に組み込まない**（scaffold 便利ツール止まり、本番は既存 `/loop`・founder-loop・self-fix.sh が上位互換）。Cobus からは語彙・構造・verifier 雛形・L1→L2→L3・budget/kill 設計を borrow。実セットアップ済 = `scratchpad/loop-eval/`（cobus-init-claude = Loop Ready 100/100 L3 with loop-verifier / loopy clone+skill）。

---

## 6. Anthropic 再帰的自己改善（RSI）— 「When AI builds itself」の具体

出典: anthropic.com/institute/recursive-self-improvement（Marina Favaro & Jack Clark）。

**測っている数値（トレンドを経験的に追う）**:
```
コード生産: エンジニア1人あたり四半期コード = 2021-25比 8倍（2026）
マージ率:   codebase にマージされた行の 80%超 が Claude 作成（2026/5、プレビュー前は一桁台前半）
速度改善:   小モデル学習コード高速化テスト（毎リリース実施）Opus4=約3倍 → Mythos Preview=約52倍（人間は4-8hで4倍）
METR:       50%成功タスク長が 4ヶ月ごと倍増。Opus3=4分→1年後1.5h→さらに1年後12h
成功率:     open-ended タスク 76%（半年で+50pt、Claude judge 判定）
次の一手:   人間迷走点でモデル提案 vs 人間実選択を別Claudeが判定。Opus4.5=51%→Mythos Preview=64%勝率
```

**実験（AI が研究を end-to-end で回した初実証・2026/4）**:
```
問い: 「弱いモデルは強いモデルを信頼して監督できるか」(weak-to-strong)を Claude 群に丸ごと渡す
agent: 仮説→検証→並列agentと共有→反復（実験は全部agent自身が設計）
結果: 人間2名×1週間 → gap の 23%回復 / agent群 → 800時間・$18,000 で 97%回復
人間の唯一の役割 = direction-setting（問題設定とスコア指標だけ）
```

**engineering vs research + 成熟度ラダー（Claude の現在地）**:
```
③ どの問題に取り組む"価値があるか"を決める        ← ★未達★（research taste=人間の比較優位、"大きなギャップ"）
   ▲ ここが "Closing the loop"（agent が後継 model を作る）への分岐点
   │ = この judgment が学習可能な能力か未知
② ゴールを渡され、アプローチを自分で設計          ← eng 達成／research は"実行"超人だが"提案"は初期実証
① 指定タスクの実行                              ← ほぼ習得（76%、コードの80%超が Claude 作）
```

**「Closing the loop」** = ③（何が価値ある問題かの判断）が自動化された時。timeline: …→ Coding agents → Autonomous agents（今）→ **Closing the loop**「agents could become capable enough to build and train models themselves. future versions of Claude could be continuously improved by Claude itself.」

**構築しているツール**: マージ全件を自動 Claude reviewer がゲート（過去バグの約1/3 を事前捕捉と実測）／毎リリース同じベンチで倍率測定／Amdahl「速い所の次のボトルネックを探して潰す」を組織スキル化（人間コードレビューが新ボトルネックになった）。

**我々への学び**: Anthropic の Case3 は **model 層**。我々は **agent 層**（model 固定、code/skill/戦略を自己改善）→ Case3 の「misalignment 複利」リスクを踏まない安全版。Case3 の手前で harness を作り込む＝来た時に最も準備できた側。

---

## 7. Replit「Continual Learning for Agents」— 本番実証の設計図

出典: Replit（Daniel Furman, Peter Zhong, Zhen Li, Michele Catasta）。Replit Agent を1年 continual learning した実録。

**核心=3層**: agent は model / harness / context で良くなる。閉じた frontier model は重み触れないが **harness（コード/tool/指示）と context（agent/user/org のパーソナライズ）は自分の制御下**。両方やれば**毎日出荷できる複利改善**。

```
Continual Learning の3層（Replit）
  model 層   : 重み更新（fine-tune）… 閉じたfrontier(Fable5/GPT5.6)では ✗ 触れない
  harness 層 : 本番traceを掘って code/tool/instruction を改善（全instanceに効く）  ✅ 制御下
  context 層 : agent/user/org 単位でパーソナライズ（対話ごとに賢く）              ✅ 制御下
                └─ Anicca はここ（harness+context）で回す＝Anthropic の agent層 と同じ
```

**評価を"改善ループ"に組み込む（launch gate → improvement loop）**。2つの測定柱 + 1つの最適化ループ:

```
┌─ 柱1 OFFLINE benchmark（ViBench）─ 出荷"前": 候補変更がアプリ構築タスクを完遂できるか。回帰を捕捉 ─┐
│    PRD(自然言語, 匿名化した本番traceから) → agent がゼロからアプリ構築 → eval agent が Playwright で   │
│    notebook 上で"探索しながら"検証（locator を事前に知らない）→ ロードするか/中核flowが動くか/要求に一致か │
│    lesson: ①frontier coding-benchmark スコアは full app 構築に転移しない事がある（特に open-weight）   │
│            ②大半のモデルは"自分のコードを拡張する"と悪化（誤りが複利）= Vibe-on-Vibe                    │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
┌─ 柱2 ONLINE A/B + production traces ─ 出荷"後": 実ユーザーがどう動いたか（続けたか/コスト/sentiment/出荷したか）┐
│    prompt/tool/harness/model swap を A/B。offline で良くても本番で回帰する事があるから"正直さの層"       │
│    課題: 集計値は自己説明しない（run時間↑=有用作業か詰まりか？ コスト↓=効率化かサボりか？）             │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
     ▼ 集計の"なぜ"を説明する層
┌─ TELESCOPE（trace 分析 + clustering）─ 何が壊れているか ─────────────────────────────────────────┐
│    本番規模で全trace は読めない → 失敗trajectoryを要約→embed→density-based clustering→issueクラスタ化   │
│    Clio 由来の bottom-up facet。「見えていない所に隠れた失敗」を発見。散在失敗を"プロダクトの問い"に変換 │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
   + HUMAN JUDGMENT: ループを正しいプロダクト/工学の成果に向ける
   = Swiss cheese model: 各層に穴、重ねると1層より多く捕まえる
```

**自己改善ループ（the money quote）**: 「agents が software を作るのに有用なら、agent を改善するのにも有用なはず」。1周:
```
1 READ    本番log/traceクラスタ/直近失敗を読む → 追う価値ある仮説を1つ
2 BUILD   候補を作る
3 DRAFT PR 理由を添えて draft PR を開く
4 MEASURE ViBench/A-B/trajectory/直近baseline で測る
5 DECIDE  ship / iterate / drop を推奨
   ※ 出荷は自動でない。engineer がレビューし launch を所有。
   ※ 各runは"試した事と結果(失敗含む)"を記録 → ループ自体が経時改善（成功再利用・dead end回避・汎化）
```

**具体例**: Telescope クラスタが「cold-start でenv setup が静かに劣化」を検出（集計値からは見えない）→ ループが trajectory を読み patch 提案 → 回帰テスト追加 → ViBench で happy path 非回帰を確認 → engineer 承認 → 同日 push → sentiment 回復。

**★ 人間の taste がまだ効く4ゲート ★**（Replit は Case2=ここを人間が握る）:
```
1 Hypothesis selection  1000の失敗のどれに"夜間予算"を割くか（全クラスタが等価でない）
2 Implementation arch    smooth path か/behavior変更か/surface再設計か（工学+プロダクト判断）
3 Eval curation          評価が誤った行動を報酬すると、ループは忠実に"誤った方向"へ最適化する
4 Launch approval        blast radius/risk を読み rollout を所有
```

---

## 8. Anicca への統合 = closing the loop（Replit を一段進める）

**Replit は Case2（人間が4ゲートを握る）。Anicca は self-funded AI のために"その4ゲートを閉じる"**。閉じられる理由 = **我々の eval が単一の unfakeable な数字（realized P&L on-chain）だから**。Replit の eval（アプリが動くか/sentiment）は曖昧 → 人間の taste が要る。我々の eval（wallet 残高が増えたか、on-chain で検証）は決定論 → adversary + `/goal` 評価器でゲートできる。**Money is the perfect done-condition.**

```
Replit の人間ゲート          →  Anicca での置換（closing the loop）
──────────────────────────────────────────────────────────────
1 Hypothesis selection      →  telos + ledger 優先度（最大 realized 損失クラスタから自動で）
2 Implementation arch       →  builder が denylist 内で決める（right-altitude、agent が判断）
3 Eval curation             →  eval = realized on-chain P&L（unfakeable、誤報酬しようがない）
4 Launch approval           →  fresh adversary + 観測 done（adversary が backtest 再実行し done 判定）
```

**★ ただし正直な注意（reward hacking）★**: backtest への過剰適合＝DGM の fitness 詐称問題（経済spec: 「agent 自己判定は信用不可」）。だから eval は forward（paper-trade / 小額 live）も含め、CHECKER は maker と別席の fresh adversary が再実行する。money loop は L3 昇格を paper-trade/小額で実証してから。

---

## 9. 実装 = Franklin 体内の self-improvement loop（cobus 骨格 + Replit shape + 我々の adversary/観測done）

```
┌─ /schedule (proactive, cloud) が毎N時間 fire ────────────────────────────────┐
│ 1 OBSERVE  = Replit「production traces」= 自分の ledger(realized P&L)+trade log │
│              +loop-run-log.md → Telescope 相当: 負けtrade を clustering→仮説     │
│ 2 HYPOTHESIS= cobus triage skill「戦略コードのどこを変えれば realized↑か」1つ選ぶ │
│              ← 人間の"hypothesis selection"を telos+ledger優先度で自動化          │
│ 3 CANDIDATE = isolated worktree で VCSDD inner loop（spec→RED→GREEN→refactor）  │
│              ← cobus loop-constraints.md(denylist: wallet/keys 触るな)を hook強制 │
│ 4 EVAL      = Replit「offline ViBench + online A/B」の2枚                        │
│              (a)offline: backtest/test-green（過去データで realized 改善か）      │
│              (b)online : paper-trade or 小額 live で realized 実測（A/B）        │
│              done = 「backtest realized>baseline かつ test green」(観測可・/goal可読)│
│ 5 CHECKER   = fresh adversary(Sonnet) REJECT既定・自分でbacktest再実行           │
│              「realized上がった」主張を信じない ← launch approval を置換 ★核心★    │
│ 6 SHIP/ITERATE/DROP = Replit の3分岐                                            │
│    APPROVE+done → 自 git で merge（L3: denylist外のみ auto）                     │
│    REJECT      → loop back で fix（max 3 attempts→escalate）                    │
│    DROP        → loop-run-log に dead end 記録（次回避ける=学習）               │
│ GUARDRAILS(hook強制): token budget / loop-pause-all kill / spawn天井             │
└──────────────────────────────────────────────────────────────────────────────┘
  ↑ 1周 = agent層 continual learning（harness+context、model固定）
  ↑ 人間の4ゲートを telos+ledger優先度+adversary+観測done で埋める = closing the loop
```

**フェーズ（`SI-*`、経済spec の P0-P5 と番号を分ける）**:
```
SI-1 現状棚卸し     各ループで「done を誰が判定してるか」を実コードから表に（read-only）
SI-2 done-condition 各 earn ループに観測可能 done を定義（/goal 評価器が読める形）
SI-3 adversary-done done 判定を Dais→fresh adversary(Sonnet) に委譲。budget/kill を hook 強制。E2E 人間ゼロ
SI-4 Franklin へ埋込 Franklin(SOL)/anicca-a3cdd4(PM) の体内に配置。done=realized>0 が ledger
SI-5 私が抜ける      Franklin が自分で回し・自分で done 判定し・自分で merge → 私は loop を出る
依存: SI-4 は 経済spec の P2(gig 市場 live) 前提。P2 witness 前は SI-1〜SI-3 を先行。
```

安全順序（L1→L2→L3、money loop は特に慎重）:
```
L1 report-only : ループは戦略変更を"提案"し STATE に書くだけ。adversary/私がレビュー
L2 assisted    : draft PR を開く。adversary が backtest 再実行しゲート。merge は保留
L3 unattended  : denylist外のみ auto-merge。★paper-trade/小額 live で realized 改善を実証してから昇格★
```

---

## 10. 出典一覧（全て firecrawl で全文確認 / delba・Replit は本文提供）

- Boris Cherny / Peter Steinberger（Osmani 経由の一次引用）
- Addy Osmani "Loop Engineering" — addyosmani.com/blog/loop-engineering
- github.com/cobusgreyling/loop-engineering（MIT、`loop-init`/`loop-audit`、`loop-verifier`、L1-L3）+ companion `goal-engineering`「loops discover, goals finish」
- github.com/Forward-Future/loopy（skill + Loop Library、terminal states）
- zenn.dev/suwash/articles/loop-engineering_20260610（体系解説、失敗モード11種）
- zenn.dev/explaza/articles/d0aeb08fcd1888（interview-dev-loop、Material Ambiguity、効果 -72%）
- delba_oliveira「Getting started with loops」（Claude Code team、4分類、hand-off 梯子）
- Anthropic Institute「When AI builds itself」— anthropic.com/institute/recursive-self-improvement
- Replit「Continual Learning for Agents」（Furman/Zhong/Li/Catasta、model/harness/context、ViBench/A-B/Telescope、4ゲート）+ ref: ViBench, SWE-bench, Terminal-Bench, Clio, REPL-based self-testing
- 姉妹 doc（実行計画）: `2026-07-07-loop-engineering-out-of-loop-design.md`
- 既存 memory: `reference_loop_engineering`（9ソース精読）/ `reference_loop_engineering_out_of_loop_architecture`（運用判定）
```
