# Naïve・自律企業・評価基盤の調査記録

観測日: 2026-11-02。実行順と状態の正本は unified SSOT。本資料は根拠と提案であり、別の実行キューではない。

## 要点

Naïveは自律企業向けの実行基盤・会社テンプレート・Studio・ベンチマークをまとめる会社。SDKはその接続面である。「Naïve自身が社員ゼロ」「公開スコアが実利益」「AniccaのNaïve統合が稼働済み」のいずれも今回の根拠からは主張できない。

推奨は、既存の一事業をNaïveから完走させる限定統合と、既存LM-EABの拡張。会社全体の移植や新しい評価プラットフォームの新設は先行させない。

## 社内の現在地

| 対象 | 今回確認した根拠 | 言えること・残る穴 |
|---|---|---|
| Naïve統合 | GitHub現行mainの `docs/company-state/SPEC.md` §6.7 | 10/28記録はチーム設計書初版と新規セットアップ着手を記載。セットアップ不在の調査はその時点のVM/repoについての記録。現在の全環境不在の証明ではない |
| 設計書 | 同資料は `lm-cloud-naive-team-spec-2026-10-28.md` をremote goalのhidden_filesとして参照 | その本文、後続ログ、agent/session ID、deploy receipt、請求のreadbackを今回取得していない。Grok/Museの実装完了は未確認 |
| 担当 | 同資料は `anicca-lm-cloud-loop` を担当として記載 | Grok Botの停止・Muse引継ぎも10/28記録。現時点のプロセス停止と断定しない。参謀Grokと配信Grok Botも別の役割 |
| ローカル検索 | canonical mainのdocs/specsと主な関連repoをSDK名・domain名で検索 | 稼働済みNaïve appの配置を発見できない。検索は全remote VMを含まず、存在しないことの証明ではない |
| LM-EAB | `apps/life-manager/eval/economic-autonomy/`、`docs/evals/lm-economic-autonomy.md` | scorer、record契約、runner、5個のpublic synthetic fixturesが存在。tuning3 / held_out2。ラベルheld_outは秘匿テストを意味しない |
| 今回の検証 | records/score/runの3 test filesを `node --test` で実行 | 42/42成功。実agent実行・実利益・provider動作の試験ではない |

旧設計資料の「branch-only」「4ケース」「41 tests」は当時の記録であり、現在mainの5ケース・42 testsより古い。過去の記録を消さず、現在の判定にはmainと今回の実行を使う。

## SDKの新旧

旧スターターのREADMEは `@usenaive-sdk/node ^0.3.0`、`NAIVE_API_KEY`、`naive.forUser(id)`、Account Kit、`agentTools()` を示す。[公式旧スターター](https://github.com/usenaive/naive-starter-template)

現在docsはManaged AgentsのSDKを `@usenaive-sdk/vetta`、APIを `api.vetta.sh`、CLIを `vetta` と明記する。その上の会社層はblueprintと `naive.config.ts` / `naive up`。[公式docs](https://usenaive.ai/docs)

現行media-blueprintのpackage.jsonはblueprints `^0.12.1`、vetta-cli `^0.6.0`、app `^0.1.0` を宣言する。これは取得したmanifestの範囲指定で、npm最新versionやAnicca導入versionの確認ではない。[manifest](https://github.com/usenaive/media-blueprint/blob/main/package.json)

旧API keyと新runtimeの互換性・workspace対応・権限を推測しない。Naïve/Vettaを示すcredentialのmetadata一致をprivate SSOTの全件読込から探索したが該当serviceを発見できない。別名・別vault・remote保持の可能性を残し、「会社として未登録」とは結論しない。秘密値は出力しない。今回は認証・key作成・signupをしない。

## ベンチマークの使い分け

| 評価 | 確認した仕組み | 私たちへの用途と限界 |
|---|---|---|
| Clipping Bench | 約30日、初期$300、決定的シミュレータ、終端精算。ルール準拠のscript baselineとhidden stateを読むoracleも表示 | 長期運用・待ち・予算・記憶・投稿規律の比較。ゲーム内$は実収益ではない。5時間cooldown等は実SNSの普遍仕様ではない |
| Short Form Bench | 7日のbrand運営、現金・在庫原価・債権債務による価値、各モデル3 seasons。simulated viewers | 営業・販売・返金・誤入金対応等。実人間の行動予測精度や因果効果は未検証 |
| Harness studies | モデルを固定してharnessを比較。terminal/business/workplace/PRD等 | モデル差と基盤差を分ける手本。小さいtask slice・seed数・不完全な費用cellを総合SOTAに拡張しない |
| LM-EAB | synthetic recordから費用・自律性・経済算術を採点 | 現状は採点器の契約確認。agentが仕事をする共通環境、独立adapter、未見課題、反復比較、実経済traceが必要 |

根拠: [Clipping](https://usenaive.ai/benchmark/clipping-bench)、[Short Form](https://usenaive.ai/benchmark/short-form-bench)、[一覧](https://usenaive.ai/benchmarks)、[Managed Agents説明](https://usenaive.ai/blogs/introducing-naive-managed-agents)。Managed Agents記事はtrial rowsを内部DBに保持し未公開と明記。Short Formは自分のagentを走らせたい場合の連絡先を掲載する。今回公開GitHubに両media simulatorの実行コードを確認できず、公開ページがあるだけで手元で再現可能としない。

推奨する評価は三層。①外部の既存benchで比較する。②LM-EABで自社業務の未見課題を比較する。③限定本番運用で実売上・費用・介入を確認する。これらは別の証拠として報告する。

LM-EABの最初の実行可能family案は、既存販売事業の「依頼→受入条件→納品→請求照合」。同じ入力・予算・制限で、固定script、現行Life Manager、Naïve経由を比較する。課題成功率、成功1件あたり費用、完走時間、介入回数/秒、重複・不明effect、費用控除後成果を分けて出す。提案であり実装済みではない。平均だけでなく試行数・分散・失敗例を公開する。反復回数はpilot分散と費用から定め、3回を統計的十分性としない。

## ハッカソンまでの残作業案

公式eventは11/7–8 SF、全teamのNaïve SDK使用、承認された参加者のみ、実稼働のlive demoを要求する。Naïve側LPの賞品TBDに対し、YCイベント本文は賞品詳細を掲載する。現金賞金と現物・creditの総額を混同しない。[YC公式イベント](https://events.ycombinator.com/naive-autonomous-companies-hackathon)、[Naïve公式LP](https://usenaive.ai/hackathon)

公開本文には、事前開発済み全成果物の持込みを許可する明文を確認できない。事前の調査・環境準備・評価設計は進め、既存部分と会期中の変更をcommitで分けて開示する。持込み適格性は運営規約/本人宛案内の確認事項として残す。参加承認・渡航の確認も今回していない。

1. remote goalの設計書・最新ログ・配置先を取得し、現行担当と実行環境を特定する。
2. 既存credentialの保管先・org・残高・spend cap・SDK世代を照合し、現行APIのread-only疎通を確認する。
3. 一事業の一業務を選び、Naïveで実際にagent/sessionが動く最小adapterを作る。既存の配信ownerや本番scheduleを二重起動しない。
4. 顧客獲得→制作/納品→請求/費用照合のうち実際に完走した範囲を記録し、人間・外部AIによる修復も介入として記録する。
5. 同条件baselineを取り、2–4分のlive demoを「依頼・判断・成果・介入・費用」で構成する。事前/会期中の成果を分ける。

これは既存全体TODOの無断reorderではなく、Naïve laneを受け入れる際の依存順。優勝・売上の保証ではない。

## 分野の学習地図

- Naïve: 会社をtemplateとして配布し、runtimeと評価を接続する。[会社の定義](https://usenaive.ai/blogs/what-is-an-autonomous-company)
- Andon Labs: シミュレーション→実店舗運営→Pion。自社記事はシミュレーションと現実の隔たり、記事時点で店舗/caféが未黒字であることも説明する。[Pionの背景](https://andonlabs.com/blog/why-we-built-pion)
- Paperclip: self-hosted OSSで組織図・予算・governanceを扱う。人間による方向付け・承認を明記。[公式about](https://paperclip.ing/about/)
- Conway: agentの暗号学的identityとcreatorの登録。identityやwalletの存在は採算性の証明ではない。[公式docs](https://docs.conway.tech/automatons)
- Simile: 人間/集団の反応を扱うsimulation領域。事業を動かすagentと、顧客行動を予測するモデルは別の評価対象。[公式](https://www.simile.com/)

専門性の柱は、①長期の意思決定と状態管理 ②権限・identity・予算 ③再現可能な環境と採点 ④実利益と顧客価値 ⑤行動予測と因果介入。what-ifの予測精度と「その介入で人の生活が改善するか」を同一視しない。未見の人・期間・環境での予測評価と、同意を得た現実の介入評価を分ける。

## 記事の制作方針

参照する構成はNaïveのManaged Agents記事とAndonのPion記事。前者は結論→費用分解→比較表/構成図→実装→限界、後者は研究上の問い→実験→失敗trace→現実との隔たり→製品をつなぐ。本稿はこの構成を使い、本文・画像を転用しない。両記事の閲覧数・conversion・販売貢献は取得していないため「成果実証済みの勝者記事」とは呼べない。この穴を残した編集上の参照である。

草稿は独自のMermaid構成図と比較表を含む。画像生成・第三者画像の転載はしない。公開試験では読了率、出典クリック、評価再現手順への遷移、適格な問い合わせを測る。現在それらの測定値はない。

## 取得と検証の限界

Firecrawl skillを読んでconnector検索を試みるが、空link_id拒否後、非空IDによる実行は `Unknown tool(firecrawl.firecrawl_search)`。成功や収集credits=0を主張しない。代替の公式ページ取得、crwlによるYC event本文取得、ghによる公式repo/現行mainを使う。remote goalのhidden_filesとlive Naïve orgは未取得。

変更は文書だけ。SDK導入、投稿、営業連絡、決済、運営への問い合わせ、production loop変更は行わない。
