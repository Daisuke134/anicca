# 12 Loops — 実測ステータスと TODO（2026-09-03 audit）

実測日: 2026-09-03。全数値は ledger / log / state file から直接読んだもの（推測なし）。
北極星: Life Manager = 財務的に自立した AGI。12 loop 全部が human-loop 最小で金を刷る。
方式: Fable が設計、Sonnet subagent が実装、loop 自身が実行（orchestration 固定）。

## 総収益（検証済みの実金のみ）

| 出所 | 金額 | 最終確認 |
|---|---|---|
| Coconala | **¥129,636 累計**（¥5,460 payout 申請 8/20、6件受注 / 806応募） | revenue-collect.log（8/15以降更新停止） |
| Capafy (mobile) | $19.98 gross / 5注文、$8 payout未着金 | 8/22 で ledger 停止 |
| Lancers | ¥0（応募60件検証済み、受注0、問合せ2件） | contracts.json 9/3 |
| CrowdWorks | ¥0（応募2件、8/11以降ゼロ） | receipts 9/3 |
| Crypto wallet | **-$18.65**（$18.7投入 → $0.05残） | portfolio-realtime 9/3 |
| その他全部（writer/affiliate/stripe/the402/x402） | ¥0 検証済み収益なし | 9/3 |

**直近3週間、新規の検証済み入金ゼロ。「動いている」と「稼いでいる」が乖離している。**

## Loop別ステータス（あるべき姿 → 実測 → 差分）

| # | Loop | 判定 | 実測 | 根本原因 / 差分 |
|---|---|---|---|---|
| 1 | Gig: Coconala | 🔴 出品全休止 | 4 lane稼働中、応募継続（9/2最新）、¥129,636 | revenue collector が 8/15 から停止 → 今の残高が見えない。paid/storefront lane が間欠 fail |
| 2 | Gig: Lancers | 🔴 応募停止中 | 6 job稼働だが application lane が毎tick `planner_contract_invalid`。今日 fresh判断0件 | `application_loop.py` の `_validate()`: observed 33件のうち1件でも budget_min/max_minor 不正だと batch全体を ValueError で捨てる設計。1行の毒で全滅 |
| 3 | Gig: CrowdWorks | 🔴 8/11から死亡 | application exit 1、`account.json` が 8/11 から `input_required` | credential 未投入（旧 hours_limit 説は取り消し） |
| 4 | Writer | 🟡 書けるが測れない | 記事公開は継続（9/1 run あり）。sales-ledger は 8/22 から `ok:false` 連発 | Note/Substack の売上計測が壊れ、収益検証不能。article-daily exit 75 |
| 5 | Affiliate | 🟡 投稿するが¥0 | X投稿は今日も稼働。毎cycle `NO_REVENUE_CREDIT` | Amazon Associates の成果が一度も confirm されず |
| 6 | Investment (Alpaca) | 🔴 blocked | `alpaca_pass_failed` を毎cycle。pm-live-trade は $2.05 で HOLD（最小 $5 未満） | Alpaca 認証/pass 失敗。hackathon 提出は paper のままで可能 |
| 7 | Agent economy / crypto | 🔴 8/28から停止 | franklin1: git checkout 衝突で毎cycle abort。franklin2: proxy 429。daemon SIGTERM 後未復帰 | net -$18.65。「財務自立 AGI」の土台が止まっている |
| 8 | Job hunter | 🟡 Workday only | 今日の run `runner_failed`。Ashby/Greenhouse/Lever は README 自認で未完成 | remote + Tokyo の一般求人に未対応（Dais の要求と乖離） |
| 9 | Fundraiser | 🔴 8/31から死亡 | disk full (Errno 28) 事故で停止、復帰せず。accelerator 応募実績の証跡なし | disk は回復済み（19Gi free）なのに loop が再起動されていない |
| 10 | Connector | 🟢 生存 | 今日も発火、Telegram 配信あり | Luma/Connpass/Peatix のみ実証。唯一「金を直接産まない」loop（設計通り） |
| 11 | LM Cloud (web) | 🟡 課金ゼロ | stripe listener/poller 今日も稼働、**新規 charge 0 件**。selfbuild は動くが `no_verified_award` | 製品は生きているがユーザー/課金がいない。QR onboarding → X で配布が未実施 |
| 12 | Mobile (Capafy) | 🟡 停滞 | $19.98 で 8/12 から売上なし、ledger 8/22 停止 | 新規販売導線なし。postiz/自前 marketing 未接続 |
| - | Ebook | ⚫ 存在しない | plist も pipeline もなし | 作るなら新規（優先度は上記の後） |


## 2026-09-04 実測サマリ（本番に載ったもの）

main `455cc4bdb` / live release `20260904T182615-455cc4bd`。

| 変更 | 証拠 | 状態 |
|---|---|---|
| launchd が `USER` を渡さず claude CLI が保存済み認証を読めなかった。runner 2 箇所で補完（plist 191 個は不変） | 同一呼び出しが rc1/result無 → rc0/schema_valid。PR #4085 | 本番 |
| Coconala 出品 14 件を `受付休止中` → `公開中` | effects.jsonl に reopen 14 行、readback 休止 0 | 本番外（効果は適用済） |
| 一覧 scraper が `受付休止中` を state:None として捨てていた | 契約検証が 14 件を毎 wake 破棄していた | 本番 |
| reply lane の backlog 飢餓（新着ゼロの pass でしか backlog を見ない gate） | 修正前は 1 thread、修正後は 3 thread 判断 | 本番 |
| Lancers `_filter_claimed_rows` が 1 行の予算不正で planner 前に全滅 | `planner_contract_invalid` 消滅、観測 33→40、exit 0。PR #4086 | 本番 |
| Lancers profile に顔写真登録、公式完成度 90% | 公式 readback | 本番 |
| 出品カタログ 20 本（platform 非依存、¥5,000〜¥350,000） | `skills/gig-work/profile/listings/catalog.json` | 資産のみ、未公開 |

**残る単一の壁:** 共有モデル runner の返答契約。`claude-direct` は rc 0 で返すが `missing required property decision` で棄却される。
storefront / paid / Lancers 応募の 3 lane がこの 1 点で止まっている。ここが開けば同時に動く。

**誤りだった仮説（記録）:** 認証切れ説、CrowdWorks の `hours_limit` 文字列説、paid lane の lock 競合説、Writer が claude で稼働中という説。すべて実測で反証。

## TODO（この順。順序 SSOT — Dais 明示なしに変更禁止）

**状態記法:** ✅DONE=本番で実測済 / 🔄進行中 / ⬜未着手。DONE は再着手しない。最終更新 2026-09-04。

### ✅ DONE（本番実測済。触らない）

| # | 内容 | 証拠 |
|---|---|---|
| D1 | launchd が `USER` を渡さず claude CLI が保存済み認証を読めなかった。runner 2 箇所で補完 | 同一呼び出しが rc1/result無 → rc0。PR #4085 |
| D2 | Claude 候補にスキーマが一度も渡っていなかった（codex だけ受領）。共有 prompt 経路で付与 | `schema_valid=true` を storefront と escalation で実測。PR #4087 |
| D3 | Coconala 出品 14 件を `受付休止中` → `公開中` | effects.jsonl reopen 14 行、readback 休止 0 |
| D4 | 一覧 scraper が `受付休止中` を state:None として捨てていた | 契約検証が 14 件を毎 wake 破棄していた |
| D5 | reply lane の backlog 飢餓（新着ゼロの pass でしか backlog を見ない gate） | 修正前 1 thread → 修正後 3 thread 判断 |
| D6 | Lancers `_filter_claimed_rows` が 1 行の予算不正で planner 前に全滅 | `planner_contract_invalid` 消滅、観測 33→40。PR #4086 |
| D7 | Lancers planner の fallback が死んだ proxy provider を指していた → `claude-direct` へ | テスト 51 件 OK。PR #4088、main `21470735d` |
| D8 | Lancers profile に顔写真登録、公式完成度 90%（残り電話認証のみ、収益 blocker ではない） | 公式 readback |
| D9 | 出品カタログ 20 本（システム/アプリ開発特化、¥5,000〜¥350,000、月額保守含む） | `skills/gig-work/profile/listings/catalog.json` |
| D10 | Coconala の capability family 欠落を復元 | `listing_contract_family_missing` 消滅 |

**運用上の必須知識（忘れると再発する）:**

`bin/cut-loop-release.sh` は `~/loops/current` の symlink を張り替えるだけで、label は指し直さない。
自動追随するのは `ai.anicca.life-manager-release-reconciler` だけで、対象は **5 label にハードコード**（gig 4 lane + disk-cleanup）。
残り 170 label は `LIFE_MANAGER_APPLY_TARGET=<loop-id> <release>/bin/lm-loop apply` を打つまで古い release で動き続ける。

その結果として 2026-09-04 に起きたこと:
- 出荷した修正が本番に載っていないのに「出荷済み」に見えた（`browser-lane-agent` が死んだ proxy を呼び続けた）
- ほぼ全 release が「使用中」と判定され回収できず、空き容量が 716MB まで低下
- `agent-economy-loop` は **削除済み release を指したまま** 8/28 から停止していた（本当の原因。git 衝突説は誤り）

回収手順: 全 label を現行 release へ指し直す → `python3 runtime/loop/central_cleanup.py --release-gc-only`（冪等、繰り返し実行可）。
恒久対策: reconciler の idle-safe な指し直しを 5 label 固定から registry 全体へ広げる。稼働中 loop を無条件に再起動しない設計が前提。
 release を切っても launchd label は自動で更新されない。
`LIFE_MANAGER_APPLY_TARGET=<label> <release>/bin/lm-loop apply` で指し直さないと変更は死んだまま。
2026-09-04 に 12 label が全部バラバラの古い release に固定されていた。

### 🔄 進行中

#### Storefront（ココナラ）— 完了条件は spec 6.2A の 8 番「全出品変更を公式帰属付きで実行し再実行ゼロ」

済:
- モデル到達（USER 環境変数）/ 休止14件を公開へ復帰 / 死んだブラウザ貸出の回収（PR #4109）
- 遅い browser 呼び出しで wake 全体を落とさない（PR #4111）
- 出品の種類をカタログに縛る（PR #4107）— 全スキルが出品候補に露出していた
- 競合参照を 6 → 14 件に拡張

残り、この順:
1. **専用ブラウザ文脈と貸出識別子**（spec 6.2A PAR-1）。今は1台共有で兄弟 lane 由来の詰まりが出る。仕様違反状態
2. **自主的な24時間制限を外す** — `storefront_direct.py:1488` `CREATE_MIN_INTERVAL_SECONDS=86400` は我々が決めた数字。ココナラの上限は20件、今15件で5枠空き
3. **看板をシステム開発へ** — 公開プロフィールが「Kosuke｜教育研修PPT×AI活用」。開発案件が来ない
4. ~~**開発でない ¥55,000（4384702「顧客インタビューを意思決定メモに整理します」）を下ろす**~~ DONE — 2026-09-06 の公式在庫15件に 4384702 は無い
5. **カタログから開発系を公開**し、公開ページで題名・本文・価格を確認
   - 5a. **guard 拒否を次回プロンプトへ差し戻す**（これが開くまで5は進まない）。2026-09-06 18:21〜20:13 の full wake 12連続が effect 0 で `failed`。Terra には到達している（同時間帯に `gpt-5.6-terra` 21回）ので #0 とは別物。
     直す場所 — `skills/earn/gig/scripts/storefront_direct.py`
     `_invoke_create_proposal`(3471) と `_invoke_proposal`(3297) は違反提案で raise して wake ごと落ちる。拒否理由は捨てられ、次wakeは同じ context から同じ違反を再生成する。
     (a) 拒否を `state_dir/proposal-rejections.jsonl` へ `{gap_key, rejection, proposed_value, observed_at_epoch}` で追記する。
     (b) `_proposal_prompt`(3236) と `_create_proposal_prompt`(3400) の CONTEXT_JSON に、同一 gap_key の直近拒否を `prior_rejections` として渡す。
     (c) prompt 本文に guard の規則を明記する — `_prohibited_copy_terms` の禁止語（実測で「スプレッドシート」）と、3554行の連用形規則（`title_stem` の末尾は `いきしちにひみりぎじびぴえけせてねへめれげぜでべぺ` のいずれか。ココナラが `ます` を付けるため）。
     (d) 同一 gap で同じ guard に3回連続で落ちたら、その gap を当該 evidence_cursor の間だけ選定対象から外し、次に価値の高い gap へ進む。無限に同じ穴を掘らせない。
     DONE: `proposal-rejections.jsonl` に拒否行が残り、同一 gap の次wakeで同じ guard に落ちない。full wake が effect 1 / readback 1 で公開まで到達する。
6. **全出品変更が公式読み戻しで確認でき、次wakeで重複ゼロ**を実証
   - 6a. **RETIRE を発火可能にする** — 今は構造的に一度も発火できない。
     `storefront_direct.py:2137` `_near_duplicate_listings` は 2154行の `ratio >= 0.9` でしか重複を認めないが、実測の最大ペアは **0.857**（4244912 × 4330105）。他は全て0.8未満。よって `duplicate_of` は空。
     もう一方の経路も閉じている: 958行 `capacity_pressure = len(contract_by_id) >= policy["slot_limit"]` は `15 >= 20` = false。
     結果 985行 `retire_ready` が全15件で false → `RETIRE`/`REPLACE` は選定されず、6344-6399 の実行器（実在し公式アーカイブ操作に束縛済み）が本番で死んでいる。
     直し方: 閾値を上げるのではなく計器を替える。difflib を捨て、`storefront-proposal-agent` に生カタログ（service_id / title_stem / capability_family / price / views / purchases）を渡して「買い手が代替品として比較する組」を判定させ、strict schema で封印する。決定論コードはアーカイブ操作・読み戻し・復元・単一effect fence を握り続ける。閾値を0.85へ下げる案は棄却 — 正当に別物の出品を畳み始める。
     実測対象の8件: SNS系5件 `4244556 / 4244912 / 4302213 / 4330105 / 4330753`、Excel系3件 `4244910 / 4313386 / 4357844`。
     DONE: 重複組が `duplicate-listings.jsonl` に新規追記され、1件が `非公開` へ落ちて公式読み戻しで確認でき、次wakeで重複effect 0、復元も実測できる。
   - 6b. **プラットフォーム上の成功出品を IMPROVE に届ける** — 収集済みなのに捨てている。
     `_extract_search_demand`(1370) が公式検索から `comparables`（`display_price_jpy` / `rating` / `review_count`）を作り、`_demand_score`(1430) が `median_price_jpy` / `sold_comparables` / `reviewed_comparables` を出し、`demand-evidence.jsonl` に残っている。実測2件:
     `excel_vba_gas_automation` = ¥29,000/レビュー464件、¥3,000/428件（当方のExcel3件は ¥7,000/¥6,000/¥5,000 で販売0）
     `line_bot_dev` = median ¥35,000、12件全て評価5.0、¥20,000〜80,000、検索結果1,657件（当方は該当出品なし）
     この構造化データは `CREATE` 経路（`_create_proposal_prompt` 3400 / blueprint 3459）にしか渡っていない。既存15件を支配する `IMPROVE` 経路 `_proposal_prompt`(3236) は、3254行で競合ページ本文を8,000字に切って渡すだけで、3272行が「Competitors supply generalized structure only: never copy their wording, images, reviews, sales, speed, guarantees or results」と使用を禁じている。
     直す場所: `_proposal_prompt`(3236) と `_judgement_prompt`(3174) の CONTEXT_JSON に、当該 `capability_family` の `demand-evidence.jsonl` 行から `median_price_jpy` / `comparables`（価格・評価・レビュー数のみ）/ `sold_comparables` / `visible_result_count` を追加する。3272行の禁止文を「表現・画像・実績の複製は禁止。観測された価格・評価・レビュー数の分布は公開事実として使用してよい」へ書き換える。文言・画像・レビュー本文・実績主張の複製禁止はそのまま残す。
     DONE: `IMPROVE` 提案の evidence に demand-evidence の path が入り、価格提案が family median を根拠に説明され、公式読み戻しで価格が確認できる。

現在の棚（2026-09-06 実測15件、全て sales_count 0、30日 views 441）:
`¥200,000 4386009 iOS/Androidアプリ開発` / `¥20,000 4330368 OpenCV画像認識実装` / `¥15,000 4371816 定型業務のAI自動化` / `¥7,000 4244910 ExcelVBA` / `¥6,000 4313386 ExcelVBA` / `¥5,000 4357844 請求書Excel` / `¥5,000 4244556 SNS公開前確認` / `¥5,000 4244912 SNS引継ぎ手順` / `¥5,000 4302213 SNS AI導入確認表` / `¥5,000 4330105 SNS AI引継ぎ手順書` / `¥5,000 4308502 研修資料再設計` / `¥4,500 4312985 UIイタリア語翻訳` / `¥3,000 4330753 SNS公開前チェック表` / `¥3,000 4313100 Web画像差替` / `¥3,000 4355225 SEO記事執筆`
15枠のうち8枠が2アイデアの反復（SNS系5・Excel系3）。詳細と根拠 → spec `docs/superpowers/specs/2026-08-16-storefront-loop-ssot.md` の 4A 節。

#### 共有部品（gig 3 platform）

3platform の実測（2026-09-06）— 共有できていない証拠:

| | ココナラ | ランサーズ | クラウドワークス |
|---|---|---|---|
| 実装 | `skills/earn/gig` 282ファイル / 114,057行 | `skills/earn/lancers` 4,072行 | repo外 `~/.local/share/anicca/crowdworks-revenue-skill/` 3ファイル・未versioned |
| label / 間隔 | `hf-gig-storefront-direct` / 60s | `lancers-revenue-storefront` / 1800s | `crowdworks.storefront` / 300s |
| 生存 | 稼働中・全wake失敗（5a参照） | lane専用ログが 9/1 23:03 で停止 | lane state が 8/15 `observed_status:failed` で凍結、plist指定ログが未生成 |
| 出品 | 15件・全て販売0 | 1件 `1338228` published | 0件 |
| 需要実測 | 30日 views 441 / 購入0 | 検索表示20・閲覧0・お気に入り0・相談0・注文0 | — |
| `_shared/marketplace-core` 利用 | なし | あり（唯一の利用者） | なし |
| SKILL.md | なし | あり | なし |

共有層 `skills/_shared/marketplace-core` は 2,251行4本（`ledger.py` 913 / `contracts.py` 549 / `application_transaction.py` 477 / `telegram_outbox.py` 312）= 帳簿と通知のみ。ココナラ側の資産（契約封印・公式読み戻し・重複fence・capability family・KPI帰属・コピーguard）は1行も共有されていない。

ランサーズの出品内容自体はココナラより良い（`B2B企業のSNS更新を止めず見込み客に伝わる投稿を毎月制作し` / ¥29,800・¥198,000・¥398,000 の月次3プラン / やらないことの明示あり）。欠けているのは露出と、出品を増やす能力。`storefront_offer.py` は docstring の通り "Inspect or align one canonical Lancers storefront offer" で、1件を整合させる以上のことをしない。

7. `capafy/catalog/` を出品候補から外す（誤出品の根本）
8. 看板を `skills/gig-work/profile/positioning.md` に切り出し3platformで共有
9. ランサーズの `products/` 独自定義を捨てカタログを読む
10. クラウドワークスもカタログを読む
11. カタログ1箇所の変更が3platformに反映されることを実測

#### レシピ集約（spec 6.2B）
12. `loop-development` を `loop-engineering` へ統合し `references/` を作る（deploy / browser / providers / degradation / money-loop-shape / evidence）
13. `earn/gig` の216ファイルから recipe と adapter を分離
14. そのレシピで新platformを1本作り再利用を実証

#### 運用上の制約（無視すると再発）
- release を切っても label は指し直されない
- ブラウザは1台共有。spec は lane毎に独立した文脈を要求しているが未実装
- 機械の負荷。agent 3セッション同時で load 60超、browser 呼び出しが時間切れになる



0. **★律速★ ルーターが Claude 候補へ到達しない** — 14 task class に fallback を入れて出荷済（PR #4090）だが、本番の試行記録は毎回 codex 1 行で終わり Claude の行が書かれない。`agent_runner.py` の候補ループ（1826-1935）と `codex_failover_action`（1449）で、codex 枠切れ後にチェーンが打ち切られている。
   DONE: `reply-semantic-agent` と `application-intent-planner` の attempts に claude の 2 行目が rc=0 で出る。
   **これが開くまで返信・応募・出品はいずれも動かない。他項目を先に開けない。**


1. **Coconala 出品をソフトウェア構築へ入れ替え** — Dais 方針: 今の 14 件は翻訳・小作業で、稼いでいる出品者が誰もやっていない領域。売るのは Web/業務システム構築、モバイルアプリ、自動化、既存システム修正。単価 5〜30万円、月額の継続オプション付き。文面・価格・オプション・画像は上位出品者の実物を写す。
   DONE 条件: システム/アプリ開発の出品 ≥2 本が公開 URL で受注可能、弱い出品は demand データ（views/favorites/purchases）を根拠に退出、次 wake で重複 0。
2. **Lancers を現行 release へ出荷** — PR #4088 は main 済み。release ビルドのロック待ち。
   DONE 条件: lane が exit 0、`planner_runner_failed` 消滅、判断数 > 0。

### ⬜ 未着手（この順）

0'. **label ドリフト解消と release 回収** — 12 label が別々の古い release を固定しており、release を切っても指し直さないと変更が死ぬ。副作用でディスクを圧迫（release だけで 16GB、空き 5.1GB）。
   DONE: 全 label が現行 release を指し、未参照 release を回収して空き 15GB 以上。


3. **Coconala paid の取りこぼし解消** — 未返信 97 thread（飢餓修正は本番済、消化はこれから）。停滞 3 件のうち 1 件は納品物済みで未送信、1 件は客がキャンセル済み、1 件は成果物なし。
   DONE: wake summary の未返信 0・未提出 0、返信 receipt ≥1。
4. **CrowdWorks 復旧** — コードが main に存在せず worktree のみ。account は 8/11 から credential 待ち。
   DONE: `application-receipts.jsonl` に 8/11 以降初の receipt 1 件。
5. **出品 asset を 3 platform 共有に** — 現在 `skills/gig-work/profile/` を読むのは Lancers のみ。Coconala/CrowdWorks 未接続。
   DONE: 同一カタログから Lancers package と CrowdWorks 出品が生成される。
6. **Coconala revenue collector 復旧** — `~/gig/earnings.jsonl` 最終行 8/12、専用 plist なし。
   DONE: 本日日付の行。
7. **Fundraiser 再起動** — 8/31 disk 事故から未復帰。 DONE: accelerator 応募 1 件の受領証跡。
8. **Agent economy 復旧** — franklin1 git 衝突、franklin2 proxy 429。 DONE: 両者 wake 完走、ledger 本日行。
9. **Writer 売上計測復旧** — DONE: `sales-ledger.jsonl` に `ok:true` 1 行。
10. **Job hunter 拡張** — Workday 専用から remote + Tokyo へ。 DONE: 応募 1 件の受領証跡。
11. **LM Cloud 出荷** — QR onboarding → X 配布 → Stripe 初 charge。 DONE: `new charges: 1`。
12. **Alpaca 修復 + hackathon 提出** — DONE: 提出受領。
13. **Capafy 販売再開** — DONE: 新規注文 1 件。
14. **「金を刷る loop を作る skill」化** — DONE: skill で新 loop 1 本、既存資産の再利用を実証。
15. **README を real-time status に** — DONE: loop が書き換えた README diff が commit される。

## 補足事実

- Lancers profile: 公式完成度 **90%**（本人確認・NDA・avatar・portfolio 済）。残り10%は電話認証のみで、収益ブロッカーではない。

### 履歴書/職務経歴書（実サイト一次情報で再検証。当初の「欄は存在しない」は誤りだったので訂正）

| サイト | 職務経歴書 upload 欄 | 一次ソース |
|---|---|---|
| **Lancers** | **新規登録フローにのみ存在**（任意、「スキップする」で飛ばせる）。通常の「プロフィール編集」画面には無く、経歴・資格はテキスト入力のみ | lancers.jp/consultation/detail/7604（回答「職務経歴書の同様の内容をプロフィールに記載することができます」）、lancers.jp/faq/A1028/615 |
| **Coconala** | **無し**。職歴・学歴・資格は全てテキスト欄。画像upload は portfolio と本人確認書類のみ | help.coconala.com/hc/ja/articles/360011290814 |

Coconala は該当なしで確定。**Lancers は登録時に skip された可能性があり、当該アカウントで実際に upload 済みかは未確認**。
ただし公式の案内どおりテキストの経歴欄で代替可能なので、収益ブロッカーとは断定できない。

### ★ 本当の穴: profile 完成度が誰にも監視されていない

`PROFILE-ASSETS.md` 手順8 は「public URL からプロフィールを読み返して完成度を記録する」と定めているが、
**`~/.local/state/anicca/lancers/` に completeness / profile readback の記録は 1 件も無い**（grep 実測 0件）。
つまり「完成度90%」は `PROFILE-ASSETS.md` に手書きされた 8-31 時点の一回限りの値で、loop は profile を継続監視していない。
**profile が劣化・reset されても誰も気付かない構造。** Lancers 公式は「完成度が高いと受注率が14倍」と明示しており、
監視不在は最上位 leverage の放置。

Lancers 公式の「完成度100%の内訳」は 3 出所（help.lancers.jp / lancers.jp/faq / info.lancers.jp）を当たったが非公開。
公式が受注率向上要素として挙げるのは: 顔写真 / 自己紹介文 / 4つの認証 / ポートフォリオ / パッケージ出品
（lancers.jp/help/beginner/lancer/profile）。

- Lancers 応募60件の内訳: open 21 / selecting 14 / canceled 11 / ended 10 / unknown 4。**明示的 rejection は記録なし、受注も0** — 落選というより案件側の流札が主。
- Coconala outcome 549件: we_won 6 / someone_contracted 128 / closed_unfilled 394。勝率 ~1.1%（応募母数比）。
- gig 3 platform は component 重複ではなく共有 profile + platform別 adapter の構成（適切な分業、再発明なし）。
