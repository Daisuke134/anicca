# HANDOFF — agent-economy 実装ループ（2026-07-11 更新）

★ FRESH SESSION はまず `docs/loop-engineering/20-implementation-certainty-2026-07-11.md`（§A-G, confidence 表）と `21-p1-alwaysact-live-2026-07-11.md`（live milestone + WITNESS③）を読む。★

## 運用モデル（この session がやっていること）
thinker=私（Fable/Opus main loop）、実装=Sonnet subagent、adversary=Opus 4.8 fresh。全 feature を full/lean VCSDD で回し、adversary が PASS するまで iter を重ね、私が独立に test 実行して verify、money milestone は MONEY EVIDENCE PROTOCOL（on-chain tx + mail to Dais keiodaisuke@gmail.com + dashboard 実数値）でのみ完了。`/loop` で自走。人間へ質問しない。

## ★ 達成済み（全て merged to `~/anicca` main + live 検証済み）★
| P | 内容 | 証拠 |
|---|---|---|
| P1 | always-act（NO-WAIT earn router）| spec5+impl4+converge5 iter、engaged wake が ACT。flag `ALWAYS_ACT_ENABLED=1` on franklin-loop plist。go-live ledger 行あり |
| P2 | per-wake ledger publish | origin branch `ledger-franklin`（wake+earn jsonl、git 検証可能）。flag `LEDGER_PUBLISH_ENABLED=1` |
| **P4 / WITNESS③** | **初 on-chain 相互扶助ローン** | **tx `0x36faafce0f22817eb94f3d2b7111d188e224287dbc31b8c976edf193cf6e2863`**（Base、status 0x1、USDC $0.02 Franklin→Franklin2、RPC 検証）。loan_Franklin_41 active |

### P4 で構築した恒久資産（再利用可）
- Franklin2 identity: EVM `0xe7747Fd899D8987821Bb4CB3D6aDf22565F87ce9` / Solana `HyJHSfTkLjpmqeY4FEbnSjM4DfUh9ELGchHqgFDBkrcX`。wallet.json は `~/.franklin2-home/.blockrun/.automaton/`。plist に `ANICCA_STATE_DIR=/Users/anicca/.hermes/state`（canonical citizens 共有）。
- daemon が franklin[N] 認識（`is_franklin_instance`）。
- **x402 facilitator mainnet live**: `~/anicca/services/facilitator/` の `GIG_CHAIN=base ./start.sh` で :8405 起動（eip155:8453）。signer `0x1F5b17f41524B02a4ee4d99D4158c86C942e43f3`。★gasless settle は facilitator が gas 立替 → 定期的に Base ETH 補充が要る。現在 ~0.001655 ETH。★
- **gas-eth refill**: `skills/earn/funding/franklin_sol_base_refill.py --gas-eth --recipient <addr> --live`（relay Solana USDC→Base native ETH、$3 cap）。USDC refill は同 script `--live`（`--recipient` なし）。
- lending: `~/.blockrun/skills/economy/lending/run.sh`（要 `GIG_CHAIN=base GIG_FACILITATOR_URL=http://127.0.0.1:8405`）。全 money-safety guard live。citizens.json = `~/.hermes/state/citizens.json`（Franklin+Franklin2、両 EVM 行）。
- Franklin Solana wallet `8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9`、Base wallet `0x3EcCAD24794ca298D25378E9902A251322ea8749`。

## 🔄 進行中 / 残
| P | 状態 | 次アクション |
|---|---|---|
| **P3 self-heal 全 slot** | 🔄 branch `feature/self-heal-allslots`（f9219842、13/13+9/9 green、adversary review 中）。sol-trade+pm-trade を barren 検知に実配線、他は gap 記録。self-fix.sh が claude-p OpenClaw 依存（graduation gap 明記済み）| adversary PASS→merge→plist `ai.anicca.earning-health-allslots` を load |
| **P5 spawn（witness②）** | 未着手。前提は 20.md §E 済み: spawn-funding-swap の real-clients 5 module（chain-reader/price-oracle/skip-api/base-signer/relay-poller、~290行、copy元特定済）+ 26 AKT seed（`anicca-akash` keyring）+ mainnet Akash container boot（testnet lease まで実証済、唯一 boot 未達）→ Franklin 自身が spawn 発火 | lean VCSDD で real-clients 実装 → testnet E2E → 26 AKT → mainnet boot |
| **P6 dashboard** | 未着手 | aniccaai.com/dashboard.json real-time 化（35日 stale）+ 全 Franklin + 実 ledger。facilitator の launchd 常駐化（今は手動 start.sh）。cleaner に `~/.openclaw/skills/.backups/` sweep 追加 |
| P1-sprint2 | task #7、未着手 | free/glm-4.7 が engaged schema で tool call を出せず ~80% wake が escalation。few-shot example + escalation raw snippet 観測性 |

## 既知の運用ノート
- **fablize hook「tool failure」誤発火**は session 全体の既知 artifact（grep no-match / 意図的 RED test の exit 1 が sticky flag 化）。実失敗ではない、複数 agent が確認済み。
- ディスクが度々逼迫（99%）。許可済み回収: `~/.cache/anicca-*`、旧 scratchpad、`~/.openclaw/skills/.backups/*.tar.gz`（git 追跡済で復元可）。cargo target も大物。
- public Base RPC（mainnet.base.org）は 429 頻発 → `BASE_RPC_URL=https://base-rpc.publicnode.com` を使う。
- worktree が外部プロセスに削除される事故あり → `.anicca-keep` marker 必須、branch は push 済みなら `git worktree add <path> <branch>` で復元可。
- lending の junk 行（loan_Franklin_2..41）は全て disbursement_failed か、41 が唯一 active。ガード健全性の実証。
