# 13 MERGED COLONY STATUS — 両台帳を1つに（2026-07-10）★他CCへの引き継ぎ正本★

> ★これは「2つの並列努力」を1つに merge した唯一のマップ。両 CC はここを読めば全体が1つに見える。★
> - 台帳A = `~/anicca/.vcsdd/`（EARN + SELF-IMPROVE 基盤、私 claude-p の側）
> - 台帳B = `~/anicca-project/.vcsdd/`（SPAWN + CEO + LEND + CLIP 社会層、別CC の側）
> - 両方 = **1つの agent economy**。相補的、衝突なし。AGENT ECONOMY LOOP(私)が親開発者として両方建てる。
> - 詳細 evidence の正本 = [[10-STATUS-verified]] §E。呼称/分業/repo = [[04-the-two-loops]] §7-10。

## TO-BE（終着 = これが全部真になったら claude-p は exit）

**人間ゼロで自走する agent economy**: citizens(Franklin/automaton) が自分の wake-cycle で
① EARN 実 realized profit（on-chain 検証）② SELF-IMPROVE 自分の戦略を進化 ③ SPAWN 子を cloud に産む
④ CEO loop に管理され(double-down/halt) ⑤ LEND 仲間を支える — を全部自分でやり、私(親/開発者)は out。

## 能力レイヤー別 マージ済みステータス（DONE / IN-FLIGHT / TODO）

### L1 EARN（citizens が稼ぐ）— GAP: 実 edge 無しで net-flat（C1）
| 状態 | feature（台帳） |
|---|---|
| ✅DONE | hl-realized-pnl(A) / earn-roi-reconciler(A) / earnings-to-settle-mirror(A) / dispatcher-live-dormant-mode(A) / recipe-6-actions(A) / roi-writer-and-dormant(A) / gig-run-shim(A) / founder-x402-self-facilitate(A) / clip-loop-dual-instance-earn(B) / gig-feasibility-volume(B) |
| 🔶IN-FLIGHT | franklin-earn-foundation(A,6→converge) / earn-shared-skeleton(A,4) / clip-post-verify-hardening(B,6→converge) / clip-clawrouter-instance-provision(B,2a) / capafy-harness(B,2a) |
| ⬜TODO | eval-driven-earning / trading-polymarket-spawn / x402-{discovery,go-live,endpoint,research} / earn-redeem-winnings / promote-fun-clip-earn / engine-parity-franklin |

### L2 SELF-IMPROVE（citizens が自分を改善）— GAP: harness は実ledger接続済、Franklin live戦略へ未接続（C1②→③）
| 状態 | feature |
|---|---|
| ✅DONE | **self-improve-real-ledger(A) ← 2026-07-10 AGENT ECONOMY LOOP が自律converge, PR#937** / proactive-loop-skeleton(A) / proactive-step6-act(A) / install-proactive-plist(A) |
| 🔶IN-FLIGHT | anicca-self-improve-harness(A,1b) / franklin-loop-revival(A,6→converge) / ship-anicca-loop(A,2c) / anicca-harness-tooluse-health(B,1c, iter4未dispatch) |
| ⬜TODO | gig-earn-self-improve |

### L3 SPAWN（citizens が子を産む）— GAP: 真の spawn ゼロ（citizens.json=seed 1件）
| 状態 | feature |
|---|---|
| ✅DONE | spawn-pin-real-ed25519(A) |
| 🔶IN-FLIGHT | **anicca-agent-spawn(B,3=impl review, spawn engine 本体)** / anicca-spawn-identity-resolution-fix(B, fix `f89f37c` 出荷済だが state=init=台帳mismatch要reconcile) |
| ⬜TODO | spawn-auto-seed / env-readme-spawn |

### L4 CEO / MANAGEMENT（ポートフォリオ配分）— GAP: CEO骨格完成、live事業への実配分は未
| 状態 | feature |
|---|---|
| ✅DONE | **claude-p-ceo-loop(B) ← CEO loop 完成** / anicca-agent-economy(B) |
| 🔶IN-FLIGHT | claude-p-loop-verification(B,6→converge) / agents-at-arms-leaderboard(B,3) / realtime-fleet-dashboard(A,init) / dash-activity-revenue(B,init) |

### L5 LEND / 相互扶助 — GAP: lending完成、実ローンはゼロ（経済未稼働のため）
| 状態 | feature |
|---|---|
| ✅DONE | anicca-agent-lending(B) |

### L6 INFRA / FUNDING / LOOP
| 状態 | feature |
|---|---|
| ✅DONE + 実証 | **AGENT ECONOMY LOOP(A) = 稼働中 + 自律実証**（2026-07-10 に self-improve を自分で converge、EXIT-CHECK 正直報告） |
| 🔶IN-FLIGHT | franklin-funding-loop(A,1b) / founder-money-loop(A,init) |
| ⬜TODO | clawrouter-zero-human / akash-provider-services-acceleration |

## REMAINING — TO-BE に到達する残作業（優先順）

1. **in-flight の phase6 を converge→complete**（両台帳): franklin-earn-foundation(A) / franklin-loop-revival(A) / claude-p-loop-verification(B) / clip-post-verify-hardening(B)。各 fresh Opus adversary 0 blocking。
2. **C1 = Franklin に実 edge**（L1 GAP）: harness が戦略進化を駆動し net-positive realized trade。手書き禁止。
3. **spawn 完遂**（L3 GAP）: anicca-agent-spawn(B,3) の次 fresh-Opus round → 初の真の自律 spawn（citizens.json 新エントリ RPC検証）。identity-resolution-fix の台帳 reconcile。
4. **CEO loop を live 事業に接続**（L4 GAP）: claude-p-ceo-loop が実 earn 事業を double-down/halt 配分。
5. **→ 実 profit + 実 spawn = 経済 alive → claude-p EXIT**（AGENT ECONOMY LOOP の自己終了ゲート発火）。

## 引き継ぎ（他CCへ）
- 両 CC は本ファイル + [[00-INDEX]] + [[10-STATUS-verified]] §D/§E を読めば「1つの真実」に立てる。
- AGENT ECONOMY LOOP は live 稼働中（worktree 使用）— 衝突回避。触るな territory: `anicca-agent-economy/**`(別CC完成物)。
- 次の統一 /goal = handover mail(v4, keiodaisuke宛) 末尾。両台帳を1本で駆動。

出典: 両 .vcsdd/features/*/state.json 全実測(2026-07-10) / 各 behavioral-spec.md タイトル / MAINLOOP-LOG.md(loop 自律 run) / git log(PR#937 `8365199`)。
