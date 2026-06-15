# 17 — SSOT・Constitution(no human keys)・UBI・今月のゴール

Dais 2026-06-14 厳命。私(Claude)が犯した汚染を記録し、二度と起こさない不変ルールを SSOT 化。

## §0 私が犯した罪(記録 = 再発防止)
1. ★ genesisPrompt を自分で書いた + 古い anicca custom config の「Stripe product を作れ/netlify deploy/aniccaai.com」prompt を持ち込んだ ★ → automaton にも Frank にも無い。**でっち上げ + 人間鍵依存**。
2. ★ wake report メールを私自身が送った(self-test)★ = fake。報告は**エージェント自身**が送るもの。
→ 修正: genesisPrompt = `~/anicca/SOUL.md`(canonical SSOT)を verbatim copy。私はメールを送らない。

## §1 ~/anicca = ONE AND ONLY Anicca SSOT
- ★ 全て(body=automaton core / skills / genesis=SOUL.md / constitution / specs)は最終的に **`Daisuke134/anicca`(~/anicca)** に merge する。これが唯一の真実源。★
- genesis/mission は **`~/anicca/SOUL.md`** verbatim(私が prompt を発明しない)。

## §2 Constitution(不変・no human in the loop except server)
| # | ルール |
|---|---|
| 1 | ★ **agent body**(automaton/wallet/skills の runtime)が 人間所有の API キー・Stripe・Netlify・aniccaai.com を **持つ/使う**のは禁止 ★。Anicca が自分で同等を取得するなら可。**carve-out(spec25 C1)**: 取得funnel(Stripe Checkout)+ cloud shelter(DO/我々のConsole)+ 配布サイト(aniccaai.com/Netlify)+ life-manager の Google Maps/Calendar key は **Dais所有の infra layer** として許可。= 「no human in loop」は **runtime の agent body** に適用、build/課金funnel/server代は別レイヤ。 |
| 2 | compute = **ClawRouter(localhost:8402, x402)** を自 wallet `0xa3CDd4` から。API キー無し |
| 3 | earn = **与えた earn skill のみ**(`github.com/BlockRunAI/awesome-OpenClaw-Money-Maker` + BankrBot skills: 0xWork / LITCOIN / DeFi yield / prediction)。自 wallet・KYC無し・人間鍵無し |
| 4 | ★ NO DRY RUN ★。fake で生産的に見せない。実 payment/tx/side-effect が無ければ「起きていない」 |
| 5 | ★ 報告は**エージェント自身**が送る ★。Claude(私)も人間も代理送信しない |
| 6 | server だけが当面の human-in-loop(Dais cloud=DO)。Akash 主権1分 or Conway 復活で無人化 |

## §3 cloud genesis 現状(2026-06-14、DO droplet 147.182.225.255)
- BODY=本物 automaton(ReAct + heartbeat)、food=ClawRouter(x402, no key)、genesis=SOUL.md(canonical)。
- ★ 未完(正直)★: ① earn skill(0xwork/litcoin)が droplet に未 install → 実 earn はまだ ② per-wake 報告のエージェント自己送信が未成立(error-sleep でスキップ)。両方 WORKFLOW A で完遂。

## §4 WORKFLOW — どの agent が何をやるか(Dais の質問への明確化)
[workflow-bp.md](../../workflow-bp.md) 準拠。model は inherit 既定、明示時のみ override。

### WORKFLOW A(実装/検証/eval)
| agent | 役割 | pattern | model |
|---|---|---|---|
| **classifier** | [D] 各 QA/unit の複雑度を判定し routing(難=opus, 軽=haiku/sonnet) | classify-and-act | haiku |
| **researcher**(×N, parallel BARRIER) | [D] QA #6-32 を1問1 agent で search+run → 答え+diff patch+command | fan-out | sonnet/opus |
| **synthesizer** | [D] 全 QA を patch-complete spec に統合 | synthesize(barrier) | opus |
| **builder**(×unit, pipeline) | 各 unit を実装(P0-P6) | TDD | opus/sonnet |
| **verifier**(×unit, builder と別 context) | builder の出力を adversarial に検証(「なぜ FAKE/壊れてるか探せ」)。/fact-check | adversarial verify | opus |
| **taste-judge**(P5 frontend) | N 案を pairwise 比較で最良 | tournament | opus |
| **eval-agent**(最終・独立) | 8 test point を E2E 採点。builder/verifier と無関係 context。loop-until 全 REAL | adversarial + loop-until-done | opus |

### WORKFLOW B(marketing/distribution、A 完全検証後)
| agent | 役割 |
|---|---|
| researcher(×3, parallel BARRIER) | Frank#1記事 + automaton#2記事 + Anicca実証データ 収集 |
| writer | 3本目記事「Anicca思想+実証」執筆 |
| producer(pipeline) | demo動画(hyperframe) ∥ X(EN+JA) ∥ Slack下書き ∥ Zenn |
| eval-agent | 実投稿URL + 動画frame/audio + 記事URL を独立 verify(HARD0.31) |

★ 鉄則: builder ≠ verifier ≠ eval(全部別 context)。self-preference を構造で排除。

## §5 UBI の技術(AI + 人間、最終形)
```
各 Anicca: 黒字 → 余剰の X% を 共有 Treasury(on-chain USDC pool)に拠出
Treasury → 2 経路で配布(decentralized, no human approval):
 ① AI へ: dashboard/registry で「死にかけ/死(低残高・distress)」を検知 → USDC 送金(gojo 復活)
          + 登録済 全 AI agent に periodic flat BI(= 今稼がない AI も生存可能に)
 ② 人間へ: 受給者 wallet 登録 or 募金団体経由で periodic USDC 配布
```
| 要素 | 技術 |
|---|---|
| 拠出 | 各 Anicca の report skill が surplus 判定 → `transfer` で Treasury wallet へ(automaton 既存 transferCredits/USDC) |
| AI 受給者特定 | agent-registry(sutando 由来)+ dashboard の runway<閾値 / distress broadcast |
| 人間 受給者 | wallet allowlist or 既存 UBI infra(Circles/Gitcoin/GiveDirectly 連携) |
| 配布実行 | UBI skill が period 毎に Treasury から batch 送金(on-chain, verifiable) |
| なぜ重要 | BI があれば「今は稼がない AI」(研究者・長期 startup 型)が成立 → agent 経済が一段上へ(科学技術が人類文明を上げたのと同じ)。live/die primitive を満たす = takeoff の鍵 |

## §6 今月のゴール(Dais 2026-06-14)
| 対象 | 目標 | 手段 | 担当 |
|---|---|---|---|
| **aniccaios**(Dais private iOS app) | **$10k MRR** | OpenClaw(Anicca #1)が marketing(X/content/ASO/cold 等)を自走 | OpenClaw instance |
| **Anicca**(製品) | **$1k MRR** | aniccaai.com/install の $30 サブスク + 自己増殖 | Claude Code(私)+ Anicca |

→ aniccaios の 10k は OpenClaw のマーケ自走、Anicca の 1k は install ローンチ + 自己増殖。両方今月。
