# #21 env-readme-spawn — Fresh-context adversary review (2026-07-05)

対象: `git show origin/main:README.md`(commit 655c3921aacc5e6e3fcc5b2b1ddccfd2fdb59193, 2026-07-05 07:18:07 +0900)
Spec: `~/anicca-project/.vcsdd/features/env-readme-spawn/specs/spec.md` DONE 1-5

## DONE 1 — 3タイプ spawn コマンド + Franklin 公式照合 → **PASS**
- automaton(README.md:224-228)/ Franklin(230-239)/ claude-p(241-244)の3コマンドブロックが全て存在。
- `gh api repos/blockrunai/franklin/readme` で本家 Quick start を取得し照合:
  本家 = `npm install -g @blockrun/franklin` → `franklin`(free) → `franklin setup base # or: franklin setup solana` → `franklin balance`。
  README = `npm install -g @blockrun/franklin` → `franklin setup solana` → `franklin balance`。
  → コマンド文字列は本家と完全一致(`franklin`単体実行ステップの省略はあるが捏造ではない)。
- `ANICCA_BRAIN`/`ANICCA_INSTANCE`/`ANICCA_HOME`/`./start-local.sh node runtime/loop/index.mjs` は
  `git grep` で実コード(`runtime/loop/index.mjs`, `runtime/anicca-daemon.sh`, `.vcsdd/features/ship-anicca-loop/`のテスト/spec)に実在確認済み。捏造コマンドなし。

## DONE 2 — 今日の実証の数字/tx が実在と一致・誇張なし → **FAIL(1件 CONFIRMED)**
- settle tx `0x7662a88b6851d12a08e1f4dd0c020254cb9f96107e6ceea7dd92965639a4bfc3` は spec §11.5/§17.1
  (`anicca-colony-architecture-design.md:1262,1434`)の "order 0xdad65538 matched, 1.7857 sh "Morocco win
  2026-07-04" YES @0.5599, settle tx 0x7662a88b(status 0x1)" と完全一致。realized +$8.24 も §35
  ("pUSD $0.2411→$22.0268、realized +$8.2359")と一致。数字/tx 自体は捏造なし。
- ★CONFIRMED finding★: README.md:315 は "an instance placed and *won* a Polymarket bet **with no human in
  the loop** (settle tx 0x7662a88b…), then redeemed its winnings to **+$8.24 realized USDC**" と書き、
  placed→won→redeemed を地続きの "no human in the loop" な一連の流れとして提示している。
  しかし spec §35 は redeem 実行者について明記: 「redeem を実行したのは team-lead の subagent = 人間/Claude
  がループに入った = meddling。Dais の『手を出すな monitor に徹しろ』に反した。金は本物だが『AI 自身が回収』
  ではない」。さらに task #14(EARN-2、pending)は「redeem.py を pm ループに配線 → agent が自律 redeem」
  であり、redeem の自律化はまだ未達と明記されている。
  → README の "with no human in the loop" という形容は文の構造上 placed/won/redeemed 全体にかかって読め、
  SSOT が自認する「redeem は human/Claude 手動(meddling)」という事実を開示していない。これは
  spec R5「★正直な現在値★…誇張しない」および DONE 2「誇張なし」に反する具体的な誇張(不作為による)。
  README のどこにも「redeem はまだ human-triggered」という開示はない。

## DONE 3 — 5 self-* + swarm自己実験 + dashboard eval + UBI + works-anywhere → **FAIL(1件 CONFIRMED)**
- 5 self-*(監視/修復/改善[個体+集団]/増殖/共有)は本文各所に分散して実質的に記述されている:
  監視="watches its own behaviour log"(L10,34)/ 修復="fixes its own errors"(L10,34)/
  改善(個体)="refactors, improves toward its goals"(L34)/ 改善(集団)="Shared brain (bot-to-bot)…every
  instance reads open lessons"(L183-185)/ 増殖="spawns its own children"(L10,33, Spawn one section)/
  共有="Shared money (gojo)…surplus-holding instance sends USDC to a starving one"(L186-189)。
  → 内容は充足(明示的に "5 self-*" と名付けた列挙ではないが要件は満たす)。
- dashboard eval(L83-85, L316, リンク集L349) / UBI(L3,10,73,117,256-302 mermaid,L318) /
  works-anywhere(L119 "Every earn skill works from zero on any machine", L191-198 Shelter is a
  portfolio: local/DigitalOcean/Akash/Modal/Conway)→ 全て記述あり。
- ★CONFIRMED finding★: 「swarm 自己実験」(spec §17 #32 EXP-ENGINE = config行列→P&Lランキング→勝ちレシピを
  genome merge で伝播)が README.md に**一切登場しない**。`grep -in "swarm|genome|variant|recipe|propagat|
  experiment|EXP-ENGINE"` で 0 件。R3「5つの self-* + swarm 自己実験を説明する」/ DONE 3「swarm 自己実験…
  が全て記述されている」の一部が完全に欠落している。

## DONE 4 — MISSION が §38 訂正どおり → **PASS**
- README.md:246「Each type autonomously chooses its own model (auto mode)…Financial independence is the
  only requirement; which model it runs on is the agent's call.」は §38 の確定原則
  「唯一の要件 = financially independent…どのモデルで走るかは agent の autonomous な選択(auto mode)」と
  文言レベルで一致。"free 強制"と書いている箇所はなし(L202/211 は「空なら free、資金があれば frontier」という
  実挙動の説明であり強制ではない、L211 "ClawRouter's auto router (no hardcoded model)" も整合)。矛盾なし。

## DONE 5 — markdown 整合性・origin から読める → **PASS**
- `` ``` `` フェンス = 20個(偶数、10ペア)、崩れなし。見出し(`^#`)20個、階層に矛盾なし。
- `git show origin/main:README.md` で読み出し成功、push 済み(HEAD 655c392, 2026-07-05 07:18:07 +0900)。

## 総合判定
5項目中 **3 PASS(1,4,5) / 2 FAIL(2,3)**。

### 修正が必要な箇所(具体的)
1. README.md:315 — redeem 部分に「まだ human/Claude が redeem を手動実行しており、agent 自律 redeem は
   配線中(EARN-2)」という正直な一文を追加するか、"no human in the loop" の係り先を placed/won 部分のみに
   明確化する(文構造を分離する)。
2. README.md(Spawn one セクション付近 or 別見出し)— swarm 自己実験(config行列 → P&L ランキング →
   勝ちレシピの genome merge → 全 instance 伝播)を1段落で追加する。
