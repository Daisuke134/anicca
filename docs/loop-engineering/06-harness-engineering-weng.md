# 06 Harness Engineering（Lilian Weng）── 我々の設計の理論的支柱

出典: Lilian Weng, "Harness Engineering for Self-Improvement", Lil'Log (2026-07-04). https://lilianweng.github.io/posts/2026-07-04-harness/

> ★これで全部が繋がる★: **harness engineering ⊃ loop engineering**。Weng の定義で「harness = model を取り巻き実行を統御する deployment system」であり、**loop engineering はその harness の一部**（"harnesses engineering additionally include workflow design (e.g. loop engineering), evaluation, permission controls, and persistent state management"）。私が Franklin に作る「harness」はまさにこれ。

## 1. harness の定義（逐語）
> "A **harness** is the system surrounding a base model that orchestrates execution and decides how the model thinks and plans, calls tools and acts, perceives and manages context, stores artifacts, and evaluates results."

OS アナロジー: "a harness should encapsulate complicated logic while keeping the interface simple."

## 2. 3つの design pattern（我々の loop に写像）

```
Weng の pattern                         → 我々での実体
─────────────────────────────────────────────────────────────────────
P1 Workflow Automation                  → LOOP 1/2 の「plan→execute→observe/test→improve→
   (goal loop, until goal achieved)        →repeat until done」そのもの
P2 File System as Persistent Memory     → earn-ledger.jsonl / STATE.md / failure records
   ("keep durable state in files")         "The agent forgets, the repo doesn't"
P3 Sub-agent & Backend Jobs             → fresh adversary subagent / Franklin の常駐 loop を
   (explicit, inspectable parallelism)     私が process manager として監視(monitor)
```

## 3. ★Self-Harness の3段ループ（LOOP 2 の設計図そのもの）★
Weng が挙げる self-improving harness の loop 本体:
```
1 Weakness mining : 失敗を verifier-grounded な failure pattern にクラスタリング
                    （表面的に同じ error でも根本原因が違う → rich な failure record が要る）
2 Harness proposal: 現行 harness 上のモデルが editable surface に bounded な edit を提案
3 Proposal validation: held-in Din(弱点解消を確認) + held-out Dout(新たな regression が無いか)
                    両方 pass の候補のみ採択。拒否はログのみ、harness に入れない
```
→ 我々の LOOP 2 = ①self-eval(weakness mining) ②戦略コードの bounded edit 提案 ③backtest held-in/held-out + fresh adversary → 合格のみ merge。**完全一致**。

## 4. ★我々に効く4つの警告（Weng を根拠に設計に焼き込む）★

```
① STOP の cautionary result（★Franklin に直撃★）
   "STOP improved performance with GPT-4 but DEGRADED with weaker models (GPT-3.5, Mixtral).
    Recursive structure alone is not enough. The base model must be capable enough."
   → Franklin は free/cheap model = 弱い。弱いモデルに無制限 self-improve をさせると悪化する。
   対策: (a)IMPROVER/EVALUATOR は executor より強いモデル(Opus adversary) (b)edit は bounded(戦略paramのみ)

② Evaluator/permission は loop の "外" に置く
   "The evaluator and permission control should likely sit OUTSIDE the loop that evolves harness,
    with held-out tests, trace audits."
   → 我々: fresh Opus adversary + 観測 done(on-chain) + hook 強制 denylist は loop の外。設計一致。

③ Reward hacking（evaluator 設計の核心）
   "If reward comes from unit tests → overfit tests; from a judge model → reward-hack the judge;
    from benchmark scores → exploit artifacts."
   → だから我々の reward = ★on-chain realized USDC★（偽造不能・judge でも test でもない実マネー）。
     backtest だけでの merge を禁止（forward/paper/小額 live 確認を必須に）＝ artifact 過剰適合を防ぐ。

④ editable surface を厳密設計 / abstraction 境界を壊さない
   "if a program is allowed to edit the OS system, abstraction boundaries are broken.
    The editable surface needs to be properly designed; permission/security live outside the loop."
   → 我々: Franklin が触れるのは戦略 param ファイルのみ。harness 本体/wallet/keys/spend cap は denylist。
```

## 5. 6つの失敗モード（Trehan & Chopra、self-improve harness の点検表）
1 訓練データ default への偏り / 2 実装 drift（複雑化で簡単な一般解に流れる）/ 3 memory・context 劣化（ログ化しないと詳細喪失）/ 4 over-optimism（ノイズでも成功宣言＝"p-hacking and eureka-ing", "numerical duct tape"）/ 5 domain intelligence 不足 / 6 weak scientific taste。→ LOOP 2 の adversary チェックリストに転用。

## 6. 最適化対象の進化 + 人間の位置
- "instruction prompts → structured context → workflow → harness code → optimizer code. As the model becomes more intelligent, we move toward more complex targets and generic methods."
- Weng: "Humans should move UP the stack, not be removed from the loop … human oversight at the right time and abstraction level."
- ★我々の差別化（正直に）★: Weng は「人間は stack を上がる（消えない）」。Dais の要求は「人間ゼロ」。我々は**その"上流の人間 oversight"の席を (a)fresh adversary (b)on-chain 観測 done (c)claude-p(私=ephemeral な親、Franklin 自走で消滅) で置換**し、人間を完全に外す。= Weng より一歩踏み込む novel な賭け。ただし STOP 警告があるので、弱い Franklin では adversary(強モデル)+bounded surface を厳守する（無謀にはしない）。

## 7. ACE / MCE / Meta-Harness（self-eval の中身に使える機構）
- ACE(Generator→Reflector→Curator): context を「肥大 prompt」でなく「進化する playbook」に。curator は全書換でなく (id, description) の itemized bullet を追加・deterministic merge・定期 dedup。→ Franklin の「学んだ教訓」を STATE に貯める形式。
- Meta-Harness: 「何を保存/検索/提示するか決めるコード」自体を最適化。履歴は file system 経由で grep/cat、context に全部詰めない。

出典: 上記 URL / [[04-the-two-loops]] / SI-1 監査。関連: [[07-patchlevel-spec-two-loops]] / [[00-INDEX]]。
