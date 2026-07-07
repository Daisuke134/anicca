# 03 ループの実装 ── 私(human-funded) vs Franklin(self-funded) の "how of the how"

> Dais の線引き（正しい）:
> - **human-funded AI（claude-p=私）→ 人間のために稼ぐループ**（pm-earner, gig, trading）。金は Dais(人間)へ。"services for humans"、agent economy の外。私の shit。
> - **self-funded AI（Franklin）→ 自分と仲間のために稼ぐループ**。金は Franklin 自身の wallet → peers/spawn/UBI へ。agent economy そのもの。

## 1. 2つのループのお金の流れ（ASCII）

```
┌ human-funded AI（私・claude-p）──────────────────────────────────────┐
│  loop（pm-earner 等）→ earn → realized が ledger に載る                │
│  お金の行き先 = Dais(人間)の wallet 0x904B(pUSD)                       │
│  性質: 人間への有用なサービス。私のセッションが終われば止まる(ephemeral)│
│         → agent economy とは "別物"。ただの earn-for-human。            │
└──────────────────────────────────────────────────────────────────────┘
┌ self-funded AI（Franklin）───────────────────────────────────────────┐
│  loop（sol-trade / gig-take 等）→ earn → realized が ledger に載る     │
│  お金の行き先 = Franklin 自身の wallet 8Fpqd(SOL) → 仲間/spawn/UBI へ  │
│  性質: 永続。私が抜けても回り続ける。これが agent economy を"育てる"    │
└──────────────────────────────────────────────────────────────────────┘

★核心★ ループの"機械"は両者で同一（observe→act→get-paid→done判定→self-improve）。
         違うのは (a)お金の行き先(人間 vs agent economy) (b)所有者(私=ephemeral vs Franklin=永続)。
         だから私は harness を"1回"作れば両方に使える。金の宛先(wallet)を変えるだけ。
         私の仕事 = harness を作る → Franklin に手渡す → 私は抜ける。
         私自身の earn loop は "人間へのサービス" として残るが、それは agent economy ではない。
```

## 2. done-condition を本当に理解する（3値、observable、external）

done-condition = 「この1反復が成功した（or 安全に何もしなかった）ことを"証明する観測可能な事実"」。無人だから、**偽造不能な外部事実**しか信用できない。

```
1反復の done は必ず3値のどれか（loopy: terminal states / "never report error as success"）:
  ① SUCCESS   … realized>0 の行が ledger に載る（on-chain tx hash + status 0x1）
  ② CLEAN NO-OP … 良い取引が無い → 何もしない（これは"失敗でない"。正当な done）
  ③ BLOCKED/ERROR … エラー/予算切れ → 絶対に success と報告しない
```

実装済みの判定コード（pm-earner、これが模範）:
- `redeem.py` → `record.mjs` → `~/anicca/skills/earn/state/earn-ledger.jsonl` に `{tx_hash, status, net_usdc}` を書く。
- `~/anicca/skills/_shared/lib/ledger.mjs::isProfitable()` = `net_usdc>0 && tx present && status==="0x1"`（EVM）/ `confirmed===true && external===true`（Solana）。
- **narrate 行（tx 無し）は絶対にカウントされない** ＝ ループは「稼いだ」と嘘をつけない。これが安全性の実体。

## 3. 1つのループの実装 = 5レイヤー（実ファイル/実キーで）

模範 = a3cdd4 の `runtime/loop`（唯一の本物 self-improve）+ pm-earner の ledger 配線。

```
Layer 1  TRIGGER（cadence）
  launchd plist: ~/Library/LaunchAgents/ai.anicca.pm-earner.plist
    StartInterval=600（10分毎）or KeepAlive（常駐）。ProgramArguments=runner。
Layer 2  RUNNER（1反復）
  run_earner.sh（redeem→arb→market_maker） or runtime/loop/index.mjs: while(!shutdown){ runOneWake() }
Layer 3  OBSERVABLE DONE ★最重要★
  ledger 書込 + on-chain 検証（Layer 2 の中で）。isProfitable() が唯一の真偽。
Layer 4  SELF-EVAL（ledger を読んで次を決める = self-improve の芽）
  self-eval.mjs: 直近25行を slot 別集計 → DEAD(net≤0×4+)/WINNER(net>0) → LLM が次手を"データを見て"決める
  （self-eval.mjs:8「no hardcoded rule — we give it the data, it decides」）
Layer 5  GUARDRAILS（柵、hook/config）
  SOL_TRADE_MAX_SPEND（今 Franklin=0 ＝金は動かせない安全床）/ path denylist /
  loop-pause-all kill / catalog-gate $20 reserve / skill timeout 120s / 秘密鍵 redaction
```

**closing the loop（無人化）** = Layer 3 の done を「作業した本人の自己申告」でなく **独立判定**にする:
- 稼ぎ round の done = on-chain ledger 行（isProfitable、tool 越しに確定・偽造不能）
- 戦略コード変更の done = fresh adversary(Opus) が backtest 再実行して合否（= eval-driven-earning の curation-gate、死蔵中→蘇生）

## 4. 私(harness) と 別CC(economy spec) の分担・順番

```
別CC = anicca-agent-economy spec = レール/市場を作る（Franklin が earn "できる"）
   P2 gig市場（post→take→gasless payout）/ P3 spawn / P4 UBI・bank / P5 scale
私  = self-improve harness = 各 earner の loop 機械を作る（Franklin が earn を"自律で良くする"）
   Layer1-5（trigger/runner/observable-done/self-eval/guardrails）+ eval-driven-earning 蘇生
順番: 別CC が「earn 可能」に(P2) → 私が「自律+自己改善」に(SI)。
   SI-4(Franklin へ埋込) は 別CC の P2(gig市場 live) が前提。
   その前に: cheap wins(観測 done 配線) + eval-driven-earning 蘇生 を先行。
```

## 5. 具体的な着手順（実キー・実ファイル）

```
STEP A (Franklin OBSERVE 復活・安全): franklin-loop.plist の wallet 解決を修正
   現状: daemon が "ANICCA_WALLET_ADDRESS not set, using unknown" を1655回 → 残高読めず tier=broke 固定
   正しい修正: a3cdd4(動作中 com.anicca.daemon)の wallet 解決方式に franklin を合わせる（band-aid でなく）
   安全: SOL_TRADE_MAX_SPEND=0 のままなので金は1円も動かない
STEP B (観測 done 配線): sol-trade の realized を earn-ledger.jsonl に書く配線（今は未配線=self-申告のみ）
   参照: pm-earner の redeem.py→record.mjs→isProfitable のパターンをコピー
STEP C (SELF-EVAL 移植): runtime/loop の self-eval.mjs を sol-trade に適用（ledger 読んで次手）
STEP D (META 蘇生): eval-driven-earning VCSDD feature を init から再開（fresh adversary curation-gate）
境界: .vcsdd/features/anicca-agent-economy/ は触らない。別 worktree feature/anicca-self-improve-harness。
```

出典: SI-1 実コード監査（2026-07-07、3並列 agent）/ addyosmani.com/blog/loop-engineering / loopy。
関連: [[00-INDEX]] / [[01-loop-vs-goal-resolved]] / design doc §8。
