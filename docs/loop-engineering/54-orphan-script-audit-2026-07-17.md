# 54 — article-writer 孤児スクリプト総点検（2026-07-17 実測）

eyecatch 事件（実装済み・未配線）と同型の欠陥を全 90 script で監査。参照 = 実呼び出しのみ（コメント言及は不算入）。**WIRED 30 / MANUAL 18 / ORPHAN 42**。

## 最重要所見（優先度順）

| # | 発見 | 影響 | 対応 TODO |
|---|---|---|---|
| 1 | **self-improve.sh が ORPHAN** — article-daily.sh STEP1.5 は playbook.json を「読む」だけで、生成する self-improve.sh を呼ぶ経路も launchd plist も存在しない | **L3 self-improve 全体が構造的に不能**（playbook.json は永遠に生まれない）。spec の「#21/#24 DONE」は手動実測の話で、自動運転は未配線だった | #66 |
| 2 | audit-7day.sh / learn-whitelist.sh — ヘッダに週次 cron 起動と自己記述するが該当 plist が存在しない | 週次の自己監査・whitelist 学習が回らない | #67 |
| 3 | devto-publish/publish-to-devto.sh 一式（5本）— 完成した実装が完全孤立。実配線は別実装（publish-devto.sh） | eyecatch と最も同型。二重実装の片方が死蔵 | #69（archive） |
| 4 | citation-strip.py（SKILL rule 26 の唯一の実装）/ bookmark-gate.sh / fetch-ai-watch.sh — 品質ゲート・トピック選定支援が未配線 | rule 26 は手作業頼み、トピック選定が digest を活かせてない | #68 |

## ORPHAN 42 の内訳

- **配線すべき（機能が死んでる）**: self-improve.sh、rotation-effect-audit.sh（self-improve 依存）、measure-funnel.py（連鎖）、audit-7day.sh、learn-whitelist.sh、citation-strip.py、bookmark-gate.sh、fetch-ai-watch.sh、extract-daily-lesson.sh
- **archive すべき（使い捨て/置換済みの残骸）**: note-publish の one-off 群（republish-only / publish-membership / set-membership / set-preview-line / shot-gate / shot-plan / verify-public / verify-draft / fix-heading / del-and-republish / delete-auto-toc / insert-toc / manual-toc / open-preview / note-publish-draft.py / note-render-tables.py / verify-screenshot.py）、x-publish レガシー（publish-to-x.py / x_core.py / x_cover2.py / x_images.py / delete-drafts.py）、devto 孤児クラスタ5本、substack 孤児（publish-to-substack.sh / substack-publish.py / render-en-substack-assets.py + 連鎖の render-tables-autofit.py / verify-render.py）、zenn-deploy-retry.sh
- **正当 MANUAL（触らない）**: note-publish F1 手動パイプライン一式、run-*-agent.sh 群、publish_guard.py、dd-keepalive.py、rebuild-note-body.py、daily-run.sh（STAGED と自己記述）

## eyecatch 事件の一般法則（この監査の存在理由）

**症状**: 機能が「skill に存在する」のに製品挙動に現れない。**誤った本能**: SKILL.md に書いてあれば動いていると思う。**正しい手**: 「実呼び出しの grep」で配線を検証する（コメント・README 言及は配線ではない）。**一般法則**: 実装完了 ≠ 配線完了。新 script を作ったら、その場で呼び出し元（launchd / 親 script / STEP 文）まで書いて初めて DONE。監査は「参照元の実体化」（bash/python3 で実際に呼ぶ行があるか）でのみ判定する。

全 90 件の詳細表は監査 subagent 出力（2026-07-17）より。WIRED 判定の主要どころ: 全 gate（deslop/eval/seo/purity/freshness/reality）、run.sh、publish 経路（note/zenn/x/substack/devto の配線側）、price-check/tag-counts/make-free-version、set-eyecatch-draft.py（STEP5.5、今日配線）、publish-paid.py（STEP13）。
