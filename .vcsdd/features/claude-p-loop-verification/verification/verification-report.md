# Verification Report — claude-p-loop-verification (Phase 5, formal hardening, mode: lean)

対象コミット: `~/anicca/.worktrees/loop-verification` HEAD `ed53bdd` / `~/profitable-claude/.worktrees/loop-verification` HEAD `496ad22`。

## スコープの実態確認

この2つの worktree の diff は spec 全体（REQ-LV-001〜146）のうち **Tier 1 純関数群 + ごく一部の Tier 2/3 配線
（loop-report.sh evidence gate、record_earn.py on-chain フック、video warmup バグ修正、REQ-LV-004 の
STARTUP 文言更新）のみ**を実装している。`TaskList` の現状（#5 launchd 配線・#6 founder-loop mail 配線・#7 loop別
verify モジュール実装・#8 self-improve 3層展開・#9 E2E adversary・#11〜#16）が示す通り、Cadence Contract の
`cadence.py`/`cadence-evidence.py`・guardrails・evaluator・funnel 関数はいずれも**単体テストは green だが本番
呼び出し元への配線は未完了**（後述、grep で確認済み）。本レポートは実装済みの純関数群に対する Tier 1 検証と、
配線済み Tier 2 経路（loop-report.sh, verify-loops.sh/verify-loops-audit.sh, record_earn.py）に対する統合検証を
行う。未配線の Tier 2/3 項目は「対象外（未着手）」として明記する。

## Proof Obligations

（= Tier1 PROP 群の実行検証。既存テストスイート実行結果 — 全て実際に実行、fresh evidence）

| スイート | 件数 | 結果 |
|---|---|---|
| `skills/self/tests/test_cadence.py`（PROP-LV-020/021/022/035/036/037/040） | 21 | PASS |
| `skills/self/self-improve/tests/test_loop_evaluators.py`（PROP-LV-023） | 15 | PASS |
| `skills/self/self-improve/tests/test_weekly_compare.py`（PROP-LV-024） | 5 | PASS |
| `skills/self/loop-scale/tests/test_guardrails.py`（PROP-LV-028/029/030） | 14 | PASS |
| `skills/self/openclaw-migrate/tests/test_migration_gate.py`（PROP-LV-039） | 3 | PASS |
| `skills/_shared/__tests__/test_ytdlp_parse.py`（PROP-LV-003 ytdlp部分） | 7 | PASS |
| `skills/earn/polymarket-trade/test_positions.py`（PROP-LV-006） | 5 | PASS |
| `skills/earn/video/tests/test_record_earn_onchain_wiring.py`（PROP-LV-008/009） | 4 | PASS |
| `skills/earn/clip-promote/tests/test_clip_promote_status.mjs`（REQ-LV-120 clip-promote部分） | 6 | PASS |
| `skills/self/founder-loop/test-report-args.mjs`（PROP-LV-007） | 4 | PASS |
| `skills/report/test-loop-report.sh`（PROP-LV-001/002） | 15 | PASS |
| `~/profitable-claude/.../gig/__tests__/test_funnel.py`（PROP-LV-004） | 6 | PASS |
| `~/profitable-claude/.../bounty/tests/test_funnel.py`（PROP-LV-005） | 7 | PASS |

pytest はこのマシンの python3.14 環境で `sys.exit()` を含む自己実行スクリプト形式のテストを INTERNALERROR で
落とす（pytest側の互換性問題、実装側のバグではない）。`python3 <file>.py` 直接実行で全件確認した。合計
**112 assertion 相当、0 failed**。

## BLOCKING finding

### F-VERIF-1（BLOCKING）: `verify-loops-audit.sh` の audit mail が REQ-LV-003 の evidence gate 自身によって
恒久的に REJECTED される — 6h ごとの cadence scorecard 配信（REQ-LV-042/103）が機能しなくなる回帰

`~/anicca/.worktrees/loop-verification/skills/self/verify-loops-audit.sh:57`:

```bash
bash "$SELF/../report/loop-report.sh" audit "$(...)$LM_NOTE |$CADENCE_SCORECARD" no-op 0 none >> "$LOG" 2>&1 || true
```

第5引数（evidence_url）が裸の文字列 `none`（`"none: <理由>"` ではない）。REQ-LV-003 実装後の
`loop-report.sh` はこれを厳密に reject する。実際に実行して確認した:

```
$ bash loop-report.sh audit "test audit body" no-op 0 none
EXIT CODE: 1
--- ~/.openclaw/logs/loop-report.log ---
...loop=audit REJECTED (empty-or-bare-none evidence)
```

`verify-loops-audit.sh` 側は `|| true` で握りつぶすため audit スクリプト自体はクラッシュしないが、
**mail は一切送信されない**。REQ-LV-042「WHEN verify-loops-audit.sh が6hごとの scorecard を送る場合、
THE SYSTEM SHALL...loop-report.sh audit ... 呼び出しの本文に含める」・REQ-LV-103「streak() を...scorecard
（REQ-LV-042、置換後）に...含める」が要求する配信そのものが、この feature が新設した evidence gate（REQ-LV-003）
自身によって静かに壊れている。REQ-LV-004 は gig/affiliate/bounty の `*-cli.sh` の `STARTUP` 文言更新のみを対象と
明記しており（「対象は...`*-cli.sh` の `STARTUP` 文字列」）、`verify-loops-audit.sh` のこの直接呼び出しはその
対象範囲に含まれていない — スコープの取りこぼしによる契約違反。

**根拠**: PROP-LV-001（`lr_valid_evidence`）自体は仕様通り正しく動いている。壊れているのは呼び出し側の
契約違反であり、evidence gate のロジックにバグがあるわけではない。

**修正方針（記録のみ、コードは触っていない）**: `verify-loops-audit.sh:57` の第5引数を `none` から
`"none: routine 6h scorecard, no per-pass artifact"` 等の `none: <理由>` 形式に変更する1行修正で解消する。

## Non-blocking findings（記録のみ、severity付き）

### F-VERIF-2（MEDIUM、潜在）: `cadence_met()` の `kind=="compound"` が空 `conditions` で vacuous-true を返す

```python
$ python3 -c "from cadence import cadence_met; print(cadence_met('2026-07-08', {'kind':'compound','conditions':[]}, {'by_condition':{}}))"
True
```

`for sub_contract in contract["conditions"]: ...` が空配列だとループ本体が一度も実行されず、無条件で
`return True` に落ちる。REQ-LV-101 は compound を「全ての sub-contract が true の場合のみ true（論理AND、
ORでも多数決でもない）」と明記しており、design 意図は「AND over 1つ以上の条件」。空配列は「AND over ゼロ件」＝
数学的には真だが、運用上は「何も検証していないのに健全と判定される」——これはまさに G1 が潰そうとした
「artifact/contract が存在するだけで健全と誤判定する」欠陥クラスの再導入である。

現時点で出荷済みの `cadence-contracts.json` の pm-earner エントリは常に2条件（`hourly-pass`/`daily-redeem`）を
ハードコードしているため**現在は到達不能**（実害なし）。ただし `cadence_met()` 自体に条件数のガードが無いため、
将来 config 編集ミスで `conditions: []` になった場合、検知されずに pm-earner が「稼働中」と誤報告される。
推奨: `cadence_met()` の compound 分岐冒頭に `if not contract["conditions"]: return False`（または raise）を
追加する防御的アサーションを次のイテレーションで検討。

### F-VERIF-3（LOW、観察）: `kind=="recency"` は marker が未来（now より後）でも無条件で met=True

```python
$ python3 -c "from cadence import cadence_met; print(cadence_met('2026-07-08', {'kind':'recency','max_age_min':40}, {'marker_epoch_seconds':2000000,'now_epoch_seconds':1000000}))"
True
```

`(now - marker) <= max_age_seconds` は経過秒が負（marker が未来）でも常に真になる。時計スキューや mtime
改ざん等の異常入力に対して fail-open になる——このコードベースの他の箇所（`record_earn.py`/`positions.py`/
`ytdlp_parse.py` 全て「絶対に捏造しない・fail-closed」を明記）と設計思想が逆。実運用の evidence 供給元
（`cadence-evidence.py::_mtime_epoch`）は `os.stat().st_mtime` を直接使うため通常は未来にならないが、
ファイルシステムの mtime は書き換え可能な値であり、原理的には防御すべき入力である。Non-blocking（現在の
呼び出し元では発火条件がほぼ無い）だが、`recency` 分岐に `if now < marker: return False` を足す方が
このコードベースの一貫した fail-closed 方針に合致する。

### F-VERIF-4（LOW、観察）: `kind=="increment"` は `previous_value` キー欠損時も暗黙 `0` にフォールバックする

`evidence.get("previous_value", 0)` — キーが完全に無い（呼び出し元のバグで渡し忘れ）場合と、明示的に
`0` を渡した場合を区別しない。実運用の `cadence-evidence.py::_bounty_today_and_previous_checked()` は常に
両キーを供給するため現状は無害だが、将来別の呼び出し元がこの関数を再利用する際、evidence 構築ミスが
「増分あり」と誤判定される余地がある。Non-blocking、観察のみ。

### F-VERIF-5（非ブロッキング・将来配線時に要検証）: `summarize_gig_funnel`/`summarize_bounty_funnel` は
**まだどこからも呼ばれていない**（grep で確認、production 呼び出し元ゼロ）。実装した累積カウントは「1行=1状態
遷移」を前提に加算しており、同一 `requestId` の複数行（例: applied→replied→受注 の3行、STARTUP prompt の
B1 NURTURE が実際にこの形で書く）をそのまま渡すと二重・三重カウントする:

```python
$ python3 -c "
from funnel import summarize_gig_funnel
rows=[{'requestId':'R1','status':'applied'},{'requestId':'R1','status':'replied'},{'requestId':'R1','status':'受注'}]
print(summarize_gig_funnel(rows))"
{'applied': 3, 'replied': 2, 'won': 1, 'paid': 0}
```

1件の応募が `applied:3, replied:2, won:1` に化ける。REQ-LV-015 の文言「当該pass分の行から...集計」は
呼び出し元が pass 単位にフィルタする前提を置いているが、関数自体には「1 requestId につき最新状態のみ」の
保証が無い。P1 タスク#7（loop別 verify モジュール実装）で `gig-cli.sh`/`bounty-cli.sh` にこの関数を実配線する
際、渡す `applied_rows` が「本当にこの pass 分のみ」か「requestId ごとの最新状態のみ」であることを
実データで確認するテストケースを追加することを強く推奨する。純関数自体のロジック（累積境界の非重複計上）は
正しい——問題は呼び出し契約側にある。

## 対象外（この Phase では未着手、grep で確認済み）

- REQ-LV-050/051（launchd 配線）: `~/Library/LaunchAgents/` に該当 plist 新設なし（task #5 pending）
- REQ-LV-018 の実配線（`founder-loop.sh` からの `loop-report.sh`/`report-args.mjs` 呼び出し）: `founder-loop.sh`
  に `loop-report.sh`/`report-args` の参照なし（task #6 pending）。純関数 `founderReportArgs` 自体は実装・
  テスト済み
- REQ-LV-015/016 の実配線（`gig-cli.sh`/`bounty-cli.sh` からの `funnel.py` 呼び出し）: 呼び出し元なし（task #7）
- REQ-LV-017 の実配線（`positions.py` を実際に叩く Tier2/3 呼び出し）: 呼び出し元なし（task #7）
- REQ-LV-110〜113（evaluator の週次実行配線・promote gate E2E）: task #11 pending
- REQ-LV-019/038（E2E + fresh-context adversary PASS、Goal 6）: task #9 pending、この Phase の検証対象外
- REQ-LV-120〜146（dashboard/loop scaling/OpenClaw統合）: task #12〜#16 pending

## Summary

（結論）

Tier 1 純関数群（cadence.py, guardrails.py, weekly_compare.py, migration_gate.py, ytdlp_parse.py,
positions.py, clip-promote-status.mjs, report-args.mjs, gig/bounty funnel.py）は **全既存テスト green +
本レポートの追加境界ケース確認済み**。**F-VERIF-1 は BLOCKING** — 次のコミットで
`verify-loops-audit.sh:57` の evidence 引数を `none: <理由>` 形式に修正し、修正後に実際に
`loop-report.sh audit ...` が `SENT` としてログされることを再確認するまで、このサブシステムの
Tier 2 統合は完了と扱わない。F-VERIF-2〜5 は non-blocking（記録・次イテレーション検討）。
