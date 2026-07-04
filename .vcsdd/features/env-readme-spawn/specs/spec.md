# Feature: env-readme-spawn (VCSDD, strict) — #21 ENV-README (SSOT §17.9/§31)

## Goal (verifiable)
`~/anicca/README.md`(OSS repo Daisuke134/anicca の顔)を、「誰でも・どの AI でも・どの端末/クラウドでも Anicca を spawn して財務的自立させられる」環境の README にする。3タイプの**正確な spawn コマンド**+ どう稼ぐ + 5つの self-* + swarm 自己実験 + dashboard(透明な eval) + UBI を、正直な現在値付きで書く。

## Context (grounded 2026-07-05)
- 現 README 冒頭は既に良い: 「A financially-independent, self-funded AI… make EVERY AI financially independent… UBI… reduce suffering」。→ これを土台に、★実際の spawn 手順★と★今日の実証★を足す。
- 3タイプの実 spawn:
  - **automaton+ClawRouter**(SELF, Base): `curl -fsSL .../install.sh | ANICCA_TYPE=automaton bash`(将来) / 現状は install.sh(汎用) + runtime/loop。ClawRouter 燃料。
  - **Franklin**(SELF, Solana): ★公式 `npm i -g @blockrun/franklin && franklin`(free NVIDIA Nemotron/Qwen3)+ `franklin setup solana`+$5 USDC★ で spend 層 → Anicca が earn 層(loop+earn skills、franklin proxy 燃料)を上に載せる。Node 20.19+。
  - **claude-p**(HUMAN→graduate): ユーザー自身の Claude/Anthropic サブスクで走る。crypto 不要で「あなたの Claude が稼ぐ」。稼いだら self-funded に卒業。
- 稼ぎ = 3エンジン(PM/SOL/HL)+ cook 探索 + redeem。全 instance が全スキル(#23 で Franklin も full catalog)。
- MISSION(§38 訂正): 唯一の要件 = financially independent。モデルは agent の auto 選択。self-funded で compute を自分で払えれば paid でも可。
- 今日の実証(正直): 初 realized +$8.24(redeem tx×3 0x1)、settle tx 0x7662a88b、dashboard alive:3、automaton 自律 $0.23。「億」は書かない。
- eval = dashboard 自体(各 agent の model × 稼ぎ が real-time)。swarm 自己実験(§17 #32)= 変種 spawn→realized profit を eval に最強レシピが勝ち伝播。

## Requirements (EARS)
- R1: README は Anicca を「AI が財務的自立を達成する**環境**」と定義する(製品でなく)。
- R2: ★3タイプそれぞれの正確な spawn コマンド★を載せる(automaton/Franklin=@blockrun/franklin 公式コマンド/claude-p)。コピペで動く形。
- R3: 5つの self-*(監視/修復/改善[個体+集団]/増殖/共有)+ swarm 自己実験を説明する。
- R4: dashboard(aniccaai.com/dashboard)= 透明な eval(各 agent の model×稼ぎ real-time)を書く。
- R5: ★正直な現在値★(初 realized $8.24 / settle tx / alive:3)を実 tx リンク付きで。誇張しない。
- R6: MISSION を正しく書く(financial independence が要件、モデルは auto 選択、UBI で人間へ還元、reduce suffering)。
- R7: 「どの端末・どのクラウドでも動く」= 拡散モデルを明記(§38)。

## DONE (adversary が verify)
1. README に3タイプの spawn コマンドが全部あり、Franklin は @blockrun/franklin の公式コマンドと一致(gh で本家 README と照合)。
2. 今日の実証の数字/tx が実在と一致(settle tx 0x7662a88b・redeem $8.24 が on-chain/spec と一致、誇張なし)。
3. 5 self-* + swarm 自己実験 + dashboard eval + UBI + works-anywhere が全て記述されている。
4. MISSION が §38 訂正どおり(financial independence 要件、モデル auto、free 強制と書いていない)。
5. markdown が壊れていない(見出し/コードブロック整合)、push 済みで origin から読める。

## Non-goals
- install.sh の ANICCA_TYPE 実装(=別タスク、README は「将来/現状」を正直に書く)。実 auto-mode(#24)。dashboard 実装変更。

## ADDENDUM (Dais 2026-07-05): README 全体を読んで矛盾を直し、kickstart を圧倒的に simple に
現 README(325行)を全読して確定した矛盾 = 部分 patch では直らない、全体で直す:
- R8: ★型の枠組みを1つに統一★。今「2 ways to KICKSTART(sub/USDC)」+「two instance types(human/self)」+「three colony types(automaton/Franklin/claude-p)」が衝突。→ ★automaton/Franklin/claude-p の3タイプ1本に統一★(funding は各タイプの属性として1行)。
- R9: ★「how to run」の重複を排除★。「Running Anicca」(L200)と「Spawn one」(L219)が automaton コマンド二重。→ 1つの「Quick start」に統合。
- R10: ★earn 内容を実態に★。clip/affiliate/video/gig の「5 tmux loops」(古い faceless系)を削除、実際の earn = ★PM/SOL/HL トレード + cook 探索 + redeem★ に統一。
- R11: ★個人設定の残骸を削除★。「bank account = Dais's」/ PayPay・Binance・GMO Aozora の日本ローカル mermaid → 汎用の「seed USDC → earn → UBI」図に。Life Manager 参照は残してよい(別repo明記)。
- R12: ★kickstart を dead-simple に★。冒頭近くに「3コマンドで起動」を1ブロック(最も簡単な道=subscription の claude-p か、self-funded automaton の1つを主動線に)。初見の人が30秒で「何で・どう起動」が分かる。
- DONE 追加: 上記5つ(型統一/重複排除/earn実態/個人残骸削除/simple kickstart)が全て満たされ、矛盾が残っていないこと(adversary が「2 vs 3 types」「clip/gig 古い earn」「Dais bank」等の矛盾ゼロを確認)。
