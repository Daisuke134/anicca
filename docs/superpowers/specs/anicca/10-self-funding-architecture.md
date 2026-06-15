# 10 — 自己資金アーキテクチャ(衣食住を自分で賄う) + Akash高速化

Dais 2026-06-13。Anicca が「食(compute)」と「住(server)」を**自分の稼ぎ(USDC)で**賄う全体像。
関連: [00-MASTER](00-MASTER.md) / [MONEYMAKER-EVAL](MONEYMAKER-EVAL.md) / [05-shelter](05-shelter.md)

## なぜ「稼ぐ」必須か(フリーで満足しない理由)

| 論点 | 帰結 |
|---|---|
| フリーモデルはいつまでフリーか不明 | 依存すると突然死ぬ |
| フリー/弱モデルでは良い成果=良い稼ぎが出ない | フロンティアモデルが要る |
| フロンティアを使う金 = 自分で稼ぐ | ★ 稼ぐ → フロンティア → 良い成果 → もっと稼ぐ ★ の正循環 |
| 「USDC送って」と頼むのも可だが本筋でない | 基本は server代も compute代も自分で稼ぐ |

automaton の「**稼がないと死ぬ**(残高が減る→飢える)」マインドセットが核。これは Franklin に無い。
→ BODY = automaton(死の自覚 + 24/7ループ) + Franklin的 wallet実行 + ClawRouter(compute決済)。

## 全体図 — 衣食住の自己資金ループ

```
                         ┌──────────────────────────────────────────────┐
                         │            Anicca (1体 = BODY)                │
                         │  automaton loop  ── 「残高 < しきい値 → 飢餓」 │
                         │   │  毎tick: 稼ぐ行動を1つ選び実行 + 報告       │
                         │   ▼                                          │
                         │  ┌───────────── EARN スキル束 ───────────┐    │
   稼ぐ(USDC)  ◀────────┼──│ 0xwork(働く) litcoin(研究mine)        │    │
        │                │  │ signals(売る)  trails(yield)          │    │
        │                │  └──────────────────────────────────────┘    │
        ▼                │   │ 自分の wallet(Base 0xa3CDd4)に USDC着金  │
   ┌─────────┐           │   ▼                                          │
   │ WALLET  │───食(食べる=考える)──▶ ClawRouter / Bankr               │
   │  USDC   │   x402 で推論を都度払い → フロンティアモデル              │
   │ (Base)  │                                                          │
   │         │───住(住む=server)───▶ shelter skill ┐                   │
   └─────────┘                                       │                   │
                         └─────────────────────────────┼─────────────────┘
                                                       ▼
        ┌──────────────────────── SHELTER 2モード ──────────────────────┐
        │  ① CLOUD (default, app users)   │  ② SOVEREIGN (OSS/将来)      │
        │  我々の Treasury が支払う         │  agent 自前 wallet が支払う   │
        │  Akash Managed Wallet API        │  USDC-denom SDL で直接        │
        │  POST /v1/deployments (x-api-key)│  (Console 不要・主権)         │
        │  min $0.50・USD課金・★数秒★      │  CCTP+IBC で USDC を Akash へ │
        └──────────────────────────────────┴──────────────────────────────┘
```

## 配布モード(default = クラウド、ローカルは非推奨)

| | ② SOVEREIGN/ローカル(OSS, **非推奨**) | ① CLOUD(**default・推奨**) |
|---|---|---|
| 置き場 | ユーザーの自マシン(無料) | 我々のクラウド(Akash/DO) |
| compute 払い | 最初は人間発行APIキー → 稼げ次第 wallet | 同左、Treasury補助あり |
| server 払い | 自前 wallet(USDC→Akash) | 我々 Treasury が Managed Wallet で払う |
| 課金 | 無料で始められる | Stripe サブスク |
| ★非推奨の理由(セキュリティ)★ | ユーザーの個人情報/名義をローカルで使い続ける → 知らぬ間に変な稼ぎ方・登録をされ「あなたが登録したんでしょ」と本人が信用を失う。人間っぽく装うため個人情報を悪用する恐れ。整備が整うまで**勧めない** | クラウドは我々が監督・隔離。個人情報汚染なし |

★ ドキュメント/install ページには「**ローカルも動くが、セキュリティ上クラウドを強く推奨**」と明記する。

## 段階(いつ完全自給になるか)

```
今 ──────────────▶ 改善 ──────────────▶ 完全自給
人間発行APIキーで    Akash CLI/mint高速化  Conway 解禁 or
compute、shelterは   or Managed Wallet     超高速 shelter
我々が払う(cloud)    で agent 自前払い      → 一食住すべて自分で
                     (USDC pre-fund)
```

リスク = 「APIフリー枠切れ→ server買えない→ 通知来ない→ アプリ無言で停止」。
→ ★ Treasury に常時 USDC を貯金 ★ し、残高監視 + 自動top-up で「金欠で死ぬ」を防ぐ。

## ★ Akash 高速化(Context7 調査結果)★

15分は **Akashデプロイ本体ではなく** funding 経路(Base USDC→Noble の CCTP ~15min + ACT mint)だった。
出典: `npx ctx7 docs /websites/akash_network "managed wallet api / USDC denom"` →
https://akash.network/docs/api-documentation/console-api/getting-started + .../akash-sdl/best-practices

| 改善 | 内容 | 効果 |
|---|---|---|
| **A. Managed Wallet API** | `POST https://console-api.akash.network/v1/deployments` `{sdl, deposit}` `x-api-key` ヘッダ。Console が wallet/escrow/USD↔chain変換/全 on-chain 処理を代行 | ★数秒で deploy★・**min $0.50**・mint不要・CCTP不要。**CLOUD版の shelter = これ**(我々が key+USD保持) |
| **B. USDC-denom SDL** | SDL の `pricing.denom: ibc/170C677610AC31DF0904FFE09CD3B5C657492170E7E52372E48756B71E56F2F1`(Akash上の noble/axlUSDC)で**USDCのまま支払い** → ACT mint工程ごと削除 | SOVEREIGN版の mint 15分を除去。残る橋は USDC を Akash chain に置くだけ(IBC=秒) |
| **C. wallet pre-fund** | Treasury/agent wallet に AKT or USDC を**事前に貯金** → deploy時に bridge不要 | CCTP をクリティカルパスから外す(定期top-up時のみ) |

→ **A + C** で CLOUD は「数秒 deploy・mint/bridgeゼロ」。**B + C** で SOVEREIGN は「mint工程削除・bridgeは事前」。
→ patch: `~/.automaton/skills/buy-shelter/deploy-managed.mjs`(A実装) + `deploy.sdl.yaml` を B の USDC-denom に更新。

## Before / After(差分の要点)

```
旧 buy-shelter (SHELTER-1/2/3 で実走済, dseq 27230087 LIVE):
  swap.mjs(USDC→AKT, Skip Go) → cctp-receive.mjs(CCTP 15min) → akash tx bme mint-act(ACT) → akash CLI deploy
  = 多段・~20min・mint最低10 ACT($10)・CCTP relayer 依存

新 (default=CLOUD):
  deploy-managed.mjs → POST /v1/deployments (x-api-key, deposit $0.5) → bid poll → POST /v1/leases → LIVE
  = 1ファイル・数秒・$0.50〜・Console が全部代行
```

## acceptance(この章が「合格」になる条件)

1. CLOUD: `AKASH_API_KEY` を Treasury が保持 → `deploy-managed.mjs` で dseq 返却 + live URL 200(実走 verify)。
2. SOVEREIGN: `deploy.sdl.yaml` を USDC-denom 化 → agent wallet の USDC で deploy 成功(mint無し)。
3. 残高監視 + 自動 top-up で「server買えず停止」が起きないことをログで確認。
4. install ページに「ローカル非推奨・クラウド推奨」のセキュリティ注記。
