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
| 1 | Gig: Coconala | 🟢 唯一の稼ぎ頭 | 4 lane稼働中、応募継続（9/2最新）、¥129,636 | revenue collector が 8/15 から停止 → 今の残高が見えない。paid/storefront lane が間欠 fail |
| 2 | Gig: Lancers | 🔴 応募停止中 | 6 job稼働だが application lane が毎tick `planner_contract_invalid`。今日 fresh判断0件 | `application_loop.py` の `_validate()`: observed 33件のうち1件でも budget_min/max_minor 不正だと batch全体を ValueError で捨てる設計。1行の毒で全滅 |
| 3 | Gig: CrowdWorks | 🔴 8/11から死亡 | application が5分毎に exit 1。4 lane は launchd に未bootstrap | `public-profile.json` の `hours_limit: "31-40"`（文字列）を validator が int 要求で reject。既知バグ（gig TODO.md L524）未修正 |
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

順序改定: 2026-09-03、Dais 承認により旧 #13（profile readback）を先頭へ前倒し。以降は 1 つずつ順に閉じる。

各項目の DONE 条件は「コードが直った」ではなく「**外形的な実測 evidence が出た**」。evidence 無しで次へ進まない。

1. **profile readback を loop 化** — `PROFILE-ASSETS.md` 手順8 の未実装分。3 platform の公開プロフィールを定期的に読み返し、完成度と欠落項目を state に記録。Lancers の職務経歴書 upload 有無もこの readback で 1 度だけ実測する。
   DONE: `~/.local/state/anicca/*/profile-readback.json` に完成度と欠落項目が記録され、2 回目の wake でも更新される。
2. **Lancers planner_contract_invalid 修正** — `_validate()` を「不正 row は skip、健全 row だけで判断」に変更（1 行の毒で batch 全滅する設計をやめる）。
   DONE: 次 wake の launchd.out.log で `error` が消え `eligible_count > 0`、かつ `application_verified` が 60 → 61 以上に増える。
3. **CrowdWorks config 修正** — `public-profile.json` の `hours_limit` を int（例 35）へ + 4 lane を launchd に bootstrap。
   DONE: exit 1 が止まり、`application-receipts.jsonl` に 8-11 以降の新規 receipt が 1 件付く。
4. **Coconala revenue collector 復旧** — 8-15 から止まっている収益取得を再稼働。稼ぎ頭の計器を直す。
   DONE: `revenue-collect.log` に本日日付の `status:ok` と現在残高が入る。
5. **Fundraiser 再起動** — disk 事故で 8-31 から停止。disk は回復済み（19Gi free）なので kickstart。
   DONE: accelerator 応募 1 件の受領証跡（確認メール or 応募 ID）を state に記録。
6. **Agent economy 復旧** — franklin1 の git 衝突解消（stash/clean）、franklin2 の proxy 429 対応、daemon 再起動。net -$18.65 の底打ちが目的。
   DONE: 両 franklin が 8-28 以降で初めて wake 完走し、ledger に本日行が付く。
7. **Writer 売上計測復旧** — Note/Substack ログイン修復。
   DONE: `sales-ledger.jsonl` に `ok:true` の実測行（金額込み）が 1 行入る。
8. **Job hunter を Workday 専用から拡張** — まず本日の `runner_failed` の根本原因修正、その後 remote + Tokyo の一般求人へ拡張。
   DONE: 応募 1 件の受領証跡。
9. **LM Cloud 出荷** — QR onboarding 最小化 → X で配布 → 初ユーザー → Stripe 初 charge。
   DONE: `stripe-revenue-poller` が `new charges: 1` 以上を観測。
10. **Alpaca 修復 + hackathon 提出** — `alpaca_pass_failed` の解消。提出は paper のままで可。
    DONE: 提出受領画面 or 確認メール。
11. **Capafy 販売再開** — marketing loop 接続（postiz self-host 検討）。
    DONE: 8-12 以降で初の新規注文が ledger に付く。
12. **共有 component / skill 化** — gig 3 platform は既に PROFILE-ASSETS.md を共有済（良）。loop-building recipe を「金を刷る loop を作る skill」へ一般化。
    DONE: skill を使って新規 loop を 1 本組み、既存資産を再利用できたことを実証。
13. **README を real-time status に** — この表を README から参照し、loop が自分で更新する仕組み。
    DONE: loop が書き換えた README の diff が commit される。

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
