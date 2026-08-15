# ココナラ公開依頼の応募境界

## 現行経路

LIVE-1 では公開依頼への応募を手順書や agent の直接 CDP 操作で実行しない。
現行の唯一のproduction経路は次である。

`launchd ai.anicca.hf-gig-apply-direct`
→ immutable `releases/apply/current/.../application_direct.py`
→ `application_parent.py`
→ `application_planner.py`
→ Coconala submit effect
→ official exact-request-ID readback
→ canonical ledger / Telegram outbox

`scripts/application_parent.py` is the sole Apply production entrypoint. Storefront parity
完了までread-onlyの履歴証拠としてrepositoryに残すが、install・enable・callしない。親プロセスだけが次の順で実行する。

1. fenced lease を取得し、同じ leased target で marketplace snapshot を固定する。
2. browser/CDP/localhost 環境を持たない `application-intent-planner` が、snapshot の全 request を一対一で判断する。
3. 親が同一 target lock 内で freshness 再取得、durable intent、form open/fill/readback、confirmation click、submit click、official applied-history の exact request ID readback を行う。
4. exact ID が確認された後だけ intent を `confirmed` にし、canonical ledger を追記する。

旧 `open-application` / `submit-application` CLI は stale caller に対して fail-closed であり、手動・agent・runbook から使ってはいけない。prepared intent の再入は readback のみで click 0、generic な成功文言は応募確認ではない。

## 運用上の制約

- 提案文、価格、納期、実行可否は isolated planner の判断であり、親は再判定しない。
- 親は identity/hash/completeness/dedupe/cap/fence だけを決定的に検証する。
- hidden target、別 target submit、raw WebSocket、blind retry は禁止する。
- 公式応募履歴に exact ID がない限り、application を confirmed/ledger 化しない。

## 運用コマンド

```bash
# install（未導入時だけ）
cp skills/earn/gig/launchd/ai.anicca.hf-gig-apply-direct.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.anicca.hf-gig-apply-direct.plist

# status
launchctl print gui/$(id -u)/ai.anicca.hf-gig-apply-direct

# 次のwakeを既存loop自身に実行させる
launchctl kickstart gui/$(id -u)/ai.anicca.hf-gig-apply-direct
```
