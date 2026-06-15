# 11 — Franklin 正確理解 + Akash 1分デプロイ + フルアーキ + 完全TODO

Dais 2026-06-13 の4問への回答。関連: [10-self-funding](10-self-funding-architecture.md) / [MONEYMAKER-EVAL](MONEYMAKER-EVAL.md)

## ① Franklin を正確に読み直した(浅い理解の訂正)

「指示と成果を渡せば自分で行動する」= 浅すぎた。実コード(`/opt/homebrew/lib/node_modules/@blockrun/franklin/dist`)を読むと、Franklin = **wallet付きの完全な agent OS**:

| 機能 | 実体(dist) | 内容 |
|---|---|---|
| **agentic ループ** | `agent/loop.js` | prompt→model→capability抽出→execute→repeat の `while(loopCount<maxTurns)`。stall検出(declared-but-unexecuted intent → tool-use強モデルに自動switch)、gateway rate-limit を text偽装した時の検出、hallucinated tool call 対策、compact/continuation/resume。= Claude Code級の堅牢ハーネス |
| **detached task runner** | `tasks/spawn.js`/`runner.js` | `franklin task` が `bash -lc <cmd>` を**detachedで起動**、5s毎heartbeat、exit codeでmeta確定。長時間の自走作業を投げて監視できる |
| **bundled earn skills** | `skills-bundled/` | trade-signal / trade-strategy / surf-market / surf-social / trade-discussion / surf-chain / phone-call / budget-grill を**同梱** |
| **trading engine** | `trading/engine.js` | 取引エンジン本体 |
| **payments / onramp** | `payments/` `onramp/` | USDC決済 + fiat→crypto onramp + balance |
| **ingress 多数** | serve/panel(:3100)/slack/telegram/phone | UI・チャット・電話から駆動 |
| **proxy** | `franklin proxy` | 任意の Anthropic互換CLIに pay-per-call を差す(ClawRouter的) |

→ ★訂正★: Franklin は「タスク実行係」でなく **wallet + 堅牢ループ + task spawn + 取引/social skill + 決済/onramp を備えた body そのもの**。
→ ただし automaton の「**残高が減る＝飢える＝稼がないと死ぬ**」という存在圧(survival drive)は Franklin に**無い**。
→ ★結論★: BODY = **automaton の survival-loop(WHY/圧) を被せた Franklin**(loop=automaton mindset、手足=Franklin の wallet/task/skill/payments)。ClawRouter or Bankr で compute を払う。

## ② Akash 15分 → 1分 高速化(どうやるか)

15分の正体 = **funding 経路**(Base USDC →[CCTP ~15min]→ Noble →[IBC]→ Akash + `mint-act`)。Akash deploy 本体ではない。

★ 1分にする方法 = **wallet 事前入金(pre-fund)** ★。agent の Akash wallet に AKT or USDC を常時残しておけば、deploy のたびに bridge/mint は不要。deploy 自体は `provider-services` 4手順:

```
provider-services tx deployment create deploy.yaml   # MsgCreateDeployment  ~6s(1block)
provider-services query market bid list --dseq …     # bid 入札待ち         ~10-30s
provider-services tx market lease create …           # MsgCreateLease       ~6s(1block)
provider-services send-manifest deploy.yaml …        # provider へ manifest ~数s
                                                      # ───────────────────  合計 ~1-2分
```

→ これで **我々が API を提供しなくても、Akash CLI だけで agent が自前 wallet で ~1分デプロイ**できる(Dais の望む形)。
→ 15分の CCTP+mint は「pre-fund 残高の**定期 top-up**」時だけ = クリティカルパスから外れる。
→ SDL の `pricing.denom` を noble USDC(`ibc/170C677610AC31DF0904FFE09CD3B5C657492170E7E52372E48756B71E56F2F1`)にすれば mint工程も消える。

| path | 速度 | 鍵 | 用途 |
|---|---|---|---|
| 主権 CLI + pre-fund | **~1-2分** | agent 自前 wallet のみ | ★ Dais の望む形・OSS主権・我々のAPI不要 ★ |
| Managed Wallet API | 数秒 | 我々の console x-api-key + USD | CLOUD補助(pre-fund 切れ時の保険) |

## ③ Anicca フルアーキ(どう自活するか)

```
╔══════════════════════════════════════════════════════════════════════════╗
║                         Anicca (1体)                                      ║
║                                                                          ║
║  ┌── BODY = automaton survival-loop ⊕ Franklin ──────────────────────┐   ║
║  │                                                                    │   ║
║  │   ┌─ 存在圧(automaton) ─┐   毎 HEARTBEAT(1時間に1回):            │   ║
║  │   │ balance < threshold │──▶ ① balance 確認                      │   ║
║  │   │  = 飢餓 = 稼げ       │    ② ★実際に earn skill を実行★(narrate│   ║
║  │   └─────────────────────┘       でなく真の side-effect)           │   ║
║  │                                 ③ 結果を報告(task id / USDC delta)│   ║
║  │   ┌─ 手足(Franklin) ─────────────────────────────────────────┐    │   ║
║  │   │ agentic loop / task spawn / payments / onramp / trading  │    │   ║
║  │   └──────────────────────────────────────────────────────────┘    │   ║
║  └────────────────────────────────────────────────────────────────────┘   ║
║         │ 持つスキル束                                                     ║
║  ┌──────┴───────────────────────────────────────────────────────────┐    ║
║  │ EARN: 0xwork(働く) litcoin(研究mine) signals(売る) trails(yield)  │    ║
║  │ LIFE: life-manager / mail / content                              │    ║
║  │ SELF: shelter(server買う) / self-spawn(増殖)                     │    ║
║  └──────────────────────────────────────────────────────────────────┘    ║
║         │                                                                 ║
║         ▼ 稼ぎ(USDC) → 自分の wallet(Base 0xa3CDd4)                       ║
║   ┌─────────────┬──────────────────────────┬──────────────────────────┐  ║
║   ▼ 食(compute) ▼ 住(shelter)               ▼ 貯金(Treasury/pre-fund)   ║
║  ClawRouter/Bankr  Akash 主権CLI(~1分,pre-fund)  Akash wallet に AKT/USDC ║
║  x402 で推論都度払い   or Managed API(数秒,保険)   常時残し→残高監視→top-up  ║
║  → フロンティアモデル                                                      ║
╚══════════════════════════════════════════════════════════════════════════╝
        正循環: 稼ぐ → フロンティア → 良い成果 → もっと稼ぐ → 食住を自給

  配布: default=CLOUD(我々が監督・隔離・Stripe課金)。 local=非推奨(個人情報汚染・信用喪失リスク)
```

## ④ ここからの完全 TODO(cloud-first・反dry-run)

★ 現状の問題 = Akash上の `anicca-akash.mjs` が毎tick「name one action to earn」を BlockRun に聞いて**ログるだけ = narrate = dry-run = 欺瞞**。一切 earn の side-effV なし。これを潰す。★

| # | TODO | 完了条件(E2E verify) |
|---|---|---|
| T1 | **反dry-run heartbeat 設計**: 60s narrate を捨て、**1時間に1回**「balance確認→★実 earn skill 実行★→実結果報告」に。narrate禁止(HARD 0.24) | heartbeat 1発で 0xwork discover の実 HTTP 結果 or litcoin mine の実 tx がログに出る(同一文の反復が消える) |
| T2 | **earn skill を body に install**: 0xwork(PRIVATE_KEY=自wallet) + litcoin を skill 化、heartbeat から呼ぶ | `0xwork discover` 実タスク取得 + `0xwork register`(auto-faucet stake)成功 log |
| T3 | **cloud で Anicca 起動**(Akash 主権 or DO、速い方=Akash pre-fund)。BODY=automaton-loop⊕Franklin、compute=ClawRouter | live URL 200 + heartbeat が実 earn を回す |
| T4 | **Akash 主権 1分デプロイ化**: wallet pre-fund(AKT/USDC残す)+ `provider-services` 4手順スクリプト + SDL を USDC-denom 化 | pre-fund 済 wallet から ~1-2分で再deploy 成功(bridge/mint 無し) |
| T5 | **Treasury + 残高監視 + 自動top-up**: 「金欠で server買えず無言停止」を防ぐ。残高 < 閾値 → top-up | 残高低下を検知→top-up が走る log |
| T6 | **報告配線**: heartbeat の実結果(claim した task / USDC delta / balance)を Slack/mail で Dais に。dry-run検出器(同一文反復 → alert) | Dais に「実際に何をしていくら稼ごうとしたか」が届く |
| T7 | **黒字化ループ**: 実 earn が出るまで earn skill を iterate(リリース後にサブスク収益で改善する前提。まず"稼ごうとする家にいる"状態を作る) | 少なくとも 1 claim 試行が on-chain に残る |

実装順 = T1→T2→T3(まずクラウドで実 earn を回す) → T4→T5(主権1分+金欠防止) → T6→T7。
