# 18 — Status-Quo Audit (2026-07-11 03:00 JST / 18:00 UTC)

RULE #0 準拠: 全項目を生ログ・on-chain RPC・plist・state.json の一次証拠で検証した。自己報告・記憶は一切使っていない。

## A. 検証結果サマリ（全て fresh evidence）

| # | 項目 | 検証方法（一次証拠） | 結果 |
|---|---|---|---|
| A1 | Franklin regression fix が autonomous wake で維持されるか | `~/.blockrun/skills/earn/state/sol-trade.trace.jsonl` 生ログ | ✅ **HOLDS**。identity-mismatch skip は 07-10T12:53Z が最後。以降 14:04 / 14:38 / 15:30 / 16:11 / 16:55 / 17:23 UTC と **6連続 autonomous live-pass**（人手介入なし、~40-50分間隔） |
| A2 | Franklin は稼いでいるか | 同 trace + Solana RPC | ❌ **全 live-pass が WAIT**（TradingSignal neutral 0% conviction、edge が往復 fee ~0.4% を超えない）。取引ゼロ |
| A3 | Franklin wallet 実残高 | Solana mainnet RPC `getBalance`/`getTokenAccountsByOwner` | SOL **0.01997** / USDC **$13.02**（8Fpqd…PCV9） |
| A4 | ★新発見★ USDC が漏れている | RPC `getSignaturesForAddress` + `getTransaction` | **$13.18 (07-10 14:04) → $13.02 (07-11 03:00 JST) と ~$0.16/日 減少**。直近 tx (4Fx45kLA…) = USDC **-$0.0086** の micropayment（x402 型、推論/シグナル課金）。WAIT し続ける限り**構造的に純減** — always-act の必要性を on-chain が裏付け |
| A5 | deployed run.sh に $ANICCA_REPO fix があるか | `~/.blockrun/skills/earn/sol-trade/run.sh:35` を Read | ✅ `WADDR="${ANICCA_REPO:-…}/runtime/wallet-address-solana.mjs"` 実配備済み |
| A6 | self-heal healthcheck | `launchctl list` + plist + `earning-health.py is-barren 20` 実行 | ✅ `ai.anicca.sol-trade-earning-healthcheck` loaded (last exit 0)、is-barren=**false**（live-pass を正しくカウント）。healthcheck out log も false 連続 |
| A7 | sol-gate genome 進化 | `sol-gate.trace.jsonl`（全6行） | ✅ 動作中。16:54Z に genome 177c0bc4→**723d9bbc**（MIN_CONVICTION 6→5 に自己緩和）。conviction 5.88/5.30 到達も momentum <2% で skip 継続 — **gate は生きているが act には届かない** |
| A8 | claude-p pm-earner | `earner.log`（15,533行）実 tail + launchctl | ✅ **稼働 + 実効**。07-10T18:00Z（監査の数分前）に resolved 勝ちポジションを **autonomous redeem: $5.00 回収**（tx `0x20ee0c4e…` status 0x1、pUSD 1.55→**6.55**）→ 直後 UFC 329 bundle に maker 2 legs 配置（1% lock狙い）。10分毎に休まず pass |
| A9 | claude-p-mainloop | `~/.openclaw/logs/claude-p-mainloop.out.log`（launchd の .out.log とは別ファイル） | ⚠️ 07-09T23:29Z と 07-10T06:00Z の run は完遂（self-improve-real-ledger Phase5-6 完了、PR #937 merge 等）。**直近 07-10T12:38Z の run は 3600s hard timeout で kill (exit 124)、成果まとめ無し** — 作業が中途で消えた可能性。次 fire は 18:38Z |
| A10 | franklin-loop 本体 | `~/.blockrun/logs/daemon.err` | ⚠️ 稼働中（PID 76744）だが **THINK が ClawRouter free model 429 (`FREE_MODEL_FAILED`) で連続失敗**する時間帯あり。earn slot 自体は wake 毎に回っている（trace が証拠）ので致命ではないが wake の一部が空振り |
| A11 | Franklin #2 | `~/.franklin2-home/.blockrun/logs/daemon.err` + earn-ledger | ❌ **walletless で空回り**。`ANICCA_WALLET_ADDRESS not set → wallet "unknown" → tier=broke`、gig は `no-signing-key`、sol-trade trace は空。cook/explore だけ回して earn 経路ゼロ |
| A12 | Franklin (Base側) earn-ledger | `~/.blockrun/…/earn-ledger.jsonl` tail | 全行 net_usdc=0（gig observe / x402-serve up / token-launch FRK / hl-fund-skipped / yield hold）。**wallet 0x3ecc… は balance $0.02 = bootstrap 資金なし** |
| A13 | citizens.json | `~/.franklin2-home/.hermes/state/citizens.json` | seed のみ（Franklin 1 entry）— witness②（autonomous spawn）未達のまま |
| A14 | dashboard vs reality | `curl https://aniccaai.com/dashboard.json` | ❌ **updated_at = 2026-06-05（35日 stale）**。Franklin残高もFranklin#2も実態と乖離。dashboard real-time 化は未着手 |
| A15 | VCSDD state | `~/anicca/.vcsdd/features/*/state.json` | ⚠️ **重大な乖離**: franklin-alwaysact-skill-router / franklin-earn-coldstart-evolution とも spec ファイル + iter1 findings 5件 + fix commit (687ede7 / a386bee) は disk に実在するが、**state.json は両方 `currentPhase: "init"`, phaseHistory 空** = 実コマンドで phase が進んでいない（CLAUDE.md 違反状態）。次 session は `vcsdd-spec`→`vcsdd-spec-review` を実コマンドで叩いて state を進めながら iter2 へ |
| A16 | ディスク | `df -h /`（cleanup subagent 実行） | ⚠️ session 中に ENOSPC 発生 → 許可済み cache + 旧 scratchpad ~1.0GiB 回収して **2.2Gi free (83%)**。残る大物は全て Dais 承認要（claudevm ~7G / ~/Library 17G / colima 2G / ~/.openclaw/.git 2G / HF系cache 1.6G）。**2.2Gi は依然危険水位** |

## B. 一行結論

**インフラ層は全て生きて自己修復まで揃ったが、経済層は「claude-p の PM redeem $5.00」以外ゼロ。Franklin は WAIT し続けながら x402 micropayment で ~$0.16/日 出血しており、always-act (VCSDD #1) が唯一のクリティカルパス。**

## C. 異常・注意（fix していない、記録のみ）

1. **Franklin USDC 出血**（A4）— WAIT でも推論/シグナル課金が発生。always-act 設計に「コスト < 期待収益」の会計を組み込むべき根拠。
2. **Franklin2 walletless**（A11）— spawn-identity は「fail-closed で漏洩しない」方向には正しく倒れているが、earn 不能。identity 付与 or 停止の判断が必要。
3. **claude-p-mainloop timeout**（A9）— 3600s で作業が切り捨てられた。プロンプトにチェックポイント/こまめ commit の規律が要るかも。
4. **VCSDD state.json 未進行**（A15）— spec 本文だけ進んで state が init のまま。次 session の最初に実コマンドで正規化する。
5. **ClawRouter free 429**（A10）— free tier 逼迫。wake 空振り率が上がると healthcheck の is-barren 窓に影響しうる。
6. **dashboard 35日 stale**（A14）— TODO #3 のまま。
7. **ディスク 2.2Gi**（A16）— Dais 承認待ちの大物リスト付き。

## D. 残 TODO（順序つき、handoff の ORDERED TODO を検証済み事実で更新)

| 順 | タスク | 状態（本監査時点の evidence） |
|---|---|---|
| 0 | status-quo audit → 18.md | ✅ 本ファイル |
| 1 | **Franklin always-act**（franklin-alwaysact-skill-router）: `vcsdd-init`済 state を実コマンドで spec/spec-review へ進め、**fresh Opus 4.8 adversary で spec-review iter2**（687ede7 を re-review、re-fix しない）→ tdd → impl → adversary → harden → converge → live 配備 → autonomous wake で「WAIT でなく ACT」を trace で確認 | spec+fix は commit 済み、state.json init のまま（A15）。**これが最優先** — 出血(A4)を止め、witness①(autonomous profit) への唯一の道 |
| 2 | **self-improve edge**（franklin-earn-coldstart-evolution）: iter1 fix (a386bee) を同様に iter2 re-review から | state.json init のまま。#1 完了後 |
| 3 | **dashboard real-time 化**: per-tool logs + full ledger + Franklin #1/#2 掲載 | 35日 stale を確認（A14） |
| 4 | **surplus → loan/job-post**（real USDC、on-chain verify） | 未着手。原資は Franklin $13.02 + claude-p pUSD $6.55 |
| 5 | **autonomous spawn**（witness②、RPC-verified） | citizens.json seed のみ（A13）。Franklin2 walletless 問題(A11)の解決を内包 |
| 6 | **記事 2本** | 未着手 |
| - | (随時) claude-p-mainloop timeout 規律 / ClawRouter 429 対策 / ディスク大物回収（Dais 承認） | C-3/5/7 |

## E. 検証コマンド再現メモ

```bash
# Franklin trace / ledger
tail -30 ~/.blockrun/skills/earn/state/sol-trade.trace.jsonl
cat ~/.blockrun/skills/earn/state/sol-gate.trace.jsonl
# on-chain
curl -s https://api.mainnet-beta.solana.com -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"getTokenAccountsByOwner","params":["8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9",{"mint":"EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"},{"encoding":"jsonParsed"}]}'
# claude-p
tail -60 ~/anicca/skills/earn/polymarket-trade/earner.log
tail -60 ~/.openclaw/logs/claude-p-mainloop.out.log   # launchd の .out.log とは別
# 健康
python3 ~/anicca/skills/self/earning-health.py is-barren 20 ~/.blockrun/skills/earn/state/sol-trade.trace.jsonl
bash ~/anicca/skills/self/colony-status.sh
# VCSDD
cat ~/anicca/.vcsdd/features/franklin-alwaysact-skill-router/state.json
```
