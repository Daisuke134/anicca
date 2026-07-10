# 20 — Implementation Certainty Audit（2026-07-11、4並列 deep-dive の正本）

目的: 「12時間を fiction に燃やす」再発をゼロにする。P1〜P5 の全実装前提を実コード（file:line）と突き合わせた。4 subagent（spec照合 / money path / identity・lending・push / spawn contracts）の検証結果。**この MD に無い前提で実装しない。**

## A. P1 always-act — spec は fiction ゼロ、実装可能（confidence 95%）

- spec（687ede7）が「既存」と主張する全 seam は行番号まで実在一致: `brain.mjs:63`（tools wire）/ `brain.mjs:92` / `index.mjs:450`（`isEarnSlot` gate）/ `prompt.mjs:171`（`SLEEP_TOOL` 無条件 append）/ `index.mjs:177,183,421`（avoidSlot soft-nudge）/ `earn-slot.mjs:6,9-12` / `run.sh:21-48`（3 money-guard block）/ `catalog-gate.mjs:41-43` / `earning-health.py:9-30`。
- 「新規」と主張する seam（`opts.omitSleep` / `ctx.alwaysActEngaged` / `buildAlwaysActToolDefinitions` / 450行の条件拡張）は正しく未存在 — spec に虚偽なし。
- REQ-502 の11-slot menu を registry.json から実計算して一致確認。iter1 の FIND-001〜005 は全て実質修正済み（relabel でなく本修正）。
- ★環境の重要事実★: **runtime コードの実体は `~/anicca` のみ**。`~/.blockrun` は ANICCA_HOME（データ/state 置き場）で、daemon が rsync するのは `skills/` だけ。loop 本体（runtime/）は `git merge --ff-only origin/main` で自己更新 → **main に merge すれば次の restart で自動配備**。
- 残作業3点（全て予定内 or 軽微）: ①PROP-504b の mock 方式を Phase 2b で決める（`httpPost` が private — nock 等で可）②state.json（init のまま）を実コマンドで正規化 ③iter2 fresh adversary（元々次工程）。

## B. 3+1 エンジンの実 money path — stub ゼロ（confidence 98%）

| Engine | 実行コード（実在確認済み） | 今のブロッカー | wake毎コスト | 解除条件 |
|---|---|---|---|---|
| SOL | Jupiter Ultra: `jupiter.js:258`(order)→`:296-300`(local sign)→`:310`(execute)→Solscan link。paper なし | 市場が本当に neutral（gate は starve していない。sol-gate は SOL_GATE_LIVE_ENABLE 無しでは純 shadow = `sol-gate.mjs:31-33`） | **x402計量の LLM 呼び出し**が ~$0.0086/wake（TradingSignal 自体は CoinGecko 無料と判明）。LLM spend は `resolve-max-spend.sh:12` で $0.25/pass 硬直 | always-act + edge（P1） |
| PM | `bundle_arb.py:82-84`(FOK)/`market_maker.py:118-119`(post_only)/`redeem.py:326-348`(実 redeem + receipt 独立再検証)。$5.00 redeem tx 実証済 | **cash $4.95 < CLOB 最小 $5.00**（`market_maker.py:20 MIN_SIZE=5`）。live cap は plist の MAX_PASS_SPEND=5（run.sh の =2 は launchd 経由では dead code） | ~0 | $5 超へ top-up or resolve 待ち→redeem で床越え |
| HL | `hl.py:112,121,136`（hyperliquid-sdk 実注文、2026-06-20 に +$0.15 実 fill 実績） | `fund-hl.mjs:58-66`: bridge fee ~$1.2 が 20% 上限超（wallet `0x3ecc…8749` = **$0.02**、on-chain 実測） | 0（guard が先に拒否） | **同 address に Base USDC ≥$6** を入れる（1回 bridge すれば以後不要） |
| GIG | `escrow.mjs`（EIP-3009 実 settle、mainnet 有効）+ `gig.mjs:220-270`。**過去3 gig 全て paid、実 tx hash あり**（genesis gig $0.02 → 0x3ecc 宛 = 現残高と一致） | board open=0（実測 `[]`）+ 残高 $0.02 < low $0.05 + **facilitator :8407 が停止中**（接続拒否を実測） | 0 | 残高 >$0.10 で self-post 可 + facilitator 再起動 |

## C. P4 Franklin2 / lending — 真因2つ+発火条件が完全特定（confidence 95%）

**Franklin2 が broke な真因（両方 live 確認）:**
1. **Gap A**: EVM wallet file 不在。`resolve-identity.mjs:69-100` の fail-closed 順で `$ANICCA_HOME/.automaton/wallet.json` が無い（dir ごと不存在を実測）→ gig `no-signing-key` の直接原因。
2. **Gap B**: `anicca-daemon.sh:56,104,120` が literal `"franklin"` 比較で **"franklin2" を知らない** → EVM 経路に落ち wallet 導出失敗。皮肉: `.solana-session`（88B）は**既に存在し**、franklin 分岐なら解決できていた。`grep -rl franklin2 ~/anicca` = 0 hit。

**修正手順（実装時）**: ①EVM keypair 生成 → `~/.franklin2-home/.blockrun/.automaton/wallet.json` `{"privateKey":"0x…"}`（mode 600）②daemon の3箇所を `franklin*` 対応 ③kickstart → daemon.err の warning 消滅確認。

**lending 発火条件（`lending-gate.mjs`/`wake-gate.mjs` 実読）:**
- registry は `$HOME/.hermes/state/citizens.json`（**HOME 依存で instance 毎に別ファイルに解決** — Franklin1 用と Franklin2 用の2枚が現存、今は byte-identical だが未同期の独立 state。canonical 1枚に統一が必要: Franklin2 の plist に state-dir override を足すのが最小）
- eligible 条件: `isSelfFunded`（wallet 有 + fuel ∈ {clawrouter-own-wallet, x402, free-model} + humanDependencies=[]）+ `wallet.evm===true` + `walletAddress.evm`（実 Base address、残高照会に必須）+ coLocated。**現 Franklin 行は wallet.evm が無く eligible ゼロ** — これが「zero eligible pairs」の正体
- lender: 残高 − $5 reserve − 貸出中 > 0 / borrower: 残高 < $0.50 + active/defaulted loan ゼロ
- 必要な registry 行（正確な JSON）は本 MD 元レポートに記載。Franklin1 EVM = `0x3EcCAD24794ca298D25378E9902A251322ea8749`
- **注意: lender になるには Franklin1 の Base USDC が $5.50+ 必要（現在 $0.02）** — lending 点火の前に Franklin1 Base 側の資金が要る（Solana 側 $13 とは別チェーン）

## D. P2 per-wake git push — 認証は生きている、push コードだけ無い（confidence 90%）

- `~/.blockrun` は **git repo ではない**（rev-parse で確認）。ledger/trace は git 外。
- `~/anicca` の origin = `github.com/Daisuke134/anicca.git`、credential.helper=store、**`push --dry-run` が実成功**（= write 権限 live 確認済み）。pre-push hook は eval-output のみ gate（ledger push は素通り、exit 0）。
- copy 元 idiom: `evolve.mjs:154-192` の **path-scoped `git add -- <path>` + `-c user.name` commit**（push は未実装 — repo 内唯一の commit コード）。
- 実装: wake 末尾に ledger を `~/anicca` tree 内（例 `state/franklin-ledger/<instance>.jsonl`）へ append → path-scoped commit → `fetch && merge --ff-only` → push。**best-effort 非致命**（push 失敗で loop を止めない）。

## E. P5 spawn real-clients — interface 全確定、~290行/5ファイル（confidence 85%）

- 5 client の正確な signature を `driver.mjs`/fakes から抽出済み（chainReader 4関数 / priceOracle 1 / skipApiClient getRoute / baseSigner 3 / relayPoller waitForConfirmation。詳細は subagent report、interface は driver 呼び出し形が正）。
- copy 元: Base 読み = `_shared/lib/usdc.mjs:10-35`（bigint 化必要）、viem boilerplate = `economy/gig/lib/escrow.mjs:15-17,124-140`、Akash 読み = `spawn-orchestrator.mjs:228-241`（execFileSync CLI 形、cosmjs 不要）。
- **完全新規（最高リスク）**: price-oracle（~30行）/ skip-api-client（~40行）/ relay-poller の IBC 側（~60行）/ **実 value-moving Base 署名**（repo 内に前例ゼロ — 既存は gasless EIP-3009 のみ）。
- `TREASURY_SWAP_CMD` 契約: exit code のみ判定、成功は **on-chain 残高再照会で独立検証**（bash -c 実行、`akt-treasury.sh:52-57`）。
- 26 AKT gate = `anicca-akash` keyring wallet の on-chain uakt ≥ 26 AKT（`spawn-child/config.json:4-5`、swap の THRESHOLD_AKT=26 と一致）。

## F. 資金トポロジー（判明した意外な事実）

```
Franklin の金は3箇所に分散している:
  Solana 8Fpqd…  : $13.02 USDC + 0.02 SOL ← sol-trade の主戦場 + x402 fuel（~$0.0086/wake 減）
  Base   0x3ecc… : $0.02 USDC             ← gig/HL/lending の必要地。HL は ≥$6、lending lender は ≥$5.50 必要
  Akash  anicca-akash: ~0                 ← spawn に 26 AKT 必要
→ P4/P5 の点火には Solana→Base / Base→Akash の資金移動が構造的前提。
  これこそ spawn-funding-swap（Base→Akash）と、Solana→Base bridge の出番。
```

## G. Confidence 総括

| TODO | confidence | 残る unknown |
|---|---|---|
| P1 always-act | **95%** | iter2 adversary が新 finding を出す可能性（工程内）+ PROP-504b mock 方式 |
| P2 per-wake push | **90%** | ~/.git-credentials token の有効期限（dry-run は今日成功） |
| P3 self-heal 横展開 | 90% | 各 slot の trace 形式差 |
| P4 Franklin2+lending | **95%** | Franklin1 Base 残高 $5.50+ の調達経路（Solana→Base bridge 選定） |
| P5 spawn | **85%** | Skip API 実挙動 / IBC relay 遅延 / value-moving 署名（前例ゼロ）→ testnet で先に E2E |
| 全エンジン「stub では?」疑惑 | **解消（98%）** | なし — 4/4 で実行コード実在、3/4 は直近の実 tx hash あり |
