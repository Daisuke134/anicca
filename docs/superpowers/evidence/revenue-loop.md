# 収益ループ1本を閉じる（article 視聴→¥ 導線）— Evidence

正本: spec §8 / goal「収益ループ=video か article を選び 視聴→¥ 導線実装、metrics ledger に実測行、¥0 は¥0 と報告」。選択=**article（profitable-article-writer、note.com 実 publish 実績あり）**。

## ✅ 完了（~/anicca-human-funded feature/human-funded b05dca97 merged+pushed）
builder 実装 → fresh Opus adversary FAIL(Mode B CTA 未到達) → 修正 → 再 adversary(bash 無しで実行不能) → **私が独立実行検証** + 冪等性 fix → merge。

### 視聴→¥ 導線（CTA link）
- `run.sh::insert_monetization_link()` が craft gate 通過後に CTA(`ARTICLE_CTA_URL`, 既定 aniccaai.com)を付与。
- **Mode B(zero-human 自律 rail)対応**: `lib/note-append-cta.py` が note.com リモート draft 本体に publish 前に CTA を追記(`update_article_raw_html`=draft_save、publish endpoint でない事を確認)。degrade-never-block。STATE.md に honest `cta_status`(carried/append_failed/not_requested/skipped)。
- **独立実行検証(私、adversary が bash 無しでできなかった分)**: `bash tests/test-prop27-monetization-cta-link.sh` = **PASS**。ephemeral note.com draft を実作成→CTA 追記→独立再取得で link 確認→冪等性→削除の live mechanism proof を含む。
- **冪等性 fix**(sprint-6 adversary finding): `if cta_url in body` が raw 比較で escape 済本体と不一致→`&` 含む URL で重複 append するバグを、escaped url 比較に修正(commit cdf14a2c)。

### metrics ledger（実測行）
- `lib/note-fetch-views.py` が note.com 認証 stats API から実 views 取得。**実測行**: `{key:nfb2ace9f0ed8, views:9, likes:2, revenue_jpy:0, revenue_source:not_verified_no_sales_api}`。取れない記事は `views:none:reason` と正直。
- `run.sh` の EXIT trap(`ARTICLE_METRICS_PASS=1`, 既定 OFF)で cadence 配線。`bash tests/test-prop28b-...` = PASS(私が独立実行)。

### 売上 ¥0 正直報告
- revenue_jpy は全行 0 + `revenue_source: not_verified_no_sales_api`。note.com sales API を探したが無し(404)。**現時点の実収益 = ¥0、正直に ¥0 と報告**。views を売上に見せかけていない(adversary 確認)。

## 残（non-blocking）
- metrics pass の cron 化は operator action(SKILL.md に手順、まだ ~/.openclaw cron 未配線)。
- `&` 含む tracking URL の重複テストは未追加(fix は入れた、既定 URL は安全)。
- V4(実売上)は別 gate: ¥0。「publish + 視聴計測まで done、売上 not yet」と分離。


## ✅ fresh Opus adversary PASS（bash 実行付き、2026-07-11）
過去2回の adversary は vcsdd-adversary の bash 非対応で実行検証できず FAIL だった。bash 付き Opus で再検証 = **overall PASS, blocking 0**:
- 全テスト自分で実行: 31/34 pass。3件失敗は共有 fixture 記事 `ne94efe526c9a` が note.com で status:deleted(Sprint4 導入、今回 merge と無関係、git log -S 確認)＝pre-existing baseline。
- CTA が Mode A+B 両方到達を run.sh で確認。**冪等性 fix を live 実証**(ephemeral draft create→append→再append no-op→削除、残渣ゼロ独立確認)。
- `note-fetch-views.py` 自分で実行: views 9/likes 2 実取得(捏造なし)、削除記事は none:reason 正直、revenue_jpy=0 固定 honest。
→ 収益ループの §10 + fresh adversary PASS 要件を正式に充足。
