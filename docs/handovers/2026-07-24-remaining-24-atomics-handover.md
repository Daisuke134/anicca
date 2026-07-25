# Life Manager 残り24 atomic 完遂ハンドオーバー(2026-07-24)

> **履歴資料。現在の件数・順序・To-doには使わない。** → `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md` §10 の **Current cursor / Live remaining to-do list** を参照。

正本: `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md` の§10表とCurrent cursorのみ。
本書は現在地の要約であり、§10と食い違ったら§10が勝つ。

## 現在地(実測済み)
- done: E2E束〜8d.2, 8g, 8h, 8c.R, 9a, **8i**(cutover完了: Railway `6806b0d4`=main `a7ac84d4`, anicca-products archived), **10g**, **10h**, **12a**。11aはL2 done(L3残)。
- pending: **24** — 8e, 8f, 9b-9f, 10a-10f, 10i, 11a(L3), 11b-d, 12b-c, 13a-d
- canonical repo = Daisuke134/life-manager のみ。anicca-products は archived(触らない)。
- production = Railway service life-call(root `apps/life-manager`)。/health が build tag を返す。

## 再利用する実装済みエンジン(再発明禁止)
- `apps/life-manager/lib/intent-graph.js` — 10g。6 intent種+provenance/confidence/expiry+訂正失効
- `apps/life-manager/lib/opportunity-engine.js` — 10h。6要素gate(act/ask/skip)
- `apps/life-manager/lib/mental-trigger.js` — 12a。効く瞬間判定(pre_event/between_events/pre_sleep, 3通/日)
- `apps/life-manager/lib/care-detector.js` — 11a-L2。本人cadence未ケア検知
- eval: `eval/run-{intent,men,phy}-eval.js` + 既存4суite。全部 `npm run eval` に常設

## 実行ルール(§10と同じ、省略なし)
1. 1 atomic = 1 isolated branch from latest main → TDD → eval 100% → PR → merge → §10とexecution-notes.mdを同一PRで更新 → merge containment確認
2. testを弱めない。Done条件を再定義しない。歴史的証拠は現在の証明にならない
3. L3は実世界の副作用のみ(実通話録音・実TG message id・実email Message-ID・DB row・logged-out URL・on-chain tx)。fixture/simulationは不可
4. secret/PII を commit/PR/log/証跡に出さない。証跡は docs/evidence/ へ(秘匿値なし)
5. 3回異なるアプローチで失敗したら記録して独立rowへ移る
