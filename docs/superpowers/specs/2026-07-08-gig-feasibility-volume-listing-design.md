# gig loop 改善 — feasibility gate + 出品(listing)モデル + 応募数最大化（2026-07-08）

## 背景（Dais 2026-07-08）

gig は AI にとって最高の稼ぎ場だが、現状「AI に難しい案件に少数だけ提案し、簡単な低ハングフルーツを大量に取れていない」。self-heal は既に実働（90 restart・実バグ修正コミット・self-fix 稼働中）で、問題は「壊れ」でなく「戦略」。

## As-is（内部コード + 市場調査、実証済み）

| 項目 | 実態 |
|---|---|
| 選定方式 | strategy.json の priority_categories(13) / skip_categories(19) を LLM が自然文 judgment（regex ハードコードでない=正しい） |
| 応募数 | max_apply_per_pass=5 だが**実績 0.42件/pass**（217 pass で 91 applied）。cap でなく model の過保守スクリーニング + 金曜夕方/週末の市場飽和が律速 |
| モデル | **「公開依頼への提案」only**。2023年9月以降これは SMS 電話認証必須 = 電話持たない AI は構造的に頭打ち |
| 出品(listing)モデル | **未使用**。出品は電話認証不要・無制限出品・継続リピート・競合ニッチを狙える = 応募数最大化の本命なのに使っていない |
| 占い(uranai) | **誤って skip_categories に**（"requires psychic abilities"）。テキスト鑑定は AI 完結のコンテンツ生成であり誤除外 |
| feasibility 判定 | 「AI-doable」一語の judgment のみ。電話/電話ログイン/SMS広告アカウント/実地/資格/録音を明示排除する基準が無い |
| 顧客拒否 | 「cheating」拒否ロジックは gig には無い（scam/不適切と「AI丸投げ禁止」尊重のみ）。ほぼ問題なし |
| self-heal | ✅ 実働（healthcheck 5分/DEAD・STALE restart→backoff→self-fix.sh Opus 委譲、90 restart・実修正コミット複数） |
| cleanup | ✅ disk-cleaner v9 に1本化済（旧3本統合）。ENOSPC 実績あり、現 73%(3.9GB) |

## To-be（MUST）

### 1. Feasibility gate（明示化、判断は agent・基準は prompt）
AI-doable の定義を prompt に明示（regex 化しない）: **可 = browser + computer で完結**（文章/コード/デザイン下書き/資料/チャット）。**不可 = 電話対応・電話/SMS ログイン・SMS 認証必須の広告アカウント運用・実地訪問・国家資格必須・音声録音・顔出し・物理制作**。不可カテゴリを skip に明記。

### 2. 出品(listing)モデルを主軸に追加（応募数最大化の本命）
- 高 AI 適性・低競合カテゴリで**サービスを出品**して待つ（電話不要）。対象: SEO記事/LP文章、ネーミング/キャッチコピー、Excel/VBA自動化、EC商品説明文、プレゼン/パワポ、文字起こし×要約、翻訳、FAQ生成。
- 運用: 1アカウント20枠、**週1〜2枠ずつ小出し**で新着露出を回転。同スキルを切り口違い（ライト/スタンダード/プレミアム、業界特化版）で複数出品し母数を増やす。初期は相場の50〜70%でレビュー収集→20〜30件で値上げ。
- これで「大量に応募」= 「大量に出品して買主を待つ」に転換（提案の電話ゲート・飽和を回避）。

### 3. 提案(proposal)モデルは feasibility 通過分に絞って全件応募
- viable な公開依頼は max まで**全件応募**（過保守で1件に絞らない）。飽和済み(応募30+)は自動 skip。

### 4. 占い再分類
skip から外し、**テキスト鑑定を listing の1カテゴリ**に（優先度は中〜低=飽和市場だが AI 完結・リピート文化）。

### 5. never-refuse 強化
prompt に「実行可能かつ合法な顧客依頼は絶対に断らない・軽視しない」を明記。断ってよいのは feasibility 不可 or 違法/scam のみ。

### 6. EDD（検証と自己改善の bar）
- **artifact**: 出品URL（listing）・提案URL（proposal）・受注・納品・入金。
- **funnel metrics**（gig-funnel.jsonl 拡張）: listings_live / proposals_applied / replies / orders_won / paid_jpy をカテゴリ別に。
- **cadence（self-heal の bar）**: 毎日「N件出品 or 応募したか」+ 全メッセージ確認したか。未達→self-fix（既存配線）。
- **evaluator（self-improve の bar）**: 週次でカテゴリ別 paid_jpy/応募 の勝率を出し、勝つカテゴリに出品を寄せ負けを減らす。lessons.jsonl に「どのカテゴリ/価格/切り口が受注したか」を記録し次 pass の出品選定に反映。
- 「今週 paid_jpy > 先週」を機械判定。

### 7. 一般化（他 loop への還元）
gig で確立する「feasibility gate（自分にできる仕事か）+ 低競合ニッチ狙い + 大量供給 + funnel evaluator + never-refuse」は、他 earn loop（clip/video/affiliate/article）にも横展開する self-improve の雛形とする。

## 判断 vs 決定論の境界
判断（どのカテゴリを出品するか・どの依頼に応募するか・価格・提案文）= agent。決定論 = feasibility 基準の提示（prompt）・funnel 記帳・cadence 判定・evaluator 集計・存在確認（出品/提案 URL を開いて確認）。regex による案件判定のハードコードは禁止（BUILD AGENTS RIGHT）。

## スコープ / 触るファイル
`~/profitable-claude/skills/human-funded/gig/`（gig-cli.sh STARTUP prompt, strategy.json, passprep.py, funnel.py, run.sh）+ `~/gig/strategy.json`。他 loop・他 repo は触らない。
