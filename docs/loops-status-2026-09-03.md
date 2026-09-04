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

## TODO（この順。順序 SSOT — Dais 明示なしに変更禁止）

順序改定 2026-09-04: Dais 明示指示「まず Coconala 出品(storefront)を直す → Lancers 完全プロフィールで応募 → CrowdWorks」。#1〜#3 を gig 3 platform で固定、以降は 9/3 順を維持。
各項目の DONE 条件は「コードが直った」ではなく「**外形的な実測 evidence が出た**」。evidence 無しで次へ進まない。

0. **全 loop の LLM provider を Claude Sonnet に統一** — Dais 指示。棚卸し 2026-09-04 実測:
   - 変更点は 1 箇所: `runtime/agent-runner/config.json` の `task_classes.*.candidates`（gig 4 lane / job-search / capafy / alpaca / marketing が共有）。Writer は `model-runner.sh` で既に claude。franklin×2 は別 repo（対象外）。
   - 現状: ほぼ全 class が `codex@acct2` 第一。claude fallback 無し 14 class（reply-semantic / application-intent-planner / marketing / diagnostic / composition / tool / repeatable / high-value / affiliate×2 / writer-repair 等）は `transient_quota` で死亡中（capafy・alpaca・reply-detector で実測）。
   - 罠1: deployed release `20260904T010225-659deab7` の config は repo と drift（planner の claude-direct fallback が deployed では消失）。修正は release 経路で出荷しないと効かない。
   - 罠2: claude leg は配線だけでは通らない（job-search で claude fallback が `validation_or_task_failure` rc=1、storefront で 160s timeout）。`claude` provider = cli-proxy `:8317` 経由、`claude-direct` = 素の CLI。どちらを既定にするかは storefront 修理の実測結果で決める。
   - `skills/earn/gig/agent-runner/` は未使用の複製（`gig_paths.py:21` は runtime 側を指す）→ 削除候補。
   手順: storefront の claude 経路が実測で通る → その provider 設定を全 class の第一候補に、codex は fallback（9/7 まで死）→ release 出荷 → 各 loop の次 wake attempts で `provider=claude rc=0` を readback。
   DONE: 全 loop の直近 wake の attempts で provider=claude rc=0。codex 依存で落ちる loop が 0。
1. **Coconala storefront 復活 → 出品カタログ化（最重要・最も汎用）**
   Dais 方針: 出品は 4 lane で最も汎用。サービス自体にレビューが蓄積し recurring になる。上限 20 本を「上手くいっている競合の出品を見て写す」。特化はシステム開発（0→1 開発、Web/アプリ、修正）。出品 asset は platform 非依存で共有し、skill で定義して Lancers/CrowdWorks へもそのまま流す。
   進捗 2026-09-04:
   - a. **DONE** — 14 件 `受付休止中` → `公開中`（commit `665bd1acd`、effects.jsonl reopen 14 行、readback 受付休止 0）。根本原因: 一覧 scraper が `受付休止中` を読めず `state:None`、contract 検証が 14 件を毎 wake 捨てていた。
   - a'. **DONE** — `listing_contract_family_missing:4371816`。repo 外 state `~/gig/private/storefront-bundle/families.json` の family 欠落を復元。
   - b. **進行中** — lane の create path が `storefront_create_proposal_failed`（#0 の provider 問題）。claude 経路を直して lane が自分で出品できる状態へ。
   - c. **競合調査 → 出品カタログ 20 本** — Coconala「システム開発・制作」「Web/業務システム」「AI」上位出品（売上件数・星5）を lane 既存の competitor 観測（`competitor-*.json`）で収集し、title/価格帯/構成/FAQ の共通パターンを抽出。雛形は `~/gig/applied.jsonl` 高単価案件（¥300,000/¥250,000/¥180,000）。asset は `skills/gig-work/profile/listings/*.json`（platform 非依存: title/body/価格tier/納期/FAQ/画像）に置き、skill で「出品 asset の作り方・流し方」を定義。
   - d. **公開** — カタログから順に公開（上限 20）、各 wake で公開状態と購入数を readback。
   DONE: 公開 ≥ 15 件、うちシステム開発系 ≥ 5 件が公開 URL で readback、wake exit 0、replay effect 0。
1'. **Coconala paid lane: 全 client に返信・提出** — 実測未（Dais 報告: 一部 client に返信/提出していない、取りこぼしあり）。paid lane の state で「未返信 client 数」「未提出 見積り数」を実測し、取りこぼし 0 にする。
   DONE: paid lane の wake summary に unanswered_clients=0、未提出 0、かつ実際の返信 receipt ≥1。
2. **Lancers 応募復旧 + 完全プロフィール応募** — `application_loop.py:320-350` `_validate()` が 1 行不正で batch 全滅（`planner_contract_invalid`、9/4 も継続、今日 fresh 判断 0）。不正 row は skip、健全 row だけで判断へ。profile は 9/4 に avatar 登録で 90%（残り電話認証のみ、blocker にしない）。
   DONE: 次 wake で `error` 消滅・`eligible_count > 0`、`application_verified` 60 → 61 以上。
3. **CrowdWorks 復旧** — 実測: `account.json` が 8/11 から `status: input_required`（credential 待ち）で application lane exit 1。9/3 に書いた `hours_limit` 文字列説は repo/state に該当ファイル無し（**誤りとして取り消し**）。credentials.json SSOT から再ログイン → 4 lane を launchd に bootstrap。
   DONE: `application-receipts.jsonl` に 8/11 以降初の receipt 1 件。
4. **profile readback を loop 化** — 3 platform の公開プロフィールを定期 readback し完成度を state に記録（Lancers storefront lane は 9/4 から `profile_completion_percent` を返す。Coconala/CrowdWorks は未）。
   DONE: `~/.local/state/anicca/*/profile-readback.json` が 2 回目 wake でも更新。
5. **Coconala revenue collector 復旧** — `~/gig/earnings.jsonl` 最終行 8/12。専用 plist 無し。
   DONE: 本日日付の行が入る。
6. **Fundraiser 再起動** — 8/31 disk 事故停止、未復帰。 DONE: accelerator 応募 1 件の受領証跡。
7. **Agent economy 復旧** — franklin1 git 衝突 / franklin2 proxy 429 / daemon 未復帰。 DONE: 両 franklin が wake 完走、ledger に本日行。
8. **Writer 売上計測復旧** — DONE: `sales-ledger.jsonl` に `ok:true` 1 行。
9. **Job hunter 拡張** — `runner_failed` 修正 → remote + Tokyo 一般求人。 DONE: 応募 1 件の受領証跡。
10. **LM Cloud 出荷** — QR onboarding → X 配布 → Stripe 初 charge。 DONE: `new charges: 1`。
11. **Alpaca 修復 + hackathon 提出** — DONE: 提出受領。
12. **Capafy 販売再開** — postiz self-host 含む marketing 接続。 DONE: 新規注文 1 件。
13. **共有 component / 「金を刷る loop を作る skill」化** — 実測: 共有 profile を読むのは Lancers のみ（`storefront_offer.py:20`）。Coconala/CrowdWorks は未接続。 DONE: skill で新 loop 1 本、既存資産再利用を実証。
14. **README を real-time status に** — DONE: loop が書き換えた README diff が commit される。

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
