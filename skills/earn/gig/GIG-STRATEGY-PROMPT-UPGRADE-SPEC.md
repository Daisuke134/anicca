# gig 稼ぎ戦略 prompt 格上げ — 増分1 spec（VCSDD-lean）

正本: `docs/loop-engineering/26-gig-loop-asis-tobe-plan.md` §6.5 + `docs/superpowers/specs/2026-07-08-gig-feasibility-volume-listing-design.md`。
スコープ: STARTUP prompt(`gig-cli.sh`) と `strategy.default.json` のみ。funnel.py 等のコード集計は増分2（別タスク）。

## Requirements（EARS）

### REQ-001: 出品で売れる型（§50）を B0 に明記
**EARS**: WHEN gig-core が B0 SHUPPIN ステップを実行する THE SYSTEM SHALL タイトル=ベネフィット型/サムネ文字入れ/説明1000字構成/松竹梅3プラン/モニター価格/カテゴリ1つ絞り/毎日ログイン週1更新/20枠週1-2枠ローテーションの基準を prompt から読める状態にする。
**Acceptance Criteria**:
- `gig-cli.sh` の STARTUP 文字列内、B0 SHUPPIN ブロックに LISTING PLAYBOOK として上記全項目が明記される。
- `strategy.default.json` に `listing_playbook` / `listing_rotation_rule` / `plan_tier_template` として同内容が構造化データでも存在する。

### REQ-002: 応募速度ルール（§63）を B2 に明記
**EARS**: WHEN gig-core が B2 APPLY BROADLY ステップを実行する THE SYSTEM SHALL 新着(sort=new)優先・掲載直後30分以内の応募・応募30件以上または数日経過の飽和案件の自動skip・提案文5段構成・実績ゼロは相場80%を prompt から読める状態にする。
**Acceptance Criteria**:
- `gig-cli.sh` の B2 ブロックに APPLY SPEED RULE として明記。
- `strategy.default.json` の `proposal_playbook` に同内容。

### REQ-003: never-refuse 明記（§5）
**EARS**: WHEN gig-core が依頼のfeasibilityを判断する THE SYSTEM SHALL 合法かつ実行可能な依頼は断らない旨、断ってよいのはfeasibility不可 or 違法/scamのみである旨を prompt に明示する。
**Acceptance Criteria**: `gig-cli.sh` に `NEVER-REFUSE` ブロックが存在し「断ってよいのは」を含む。`strategy.default.json` に `never_refuse_policy` フィールドが存在する。

### REQ-004: feasibility gate 明示（§1）
**EARS**: WHEN gig-core が案件のAI対応可否を判断する THE SYSTEM SHALL 可=browser+computerで完結する仕事(文章/コード/デザイン下書き/資料/チャット)、不可=電話対応・電話/SMSログイン・SMS認証必須の広告アカウント運用・実地訪問・国家資格必須・音声録音・顔出し・物理制作、を prompt に明示する。
**Acceptance Criteria**: `gig-cli.sh` に `FEASIBILITY GATE` ブロックが存在し「可=browser」を含む。`strategy.default.json` の `feasibility_rules.ai_doable`/`ai_infeasible` に同内容。

### REQ-005: 占い再分類（§4）
**EARS**: WHEN strategy.default.json が霊感/スピリチュアル/占いカテゴリを扱う THE SYSTEM SHALL それを skip_categories から除外し listing_categories（listing対象）側に置く。
**Acceptance Criteria**: `strategy.default.json` の `skip_categories` 配列に「占い」「霊感」「スピリチュアル」を含む要素が存在しない。`listing_categories` に「霊感/スピリチュアル/占い」エントリが存在する。
**既知の残課題**: 実行中の `~/gig/strategy.json`（v38, 増分1のスコープ外）には依然「占い」が skip_categories に残っている。passprep.py はファイルが存在する限り default で上書きしない（missing/corrupt 時のみ復元）ため、この既存 live state を直すには別途 B4 IMPROVE STEP か手動修正が必要（今回の増分では touch しない）。

### REQ-006: 松竹梅 price/plan scaffold + listing 対象カテゴリ
**EARS**: WHEN gig-core が listing_categories を参照する THE SYSTEM SHALL SEO記事/LP文章・ネーミング/キャッチコピー・Excel/VBA自動化・EC商品説明文・プレゼン/パワポ・文字起こし×要約・翻訳・FAQ生成・占いの各カテゴリと、松/竹/梅の価格倍率テンプレートを strategy.default.json から読める状態にする。
**Acceptance Criteria**: `strategy.default.json` に `listing_categories`（9カテゴリ）と `plan_tier_template`（梅/竹/松）が存在する。

## Edge Cases
- strategy.json が壊れている/存在しない場合: passprep.py が strategy.default.json からブートストラップする（既存機能、本増分では変更なし）ので、上記フィールドは自動的に live state へ伝播する。
- gig-cli.sh の STARTUP は単一引用符の巨大文字列: 内部に生の `'`（straight apostrophe）を絶対に入れない（bash構文破壊）。本増分の全挿入文はこの制約を満たす（`bash -n` で検証済み）。
- 判断（どのカテゴリに出品するか・どの依頼に応募するか・価格・提案文の文言）は agent 自身が行う。regex によるハードコード判定は行わない（`~/.claude/rules/building-effective-ai-agents.md`）。prompt/JSON は判断の「基準」を提示するのみ。

## Purity Boundary
- 決定論的: strategy.default.json のスキーマ・grep による文字列存在確認（verify script）。
- Agent判断: どのカテゴリを出品/応募するか、価格設定の具体値、提案文の作文内容。

## 検証（verify_gig_strategy.sh）
1. `bash -n gig-cli.sh` — STARTUP 文字列を含む bash 全体が構文的に正しいこと。
2. `python3 -c json.load` — strategy.default.json（および参考として live `~/gig/strategy.json`）が valid JSON であること。
3. grep（gig-cli.sh + strategy.default.json 結合テキストに対して）— 松竹梅/モニター価格/サムネ.*文字/ベネフィット/掲載.*30分/(NEVER.*断らない|断ってよいのは)/(feasibility|可=browser) の各パターンが存在すること。
4. strategy.default.json の skip_categories に占い/霊感/スピリチュアルが存在しないこと。

全 PASS するまで実装を直す（RED相当は「実装前に verify script を書いて既存ファイルに対して走らせ、REQ-001〜006 が全てFAILすることを確認する」フェーズ、GREENは全PASS）。
