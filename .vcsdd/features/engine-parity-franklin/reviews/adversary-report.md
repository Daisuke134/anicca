# Adversary Report — engine-parity-franklin (#23 スコープのみ)

Fresh-context, read-only 検証。対象 = `.vcsdd/features/engine-parity-franklin/specs/spec.md` の DONE 1–6。
検証時刻: 2026-07-04 21:59:52Z 前後（実ログ・実プロセス・実 launchctl 状態を直接読んだ）。

## 総合判定: **PASS**（DONE 1–6 全て PASS）

| # | 条件 | 判定 | 根拠 |
|---|---|---|---|
| 1 | full loop が回り、sol-trade 以外の slot が invocable として catalog に現れる | **PASS** | `~/.blockrun/logs/daemon.err:5` — `[loop] live skills: report, self/spawn, self/spawn-child, self/issue-dev, self/coordinate, economy/ubi, cook, yield, hl_trade, x402_sell, token_launch, earn/gig, earn/clip, earn/clip-producer, earn/video, earn/bounty, earn/sol-trade, earn/polymarket-trade` — sol-trade 一本足ではなく automaton と同じ 17-slot catalog が実際に load されている。 |
| 2 | BlockRun 燃料で THINK 成功（実 wake ログ） | **PASS** | `~/.blockrun/state/ledger.jsonl` の narrate/wake エントリに自然文の判断結果（例: `"WAIT — SOL TradingSignal is neutral (33% confidence)..."`）が実在。`~/.blockrun/franklin-stats.json` の `history` 末尾 `lastRequest:1783202189771`(ms) は検証時刻とほぼ同時刻 — 実 HTTP リクエストが直近まで継続。`ai.anicca.franklin-loop.plist` に `OPENAI_BASE_URL` は daemon.sh 内で `http://127.0.0.1:8403/v1`（franklin proxy）に固定されており、経路は仕様通り。 |
| 3 | sol-trade は full loop 経由でも動く（Solana 残高を読み判断） | **PASS** | ledger.jsonl の wake エントリ全件が `slot:"earn/sol-trade"` で、result に `wallet USDC $1.27/$1.30/$1.41/$1.44 insufficient` 等、実際の Solana wallet 残高を読んだ具体的判断が出ている。 |
| 4 | telemetry-post-franklin 継続 → dashboard alive | **PASS** | `~/.blockrun/logs/poster.log` 最終行 `2026-07-04T21:59:27.719Z Franklin net ... -> 202 {"ok":true}` — 検証時刻(21:59:52Z)の25秒前まで 202 応答が継続。プロセスツリー確認で `sleep 120`(PID 46751, PPID 36887=anicca-daemon.sh) が生存 — one-shot post→sleep 120 ループが正しく回っている。 |
| 5 | 我々の Mac Mini で crash せず回る(§38 works-here) | **PASS** | `launchctl list ai.anicca.franklin-loop` → `PID=36830, LastExitStatus=0`。daemon.err に fatal error なし（`ANICCA_WALLET_ADDRESS not set`/`Balance fetch failed — keeping tier=broke` の WARNING のみ、非致命）。self-update/skills-sync/proxy起動/loop起動のログが1回のみ = daemon.sh の再起動（＝クラッシュ）が発生していない。 |
| 6 | 旧 plist が退避されロールバック可能 | **PASS** | `~/Library/LaunchAgents/ai.anicca.franklin-sol.plist.disabled` 現存、中身は旧 `skills/earn/sol-trade/run.sh` 直叩き構成そのもの。`launchctl list \| grep ai.anicca.franklin-sol`（`.disabled` なしの旧ラベル）は該当なし = 正しく unload 済みで、rollback は「新 unload → `.disabled` を `.plist` にリネームして load」で即座に可能。 |

## §38 works-here の実体確認
- `ai.anicca.franklin-loop.plist` の EnvironmentVariables: `ANICCA_HOME=/Users/anicca/.blockrun`, `ANICCA_INSTANCE=franklin`, `ANICCA_BRAIN=proxy`, `FRANKLIN_PROXY_PORT=8403` — spec R1/R3 の設定と一致。
- R6 の tier=broke は **設計通り、非致命** と確認: `~/anicca/runtime/anicca-daemon.sh` のコメント（"ANICCA_WALLET_ADDRESS unset for Franklin is correct — the loop just keeps tier=broke, non-fatal"）通り、balance.mjs が `0x`-EVM アドレスしか受け付けないため Solana wallet の Franklin は意図的に tier=broke。バグと誤認しないこと、を確認した。

## 追加深掘り: PM(earn/polymarket-trade) は catalog に出ているか
**出ている。** `daemon.err` の `live skills` 行に `earn/polymarket-trade` が明記され、catalog（invocable リスト）には含まれる。

ただし **ledger.jsonl 5件の wake は全件 `slot:"earn/sol-trade"`** のみで、PM/HL が実際に選ばれて実行された記録はまだゼロ。理由をコードで確認:
- `~/anicca/runtime/loop/index.mjs:184-196` の tier 計算は EVM アドレス前提（`ANICCA_WALLET_ADDRESS`）で、Franklin は unset → tier=broke 固定。ただし本文コメント通りこれは non-fatal で slot 選択自体をハードコードで塞ぐものではない。
- 同ファイル 208行目のコメント「no hardcoded 'avoid hl_trade' rule; we give it the money signal, it judges」から、PM/HL が呼ばれていないのは **hardcoded gating ではなく、モデル自身が資金状況（EVM資金ゼロ）を見て sol-trade のみを選び続けている自律判断** である可能性が高い。
- `loop_detect` エントリ（`ledger.jsonl` 最終行、`slot:"earn/sol-trade", streak:1`）は同一 slot の繰り返し選択を検知する多様化機構だが、streak がまだ 1 = 検知され始めたばかりで、強制的な slot 切り替えはこれからの段階。

結論: 「Franklin が全スキルを持つ（invocable）」という DONE 条件の核心は満たされている（catalog に PM/HL とも掲載）。「実際に選ばれて動く」段階はまだ sol-trade 一本に留まっており、これは EARN-3(#15, capital-gated)側の課題であって #23 のスコープ外（spec の非-goal 注記通り）。

## Confirmed findings（要フォロー、DONE 判定には影響しない）
- franklin-stats.json の直近リクエストは `openai/gpt-5-mini`（有料、1件あたり ~$0.009）が多数使われており、franklin proxy 起動フラグ `--model nvidia/llama-4-maverick --no-fallback`（free モデル固定の意図）と実際のモデル使用実績が食い違っている。THINK 自体の成立（DONE 2）には影響しないが、コスト面で確認価値あり。
