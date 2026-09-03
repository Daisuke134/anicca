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

1. **Lancers planner_contract_invalid 修正** — `_validate()` を「不正 row は skip、健全 row だけで判断」に変更（batch 全滅をやめる）。修正後、次 wake で fresh判断 >0 と応募実行を実測。
2. **CrowdWorks config 修正** — `hours_limit` を int（例 35）に修正 + 4 lane を launchd に bootstrap。応募 canary 1件を実測。
3. **Coconala revenue collector 復旧** — 8/15 から止まっている収益取得を再稼働、現在残高を実測。稼ぎ頭の計器を直す。
4. **Fundraiser 再起動** — disk 回復済みなので kickstart、accelerator 応募 1件の受領証跡まで確認。
5. **Agent economy 復旧** — franklin1 の git 衝突解消（stash/clean）、franklin2 の proxy 429 対応、daemon 再起動。まず yield で黒字化の一歩。
6. **Writer 売上計測復旧** — Note/Substack ログイン修復、sales-ledger `ok:true` を実測。
7. **Job hunter を Workday 専用から拡張** — remote + Tokyo。まず今日の `runner_failed` の根本原因修正。
8. **LM Cloud 出荷** — QR onboarding 最小化 → X で配布 → 初ユーザー → Stripe 初 charge。
9. **Alpaca 修復 + hackathon 提出**（paper のままで提出可）。
10. **Capafy 販売再開** — marketing loop 接続（postiz self-host 検討）。
11. **共有 component / skill 化** — gig 3 platform は既に PROFILE-ASSETS.md を共有済（良）。loop-building recipe を「金を刷る loop を作る skill」に一般化。
12. **README を real-time status に** — この表を README から参照し、loop が自分で更新する仕組み。

## 補足事実

- Lancers profile: 公式完成度 **90%**（本人確認・NDA・avatar・portfolio 済）。残り10%は電話認証のみで、収益ブロッカーではない。
- **résumé/履歴書 field は Coconala・Lancers いずれにも存在しない**（9/3 再確認: `PROFILE-ASSETS.md` 全文 + Lancers/Coconala state dir + gig scripts を résumé/resume/履歴書/職務経歴/resume_upload で grep、0件）。両サイトとも self-intro文（300字以上、済）+ portfolio/package（済）が résumé相当で、document upload 欄自体がない。「résumé未upload」は該当なし。
- Lancers 応募60件の内訳: open 21 / selecting 14 / canceled 11 / ended 10 / unknown 4。**明示的 rejection は記録なし、受注も0** — 落選というより案件側の流札が主。
- Coconala outcome 549件: we_won 6 / someone_contracted 128 / closed_unfilled 394。勝率 ~1.1%（応募母数比）。
- gig 3 platform は component 重複ではなく共有 profile + platform別 adapter の構成（適切な分業、再発明なし）。
