# Purity Boundary Audit — claude-p-loop-verification (Phase 5, formal hardening, mode: lean)

verification-architecture.md の Purity boundary map（Tier 1 = 純関数/単体テスト可、Tier 2/3 = 副作用境界）
に対して、実装済みファイルが実際にその宣言と一致しているかを grep + Read で監査した。

## Declared Boundaries

（Tier 1 と宣言されたファイルの I/O grep 結果）

`open(|urllib|requests\.|subprocess|readFileSync|writeFileSync|fetch\(|os\.stat|os\.path\.exists|execSync|child_process`
で全ファイルを検査（ファイル/ネットワーク/プロセスI/Oを表す代表的な呼び出しパターン）。

| ファイル | 宣言（verification-architecture.md） | grep結果 | 判定 |
|---|---|---|---|
| `skills/self/cadence.py`（`cadence_met`/`streak`） | Tier1純粋、I/Oなし | I/O呼び出しゼロ | 一致 |
| `skills/self/loop-scale/guardrails.py`（`scale_eligible`/`cooldown_ok`/`fleet_at_capacity`/`is_ban_suspected`） | Tier1純粋 | I/Oゼロ | 一致 |
| `skills/self/self-improve/lib/weekly_compare.py`（`beats_previous_week`） | Tier1純粋 | I/Oゼロ | 一致 |
| `skills/self/openclaw-migrate/migration_gate.py`（`channel_migration_eligible`） | Tier1純粋 | I/Oゼロ | 一致 |
| `skills/_shared/lib/ytdlp_parse.py`（`parse_ytdlp_json`） | Tier1純粋 | I/Oゼロ | 一致 |
| `skills/earn/polymarket-trade/positions.py`（`parse_positions_response`） | Tier1純粋 | I/Oゼロ | 一致 |
| `skills/earn/clip-promote/clip-promote-status.mjs`（`clipPromoteStatus`） | Tier1純粋 | I/Oゼロ | 一致 |
| `skills/self/founder-loop/report-args.mjs`（`founderReportArgs`） | Tier1純粋 | I/Oゼロ | 一致 |
| `~/profitable-claude/.../gig/funnel.py`（`summarize_gig_funnel`） | Tier1純粋 | I/Oゼロ | 一致 |
| `~/profitable-claude/.../bounty/funnel.py`（`summarize_bounty_funnel`） | Tier1純粋 | I/Oゼロ | 一致 |
| `skills/report/loop-report.sh` 内 `lr_valid_evidence()` | Tier1純粋（"`--<flag>`引数で直接呼べるパターン"） | 文字列判定のみ、I/Oゼロ | 一致。かつ実際に `--valid-evidence` フラグで直接呼び出し可能な形（`if [ "${1:-}" = "--valid-evidence" ]; then lr_valid_evidence "${2:-}"; exit $?; fi`）で実装されており、`hrl_classify`/`sf_should_continue` の既存パターンを正しく踏襲している |

**判定: Tier 1 と宣言された全10ファイルについて、宣言と実装が完全に一致している。新しい I/O 呼び出しの
混入は無い。**

## `cadence-evidence.py` — 唯一の impure モジュールとしての境界確認

verification-architecture.md は「cadence.py 自体は一切ファイルに触れない、全ての実mtime/jsonl読み取りは
呼び出し元（`verify-loops.sh`/`verify-loops-audit.sh`/各loopのhealthcheck.sh）の責務」と明記している。
実装は `cadence-evidence.py` という専用モジュールにこの責務を集約しており（`cadence.py` を import して
`cadence_met`/`streak` を呼ぶ側）、`os.stat`/`open`/`zoneinfo` 等の実ファイルアクセスはこのファイルにのみ
存在することを確認した:

```
$ grep -c "os\.\|open(" skills/self/cadence.py            → 0
$ grep -c "os\.\|open(" skills/self/cadence-evidence.py    → 12 (意図通り、境界を担う唯一のファイル)
```

境界は宣言通り正しく1ファイルに集約されている。**一致。**

## `ledger_metrics.py`／各 loop `evaluator.py`（REQ-LV-110）— 用語の整合性に関する注記（non-blocking）

`skills/self/self-improve/lib/ledger_metrics.py` の docstring は「Pure: reads a jsonl ledger file
(read-only) and returns a combined_score float」と書かれており、`load_ledger_rows()`/
`evaluate_stage1_generic()` は実際に `open(ledger_path)` を呼ぶ——**厳密な意味での純関数（出力が引数のみに
依存する）ではない**（ファイルの中身という外部可変状態に依存する）。verification-architecture.md の
REQ-LV-110行も「fixture/ledger読み取り→combined_score返却のみ、I/O副作用なし（新設・純粋）」と同じ用語を
使っている。

これは実装のバグではなく、**このコードベース全体の既存慣習**（Ground truth に明記された
`~/anicca/skills/earn/self-improve/evaluator.py` の `evaluate_stage1()`/`evaluate_stage2()` が同じ
「読み取り専用I/O＝pure」という語法を既に採用しており、この feature はそのパターンを copy+tweak しただけ）
と一致している。実際に PROP-LV-023 が検証しているのも「同一入力（＝同一ファイル内容）→同一出力
（決定論性）」と「発注/投稿系モジュールを一切importしない（sandbox境界）」の2点であり、「引数のみに依存する
関数」という厳密な純粋性は最初から要求されていない。監査で確認したのはこの sandbox 境界が実際に守られて
いるか、の1点:

```
$ grep -n "^import\|^from" skills/self/self-improve/{clip,affiliate,video,gig,bounty}/evaluator.py
→ os, sys, ledger_metrics（内部の lib）のみ。post/apply/dispatch/execution系モジュールのimportはゼロ
```

**判定: sandbox 境界（LLM judge不使用・発注/投稿モジュール非import）は5 loop 全てで守られている。
「pure」という語がこの feature 内で厳密な純粋性ではなく「read-only・no-write-side-effect・no-execution-
import」を意味する用語として一貫使用されていることを記録として明示する（deviation ではなく、既存慣習との
一致）。**

## Observed Boundaries

（副作用境界を持つファイル Tier 2/3 の越境チェック）

以下は元々 Tier 2/3（副作用境界）と宣言されているため、I/O を含むこと自体は仕様通り。監査対象は
「宣言されていない種類の副作用（例: 純粋関数境界の呼び出し元が判断ロジックを持ってしまっていないか）」。

- `skills/report/loop-report.sh`（本体、`lr_valid_evidence` を除く部分）: mail送信・ログ書き込み・
  `.env` self-resolve。Tier2として宣言通り。判断ロジック（evidence が有効か）は `lr_valid_evidence` に
  完全に切り出されており、本体は「呼ぶだけ」——判断とI/Oの分離は守られている。
- `skills/earn/video/record_earn.py`: `is_real_usdc_inflow`（純粋スキーマゲート）と `record_earn`
  （ファイルI/Oを行うオーケストレータ）が明確に分離されている。`onchain_check` 注入シームも無改変
  （PROP-LV-009で確認）。判断（スキーマ妥当性）とI/O（ファイル追記）の分離は既存設計のまま維持。
- `skills/earn/video/onchain.py`: 全体が意図通り Tier2/3（実RPC呼び出し）。ログフィルタ部分
  （`confirm_usdc_inflow`内のTransfer log条件判定）は関数内にインライン化されており、
  verification-architecture.md が示唆する「純関数として抽出可能」（PROP-LV-008の対象）という形には
  まだリファクタされていない——ただし機能的には正しく動作しており（テストgreen）、これは**設計上の
  改善余地**であって purity 違反ではない（副作用境界内で判断ロジックが埋め込まれているだけで、境界の
  外に漏れているわけではない）。non-blocking。

## `founder-loop.sh` への REQ-LV-018 配線（現状: 未実装）

`report-args.mjs`（純関数 `founderReportArgs`）は実装・テスト済みだが、`founder-loop.sh` 側に
`loop-report.sh`/`report-args` への参照が一切無いことを grep で確認した（P0-6, task #6 pending）。
したがって、この境界について「純関数と副作用境界の分離が正しく実装されているか」を判定する対象コード自体が
まだ存在しない。**purity違反として報告すべき実装は無い**（実装されていないものは違反しようがない）——
次の統合実装時に、`founder-loop.sh` が `founderReportArgs()` の戻り値をそのまま `loop-report.sh` の
引数に渡すだけで、判断ロジック（`result`/`earned_usdc`/`evidence` の決定）を `founder-loop.sh` 側に
再実装しないことを Phase 5 相当の再監査で確認する必要がある、と記録しておく。

## Summary

（総括）

| 対象 | 判定 |
|---|---|
| Tier1宣言10ファイル | 全て一致、I/O混入なし |
| `cadence-evidence.py`境界集約 | 一致、cadence.pyはI/Oゼロを維持 |
| evaluator/ledger_metrics の「pure」用語 | 厳密な純粋性ではないが既存慣習と一致、sandbox境界は実際に守られている（non-blocking注記） |
| Tier2/3宣言ファイルの判断/I/O分離 | loop-report.sh・record_earn.pyは分離良好。onchain.pyは境界内に判断ロジックがインライン化（non-blocking改善余地） |
| founder-loop.sh配線 | 未実装のため対象外、次回監査項目として記録 |

**BLOCKING な purity 違反は確認されなかった。**
