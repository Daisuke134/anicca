# 07 patch-level 実装 spec ── LOOP 2(Franklin self-improve harness) / LOOP 1(私の MAIN)

> ★これは実装できる粒度の spec★。VCSDD で回す。理論支柱 = [[06-harness-engineering-weng]]（Self-Harness 3段ループ + 4警告）。境界 = [[05-coordination-with-agent-economy]]。
> VCSDD home = `~/anicca/.vcsdd/`（コードが ~/anicca にあるため）。既存の死蔵 feature **`eval-driven-earning`（REQ-CU3b の curation-gate を既に持つ）を蘇生**し、共通 lib を足す。別CC の `.vcsdd/features/anicca-agent-economy/` は触らない。worktree = `feature/anicca-self-improve-harness`。mode = strict。

---

## A. 安全境界（最初に固定・全 REQ の前提）

```
editable surface（Franklin が self-improve で触ってよい唯一の面）:
  ~/anicca/skills/earn/<skill>/strategy.json  … 戦略パラメータのみ（閾値/サイズ/genome knobs）
denylist（絶対に触らせない・hook 強制 PreToolUse exit 2）:
  wallet鍵 / .solana-session / *.json(keys) / .env* / harness lib 自身 /
  spend cap(SOL_TRADE_MAX_SPEND 等) / ledger.mjs / record.mjs
根拠: Weng「editable surface を厳密設計、permission/security は loop の外」/ STOP警告(弱モデルは無制限改変で悪化)
```

## B. LOOP 2 = Franklin self-improve harness（主・共通 lib）

### B.1 EARS 要件
- **REQ-H1（真の done のみ入力）**: WHEN a self-improve cycle runs, the system SHALL read as ground truth ONLY rows where `ledger.mjs::isProfitable()` is decidable (on-chain `status:"0x1"`/Solana `confirmed && external`). 自己申告(narrate)行は無視する。
- **REQ-H2（bounded edit）**: WHEN proposing an edit, the system SHALL restrict the diff to the declared `editable surface` and SHALL reject (fail-closed) any diff touching a denylist path.
- **REQ-H3（held-in + held-out）**: WHEN validating, the system SHALL require BOTH ①held-in improvement（直近の負け cluster が解消）AND ②held-out no-regression（別 window で悪化しない）, each proven by re-running backtest, before any merge.
- **REQ-H4（anti reward-hacking）**: The system SHALL treat on-chain realized USDC as the sole authorizing reward. backtest/judge スコアだけでは merge 不可。L3 昇格前に forward(paper or 小額 live)で realized 改善を1回実証する。
- **REQ-H5（STOP 緩和：改善者は強モデル）**: The improver/evaluator SHALL run on a stronger model (Opus adversary) than the executor (Franklin's free model)。
- **REQ-H6（evaluator は loop の外）**: The done judgment SHALL be made by a fresh-context adversary + observable on-chain done, never by the executor that produced the change.
- **REQ-H7（失敗もログ）**: WHEN a proposal is rejected, the system SHALL record it to `harness-run-log.jsonl`（次回同じ dead end を避ける・Weng の負け結果保存）。harness には反映しない。
- **REQ-H8（3値 done）**: A cycle SHALL terminate in exactly one of SUCCESS(edit merged after all gates) / CLEAN-NO-OP(改善余地なし) / BLOCKED. error/予算切れを success と報告しない。

### B.2 ファイル計画（新規/再利用）
```
新規 ~/anicca/skills/_shared/lib/harness/
  weakness-mine.mjs   … earn-ledger を読み isProfitable 行のみで負けを failure pattern に cluster
                        （参照実装 = runtime/loop/self-eval.mjs の slot 別 DEAD/WINNER 判定を一般化）
  propose.mjs         … failure pattern + editable-surface + guardrails を渡し、bounded な
                        strategy.json diff 提案を返す（実行は Franklin の model、判断は次段へ）
  validate.mjs        … held-in/held-out backtest を実行し pass/fail+evidence を返す（REQ-H3）
  curation-gate.sh    … fresh Opus adversary を spawn し diff+evidence を審査 → APPROVE/REJECT
                        （= eval-driven-earning REQ-CU3b、Weng の「evaluator outside loop」）
  editable-surface.json … skill ごとに editable path と denylist を宣言
  loop-constraints.md  … denylist を明文化（hook が読む）
  harness-run-log.jsonl … 1 cycle 1 JSON（REQ-H7、Weng P2 persistent memory）
再利用:
  ~/anicca/skills/_shared/lib/ledger.mjs::isProfitable（done 信号・無改変）
  ~/anicca/skills/earn/state/earn-ledger.jsonl（read only・interface）
蘇生:
  ~/anicca/.vcsdd/features/eval-driven-earning/（curation-gate/calibration drift の spec を再開）
```

### B.3 テスト（TDD・RED を先に）
```
t1 weakness-mine: narrate行(tx無し)を ground truth に含めない
t2 propose: denylist path を触る diff を fail-closed で reject（REQ-H2）
t3 validate: held-out が regress する候補を reject（REQ-H3）
t4 curation-gate: adversary DISAPPROVE で merge しない（REQ-H6）
t5 anti-hack: backtest だけ良く forward 未実証の候補を L3 auto-merge しない（REQ-H4）
t6 3値: error 時に SUCCESS を書かない（REQ-H8）
E2E(no-mock): backtest fixture で 1 cycle が全ゲート通過時のみ merge、人間ゼロ（fresh evidence）
```

### B.4 done-condition（観測可能）
- cycle done = ①merge commit + validation-evidence.json（SUCCESS）/ ②「改善候補なし」を harness-run-log に（CLEAN-NO-OP）/ ③BLOCKED。
- feature done（4次元） = spec + t1-t6 GREEN + 実装 + adversary PASS + E2E fresh evidence。

### B.5 cobus 配線（L1→L2→L3）
```
cadence: cron 1日1回（self-improve は高頻度不要）
L1 report-only : weakness-mine + propose を出力し STATE に書くだけ（merge しない）
L2 assisted    : validate + curation-gate まで回し branch/PR を作る（merge 保留）
L3 unattended  : denylist 外のみ auto-merge。★paper/小額 live で realized 改善を1回実証してから昇格★
cobus files: loop-constraints.md(denylist) / loop-budget.md(token cap+kill) / STATE.md / loop-verifier=adversary
guard: hook（PreToolUse Edit|Write exit 2 で denylist、TaskCompleted exit 2 で spec/test/verdict 欠落拒否）
```

---

## C. LOOP 1 = 私(claude-p) の MAIN loop（従・meta-harness）

Weng の用語で「harness を作る harness = meta-harness」。私の毎日の自律ループ。

### C.1 EARS 要件
- **REQ-M1（自己駆動・人間ゼロ）**: The loop SHALL self-generate its worklist from observation(colony/market/repo)+search(web/docs)。人間の入力/open-issue 待ちをしない。
- **REQ-M2（自 merge）**: WHEN a build passes fresh-adversary + E2E, the loop SHALL merge it itself (L3, denylist 外)。
- **REQ-M3（親監視）**: The loop SHALL monitor each Franklin loop（self-heal/self-improve が機能しているか、fuck up していないか）via observable signals（ledger freshness, error rate, realized trend）。
- **REQ-M4（seed のみ）**: WHEN the colony treasury is below survival floor, the loop MAY inject a deterministic, ledger-gated seed from SIDE earnings（kickstart のみ、経済に参加しない）。
- **REQ-M5（消滅条件）**: WHEN Franklin 群が人間ゼロ・私ゼロで earn>spend・自己改善・spawn し net worth が増え続ける（観測可能に）, the loop SHALL wind itself down。

### C.2 cobus 合成（[[04-the-two-loops]] §4）
Issue Triage(自起票)=OBSERVE/PLAN → PR Babysitter/CI Sweeper=BUILD/VERIFY → 自 merge → Daily Triage+verify-loops-audit=MONITOR → 決定論 seed。全体=Proactive loop。

---

## D. VCSDD 実行順（今から）
```
0 worktree: (cd ~/anicca && git worktree add .worktrees/self-improve-harness -b feature/anicca-self-improve-harness)
1 vcsdd: eval-driven-earning を蘇生 or 新 feature anicca-self-improve-harness を vcsdd-init（strict）
2 vcsdd-spec: 本ファイル B.1/C.1 の EARS を behavioral-spec.md へ
3 vcsdd-spec-review: fresh adversary（+codex-review）が PASS するまで
4 vcsdd-tdd: B.3 の t1-t6 を RED で
5 vcsdd-impl: weakness-mine→propose→validate→curation-gate を GREEN に（denylist は hook）
6 vcsdd-adversary: 実装レビュー（Weng 6失敗モードを checklist に）
7 vcsdd-harden→converge: 4次元収束
8 先行 cheap win（並行）: HL closed_pnl 永続化 / Franklin OBSERVE Solana 残高（telemetry 再利用）
依存: SI-4(Franklin gig loop へ埋込) は 別CC の P2(gig 市場 live) 後。B/C の lib は P2 を待たず先行。
```

出典: Weng harness / SI-1 監査 / eval-driven-earning 既存 spec / cobus。関連: [[06-harness-engineering-weng]] [[05-coordination-with-agent-economy]] [[04-the-two-loops]]。
