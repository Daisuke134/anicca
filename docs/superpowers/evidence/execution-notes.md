# Execution Notes — loop 修理（open/evidence/pass-fail-blocked を随時更新）

正本 TODO = `docs/loop-engineering/00-SSOT.md §5`。詳細 evidence は本 dir の各 MD。

## Phase 1 — ✅ 全完了（2026-07-12）
- M1..M7 / S1..S7 / C1..C7 = done（SSOT §5 参照）。
- **M3 life-manager 二重起動退治（2026-07-12 実行・実証）**:
  - 退役: launchd `ai.anicca.life-manager-loop-healthcheck` を `launchctl bootout`+`disable`、plist→`.disabled`（可逆）。
  - kill: tmux `anicca-life-manager-loop` + `anicca-selffix-life-manager-loop`（両 sock GONE）。
  - 実証: `ps` に life-manager-loop worker プロセス無し = **2x課金停止**。
  - 復活経路点検: `self-fix.sh life-manager` escalation 不在（grep NONE）、LMHB は report専用（verify-loops-audit.sh:70,172）→ 蘇らない。
  - PC版 `ai.anicca.life-manager-core-healthcheck` → tmux `anicca-life-manager-core` は稼働継続。
  - commit: anicca-products `f04afa062`。

## Phase 2 — 進行中（gig=L1 を1本閉じる）
- **L1 gig — increment-2b（own-eyes reality-verifier を loop に内蔵）**:
  - status: builder 完了・branch `feature/gig-reality-verify`（repo ~/anicca、2 commits push済）・**未merge**。
  - 成果物: `gig_judge.py`（pure prompt-builder, judge.py copy）/ `gig_reality_verify.sh`（fresh claude -p が :9222 navigate+screenshot+report-skeptical判定→false時 selfheal-request）/ `auditor.sh`（決定verdict後に呼ぶ・additive）。
  - builder live E2E: 実走6m05s、fresh claude が services_lists/received_orders/dashboard_provider を navigate、10 claim 照合 → **verdict:true を `~/gig/audit-reality.jsonl` に実記録**、selfheal-request 未生成（正）。screenshot `~/gig/trajectory/verify001/01-reality_verify_check.png`。
  - GATE（未通過）: fresh adversary(Sonnet) 審査中 → 私自身が `gig_reality_verify.sh` 再実走で独立確認 → merge → gig 再起動。
- 残: L1 の increment-2 本体（self-heal 配線 Reflexion→self-fix.sh / 50-50 BP web検索自己改善 / gig-funnel metrics / gig-spec playbook 100%=doc26 §6.5）。
- 未着手: #5 connector 7日streak / #8 LM Phase B / L2 capafy / #7 article / L5 affiliate / L7 bounty / L8 explorer / #6 CEO縮退 / #9.5 factory(go待ち)。

## Phase 3 — end-state（未）
- G-GIG-FULL（gig 100%）→ G-PRODUCTIZE（earn loop を profitable-claude へ copy、1コマンド→新account→実¥）→ G-CLOUD（Mac→cloud、self-funded compute、hundreds並行）。
