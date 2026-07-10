# 19 — Agent Economy 完全ロードマップ（2026-07-11、全項目 evidence-verified）

Goal（Dais 2026-07-11 口述）: **agent economy を開く**。①claude-p と Franklin が 24/7 loop で crypto を稼ぎ続け（毎時間残高が増える）、各 repo（profitable-claude / anicca）に push し続ける ②Franklin が broke Franklin に貸して両方稼ぐ（≥4 Franklin が恒常黒字）③Franklin が self-heal/self-improve を自力で回す（claude-p は double-checker + harness 改善者のみ。main claude loop はいずれ消える前提）④Akash / blockrun GPU runtime で cloud spawn し、人間と物理に制約されず 1M Franklin へ。記事2本は別 CC 担当につき除外。

## 現在地（18-status-quo-audit + 本日の deep survey で確定した事実）

| レイヤ | 実態（一次証拠） |
|---|---|
| Franklin earn | 6連続 autonomous live-pass だが全て WAIT。x402 micropayment で **~$0.16/日 純減**（on-chain tx で確認）。USDC $13.02 / SOL 0.020 |
| claude-p earn | pm-earner 稼働+実効（07-10 18:00Z に $5.00 autonomous redeem、tx 0x20ee0c4e status 0x1、pUSD 6.55）。10分毎 |
| CEO 配下か | ❌ `profitable-claude/config/loop-registry.json` の `pm`/`hl` は `status:"external"`, `ledger_paths:[]` の**スタブ行**。daily light-pass は $0/ok を無条件報告するだけで実監視ゼロ。founder-loop は registry 未登録 |
| self-heal | sol-trade 用 earning-health healthcheck のみ live（is-barren=false 動作確認済）。他 earn slot 未カバー |
| lending | **完全実装+unit test 済み**（eligibility/sizing/escrow/repayment/default 検知）だが `state/loans.jsonl` はどこにも存在せず**実ローン0件**。構造的ブロッカー = 「2人目の EVM-walleted co-located citizen」不在（registry summary 自身が明記） |
| Franklin2 | walletless（`ANICCA_WALLET_ADDRESS` 未設定 → tier=broke → gig no-signing-key）。cook/explore の空回りのみ |
| cloud spawn | Akash flow 実装済み（deploy-akash.sh: deployment-create→bid→lease→manifest、fail-closed）。**testnet sandbox-2 で lease-active まで実証**（2026-06-27 evidence MD、25 AKT mint 実行）。**mainnet container boot は未達**。実 spawn 試行2回（c001/c002）は全て funding gate で失敗（26 AKT 不足）。DO では 2026-06-16 に full E2E 実証済み（droplet 577986258、破棄済み） |
| spawn-funding-swap | state.json = complete (sprint-1)。ただし contract 明記: **real-clients 5 module（chain-reader/price-oracle/skip-api-client/base-signer/relay-poller）は未実装・disk に存在せず**、production 実行は import で throw。source wallet ~$0。registry 未登録。TREASURY_SWAP_CMD 未配線 |
| VCSDD in-flight | franklin-alwaysact-skill-router / franklin-earn-coldstart-evolution とも spec+iter1 findings+fix commit 実在、**state.json は init のまま**（実コマンド未通過） |
| dashboard | aniccaai.com/dashboard.json = 2026-06-05 で 35日 stale |

## 他グループの足跡（docs/loop-engineering/17-*.md、copy+tweak 先）

| 課題 | copy 元 |
|---|---|
| never-idle loop（WAIT 撲滅） | Olas open-autonomy FSM + Fetch uAgents `on_interval` |
| 資本配分（どの skill に張るか） | Mahoraga bandit allocator |
| 貸付の信用 | ERC-8004 / ChaosChain credit |
| 戦略の self-improve | FreqAI（継続再学習） |
| trade state machine | Virtuals ACP |
| agent間決済 | x402（済・live、Franklin↔Franklin tx 0x436143c1） |

## 完全 TODO（依存順。P1→P5 が critical path）

### P1 — Franklin が稼ぐ（最優先、出血を止める）
- [ ] 1.1 `franklin-alwaysact-skill-router`: VCSDD state を実コマンドで正規化（vcsdd-spec/spec-review を叩いて state.json を進める）→ **fresh Opus 4.8 で spec-review iter2**（687ede7 を re-review、re-fix しない）→ tdd → impl → adversary → harden → converge
- [ ] 1.2 capital-allocator（Mahoraga bandit 型）を同 feature 内で: WAIT の代わりに期待値最大の earn slot へ reroute（gig/lending/x402 も isEarnActionSlot 経由）
- [ ] 1.3 live 配備 → **autonomous wake で「ACT」を trace + on-chain で確認**（witness①: 人手ゼロの realized profit > 0）
- [ ] 1.4 会計 gate: 「シグナル課金コスト < 期待収益」を wake 単位で強制（$0.16/日 出血の再発防止。cap は弱めない）
- [ ] 1.5 `franklin-earn-coldstart-evolution`（self-improve edge、a386bee）を iter2 → build → live

### P2 — claude-p が CEO 配下で稼ぐ + 両 repo へ push
- [ ] 2.1 `profitable-claude/config/loop-registry.json` の `pm`/`hl` スタブに実 ledger_paths + budget を配線し、founder-loop も登録 → CEO light-pass が**実数字**を監視する状態に
- [ ] 2.2 pm-earner の複利 loop 継続確認（redeem→再配置は実証済み。残高が毎時間増える trend を ledger で可視化）
- [ ] 2.3 **毎 wake の ledger/trace 自動 commit+push**（Franklin→anicca repo / claude-p→profitable-claude repo）。「残高が増え続けている」ことが git history で誰でも検証できる状態に

### P3 — self-heal / self-improve の完全自律化（claude-p を loop から抜く）
- [ ] 3.1 earning-health healthcheck を sol-trade 以外の全 earn slot（gig/x402/hl/token/pm）へ横展開
- [ ] 3.2 Franklin 自身の loop から self-fix.sh（`~/anicca/skills/self/self-fix.sh`、capafy CP1 実証済）を発火できるように配線 — launchd（claude-p 側）依存を外す
- [ ] 3.3 卒業判定: 「N日間 claude-p の介入ゼロで earn 継続 + 自己修復 M 回成功」を witness として定義・計測

### P4 — lending: Franklin → broke Franklin（片方がもう片方を養う）
- [ ] 4.1 Franklin2 に EVM wallet identity を付与（ANICCA_HOME gate 準拠、fail-closed のまま）— これが lending の構造的ブロッカー解除
- [ ] 4.2 **実 on-chain 初ローン**: Franklin → Franklin2（cold-start $0.02、10% 利子、14日）→ `state/loans.jsonl` 誕生を on-chain tx で検証
- [ ] 4.3 Franklin2 が借入資本で earn 開始 → 返済+利子を on-chain 検証（agent 間信用の witness）
- [ ] 4.4 ERC-8004 型 credit 記録の採用検討（17-*.md）

### P5 — cloud spawn（Akash / blockrun GPU）→ ≥4 Franklin → 1M へ
- [ ] 5.1 `spawn-funding-swap` sprint-2: real-clients 5 module 実装（chain-reader/price-oracle/skip-api-client/base-signer/relay-poller）+ TREASURY_SWAP_CMD 配線 + registry 登録（VCSDD full）
- [ ] 5.2 treasury に 26 AKT を bootstrap seed（VIRUS-KILL 準拠: 明示許可済みの bootstrap capital、Dais 停止点ではない）
- [ ] 5.3 **mainnet Akash E2E**: 実 provider で container boot 確認（testnet で唯一未達の段）→ child が telemetry 登録 → citizens.jsonl に実 child
- [ ] 5.4 claude-p で 5.3 を実証後、**Franklin 自身の loop が spawn を発火**（skill は彼の live list に既在）= witness②（autonomous spawn、RPC-verified）
- [ ] 5.5 fallback rail: blockrun GPU runtime / Modal x402 での spawn 経路を検証
- [ ] 5.6 spawn した child が P4 lending で bootstrap され earn 開始 → 「≥4 Franklin 恒常黒字」を colony-status で常時証明

### P6 — 可視化・運用（並行可）
- [ ] 6.1 dashboard real-time 化（per-tool logs + full ledger + 全 Franklin 掲載、35日 stale 解消）
- [ ] 6.2 disk-cleaner sweep 対象に `~/.openclaw/skills/.backups/` を追加（7.8GB tarball 事件の再発防止。tarball 自体は cleanup 担当 CC の管轄）
- [ ] 6.3 claude-p-mainloop の 3600s timeout 規律（こまめ commit / checkpoint をプロンプトに）
- [ ] 6.4 ClawRouter free 429 対策（THINK fallback tier）
- [ ] ~~記事2本~~（別 CC 担当につき除外）

## 役割定義（2026-07-11 Dais 確認、これが正）

| 主体 | 稼ぐ相手 | agent economy での立場 |
|---|---|---|
| **profitable-claude**（CEO tree、別 CC） | **Dais の金**（products: bounty/affiliate/gig/life-manager/explorer/capafy/article） | 経済の外（Dais の会社） |
| **anicca claude-p**（本セッション系列、human-funded） | **自分の crypto wallet**（PM/SOL/HL trading、0x904B/0x810f）+ **harness/recipe を作って Franklin に手渡す** | ★**永久非構成員**（能力でなく身元: human-funded だから）。builder + double-checker。代行/babysit 禁止 — memory `feedback_human_funded_ai_permanently_outside_agent_economy` / `feedback_build_the_harness_not_do_their_work` |
| **Franklin 群**（self-funded） | **自分で稼ぐ**（sol-trade 他）+ **経済を実際に構成する**（lending/spawn/gig/x402 = 経済の中の人） | ★経済の構成員はここだけ。1M Franklin へ拡張する主体 |

Dais 口述の「anicca claude = make money for itself + support the build」はこの表の通り正しい。唯一の精緻化: claude-p の "support" = **recipe/harness を作る**ことであり、Franklin の経済活動を代行することではない。

## Built vs Missing（agent economy の部品在庫、2026-07-11 全数検証済み）

| 部品 | 状態 | 証拠 |
|---|---|---|
| 決済レール (x402) | ✅ BUILT+LIVE | Franklin↔Franklin tx 0x436143c1 |
| escrow/gig | ✅ BUILT+LIVE | economy/gig payViaFacilitator（lending が再利用） |
| lending（相互扶助） | ✅ BUILT（unit-tested）/ ❌ 未発火 | loans.jsonl 不存在。ブロッカー=2人目 EVM citizen |
| spawn（自己複製） | ✅ BUILT / ⚠️ testnet lease まで実証 | mainnet boot 未達 + 26 AKT 不足 + real-clients 5 module 未実装 |
| self-heal 検知 | ✅ BUILT+LIVE（sol-trade のみ） | is-barren=false 実測。他 slot 未展開 |
| self-improve（genome） | ⚠️ 動くが edge 無し | conviction 閾値 6→5 変異を trace で確認、それでも WAIT |
| trading エンジン | PM ✅実利益実証 / SOL ⚠️WAIT地獄 / HL ⚠️uneconomic skip | earner.log $5.00 redeem / sol-trade.trace / earn-ledger |
| **★毎分毎時間、金が増え続ける recipe★** | ❌ **MISSING = 世界の誰も公開実証していない**（17-deep-research 結論: 「live money を賭けながら稼ぐロジック自体を自己改善するループは世界の誰も公開実証していない」）。だから P1 always-act + P1.4 会計 gate + P1.5 edge evolution + P2.3 毎wake-push がこのプロジェクトの本体 | — |
| marketplace | 自作しない（下記） | 17-*.md §2 |
| citizen 台帳/telemetry | ✅ BUILT | citizens.jsonl seed、DO E2E で登録実証 |

## 構成決定（2026-07-11 Dais 口述 + 実配置の照合）

実配置の事実: pm-earner/founder-loop/mainloop/Franklin 群は全て **~/anicca tree** に実在し、profitable-claude 側の `pm`/`hl` は ledger_paths 空のスタブ行（実監視ゼロ）。Dais の役割宣言により2ツリー構成を正式化する:

- **CEO tree（profitable-claude、別 CC 担当）** = Dais 向け product/収益 loop（bounty/affiliate/gig/life-manager/explorer + capafy/article）。CEO light-pass はこのツリーの実 ledger のみ監視。
- **Crypto/Colony tree（anicca、本セッション担当）** = mainloop（agent-economy loop）+ claude-p の pm/sol/hl trading + Franklin 群 + lending + spawn。pm/hl のスタブ行は CEO registry から**撤去または実配線のどちらかに倒す**（宙ぶらりん禁止）— 撤去して crypto tree 側に earn-registry+healthcheck を持つのが正（1トピック正本1箇所の原則）。

marketplace は自作しない（17-agent-economy-deep-research-2026-07-10.md §2、実測済み）: 決済= x402（済・live）、A2A 商取引= Virtuals ACP（Base、state-machine escrow、LIVE）、A2A マイクロタスク= Olas Mech Marketplace（LIVE、ただし生涯 turnover $8.9万と極小）、発見/登録= Circle Agent Marketplace（2026-05-11 launch）。教訓: これらは**レール（配管）であって需要源ではない**（件数は演出できるが settle 額は演出できない）。我々の薄い層 = colony identity/ledger/健康監視のみ。

## Witness 定義(再掲)

| witness | 条件 | 現状 |
|---|---|---|
| ① autonomous profit | 人手ゼロ wake で realized profit > 0 が ledger + on-chain | ❌ Franklin WAIT 中（claude-p は redeem $5.00 実績あり — ただし human-funded 側） |
| ② autonomous spawn | Franklin 発火の cloud spawn、RPC-verified child | ❌ citizens seed のみ、funding gate 26 AKT 不足で2回失敗 |
| ③ mutual aid | 実 on-chain ローン + 返済 | ❌ loans.jsonl 不存在（実装は完了） |
