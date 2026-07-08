# capafy loop ハーネス化 Design（2026-07-09）

## 背景
capafy loop は既に稼働中（skill=~/.openclaw/skills/capafy-autopublish、runner=~/anicca/skills/self/capafy-loop、ledger=state/published.jsonl に実公開実績: Life Manager online / meeting-action-items submitted）。だが gig で確立した「5部品ハーネス」の3つが欠けている: ①cadence contract（今日 publish したか判定なし、cadence-contracts.json に capafy 不在）②loop-report evidence mail 未配線 ③検索+metrics の self-improve 未配線。gig の型を capafy に copy+adapt する。

## As-is / To-be

| 部品 | as-is | to-be |
|---|---|---|
| BASE | ✅ CP1(card)→CP2(host)→CP3(submit) で skill 公開 | 維持 |
| VERIFY | 一部（reconcile_ledger.py が server 照合） | 公開後に agent URL/status を実際に確認して published.jsonl に記帳（既存 reconcile を cadence 源に活用） |
| SELF-HEAL | ✅ capafy-loop-healthcheck（稼働中） | cadence contract 化: 「今日 publish or 実 progress したか」未達→self-fix |
| SELF-IMPROVE | ❌ 無し | 検索+metrics 両輪: capafy.ai/growth#cases（公式成功事例）+ X の売れてる skill を agent-reach で検索して型を取り込む / published 後の閲覧・購入・収益 funnel を見て売れたカテゴリの skill を増やす |
| REPORT | ❌ 無し | loop-report evidence mail（公開 URL + status + 収益、空なら none:理由） |

## 要件（全 MUST、判断=agent/検証・cadence・検索実行・記帳=決定論、regex 判定禁止）

1. **cadence contract**: cadence-contracts.json に capafy entry 追加。source = published.jsonl の当日実イベント行（submitted/online 等の実 status、reconcile の noop 行は除外）。kind=row-exists（gig と同型、当日実 publish/progress のみ true）。他 loop entry は byte 不変。
2. **loop-report evidence 配線**: capafy の DAILY_LOOP/loop.sh の pass 末尾に loop-report.sh capafy 呼び出し（evidence = 公開した agent の URL(capafy.ai/store/agent/<id>) + status + 収益、無ければ none:理由）。
3. **検索駆動 self-improve**: STARTUP/DAILY_LOOP に「pass 内で agent-reach で capafy.ai/growth#cases と X の売れてる skill の型を検索→現状と差分→次 pass の skill 選定に反映（cold-start は検索重め）+ published funnel メトリクス（閲覧/購入/収益）を見て売れたカテゴリに倍賭け」を追記。lessons.jsonl に「売れた型/BP差分」記録。
4. **verify**: 公開後に agent URL の live 存在確認（既存 reconcile_ledger.py の server 照合を活用、HTTP だけで判定しない）。
5. organic 主体（marketing は後）。AI 申告記述は書かない（Dais 制約、全 loop 共通）。

## スコープ / 触るファイル
~/.openclaw/skills/capafy-autopublish/（SKILL.md/DAILY_LOOP.md/scripts）+ ~/anicca/skills/self/{capafy-loop/, cadence-contracts.json, cadence-evidence.py の capafy 分岐（gather_evidence と evidence_by_date_for_streak の両方）, verify-loops.sh, verify-loops-audit.sh, cadence-deadline-check.sh の capafy 配線（★ spec-review iteration-1 FINDING C-2 で追加: cadence-contracts.json への entry 追加だけでは本番の CADENCE_LOOPS/legacy stale_hrs escalation に一切効かないため verify-loops.sh/verify-loops-audit.sh の capafy 関連行のみ触る。★ spec-review iteration-2 FINDING C-3 で cadence-deadline-check.sh を追加: 実際に self-fix.sh を呼ぶのはこのファイルの独自ハードコード CADENCE_LOOPS のみで、verify-loops.sh/verify-loops-audit.sh 側の配線だけでは自己修復が一切発火しない regression になるため、この3ファイル目も capafy 関連行のみ触る ★）}。他 loop・他 repo は触らない（reddit/lm の legacy stale_hrs は対象外のまま）。gig の cadence-evidence.py パターンを copy+adapt。
