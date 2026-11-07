# プラットフォーム別ベストプラクティス正本 — 2026-11-07

本人指示（2026-11-06 17:25-17:26 PST）: 「全プラットフォーム分を検索して、忘れないようファイルに記録し、実際にそれに従って行動しろ」「勝者をコピーするだけでは足りない。勝者は既に勝者でありペースを落としていることがある。各プラットフォームには『そのプラットフォームで金を稼ぐための一般的なベストプラクティス』が存在するので、それをウェブで探して従え」。

## このファイルの規律

- **「ベストプラクティス」と書けるのは、名前のある一次の発信者（勝者・運用者・公式）が実際にそう言ったことを原典で確認できた主張だけ**（AGENTS.md 絶対ルール 2026-11-06）。出典が取れない項目は「推定」と明示して分離する。
- 各プラットフォームは2層で記録する: **(A) 固定勝者個人の現在のやり方** と **(B) プラットフォーム一般のベストプラクティス**（実践者群の共通項・公式プレイブック・実測研究）。勝者の現在のペースが成長期の型を下回る場合は、その差をギャップとして明記し、量の目標は成長期の型に置く。
- 各節の形式: (1) 核（頻度・形式・課金/単価・ファネル・面内SEO、数字つき) (2) 出典 (3) 自社の現在地 (4) 従えていない点（ギャップ) (5) 次のアクション（担当ループ／既存Todoとの接続）。
- KYC（本人確認・身分証・本人の身体）が必要な手法は「実施不可」と明記する。
- このファイルは調査と記録の正本。適用（投稿・応募・設定変更）は各担当ループの仕事。

## 対象外

- **X**: 全エージェント全面停止中（再開判断は本人のみ）。ベストプラクティス調査の対象外とする。

---

# 参照で済ませる面（勝者・仕様が確定済み。再調査しない）

## LinkedIn（参照: hidden_files/linkedin-quantity-2026-11-07.md）

### (A) 勝者 Justin Welsh の現在
- 現在 約7.5本/週（CaptureFlow、直近100投稿実測）。2年平均 約12本/週。
- 形式ミックス: 全1,096投稿の約93%が引用カード画像（平均いいね3.3K）、テキストのみ約2%（同498）。

### (B) 一般ベストプラクティス／成長期の型
- **Welsh の成長期は 2本/日**（本人のコースで公言。MagicPost の26,428クリエイター実測研究、2026-06更新で照合）。現在の7.5本/週は「既に勝者になった後の減速ペース」であり、自社の量の目標には使わない。
- 量の上限層: Gary Vaynerchuk は LinkedIn で平均 約20本/週・最大6本/日（MagicPost 実測）。
- Buffer（200万投稿の実測）: 週11本以上の層が投稿あたり表示最大で、量の効果は単調増加。
- 形式: プラットフォーム側でもドキュメント形式が最高効率（Socialinsider 実測 7.00%）。

### 自社の確定量（勝者コピーと一般BPの照合結果）
- **3本/日・週21本**、枠は毎日 06:00 / 12:30 / 20:48 JST、主形式は引用カード画像つき。固定スケジュール正本と担当ループ（anicca-distribution-max-loop）本文へ反映済み・読み戻し検証済み。
- 食い違いの記録: 勝者の現在値（7.5本/週）ではなく成長期の型（2本/日）と上限層の実測（週20本級）に寄せて 3本/日を採用。理由: 自社は成長期側であり、勝者の減速ペースをコピーする局面ではないため。

### ギャップ／次のアクション
- 本日追加分はテキスト投稿であり、引用カード主形式化は次回以降のループ実行から適用（担当: distribution 系ループ）。
- エンゲージメント行動（他者投稿への反応等）は政府発行身分証の本人確認要求のため**実施不可**（KYCは行わない）。

## Apify（参照: hidden_files/apify-winner-copy-spec-2026-11-07.md）

### (A) 勝者 compass / crawler-google-places「Google Maps Scraper」
- 累計ユーザー 683,817、月間ユーザー 47,896、30日で約400万回実行、成功率 96.0%、評価 4.7／1,825件、Google Maps 分類1位、Store 内検索3語で1位（独立センサス apifystats 実測、2026-11-07）。
- 課金の肝: 買い手のプラン階層で変わる段階価格（主イベント $4.00／$3.00／$2.00／$1.50 /1,000件）＋アドオン別売り（フィルタ +$1、詳細 +$2、連絡先 enrichment +$2、レビュー・画像 +$0.50、人脈・SNS enrichment は Free 階層 +$100）。

### (B) 一般ベストプラクティス
- Apify プラットフォーム申告: 月約$1.5M を約3,900人の開発者へ支払い、開発者の取り分は pay-per-event 収益の 80%。
- dev.to の pay-per-event 実践者（Google Maps 系含む11本を Store 公開）の一次証言: Google Maps は load が永遠に発火しないため page.route() で image/font/media を abort すること、Residential プロキシが必須。
- 配信は Apify Academy 公式チェックリスト型（Store 内SEO→dev.to・YouTube・Product Hunt・Reddit→MCP・スキル集・n8n テンプレート展開）。

### 自社の現在地／ギャップ
- Actor（Google Maps Lead Scraper）は修理完了: ビルド 0.0.21、検証 Run で実データ5件取得を確認（2026-11-06）。仕様の Console 適用（段階価格・README v2・入力スキーマ）はブラウザレーンで実行中。
- ギャップ: (1) 課金が一律 $1.50 で、最大層（Free）から勝者の 37.5% しか取れていない → 階層価格へ。(2) exampleRunInput が `{"helloWorld": 123}` のまま（Store の Try it が壊れている）。(3) 入力フォームの並びがアルファベット順で Search terms が最後尾、診断用 probeUrls が公開面に出ている、フィルタ入力が未実装（受け取るだけ）。
- 次のアクション: 仕様書の完成稿を Console へ適用し公開ページで検証（実行中）。アドオン実装は A1 実フィルタ → A2 連絡先 → A3 詳細 → A4 レビュー・画像 → A5 人脈の順。

## Capafy（参照: 勝者 saya／CloneCut、価格ラダーは実測で決着済み）

### (A) 勝者 saya／CloneCut
- 実プラン: **Weekly $12.99 / Monthly $29.99 / Yearly $149.99**（2026-11-04 実測で決着。従来の「$12.50/月」は年額÷12の月換算表示）。
- CloneCut の Sold は 47,674（実測）。
- 内側配信: Video カテゴリのトップ配置＋タイトル内検索語＋公式ブログ／Publisher Guide の特集。外側配信: 自社サイト clonecut.net＋ツールディレクトリ＋レビュー記事。

### 自社の現在地／ギャップ
- 公開42件／審査中26件／Review Failed 5件（2026-11-07 09:13 JST枠実測）。直近7日売上 $26.97、新規購入者4、詳細→購入 0.15%。
- Ready 4件の公開は完了（公開ページ実開検証済み）。JD Writer v1.0.5 には「Who it's for」節が無く、次バージョンで追加が残件。
- 自社との差分は14件を別途記録済み（価格アンカーのコピーが主）。
- 次のアクション: 審査結果の確認と通過後の公開＋価格・モデル表記の再確認（担当: Capafy ループ）。毎サイクル、勝者形式の新規エージェントを最低1本出荷するのが主トラック（本人指示 2026-11-04）。

## Upwork（参照: hidden_files/upwork-winner-copy-spec-2026-11-07.md）

### (A) 勝者 Dishant A.（Bengaluru、2026-11-07 固定）
- 見出し「Expert AI Engineer | AI Agents Developer | Agentic AI | Automation」。Total earnings **$500K+**／Jobs 184／20,000+ hrs／Job Success 100%／Top Rated Plus／レビュー88件・4.9（候補12人の実測比較で選定。数字最大の Steven Paul I. $600K+ はニッチ不一致で失格）。
- 仕様ファイルにプロフィール14ブロック分解＋自社差分表あり。自社差分は実測7件（収益$0 vs $500K+、レビュー0 vs 88件等）。

### ギャップ／次のアクション
- 未実測: 勝者の時給・コンサル価格、自社プロフィール本文（Cloudflare で到達不可の期間あり）。
- 招待案件（Skyna G.、日本語会話録音プロジェクト）の返信期限 2026-11-07 15:47 JST が当面の最優先（担当レーンで送信完走を図る）。

## Contra（参照: 登録簿 files/account-registry-2026-11-07.md）

### (A) 勝者
- プロフィール構成・価格の段階設計は **DigiNo の型**。プロフィール勝者は **Nikol Hayes**（$100K+ Earned・21 Paid projects・評価5.00・Top Independent／YC Hired）。

### 自社の現在地／ギャップ
- Applied 累計18件（2026-11-06 実測）。30日閲覧3、Earned $0、Discovery 32 pts。受付状態 Available（期限 2026-12-07 へ延長済み）。
- 最新コミュニティ投稿（ZoOISNwM）が日本語混在の誤投稿であり、英語化が是正レーンで進行中（登録簿の言語ルール違反として記録済み）。
- 次のアクション: 英語化の着地確認後、DigiNo 型の価格段階と Nikol Hayes 型プロフィールへの差分を詰める（担当: Contra ループ）。

---

---

# 配信プラットフォーム（今回調査分）

# プラットフォーム一般ベストプラクティス調査 — Instagram / TikTok（2026-11-07）

調査と記録のみ。投稿・設定変更はしていない。
調査規律: 「ベストプラクティス（B層）」と書くのは、名前のある一次の発信者（公式文書、実践者本人の発信、実施主体と標本が明示された実測研究）が実際に言ったことを、原典ページを実際に開いて確認できた主張だけに限った。出典が取れないものは各節末尾に「推定」として分離した。
A層＝自社の固定勝者個人の現在のやり方（本タスクで渡された実測事実のみ。新規実測はしていない）。B層＝プラットフォーム一般のベストプラクティス。
確認日: 2026-11-07（JST）。原典を開けなかった項目は、その旨を出典欄に明記した。

---

## Instagram

### (1) 核

#### (A) 勝者の現在（固定勝者・渡された実測事実のみ）

- 英語アファメーション3面の勝者 = @iam.affirmations。日本語2面の勝者 = @motto_app_jp。僧侶2面の勝者 = Yang Mun。
- AI情報面 anicca.app2 の勝者 = @chatgptricks: フォロワー 2,758,783、投稿 2,656件、約4.1件/日、形式ミックスはカルーセル55%／動画43%。
  - 数字で見ると、この勝者の頻度（約28.7件/週）は下記B層の実測研究の「最適帯」を大きく上回る。つまりこの面では「一般論の頻度」ではなく「勝者の頻度と形式ミックス（カルーセル過半）」がコピー対象そのもの。
- 日本語面 anicca.bochi の勝者 = @sinrigaku_sns（クラスB）: フォロワー 10,236、全48本がリール単一形式。B層の「単一形式に賭けるな」とは逆の、ニッチ内勝者の実態。A層優先の原則どおり、この面は単一形式が正。
- @iam.affirmations / @motto_app_jp / Yang Mun の現在の頻度・形式ミックスの数字は、本タスクの実測事実に含まれていないため本節では書かない（未実測）。

#### (B) 一般ベストプラクティス（出典つき・数字つき）

**頻度**
- Instagram公式は頻度の公式数字を出していない。Metaは2024-10-01、プロフェッショナルダッシュボード内に教育ハブ「Best Practices」を新設し、Creation区分で「どれくらいの頻度で投稿すべきか、リールの長さ、トレンド音源とハッシュタグ」を扱うと公式発表した。つまり公式の答えは「各アカウントのダッシュボード内の個別化された提示」であり、一律の数字ではない。
- 実測研究（Buffer、2025-08-13公開、2.1M投稿／102,000アカウント、各アカウントを自分自身と比較する固定効果モデル）: フィード投稿（写真・リール・カルーセル合算、Stories除く）で、週1〜2回→週3〜5回への増量が最大の跳ね上がり。リーチ/投稿は週3〜5回で約+12%、週6〜9回で約+18%、週10回以上で約+24%（対週1〜2回）。週フォロワー成長率のモデル推定は週1〜2回 +0.12%、週3〜5回 +0.26%、週10回以上 +0.66%。投稿ゼロの週は自アカウントの通常水準を下回る（Buffer自身が「no-post penalty」と呼ぶ）。Bufferの結論は「週3〜5回が効率のスイートスポット」。
- 実測研究（Socialinsider、Instagramベンチマーク、標本 21,280,832件のInstagram投稿、2025-10〜2026-03、フォロワー1K〜1Mのブランド）: ブランドの平均月間投稿量はリール10件／画像8件／カルーセル5件（合計約23件/月 ≒ 約5.3件/週）。

**形式ミックス**
- Socialinsider 同研究: エンゲージメント率はカルーセル 0.52% ＞ リール 0.50% ＞ 画像 0.35%。投稿量最多のリールより、量が半分のカルーセルの方がエンゲージメントで勝つ。同研究の明示結論は「各形式には別の役割があり、単一形式に全てを賭けるのはほぼ常に悪手」。
- ただしリールは新規リーチの主経路: Mosseri「Instagram Ranking Explained」（2023-05-31）で、ReelsはExploreと同様に「見るものの大半はフォローしていないアカウント」と明記。

**ランキング／フック・冒頭**
- Mosseri（2023-05-31、公式）: 単一のアルゴリズムは存在せず、Feed／Stories／Explore／Reels／Searchは面ごとに別ランキング。Reelsの最重要予測は「最後まで見るか、再シェアするか、いいねするか、音源ページへ行くか」。低解像度・ウォーターマーク付き・ミュート・枠（ボーダー）付き・テキスト主体のリールは「見えにくくする」と明記。
- Mosseri 本人発信（2025-01、ランキング解説動画シリーズ第1回。Social Media Today 2025-01-22 が本人の言葉を転記し、本調査でその報道ページを開いて確認）: 「ランキングで最も重要な上位3シグナルは watch time、likes、sends。Insightsでは average watch time、likes per reach、sends per reach を見よ」。補足として「likesはフォロワー向け（connected）でやや重要、sendsは非フォロワー向け（unconnected）でやや重要」。数値の重み（sendsは何倍か等）は公式に一切公表されていない — 「sendsはlikesの3〜5倍」等の流布数字は出典なしとして扱う。
- フックの秒数そのもの（例: 最初の3秒）について、Instagram公式が秒数の閾値を公表した原典は本調査では確認できなかった。公式が言っているのは「watch time／最後まで見る予測が最重要」まで。3秒という数字は後述「推定」に分離する。

**オリジナリティ（コピー戦略に直接関わる公式ルール）**
- Instagram Creators 公式発表「Helping Creators Find New Audiences」（2024-04-30）: 同一コンテンツが複数見つかれば推薦されるのはオリジナルのみで、コピーはオリジナルに置き換えられ、ラベルで原作者へリンクされる。自作でも実質的に手を加えてもいない他者コンテンツを30日間に10回以上投稿したアカウント（アグリゲーター）は推薦面に出なくなる。小規模クリエイター向けに、適格コンテンツはまず小さいオーディエンスに出し、反応が良いものが段階的に広がる方式も同発表。
  - 注意: これは「他者のファイルを再投稿する」行為への規則であり、「勝者の形式・台本構造を自社制作で再現する」こと自体を禁じる文ではない。ただし自社投稿同士・勝者投稿と視覚的に同一と判定される水準のコピーは、この置き換え／推薦除外の対象になり得る。線引きは自社の制作実態で決まる。

**ファネル**
- 公式が数字で裏付けるファネル中核は「sends per reach」（DMで人に送る行動）が非フォロワー拡大の最重要シグナルという点（Mosseri 2025-01、上記）。つまり設計目標は「保存」単体ではなく「誰かに送りたくなる1枚／1本」。
- コメント数は上位3シグナルに入っていない（Social Media Today の同報道も「comments are not mentioned at all」と明記）。コメント誘導だけを目的化する設計はB層とずれる。

**面内SEO**
- Mosseri「Breaking Down How Instagram Search Works」（2021-08-25、公式）: Searchの最重要シグナルは入力テキストそのもの。マッチ対象はユーザーネーム、bio、キャプション、ハッシュタグ、場所。公式ベストプラクティスとして明記された3点: (1) ハンドル／プロフィール名にコンテンツ関連語を入れる、(2) bioに関連キーワード（と場所）を入れる、(3) キーワードとハッシュタグはコメント欄ではなくキャプションに入れる。

**収益化**
- Meta「Best Practices」公式発表（2024-10-01）: Monetization区分をダッシュボード内に置き「Instagramでお金を稼ぐ全ての方法」を扱うとしているが、金額・単価の公式数字は同発表にない。
- 自社文脈での収益化はアプリ課金への導線（プロフィールリンク／Stan型の階段導線等、勝者A層の設計）が本体であり、Instagram自体のクリエイター報酬の単価を一次出典で確認できたものは本調査ではない。単価を書く場合は「推定」に分離する（下記）。
- Instagramの収益化プログラム（ボーナス、Subscriptions、ギフト等の受取設定）は支払い情報・税務情報の登録、すなわち本人確認（KYC）相当の手続きを要するのが通常であり、自社では **実施不可（KYC）** として扱う。配信→自社プロダクト販売の導線はKYCなしで実施可能であり、そちらが正路。

### (2) 出典（Instagram）

- Adam Mosseri（Instagram責任者）・「Instagram Ranking Explained」・2023-05-31・https://about.instagram.com/blog/announcements/instagram-ranking-explained/ （本調査で原典を開いて確認）
- Adam Mosseri・「Breaking Down How Instagram Search Works」・2021-08-25・https://about.instagram.com/blog/announcements/break-down-how-instagram-search-works （原典を開いて確認）
- Meta（公式）・「Introducing Best Practices, an Education Hub for Creators on Instagram」・2024-10-01・https://about.fb.com/news/2024/10/best-practices-education-hub-creators-instagram/ （原典を開いて確認）
- Adam Mosseri 本人発信（ランキング解説動画、2025-01）／転記: Social Media Today・「Instagram Shares Algorithm Insights To Inform Strategy」・2025-01-22・https://www.socialmediatoday.com/news/instagram-shares-algorithm-insights-2025/738034/ （報道ページを開いて本人の発言文を確認。Mosseri本人のInstagram動画そのものは本調査のテキスト取得経路では開いていない）
- Buffer（データサイエンティスト Julian Winternheimer による分析）・「How Often Should You Post on Instagram in 2026? Data From 2 Million Posts」・2025-08-13・数値は本調査で開いた二次集計ページ群（creatorflow.so、instantdm.com 等、同一のBuffer原典を標本・日付つきで引用）で相互照合した。Buffer原典ページ自体はTikTok版のみ直接開いた（下記TikTok節）ため、Instagram版は「原典の数値を複数の引用元で照合」と明記する。
- Socialinsider（Elena Cucu）・「Social Media Posting Frequency vs Engagement」・標本と方法論（21,280,832件のInstagram投稿、2025-10〜2026-03）を同ページ内に明記・https://www.socialinsider.io/blog/social-media-posting-frequency/ （原典を開いて確認）
- Instagram Creators（公式）・「Helping Creators Find New Audiences」・2024-04-30・creators.instagram.com 上の発表。内容は本調査で開いた複数の確認ページ（TechCrunch 2024-04-30 報道を引く各ページ）が同一文で一致することを照合した。creators.instagram.com 原典ページ自体はテキスト取得できなかったため、その旨をここに明記する。

### (3) 自社の現在地（渡された実測事実のみ）

- アカウント9件。勝者固定: 英語アファメーション3面=@iam.affirmations、AI情報面 anicca.app2=@chatgptricks（フォロワー2,758,783・投稿2,656件・約4.1件/日・カルーセル55%／動画43%）、日本語2面=@motto_app_jp、anicca.bochi=@sinrigaku_sns（クラスB、フォロワー10,236・全48本リール単一形式）、僧侶2面=Yang Mun。
- 全アカウント下限3本/日（=21本/週/アカウント）。
- 直近30日 Views: anicca.en 53,043（前回比-29.1%）、anicca.jp.videos 8,467（-33.1%）。主エンジン2面が同時に約3割下落、フォロワーは横ばい。
- 2026-11-05監査で44投稿中「差分ゼロのコピー確認済み」は0件。
- 投稿別インサイトは取得可能。

### (4) 従えていない点（ギャップ）

1. **頻度はB層を大幅に上回っているのにViewsが約3割下落している。** 自社の下限21本/週は、Bufferの「効率の最適帯」週3〜5回、Socialinsiderのブランド実測（約23件/月）の約4倍。それでも主エンジン2面が同時に下落したという事実は、ボトルネックが量ではなく1本あたりの watch time／sends per reach（＝コピーの差分）であることを示す。B層の数字は「量を増やせば伸びる」根拠にはならない（Buffer自身、効果はアカウント自身との比較であり質が最重要と留保）。
2. **勝者コピーの未達が最大のギャップ。** 44投稿中、差分ゼロ確認済み0件。B層（Mosseri）が見る指標は average watch time と sends per reach であり、コピーの差分はこの2指標に直接効く。自社は投稿別インサイト取得可能でありながら、下落局面で「どの投稿の、どの差分が watch time／sends を落としたか」の切り分けが記録上はまだ接続していない。
3. **形式ミックスの未検証。** 勝者 @chatgptricks はカルーセル55%過半で、Socialinsiderでもカルーセルがエンゲージメント首位（0.52%）。自社面ごとの形式ミックス実績（カルーセル比率）と勝者比率の差分が、本タスクの実測事実には含まれていない。anicca.bochi の勝者は単一形式リールであり、ここはB層ではなくA層が正（ギャップではない）。
4. **面内SEOの3点（ハンドル／bio／キャプション内キーワード）が勝者コピー検証の必須項目に入っているかが未確認。** Mosseri 2021の公式3点は実装コストゼロで、Searchが入力テキスト最優先である以上、キャプション外（コメント欄）へのキーワード配置は公式と逆になる。
5. **オリジナリティ規則との距離。** 「差分ゼロコピー」をファイルの再投稿に近い形で実行すると、2024-04-30公式規則（同一コンテンツはオリジナルのみ推薦、30日10回以上の無加工再投稿で推薦除外）に触れ得る。自社制作での再現であることを制作記録で示せる状態が、推薦除外リスクへの唯一の防御。
6. **ファネル指標の置き違いリスク。** 公式上位3シグナルにコメントは入っていない。自社の検証指標がコメント数中心になっている面があれば、B層とはずれている（sends per reach＝共有数÷リーチ を主指標にすべき）。

### (5) 次のアクション（Instagram）

- 配信ループ（anicca-distribution 系ループ／固定投稿スケジュール運用）: 投稿前チェックに「average watch time、likes per reach、sends per reach」の3指標を投稿別インサイトから取得・記録する行を追加する。量（下限3本/日）は既存の固定スケジュールどおり維持し、増量では解かない。
- 勝者コピー検証（既存の copy100 監査の流れ）: 44投稿0件だった差分ゼロ確認を、面ごとに「勝者のその投稿と並べて差分を数える」形式で再実施する。特に anicca.en / anicca.jp.videos の直近投稿について、フック冒頭と sends を生む要素（送りたくなる一文／一枚）の差分を先に潰す。
- 面内SEO: 全9アカウントのハンドル／表示名／bio／キャプション内キーワードを、Mosseri 2021公式3点と勝者プロフィールとで照合する棚卸しを1回行い、登録簿（account-registry）側へ反映する。
- 収益化: Instagram内蔵の報酬・受取系（KYC必須）は **実施不可** と明記したまま触らない。収益は従来どおりアプリ導線（プロフィール→ストア）で測り、/open の数字と接続する。

### 推定（Instagram・出典なし分離）

- 「フックは最初の3秒」「最適な投稿時刻は面ごとに存在する」「ハッシュタグは3〜5個が最適」等は、本調査で一次出典（公式または標本明示の実測）を開いて確認できなかったため、ベストプラクティスとしては採用しない。必要なら別途、名前のある発信者の原典を取ってから昇格させる。
- Instagramクリエイター報酬の具体単価（RPM等）も未確認のため書かない。

---

## TikTok

### (1) 核

#### (A) 勝者の現在（固定勝者・渡された実測事実のみ）

- 勝者固定: 英語=@daily.motivation.dosis、日本語=@momo_pengram（クラスB）、僧侶=Yang Mun、本音JP=@rino_renai（クラスB）、本音EN=Rizz系、Capafy宣伝=@cosmance.co。
- 各勝者の現在の頻度・形式ミックス・ファネルの数字は、本タスクの実測事実に含まれていないため本節では書かない（未実測）。したがって「勝者が成長期より減速しているか」の判定も、渡された事実からはできない（ギャップとして (4) に明記）。

#### (B) 一般ベストプラクティス（出典つき・数字つき）

**推薦の仕組み（土台）**
- TikTok Newsroom 公式「How TikTok recommends videos #ForYou」: 推薦因子は (1) ユーザーインタラクション（いいね・共有・フォロー・コメント・制作）、(2) 動画情報（キャプション、サウンド、ハッシュタグ）、(3) デバイス／アカウント設定（言語・国・機種、ただし重みは低い）。「長い動画を最後まで見終える」ような強い関心シグナルは、同一国かどうか等の弱いシグナルより重い。フォロワー数も過去のヒット実績も、推薦システムの直接因子ではない、と公式が明記。

**頻度**
- TikTok公式「5 tips for TikTok creators」: 「投稿本数はFor You推薦のされ方に影響しない。だから自由に実験してよい」と公式が明記。頻度それ自体は公式にはベストプラクティスとして存在しない。
- 実測研究（Buffer、2025-10公開、データサイエンティスト Julian Winternheimer、11.4M投稿／150,000超アカウント、固定効果回帰で各アカウントを自分自身と比較）: 週1回→週2〜5回で views/投稿が最大+17%（効率最大の跳ね上がり）、週6〜10回で+29%、週11回以上で+34%。ただし中央値 views/投稿は頻度によらず約500（489／506／487／459）でほぼ不変。伸びるのは上位10%（p90: 週1回 3,722 → 週11回以上 14,401、バイラル比 7.6倍→31.4倍）。Buffer本人の総括: 「投稿を増やすことは主に当たる確率を上げること。TikTokは heavy-tailed で、1本当たればよい」。推奨は週2〜5回。

**フック／冒頭・形式**
- TikTok Newsroom 公式「5 tips」: 縦型動画が最良、5秒より長い動画。キャプションで文脈を足すこと。視聴維持については「watch timeが推薦因子。冒頭で注意を掴み、最後まで維持することが watchable で shareable なコンテンツを作る」と明記。For You推薦は概ね過去90日以内の動画から引かれ、新規動画のエンゲージメントのピークは公開直後、ただし数日かけて伸びるので即断しないこと。
- TikTok Creator Summit 発信（TikTok Newsroom「Scroll-stopping tips from top TikTok creators」、実践者本人の発言として掲載）: @olivialilymarks「強いフック。冒頭から注意を掴むこと、ダラダラ話さない。ティーザーか見せ場を最初に」。@morganmjames「キャプション（字幕）は決定的に重要。アクセシビリティ、伝達、維持に効く」。@roshiehharte（教育系）「小さな具体物1つから始めて物語を広げる」。
- TikTok for Business 公式「Creative Codes」（TikTok Marketing Science のメタ分析が裏付けと明記）: 構造は hook／body／close の3部。Hookについては「広告想起への影響の90%は最初の6秒以内に決まる」。Bodyで商品を画面に出す広告はブランド親和+65%・想起+25%。CloseのCTAカードは想起+45%・好感+19%。音については「ユーザーの88%がTikTok体験に音は不可欠と回答」。TikTok-first（テキストオーバーレイ、ボイスオーバー、グリーンスクリーン、デュエット等の面内機能で作る）な広告はそうでないものより行動（クリック・いいね・共有）が3.3倍、という同社の研究引用。
- TikTok for Business 公式「高エンゲージメント短尺ガイド」: 3ステップ＝強いフック（質問・共感文・大胆な主張で開く）→商品の利点で課題を解く→明確なCTA（購入方法を示す）。効く型として Trend／Problem-Solution／Tips and Hacks／Product Demo／Unboxing を列挙。67%のユーザーが「買うつもりがなくてもTikTokに購買を触発された」と回答（同ガイド内の引用）。

**ファネル／コメント**
- 公式の土台は「会話を生むこと」: Newsroom「5 tips」は captivative な動画の共通点を「物語を語り、引き込み、会話を spark すること」とし、TikTok for Business の3部構造は close の CTA を必須要素とする。コメント返信を動画化する等の個別戦術の一次出典は本調査では確認できていない（推定に分離）。

**面内SEO**
- 公式: For You では動画情報としてキャプション・サウンド・ハッシュタグが読まれる（Newsroom、推薦因子(2)）。ハッシュタグは「内容に本当に関連するものだけ。#FYP や #ForYou のような汎用タグは他のタグと同扱いで、For You入りを改善しない。数を増やしてもリーチは保証されない」と公式が明記（「5 tips」）。関連性の低い汎用タグで埋める運用は公式と逆。
- Creator Search Insights（TikTok公式の検索需要ツール、content gap = 検索されるが供給が薄いテーマの表示）の存在と使い方は、複数の二次ページが Creator Academy を引いて説明しているが、本調査で Academy 原典ページの本文はテキスト取得できなかった（ページは開いたが本文が描画されなかった）。したがって「検索需要を見てテーマを選ぶ」手順は、原典再確認まで正式なB層に昇格させない（下記「推定」寄りの扱いとし、出典欄に状態を明記）。

**収益化（数字つき・KYC明記）**
- TikTok Support 公式「Creator Rewards Program」: 参加条件は、フォロワー10,000以上、直近30日の動画 views 100,000以上、18歳以上（韓国は19歳）、Personal Account（Business不可）、対象国に居住、実名・生年月日等の真正なアカウント情報。報酬対象動画は「1分以上、オリジナルで高品質、参加後に投稿、qualified For You views 1,000以上」。qualified views は For You からのユニーク視聴で、5秒未満視聴・不正・有料・dislike 等を除く。報酬は qualified views × RPM（1,000 qualified views あたり）で計算され、RPMの公式単価は公表されていない。
- **実施不可（KYC）**: Creator Rewards は実名・生年月日等の真正情報と対象国居住を参加条件とし、申請過程で年齢・本人確認を要する。自社のエージェント完結運用では **実施不可**。同様に TikTok Shop の販売者／アフィリエイト登録も本人確認・事業者確認を要するため **実施不可（KYC）** として扱う。収益化の正路は従来どおり、動画→プロフィール／外部導線→自社プロダクト（アプリ、Capafy等）の販売であり、これはKYCなしで実施可能。
- オリジナリティ条件に注意: 同Supportページは「他者コンテンツの軽微な改変（速度変更、フィルター、固定テキスト、ステッカー）」「ループ動画、写真のみ、テキストオーバーレイのみのコンテンツ」をオリジナルでない例として明記。勝者コピーを「テキストだけ／写真だけ」の形で出す面は、仮に将来KYCが解けても報酬対象外の形式である。

### (2) 出典（TikTok）

- TikTok Newsroom（公式）・「How TikTok recommends videos #ForYou」・https://newsroom.tiktok.com/how-tiktok-recommends-videos-for-you?lang=en （原典を開いて確認）
- TikTok Newsroom（公式）・「5 tips for TikTok creators」・https://newsroom.tiktok.com/5-tips-for-tiktok-creators?lang=en （原典を開いて確認）
- TikTok Newsroom（公式）・「Scroll-stopping tips from top TikTok creators」（@olivialilymarks、@morganmjames、@roshiehharte 等、実践者本人の発言）・https://newsroom.tiktok.com/scroll-stopping-tips-from-top-tiktok-creators?lang=en-GB （原典を開いて確認）
- TikTok for Business（公式）・「Creative Best Practices for TikTok Ads / Creative Codes」（裏付け研究として TikTok Marketing Science 各調査を脚注明記: Kantar、Ipsos、Neuro-Insight 等）・https://ads.tiktok.com/business/en/blog/creative-best-practices-top-performing-ads （原典を開いて確認）
- TikTok for Business（公式）・「Making TikTok Videos For High Engagement: The Complete Guide」・https://ads.tiktok.com/business/en/blog/tiktok-short-video-best-practice?ab_version=experiment_2 （原典を開いて確認）
- TikTok Support（公式）・「Creator Rewards Program」・https://support.tiktok.com/en/using-tiktok/creator-tools/creator-rewards-program （原典を開いて確認）
- Buffer（データサイエンティスト Julian Winternheimer）・「How Often Should You Post on TikTok in 2026? Data From 11 Million+ Posts」・2025-10・https://buffer.com/resources/how-often-should-you-post-on-tiktok/ （原典を開いて確認。11.4M投稿／150,000超アカウント、固定効果回帰）
- TikTok Creator Academy（公式）・「Creator Rewards Program」・https://www.tiktok.com/creator-academy/en/article/creator-rewards-program （ページは開いたが本文テキストが描画されず、条件の確認は上記 Support 公式ページで代替した。Academy本文の直接確認は未完）

### (3) 自社の現在地（渡された実測事実のみ）

- アカウント13件。勝者固定: 英語=@daily.motivation.dosis、日本語=@momo_pengram（クラスB）、僧侶=Yang Mun、本音JP=@rino_renai（クラスB）、本音EN=Rizz系、Capafy宣伝=@cosmance.co。
- 本日は日本語5ch・英語7chとも4/4枠を全て公開（枠の消化は100%）。
- honnevideo の1本が再生3,320で本日最大。ただし全枠でコメント0件。
- 投稿経路は Postiz（有料終了 2026-11-25）。無料経路（Social Champ）は @anicca.jp の1面のみ実証済みで、残り面の移行が未完。

### (4) 従えていない点（ギャップ）

1. **頻度はB層の効率帯を大きく上回っている。** 自社は4枠/日 ≒ 28本/週/チャンネル。Buffer実測では週2〜5回が効率最大で、それ以上は中央値が上がらず「当たる確率」だけが上がる。自社の28本/週は「確率を買う」側の極端に位置するが、本日の最大再生が3,320（honnevideo 1本）に留まることは、確率を買う前提である「1本ごとの当たりうる質（フックと維持）」がまだ勝者水準に届いていない可能性を示す。量の正しさを再生の中央値ではなく p90（自社の上位10%）で判定すべき、というのがBuffer実測からの直接の含意。
2. **コメント0件（全枠）は公式B層との明確な乖離。** TikTok公式は良い動画の共通点を「会話を spark すること」とし、推薦因子(1)にもコメントが含まれる。全枠コメント0は、フック／テーマが「見るだけ」で終わり、返信・議論を生む設計（問い、賛否が割れる主張、続きを見たくなる未完結）になっていないサイン。再生3,320が出ても会話ゼロなら、ファネルの次段（フォロー、プロフィール遷移、商品導線）が構造的に発生しない。
3. **勝者A層の現在値が未実測。** 固定勝者6系統について、現在の頻度・形式ミックス・直近の伸び（減速の有無）が本タスクの事実にない。B層（週2〜5回が効率帯）とA層（勝者の実頻度）が食い違う可能性を判定できないまま、自社の28本/週が置かれている。
4. **面内SEOが公式と逆になり得る点。** 公式は「関連ハッシュタグのみ、汎用タグ（#FYP等）は無効」と明記。自社の各投稿でキャプション／タグが勝者の関連語で統一されているか、汎用タグで埋めていないかは、実測事実に含まれず未確認。
5. **投稿経路の期限ギャップ（配信基盤）。** Postiz有料終了が2026-11-25で、無料経路Social Champの実証は13面中1面のみ。B層以前の問題として、11-25以降に枠そのものが止まるリスクが残り12面分ある。これは既存の移行作業の未完であり、本調査の範囲では新規実証はしていない。
6. **収益化の形式ミスマッチ。** Creator Rewards自体は **実施不可（KYC）** だが、その公式オリジナリティ定義（テキストのみ／写真のみ／軽微改変はオリジナルでない）は、仮に導線先のプロダクト販売でも「面の信頼と推薦適格」の目安になる。自社のテキスト主体の面がこの定義にどう映るかは未点検。

### (5) 次のアクション（TikTok）

- 配信ループ（TikTok配信枠運用）: 判定指標を「総再生」から「チャンネル別 p90 再生＋コメント発生率」へ寄せる。Buffer実測の読み（頻度は中央値を上げない）に基づき、まず上位10%に入った投稿（例: honnevideo 再生3,320）のフック冒頭とテーマを、勝者の同系統投稿と並べて差分を数える。
- コメント0の解消（同ループ内）: 公式「会話を spark する」を実装項目化する — 各系統の勝者の直近投稿でコメントを生んでいる要素（問い／未完結／賛否）を実物で確認し、その要素だけを次の枠に差分ゼロで入れる。効果は「コメントが付いた投稿の比率」で測る。
- 勝者A層の棚卸し（勝者マップ更新の流れ）: 固定勝者6系統の現在頻度・形式ミックス・直近30日の代表再生を1回実測し、account-winner-map と登録簿へ書く。B層との食い違い（例: 勝者が週2〜5回に減速している等）があれば、その差をギャップとして次回更新に明記する。
- 投稿経路移行（既存の Postiz 代替作業）: 2026-11-25 の有料終了までに、Social Champ 等の無料経路を残り12面で1面ずつエンドツーエンド実証する。1面成功→次、の順を崩さない。
- 収益化: Creator Rewards と TikTok Shop 販売者登録は **実施不可（KYC）** と明記し、着手しない。収益はプロフィール導線→自社プロダクトで測り、/open と接続する。

### 推定（TikTok・出典なし分離）

- 「最適な投稿時刻」「コメント返信を動画化すると伸びる」「Series／LIVEを混ぜると良い」等は、本調査で一次出典を開いて確認できなかったため、ベストプラクティスとして書かない。
- Creator Search Insights を使った検索需要先行のテーマ選定は、公式ツールの存在自体は複数の二次情報で一致するが、Creator Academy 原典本文を本調査で直接読めていないため、B層への昇格は原典再確認後に回す。
- TikTokが公式に公表していない RPM 単価の流布数字（例: $0.50〜$2.00/1,000 views）は出典のない推定として扱い、収益計画には使わない。

---

## 両プラットフォーム共通の結論（1行）

量は両面ともB層の効率帯を既に大きく上回っており、公式と実測研究が一致して指すボトルネックは量ではなく、1本あたりの watch time／sends（IG）と会話の発生（TikTok）、すなわち勝者コピーの差分そのものである。

---

# ベストプラクティス調査：YouTube（Shorts＋長編）／Threads（2026-11-07）

作成: 2026-11-07（調査・記録のみ。本書では投稿・設定変更は行っていない）
対象: YouTube Shorts、YouTube 長編、Threads（オーガニック＋Threads Ads）

## 調査規律と読み方（全節共通）

- **B層＝プラットフォーム一般のベストプラクティス**として書いたのは、名前のある一次の発信者（YouTube／Meta の公式 Help・公式ブログ・Transparency Center、実践者本人の発言、実施主体と標本数が明示された研究）が実際に言ったことを、原典ページを `browser.open` で実際に開いて確認できた主張だけである。各主張には発信者・文書・URL を付けた。
- **A層＝固定勝者の現在**は、自社の勝者マップ（`hidden_files/account-winner-map-2026-11-04.md`、2026-11-04 再実測値）と、勝者本人／勝者が使うツールの公式ケーススタディで確認できた範囲だけを書く。勝者の現在の頻度・形式が今回の調査で実測できなかった項目は「未検証」と明記し、推測で埋めていない。
- **出典が取れなかった主張は「推定・未検証」として各節の末尾に分離した。** 世間でよく言われる数字（例: Shorts の「視聴維持率75%が合格線」「21–34秒が最適」）は、公式原典が確認できなかったためベストプラクティスには入れていない。
- **KYC が必要な手法は「実施不可」と明記した。** 具体的には YouTube Partner Program（YPP）申請に伴う AdSense 本人確認・税務確認、Studio の本人確認ダイアログを人間の身分証で通す行為が該当する。投稿そのもの（本人確認が不要な範囲）とは区別して書いた。
- 時刻はすべて現地時間（local time）表記の原典に従う。自社アカウントの対象地域での換算は本書では行っていない（推定になるため）。

---

## YouTube Shorts

### (1) 核

#### (A) 勝者の現在

対象チャンネルと固定勝者（自社実測事実）:

- `@aniccaffirmations` の勝者 = **@iam.affirmations（声なし型）**（2026-11-06 確定。旧 Innertune 固定は失効）
- `@monkmujo` の勝者 = **Yang Mun**（HeyGen アバター僧侶）

@iam.affirmations（A層）:

- 形式: 音声なし。テキストのアファメーション文を画面に並べる型。Instagram 側の実読例では、オフホワイト背景に "reminder" の見出し＋ハート＋7本の "I am …" 文を中央配置し、キャプションで「Tap ❤️ if you affirm this」型の反応とアプリへの導線を持つ投稿、および10区画に番号付きアファメーション文を流し、各区画の末尾で指定フレーズのコメント（例: "I receive"）を求めるリールが確認できた。
- 規模: Instagram フォロワー 1,816,261（自社実測 2026-11-03〜04、勝者マップ）。Instagram 投稿の表示では 1.9M followers 表記（2025-07-30 投稿時点の表示）。
- **未検証（重要）**: @iam.affirmations は Instagram の勝者であり、その YouTube Shorts 面での現在の投稿頻度・尺・タイトル形式は今回の調査では原典を開いて実測できていない。したがって「YouTube Shorts での勝者の頻度は ○本/日」とは書けない。A層として確定しているのは「声なし・テキスト文型・コメントで指定フレーズを言わせる型・アプリ導線」という形式の骨格だけである。
- 減速の有無: YouTube 面での減速は未実測のため判定不可（ギャップとして (4) に明記）。

Yang Mun（A層）:

- 形式: HeyGen のアバター＋ボイスによる実写風AI僧侶。ツール公式の顧客事例（HeyGen、制作者 Shalev Hani 本人の発言として掲載）によれば、脚本は「短く、シンプルに」が本人の学びで、凝ったグラフィックや重ね編集はせず「minimal, message-first」。1本あたり制作時間は約20分、バッチ制作して週にわたって予約投稿する。
- 頻度: 同事例で本人は「週に数本 → 毎日（daily content）へ移行した」と述べ、その転換後に頻度・リーチ・エンゲージメントが上がったとしている。対象は主に Instagram 文脈の事例であり、YouTube Shorts 単独の本数として切り分けられてはいない。
- 規模: Instagram 2.5M 超フォロワー（HeyGen 事例）。YouTube は登録者約159,000（2026-11-04 自社再実測、勝者マップ）。
- 収益化（勝者側）: 勝者マップ記載の販売価格は電子書籍 各$12.99／バンドル$19.99、30-Day Healing Journey $29.99。YouTube 広告収益が主軸という証拠は今回の原典では確認できていないため、僧侶面の収益の核は「動画 → 電子書籍・プログラム販売」として読むのが原典に沿う。
- **二次情報としての注意**: 「1日3本を4プラットフォームへネイティブ投稿」という Yang Mun プレイブックの記述は、本人の X 投稿を要約した二次記事経由でしか確認できていない。HeyGen 公式事例の本人発言は「毎日」までであり、「3本/日」を A層の確定値としては扱わない（(推定・未検証) 参照）。

#### (B) 一般ベストプラクティス（出典つき）

頻度:

- **最低投稿頻度という要件は存在しない。** YouTube 公式 Help（Search & discovery tips – Shorts）は「There is no minimum posting cadence required for your videos to perform well」と明言し、視聴者と自分の持続可能性に合う頻度を自分で決めることを勧めている。つまり「Shorts は毎日／1日○本が公式推奨」は公式には存在しない。
- 投稿時刻は長期パフォーマンスに影響するとは知られていない（YouTube 公式 Performance FAQ、長編と共通の記述。Creator Insider の Shorts 解説でも "Does posting time matter?" が独立の論点として扱われている）。

形式・尺:

- Shorts は最大3分まで（YouTube 公式 Help「Get started creating YouTube Shorts」: "short-form videos that are up to 3 minutes long"、タイトルは最大100文字、最大解像度1080p）。
- **システムは特定の形式を優遇しない。** 同 Help（Search & discovery tips – Shorts）: "Our system has no opinion about what type of Shorts you make. It also doesn't favor any particular format." 順位は形式ではなくパフォーマンスと視聴者個人化で決まる。
- 「最適な尺」は公式には存在しない（上記の帰結。尺の数字を出す主張はすべて B層には入れない）。

冒頭フック／ランキングの中核（公式が名指しした指標）:

- Shorts の順位付けで公式が名指ししたのは次の3点＋満足度である（YouTube 公式 Help、Search & discovery tips – Shorts）:
1. **% of viewers who chose to view**（視聴者が見ることを選んだ割合。いわゆる Viewed vs. swiped away）
2. **average view duration**（平均視聴時間）
3. **average % viewed**（平均視聴率）
4. 最後に、いいねと視聴後アンケートによる「楽しんだか」
- したがって公式に言えるフックの定義は「最初の画面でスワイプされず "choose to view" を取ること」までであり、「最初の3秒で○○を言え」「維持率○%が合格線」という数値つきの型は公式には無い（該当主張は推定側に分離）。
- アップロード画面には "Get feedback"（フック・ペーシング等の分析）機能があることが公式 Help に記載されている。制作後の自己採点に公式ツールが存在する、という事実までが B層である。
- 推薦システム全体は 80 billion 超のシグナルから学習し、主シグナルは clicks、watchtime、survey responses、sharing、likes、dislikes（YouTube 公式ブログ、Cristos Goodrow, VP of Engineering, 2021-09-15）。満足度は1–5星アンケートで測り、4–5星の視聴だけを "valued watchtime" と数える。

タイトル／サムネイル:

- Shorts のタイトル上限は100文字（公式 Help、上記）。
- Shorts 専用のサムネイル最適化数値（CTR目標など）は公式原典では確認できなかった。長編の CTR 基準（2–10%）を Shorts に転用することはしない（面が違うため）。

面内SEO:

- 検索面では、メタデータと検索クエリの一致、およびクリックして視聴されるかが順位要素（公式 Help、Search & discovery tips – Shorts の Search 節）。
- 人気サウンド／サンプリング音源のトレンドに乗るとサウンドページに現れる可能性が上がる（同 Help、Sounds & hashtags 節）。ただし @iam.affirmations 型は声なし・音源主軸ではないため、この lever は勝者の型とは一致しない。勝者の型を優先し、音源トレンドは型を壊さない範囲でのみ使うのが整合的である（これは自社の判定であり、公式の推奨ではない）。
- ハッシュタグは推薦を押し上げるという公式記述は確認できなかった。公式のハッシュタグ規則は「60個を超えると全てのハッシュタグが無視される」「説明文の最大3個がタイトル脇に表示される」であり、#shorts 自体は Shorts 化の要件ではない（YouTube Help のハッシュタグ規則を要約した二次確認に基づく。原典ページ自体の今回の実読はしていないため、断定はここまでとする）。
- タグ（metadata tags）は重要ではない。公式 Performance FAQ: "Not important. Tags are primarily used to help correct for common spelling mistakes."

収益化:

- YPP（広告収益分配）の Shorts 経路: **登録者1,000人 ＋ 直近90日で qualified Shorts views 10 million**（YouTube 公式 Help「YouTube Partner Program overview & eligibility」および「Get started creating YouTube Shorts」）。
- 2025-03-31 以降、Shorts の "views" は再生開始・リプレイのたびに数え（最低視聴時間なし）、従来の厳しい数え方は **"Engaged views"** と改名され、**YPP 資格と Shorts 広告収益分配は Engaged views 基準のまま**（公式 Help「Get started creating YouTube Shorts」）。表示上の views の伸びを収益資格の伸びと混同してはいけない。
- YPP 加入要件には、チャンネル収益化ポリシー遵守、対象国在住、Community Guidelines の有効な strike が無いこと、Google アカウントの2段階認証、advanced features、AdSense for YouTube アカウントのリンクが含まれる（公式 Help、同上）。
- **YPP 申請・AdSense リンクは本人確認・税務確認（KYC）を伴うため、自社のゼロパーソン運用では実施不可として扱う。** 数字の門（10M）に届く前でも届いた後でも、この門は人間の身分証なしには通らない。したがって Shorts の収益計画は YPP 広告に置かず、勝者と同様に「プロフィール／説明からの自社プロダクト（アプリ、電子書籍等）への導線」で設計するのが、原典と自社ルールの両方に整合する。
- 量産・テンプレート反復への注意: YouTube は 2025-07-15 に従来の "repetitious content" ポリシーを "inauthentic content" と改名し、反復的・大量生産的なコンテンツは従来から収益化対象外であることを明確化した、と収益化ポリシー原典を読んだ複数の二次資料が一致して報告している。**本項目は Help 原典ページ自体を今回開いていないため「二次一致報告」として記録する**（断定は原典実読後に行う）。ただし方向性として、勝者コピーであっても「同一テンプレートの量産」と判定される作り方は収益化リスクになる、という注意は残す。

#### 推定・未検証（B層に入れなかったもの）

- 「最初の3秒が全て」「維持率75%（viewed vs swiped）が合格線」「21–34秒が最適尺」「1日1–2本が理想」: いずれも第三者ブログ・まとめ記事の主張であり、名前のある一次発信者の原典を今回開いて確認できなかった。**推定として分離し、運用の判定線には使わない。**
- Yang Mun「1日3本・4面ネイティブ」: 本人主張を要約した二次記事経由のみ。A層の確定値にしない。
- Shorts の削除・再投稿、ハッシュタグ個数と推薦の相関: Creator Insider の論点としては存在するが、動画本文の逐語確認は今回できていないため数値・結論は引用しない。

### (2) 出典

- YouTube（公式）— "Search & discovery tips – Shorts"、YouTube Help — https://support.google.com/youtube/answer/11914225?hl=en&co=YOUTUBE._YTVideoType%3Dshorts
- YouTube（公式）— "Get started creating YouTube Shorts"、YouTube Help（3分上限、タイトル100文字、views／Engaged views の定義変更 2025-03-31、YPP Shorts 門） — https://support.google.com/youtube/answer/10059070?hl
- YouTube（公式）— "YouTube Partner Program overview & eligibility"、YouTube Help（1,000人＋4,000時間／10M Shorts、2段階認証・advanced features・AdSense 要件、6か月無投稿での収益化停止可能性） — https://support.google.com/youtube/answer/72851?visit_id=639275027457673968-1319602071&rd=1
- YouTube（公式）— "How YouTube recommendations work"、YouTube Help（80 billion signals、watch/search history、subscriptions、likes/dislikes、"Not interested"、satisfaction surveys） — https://support.google.com/youtube/answer/16089387?hl=en&ref_topic=9257501
- Cristos Goodrow（YouTube VP of Engineering）— "On YouTube's recommendation system"、YouTube Official Blog、2021-09-15（clicks／watchtime／survey／sharing／likes／dislikes、valued watchtime は4–5星のみ） — https://blog.youtube/inside-youtube/on-youtubes-recommendation-system/
- YouTube Creator Insider（Todd Sherman, Director of Shorts Product Management）— "YouTube Shorts Algorithm — Explained!"（viewed vs swiped away、尺、ハッシュタグ、投稿時刻、投稿量、削除再投稿、長編への影響が論点であることまでを確認。本文の逐語は未確認） — https://www.youtube.com/watch?v=n3jsYK_-aRU
- HeyGen（公式顧客事例、制作者 Shalev Hani 本人の発言として掲載）— "How Yang Mun Built 2.5M Followers with AI Video"（制作約20分／本、simple scripts、minimal message-first、バッチ制作、週数本→毎日、Instagram 2.5M） — https://www.heygen.com/customer-stories/yangmun
- 自社実測 — 勝者マップ `hidden_files/account-winner-map-2026-11-04.md`（@iam.affirmations フォロワー 1,816,261［2026-11-03〜04］、Yang Mun YouTube 登録者約159,000［2026-11-04］、電子書籍価格）

### (3) 自社の現在地（実測事実）

- チャンネルは4件。Shorts の勝者は上記 (A) のとおり固定済み。
- `@aniccaffirmations` は **Studio の本人確認ダイアログで Shorts アップロードがブロック**されている。
- `@monkmujo` は **Postiz の YouTube 日次クオータエラーで 09:30 枠が連続未達**。
- 僧侶面の制作手段である **HeyGen はクレジット0、次回リセットは 2026-11-20**。
- 既存ヒットは `shorts/zytjgLec11Q`（85回視聴）程度にとどまる。
- 監査では、公開済み Shorts 全本が「100%コピーではない」と判定された。

### (4) 従えていない点（ギャップ）

1. **公式の中核指標が自社で計測できていない。** 公式が名指しした % chose to view／平均視聴時間／平均視聴率／Engaged views で自社 Shorts を1本ずつ採点した記録が無い。85回視聴という views（再生開始カウント）だけでは、公式の物差しでは何も判定できない。
2. **勝者コピーが差分ゼロに達していない。** 監査で全本「100%コピーではない」。特に声なし型（@iam.affirmations）では音声を付けること自体が型からの逸脱であり、僧侶型では姿勢・脚本・声の同一性など既存監査の差分が残る。
3. **A層の実測不足。** @iam.affirmations の YouTube 面での現在（頻度・尺・タイトル）は未検証のまま YouTube 勝者として固定されている。面をまたいだ勝者移転になっていないかを、YouTube 面の実読で裏付ける作業が残っている。Yang Mun についても YouTube Shorts 単独の直近投稿頻度は未実測であり、「毎日」は Instagram 文脈を含む事例発言からの読みである。
4. **投稿そのものが止まる詰まりが2件重なっている。** 本人確認ダイアログ（@aniccaffirmations）と Postiz クオータ（@monkmujo、09:30枠）。公式が言う「最低頻度は無い」は「止まってよい」ではなく、自社の固定スケジュール（下限3本/日/アカウント等、自社ルール）に対しては未達である。
5. **HeyGen クレジット0（〜2026-11-20）。** 僧侶面は代替音声・静止画で埋めることが自社ルールで禁止されているため、この期間の僧侶 Shorts は正規経路では作れない。未達として数えるのが正しく、代替投稿を「投稿した」と数えてはいけない。
6. **収益導線の未整備。** YPP は KYC のため実施不可（上記）。である以上、Shorts の収益はアプリ／電子書籍への導線で測るしかないが、Shorts → プロフィール／説明 → インストール／購入の面内導線が勝者の型どおりに揃っているかの確認記録が無い。

### (5) 次のアクション

1. Studio Analytics で公開済み Shorts 全本について、公式指標（% chose to view、平均視聴時間、平均視聴率、Engaged views）を1本ずつ抜き、views（再生開始数）と分けて台帳化する。判定はこの4指標で行い、views 単独での成功報告をやめる。
2. @iam.affirmations の **YouTube 面**を実際に開き、直近投稿の頻度・尺・タイトル・コメントCTA・説明文導線を実測して A層を確定させる。YouTube 面に規模・型が無ければ、勝者固定の根拠を IG 面に限定する旨を登録簿へ明記する（面またぎの移転と誤認しないため）。
3. Yang Mun の YouTube Shorts 直近20本の投稿間隔・尺・冒頭1フレーム・姿勢を実測し、HeyGen 事例の「毎日・simple・minimal」と突き合わせて差分を数える。
4. 詰まり2件は投稿経路の問題として切り分ける: @aniccaffirmations の本人確認ダイアログは **KYC が絡むため人間の身分証で通す方法は実施不可**とし、到達可能な別経路（本人確認を要求されないアップロード経路の有無）を先に検証する。@monkmujo の Postiz クオータは代替の直接投稿経路の実証で埋める（Postiz 解約・代替の既定方針と整合）。
5. HeyGen リセット（2026-11-20）までは僧侶枠を未達として記録し、代替制作で埋めない。リセット後はバッチ制作（勝者の型）で遅れを取り戻す計画を先に置く。

---

## YouTube 長編

### (1) 核

#### (A) 勝者の現在

対象チャンネルと固定勝者（自社実測事実）:

- `@life-manager-m4p` の勝者 = **Improvement Pill**
- `@AIEntitiesClub` の勝者 = **Two Minute Papers**
- 別途、長編参照として **Bob Baker**（アファメーション長編）

Improvement Pill（A層）:

- 形式: 顔出しなしのアニメーション解説。習慣・心理学・自己改善を、研究に裏付けられた説明＋アニメーションで運ぶ型（複数資料で一貫）。
- 規模: 登録者約3,770,000（2026-11-04 自社再実測、勝者マップ）。総再生約220M・動画約340本という集計も検索で確認できるが、集計主体・時点が資料ごとにずれるため、確定値は自社実測の3.77Mのみを使う。
- **未検証**: 現在の投稿頻度・平均尺・サムネイル文言量は今回実測していない。「週○本」とは書かない。

Two Minute Papers（A層）:

- 形式: フェイスレス（本人のナレーションのみ、顔なし）。**1本＝ブレイクスルー（論文）1件**。タイトルは文ケース（sentence case）。説明文はスポンサー行 → 出典リンク → Patreon クレジットの順（勝者マップ、2026-11-04 深掘り）。
- 規模: 登録者 1,840,000（vidIQ、2026-11-03、勝者マップ）。直近12本の長編は 110K–470K 再生、中央値約313K。
- 頻度・尺（外部実測）: 2026-08-09 時点の観測をまとめたチャンネル分解では、登録者1.83M、動画1,085本、直近6本の尺は3:55–6:31、頻度は週2–3本。各動画が対象論文を明示して引用する。別カタログでも "Uploads: 2-3 per week" "Subscribers: 1.83M" と一致する。
- 収益化（勝者側）: YouTube チャンネルメンバーシップ（$5／$25 の2段が観測された）と Patreon（早期アクセス等、1.2k 表示は無料＋有料合算で有料人数は非公開）がチャンネル上に存在する。金額・人数の確定値は公開情報からは取れない。

Bob Baker（A層、長編参照）:

- 形式: 本人の声による spoken-word の朝アファメーション／ガイド瞑想。尺は5分・20分・30分帯がヒットの中心（例: "Morning GRATITUDE Affirmations 20 Minutes" 1.46M 再生、2023-01-11）。
- 規模: 登録者436,000、総再生82,906,706、動画1,600本（vidIQ、2026-11-06 更新）。
- 頻度: チャンネル説明として "publish new videos every week"（毎週新作）と自称している（チャンネル紹介文の引用を集計サイトが掲載）。実測の投稿間隔ではないため「週次を自称」までにとどめる。
- 収益化（勝者側）: YouTube 本体に加え、同一音源をポッドキャスト／ストリーミング（Spotify、Apple Music、Insight Timer 等）へ展開し、コーチング／メンタープログラム（Impact Formula Lab）へつなぐ多面展開が本人の発信で確認できる。長編アファメーションの勝者は「広告だけ」ではなく「音源資産の多面配信＋高単価プログラム」が核である。

#### (B) 一般ベストプラクティス（出典つき）

ランキングの仕組み（長編）:

- 順位は **パフォーマンスと視聴者個人化**で決まる（YouTube 公式 Help、Search & discovery tips – Video）。システムが見るのは: 推薦されたときに視聴者が見ることを選ぶか／無視するか／"not interested" か、次に **average view duration と average % viewed** で「残ったか」、最後にいいねと視聴後アンケートで「楽しんだか」。
- Home の選択は「Performance（似た視聴者をどれだけ惹きつけ満足させたか）」と「Watch and search history」で決まる（公式 Performance FAQ）。Up Next（Suggested）は視聴中の動画自体が主シグナル（公式 Help、How YouTube recommendations work）。
- 推薦は clicks だけでは決まらない。公式ブログ（Goodrow, 2021）が明言するとおり、クリックは視聴の保証にならないため 2012 年に watchtime が加わり、導入直後に views は20%落ちたが YouTube はそちらを選んだ。さらに満足度アンケート（1–5星、4–5星のみ valued watchtime）で「後悔しない視聴」を測る。

頻度・公開時刻:

- **毎日投稿も週1投稿も必須ではない。** 公式 Performance FAQ: 投稿間隔と views の伸びに相関は見られず、休止期間の長さと views の変化にも相関は無かった（数千チャンネルの分析、と公式が記載）。"quality over quantity" を公式が勧めている。
- **公開時刻は長期パフォーマンスに影響するとは知られていない**（同 FAQ）。公開時刻が効くのは Live と Premiere のみで、その場合も Analytics の「視聴者が YouTube にいる時間」レポートで決める。

尺と維持:

- 短い動画では相対視聴時間（%）、長い動画では絶対視聴時間（分）がより重要、と公式 FAQ が使い分けを明示している。したがって長編では「%を上げるために短くする」よりも「絶対視聴時間を稼げるだけの密度で必要な長さにする」が公式に沿う。
- 特定の「最適尺 ○分」という公式数値は存在しない。

タイトル／サムネイル:

- 公式の原則は **正確さ**である（Performance FAQ）: 内容を正確に表す魅力的なタイトルとサムネイルを作る。避けるべきものとして公式が列挙するのは、deceiving／misleading／clickbaity／sensational、shocking、disgusting、gratuitous violence、indecent、そして ALL CAPS や "!!!!!" のような "Loud" な表現。
- タイトル／サムネイルの変更は、それ自体ではなく「見た目が変わることで視聴者の反応が変わる」ことを通じて再評価されうる。公式は「機能しているものは変えるな」とも書いている。つまり場当たり的な差し替えではなく、反応を測る変更だけが意味を持つ。
- CTR の公式基準: **全チャンネル・全動画の半分は impressions CTR が 2%–10% の範囲**にある（YouTube 公式 Help、Impressions & click-through-rate FAQs）。新規（1週間未満）や100 views 未満では範囲はさらに広がる。Home に載って impressions が増えると CTR が下がるのは自然である、とも公式は書いている。したがって CTR は絶対値ではなく、面（Home／Search／Suggested）別・自チャンネル推移で読むのが公式の読み方である。
- Test & Compare（公式 A/B）については、勝敗は CTR ではなく **watch time share** で判定される、と YouTube の Rene Ritchie の説明を vidIQ が報じている（2025-07）。**これは vidIQ 経由の二次報告として記録する**（公式 Help 原典での今回の実読はしていない）。含意は B層の原則と一致する: クリックだけ取るタイトル／サムネイルは勝者に選ばれない設計である。

面内SEO（Search）:

- YouTube 検索の順位要素は公式に3つ: **Relevance、Engagement、Quality**（YouTube 公式 Help、How YouTube search works）。Relevance はタイトル・タグ・説明文・動画内容とクエリの一致で推定され、Engagement は「そのクエリに対してその動画がどれだけ視聴されたか（watch time）」が関連性の証拠になる。Quality は専門性・権威性・信頼性（E-A-T）のシグナル。
- 検索結果は「最も再生された順」ではない（公式 Performance FAQ）。
- タグは重要ではない（同 FAQ、Shorts 節と同一文言）。SEO の主戦場はタイトル・説明文・動画内容そのものと、そのクエリでの視聴実績である。

収益化:

- YPP 長編経路: **登録者1,000人 ＋ 直近12か月で qualified watch hours 4,000時間**（公式 Help）。Shorts フィードでの視聴時間はこの4,000時間には算入されない。6か月以上アップロードも Posts も無いチャンネルは収益化を停止されうる（同 Help）。
- 収益分配率は本書の原典範囲では確認していないため書かない（数字が必要なら公式の収益モジュール原典を別途実読すること）。
- **YPP／AdSense の本人確認・税務確認（KYC）は実施不可**（Shorts 節と同理由）。長編の収益計画も、勝者（Two Minute Papers のメンバーシップ／Patreon、Bob Baker の音源多面配信＋プログラム）のように **プラットフォーム広告の外側に収益面を持つ設計**が前提になる。なおメンバーシップ等のファンファンディング機能自体も YPP 加入が前提になる場合は、その時点で同じ KYC の門に当たるため、加入可否は機能ごとに見分ける必要がある（ここは未検証として残す）。

#### 推定・未検証（B層に入れなかったもの）

- サムネイルの「顔あり69%」「 overlay テキスト中央値5語」「高コントラスト56%」等の vidIQ 2026 年調査（500本の breakout 動画）数値は、vidIQ 原典ではなく第三者ブログの要約経由でしか今回確認できなかった。**原典未実読のため推定側に置く。** 採用するなら vidIQ 原典を開いてからにする。
- 「サムネイルは3要素まで」「タイトル50文字以内」等の MrBeast 由来とされる型は、本人の一次発信原典を今回開いて確認できなかったため B層に入れていない。
- Improvement Pill の現在の投稿頻度・尺、Bob Baker の実測投稿間隔は未検証。

### (2) 出典

- YouTube（公式）— "Search & discovery tips – Video"、YouTube Help（performance と personalization、avg view duration／avg % viewed、likes／surveys） — https://support.google.com/youtube/answer/11914225?hl=en&co=YOUTUBE._YTVideoType%3Dvideo
- YouTube（公式）— "YouTube performance FAQ & Troubleshooting"、YouTube Help（Home の Performance／history、Search の2要素、タイトル／サムネイル最適化と禁止表現、タグは重要でない、毎日投稿は不要・休止と相関なし、公開時刻は長期成績に影響しない、相対 vs 絶対視聴時間） — https://support.google.com/youtube/answer/141805?hl=en
- YouTube（公式）— "How YouTube search works"、YouTube Help（Relevance／Engagement／Quality） — https://support.google.com/youtube/answer/16090438?visit_id=638815605160947728-37981164&p=how_search_works&rd=1
- YouTube（公式）— "Impressions & click-through-rate FAQs"、YouTube Help（半数のチャンネル／動画は CTR 2%–10%） — https://support.google.com/youtube/answer/7628154?hl=en
- YouTube（公式）— "YouTube Partner Program overview & eligibility"、YouTube Help（1,000人＋4,000時間、Shorts 時間は算入されない、6か月無活動での停止） — https://support.google.com/youtube/answer/72851?visit_id=639275027457673968-1319602071&rd=1
- Cristos Goodrow（YouTube VP of Engineering）— "On YouTube's recommendation system"、YouTube Official Blog、2021-09-15 — https://blog.youtube/inside-youtube/on-youtubes-recommendation-system/
- vidIQ（実施主体明示の集計）— "Bob Baker Affirmations YouTube Stats"（登録者436K、総再生82.9M、動画1,600本、2026-11-06 更新。ヒット動画と尺の内訳） — https://vidiq.com/youtube-stats/channel/@bobbaker/
- TakehomeHub（チャンネル分解、2026-08-09 観測）— "Two Minute Papers: a research habit turned publishing operation"（登録者1.83M、1,085本、直近6本 3:55–6:31、週2–3本、メンバーシップ $5／$25、Patreon の表示人数の注意） — https://takehomehub.com/creator-money/channel-breakdowns/two-minute-papers
- AIDataHub（チャンネルカタログ、2026-04〜09 検証）— Two Minute Papers: Subscribers 1.83M、Uploads 2-3 per week — https://www.aidatahub.io/youtube
- 自社実測 — 勝者マップ `hidden_files/account-winner-map-2026-11-04.md`（Improvement Pill 登録者約3,770,000［2026-11-04］、Two Minute Papers 登録者1,840,000［vidIQ 2026-11-03］・直近12本 110K–470K 再生・中央値約313K・説明文の型）

### (3) 自社の現在地（実測事実）

- 長編の勝者は `@life-manager-m4p` = Improvement Pill、`@AIEntitiesClub` = Two Minute Papers に固定済み。別途 Bob Baker を長編参照として置いている。
- Shorts 側の詰まり（本人確認ダイアログ、Postiz クオータ、HeyGen クレジット0）が長編制作の工数配分にも影響する状態にある（Shorts 節 (3) 参照）。
- 長編単独の視聴実績として本調査に渡された実測は無い。既存ヒットとして示されているのは Shorts の85回視聴のみであり、長編の CTR・平均視聴時間の自社実測は本書の材料に含まれていない（＝未計測として扱う）。

### (4) 従えていない点（ギャップ）

1. **長編の公式物差し（CTR、平均視聴時間、平均視聴率）が自社で未計測。** 公式が「この3点で見る」と名指ししているのに、自社長編の数字が材料に存在しない。測っていないものは改善も報告もできない。
2. **勝者の形式ミックスの棚卸し不足。** Improvement Pill の現在の頻度・尺・サムネイルが未実測のまま勝者固定されている。Two Minute Papers は頻度（週2–3本）・尺（約4–6分半）・1本1論文・説明文の型まで揃っているのに対し、Improvement Pill 側は規模だけが根拠になっている。A層の厚みがチャンネル間で不均一である。
3. **タイトル／サムネイルの正確さの検証が無い。** 公式が禁じる clickbaity／sensational／ALL CAPS 等に自社長編が触れていないか、CTR 2–10% という公式範囲と面別に突き合わせた記録が無い。
4. **検索SEOの実装確認が無い。** 検索の3要素（Relevance／Engagement／Quality）のうち、自社で操作できるのはタイトル・説明文・内容とクエリの一致だが、想定クエリを決めてタイトル先頭に置く運用が型として固定されているか不明である。タグへの工数は公式が「重要でない」と言う以上、割く根拠が無い。
5. **収益設計が YPP 前提のままでは成立しない。** YPP は KYC で実施不可。自社長編は、勝者のように広告外の収益面（自社アプリへの導線、メンバーシップ相当の自社課金、音源・記事への展開）を説明文・固定コメント・終了画面で設計する必要があるが、その導線の有無と転換の計測が無い。

### (5) 次のアクション

1. 自社長編全本について、面別 CTR（Home／Suggested／Search）、平均視聴時間、平均視聴率、検索クエリ別視聴時間を Studio から抜き、公式範囲（CTR 2–10%）と並べた台帳を作る。未計測を解消してから次の制作判断をする。
2. Improvement Pill の直近投稿を実際に開き、頻度・尺・タイトル形式・サムネイル（文字量・顔の有無・コントラスト）を実測して A層を Two Minute Papers と同じ厚みに揃える。実測できないまま「勝者をコピーしている」と報告しない。
3. 次回長編から、想定検索クエリを1本につき1つ決め、タイトルと説明文冒頭と内容冒頭の一致をチェック項目にする（公式 Search の Relevance 対応）。タグ整備への工数は止める。
4. タイトル／サムネイルは Test & Compare の考え方（勝敗は watch time 側で見る）を前提に、変更したら反応（CTR＋平均視聴時間のセット）で判定する。クリックだけ上がって視聴時間が落ちる変更は失敗として戻す。
5. 長編の収益導線を YPP 外で設計し直す: 説明文の型を勝者（Two Minute Papers の出典明示の型）に倣いつつ、自社アプリへの導線を固定位置に入れ、導線クリック → インストールを計測できる形にする。YPP 申請は **実施不可（KYC）** として計画から外す。

---

## Threads

### (1) 核

#### (A) 勝者の現在

対象アカウントと固定勝者（自社実測事実）:

- `@anicca.en` の勝者 = **@thriveanxietysolutions のみ**（旧 @manifest_with_selflove 等の併記は失効）

@thriveanxietysolutions（A層）:

- 主体: Carrie Howard。本人の他面プロフィール経由で確認できるテーマは anxiety（不安）、people-pleasing（人に合わせすぎる傾向）、boundaries（境界線）、self-trust で、ポッドキャスト出演時の紹介も同テーマで一貫している。
- 規模: フォロワー 111,839（2026-11-04 自社再実測、勝者マップ）。
- コピー元として自社が指定している投稿例: `https://www.threads.com/@thriveanxietysolutions/post/DfNFNi4IEAF`（再読時いいね136、勝者マップ記載）。
- **未検証（重要）**: 勝者の Threads での現在の投稿頻度、返信量（他者への reply の本数）、形式ミックス（テキストのみ／画像付き／カルーセル／動画の比率）、トピックタグの使い方、投稿時刻帯は、今回の調査では実測できていない。Threads は検索・外部クロールでの投稿一覧取得が弱く、勝者の「現在のやり方」の数字は取れなかった。したがって A層として確定しているのは「不安ニッチの単一テーマ、教え系の投稿がコピー元として指定されている」という範囲までであり、頻度・返信の型は未確定である。
- 減速の有無: 未実測のため判定不可。フォロワー数の時系列（111,839 からの増減）を取る仕組みが無ければ減速は検知できない（ギャップとして明記）。

#### (B) 一般ベストプラクティス（出典つき）

会話が核であること（公式数値）:

- **Replies account for almost half of the views on Threads**（返信が Threads の views のほぼ半分を占める）。Meta 公式 Newsroom（2024-10-21、Threads 教育的インサイトの発表）が自社データとして明示した数字である。「投稿する」ことと同等以上に「会話に入る」ことがリーチの源泉だというのが公式の位置づけである。
- Adam Mosseri（Head of Instagram、当時 Threads も統括）は Platformer のインタビューで "The sum of all your replies is about as valuable as the sum of all the value of all your posts" と述べ、成長したいなら **"reply much more than you post"**（投稿よりずっと多く返信せよ）が要約として繰り返し引用されている（Buffer の返信研究記事が Platformer を出典として明示し、原典として開いて確認した）。
- Buffer の実測研究（データサイエンティスト Julian Winternheimer、128,000件超の Threads 投稿、固定効果回帰で各アカウントを自分自身と比較）: **自投稿へのコメントに作者が返信した投稿は、返信しなかった投稿よりエンゲージメントが約42%高い**。全プラットフォーム中で最大の lift（LinkedIn +30%、Instagram +21% が続く）。Buffer 自身が「相関であり因果の保証ではない」「自然に伸びた投稿ほど返信も増えうる」と注意を明記しているため、42% は「返信した投稿の方が伸びている」という観測値として使う。

頻度:

- **Meta 公式の最低線: 週に少なくとも2–5回投稿**（同 Newsroom、2024-10-21）。根拠として公式は「投稿頻度が高いほど1投稿あたりの impressions が高い相関がある」と述べている。これは「最低線」であり上限ではない。
- Buffer の成長実践（Buffer 公式ブログ、Threads で伸ばした自社チームと成功クリエイターの観測）: 成功している Threads クリエイターは **1日1–3回以上**投稿し、**他者投稿への返信もその総数に数える**。Buffer チームの推奨は、速い成長 = 3回以上/日、安定成長 = 2–3回/日、最低維持 = 1回/日。
- この2つは矛盾ではなく層が違う: Meta の数字は「週2–5回未満では土台に乗らない」という公式最低線、Buffer の数字は「伸ばしている実践者の実量」である。自社の下限ルール（3本/日/アカウント）とも照らせば、運用目標は Buffer 側（返信込みで1日複数回）に置き、Meta の週2–5回は「これを割ったら公式最低線割れ」という警報線として使うのが、原典に忠実な読み方である（この使い分け自体は自社の判定であり、原典の文言ではない）。

形式:

- **テキスト付きの動画・写真・カルーセル投稿は、テキスト無しのものより平均 views が高い**（Meta 公式 Newsroom）。テキストと動画を1投稿に組み合わせることも公式が推している。
- おもしろい（funny）コンテンツは views が高い（同公式）。
- 会話を生む投稿ほど推薦されやすい（同公式: "Posts that drive conversations are more likely to get recommended"）。
- 上位クリエイターは **Threads 専用に作ったオリジナルコンテンツ**を投稿している（同公式）。他面の投稿のそのままの流用は、公式の言う「勝者の型」とは逆である。
- 形式別のエンゲージメント率については、Buffer の 2026 年 State of Social Media Engagement（52M 投稿分析）を要約した二次資料で、Threads の中央値エンゲージメント率は動画 5.55%、画像 4.55%、テキスト 2.79%、リンク 2.34% と報告されている。**この報告書の原典ページ自体は今回開いていないため、確定値ではなく二次報告として記録する。** 方向性（動画・画像 ＞ テキストのみ ＞ リンク）は Meta 公式の「テキスト付きメディアが views で勝つ」とも矛盾しない。

時刻:

- Buffer の実測研究（Buffer 経由で投稿された **2.5 million 件**の Threads 投稿、2026-02-04 公開、指標は median engagement）:
- 最良の単一枠: **木曜 9:00**。次点は水曜 12:00、水曜 9:00。
- 最良の窓: **平日 6:00–11:00**。
- 最良の曜日: 水曜 ＞ 木曜 ＞ 火曜。
- 最悪: 夕方 18:00–23:00（全曜日で一貫して低い）、週末（特に土曜が最低）。
- 時刻はすべて audience の local time として読む設計（Buffer が timezone を吸収して集計）。
- **衝突の明記**: Meta 公式 Newsroom は逆に「週末に頻繁に投稿するとエンゲージメントが上がりうる」と書いている。Buffer の2.5M 実測では週末（特に土曜）は最低である。一次発信者はどちらも名前があるため、両方を記録し、判定では大標本の実測（Buffer）を優先しつつ、自社アカウントの Insights で週末枠を1枠だけ残して検証するのが妥当である（優先順位付けは自社の判定）。

面内SEO／発見可能性:

- ランキングの仕組みは Meta Transparency Center のシステムカード（"Instagram Threads Feed AI system"、2025-03-07 更新）が公式原典である。3段階（inventory の収集 → signals の活用 → predicted value で ranking）で、予測対象は「いいねする確率」「スクロールで流す確率」「作者プロフィールを開く確率」「投稿を開いて次を開く確率」「**返信を作る確率**」「投稿をタップする確率」「滞在時間」など。返信の予測が独立の予測モデルとして存在する点が、YouTube の「視聴」中心と決定的に違う。
- 同カードのシグナルには、直近1時間・6時間の descendants（返信・いいね等の子孫エンゲージメント）が繰り返し現れる。つまり投稿直後の会話の立ち上がりが、その投稿の分布を決める材料として公式に組み込まれている。
- Following フィードは逆時系列（新しい順）であり、推薦は混ざらない（同カード）。
- トピックタグは1投稿に1つ。タグは「トピックのシグナル」として働き、意図した相手に届ける助けになる（Buffer 公式ブログが Threads チームの説明と自社実践をもとに記述）。Meta が「トピック付き投稿は views が多い」と分析したという報告は二次資料経由のため、確定値としては扱わない。
- 投稿の上限仕様: 本文500文字、長文は最大10,000文字のテキスト添付が可能（Meta Newsroom、2025-10 のテキスト添付発表を検索で確認。本書では仕様の存在までを記録し、運用型としては未採用）。

収益化（オーガニック）:

- Threads オーガニックに、YouTube YPP のような公式の収益分配プログラムが存在するという原典は、今回の調査では確認できなかった。**Threads の収益はオーガニック投稿そのものからは生まれず、プロフィール／投稿からの自社プロダクト（アプリ等）への導線と、次項の広告で設計する**のが原典に沿う前提である。

収益化／獲得（Threads Ads、B層）:

- 配置の仕組み（Meta Business Help Centre の内容を、2026-10-20 時点で Help 原典を確認したと明示する二次ガイド2件で一致確認。本書では「Help 由来の二次一致」として記録する）:
- Threads 広告は Ads Manager で買う。独立した Threads 専用プラットフォームは無い。
- **Threads feed 配置は Advantage+ placements ではデフォルトで選択され、手動配置でもデフォルトで選択されている。** Meta の世界展開発表（2026-01）も「既存キャンペーンへ Threads 配置を自動追加してリーチを拡張する簡単な方法」と位置づけている。
- Threads 単独配置では回せない。手動配置でも Instagram feed と併せて選択する必要がある（＝Threads だけを切り分けた純粋テストは1広告セット内ではできない）。
- 配信はモバイルのみ、Threads feed のみ。Search・Stories・DM の配置は無い。
- 仕様（同上、Help 由来）:
- 画像: JPG/PNG、推奨 1440×1440、比率 1.91:1〜9:16（4:5 より縦長は 4:5 にクロップ）
- 動画: MP4/MOV/GIF、推奨 1440×1800、同様に 4:5 クロップ。動画キャプションは未対応
- カルーセル: 2–10枚、画像のみ、ランディングURL必須
- プライマリテキスト推奨 80–160文字、見出し40文字。プライマリテキスト内に URL は不可
- 自社仕様書との照合（既存実測・既存調査）: 自社の Threads Ads 仕様書（`hidden_files/threads-ads-app-install-spec-2026-11-07.md`）では、ベンダー実績としてユーティリティのアプリインストール **CPI $0.90–$2.10**（New Public Media、47アカウント、2026-06〜07）が損益分岐 CPI $2.10–$3.57 の下限に接する唯一の Meta 系の帯として記録されている。また **Advantage+ 支出の15–30%が Threads へ無言で流れる**リスクが同仕様書に明記されている。これは上記の「デフォルトで配置に入る」という公式仕様と整合する。数字はいずれもベンダー集計の主張であり自社実測ではない。
- **** Threads Ads の支出自体は、自社仕様書の Gate 0（RevenueCat 実測5点）未通過のため現在は未実施であり、これは KYC 以前の門である。加えて、広告アカウント側で事業・本人確認（KYC）が求められる手続きが発生する場合は、その部分は **実施不可** として扱い、人間の確認で通す計画を立てない。

#### 推定・未検証（B層に入れなかったもの）

- 勝者 @thriveanxietysolutions の現在の投稿頻度・返信量・形式ミックス・タグ使用・時刻帯: すべて未実測。B層（Meta 公式＋Buffer 実測）で代替して勝者の型とみなすことはしない（A層とB層の混同を避ける）。
- 「リンク投稿は下げられる／下げられない」: Mosseri の発言をめぐる二次報道が割れており、公式原典で確定できなかったため判定に使わない。Buffer の形式別数値（リンク 2.34% が最下位、二次報告）だけを観測として残す。
- Threads の「最初の1時間が全て」という型: システムカードに1時間・6時間のシグナルが存在することは公式だが、それを「1時間で○件の返信が必要」という数値の型に変換した一次発信者は確認できなかった。数値化は推定として扱う。

### (2) 出典

- Meta（公式）— "Find Your Community With New Threads Educational Insights"、Meta Newsroom、2024-10-21 公開（replies は views のほぼ半分、週2–5回以上の推奨と頻度–impressions の相関、funny は views が高い、テキスト付き動画／写真／カルーセルが平均 views で勝つ、週末の頻繁な投稿が engagement を押し上げうる、会話を生む投稿が推薦されやすい、上位者は Threads 専用オリジナル） — https://about.fb.com/news/2024/10/find-your-community-with-new-threads-educational-insights/
- Meta（公式）— "Instagram Threads Feed AI system"、Meta Transparency Center、2025-03-07 更新（3段階ランキング、予測一覧［いいね／流す／プロフィール／返信／タップ／滞在］、1時間・6時間の descendants シグナル、Following は逆時系列） — https://transparency.meta.com/features/explaining-ranking/ig-threads-feed/
- Buffer（Julian Winternheimer、データサイエンティスト）— "Replying to Your Threads Comments Can Boost Engagement by 42%"（128,000件超、固定効果回帰、+42%、相関であり因果保証なしと明記。Mosseri の Platformer 発言 "The sum of all your replies is about as valuable as the sum of all the value of all your posts" を出典明示で引用） — https://buffer.com/resources/threads-comments-engagement/
- Buffer — "The Best Time to Post on Threads in 2026 — Data from 2.5M Posts"、2026-02-04（2.5M 投稿、median engagement、木曜9時／水曜12時・9時、平日6–11時、水曜最良、土曜最低、夕方18–23時が最悪） — https://buffer.com/resources/the-best-time-to-post-on-threads/
- Buffer — "Get More Followers on Threads: 10 Tactics to Help You Grow"（成功クリエイターは1日1–3回以上、返信も総数に数える。速い成長3回以上/日、安定2–3回/日、最低1回/日。タグはトピックシグナル） — https://buffer.com/resources/how-to-grow-on-threads/
- Meta Business Help Centre 由来の仕様（Help を 2026-10-20 に確認したと明示する二次ガイドで一致）— Zolyp "How to Advertise on Threads"（Advantage+ がデフォルトで Threads を含む、手動でもデフォルト選択、Threads 単独では回せない、仕様表） — https://www.zolyp.com/blog/how-to-advertise-on-threads
- 同上（Help 由来の仕様の一致確認）— Blackfire Marketing "Threads Ads UK"（画像1440×1440推奨、動画1440×1800推奨、カルーセル2–10枚、テキスト80–160文字、見出し40文字、本文URL不可） — https://blackfiremarketing.co.uk/blog/threads-ads-uk
- 自社仕様書 — `hidden_files/threads-ads-app-install-spec-2026-11-07.md`（CPI ユーティリティ $0.90–$2.10［ベンダー主張］、Advantage+ 支出の15–30%が Threads へ流れるリスク、Gate 0 未通のため支出未実施）
- 自社実測 — 勝者マップ `hidden_files/account-winner-map-2026-11-04.md`（@thriveanxietysolutions フォロワー 111,839［2026-11-04］、コピー元投稿の指定）

### (3) 自社の現在地（実測事実）

- `@anicca.en` の勝者は @thriveanxietysolutions に固定済み。
- Threads Ads の仕様書は作成済み（上記）。ユーティリティ CPI $0.90–$2.10、Advantage+ 支出の15–30%が Threads へ無言で流れるリスクを確認済み。ただし **Gate 0 未通のため広告支出は未実施**。
- **オーガニック側の現行運用実測は薄い。** 自社の投稿頻度・返信量・形式ミックス・時刻帯・投稿別 views／返信数の台帳が、本調査に渡る材料としては存在しない。

### (4) 従えていない点（ギャップ）

1. **最大のギャップは返信である。** 公式は「返信が views のほぼ半分」「投稿よりずっと多く返信せよ」と言い、Buffer 実測でも作者返信のある投稿が +42% である。自社の運用実測が薄いということは、返信量（自投稿への返信、他者投稿への返信）がそもそも数えられていない可能性が高い。投稿本数だけ数える運用は、Threads では半分の仕事しかしていないことになる。
2. **勝者（A層）の現在が未実測。** 頻度・返信・形式ミックス・タグ・時刻のどれも取れていないため、「勝者をコピーしている」と言える状態に無い。B層で型を補うことはできるが、それは勝者コピーとは呼ばない（自社の横展開ルールと同趣旨）。
3. **時刻の衝突を自社で検証していない。** Meta 公式（週末が効きうる）と Buffer 2.5M 実測（週末・夕方が最悪、平日朝が最良）が逆を向いている。自社アカウントの Insights で曜日・時刻別の実績が無いため、どちらの枠に寄せるかを実測で決められていない。
4. **形式が公式の型（テキスト付きメディア、会話を生む投稿、Threads 専用オリジナル）に揃っているか不明。** テキストのみの垂れ流しや他面流用が混ざっていないかを、投稿一覧で数えた記録が無い。
5. **広告側は「無言で流れる」リスクだけが先に立っている。** Advantage+ を Meta 側で回し始めた瞬間に Threads へ予算が混ざる仕様である以上、配置別内訳（Breakdown → Placement）を読む手順が Meta 運用側に入っていないと、Threads の CPI も Meta 全体の CPI も正しく読めない。自社仕様書の先行条件（配置別記録）は未実施のままである。
6. **収益導線の計測が無い。** オーガニックに収益分配が無い以上、Threads の成果は「プロフィール遷移 → アプリインストール → 課金」でしか測れない。その遷移を投稿別・週別に数える台帳が無い。

### (5) 次のアクション

1. Threads の運用台帳を「投稿」と「返信」を分けて作る: 週あたり投稿数、自投稿への作者返信数、他者投稿への返信数をそれぞれ数える。目標の置き方は原典どおり、最低線 = Meta 公式の週2–5回投稿（これ未満は警報）、実量目標 = Buffer 実践の返信込み1日複数回（速い成長は3回以上/日相当）。返信を投稿と合算して「投稿した」と報告しない。
2. 勝者 @thriveanxietysolutions の直近投稿を Threads 面で実際に開き、頻度・返信の有無と量・形式ミックス・タグ・時刻を実測して A層を確定させる。実測できるまで、Threads の型は B層（Meta 公式＋Buffer）で運用し、「勝者コピー」とは呼ばないことを台帳に明記する。
3. 時刻は Buffer 実測を主枠（平日朝、特に水・木）にして自社の固定枠を置き、週末枠は検証用に1枠だけ残して Insights で4週間比べる。夕方18–23時（audience local time）の枠は Buffer 実測で全曜日最低のため、主枠から外す。
4. 形式の既定を公式の型に固定する: テキストのみで出す場合でも会話を生む問い・主張の形にし、メディアを使う場合は必ずテキスト（文脈）を付ける。他面投稿のそのままの転載は「Threads 専用オリジナル」という公式の勝者像に反するため既定にしない。
5. 広告は Gate 0 を通るまで支出しない（現状維持）。ただし Gate 0 以前にできる先行条件として、Meta 側で Advantage+ を扱う全手順に「Breakdown → Placement で Threads の支出シェア・CPI を週次で記録する」行を入れる。事業・本人確認（KYC）が求められる手続きは **実施不可** として、代替（確認なしで回せる範囲の配置管理）に切り分ける。

---

## 全節を通じた結論（1行要約）

- YouTube は Shorts も長編も、公式が数えるのは「選ばれたか（chose to view／CTR）→ 残ったか（視聴時間・視聴率）→ 満足したか（いいね・アンケート）」の3段であり、頻度・時刻・タグ・尺の数値型は公式には存在しない。自社の不足は型の知識ではなく、この3段での自社実測と、勝者との差分ゼロ化と、投稿経路の詰まり2件である。
- Threads は公式に「返信が views のほぼ半分」という、他面に無い会話中心の面であり、自社の不足は投稿量以前に返信量の未計測と勝者の未実測である。
- 収益は両面とも広告分配に置けない（YouTube YPP は KYC で実施不可、Threads オーガニックに分配プログラムの原典なし）。勝者が実際にやっている自社プロダクトへの導線（アプリ、電子書籍、プログラム）で設計し、Threads Ads は Gate 0 通過後に配置別で測る。

---

# プラットフォーム一般ベストプラクティス調査 — note / Substack / Medium

- 調査日: 2026-11-07（JST）
- 範囲: 調査と記録のみ。投稿・設定変更はしていない。
- 調査規律: 「ベストプラクティス」と書いた項目は、名前のある一次の発信者（公式ガイド／ヘルプ、実践者本人の発信、実測のある第三者集計）の原典ページを `browser.open` で実際に開いて確認したものだけ。出典が取れないものは「推定」と明示して分離した。
- 層の区別: **A層＝固定勝者個人の現在のやり方**、**B層＝プラットフォーム一般のベストプラクティス**（公式プレイブック＋伸びている実践者群の共通項）。
- 勝者の減速・前提のズレが判明した場合は「ギャップ」として明記した。

---

## note

### (1) 核

#### (A) 勝者の現在 — ひつじ @hituji1234『あとがき』

- **規模・価格（実読 2026-11-07）**: メンバーシップ ¥780/月。プロフィール実読では 1,225名参加中（本調査の前提事実では 1,226名 × ¥780/月 ＝ 月約95万円規模。1名差は時点差として扱う）。読み放題は 3マガジン・78記事。
- **頻度・記事の型（本人がメンバーシップ説明・募集記事で明示）**:
  - 月4記事以上 ＋ 月1回ライブ実演（プロフィール説明文の表記）。募集記事本文では「月3〜4本を目安」とも書かれており、実態は月3〜4本＋月1ライブが核。
  - マガジン構成（実読）: 「AI活用の教科書」43件、「AI勉強会」12件、「ひつじのAIツールBOX」13件 — つまり **記事（教科書）／勉強会（ライブ）／ツール配布** の3本立て。
  - 提供価値の3点セット（本人募集記事）: **AI情報 × 時短ツール × コミュニティ**。特典は ①メンバー限定記事＆学習ロードマップ ②自作ツール（Nanobananaジェネレーター等）のアクセス権 ③別ツール（ゴーストライター4U）のアクセス権 ④Slackコミュニティ。記事単体ではなく「ツール利用料＋コミュニティ」として月額を正当化している。
- **価格設計（期生制・希少性）**: 0期 ¥500 → 1期 ¥600（定員600名、「参加中の値上げなし」）→ 2期 ¥780（2期が揃い次第クローズ、3期は ¥980へ値上げ予定と予告）。募集記事実測では 0期は「募集3時間で100名、追加枠300名も24時間以内にクローズ」。期を区切る・定員を置く・次期値上げを予告する、の3点で加入を急がせる設計。
- **ファネル（無料→有料）**:
  - 無料noteでは書けない濃い情報をメンバーシップのクローズド発信へ切り替える（本人募集記事の明言）。
  - 外部流入が前提: 本人インタビュー（みんかぶ、2026-10-06）で「noteを書けばそのまま売れるわけではない」「収益化している人の多くは note の外でも露出を取っている。XやInstagram、YouTubeなどでまず知ってもらってから note へ来てもらう」「記事を書く前に『この記事を誰が、どこから見つけるのか』を考えた方がいい」と明言。本人は X 約7万人フォロワー（同インタビュー時点）から送客。
  - 代替ルートも本人が提示: note内で無料記事を大量公開してフォロワー約1万人まで育ててから収益化する型。共通点は「先に無料で価値提供して信頼を作る」こと。
  - 数字の逆算（本人インタビュー）: 目標月収 → 価格 → 必要購入者数 → （購入率を仮に1%と置いて）必要露出数、の順に設計する。例示: ¥500で月¥10万なら200人、1%転換なら約2万人への露出が必要。手数料差し引きも織り込む。

#### (B) 一般ベストプラクティス — 公式が言っていること

- **メンバーシップの価格（note公式ヘルプ）**: 会費は通常会員 ¥100〜¥50,000 の範囲で設定可能。「創作の種類にもよりますが、長く創作を続けるためにも、**500〜1,000円の値付けをおすすめ**しています」。**会費は一度設定すると変更できない**ため、期生ごとに別プランを作るひつじ型はこの制約への整合的な対処でもある。初月無料（または入会日から1ヶ月無料）機能も公式に用意されている。
- **メンバーシップの説明の書き方（note公式ヘルプ）**: 説明は500字以内で「なにをするメンバーシップか」「どれくらいの頻度で更新か」「どんな人に来てほしいか」「どのように参加してほしいか」を簡潔かつ分かりやすく。プラン説明は140字以内で具体的な内容・更新頻度を書く。特典例として公式が挙げるのは外部ツール参加権、1on1相談、オフ会、メンバー限定記事など。
- **告知（note公式ヘルプ）**: 開始時は (a) noteでメンバーシップ開始記事を書く、(b) TwitterやYouTubeなど普段活動している場でも告知し、プロフィール・概要欄にリンクを貼る。初回プラン公開時はフォロワーへ通知が飛ぶ仕組み。
- **面内発見／SEO（note公式ヘルプ「ハッシュタグとは」）**: ハッシュタグは「検索キーワードのようなもの」。付け方は4観点 — ①記事タイプ（#日記 #エッセイ等）②テーマ ③シリーズ名・商品名 ④関連ワード。**「特別な理由のない限り、3〜5個程度を目安に」**。付けすぎではなく本文と合ったタグの厳選が公式方針。
- **審査という門（note公式ヘルプ）**: プラン公開には事務局審査が必要で、審査通過後に価格設定して公開する流れ。

#### 推定（出典が取れていない／自社の計算）

- [推定] 「おすすめ記事／今日の注目記事」等の編集部ピックアップが新規流入の主経路である、という主張は本調査では公式原典を開いて裏付けできていないため、ベストプラクティスとしては採用しない。
- [推定] ひつじ型の「ツール配布」を自社（AIエージェント運用の実践知）にそのまま移すと、記事＋運用ツール／テンプレート配布＋掲示板、の3点セットが再現形になる。これは自社の翻案であり、勝者本人の発言ではない。

### (2) 出典

- ひつじ本人プロフィール（メンバーシップ ¥780/月、参加人数、マガジン件数、月4記事以上＋月1ライブの説明）: https://note.com/hituji1234
- ひつじ本人「AI活用を学べるメンバーシップ『あとがき』の1期生メンバーを募集します」（月3〜4本、3点セット、0期3時間100名・24時間クローズ、1期¥600・定員600名、2期¥780値上げ予定）: https://note.com/hituji1234/n/nb8a97f75f63c
- ひつじ本人インタビュー「noteで月売上100万円超 人気Xアカウントの中の人が明かす収益化術」みんかぶマガジン 2026-10-06（外部SNSから送客、誰がどこから見つけるか、価格×人数×露出の逆算、購入率1%の例示）: https://mag.minkabu.jp/money/44317/?membership=1
- note公式ヘルプセンター「メンバーシップをつくる（オーナー向け）」（価格帯 ¥100〜¥50,000、推奨 ¥500〜¥1,000、会費変更不可、説明500字／プラン説明140字、特典例、告知方法、審査フロー）: https://www.help-note.com/hc/ja/articles/22752829171225-%E3%83%A1%E3%83%B3%E3%83%90%E3%83%BC%E3%82%B7%E3%83%83%E3%83%97%E3%82%92%E3%81%A4%E3%81%8F%E3%82%8B-%E3%82%AA%E3%83%BC%E3%83%8A%E3%83%BC%E5%90%91%E3%81%91
- note公式ヘルプセンター「ハッシュタグとは」（4観点の付け方、3〜5個目安）: https://www.help-note.com/hc/ja/articles/900004261886-%E3%83%8F%E3%83%83%E3%82%B7%E3%83%A5%E3%82%BF%E3%82%B0%E3%81%A8%E3%81%AF

### (3) 自社の現在地（実測事実）

- 勝者は ひつじ @hituji1234 に固定（メンバーシップ 1,226名 × ¥780/月 ＝ 月約95万円規模）。
- 自社 anicca_agent は記事を19本→10本へ再構築しマガジン公開済み、表示名は実在の書名へ訂正済み。
- しかしメンバーシップの門（個人情報の登録）が未入力で販売開始できていない。
- note の売上は日報記事経由が中心で金額は小さい。

### (4) 従えていない点（ギャップ）

1. **販売の門そのものが未開通**: ひつじ型の中核は「メンバーシップ販売」だが、自社はその入口に到達していない。記事再構築（10本・マガジン）はファネルの前段までで、転換点が無い。
2. **メンバーシップの門は「実施不可（エージェント側）・門の存在として記録」**: メンバーシップ開設に必要な個人情報の登録は本人の個人情報が必要な門であり、エージェント側では実施不可。回避策を発明せず、門として記録する（本ファイルがその記録）。
3. **頻度・型の未達**: 勝者は月3〜4本のメンバー向け記事＋月1ライブ＋ツール配布。自社にはメンバー向け記事の定期供給もツール配布特典もコミュニティ特典も無い（門の手前であることも一因だが、無料側の供給頻度としても勝者の無料発信量に届いているかは未検証）。
4. **外部送客の設計不足**: 勝者は「書く前に、誰が・どこから見つけるか」を決める。自社の日報記事中心の売上は、外部SNS→note の導線を記事単位で設計した形跡が弱い。
5. **価格・逆算の不在**: 勝者は目標額から価格・必要人数・必要露出を逆算する。自社には note 単独の価格×人数×露出の設計表が無い。
6. **ハッシュタグ運用の未検証**: 公式目安（本文に合うタグを3〜5個、タイプ／テーマ／シリーズ／関連ワード）に従っているか、自社10本分は未監査。

### (5) 次のアクション

1. メンバーシップの門（個人情報登録）については「実施不可（エージェント側）」として台帳に固定し、エージェント側でできる範囲（販売開始に必要な記事・プラン説明文・特典設計の下書きを ¥780／月3〜4本＋ツール＋コミュニティの勝者設計どおりに用意しておく）を先に完了させる。
2. 無料側ファネルを勝者どおりに作る: 記事ごとに「誰が・どこから（X／IG／YouTube のどの面から）見つけるか」を冒頭で決めてから書く運用を徹底する。
3. 価格逆算表を作る: 目標月収 → ¥780想定 → 必要メンバー数 → 想定転換率1%での必要露出数、を1枚にし、日報記事の露出実績と突き合わせる。
4. 自社10本のハッシュタグを公式4観点・3〜5個目安で監査する。

---

## Substack

### (1) 核

#### (A) 勝者の現在 — Packy McCormick『Not Boring』

- **前提の訂正（重要）**: 本調査の前提では「有料購読モデル」とされていたが、原典確認では現在の Not Boring は **Freemium（無料が主軸）** である。Reletter の集計（実読）では Pricing = Freemium、Publishes = Twice weekly、Issues = 676件、Business カテゴリ順位は Free で #15／Paid で #28。最新号の本文冒頭では購読者 **281,011人** と本人が記載。
- **頻度・記事の型**: 週2回。型は (a) 企業・テーマを深掘りする長編エッセイ、(b)「Weekly Dose of Optimism」型の楽観ニュース・ラウンドアップ、の2本立て（Reletter 最新号一覧で実読: Weekly Dose of Optimism #217 / #215 と単体エッセイ「Runway」が並ぶ）。
- **収益モデルの実態（減速ではなくモデルの違いとして明記）**: Packy は初期に有料購読化を検討しながら、無料でリストを速く伸ばす方を選び、スポンサーシップ（広告）を主収益にしてきた経緯が複数の本人発言の要約で知られる。本調査で原典として開けた範囲では、現在は有料ティアも併設された Freemium であり、「有料購読一本で勝った勝者」と単純化するとコピー先を誤る。有料ティアの価格は第三者集計（Sidestack／Newsletter Insights、検索で確認）で **$20/月・$200/年** と表示されるが、これは本人の購読ページ原典を直接開いての確認ではないため、価格の確定値としては扱わない（要再確認）。
- **ファネル**: 無料長編で大規模リスト（28万人規模）を作り、収益はスポンサー＋有料ティア（投資メモ等）＋周辺事業（Not Boring Capital）へ分岐させる構造。無料→有料の単線ではない。

#### (B) 一般ベストプラクティス — 公式＋実践者

- **公式「Going Paid」ガイド（Substack公式）**:
  - 読者は「単一の記事や情報」ではなく「書き手への継続的アクセス（独自の世界観・専門性・スタイル）」に対価を払う。誰に・なぜ読まれるかを先に明確化してから提供内容を設計する。
  - 成長はリーチ（読者数）× エンゲージメント（注意の深さ）で見る。
  - 無料リストの成長が先: 「定期的に・一貫して書き、宣伝すること」が成長の鍵。伸びは複利で効く。
  - 有料ローンチは一度きり: 1日で終わらせず、一連の施策で熱量と購読の波を作る「シリーズ」として設計する。
  - **転換率の公式目安: 無料購読者の 5〜10% が有料転換し、10% が狙うべき水準**。大幅に下回る場合は他ライターの実証済み tactics で改善する。
- **面内発見（Buffer 公式ガイド、著者は Buffer 自社 Substack『The Weekly Scroll』92K+購読者の運営者として実名で執筆）**:
  - 「成長の大半は Substack の内部で起きる。Recommendations と Notes が主経路なので、外部にリンクを撒く前にまず内部機能をオンにする」。
  - Notes は未フォローの人にも届く短文フィードで発見の入口。著者本人は1か月間 Notes を毎日投稿する運用を実践したと明記。
  - フォロワーは Notes しか見ずメールは届かない。購読者化が目的であり、フォロワーは輸出できないが購読者リストはエクスポート可能。
  - SEO: 投稿ごとに SEO タイトルと説明を埋める。Substack 記事は Google でランクする。
  - 収益化の仕様: 有料化すると Substack 手数料 10% ＋ Stripe 処理手数料。価格は月額／年額／任意の Founding ティアの3本立てが標準形。Stripe 接続は有料化前でも先に済ませることが推奨されている（ただし Stripe 接続自体は本人情報・銀行口座を要する門になり得る点に注意。下記ギャップ参照）。

#### 推定

- [推定] 「長編は週1〜2本、Notes は1日1本以上」が伸びている実践者群の共通頻度だという整理は、複数の実践者ガイドの検索結果では繰り返し現れるが、本調査で原典を開いて横断集計したものではないため、公式数値としては扱わない。公式が数字で言っているのは転換率 5〜10% のみ。
- [推定] Not Boring の $20/月・$200/年という価格は第三者集計由来であり、本人の購読ページでの再確認が済むまで確定値にしない。

### (2) 出典

- Substack公式「Going paid guide」（継続的アクセスへの課金、リーチ×エンゲージメント、一貫した執筆と宣伝、ローンチはシリーズ、転換率5〜10%・目標10%）: https://substack.com/going-paid-guide?utm_source=menu-dropdown
- Buffer「How to Use Substack」（Buffer 自社刊行物 92K+購読者の運営実践。成長は内部の Recommendations と Notes が主、Notes 毎日投稿の実践、SEOタイトル／説明、10%＋Stripe手数料、月額／年額／Foundingの価格形）: http://buffer.com/resources/how-to-use-substack/
- Reletter「Not Boring by Packy McCormick」（Freemium、週2回、676号、Free #15／Paid #28、最新号で281,011人と本人記載）: https://reletter.com/publications/not-boring-by-packy-mccormick

### (3) 自社の現在地（実測事実）

- 勝者は Packy McCormick（Not Boring）に固定。
- 自社 anicca.anicca は **公開記事 0本**、サインインが詰まっていて未着地。

### (4) 従えていない点（ギャップ）

1. **ゼロからの未着地**: 記事0本では公式の言う「定期的に・一貫して書く」「無料リストを育てる」の出発点に立っていない。Notes も Recommendations も未稼働とみなされる。
2. **勝者モデルの誤認リスク**: 勝者を「有料購読モデル」とだけ捉えると、実際の勝者の主軸（無料で28万人規模のリスト＋スポンサー＋有料ティア併設）を取り違える。コピーすべきは「週2回の長編（深掘り＋定期ラウンドアップ）の型と無料リスト優先」であって、有料化を急ぐことではない。
3. **転換の土台が無い**: 公式目安の転換率 5〜10% は無料リストがあって初めて意味を持つ。自社は分母（無料購読者）がゼロ。
4. **サインインの詰まりは門として未解消**: 投稿以前にアカウント到達ができていない。Stripe 接続まで進む場合は本人情報・銀行口座を要する可能性があり、その段階は「実施不可（エージェント側）・門として記録」の対象になり得る（現時点ではサインイン段階が先）。

### (5) 次のアクション

1. サインインの詰まりを、突破している他者の方法・ツールで調べ直して解消し、アカウント到達を先に完了させる（投稿はその後）。
2. 到達後、勝者の型で開始する: 週2回（深掘り長編1本＋ラウンドアップ1本）を無料で出し、Notes を毎日1本、Recommendations を同ニッチ刊行物で初期設定する。SEOタイトル／説明は毎投稿で埋める。
3. 有料化は無料リストが育ってから。価格を決める際は Not Boring 本人の購読ページを原典で開いて再確認してから固定する（第三者集計の $20/$200 を確定値として使わない）。

---

## Medium

### (1) 核

#### (A) 勝者の現在 — Benjamin Hardy

- **履歴としての勝者像（確認できた範囲）**: 2015〜2018年に Medium で #1 writer とされた書き手。記事の累計閲覧は1億回超、単一記事で2,500万回規模の事例、Medium 経由でメールリストを 0 → 40万人に伸ばしたことが、本人の登壇・インタビューのエピソード要約として繰り返し記録されている（London Writers' Salon の回次要約等）。
- **現在の状態＝減速／主戦場の移動（ギャップとして明記）**: Hardy の現在の主軸は書籍（共著を含む多数）と Scaling.com 等の事業側に移っており、**「現在も Medium で高頻度に投稿して伸ばし続けている勝者」としての実測は本調査では取れていない**。勝者マップ上の固定は 2015〜2018年の実績に基づくもので、現在の Medium 投稿頻度・直近のバイラル記事は未確認。したがって A層の「現在の頻度・型」は **未計測・要確認** とする。過去の型（自己変革／未来の自分をテーマにした長編エッセイを大規模 Publication 経由で流通させ、記事末からメールリストへ送る）も、本調査では本人の Medium 原典記事を開いての再検証はできていないため、確定したコピー仕様としては扱わない。

#### (B) 一般ベストプラクティス — 公式が言っていること

- **収益の仕組み（Medium公式 Partner Program ページ）**: メンバー向け（paywall）記事は、**メンバーが30秒以上読んだ時点から読了時間に応じて**収益が発生し、長く読まれるほど増える。追加の増分要素は (a) 前向きな反応（clap／highlight／reply 等）、(b) フォロワーボーナス（フォロワーが継続して読む・反応する）、(c) **Boost ボーナス**。公式は「Boost の水準に届くために、**少ない本数に時間をかけて高品質な記事を書く**ことを推奨」と明記 — 量より質が公式方針。
- **流通の3層（Medium公式ヘルプ「What happens to your story when you publish on Medium」、2025-09-10更新）**:
  1. **Personal network**: フォロワーの Following フィード、Digest メール、任意のメール通知。
  2. **General distribution**: 全記事がデフォルトで対象。推薦アルゴリズムが For you フィード、Digest（非フォロワー含む）、トピックページ、Explore、おすすめ欄、ログアウト時ホームへ配信する。低品質と判定された記事は **Network only** に落とされる。
  3. **Boost**: 人間のキュレーター（＋ Publication 編集者やコミュニティの推薦）が、洞察・思慮深さ・ニュアンス・丁寧さで際立つ記事を選んで追加配信する。
  - **Publication の役割（公式）**: Publication に載せると、そのフォロワーへの Digest／Following 配信と Publication のニュースレター配信が上乗せされる。流通を増やす公式手段として位置づけられている。
  - 検索: 記事は検索エンジンにインデックスされ得て、Medium の記事は検索結果で上位に出やすい旨も公式が案内する（SEO は面内流通とは別の入口）。
- **AIコンテンツ政策（Medium公式ヘルプ、2026-04-29更新）— 自社にとって最重要の制約**:
  - 「Medium is for human storytelling, not AI generated writing」が公式の第一文。
  - **AI生成ライティング（大半がAI生成で編集がほぼ無いもの）は、開示の有無にかかわらず Partner Program の paywall に置けない**。違反すると paywall からの除去や Partner Program 登録の取消しがあり得る。
  - **未開示のAI生成ライティングは Network Only 配信**（フォロワーにしか届かず、一般流通・Boost の対象外）。
  - AI支援（アウトライン、文法・スペル・事実確認）は開示不要で可。ただし AI生成テキストを取り込んだ記事は開示が必要で、開示文は冒頭2段落以内に置くのが公式の案内。AI生成画像はキャプションで明示すれば可。
  - SEO目的のAI量産（書籍要約・製品レビュー等のスパム的生成）や、他者コンテンツのAIリライト（盗用扱い）、容易に反証できるAI幻覚の事実誤認も禁止。
  - つまり Medium では「AIエージェントが生成した記事をそのまま有料化・拡散する」モデル自体が公式政策と衝突する。**人間による実質的な執筆・編集と一次経験が前提**であり、この前提を満たせない運用は実施不可として扱うべき領域である。

#### 推定

- [推定] 「週2本・1,000〜2,500語・タグは大2＋小3」のような具体的な運用数値は実践者記事の検索結果には現れるが、公式原典で確認できた数値ではないため、ベストプラクティスとしては採用しない。公式が数字で言っているのは「30秒以上の読了から収益」「少ない本数に時間をかける（Boost）」の2点が中心。
- [推定] Hardy の過去の型を現在の Medium 政策下で再現できるかは未検証。特にメールリスト送客型の記事末 CTA は、現在の流通・Boost 基準（過剰な CTA の扱い等）との整合を原典で確認してからでないと採用しない。

### (2) 出典

- Medium公式「Partner Program」（30秒以上のメンバー読了で収益、反応・フォロワーボーナス・Boostボーナス、少ない本数に時間をかけて高品質に）: https://medium.com/partner-program
- Medium公式ヘルプセンター「What happens to your story when you publish on Medium」（流通は Personal network／General／Boost の3層、低品質は Network only、Publication による追加配信、検索インデックス）: https://help.medium.com/hc/en-us/articles/360018677974-What-happens-to-your-story-when-you-publish-on-Medium?source=post_page-----bff97a4eb9c1---------------------------------------
- Medium公式ヘルプセンター「Artificial Intelligence (AI) content policy」（2026-04-29更新。AI生成文の paywall 禁止・未開示は Network Only・開示は冒頭2段落以内・AI画像はキャプション明示）: https://help.medium.com/hc/en-us/articles/22576852947223-Artificial-Intelligence-AI-content-policy
- London Writers' Salon 回次要約「Ben Hardy — Mastering Articles on Medium.com」（2015〜2018年 #1 writer、累計1億回超、Medium でメールリスト 0→40万人）: https://londonwriterssalon.simplecast.com/episodes/005-ben-hardy-mastering-articles-future-self-dRKVtnmd

### (3) 自社の現在地

- 勝者は Benjamin Hardy（勝者マップ上の固定）。
- 自社の Medium 上の運用実測は手元に無いため、現在地は **「未計測・要確認」** と正直に記す。記事本数・フォロワー数・Partner Program 加入有無・収益はいずれも未計測であり、推測で埋めない。

### (4) 従えていない点（ギャップ）

1. **勝者の鮮度ギャップ**: 固定勝者 Hardy は 2015〜2018年の勝者であり、現在 Medium で能動的に伸ばしている実測が無い。勝者マップの固定自体が「現在の勝者」として有効か、再検証が必要（減速した勝者をコピーしても現在の流通は再現できない）。
2. **計測ゼロ**: 自社の運用実測が皆無で、公式の3層流通（Personal／General／Boost）のどこにいるかすら判定できない。
3. **AI政策との正面衝突（最重要）**: 自社はAIエージェント運用が前提のため、Medium 公式の「AI生成文は paywall 不可・未開示は Network Only」という政策と、収益化モデルが構造的に衝突する。人間の一次経験として書け、実質編集できる題材以外は、Medium での有料化は **実施不可** として扱う必要がある。無理に量産すると Partner Program 登録取消しのリスクがある（公式明記）。
4. **公式の型との不一致リスク**: 公式は「量より質、少ない本数に時間をかける」＋ Publication 経由の流通を推す。自社に Publication 所属も Boost 実績も確認できていない。

### (5) 次のアクション

1. まず計測から: 自社 Medium アカウントの有無・記事本数・フォロワー・Partner Program 状態を実測し、本節の現在地を「未計測」から実数へ更新する。
2. 勝者の再検証: Hardy の直近の Medium 投稿実績を本人のプロフィール原典で確認する。能動的な投稿が無ければ、「歴史的勝者」と「現在の勝者」を分けて記録し直し、現在の Medium で実際に Boost／流通を取っている書き手群を B層の実践者として別途棚卸しする。
3. 題材の線引き: Medium に出す場合は、AI生成文の量産ではなく、自社の一次運用データ（実数・失敗・検証結果）を人間の記事として成立させる型だけに限定し、AI支援の範囲と開示要否を公式政策どおりに運用する。paywall 化は政策適合を確認できた記事だけにする。

---

## 横断まとめ

| 面 | 勝者（A層）の核 | 公式（B層）の核となる数字 | 自社の最大のギャップ |
|---|---|---|---|
| note | ひつじ: ¥780/月、月3〜4本＋月1ライブ、記事×ツール×コミュニティ、期生制で希少性、外部SNSから送客 | 会費推奨 ¥500〜¥1,000（変更不可）、ハッシュタグ 3〜5個 | メンバーシップの門（個人情報登録）が未入力 ＝ **実施不可（エージェント側）・門として記録** |
| Substack | Packy: 週2回（深掘り＋ラウンドアップ）、28万人規模の無料リストが主軸、収益はスポンサー＋有料ティア併設の Freemium | 無料→有料の転換率 5〜10%（目標10%）、成長は内部の Notes／Recommendations が主 | 公開記事0本・サインイン詰まりで未着地。勝者を「有料一本」と誤認しないこと |
| Medium | Hardy: 2015〜2018年の #1 writer（現在は書籍・事業が主軸で Medium は減速／未確認） | 収益は30秒以上のメンバー読了から、Boost は「少ない本数を高品質に」、AI生成文は paywall 不可 | 運用実測が未計測・要確認。AI政策と自社モデルの構造的衝突 |

- KYC／個人情報が必要な手法は、いずれの面でも「実施不可」と明記した（note のメンバーシップ登録が該当。Substack の Stripe 接続も到達した段階で同様の門になり得る）。
- 本ファイルで「推定」と分離した項目は、原典が取れるまでベストプラクティスとして運用しない。

---

# ベストプラクティス調査 — 自社ブログ/SEO・GEO と App Store（ASO）— 2026-11-07

調査と記録のみ。設定変更・提出はしていない。

## 注記（骨格の出所と今回の確認範囲）

- 骨格は既存の出典つき調査の確定事項（llms.txt 実測ゼロ／FAQ スキーマは引用にマイナス／FAQ 本文と質問形タイトルが効く／勝者 thevisionboard.app の資産は「全アプリ実機テスト＋同一ルーブリック採点＋日付つき一次データ」／GEO は第三者言及が支配的／App Store リスティングが ChatGPT アプリ推薦の引用源の約半数）を使い、再調査していない。
- 正本の所在: `~/workspace/research_notes/seo-geo-best-practice-tools-20261105-2131/report.md`（目標フォルダ配下ではなく workspace 直下。本回 §4 を含め全文実読し、本ファイルの骨格として使った）。
- 今回新たに原典を開いて確認したもの: Google 公式 AI 最適化ガイド、Google 公式「AI features and your website」、Google Search Central Blog（2025-05-21）、Google Search Central ドキュメント更新ログ（FAQ リッチリザルト廃止・llms.txt 明確化の各エントリ）、Apple 公式 App Store search／product page／product page optimization の3ページ、AppTweak の引用源分析記事。各主張の出典は各節 (2) に明記。
- 「ベストプラクティス」と書いたのは、名前のある一次の発信者（公式・実践者本人・実測研究）が実際に言ったことを原典または原典に準ずる記録で確認できた主張のみ。確認できていないものは「推定」「未確認」と明示して分離した。

---

## 自社ブログ/SEO・GEO

### (1) 核（数字つき）

**Google 公式の確定事項（GEO＝特別な裏技ではなく通常の SEO）**
- 生成 AI 機能（AI Overviews／AI Mode）は Google のコア検索ランキング・品質システムに根ざしており、「生成 AI 検索の最適化は、Google の見方では検索体験の最適化であり、すなわち今も SEO」である。表示の最低条件は「インデックスされ、スニペット表示が可能であること」＋ Search Console の生成 AI 包含設定。
- 最も効くのは「ユニークで、コモディティでない、人第一の一次情報コンテンツ」。Google はコモディティ型コンテンツ（誰でも書ける一般論のまとめ）を名指しで弱いとし、一人称の実体験・実測に基づく内容を強いとする。
- Google が公式に「やらなくてよい」と列挙した5点: ① llms.txt 等の AI 専用ファイル／マークアップ（Google Search は使わない。置いても順位・可視性にプラスにもマイナスにもならない）② コンテンツの細切れ（チャンク分割、理想の文量も存在しない）③ AI 向けの書き直し・ロングテール変種の量産（scaled content abuse に該当し得る）④ 不自然な「メンション」の獲得工作 ⑤ 生成 AI 用の特別な構造化データ（不要。構造化データ自体はリッチリザルト用に継続が推奨）。
- FAQ リッチリザルトは終了済み: 2023-08 に政府・公的医療サイト等へ限定 → **2026-05-07 をもって全サイトで表示終了**、2026-06-15 にドキュメント自体が撤去された（Google 更新ログで本回確認）。したがって「FAQ スキーマで検索面を取る」施策は前提が消えている。残る価値は FAQ 本文（質問形の見出し＋端的な回答）という可視コンテンツ側にある、というのが既存調査の確定事項であり、Google 公式の「構造化データは表示内容と一致させること」「重要な内容はテキストで」という原則とも矛盾しない。
- 計測は Search Console の **Generative AI performance report** で行うのが Google 公式の指定経路。

**実測研究の数字**
- Princeton／IIT Delhi の GEO 論文（Aggarwal et al.、KDD 2024、GEO-bench 10,000 クエリ）: 引用（quotation）追加で可視性 **約+41%**、統計（statistics）追加で **約+31%**、出典引用（cite sources）で **約+27%**。キーワード詰め込みは逆効果。
- Ahrefs の 75,000 ブランド相関研究: ブランドのウェブメンションと AI 可視性の相関 **0.664** に対し、被リンク数は **0.218**（約3倍の差）。YouTube メンションは **0.737** で最強層。※相関であり因果ではない（Ahrefs 自身が明記、という二次記録あり）。
- AppTweak（2026-05、ChatGPT のアプリ推薦回答 125,000 件超・米市場を分析）: 引用源の内訳は **アプリストアのリスティング合計 47.5%**（App Store 単体 37.6%＋Google Play 9.6%）、オープンウェブ 27%、出典なし（モデル内知識のみ）22.6%。推薦順位 1〜4 位は 80〜85% が出典つきで引用されるのに対し、8 位では 25% 未満まで落ちる。引用されやすい情報源の条件は「構造化され抽出可能であること」「信頼される面に載っていること」「複数面で説明が一致していること」。
- SE Ranking（129,000 ドメイン、ChatGPT）: FAQ スキーマのあるページの平均引用は **3.6 件 vs スキーマなし 4.2 件**（スキーマは引用にマイナス側）。一方で FAQ 本文のセクションと質問形タイトル／H1 は引用と相関し、小規模ドメインでは質問形タイトルの影響が約7倍。また、直近3か月以内に更新されたコンテンツは平均 6 件の引用 vs 古いもの 3.6 件、統計を19点以上含むページは 5.4 件 vs 最小限のページ 2.8 件、見出し間 120〜180 語のセクションは 4.6 件 vs 50 語未満 2.7 件。Reddit／Quora に大量のブランド言及があるドメインは引用確率が約4倍、レビュープラットフォームのプロフィール保有は約3倍。
- 自社ラウンドアップの逆効果（実測）: Lily Ray（Amsive）の実践者調査では、自社を上位に置いた自社リストが AI Overviews に引用された際、そのブランドが推薦から外れた割合は **69%（2026-06）→ 83%（2026-09 再測）**。Ahrefs の統制実験（34 ページ、9,886 回答）では、無名ブランドは自社ページ経由で言及が増えた一方、引用された自社ページから競合が推薦されたケースが **43%** あった。「best」系リストは ChatGPT 引用ページタイプの 43.8% を占め、引用されたリストの 79.1% は 2025 年中に更新され、26% は直近2か月以内に更新されていた（Ahrefs／Glen Allsopp）。
- 通常検索側の数字: Backlinko（1,180 万結果）では 1 位は 2〜10 位より被リンクが平均 **3.8 倍**。Google 公式の Page Indexing 考え方では「未インデックス 522 件」自体は診断ではなく、重要な正規ページがインデックスされているかが問題（重複・パラメータ変種等は未インデックスが正常）。Princeton の +41% 等には注意書きが要る: あの実験はモデルに情報源を渡した状態での可視性であり、後続ベンチマークでは検索順位を含めると効果が大幅に弱まるという反証もある（正本 §2d）。
- 既存調査の確定事項（再掲）: GEO は第三者言及が支配的で、自社サイトだけでは推奨は取れない。引用されても推奨から外される割合が高いため、mention 率・citation 率・recommendation 率は分けて測る。勝者 thevisionboard.app の移せる資産は「全アプリ実機テスト＋同一ルーブリック採点＋日付つき一次データ」という一次データの作り方そのものであり、クローン型ラウンドアップは Google 公式に「commodity」と呼ばれる側に落ちる。
- 正本 §4 の優先順位（SEO）: ①インデックスされる核を直し比率は無視する ②内部リンクを核ページへ集中 ③旗艦ラウンドアップを実機テスト済みの一次記事に書き換えて維持し、クローン量産は止める ④ホームページのエンティティ希薄化（「Anicca＝アファメーションアプリ」と plainly 言い切るハブ）を解消 ⑤外部での掲載・リンク獲得が長期の本丸 ⑥ヘッド語ラウンドアップの追加ではなく低競争の隣接トピックを SERP の弱点分析で選ぶ。

### (2) 出典

| 主張 | 発信者／文書 | URL |
|---|---|---|
| GEO は今も SEO／llms.txt・チャンク分割・AI 向け書き直し・不自然なメンション・特別スキーマは不要／非コモディティな一次情報が核／Generative AI performance report で計測 | Google Search Central「Optimizing your website for generative AI features on Google Search」（最終更新 2026-07-10、本回原典実読） | https://developers.google.com/search/docs/fundamentals/ai-optimization-guide |
| AI 機能への表示はインデックス＋スニペット適格が条件、追加の技術要件なし | Google Search Central「AI Features and Your Website」（本回原典実読） | https://developers.google.com/search/docs/appearance/ai-features |
| ユニークで価値あるコンテンツ、良好なページ体験、構造化データは表示内容と一致 | Google Search Central Blog「Top ways to ensure your content performs well in Google's AI experiences on Search」（2025-05-21、本回原典実読） | https://developers.google.com/search/blog/2025/05/succeeding-in-ai-search |
| FAQ リッチリザルトは 2026-05-07 で表示終了・2026-06-15 にドキュメント撤去／llms.txt は「必要なく、可視性にも順位にも影響しない」旨の明確化（2026-06-15） | Google Search Central ドキュメント更新ログ（本回原典実読。FAQPage ドキュメント URL は同ログへリダイレクト） | https://developers.google.com/search/docs/appearance/structured-data/faqpage |
| 引用+41%／統計+31%／出典引用+27%、キーワード詰め込みは逆効果 | Aggarwal et al.「GEO: Generative Engine Optimization」Princeton／IIT Delhi、KDD 2024（arXiv:2311.09735）。本回は原典要約の二次記事で照合 | https://kime.ai/blog/what-is-geo |
| ウェブメンション相関 0.664 vs 被リンク 0.218、YouTube メンション 0.737（相関であり因果でない） | Ahrefs、75,000 ブランド研究（2025-05／追跡編 2025-12-12）。本回は同研究を一次引用する記録で照合 | https://www.pressfront.co/reference/ai-recommendation-consistency |
| アプリ推薦の引用源: ストアリスティング 47.5%（App Store 37.6%）、オープンウェブ 27%、出典なし 22.6%。順位 1〜4 位は 80〜85% が出典つき、8 位は 25% 未満 | AppTweak「Which sources do AI search engines cite when recommending apps」（2026-05 分析、ChatGPT 推薦回答 125,000 件超、本回原典実読） | https://www.apptweak.com/en/aso-blog/which-sources-do-ai-search-engines-cite-when-recommending-mobile-apps |
| mention／citation／recommendation は分けて測る、植えたメンションはやらない、比較・価格ページを公開する | 社内仕様（The Rank Master 実測記事・JUN&GEO 白書等を原典として作成済み） | `hidden_files/affirmation-geo-citation-spec-2026-11-05.md`（社内ファイル） |
| FAQ スキーマ 3.6 vs なし 4.2 件、質問形タイトルは小規模ドメインで約7倍、更新鮮度・統計点数と引用の相関、Reddit/Quora 約4倍・レビュー面約3倍、llms.txt 効果なし（約30万ドメイン） | SE Ranking「How to Optimize for ChatGPT」／「LLMs.txt: Why Brands Rely On It and Why It Doesn't Work」（正本が原典実読済み） | https://seranking.com/blog/how-to-optimize-for-chatgpt/ ／ https://seranking.com/blog/llms-txt/ |
| 「best」リストは引用ページタイプの 43.8%、更新鮮度 79.1%／自社プロモ実験で競合推薦 43% | Ahrefs（Glen Allsopp）／同（Mateusz Makosiewicz）（正本が原典実読済み） | https://ahrefs.com/blog/best-lists-research/ ／ https://ahrefs.com/blog/self-promotional-content-ai-seo-experiment/ |
| 自社リスト引用時に推薦から外れる割合 69%→83% | Lily Ray（Amsive）の実践者調査（正本では二次報道経由として明記） | https://www.promptthemarket.com/self-ranking-best-of-listicles-now-exclude-brands-83-of-the-time/ |
| 上記全体の骨格・§4 優先順位 | 既存調査正本（2026-11-05、出典つき） | `~/workspace/research_notes/seo-geo-best-practice-tools-20261105-2131/report.md`（社内ファイル） |

### (3) 自社の現在地（実測事実として提示されたもの）

- Google 検索: 「affirmation app」で aniccaai.com が **1位**、「best daily affirmation apps」で **4位**（直近 3位→4位）。
- GSC 実測: クリック **7**・表示 **416**・CTR **1.7%**・平均順位 **15**。
- GEO: 8 プロンプト中、言及 **0/8**・引用 **0/8** が継続。競合は ThinkUp 5/8、Insight Timer 4/8、Affirmation Pod 3/8、I am 1/8。
- Todo 項目40（GEO）進行中: AlternativeTo へ提出済み（審査待ち）、第三者サイト 4 件へ掲載働きかけメール送信済み（返信未着）、AppsWeRecommend は有料掲載 $49 のため対象外と確定。
- robots.txt は AI 検索クローラをブロックしていない（2026-11-05 社内実測で `Allow: /` を確認済み）。

### (4) 従えていない点（ギャップ）

1. **第三者言及がほぼゼロのまま**: GEO の支配的レバー（Ahrefs 相関 0.664、AppTweak の「複数面での一致」）に対し、自社の第三者面は AlternativeTo 審査待ち＋働きかけ 4 件・返信 0 件のみ。言及 0/8・引用 0/8 という現在地と整合する最大のギャップ。
2. **面ごとの説明の不一致**: App Store 側でサブスク名の表記不一致（"Anicca Pro" 表記だが実商品は Premium 系）がある。AppTweak の引用条件「ストア・自社サイト・レビュー面で同じ説明が一致」は、ASO 節と共通する土台であり、ここが崩れている。
3. **ヘッド語は取れているのに全体が薄い**: 「affirmation app」1位・「best daily affirmation apps」4位の一方で、平均順位 15・CTR 1.7%・クリック 7。勝者 thevisionboard.app 型の資産（全アプリ実機テスト＋同一ルーブリック＋日付つき一次データ）で自社ラウンドアップが作られているかは、本回では未検証（要実物確認）。Google 公式の言う「commodity」側に寄っている記事が残っていれば、それが候補になる。
4. **計測の公式経路が未実施**: Search Console の Generative AI performance report の読みが社内仕様の完了条件に入ったまま未実施（仕様ファイルに明記）。Google 公式の指定経路で AI 面の表示をまだ測れていない。
5. **やらなくてよいことの棚卸し未確認**: llms.txt や FAQ スキーマ目的の作業が自社側に残っていないかは本回未確認。残っていれば労力の付け替え対象（Google 公式: llms.txt は無影響、FAQ リッチリザルトは 2026-05-07 終了。SE Ranking 実測では FAQ スキーマは引用 3.6 vs なし 4.2 件とマイナス側）。
6. **ホームページのエンティティ希薄化（正本 §1a の実測指摘）**: aniccaai.com のトップは「agent-run company／Manager」中心の構成で、「Anicca＝アファメーションアプリ」というエンティティ連想が Google・LLM の双方に対して弱い構造になっている（正本が 2026-11-05 に実読して指摘）。アファメーションアプリと明言するハブページと、トップからの説明的アンカーでの内部リンクが未整備。
7. **自社ラウンドアップの本数と鮮度**: 正本 §4 の型は「 honest な自社ラウンドアップは1本だけ、実機テスト済み・日付つきで維持」。自社が複数本のクローン型を量産しているなら、それ自体が Lily Ray 実測（推薦除外 69〜83%）と Google の scaled content abuse の双方に触れる。現在の本数・更新日・実機テスト有無は要実物照合。

### (5) 次のアクション

- Todo 項目40 の継続を主線にする: AlternativeTo の審査結果確認、働きかけ 4 件の返信追跡と未返信先への再送、対象リストの追加は「AI が実際に引用しているラウンドアップ／レビュー面」から取る（社内 GEO 仕様 手順4 のとおり。自社記事で自社を 1 位にする型は採らない）。
- 面の一致を先に直す: ストア（ASO 節参照）・aniccaai.com・第三者掲載の3面で、アプリ説明・価格・サブスク名を同一表記に揃える。AppTweak の実測ではストアリスティング単体が引用源の 37.6% を占めるため、これは GEO の作業でもある。
- 計測を公式経路で閉じる: Generative AI performance report の初回読みを実施し、質問バンク（10〜15 問）× 主要エンジン × 各 3 回の mention／citation／recommendation 分離計測を月次で回す（社内 GEO 仕様 手順1 の完了条件）。
- ブログ側は勝者型の実物照合: 自社の affirmation アプリ比較記事が「全アプリ実機テスト＋同一ルーブリック採点＋日付つき一次データ」になっているかを実物で開いて差分を数え、コモディティ型の焼き直し記事は作らない（Google 公式ガイドの非コモディティ原則）。旗艦は1本に絞り、四半期更新で鮮度を保つ（Ahrefs: 引用リストの 79.1% が当年更新）。
- 正本 §4 の SEO 側 6 項目をそのまま作業順にする: インデックス核の固定（未インデックス件数の比率追いはしない）→ 内部リンク集中 → 旗艦ラウンドアップの一次化 → ホームページのエンティティ希薄化の解消 → 外部掲載・リンク獲得 → 低競争の隣接トピック追加。

### 推定（出典が取れていないため分離）

- 平均順位 15・CTR 1.7% の主因がロングテール側の薄さにある、という読みは GSC の数字からの推測であり、クエリ別内訳の実測なしには断定しない。
- Health & Fitness カテゴリ固有の引用源内訳は AppTweak のカテゴリ表に含まれておらず、自社カテゴリでストア比率が 47.5% と同じになるかは不明。一般値としてのみ使う。

---

## App Store（ASO）

### (1) 核（数字つき）

**Apple 公式の確定事項**
- 検索順位の決定要因は2系統: テキスト関連性（タイトル・サブタイトル・キーワード・主カテゴリへの一致）と、ユーザー行動（ダウンロード数、評価・レビュー等）。副カテゴリも索引対象。
- キーワード欄は **100 文字**、カンマ区切り・スペースなし。タイトル／サブタイトル／カテゴリと重なる語は入れない。複数形の重複、一般語（"app" 等）、つなぎ語、特殊文字は枠の無駄。他社商標・有名人名・**競合アプリ名は禁止**（リジェクト理由になる）。
- 枠の上限: アプリ名 **30 文字**、サブタイトル **30 文字**、プロモーション文 **170 文字**、スクリーンショット **最大 10 枚**、IAP 表示名 **35 文字**。
- **プロモーション文は検索順位に影響しない**（Apple 公式明記）。ただし審査なしでいつでも変更できる唯一の面であり、転換用コピーの置き場として使うのが公式の想定。
- スクリーンショットは検索結果に **最初の 1〜3 枚**が表示される。1 枚目側に本質を置くことが公式推奨と一致する。
- 評価・レビューは検索順位に影響する。アプリ内評価プロンプト（SKStoreReviewController）は **365 日に最大 3 回**まで。
- 製品ページ最適化（PPO）: 代替案は **最大 3 案**、テストは **最大 90 日**、勝敗は **信頼度 90% 以上**で判定してから適用するのが Apple 公式手順。Apple の開発者ストーリー実例では転換率 +3%（Simply Piano）、+8%（Peak Brain Training）。
- ローカライズは公式の発見性レバー: 説明・キーワード・スクリーンショット・プレビューを市場ごとに本地化し、キーワードも市場ごとに作る。
- Apple Ads の公式表明として「ダウンロードの **約 65%** は検索の直後に起きる」（Apple 公式 App Store search ページ自体には百分率の記載はなく、この数字は Apple Ads 側の表明として複数の二次報道・実践者記事が引用。本回は原典ページでの直接確認はできていないため、出所の種別をここに明記する）。

**実測ベンチマーク（社内 ASO 仕様が原典実読済みの集計値）**
- 順位と獲得の非線形性（Sensor Tower 系集計）: 1 位がそのキーワードの日次インストールの **34%** を取り、8〜15 位の **6.2 倍**、16〜30 位の 14.8 倍。2〜3 位で 27%、4〜7 位で 18%。
- 転換の中央値: iOS のタップ→インストール **33.4%**（上位四分位 45.6%）。カテゴリ Health & Fitness の期待帯は **30〜36%**。
- メタデータ変更後の順位安定化は平均 **28 日**。週次変動は上位 100 語で平均 ±4.2 のため、28 日未満の判定はノイズとして扱う。
- 評価 **4.5 以上**のアプリは 4.0 未満の **1.7 倍**のインストール率。順位安定の目安は 1,000 インストールあたり 12 レビュー。
- 戦術の順序: ヘッド語は全体のごく一部で競争が最激のため、ロングテール（2〜4 語）で 4〜7 位を先に取る → ヘッド語へ上がる、が実践者・集計の共通項。

**両論併記 — 「ASO の優先度は低い」とする実践者との緊張関係**
- Apple Ads 表明の「DL の約 65% は検索直後」＋順位シェアの非線形性（1 位 34%）からは、検索面は最大の発見面であり ASO は主レーンになる。
- アプリ実践者・一誠の実測発信（本人がスクリーンショットで共有し 2026-11-06 に記録）: 自分のアプリでは **DL の 98% は SNS 投稿 → アプリ名検索（ブランド検索）経由**であり、ストア転換率は投稿の質で **58〜62% → 70%** へ動いた。したがって ASO（カテゴリキーワード最適化）の優先度は低く、効くのは投稿の質と、それを受けたブランド検索の転換率である、という主張。
- 両者は矛盾ではなく対象が違う、という整理は次のとおり（本節の分析であり出典ではない）: 一誠の数字でも流入の受け皿はストアの製品ページであり、ブランド検索で来た人の転換率（58〜70% の議論）はリスティングとスクリーンショットの質で決まる。キーワード ASO（非ブランド語の順位）と、ブランド検索の受け皿としての製品ページ転換は、別レバーとして分けて扱うべきものである。
- なお一誠の発信は原典 URL が社内記録に残っておらず、本回ウェブで原典を再確認できていない。実践者の実測発信として記録するが、出典の強さは Apple 公式・集計研究より一段弱いものとして扱う。

### (2) 出典

| 主張 | 発信者／文書 | URL |
|---|---|---|
| 順位要因＝テキスト関連性（タイトル・サブタイトル・キーワード・主カテゴリ）＋ユーザー行動（DL・評価）／キーワード 100 文字の規則と禁止事項／プロモ文は順位に影響しない／副カテゴリも索引 | Apple Developer「App Store search」（本回原典実読） | https://developer.apple.com/app-store/search/ |
| 名前 30 字・サブタイトル 30 字・プロモ文 170 字（審査なしで随時変更可）・スクショ最大 10 枚（検索結果には最初 1〜3 枚）・説明文へのキーワード詰め込み禁止と価格記載回避・IAP 名 35 字・評価プロンプト年 3 回まで・ローカライズ | Apple Developer「Creating Your Product Page」（本回原典実読） | https://developer.apple.com/app-store/product-page/ |
| PPO は最大 3 案・最大 90 日・信頼度 90% 以上で適用、実例 +3%／+8% | Apple Developer「Product Page Optimization」（本回原典実読） | https://developer.apple.com/app-store/product-page-optimization/ |
| 順位シェア 34%（1 位）・TTI 中央値 33.4%・Health & Fitness 帯 30〜36%・安定化 28 日・週次変動 ±4.2・評価 4.5 以上で 1.7 倍・1,000 DL あたり 12 レビュー | Digital Applied「ASO Statistics 2026」（AppTweak／Sensor Tower／data.ai 等の集計。社内仕様が全文実読済み） | https://www.digitalapplied.com/blog/app-store-optimization-aso-statistics-2026-data |
| DL の 98% は SNS → アプリ名検索経由、転換率は投稿の質で 58〜62% → 70%、ASO の優先度は低い | 実践者・一誠の発信（2026-11-06、本人が共有したスクリーンショット経由で MEMORY.md に記録。原典 URL は記録なし、本回再確認不可） | （URL なし） |
| 勝者 I am のリスティング実測（US「positive affirmations」等 1 位、スクショ 9 枚、評価 US 4.8／738K 件・JP 4.7／1,778 件、副カテゴリ Lifestyle あり、14 言語） | 社内実測（Apple 公式 API・App Store ページ実読、2026-11-04） | `hidden_files/aso-winner-teardown-2026-11-04.md`（社内ファイル） |

### (3) 自社の現在地（実測事実として提示されたもの＋社内実測）

- キーワード順位: JP「アファメーション」は **32 ↔ 97 ↔ 111 位**を往復、JP「感謝」**174 位**、JP「ポジティブ」**114〜126 位**、JP「自己肯定感」**56〜61 位**。US は Anicca の全語が圏外。
- 勝者 I am は US「positive affirmations」**1 位**・JP「アファメーション」**1 位**。
- アプリ: Anicca iOS **1.9.6 がライブ**、1.9.8 は Developer Rejected（取り下げ済み）。
- 価格: Weekly $6.99／Monthly $14.99／Annual $59.99／Lifetime $59.99。
- JP 評価 **4.5（48 件）**。US 評価は 5.0／1 件（2026-11-04 社内実測）。
- サブスク名の表記不一致あり（"Anicca Pro" 表記だが実商品は Premium 系）。
- リスティングの形（2026-11-04 社内実測）: スクリーンショットは原稿計画 5 枚（勝者は 9 枚）、プロモーション文には課金注意文が入り枠を使っている、副カテゴリなし（勝者は Lifestyle あり）、対応言語 6（勝者は 14）。
- プロダクト計測は Mixpanel 一本化が決定済み（Todo 項目39）。

### (4) 従えていない点（ギャップ）

1. **非ブランド語の順位が全面で弱い**: US は全語圏外、JP も最重要語「アファメーション」が 32〜111 位を往復し安定していない。ベンチマークでは 8 位以下は日次インストールの取り分が 12% 以下に落ちる帯であり、現状はその外側。
2. **メタデータ改訂が止まっている**: 1.9.8 が却下・取り下げ済みのため、タイトル／サブタイトル／キーワード欄の変更（新バージョン提出とセット）自体が進んでいない。社内 ASO キーワード仕様（2026-11-05、タイトル・サブタイトル・キーワード欄の確定案あり）は適用待ちのまま。
3. **プロモーション文の使い方**: Apple 公式では順位に影響しない転換用コピー面だが、自社は課金注意文が枠を占めている（勝者は機能・便益のみ）。プロモ文は審査なしで即日変更できる唯一の面であり、使っていない分は即日回収できるギャップ。
4. **スクリーンショットの枚数と検索表示**: 勝者 9 枚に対し自社は計画 5 枚。Apple 公式では検索結果に出るのは最初の 1〜3 枚であり、枚数と先頭の設計の両方に差がある（自社の現行枚数はテキスト経路では未読、という社内注記あり。要目視確認）。
5. **副カテゴリ未使用**: Apple 公式で副カテゴリも索引対象であり、勝者 I am は Lifestyle を副に持つ。自社は Health & Fitness のみ。
6. **表記不一致**: サブスク名 "Anicca Pro" と実商品 Premium 系の不一致は、Apple のメタデータ正確性の観点でも、GEO 節の「複数面での一致」の観点でもマイナス。
7. **レビュー量の絶対差**: JP 48 件 vs 勝者 JP 1,778 件／US 738K 件。評価 4.5 は閾値（4.5 以上で 1.7 倍の帯）ちょうどにいるが、レビュー速度（1,000 DL あたり 12 件）が順位安定の前提であり、ここは配信量とセットでしか埋まらない。
8. **PPO（製品ページ A/B）の実施記録が見当たらない**: Apple 公式の転換改善手順（最大 3 案・90 日・信頼度 90%）を回した記録が社内仕様ファイルにない（未確認事項として記載）。

### (5) 次のアクション

- 既存の社内 ASO キーワード仕様（2026-11-05）の確定案を、次回提出のメタデータにそのまま適用する前提で差分表を維持する（タイトルにヘッド語、サブタイトルはタイトルと重ならない語、キーワード欄は重複排除・ロングテール先行、ja は英語欄の直訳を使わない）。判定は 28 日ルール（安定化平均 28 日・週次変動 ±4.2）を守り、短期の順位変動で一喜一憂しない。
- プロモーション文だけは提出を待たず即日で勝者型（機能→選択→終日リマインダーの便益コピー）へ組み替える。注意文は説明文の課金節へ寄せる（勝者分解 §6-3 の確定案あり）。
- サブスク名の表記不一致を解消し、ストア・Web・第三者面の表記を一致させる（GEO 節 (5) と同一作業）。
- ベースラインを先に取る: 対象 20〜40 クエリ×対象ストアフロントの順位、検索由来インプレッション・商品ページ閲覧・インストール、TTI（Health & Fitness 帯 30〜36% と比較）を変更前に記録する（社内仕様の計測手順）。
- 一誠型の主レーン（SNS 投稿の質 → ブランド検索 → ストア転換）と両立させる: ASO 作業の成果指標は「非ブランド語順位」だけでなく「ブランド検索経由の転換率」も併記し、投稿側の改善（転換率 58〜62% → 70% の型）と製品ページ側の改善を同じ表で見る。製品側の詳細計測は Mixpanel 一本化（Todo 項目39）と接続する。
- PPO はメタデータ適用後に 1 枚目スクリーンショットから開始し、メタデータの 28 日判定と PPO の判定を混ぜない。

### 推定（出典が取れていないため分離）

- JP「アファメーション」の順位が 32 ↔ 111 位と大きく往復する主因（レビュー速度不足か、メタデータの索引の弱さか、DL 速度か）は、要因別の実測がないため断定しない。Apple 公式が挙げる要因はテキスト関連性とユーザー行動の2系統のみ。
- 「キーワード ASO より投稿の質が先」という優先順位付けは、一誠の単一アプリ実測と自社の現在地（US 全語圏外＝そもそも非ブランド検索の受け皿が無い）からの運用判断であり、プラットフォーム一般の定理としては扱わない。

---

# 販売・受託プラットフォーム（今回調査分）

# マーケットプレイス4面 ベストプラクティス調査（出典つき）

- 調査日: 2026-11-07（JST）
- 対象: PromptBase / Whop / RenderHub / Legiit
- 範囲: 調査と記録のみ。出品・設定変更は行っていない。
- 規律: 「ベストプラクティス」と書くのは、名前のある一次の発信者（公式ガイド／ヘルプ、実際に売れている販売者本人の発信、実測データのある研究）の原典ページを実際に開いて確認できた主張だけ。出典は「誰の・どの文書か・URL」で付ける。出典が取れないものは **推定** と明示して分離する。
- 区分: **A層＝固定勝者／売れている出品の型**、**B層＝プラットフォーム一般のベストプラクティス**。プラットフォーム公表数字（手数料率・分配率）は公式ページで確認したものだけを「公式」と書く。
- KYC（本人確認）が必要な手法は **実施不可** と明記する。

---

## PromptBase

### (1) 核

#### (A) 売れている型

- **Game Builder 型（Claude Code 向け）が Trending の上位を占める。** PromptBase 公式マーケットプレイスのトップ／Trending 欄（2026-11-07 検索クロールで実読）では、`@bentleyartdesign` の Game Builder 群が繰り返し並ぶ。確認できた価格: Extraction Looter Game Builder $9.99、Night Siege Crafting Game Builder $9.99、Garden Horde Survivor Game Builder $9.99、Isometric Horde Defense Game Builder $9.99、Isometric Tactics RPG Game Builder $9.99、Cozy Pixel Farming Sim Game Builder $9.99、Slot Machine Roguelike Game Builder $9.99、3D Pirate Seas Roguelite Game Builder $4.99、3D Tower Defense Roguelite Game Builder $4.99、3D Dragon Rider Aerial Combat Builder $7.99、Ps1 Ghost Hunting Game Builder $11.24〜$14.99、Steamready Ps1 Horror Game Builder $14.99。型は「ジャンル＋ゲーム機構＋Game Builder」のタイトルで、1人の販売者が同一フォーマットで量産している。
- **公式が「最も売れる」と明言する型は2つ。** PromptBase 公式 Prompt Submission Guidelines: (i) high use-case factor（実プロジェクトで使えるもの。例: ロゴ、ブログ画像、商品ビデオ、アルバムアート、Tシャツプリント）、(ii) unique styles（公式曰く「The top selling category on PromptBase is "unique styles"」）。
- **価格帯の実測（一次ではない・研究サンプルとして分離）:** EarnQuill の 2026年7月実測サンプル（188件の live listing）では中央値 $5.99、91% が $10 以下、Trending ページ中央値 $3.99、テキスト系 $6.99、agent skills $9.99。AgentHustles の 2026-10-17 マーケットプレイス・サンプルでは大半が $2.99〜$4.99。いずれも公式数字ではなく調査者の実測値として扱う。

#### (B) 一般ベストプラクティス

- **手数料（公式）:** マーケットプレイス販売 20%（販売者が 80% を保持）、自社 referral link 経由 0%、custom job 10%。隠れた取引手数料なし。例: $10 の販売で保持額は $8.00／$10.00／$9.00（PromptBase 公式 Support）。
  - 補足（二次資料が公式 changelog／ブログを引用）: referral link の 0% は「5件以上の販売後」で、それ未満は 10% とする記述が AgentHustles／TheProofDesk にある。公式 Support 本文自体にはこの条件が書かれていないため、**要再確認（推定扱い）**。
- **承認の絶対条件（公式 Guidelines）:**
  - プロンプトは「テンプレート」でなければならない。買い手が編集できる変数を **[square brackets]** で入れる。単一の特定出力を出すだけのプロンプトは承認されない（ランダム生成型でスタイルが一貫するものは例外）。
  - test prompt（変数を全て埋めた完成形を1つ）を必須とする。指示文を混ぜた test prompt、複数プロンプト入りの test prompt は Decline 理由になる。
  - 英語のみ。スペルミス・意味不明文・買い手に役立たないタイトル／説明は Low quality output で Decline。
  - スコープの目安: アイデアの組み合わせは3つまで、それも広い概念同士。例として公式は「3D doctor animals with moustaches（4概念・ニッチ2つ）」を却下例、「3D animals with jobs（3概念・全て広い）」を改善例として提示。狭すぎる変種を量産するのではなく、1本を変数で汎用化する。
  - 例示出力は「同一スタイル・異なる被写体」で多様に。似すぎた出力（同じ被写体ばかり）は Decline。編集・コラージュ・文字入れした出力、Midjourney の 2x2 デフォルトグリッドは不可（raw 出力、アップスケール済みを出す）。
  - 単純すぎてタイトルと例示から再現できるプロンプト、既存出品と近すぎるプロンプト、公知ソースからの盗用、AI で大量生成したプロンプトは Decline／アカウント停止対象になり得る（公式 3.11／3.13／3.16／3.18）。
  - 審査時間は 15分〜36時間（公式 Support）。
- **面内検索SEO／ランキング（公式 Support）:**
  - ランキング・Trending の決定要因は **Sales / Views / Favorites / Uses / Reviews** の5つ。
  - 全出品ページは Google 向け SEO 最適化され、**プロンプトのタイトル＋説明がそのまま SERP の meta title／description になる**。Google Trends 等で需要を確認して作ることを公式が推奨。
  - サムネイルのバリエーション実験でクリックを伸ばす、analytics で効いている出品に倍賭けする、sales source（購入者がどこで何を検索したか）を見る、が公式の「How do I improve my views/sales?」の手順。
  - 買い手は詳細な instructions（プレビュー画像をどう生成したかの例を含む）を好み、リピート購入につながる（公式 Support）。
  - 実用品（Tシャツプリント等、実プロジェクト／ビジネスで使えるもの）がアート作品より長期的に売れる（公式 Support／Guidelines）。
  - **upload streak（公式 Support）:** 週1件以上の提出で継続する仕組みがあり、週は月曜〜日曜（現地時間）。提出すれば審査結果は問わない。
- **価格付け（公式に価格帯の指定なし）:** 公式 Support／Guidelines に推奨価格帯の明記は確認できなかった。新規販売者の価格上限 $19.99（販売実績で $99.99 まで上昇）、$9.99 超は PromptBase Select（月10件DLの購読）の対象外、という数字は PromptBase changelog を引用する二次資料（AgentHustles、RareConnections、iimagined）経由であり、**公式ページでの直接確認は取れていないため推定として分離**する。

### (2) 出典

1. PromptBase 公式「Prompt Submission Guidelines」— テンプレート必須、high use-case、unique styles がトップカテゴリ、Decline 理由の全リスト: https://promptbase.com/prompt-guidelines
2. PromptBase 公式「Support（FAQ）」— 手数料 20%／0%／10%、ランキング要因5つ、タイトル＋説明＝SEO meta、審査 15分〜36時間、upload streak: https://promptbase.com/support
3. PromptBase 公式マーケットプレイス（トップ／Trending 欄）— `@bentleyartdesign` の Game Builder 群と価格 $4.99〜$14.99 の実在確認: https://promptbase.com/?ref=2dm-tool-ai
4. EarnQuill「How to Sell AI Prompts Online in 2026」— 188件サンプルの価格実測（中央値 $5.99 等、公式ではない）: https://earnquill.com/ai-earning/how-to-sell-ai-prompts-online
5. AgentHustles「Sell AI prompts on a marketplace: 2026 Guide」— 公式 Support／changelog の引用整理と 2026-10-17 価格サンプル $2.99〜$4.99: https://www.agenthustles.com/h/sell-ai-prompts-on-a-marketplace/

### (3) 自社の現在地（実測事実）

- アカウント: keipanda
- 出品: 「3D Moon Bakery Delivery Game Builder」$5.99 が Live、「Lighthouse」$4.99 は Declined で編集が再審査中、「Paper Lantern」$9.99 は Pending。
- pending 上限（2件）のため新規提出はブロック中。
- 実測: 76 views、Gross $0.00、売上 $0。
- 勝者参照は Game Builder 型 `@bentleyartdesign`。

### (4) 従えていない点（ギャップ）

1. **出品数が勝者型に対して決定的に不足。** Live は 1件のみ。勝者 `@bentleyartdesign` は同一「Game Builder」フォーマットで Trending 欄に10件超が同時に出る量で勝っている。自社は pending 上限で新規提出が止まっており、量の型を再現できていない。
2. **週1件の upload streak を維持できる状態にない。** pending ブロック中は streak の前提（毎週提出）自体が崩れる。
3. **価格は型の範囲内だが検証材料がない。** Live の $5.99 は実測中央値 $5.99 と一致し、勝者の主力 $9.99 より低い。ただし売上 0・views 76 では価格が原因かどうかを判定できない（母数が不足）。
4. **Decline 済み「Lighthouse」の再審査が、公式 Decline 理由のどれに該当したかの照合記録がない。** テンプレート性（[変数]）、test prompt、出力の多様性、スコープ3概念以内、といった公式チェック項目との差分を数えた記録が本調査時点では無い。
5. **SEO／詳細 instructions の型が未検証。** 公式は「タイトル＋説明＝Google の meta」「プレビュー生成手順を含む詳細 instructions がリピート購入を生む」と明言するが、自社 Live 出品がこの2点を満たすかの実読照合は未実施（本調査は記録のみのため未着手として明記）。
6. **referral link 0% の活用以前の段階。** 売上 0 のため、仮に二次資料の「5件以上で 0%」条件が正しければ、まず面内販売で実績を作る順序になる。

### (5) 次のアクション

1. Pending 2件（Lighthouse 再審査・Paper Lantern）の審査結果を確定させ、pending 上限のブロックを解消する（新規提出の前提）。
2. Decline 理由を公式 Guidelines の節番号（3.3〜3.23）に対応づけて記録し、該当項目だけを直して再提出する。
3. Live 出品「3D Moon Bakery Delivery Game Builder」を公式チェックで実読照合する: [変数] の有無、test prompt、説明文にプレビュー生成手順が含まれるか、タイトルが検索語になっているか。
4. ブロック解消後、Game Builder 型で週1件以上の提出（upload streak）を再開し、出品数を勝者型の量へ寄せる。新規は「ジャンル＋機構＋Game Builder」の命名と $4.99〜$9.99 の価格帯を既定とする。
5. analytics の sales source と views を出品ごとに記録し、views が付くジャンルに倍賭けする（公式 Support の手順どおり）。

---

## Whop

### (1) 核

#### (A) 売れている型

- **型は「コース＋コミュニティ＋継続課金」。** Whop 公式ブログ（コース販売ガイド）が実例として挙げる売れている whop は、コース単体ではなくコミュニティを併設したもの: Digital Nomad University（Adam Caspary、238 members、全て5つ星レビュー）、Creator Cashflow（300人規模の Discord コミュニティ併設、ライブワークショップと 5-star rating）、Crystal Academy（毎日のライブセッション＋コース）。
- **販売ページの型（公式が「Perfect」と評した構成）:** 短く鋭い headline → 何を学べるか／なぜ重要かを benefits 中心に（features の羅列ではなく「Go from zero followers to TikTok pro in 4 weeks」型）→ testimonials／reviews の社会的証明 → メンバーの成果表示。
- **価格帯について:** 公式ブログに「Whop 全体の標準価格帯」の公表数字は確認できなかった。二次ガイド（InsightRaider）が示す $10-29/月（入門コミュニティ）、$39-79/月（プレミアム）、$99-199/月（高価値シグナル／ソフト）等は、同ガイド自身が「planning examples, not measured averages」と明記した計画例であり、**実測ではないため推定として分離**する。公式が明言するのは「初期価格は固定ではない。価格点を実験し、フィードバックで調整して sweet spot を探す」「初心者は traction のために低めから、専門性の高いものは高く」まで。

#### (B) 一般ベストプラクティス

- **手数料（公式ブログで確認）:** 月額料金 $0。取引は **2.7% + $0.30**（Whop 公式「Where to sell digital products」「How to sell online courses」ともに同表記）。価格形態は one-time／subscription（週・月・四半期・年）／BNPL を選択可。割引・期間限定プロモ・バンドルが公式に推奨される価格実験の手段。
  - 補足数字（公式 fee docs を引用する二次資料経由、**直接の公式ページ確認は未了＝推定として分離**）: 国際カード +1.5%、通貨換算 +1%、ACH 1.5%（上限 $5）、billing 自動化 0.5%、税務の徴収・納付代行 2%（有効時）、affiliate 処理 1.25%、出金は翌日 ACH $2.50／即時 4% + $1.00／crypto・Venmo 5% + $1.00／wire $23、最低出金 $10、紛争 $15（AllyOtter、Flatpass、Ruzuku が docs.whop.com/fees と whop.com/network/pricing を同内容で引用）。
  - **Discover（面内マーケットプレイス）手数料:** 旧来の 30% は、Whop changelog（2025-05-12）で 0% へ引き下げられたと複数の二次資料（AllyOtter、Sacra 経由の各レビュー）が一致して報じる。公式ブログ本文での直接確認は取れていないため、**「0% が現行」という扱いは推定**とし、実務では自社ダッシュボード表示で再確認する前提で記録する。30% を現行数字として使うことは禁止（旧数字）。
- **面内流通（Discover）:** 公式ブログは「Discover への露出と leaderboard ランキング」が組み込みの販売・マーケティング機能であると明記。販売ページの完成度とレビューが前提になる（公式コースガイドの販売ページ構成がそのまま審査・転換の型）。
- **集客の公式型:** 「post and pray は禁止」。公式コースガイドは TikTok／Discord／Twitter／YouTube Shorts での発信に加え、**Content Rewards**（クリッパーが切り抜きを拡散し、再生が出た分だけ支払う仕組み）で upfront リスクなしに micro-influencer 軍を作ることを推奨。スケール段階では upsell／バンドル（ボーナスレッスン、1:1、ダウンロード）で顧客単価を上げ、コミュニティの engagement が upsell と紹介を生む、という順序を公式が示す。
- **アフィリエイト:** 公式に affiliate program の設定が可能（自社商品を他者に売らせる）。料率は販売者設定であり、公式の固定数字は無い。二次ガイドの「既定 30%」表記は **推定** として分離する。
- **出金と本人確認:** Payouts の有効化には本人確認（KYC）が必要。これは自社では **実施不可**（下記現在地参照）であり、KYC 前提の出金最適化（出金方法の使い分け等）は全て実施不可として扱う。ゲスト購入（買い手側の購入導線）は KYC とは無関係に機能する。

### (2) 出典

1. Whop 公式ブログ「How to sell online courses the easy way」— 手数料 2.7% + $0.30・月額 $0、販売ページの型（headline／benefits／社会的証明）、Discover 露出、Content Rewards、upsell／バンドル、売れている whop の実例と数字（238 members 等）: https://Whop.com/blog/sell-online-courses/
2. Whop 公式ブログ「Where to sell digital products [2026]」— Whop の料金（月額なし、direct sales 2.7%）、all-in-one（courses／memberships／communities／downloads）＋ affiliate 選択肢: https://whop.com/blog/where-to-sell-digital-products/
3. InsightRaider「Sell on Whop 2026: 0% Platform Fee (Full Seller Guide)」— 価格帯は計画例である旨を自ら明記した二次ガイド。free tier から有料への転換、affiliate 20-30% 等の実践整理（一次ではない）: https://insightraider.com/en/blog/whop-marketplace-guide
4. AllyOtter「Whop requirements for vendors」— docs.whop.com/fees と Whop changelog（2025-05-12、Discover 30%→0%）の引用整理。公式 docs の直接確認が取れるまでの代替記録として明示: https://www.allyotter.com/guides/whop

### (3) 自社の現在地（実測事実）

- 商品「AI Monk Database Full Data」バンドル $29（定価の取り消し線 $36.25）。
- 売上 $0、63 views。
- Payouts は Inactive（本人確認待ち＝KYC のため **実施不可**）。
- 税務バナーは期限 2026-11-30 で未対応。
- ゲスト購入は可能（ログアウト状態で Buy now → チェックアウト到達を検証済み）。
- aniccaai.com の2ページから導線リンクあり。

### (4) 従えていない点（ギャップ）

1. **商品形態が勝者型と違う。** 勝者型は「コース＋活発なコミュニティ＋継続課金」。自社は one-time $29 のデータ・バンドル単体で、コミュニティ要素も継続課金も無い。公式の「one-time buyers を loyal な repeat customers に変えるコミュニティ」構造が欠けている。
2. **社会的証明がゼロ。** 公式型では reviews／testimonials が販売ページの中核。自社は売上 0 のためレビューが存在せず、Discover での転換材料が無い。
3. **価格実験をしていない。** $29＋取り消し線 $36.25 の1点のみで、公式推奨の「価格点を実験して sweet spot を探す」「割引・期間限定プロモ・バンドル」を回した記録がない。なお $29 は二次ガイドの計画例レンジ（$10-29/月）とは形態が違う（自社は月額ではなく one-time）ため、レンジ適合をもって適正とは言えない。
4. **面外集客が自社サイト2ページのリンクのみ。** 公式型の Content Rewards や SNS 発信による能動集客は未実施。63 views は導線の弱さと整合する。
5. **Payouts Inactive（KYC）＝実施不可。** 売上が立っても出金できない状態であり、これは手法の問題ではなく門の問題として分離する。同様に税務バナー（期限 2026-11-30）への対応も、本人情報の入力を要する範囲は実施不可として扱う。

### (5) 次のアクション

1. 販売ページを公式型へ寄せる: headline を benefits 型に書き換え、「何が入っているか」だけでなく購入後の成果を明示し、レビューが無い間は中身の具体物（収録範囲・件数・サンプル）で社会的証明の代替を作る。
2. 価格実験の設計だけ先に記録する: one-time $29 の現行に対し、割引プロモとバンドル構成の候補を用意し、views→checkout 到達率で判定する（ゲスト購入導線は検証済みのため計測可能）。
3. Discover 掲載の前提（ページ完成度）を確認し、不足要素（gallery／video、説明の正確性）を埋める。
4. Content Rewards の適用可否（KYC なしで開始できるか）を公式 docs で確認する。KYC が前提なら実施不可として記録し、面外は既存の自社導線強化に寄せる。
5. 税務バナー期限 2026-11-30 は、対応可否を実施不可の範囲と切り分けて記録し、期限前に再判定する。Payouts の KYC は実施不可のまま変更しない。

---

## RenderHub

### (1) 核

#### (A) 売れている型

- **公式の物差しは Trending／Best Selling 順。** RenderHub 公式「How To Sell Like a Pro」は「first page when sorted by Trending に出るベンダーのやり方に慣れよ」と明記し、公式フォーラムの価格ガイド（スタッフ回答）も「Trending／Best Selling 順で眺めて asset type ごとの sweet spot を掴め」とする。固定の単一勝者を名指しする公式資料は無いため、A層は「Trending 上位の型」として記録する。
- **価格の実在レンジ（出品ページの実読）:** Daz 系 props／poses で $9.10（定価 $14.00 の 35% off）、$11.25（定価 $15.00 の 25% off）、バンドル $21.00（定価 $28.00、合算価値 $33.00 表示）、$14.40（定価 $24.00 の 40% off）、小物 props $2.40（定価 $3.00）。セール割引は 10〜40% の範囲で常時かかっている型が上位の常態。
- **バンドルの型:** 複数アイテムを束ね、Combined Value（合算価値）を定価より高く表示して割安感を作る（gonzalesart のバンドル群で反復確認）。
- **無料サンプルの位置づけ（公式フォーラム・スタッフ回答）:** freebie は注意と信頼を得る手段だが、出しすぎると買い手が次の無料を待つようになる。「品質をそのまま表す少数の無料だけを出す」が公式回答の型。

#### (B) 一般ベストプラクティス

- **分配率 Tier（公式「How To Sell Your 3D Models」で直接確認）:** Tier 1 = 55%（1-50 items）、Tier 2 = 60%（51-100 items）、Tier 3 = 65%（101-200 items）、Tier 4 = 70%（201+ items）。非独占（exclusivity 要求なし）。
  - **注意（数字の不一致）:** 本調査の前提として渡された Tier 区分（Tier 2: 51-250、Tier 3: 251-1000、Tier 4: 1001+）は、2026-11-07 に実際に開いた公式ページの記載（51-100／101-200／201+）と一致しない。今後の記録・計算は公式ページの現行記載を正とする。
- **支払い（公式 Support FAQ）:** 支払いは毎月15日以降、前月末までの売上分。最低支払額 $20、未達分は翌周期へ繰越。支払い方法は PayPal／Venmo／Payoneer／小切手／米銀行振込（ACH）から選択（公式 Sell ページ）。**自社は支払い方法未設定のため、この step が未完了。**
- **商品名（公式 Sell Like a Pro）:** Title Case、シンプルで正確な記述名。キーワード詰め込み禁止、全小文字／全大文字禁止、「3D Model」の語はシステムが自動付加するので商品名に入れない。
- **説明文:** 買い手の判断に役立つ具体情報（特徴、ソフトウェア互換性、使用ケース）を自然な完全文で。Wikipedia 等の汎用情報は入れるな。キーワードは自然に含め、詰め込みは禁止。詳細な説明は Google／Bing の検索順位と AI 推薦での発見可能性を上げる、と公式が明記。法的条項を説明文や同梱ファイルに入れることは禁止（ライセンスは公式 Licensing Agreement に一元化）。
- **カテゴリ／タグ:** 最も適切な Category／Subcategory を選ぶ（誤分類は売れない）。検索タグは最大16個、関連するものは可能な限り多く使う。無関係タグは禁止。
- **技術情報:** 3D モデルは polygon／vertex 数を正確に（誤記は返金理由になる）。Photorealistic／Game Ready のドロップダウンは実際に該当する場合のみ Yes。
- **サムネイル／プロモ画像（公式が「最も効く」と明記）:** メインサムネイルは高品質・適切なクロップが最重要。単一ビューが基本（複数ビューはコレクション／バンドル／バリエーション時のみ可）。不要な文字やプロモグラフィックは避け、商品が正方形の大部分を占めるまで寄せる。プロモ画像は複数アングル＋詳細＋ワイヤーフレーム推奨。**360 turntable 等の動画がある商品は無い商品より常に売れる**（公式の断定表現）。
- **特集（featured）条件（公式 Support FAQ）:** 高品質で適切にクロップされたメインサムネイルと優れたプロモ画像が前提。**価格が低すぎる商品はマーケティング promotion に含まれない。**
- **価格付け（公式フォーラム・スタッフ回答）:** ベンダーが価格を決め、公式の最低／最高価格はない。安売り競争（race to the bottom）は全員の害になるため避ける。3D モデル買い手は価格が低すぎると低品質と判断することがある。無料は少数に留める。
- **セール／クーポン運用:** Sale Manager でセール設定（SALE タグが付き traffic が増える）、クーポンコードを自作して SNS で配る、forum の Product Showcase に新作を投稿する、SNS と外部サイトから自店へリンクする（Google traffic 改善）——いずれも公式 Sell Like a Pro Part 2 の手順。なお割引率の上限 40%・最短3日等の数字は公式フォーラムの admin 発言経由であり、Sell ページ本体での確認は取れていないため **参考（推定寄り）** として分離する。

### (2) 出典

1. RenderHub 公式「How To Sell Your 3D Models」— Tier 分配率 55%／60%／65%／70% と区分（1-50／51-100／101-200／201+）、非独占、支払い方法5種: https://www.renderhub.com/info/how-to-sell-3d-models-on-renderhub
2. RenderHub 公式「How To Sell Like a Pro and Make More Money」— 商品名・説明文・カテゴリ・タグ16個・ポリゴン数・サムネイル・プロモ画像・動画・価格・セール／クーポン／Showcase の全ガイド: https://www.renderhub.com/learning/how-to-sell-like-a-pro-and-make-more-money
3. RenderHub 公式「Contact Support（FAQ）」— 支払い周期（毎月15日以降・最低 $20）、featured 条件（サムネイル品質と適正価格、低すぎる価格は promotion 対象外）: https://www.renderhub.com/info/contact-support
4. RenderHub 公式フォーラム「Are there guidelines on what price to set for products?」（スタッフ回答、2025-05-19）— 価格の sweet spot は Trending／Best Selling で掴む、race to the bottom 回避、無料は少数: https://www.renderhub.com/forum/10572/are-there-guidelines-on-what-price-to-set-for-products

### (3) 自社の現在地（実測事実）

- 出品9品全て Active。
- 合計 Views 34、Downloads 1（無料サンプルのみ）、Sales 0、Earnings $0.00、Karma 205、Likes Received 5。
- 支払い方法は未設定。
- License Type フィールドが保存されないサイト側バグあり（サポートへ再送済み、返信待ち）。
- 手数料 Tier の前提情報として渡された区分: Tier 1 は 55%（1-50 items）、Tier 2 は 60%（51-250）、Tier 3 は 65%（251-1000）、Tier 4 は 70%（1001+）。※公式ページの現行記載とは区分が異なる（上記 (1)(B) の注意参照）。

### (4) 従えていない点（ギャップ）

1. **出品数が Tier 1 の下限域（9品／1-50）。** 次 Tier（公式区分では 51品で 60%）まで 42品不足。量そのものが分配率と発見可能性の両方を押し下げる構造になっている。
2. **支払い方法が未設定。** 公式の支払い条件（毎月15日以降・最低 $20）以前に、受け取り口座の設定 step が未完了。売上が立っても受け取れない。
3. **動画の有無が未確認。** 公式は「動画がある商品は常に売れる」と断定するが、自社9品に 360／動画があるかの記録がない。Views 34（9品平均 約3.8 views/品）は、サムネイルと動画という公式の最重要2要素が弱い可能性と整合するが、断定はできない（未計測として分離）。
4. **セール／クーポン／Showcase の運用記録がない。** 公式 Part 2 の販促手順（Sale Manager、クーポン、Product Showcase 投稿、外部リンク）を回した記録が本調査時点では無い。Downloads が無料サンプル1件のみという結果は、公式型の「無料は少数・品質の見本として」という使い方とは別に、有料品への転換導線が働いていないことを示す。
5. **License Type バグが未解消（サイト側、返信待ち）。** ライセンス表示は買い手の判断材料であり、公式が「ライセンスは公式 Agreement に一元化」とする前提の表示面が欠ける。ただしこれは自社作業ではなくサイト側障害として分離する。

### (5) 次のアクション

1. 支払い方法を設定する（PayPal／Venmo／Payoneer／ACH 等から、本人確認を要しない範囲で可能なものを選択）。設定可否が本人確認に抵触する場合は、その方法を「実施不可」と記録して他の方法を当たる。
2. 9品全品を公式チェックで実読照合する: メインサムネイルのクロップ（商品が画面の大部を占めるか、単一ビューか、不要な文字がないか）、タグが16個まで使われているか、説明文に互換性と使用ケースの具体情報があるか、動画の有無。差分を品ごとに数える。
3. 動画（360 turntable）を持たない品から優先的に追加する計画を作る。
4. Sale Manager でのセール設定とクーポン発行、forum の Product Showcase への投稿を、出品ごとに1回ずつ実施する運用を開始する（割引率は 40% を上限の目安とするが、公式本体未確認のため実画面の制限表示で確認する）。
5. 出品数を公式 Tier 2 の入口である51品へ向けて増やす。License Type バグはサポート返信を待ち、返信が来たら即時に全品へ反映する。

---

## Legiit

### (1) 核

#### (A) 売れている型

- **トップセラー本人の型: SerpAbove（Rushabh Shah）。** Legiit 公式ブログ掲載の本人発信: SEO サービスで累計 $150K 超、月 $10K（良い月は $20-30K）。開始当初（2019年）は2か月で $560 だった。実行した型は下記の通りで、全て本人の記述に基づく。
  - 平日2時間を Legiit に投資し、カテゴリのトップセラーを調べて自社サービスを「unique and compelling」に作り替えた（競合調査→サービス最適化）。
  - 説明文は well-written で comprehensive に、サムネイルは professional に投資した（本人の pro tip）。
  - 集客は無料＋有料の併用: Legiit Official Facebook Group への定期投稿と Roundup Post への掲載（無料）、Legiit の有料 promotion（カテゴリ広告枠を 2026年分まで予約）、メールマーケティングの継続。
  - **オファーの階段:** 最も単純なサービスに最大の割引をかけ、低価格品を lead gen にして注文と良レビューを集め、信頼を作ってから high-ticket サービスを出した。まとめ買い割引、リピーター割引も併用し、**売上の 90% がリピーター**（本人記述）。新規客には納品時に次回割引を付ける。
  -  communication: 注文の即時 acknowledgment、進捗の随時共有、延長が必要なら即連絡、詳細レポート。納品後も成果（順位変動）を追う aftercare。
  - Legiit Premium に upgrade して traffic と conversion を計測した。
- **タイトル型（公式ガイドが「top sellers が使う」とする3部公式）:** Primary Keyword（買い手が実際に検索する語）＋ Specific Deliverable（受け取る物の具体）＋ Differentiator（DA 50+ 等の検証可能な指標、ニッチ、納期、保証）。詳細は (B) 参照。

#### (B) 一般ベストプラクティス

- **手数料（公式 Terms／公式 Support で確認）:** 販売手数料 **15%**（販売者は 85% を保持）。affiliate 経由の販売では affiliate に 15% が追加で差し引かれ、販売者の取り分は **70%**（$100 の販売で $70／affiliate $15／Legiit $15）。第三者決済の利用時は 3% の processing fee がかかる場合があり、wallet 資金での支払いは対象外。出金手数料は1回 $3、出金は1日 $1,000 まで（公式 Terms 第13・16項）。escrow は買い手の完了 marking 後、検証（最大5日）を経て出金可能になる（自動完了は3日）。
- **タイトル最適化（公式ブログ「How to Optimize Your Legiit Service Title in 2026」）:**
  - タイトルは Legiit 検索と Google の両方で **第1のランキング要素**。アルゴリズムはタイトルの先頭を重く見るため、primary keyword を先頭 2-4語以内に置く。
  - 上限は **50文字**。「I Will」で始めない（最も価値ある文字の無駄）。professional／high quality 等の検証不能な形容詞は differentiator にならない。キーワードの詰め込み・重複は禁止。
  - primary keyword の見つけ方（公式の5手法）: 検索バーの autocomplete、カテゴリを Best Selling／Top Rated で並べて上位タイトルの反復語を見る、買い手の言葉で書く（Editorial Link Placement ではなく Guest Post）、取引意図の語を選ぶ、Facebook グループで毎月公表される検索キーワード上位 20-40 を見る。
- **面内検索SEO 全体（公式 Support「Legiit Search」）:** キーワードを置く場所は title＋subtitle、meta title、meta description、description 本文、tags、FAQs の全て。サービスページをブログ記事のように最適化する。詳細で well-written な説明が販売率を上げる。正のレビューが順位を押し上げる。検索バー広告（promote keyword）は導入価格 $5/日・最大3日（公式 Support 記載）。
- **転換チェックリスト（公式ブログ「Conversion Checklist」11項目）:** (1) 高品質でクリーンなサービス画像（カテゴリ画面とサービス画面の両方で確認）、(2) title と subtitle で提供内容・差別化・信頼を伝え、subtitle を title の繰り返しにしない、「I will provide…」等の空句を使わない、(3) 買い手の problem を冒頭で言語化する、(4) 自分が解決策であることを示す、(5) objections を先回りで潰す、(6) 得られる物／得られない物を 100% 明確にする、(7) 文法と書式、(8) 社会的証明（レビュー・testimonial・サンプル・スクリーンショット）を説明文に埋め込む、(9) 価格は競合の実績（レビュー数・納期遵守率・社会的証明）と見比べて決め、信頼が不足するうちは同等価格を付けない、(10) 販売者プロフィールを完全に埋める、(11) 競合ではなく自分を選ぶ理由を1つ作る。
- **レビューと評判の位置づけ:** 公式 Support は「高品質な納品と良いコミュニケーションで正のレビューを得ることが順位を押し上げる」とし、公式ブログも 5-star reviews の蓄積が marketplace での visibility を決めるとする。SerpAbove 型の「低価格の単純サービスでレビューを先に集める」階段は、この公式構造と一致する。

### (2) 出典

1. Legiit 公式ブログ「How to Optimize Your Legiit Service Title in 2026」— タイトルが第1ランキング要素、3部公式、50文字上限、先頭へのキーワード配置、キーワードの見つけ方5手法、誤り6種とチェックリスト: https://legiit.com/blog/service-seo-guide
2. Legiit 公式ブログ「Conversion Checklist For Your Legiit Service Page」— 転換の11項目（画像、title/subtitle、problem 提示、objections、社会的証明、価格、プロフィール）: https://legiit.com/blog/conversion-checklist-for-legiit
3. Legiit 公式 Support「Legiit Search | How Can I Make my Service Appear on Legiit Search?」— キーワード配置先の全リスト、レビューが順位を上げること、promote keyword $5/日: https://legiit.freshdesk.com/support/solutions/articles/36000454540-legiit-search-how-can-i-make-my-service-appear-on-legiit-search-
4. Legiit 公式 Support「Legiit Seller Fees」— 85%/15%、affiliate 経由 70%/15%/15% の内訳: https://legiit.freshdesk.com/support/solutions/articles/36000106556-legiit-seller-fees
5. Legiit 公式「Terms Of Use and Licensing Agreement」（2025-09-25 更新）第13・16項 — Seller Fee 15%、processing fee 3%（wallet は対象外）、出金 $3/回・$1,000/日上限、escrow の検証手順: https://legiit.com/terms
6. Legiit 公式ブログ「How To Make $10k Per Month On Legiit」— トップセラー SerpAbove（Rushabh Shah）本人の発信。累計 $150K、月 $10-30K、リピーター 90%、低価格 lead gen の階段、有料 promotion と Facebook Group の併用: https://legiit.com/blog/how-to-make-10k-per-month-on-legiit

### (3) 自社の現在地（実測事実）

- サービス2件とも ACTIVE。
- Total Earnings $0、注文0、メッセージ0、ウォレット $0.00。
- セッション喪失をパスワードリセットで回復済み。
- 再問い合わせ禁止期間 〜2026-11-08 18:29 JST。

### (4) 従えていない点（ギャップ）

1. **注文0・レビュー0で、公式の順位構造の入口に立てていない。** 公式は「正のレビューが順位を押し上げる」「タイトルが第1要素」とするが、レビューがゼロの段階では SerpAbove 型の「低価格の単純サービスで最初の注文とレビューを取る」階段が未実施。
2. **タイトルの3部公式への照合記録がない。** 自社2件のタイトルが「primary keyword を先頭 2-4語に」「具体的な deliverable」「検証可能な differentiator」「50文字以内」「I Will で始めない」を満たすかの実読照合は未実施（本調査は記録のみ）。
3. **キーワード配置の全面展開が未検証。** 公式 Support が挙げる配置先（subtitle、meta title、meta description、tags、FAQs）の全てにキーワードが入っているかの確認記録がない。
4. **転換11項目の未達が推定される項目:** 社会的証明は注文0のため説明文に埋め込む材料自体が無い。販売者プロフィールの完成度も未検証。※これは実測ではなく構造からの推定として分離する。
5. **集客の手がゼロ。** SerpAbove 型の無料集客（Official Facebook Group 投稿、Roundup Post）と有料 promotion のどちらも実施記録がない。メッセージ0は、面内検索以外からの流入も無いことと整合する。
6. **価格の根拠が未記録。** 公式チェックリストは「競合のレビュー数・実績と見比べて価格を決める。信頼が不足するうちは同等価格を付けるな」とするが、自社2件の価格がこの比較で決められた記録がない。

### (5) 次のアクション

1. 再問い合わせ禁止期間（〜2026-11-08 18:29 JST）の終了を待つ。それまでサポートへの再連絡はしない。
2. 2件のタイトルを公式チェックリスト（Section 6）で実読照合し、差分を数える: キーワードの位置、deliverable の具体性、differentiator の有無、50文字、「I Will」の有無。
3. キーワード配置を公式 Support の全配置先（subtitle／meta title／meta description／tags／FAQs）で点検し、不足箇所を埋める。
4. SerpAbove の階段を自社に適用する設計を記録する: 2件のうち1件を「単純で低価格な lead gen 型」に寄せ、最初の注文とレビューを取ることを目的化する（価格変更の実施は本調査の範囲外のため、次工程で判断）。
5. 無料集客から始める: Legiit Official Facebook Group と Roundup Post への掲載可否と手順を確認する。有料の promote keyword（$5/日）は、タイトルとページの照合が済んでから検討する。

---

## 横断メモ（4面共通）

- **共通する公式構造:** 4面とも「タイトル／商品名＋説明文がそのまま検索（面内＋Google）の入力になる」「レビュー／販売実績がランキングを押し上げる」「サムネイル／画像の品質がクリックを決める」が公式に明記されている。自社の4面はいずれも売上 $0・レビュー 0 であり、順位構造の初期条件を満たすための「最初の1件の販売とレビュー」が共通のボトルネックである。
- **数字の扱い:** 手数料・分配率で公式ページの直接確認が取れたのは PromptBase（20%／0%／10%）、RenderHub（55-70% Tier、最低支払 $20）、Legiit（15%、affiliate 時 70%）。Whop は公式ブログで 2.7% + $0.30 を確認し、それ以外の細目は二次資料経由のため推定として分離した。RenderHub の Tier 区分は、渡された前提数字と公式の現行記載が食い違うため、公式記載を正として記録した。
- **実施不可の分離:** Whop の Payouts 有効化（KYC）は実施不可。本人確認を前提とする出金・税務・本人情報入力の各手法は、売上手法とは切り離して実施不可のまま保持する。

---

# 日本クラウドソーシング3面 ベストプラクティス調査（出典つき）

- 調査日: 2026-11-07
- 対象: CrowdWorks / ランサーズ / ココナラ
- 範囲: 調査と記録のみ。本ファイル作成に伴う応募・送信・出品変更は行っていない。
- 調査規律の適用:
- 「ベストプラクティス」と断定するのは、名前のある一次発信者（公式ガイド／ヘルプ、実際に受注しているワーカー本人、認定ランサー等の実名発信、実測データのある調査）の主張で、原典ページを `browser.open` で実際に開いて確認できたものだけ。本文中では **[原典確認済み]** と付す。
- 検索結果の抜粋だけで原典を開けなかったもの（ランサーズ公式LPの一部は直接取得で HTTP 405、note 1件は 404、ココナラ1件は取得レート制限）は **[検索抜粋のみ＝推定扱い]** と明示し、ベストプラクティスとして断定しない。
- A層＝固定勝者／実際に受注している型、B層＝プラットフォーム一般のベストプラクティス、を分けて書く。自社に固定勝者がいない面は「A層は未固定」と正直に書く。これが最大のギャップである面が多い。

---

## CrowdWorks

### (1) 核

#### (A) 受注している型 ― 固定勝者／実測で受注している者の型

- **A層は自社では未固定である。** 下記は「受注している者として原典で確認できた型」の棚卸しであり、自社がその1人を固定してコピーしているという意味ではない。
- **相談所の実回答者 ezuki 氏の型 [原典確認済み]**: 初案件までの動きは「いいクライアント探し」が最重要。最初の仕事が決まるまで毎日100件以上の仕事／クライアントを見て目を養う。応募先の選別基準は、クライアント評価 **4以上（できれば4.8以上）・プロジェクト完了率80%以上（できれば95%以上）・過去の評価コメントで揉めた形跡がない・高単価**。良い募集が出たらその日のうちに応募する。理由として、クライアントの約1割は「条件さえ合えば早く契約してスタートさせたい」層で、受注件数が少ない状態でも契約に至ることがある、と本人が述べている。
- **相談所の実回答者 Ryotetsu 氏の型 [原典確認済み]**: (1) 最初の数行でスキルが伝わるよう簡潔にポイントを抑える（応募が多い案件ではクライアントは全文を読まない前提）。(2) 応募テンプレートを複数パターン用意し即応できるようにする。ただし闇雲に応募せず、クライアントの実績・評価・本人確認済みか・継続コメントがあるかを確認する。(3) CrowdWorks上で実績がなくても他所での経験をポートフォリオ化して提示する。
- **相談所の実回答者 navi 氏の型 [原典確認済み]**: クライアントと直接接点を持てるのは基本的に「応募時の1回きり」。したがって応募時点でポートフォリオ等で自分の優位性を全てぶつける。挨拶だけで済ませる応募は負ける、という主張。
- **初心者で高受注率を出した実名note事例 [検索抜粋のみ＝推定扱い]**: note著者 chanachan_ 氏の記事タイトル／抜粋では「1ヶ月で応募62件・受注31件・受注率50%（うち継続4件）、登録初日に初受注」。ただし原典を `browser.open` したところ 404 で本文を確認できなかったため、この数字はベストプラクティスとして採用しない。件数の目安の参考（推定）としてのみ分離して置く。

#### (B) 一般ベストプラクティス ― 数字つき

1. **応募量と競争の実態**
- 公式は応募数の目安を公表していない **[原典確認済み: 公式ガイドに記載なし]**。
- 競争率の実測（二次調査・検索抜粋）: ライティング案件1件あたり応募者数の中央値 **13人**、Webデザイン／HP制作 **23人**、事務 **7人**、システム開発 **1人**（2026年9月に案件989件を数えた note「AI手順ラボ」記事の抜粋）**[検索抜粋のみ＝推定扱い]**。別の二次記事（atsoho）抜粋では「データ入力・ライティング・簡単なデザインでは1案件に20〜50人が応募することも珍しくない」**[検索抜粋のみ＝推定扱い]**。
- したがって「通らないのが普通」が前提で、勝負は応募総数ではなく「選別した案件への即日応募＋冒頭で伝わる提案」である、というのが ezuki／Ryotetsu 両氏の一致した主張 **[原典確認済み]**。
- **推定（自社計算として分離）**: 仮に1応募あたり受注率を3%／5%／10%と置くと、少なくとも1件取る確率が80%を超える応募数は順に53件／32件／16件になる。これは incomelabo 記事が示したシナリオ計算の抜粋であり、公式の受注率ではない **[検索抜粋のみ＝推定]**。

2. **提案文の型**
- 公式ガイド **[原典確認済み]**: 興味のある仕事が見つかったら「希望の契約条件を設定しメッセージを添えて応募」し、メッセージには **経歴・スキル・応募動機** を記載する。プロジェクト形式では実績・経歴の提出に加え見積もりを求められることもある。
- 相談所スレッド16764の受注率向上策 **[原典確認済み]**: 提案文は「私はこうした経験があり、貴社の〇〇という課題を解決できます」と **クライアントの課題→解決策→成果** の順で具体的に書く。成果にフォーカスし、納期目安を明示し、可能なら希望より少し早めを提示する。
- 冒頭の作法 **[原典確認済み: ezuki／Ryotetsu]**: プロフィールも提案も **最初の数行／最初の5行** で決まる。挨拶や名前の自己紹介から入らず、できること・根拠を先に置く。

3. **返信速度**
- 公式の数値基準は確認できなかった（ランサーズのような「24時間以内返信率」の公開指標は CrowdWorks 公式ガイド原典には無い）**[原典確認済み: 不在の確認]**。
- 相談所スレッド16764 **[原典確認済み]**: 「メッセージにはできる限り早く返信することで誠実さをアピール」「進捗報告を怠らない」が受注率向上策として挙げられている。具体的な時間（何時間以内）の一次基準は無いため、「○時間以内がベストプラクティス」とは書けない。

4. **単価と手数料**
- 公式 **[原典確認済み: 仕事を受注する方法ガイド]**: 受注までは無料。報酬確定時にワーカーが受け取る報酬の **5%〜20%** をシステム利用料として徴収。
- 公式の料率内訳（検索結果で公式ページを確認）: 10万円以下の部分 **20%**、10万円超〜20万円以下の部分 **10%**、20万円超の部分 **5%**、タスク形式は一律 **20%**。つまり小額の固定報酬契約ほど手取りの目減り率が最大になる構造であり、低単価を量で積む型は粗利で不利になる **[出典は公式feeページ・検索抜粋で料率を確認]**。
- 相場そのもの（文字単価等）は職種で大きく異なり、プラットフォーム一般の単一相場は公式に無い。二次調査の抜粋ではライティング文字単価の中央値 **1.3円**、1円未満が13%（989件調査）**[検索抜粋のみ＝推定扱い]**。

5. **プロフィール設計**
- ezuki 氏 **[原典確認済み]**: 検索一覧ではプロフィールの前半しか表示されない。したがって **見出し文＋最初の5行** に (1) 何ができるか（業務内容）(2) 経歴（掲載歴・受賞歴など）(3) 使用できるソフト、の3点を入れる。ここが無いプロフィールはスカウトも応募転換も起きない。
- スレッド16764 **[原典確認済み]**: 具体的なスキル・経験を詳細に書き、 **数字や成果を入れる**（例: 〇〇案件で売上20%アップ）。清潔感のあるプロフィール写真、成果物を整理したポートフォリオ、資格の記載が信頼を上げる。小さな案件でも丁寧に対応して良い評価を集め、納品後にレビュー依頼とポートフォリオ掲載許可を取ることが次の提案につながる。

6. **実績の積み方**
- スレッド16764 **[原典確認済み]**: 初めは競争率の低い／初心者向け案件から始め、小さな成功とレビューを積み重ねて信頼を上げる。スキルに合った案件にフィルタリングして提案時間を効率化する。

### (2) 出典

- CrowdWorks公式「仕事を受注する方法（働きたい方向けガイド）」― 発信者: 株式会社クラウドワークス公式 ― https://crowdworks.jp/pages/guides/employee/index ― 原典開封確認済み（応募メッセージへの経歴・スキル・応募動機の記載、3形式、手数料5〜20%）。
- CrowdWorks公式「みんなのお仕事相談所 ID:16171 初案件受注のコツを教えてください」― 回答者: ezuki 氏／Ryotetsu 氏／navi 氏（実ワーカー）― https://crowdworks.jp/consultation/threads/16171 ― 原典開封確認済み（クライアント選別基準、最初の5行、テンプレ複数用意、応募時1回が勝負）。
- CrowdWorks公式「みんなのお仕事相談所 ID:16764 クラウドワークスでウォーカーの受注率を高めるための道」― https://crowdworks.jp/consultation/threads/16764 ― 原典開封確認済み（プロフィール・提案文・料金納期・レビュー・迅速返信の8項目）。
- CrowdWorks公式 システム利用料ページ ― https://crowdworks.jp/pages/guides/employee/fee ― 検索結果で料率表を確認（20%／10%／5%、タスク20%）。
- [検索抜粋のみ] note「クラウドワークス初心者が1ヶ月で31件受注して分かった『通る提案文の構造』」著者 chanachan_ ― https://note.com/chanachan_/n/nefb02bc684aa ― 開封時404のため本文未確認。数字は推定扱い。
- [検索抜粋のみ] 「収入源を増やすラボ」最初の1件の取り方（受注確率のシナリオ計算、公開募集6件の競争人数）― https://incomelabo.com/crowdworks-first-job/
- [検索抜粋のみ] note「AI手順ラボ」案件989件調査（応募者数中央値・文字単価中央値）― https://note.com/aitejunlab/n/n6b9fca99cf8f

### (3) 自社の現在地（実測事実・依頼時に与えられた値）

- 提案管理ページの実測総数 **811件**。ただし検証済みの増分は小さく、本数が独り歩きしている疑いがある。
- 最新の実測では新規応募は **1件/回程度**。返信スイープは高速で回っている。
- 固定報酬の契約は **10件で合計税込371円・控除後285円** と極小。受注率は低い。

### (4) 従えていない点（ギャップ）

1. **量の質が逆転している**: 総数811件という「量」はあるのに、直近の新規応募は1件/回程度で、ezuki 氏の「毎日100件以上の案件／クライアントを見て、良い募集にその日のうちに応募」とも、Ryotetsu 氏の「複数テンプレで即応できる体制」とも一致しない。過去の累計本数を成果として数える運用自体が、原典の型とずれている。
2. **単価構造が最悪の帯に集中している**: 契約10件で税込371円＝1件平均37.1円。公式料率では10万円以下の部分は20%（＋税）差し引かれる帯であり、低単価の極小契約を積んでも粗利はほぼ残らない（371円→285円で差額86円）。「高単価クライアントを選ぶ」という ezuki 基準と真逆の結果になっている。
3. **クライアント選別をやった証跡がない**: 評価4以上／完了率80%以上（できれば95%以上）・揉めた形跡なし、という選別基準で応募先を絞った記録が現在地の事実に無い。選別なしの大量応募は Ryotetsu 氏が戒めた「闇雲に応募」と同型になる危険がある。
4. **プロフィール冒頭5行の検証がない**: 見出し＋最初の5行に「できること／経歴／使えるソフト・ツール」が入っているかを原典基準で照合した記録がない。
5. **A層（固定勝者）がいない**: 誰の提案文・プロフィールを差分ゼロでコピーするのかが固定されていない。プラットフォーム一般論（B層）だけで応募を回している状態。

### (5) 次のアクション

1. 811件という総数の数え直しを先に行う（提案管理の実在件数・期間・重複を1件ずつ照合し、「独り歩き」を解消してからでないと受注率の分母が成立しない）。
2. 応募先選別シートを作る: クライアント評価・完了率・過去コメント・単価を記録し、ezuki 基準（評価4以上、完了率80%以上、高単価）を満たす案件だけを「本応募」と数える運用に切り替える。
3. プロフィールを原典基準で監査する: 見出しと冒頭5行だけを抜き出し、業務内容・経歴・使用ツール＋数字成果が入っているかをチェック表で判定する。
4. 固定勝者を1人決める: CrowdWorks内で自社と同ニッチ・同商品形態で継続受注している実名ワーカーを1人選び、そのプロフィール冒頭と提案構成を実際に開いて記録してからコピー対象にする（未選定のまま量を増やさない）。
5. 単価の下限を置く: 手数料20%帯でも粗利が残る最低契約額を決め、それ未満の固定報酬は「実績作り」と明示した場合だけに限定する。

---

## ランサーズ

### (1) 核

#### (A) 受注している型 ― 固定勝者／認定ランサーの型

- **認定ランサー 奥川駿平（oku305）氏の公開プロフィール型 [検索抜粋で反復確認]**:
- キャッチフレーズ: 「SEO×広告×SNS運用┃歴11年のマーケターが戦略設計から運用まで一気通貫対応」― **スキル掛け合わせ × 経験年数 × 一気通貫という提供範囲** を1行で言い切る型。
- 自己紹介の冒頭: 「」と **金額・完了率・リピーターを数字で先に置き**、続けて「2015年よりBtoB企業を中心に…一貫して任せられることが最大の強み」と対象と強みを書く。
- 実績の書き方: 累計5,000本超のSEO記事、オウンドメディア1年で月間1万PV超、リード獲得200件以上、META広告 ROAS最大256%・CVR5.85%、Instagram約4ヶ月でフォロワー5,000人増・最大再生222,000回、のように **施策ごとに検証可能な数字** を並べる。
- 公開指標: 実績 **687件**（検索時点の表示ゆれ 680〜687件）、満足率 **100%**、完了率 **98%**、リピーター **41人**。
- これは自社が既にキャッチフレーズと自己紹介文を書き換える際のコピー元にした型であり、A層として最も具体的に記録できている事例である。ただし「文面を寄せた」ことと「数字の裏付けが自社にある」ことは別であり、後者は無い（(4)参照）。
- **提案営業で成約した TAKA 氏の実験 [検索抜粋のみ＝推定扱い]**: ランサーズ公式メディア「THE LANCER」の取材記事の抜粋では、営業代行ランサー TAKA 氏が提案営業を **20件実施し、返信率35%、成約率10%（2件獲得）**。公式LPが直接取得で405となり原典本文を開けなかったため、この数字は推定として分離する。ただし「公募への提案以外に提案営業という獲得経路がある」こと自体は公式メディアの存在で確認できる論点である。
- **公式が示す提案文の型 [検索抜粋のみ・LP405のため推定扱いだが、構成は複数検索結果で一致]**: ランサーズ公式「受注のためのアクションを取ろう①: 公開PJ・コンペに提案する」の抜粋によれば、提案文に入れる要素は **挨拶（冒頭で「おっ」と思わせる一言）／提案内容（業務内容・予算・スケジュール・進め方）／経歴／実績・得意／自己PRポイント**。良い例の条件は「クライアントや依頼内容を把握したうえでの提案（自己アピールだけで終わらない）」「読みやすい構成で冒頭に引っかかりがある」「修正回数やコミュニケーション方法など想定問答が入っている」。提案営業編（同⑤）の抜粋では「誰にでも送れるテンプレートは嫌がられる」「相手の課題をどう支援・解決できるかという視点で具体的に書く」が公式の注意である。

#### (B) 一般ベストプラクティス ― 数字つき

1. **ランク制度がそのままベストプラクティスの数値基準になっている [原典確認済み]**
- レギュラー: 表示名・プロフィール画像・自己紹介 **300文字以上**・スキル／ポートフォリオ／出品サービスのいずれか1つ・ビジネス経験／資格のいずれか1つ・本人確認・機密保持確認・電話確認・最終ログイン1ヶ月以内。
- ブロンズ: レギュラー条件 ＋ **プロジェクト方式の受注1件以上**。
- シルバー: ブロンズ条件 ＋ 過去1年のプロジェクト **完了率90%以上**・過去1年の **平均評価4.8以上**・ **24時間以内のメッセージ返信率80%以上**。
- 認定ランサー: 獲得報酬額が **各依頼カテゴリ（小カテゴリ）の上位20%**、過去1年のクライアント評価で **「満足」の割合95%以上**、仕事完了率 **90%以上**、タスク承認率 **90%以上**（タスク実績がある場合）、最終ログイン1ヶ月以内、各種認証・プロフィール登録（写真・表示名・自己紹介300文字以上・本人確認・機密保持確認・電話確認・ランサーズチェック・スキル・資格）。毎月審査。
- 出典: ランサーズ公式ヘルプ「認定ランサーの基準を教えてください」、公式お知らせ「ランサー様向けにランク制度を導入いたしました」。いずれも原典開封確認済み。

2. **返信速度 [原典確認済み]**
- 定義: **返信率 ＝ 24時間以内に返信した件数 ÷ 返信した件数**。対象は過去1年間に返信を5件以上行った者。「要返信」チェックが無いメッセージは計算に入らない。未返信のままの件は母数に入らない点にも公式が注意している。
- 公式が基準を置く理由: クライアントへの聞き取りで「クイックレスポンスが安心につながる」という声が多く、**24時間以内80%** での対応を求めている。
- したがってランサーズでは返信速度は感覚ではなく **80%が公式の下限線** である。

3. **プロフィール設計 [原典確認済み]**
- 公式初心者向けページ: 「過去の受注データを分析した結果、**プロフィールが充実しているほど受注率が高い**」。顔写真で信頼感、本人確認・電話認証など **4つの認証**、ポートフォリオで実際の作品を見せる（動画は外部リンク可、画像が難しい職種はキャプチャ＋タイトル・説明で詳細実績を示す）。
- 公式LP「プロフィールを整えて、選ばれるランサーになろう」: クライアントのほとんどは提案文やパッケージ説明だけでなくプロフィールを確認して選定する。判断観点は (1) スキル・経験のマッチ (2) 具体的な実績・ポートフォリオ (3) 仕事の姿勢・コミュニケーション方法 (4) 一緒に仕事をしたい人か。顔写真で信頼性が上がり受注率・受注金額が上昇することがある、表示名は本名で信頼度が上がる、キャッチフレーズは特徴・得意を一言で、自己紹介は経歴・実績＋人となり、スキルは程度（経験）まで書く。
- 同LPの数値: プロフィールを整えて **レギュラーランクになると受注率が約17倍上がる** と公式が表示している。理由は、ランサー検索と提案一覧のデフォルト表示がレギュラー以上に限られるため（ランクなしは操作しないと表示されない）。

4. **応募量・提案の考え方**
- 公式は「何件応募すべきか」の数値を公表していない **[原典確認済み: 不在の確認]**。TAKA氏の20件→返信35%→成約10%は1人の実験値であり一般基準ではない（推定扱いとして分離済み）。
- 一般論として公式LPが繰り返すのは量より **案件理解の具体性** であり、テンプレの使い回しは明示的に否定されている **[検索抜粋のみ＝推定扱い・LP本文]**。

5. **単価**
- プラットフォーム一般の単価基準は公式に無い。認定の物差しは絶対額ではなく **カテゴリ内上位20%という相対順位** である点が重要で、「いくら稼げばよいか」は自社カテゴリの分布を見ないと決められない **[原典確認済み: 認定基準の構造から]**。

6. **実績の積み方**
- ランクの階段がそのまま積み方である: まず認証と300文字以上の自己紹介でレギュラー（表示される土俵に立つ）→ プロジェクト1件完了でブロンズ → 完了率90%・評価4.8・返信率80%を1年維持してシルバー → 報酬上位20%＋満足95%で認定。**1件の完了と評価の質が、応募本数より先に来る設計** になっている。

### (2) 出典

- ランサーズ公式ヘルプ「認定ランサーの基準を教えてください」― https://www.lancers.jp/faq/l1005/328 ― 原典開封確認済み。
- ランサーズ公式お知らせ「ランサー様向けにランク制度を導入いたしました」― https://info.lancers.jp/20004 ― 原典開封確認済み（レギュラー／ブロンズ／シルバーの全基準）。
- ランサーズ公式ヘルプ「返信率の定義を教えてください」― https://www.lancers.jp/faq/l1005/352 ― 原典開封確認済み（定義式・過去1年・5件以上・80%を求める背景）。
- ランサーズ公式「プロフィールで受注率UP!（初心者向け）」― https://www.lancers.jp/help/beginner/lancer/profile ― 原典開封確認済み（充実度と受注率の相関を公式が明言、4認証、ポートフォリオ）。
- ランサーズ公式LP「プロフィールを整えて、選ばれるランサーになろう」― https://www.lancers.jp/lp/beginner/l/02 ― 原典開封確認済み（選定観点、レギュラーで受注率約17倍、デフォルト表示の仕組み）。
- ランサーズ公式LP「受注のためのアクションを取ろう①／③」― https://www.lancers.jp/lp/beginner/l/03 ／ https://www.lancers.jp/lp/beginner/l/05 ― 直接開封はHTTP 405で失敗。構成要素は検索抜粋で確認したため推定扱い。
- 奥川駿平（oku305）公開プロフィール抜粋（ランサーズ検索結果に反復表示）― 代表URL: https://www.lancers.jp/menu/detail/1341439?ref=profile_search ― キャッチフレーズ・総受注額1,600万円超・実績・完了率・リピーター数を検索結果で確認。
- [検索抜粋のみ] ランサーズ公式メディア THE LANCER「TAKAが案件獲得法を教えます／提案営業」― 20件・返信率35%・成約率10%の実験値。原典LPを開けなかったため推定扱い。

### (3) 自社の現在地（実測事実・依頼時に与えられた値）

- 提案数 **541（プロフィール表示）vs 提案管理525件** の食い違いあり（差16件）。
- 受注数 **1→2件へ増加**（2件目の実態は未特定）。報酬額の記録は **¥0**。
- ランクは **ブロンズ**。**24時間以内返信率71%**。
- プロフィールのキャッチフレーズと自己紹介文を認定ランサー奥川駿平（oku305）の型へ書き換え済み（公開ページで反映確認済み）。

### (4) 従えていない点（ギャップ）

1. **返信率が公式の下限を9ポイント下回っている**: 71% vs シルバー／認定圏の基準 **80%**。返信率の定義上、未返信は母数に入らないため、71%は「返信したものの中でも24時間超えが29%ある」という意味であり、スイープの回転数ではなく **24時間以内に初回返信を閉じる運用** が足りていない。3面の中で唯一、公式数値基準に対して自社の遅れが数字で特定できる項目である。
2. **ブロンズの次（シルバー）の3条件が未達／未計測**: 完了率90%以上・平均評価4.8以上・返信率80%以上。返信率は71%で未達確定。その他2つは現在地の事実に数字が無く、計測自体が欠けている。
3. **受注2件・報酬¥0の矛盾が未解消**: 受注が増えたのに報酬記録が¥0では、認定基準の「カテゴリ上位20%」以前に、自社の台帳が実態を映していない。2件目の実態（金額・完了有無・評価）が未特定のままでは完了率も計算できない。
4. **提案数の二重帳簿**: 541 vs 525の差16件。分母が2つある状態では受注率（2÷541か2÷525か）も確定できない。CrowdWorksと同型の「本数の独り歩き」がここでも起きている。
5. **oku305型への書き換えは文面のみで、数字の裏付けが無い**: 奥川氏の型の核はキャッチフレーズの言い回しではなく、冒頭に置かれた検証可能な数字（1,600万円超・98%・リピーター41人・施策別成果）である。自社は文面を寄せたが、自社の数字（受注2件・報酬記録¥0）では同じ冒頭を書けない。型のコピーが「形式だけ」で止まっている。

### (5) 次のアクション

1. 返信率を80%以上へ: 要返信メッセージの24時間以内初回返信を台帳化し、71%→80%の差（返信済み件数ベースで何件の遅延を無くせば届くか）を件数で出す。シルバーの入口条件として最優先。
2. 受注2件の実態特定: 契約金額・完了／検収有無・評価・カテゴリを1件ずつ確定し、報酬¥0の記録を実額に直す。完了率と平均評価をシルバー基準（90%／4.8）と並べて表示する。
3. 提案数の突合: プロフィール表示541と提案管理525の差16件の内訳（取消・期限切れ・重複等）を特定し、正本を1つに決める。
4. プロフィールの数字欄を自社の実数で書き直す: 奥川氏の数字を借りるのではなく、自社で検証できる小さな数字（完了件数・対応範囲・返信方針）から冒頭を構成し、実績が増えるたびに差し替える運用にする。
5. 提案文を公式型で監査する: 直近の提案から抜き出し、挨拶の冒頭一言・提案内容（進め方・スケジュール・修正／連絡方法の想定問答）・経歴・実績・自己PRの5要素が入っているか、案件固有の一文があるかをチェックする（テンプレ一括送信の有無を含む）。

---

## ココナラ

### (1) 核

#### (A) 受注している型 ― 固定勝者／大量販売者の型

- **A層は自社では未固定である。** 特に「勝者コピー元の個別出品URLが記録されていない」という既知の欠落があるため、下記は原典で確認できた大量販売者の型の棚卸しに留まる。
- **JOHN DOE DESIGN（ココナラ歴10年以上）氏の型 [原典確認済み]**: 出品ページ「実績4800件の私がココナラ出品について助言します」で、本人が **総合販売実績5つ星を維持したまま5,000件以上、累積売上30,000,000円超** と明記。提供形態は電話相談 **200円/分（税抜）** という低単価の入口で相談を受け、サムネイル作成等の本サービスへつなげる階段構造。購入前にDMで相談内容を送らせる事前ヒアリングを必須にし、同業者の購入を断るなど **入口の選別** まで設計している。出品の悩みとして本人が列挙するのは「サービス説明の文章」「サムネイルを魅力的に」の2点であり、売れる出品の詰まりどころが文章と画像であることを大量販売者自身が示している。
- **プラチナ大量販売者の型 [検索抜粋のみ＝推定扱い]**: 「初心者が1ヶ月でプラチナランク達成」を掲げる出品（日本マーケティング）では、取引実績 **5,013件超／累計売上1,523万円超／初月売上343,200円** を冒頭の実績として提示している。原典ページの開封が取得レート制限で完了しなかったため数字は推定扱いとするが、「冒頭に累計件数と累計売上を置く」形式は JOHN DOE 氏と共通する。

#### (B) 一般ベストプラクティス ― 数字つき

1. **プラットフォームの主従: 出品が主、募集応募は従 [原典確認済み]**
- ココナラ公式「ココナラ通信7月号 出品活動チェックポイント完全版」の手順は (1) プロフィール作成 → (2) 初サービス出品 → (3) 閲覧を増やす（広告機能は1,000円から、クリック課金）→ (4) 出品者ランクを目標にする → (5) クーポンで新規もリピーターも逃がさない、の順であり、募集への応募は **「番外編: 実績を積めてきたら、積極的に受注を増やしに行こう」** と最後に置かれている。
- 同記事の募集応募への公式コメント: 「受注に繋げるには応募の数を稼ぐことも大事ですが、**一つ一つの応募を丁寧に作成することが肝**」。量と丁寧さの両立が公式の言い方であり、量だけではない。

2. **出品者ランクの数値基準 [原典確認済み]**
- レギュラー: 累積の有料販売件数 **1件以上**。
- ブロンズ: 累積販売 **10件以上** ＋ 累積納品完了率 **80%以上**。
- シルバー: 直近3ヶ月の販売 **10件以上** ＋ 直近3ヶ月の納品完了率 **85%以上** ＋ 最終ログイン1ヶ月以内。
- ゴールド: 直近3ヶ月の販売額 **5万円以上** ＋ 納品完了率 **90%以上** ＋ 平均評価 **4.8以上** ＋ 本人確認済み。
- プラチナ: 直近3ヶ月の販売額 **10万円以上** ＋ 納品完了率 **90%以上** ＋ 平均評価 **4.8以上** ＋ 本人確認済み。
- つまりココナラの物差しは応募数ではなく **直近3ヶ月の販売額・完了率・評価** であり、月額換算ではプラチナは約3.3万円/月ペースの販売が下限になる。

3. **プロフィール設計 [原典確認済み]**
- 公式「ココナラ通信10月号」: プロフィールは「あなただけのホームページ」。注力点は2つ。(1) **出品サービスの裏付け**: 経歴・ポートフォリオは出品サービスに関連するものを充実させ、目的・背景・注力点まで書いて成果物の解像度を上げる。得意分野は情報を詰め込みすぎず、見積り相談したくなる内容を端的に。(2) **第一印象**: キャッチフレーズと自己紹介文が最初に目に入る。並び順（自己PR→出品サービス）に合わせ、「〇〇をやってきたので → 〇〇のサービスが提供できます」という流れで構成する。経験職種と経験年数を上部に置く。
- 公式の総括: プロフィールの質は「登録した項目数」ではなく「充実度」で決まる。活動に関係のない情報が多いと読まれなくなる。
- 公式7月号: 購入者はサービスページからプロフィールを合わせて確認することが多いため、**サービス内容とプロフィールの繋がり** を意識して文章を調整すると購入に結びつく可能性が高まる。

4. **出品ページ（サービス）の作り [原典確認済み]**
- サムネイル: 検索画面で目に留まるよう、自信のある作品か **インパクトのあるキャッチコピー入りの画像** を使う（公式7月号）。
- 閲覧が起点: 購入に結びつけるにはまずサービス閲覧を増やす。出品直後は検索上位に出にくいため、公式は広告機能（1,000円〜、クリック課金）と分析ページでの推移確認、伸びてきた段階でのクーポン（対象5パターン）を公式の打ち手として提示している。

5. **募集への応募の型 [原典確認済み]**
- 公式ヘルプ「ココナラ募集の流れ（単発型／応募者向け）」: 応募では **提案内容を具体的に** 記載し、提案額は募集者の予算を踏まえて設定（設定額がそのまま販売価格になる、カテゴリ別最低価格未満は不可）、完了予定日を設定する。
- 募集者に表示されるのは応募内容に加えて **販売実績・評価・納品完了率**。つまり募集応募でも、出品側の実績3点が選定材料になる。購入期限は募集終了から7日間で、過ぎれば不採用通知が自動配信される。

6. **返信速度・単価**
- 返信速度の公式数値基準は、今回開いた公式原典（ランク・通信・募集ヘルプ）には無い **[原典確認済み: 不在の確認]**。「何時間以内がベストプラクティス」とは書けない。
- 単価はカテゴリ別最低価格が下限として存在するのみで、一般相場の公式提示は無い。JOHN DOE 氏のような **低単価の入口（200円/分）→本サービス** という階段設計は、大量販売者1人の型としてA層に置く。

### (2) 出典

- ココナラ公式「出品者ランクとは」― https://coconala.com/pages/about_rank ― 原典開封確認済み（5ランクの販売実績・納品完了率・評価・本人確認・最終ログインの全基準）。
- ココナラ公式「ココナラ通信10月号 購入率UPにつながる! 出品者プロフィールの注力ポイント」（2023-10-11）― https://coconala.com/news/892 ― 原典開封確認済み。
- ココナラ公式「ココナラ通信7月号 出品活動チェックポイント完全版 〜初出品から軌道に乗せるまで〜」（2024-07-12）― https://coconala.com/news/1035 ― 原典開封確認済み（出品の手順、サムネイル、広告1,000円〜、クーポン、募集は番外編で「数を稼ぐことも大事だが一つ一つ丁寧に」）。
- ココナラ公式ヘルプ「ココナラ募集の流れ（単発型／応募者向け）」― https://help.coconala.com/hc/ja/articles/218272718-%E3%82%B3%E3%82%B3%E3%83%8A%E3%83%A9%E5%8B%9F%E9%9B%86%E3%81%AE%E6%B5%81%E3%82%8C-%E5%8D%98%E7%99%BA%E5%9E%8B-%E5%BF%9C%E5%8B%9F%E8%80%85%E5%90%91%E3%81%91 ― 原典開封確認済み（提案内容・提案額・完了予定日、選定時に販売実績・評価・納品完了率が表示されること、購入期限7日）。
- JOHN DOE DESIGN 出品ページ「実績4800件の私がココナラ出品について助言します」― https://coconala.com/services/1039866 ― 原典開封確認済み（5,000件以上・累積売上3,000万円超・200円/分・事前DM必須）。
- ココナラ公式「ココナラ通信11月号『信頼』が売れる秘訣! プロフィール充実のススメ」― https://coconala.com/news/1263 ― 開封したが本文テキストが取得できず見出しのみ確認。内容は10月号と同趣旨のため新規の根拠には使っていない。
- [検索抜粋のみ] プラチナ出品「初心者が1ヶ月でプラチナランク達成! 取引実績5013件超え」― https://coconala.com/services/2060420 ― 開封が取得レート制限で未完了のため数字は推定扱い。

### (3) 自社の現在地（実測事実・依頼時に与えられた値）

- 当日累計応募 **43件**（数え直し未実施で **48 vs 41** の食い違いあり）。
- ダッシュボードの応募数 **78件 vs 応募管理58件** の不整合あり（差20件）。
- 今月売上はダッシュボード **¥5,000 vs 売上管理 ¥3,900** で **¥1,100の差が未解消**。
- 最新ラウンドで出品磨き3件・画像差し替え1件・新規応募2件。
- 既知の欠落: **勝者コピー元の個別出品URLが記録されていない**。

### (4) 従えていない点（ギャップ）

1. **主従が逆転している**: 公式の型は「出品が主、募集応募は実績を積んだ後の番外編」。自社の計測と活動の中心は応募件数（43／78／58件という応募の数字ばかりが並ぶ）であり、出品側の核指標（直近3ヶ月の販売額・納品完了率・平均評価、閲覧数→購入率）が現在地の事実に1つも無い。ランク基準と照らす物差し自体を持っていない。
2. **売上の正本が2つあり、差¥1,100が未解消**: ¥5,000 vs ¥3,900。ゴールド基準（直近3ヶ月5万円）との距離を測る以前に、今月の実額が確定していない。3面共通の「数字の二重帳簿」がここでは金額に直接出ている。
3. **応募数の不整合が最大**: 43件という当日累計自体に48 vs 41の揺れがあり、累計でも78 vs 58と20件ずれている。何件応募したかが確定しないため、公式の言う「数を稼ぐ」段階にいるのかすら判定できない。
4. **勝者コピー元のURLが無い＝検証不能**: 出品磨き3件・画像差し替え1件を行ったとあるが、どの勝者のどの出品（タイトル・サムネイル・価格・実績表示）をコピーしたのか記録が無いため、差分ゼロの確認が原理的にできない。JOHN DOE 型のような「冒頭に累計件数・累計売上を置く」「低単価の入口→本サービス」の階段も、自社出品に適用した記録がない。
5. **プロフィールと出品の繋がりの監査がない**: 公式10月号の注力点（経歴・ポートフォリオが出品の裏付けになっているか、自己PR→出品サービスの流れ）で自社ページを照合した記録がない。

### (5) 次のアクション

1. 数字の正本を1つに決める: 応募数は応募管理を正として78 vs 58の差20件の内訳を特定し、売上は売上管理を正として¥1,100差（手数料・キャンセル・計上タイミング等）の原因を1件ずつ突き止める。当日累計の48 vs 41も数え直して確定する。
2. 出品側の核指標を台帳に新設する: 出品ごとに閲覧数・お気に入り・販売件数・直近3ヶ月販売額・納品完了率・平均評価を記録し、ランク基準（ブロンズ10件／シルバー直近3ヶ月10件・85%／ゴールド5万円・90%・4.8）との距離を表示する。
3. 勝者を1出品だけ固定してURLを記録する: 自社と同カテゴリで販売実績が大きい出品を1つ選び、URL・タイトル・サムネイル文言・価格・オプション構成・冒頭の実績表示を原典として保存してから、自社出品との差分表を作る（磨きはその後）。
4. プロフィール監査: 公式10月号の2注力点（裏付け／第一印象の流れ）で自社プロフィールを照合し、出品と無関係な記述の削除と、経歴・ポートフォリオの出品連動への書き換えを行う。
5. 募集応募の位置づけを公式どおりに戻す: 応募は「数を稼ぎつつ1件ずつ丁寧に」の範囲で継続し、主の成果指標は出品の販売に置く。応募時に募集者へ表示される3点（販売実績・評価・納品完了率）を上げることが応募の成約率にも効く、という公式ヘルプの構造を運用に反映する。

---

## 3面を通じた総括（調査者の整理・推定を含む）

- **公式数値基準が最も厳密なのはランサーズ**（返信率80%・完了率90%・評価4.8／満足95%・報酬上位20%）。自社の遅れが数字で言えるのもランサーズだけであり、返信率71%→80%が3面で最も具体的な是正点である。**[原典確認済み基準への自社実測の当てはめ]**
- **3面共通の自社側の病は「本数の二重帳簿」である**: CrowdWorks 811件の検証済み増分の小ささ、ランサーズ 541 vs 525、ココナラ 78 vs 58／48 vs 41／売上¥1,100差。いずれもベストプラクティス以前に、分母と実額が確定していない。 **[自社実測事実の横断整理]**
- **3面共通で A層（固定勝者）が弱い**: ランサーズのみ奥川駿平氏の型への書き換え実績があるが数字の裏付けが無く、CrowdWorksとココナラは固定勝者そのものが未記録。B層の一般論で量を回す運用から、A層1人を固定して差分を数える運用への転換が共通の次手である。 **[推定ではなく、現在地の事実からの帰結として記載]**
- 本調査で「ベストプラクティス」と断定できなかったもの: 応募本数の公式目安（3面とも公式提示なし）、返信速度の公式基準（CrowdWorks／ココナラでは原典で確認できず）、単価の一般相場（公式提示なし・二次調査は推定扱い）。これらを数字で語る場合は、必ず一次発信者の実測を新たに開いてから行うこと。

---

# フリーランス系プラットフォーム 一般ベストプラクティス調査（出典つき）

- 調査日: 2026-11-07（JST）
- 対象: Guru / GoLance / Fiverr / Freelancer.com / Mercor
- 目的: 「プラットフォーム一般のベストプラクティス（B層）」と「稼いでいる型（A層）」を分けて、原典で確認できた主張だけを記録する。調査と記録のみ。本ファイル作成に伴う応募・送信・設定変更はしていない。
- 調査規律の適用:
  - 「ベストプラクティス」と書いた項目は、名前のある一次発信者（公式ヘルプ／公式ガイド／公式価格ページ／公式データ発表、または実際に稼いでいる本人の発信、実測データのある研究）の原典ページを `browser.open` で実際に開いて確認したものだけ。
  - 原典で確認できなかった推論・他社まとめサイト経由の数字は **「推定」** または **「二次情報・未確認」** と明示して分離した。
  - KYC（ID認証・W-9・Webカメラでの本人確認・Persona 等）が必要な手法は **「実施不可」** と明記した。これは会社の既定（本人確認を人間に回さない／エージェント完結できない門は実施不可）に従う表記であり、手法自体の是非ではない。

---

## Guru

### (1) 核

#### (A) 稼いでいる型

- **一次情報で確認できる「型」は、単発の安売りではなく「All-Time Transaction Data が積み上がった長期・複数雇用主型」である。** Guru 公式は、雇用主がフリーランサーを選ぶ際に All-Time Earnings（累計収益）／直近12か月収益／雇用主数／有料インボイス総数／最大の雇用主（Largest Employer）／加入日を見る、と明記している。つまり勝ち筋は「累計・直近・雇用主の分散」がプロフィール上で可視化される状態を作ることであり、実績ゼロの間はその表示自体が無い（未払いのフリーランサーには表示されず、代わりに ID Verification ステータスが Quote と共に表示される）。
- **特定の個人名・特定カテゴリで「いくら稼いだか」を Guru 公式が発表した一次データは、本調査では確認できなかった。** カテゴリ別のトップ表示（例: Twilio 開発者で年間表示 $149,200／yr・100% 等の検索結果スニペット）はプラットフォームの検索一覧の表示であり、検証可能な「稼いでいる型」の研究データではないため、A層の根拠としては採用しない。ここは **推定にしない／未確認として空ける** のが正しい扱い。

#### (B) 一般ベストプラクティス — 数字つき

1. **ビッド（Quote）の総量は会員種別で硬く決まる。** 無料 Basic は **10 Bids/月**、有料は全プラン **50 Bids/月**。1 Quote = 1 Bid 消費。Premium Quotes は 4〜6 Bids 追加消費、Sales Messages（雇用主への直接連絡）は 3〜5 Bids 消費（プランにより異なる）。有料の年間ロールオーバーは 100〜300 Bids（上限あり）。
2. **手数料は会員で下がる。** Job Fee は Basic 9% / Basic+ 9% / Professional 7% / Business 6% / Executive 5%。月額は Basic 無料 / Basic+ $11.95 / Professional $21.95 / Business $33.95 / Executive $49.95（年払いで最大27%割引）。「量を増やす」と「手数料を下げる」が同じ有料化で同時に起きる設計。
3. **プロフィールは「キーワードリッチな Service と Portfolio を増やす」ことが公式の指示。** 公式 How It Works は “The more keyword-rich services and portfolios you have, the better.” と明記。完成したプロフィールが Quote の代わりに実力を示す、という前提。
4. **Quote は「詳細に、スコープ理解を示して」送る。** 公式は “Establish a clear understanding with the Employer by sending a detailed Quote when you apply.” とし、支払条件は4種類（Hourly / Fixed price / Task-based / Recurring）から選ぶ。
5. **24時間以内のフォローアップが公式 Tip。** “Consider following up after 24 hours if you haven't received a response to your Quote.” 送って終わりにしない。
6. **仕事開始前に SafePay へ資金を入れてもらう。** 公式は初回取引では特に SafePay 推奨、開始前に最低残高の入金を求めることを手順として示す。WorkRooms で合意・ファイル・インボイスを一元化する。

### (2) 出典

- Guru 公式「How Guru Works for Freelancers」— プロフィールの作り方（keyword-rich services/portfolios）、詳細な Quote、24時間フォローアップ、SafePay、4つの支払条件: https://www.guru.com/how-it-works-freelancer/
- Guru 公式「Guru Pricing for Freelancers - The Benefits of Paid Membership」— Job Fee 9%/9%/7%/6%/5%、Bids 10/50/50/50/50、月額 Free/$11.95/$21.95/$33.95/$49.95、Premium Quotes・Search Boost・年間ロールオーバー: https://www.guru.com/pricing-freelancer/
- Guru 公式 Help「All-Time Transaction Data - Freelancers」— 累計収益・直近12か月・雇用主数・インボイス数・Largest Employer・加入日の定義、未払い時は表示なし＋ID Verification 表示: https://www.guru.com/help/freelancer/all-time-transaction-data-freelancer/

### (3) 自社の現在地（実測事実）

- 提案 7件は全て反応なし。
- 残ビッド 3件（補充は 2026-11-28）。

### (4) 従えていない点（ギャップ）

- **量が公式の上限設計に対して枯渇している。** 無料枠は 10件/月が公式上限であり、自社は既に 7件消費・残3件。公式が想定する「50件/月で回す」運用（有料）とは 5倍の差がある。ただし有料化は支出であり、本調査の範囲では判断しない。少なくとも「残3件で新規に広く打つ」ことは公式の量設計と両立しない。
- **24時間フォローアップを実施した記録が現在地に無い。** 公式 Tip の中でも最も安価に実行できる項目が未実施のまま、7件が無反応で放置されている状態と読める。
- **All-Time Transaction Data がゼロであることが最大の構造的弱み。** 公式が雇用主の第一の信頼材料と明記する累計実績が無い間は、Quote 本文と Portfolio で代替するしかない。ID Verification で代替表示される経路は **KYC のため実施不可**。
- **Service／Portfolio が「keyword-rich」に増やされているかは、現在地の実測事実からは確認できない（未計測）。** 公式手順との照合ができていない。

### (5) 次のアクション

1. 残3ビッドは使わずに温存せず、公式の選別思想（プロフィールに合う案件のみ）に沿って、最も適合度の高い3件だけに「詳細 Quote＋スコープ理解の明示」の型で使う。汎用テンプレ一括送信はしない。
2. 既存7件について、送信後24時間を過ぎたものから順に1回だけフォローアップする運用を台帳化する（公式 Tip の実施証跡を残す）。
3. 補充日 2026-11-28 を台帳に固定し、補充後に「何件打つか」ではなく「どの Service キーワードで何件打つか」を先に決める。
4. Service／Portfolio のキーワード棚卸し（自社が売るサービス名が雇用主の検索語と一致しているか）を、応募より先に実施する。

---

## GoLance

### (1) 核

#### (A) 稼いでいる型

- **公式ガイドが示す勝ち筋は「ニッチを絞った専門家型＋長期関係型」である。** goLance 公式「How to Start Freelancing — From Zero to First Client」は、最も速くクライアントを取るのは広く何でもやる者ではなく具体的に絞った者だとし、例として “Email copywriter for e-commerce brands” は “copywriter” 単体より検索可視性でも成約でも勝つ、と明記する。同ガイドは goLance を “Best for long-term client relationships” と位置づける。
- **2026年の高需要ニッチ（公式ガイド列挙）:** AI prompt engineering / workflow automation、Cybersecurity consulting、UX・product design、B2B content writing、Data analytics / visualization、No-code development。
- **金額の一次データ（goLance 上で実際にいくら稼げているかの分布）は公式からは発表されておらず、本調査では確認できなかった。** よって A層の金額は **未確認** とする。手数料が低い等の宣伝文句を「稼げる証拠」として扱わない。

#### (B) 一般ベストプラクティス — 数字つき

1. **プロフィール完成度 80% が絶対の門。** 公式 Help は、80%未満では「プロフィールが他ユーザーに表示されない」「提案を送信できない」と明記。自社の 70% はこの門の手前であり、提案以前の問題。
2. **完成させる中身は公式に列挙されている:** 顔が分かるプロフェッショナルな写真、詳細な Profile Summary（経験・スキル・資格・情熱）、Work Experience（職名・責任・成果）、Portfolio（Project Items を複数）、スキルを最新に保つこと、Social Links（LinkedIn 等）。
3. **Profile Video は「任意だが強く推奨」。** 公式 Help は、信頼・透明性を作り、目立ち、採用率を上げる、とする。ただし自社の文脈では、顔出し動画が前提になる案件フローについては後述のとおり別扱い。
4. **Skill Assessments を取る。** 公式 Help は、能力の証明・強みの理解・雇用主の安心材料になるとする。
5. **提案文は 300語未満・個別化・クライアント中心。** 公式ガイド Step 6 は次を明記: 相手を名前で呼ぶ、ブリーフ内の具体事項に言及して読んだ証拠を示す、自分の履歴書ではなく「相手のために何をするか」から入る、関連サンプル／成果を1つ入れる、**300語未満**に収める。加えて「3〜5日後の丁寧なフォローアップで成約する方が、テンプレ一発より多い」とする。
6. **オファーは1文で定式化する。** “I help [specific client type] achieve [specific outcome] through [your service].” この1文をプロフィール冒頭と全提案の冒頭に使う、が公式ガイドの指示。プロフィール Bio の構造も「誰を助けるか → 成果 → 信頼シグナル → 明確な CTA」の4点。
7. **Portfolio は 3〜5点の強いサンプル＋1段落の Bio で足りる。** 実績が無ければ spec work（架空ブランドの試作）、知人・非営利の割引／無償案件での実名サンプル、既存物の作り直し（Before/After）が公式に認める作り方。
8. **価格の基準式（公式ガイド）:** Hourly Rate = (Desired Monthly Income ÷ Billable Hours) × 1.3。例: 月 $3,000・80時間なら約 $49/時。初心者は Fixed-price project 型から始めることを公式は推奨。税金用に受取の 25〜30% を初日から分離することも明記。
9. **契約・Milestone なしに着手しない。** 公式ガイドは、プラットフォーム内置の支払保護と契約／マイルストーンが有効になる前に仕事を始めるな、と明記。
10. **goLance Blog の提案論（公式ブログ、実務家寄稿）:** 提案は「仕事を取るもの」ではなく「自己提示の機会を作る招待」に過ぎない、定型文（boilerplate）が最大の後悔の元であり、1件の完全個別化は12件の使い回しより良い、相手の名前を冒頭で呼ぶ、要件の全点を A〜Z で拾う、価格と期間を早めに提示する、最も関連する実例を添付する（プロフィールを見に行かせない）— という趣旨。※同ブログ記事は AMP 経由の抜粋確認となったため、細部の逐語引用は行わず要旨のみ採用する。

### (2) 出典

- goLance 公式 Help Center「Working as a Freelancer on goLance」— 80%完成の門、Project Items、Profile Video 推奨、Skill Assessments、詳細サマリー等の Tips: https://help.golance.com/hc/en-us/articles/37764986550164-Working-as-a-Freelancer-on-goLance
- goLance 公式 Help Center「Freelancing with goLance」— 80%で表示・提案可能になること、写真／サマリー／経歴／Portfolio／Video／Skill Tests／Social Links の各節、成功プロフィールを研究せよという指示: https://help.golance.com/hc/en-us/articles/37765383969684-Freelancing-with-goLance
- goLance 公式「How to Start Freelancing — From Zero to First Client」— ニッチの絞り方、高需要ニッチ、オファー1文式、Portfolio 3〜5点、価格式 ×1.3、提案 300語未満・個別化、3〜5日フォローアップ、契約／Milestone 前着手禁止: https://golance.com/blogs/how-to-start-freelancing-2026
- goLance 公式 Blog「Freelance Project Proposals Between Myth and Reality」— 定型文の否定、完全個別化、名前で呼ぶ、全要件への対応、価格・期間の早期提示、最適実例の添付: https://blog.golance.com/freelance-project-proposals-between-myth-and-reality/amp/

### (3) 自社の現在地（実測事実）

- 残高 $0.00、Contracts 0、Proposals 3件＋送信済み提案7件は全件変化なし。
- プロフィール完成度 70%。
- 時給案件9件は全て提案フロー Step 1 of 3 の動画ゲートで送信中止（動画要件を理由に送れていない）。
- 残件は Tax Form、goWallet、スキル評価2件（うち1件 `es5ae5wayr` は Webカメラ必須）。

### (4) 従えていない点（ギャップ）

- **最優先ギャップは完成度 70% ＜ 公式門 80%。** 公式上、この状態ではプロフィール自体が他者に表示されず、提案もできないのが原則。自社で「Proposals 3件＋送信済み7件」が存在することと公式の門の関係（過去に80%だった時期があったのか、案件種別で門が違うのか）は **未確認** であり、まず現物で照合が必要。いずれにせよ 80%未達は公式ベストプラクティス違反の筆頭。
- **動画ゲートで9件が止まっている。** 公式 Help 自体は Profile Video を「任意だが強く推奨」とする一方、個別案件フロー Step 1 of 3 で動画が必須化されている実測がある。顔出し／実写動画が前提の経路は、自社の運用形態では恒常的なボトルネックになる。動画必須の時給案件に固執せず、動画なしで提案できる案件種別へ寄せる選別が必要。
- **スキル評価 `es5ae5wayr` は Webカメラ必須のため実施不可（KYC／本人確認に準ずる門）。** もう1件のスキル評価がカメラなしで可能かは未確認。
- **Tax Form は税務フォームであり、内容によっては KYC／本人情報の提出に該当する。** 提出可否はフォームの中身を実読してから判断すべきで、本調査では「未実施・要中身確認」とする。安易に「やれば完成度が上がる」とは書かない。
- **提案の型（300語未満・名前呼び・ブリーフ固有事項・サンプル1点・3〜5日フォローアップ）を既存10件に適用した証跡が現在地に無い。** 全件変化なしという結果は、量の問題ではなく型とフォローアップの問題として読むのが公式に沿う。

### (5) 次のアクション

1. 完成度を 80%へ上げるために不足しているセクションを画面で特定し、動画と Tax Form と Webカメラ評価を除いた項目（Summary の詳細化、経歴、Portfolio 3〜5点、Social Links、通常の Skill 情報）だけで 80%に届くかを先に検証する。届かない場合は、その事実自体を台帳に記録する。
2. 動画ゲートのない案件種別（固定価格等）だけを対象に提案対象を組み直し、9件の動画必須案件は「送れない案件」として台帳で区別する（送った数に数えない）。
3. 新規提案は公式型（300語未満・個別化・サンプル1点添付）で作成し、送信後3〜5日のフォローアップ日時を送信と同時に台帳へ書く。
4. スキル評価は、Webカメラ必須の `es5ae5wayr` を **実施不可** として閉じ、残り1件はカメラ要件の有無を実読してから可否を決める。

---

## Fiverr

### (1) 核

#### (A) 稼いでいる型

- **需要の伸びで見る「今売れている型」は、Fiverr 公式の Business Trends Index（Fall 2025、2025-12-10 発表、GlobeNewswire 配信）が一次データである。** 直近6か月の検索伸び: faceless YouTube video creator **+488%**、AI automation **+136%**、prompt engineering **+76%**、AI video creators **+66%**、faceless YouTube video editor **+59%**、AI influencer **+43%**、AI music video **+25%**。同時に TikTok promotion +66%、social media managers +33%、Instagram reels +24% と、短尺・SNS 運用の人間スキルも伸びている。つまり A層は「AI動画／自動化の実装型」と「プラットフォーム固有の短尺編集型」の2系統。
- **春版（Spring 2025）では AI Agent 関連検索が +18,347% という数字が Fiverr 公式 Index として各所で引用されているが、本調査ではその原典プレスリリースを直接開いての確認はできていないため、本ファイルでは Fall 2025 の確認済み数字のみを A層の根拠とし、+18,347% は「二次引用・未確認」と分離する。**
- **売り手の収入分布の一次データは Fiverr 公式からは公開されていない。** 「中央値 $100〜500/月」「Top Rated は $3,000〜10,000/月」等の数字は第三者サイトの推計であり、本ファイルではベストプラクティスとして採用しない（**推定**として参考にも載せない。必要なら別途、出典の質を明記して調査する）。

#### (B) 一般ベストプラクティス — 数字つき

1. **Gig は「店構え」であり、検索順位の第一要素は Relevancy（関連性）。** 公式 Search 解説は、関連性が最も重要なランキング要素であり、リスティングの説明と検索クエリの一致で測る、と明記。その他の要素は Historical appeal（過去の検索・取引での魅力）、Client satisfaction、レビュースコア、価格、Availability、Responsiveness、機械学習モデル。
2. **タイトルは “I will” の後に強い動詞＋最も関連するキーワード。** 文法的に正しく、が公式 Best Practices の指示。サブカテゴリを閲覧して最頻出キーワードを拾い、Search Tags に入れる。
3. **説明文に入れるべきものが公式に列挙されている:** 提供価値とスキル、提供しないサービス、対応言語／プラットフォーム／ソフトウェア、納期とリビジョン回数。他セクションと重複させない。説明文の上限は別途公式作成ガイドで 1,200文字・FAQ は最大10件とされる（本調査では Best Practices 原典で FAQ の存在と「よく聞かれる質問を入れる」ことまで確認。文字数の細部は作成ガイド側の数字として扱う）。
4. **パッケージは3段階が公式推奨。** 「少なくとも3つの異なる価格帯のパッケージを作る」「Gig Extras で追加サービスを有料化する」「Custom Offer で個別要件に応える」。価格設定では「自分の取り分は購入額の **80%**」であることを前提に、所要時間と市場平均を見て決める。評判が上がったら価格を上げることも公式に書かれている。
5. **ギャラリーは動画が効く。** 公式は “Gigs with videos perform better.” とし、高品質画像を必須、動画ショーリールを推奨。非ビジュアル系サービスでは Gig を説明する独自画像、文章系ではサンプル／レビューの PDF が公式の推奨。
6. **要件（Requirements）はテンプレート化して期待値を固定する。** 注文開始に必要なものを全て列挙する、が公式指示。
7. **プロフィールの真正性:** プロフィール写真、正確な職歴説明、学歴・スキルの記載、プロフェッショナルサイト欄の入力がモデレーション上の信頼材料になる、と公式は書く。コミュニケーションは Fiverr 内に留める、レビューを依頼しない、が公式ポリシー。
8. **公開後の編集コストに注意（推定ではなく運用上の注意として分離）:** 公開済み Gig のカテゴリは変更できない等の制約は作成ガイド側の仕様であり、Best Practices 原典の範囲外。公開前にタイトル／カテゴリ／タグを確定させることが実務上の帰結になるが、これは **自社の推論** として分離する。

### (2) 出典

- Fiverr 公式 Help Center「Gigs best practices」— タイトル（I will＋強い動詞＋最重要キーワード）、Search Tags、説明文の必須要素、FAQ、Requirements テンプレート、ギャラリーと動画、価格（取り分80%、3パッケージ、Extras、Custom Offer）、プロモーション手段: https://help.fiverr.com/hc/it/articles/360010949038-Consigli-e-trucchi-prima-di-creare-il-servizio
- Fiverr 公式 Help Center「Fiverr's search and recommendation system」— Relevancy が最重要、Historical appeal／Client satisfaction／レビュー／価格／Availability／Responsiveness、Fiverr's Choice／Pro／Ads の扱い、パーソナライズ: https://help.fiverr.com/hc/en-us/articles/23429542870161-Fiverr-s-search-and-recommendation-system
- Fiverr International Ltd. 公式発表「Fall 2025 Business Trends Index」（2025-12-10、GlobeNewswire 配信、Nasdaq 掲載）— faceless YouTube creator +488%、AI automation +136%、prompt engineering +76%、AI video creators +66% 等の検索伸び、Esti Levy-Dadon（GM, Fiverr Pro）および Fiverr 上の AI video creator Luigi Florente の発言: https://www.nasdaq.com/press-release/demand-ai-video-creators-surges-66-businesses-race-scale-marketing-campaigns-2025-12

### (3) 自社の現在地（実測事実）

- Gig はドラフトのまま未公開、Inbox 0。
- 門は本人確認（ID認証）＋W-9。

### (4) 従えていない点（ギャップ）

- **最大のギャップは「未公開」であり、最適化以前の段階である。** 公式 Best Practices は全て公開済み Gig の検索・成約を前提にしており、ドラフト状態では Relevancy も Historical appeal も発生しない。Inbox 0 は結果ではなく未公開の当然の帰結。
- **公開の門である ID認証＋W-9 は KYC のため実施不可。** 本ファイルではこの門を「努力で超える対象」として扱わない。Fiverr は現行の自社運用では **実施不可（KYC）** と明記して閉じるのが正しい現在地である。
- したがって、タイトル／タグ／3パッケージ／動画ギャラリー等の B層は「知識としては確定、しかし公開できないため未適用」ではなく「KYC 門により適用機会自体が無い」と正確に書くべき状態。Gig ドラフトの中身が公式型に沿っているかの照合は、公開見込みと切り離して行う価値は低い。

### (5) 次のアクション

1. Fiverr レーンは **KYC（ID認証＋W-9）のため実施不可** として台帳上で閉じ、以後のループで「Gig を公開せよ」という未達を繰り返し発生させない。
2. ドラフト Gig の題材（AI動画／自動化系は公式 Index 上の需要伸びと一致する）自体は、KYC 門のない他プラットフォーム（Guru／Freelancer.com 等）の Service／案件選定の参考としてのみ流用する。Fiverr 向けの追加制作はしない。
3. 万一、将来 KYC の扱い自体が会社方針で変わる場合に備え、本節の B層チェックリスト（タイトル型・タグ・3パッケージ・80%取り分前提の価格・動画ギャラリー・FAQ・Requirements）をそのまま再利用できる形で残す。

---

## Freelancer.com

### (1) 核

#### (A) 稼いでいる型

- **一次情報で言える型は「狭く絞った案件に、個別化した短い入札を、Milestone 分割つきで出す専門家型」である。** 公式 Support「Tips for winning projects」は、魔法の公式はないとしつつ、プロジェクト説明を熟読する、入札は明確・簡潔に、**Milestone を 3〜5個** 提案する、価格は「安さ」ではなく「競争力」で（最低価格が勝つとは限らない）、過剰に売り込まない、校正する、Portfolio の質は量より質、を挙げる。
- **競争密度の数字:** 「1プロジェクト平均41件の入札」「67%のプロジェクトが投稿後60秒以内に最初の入札を受ける」という数字は、Freelancer.com の自己公表データとして二次サイト（GigRadar）が引用しているもので、本調査では公式原典ページを直接開いて確認できていない。よって **二次情報・未確認** として分離する。ただし含意（人気案件は入札が速く・多く集まる）は公式の「Bid Insights で他者と比較せよ」という設計とも整合する。
- **金額分布の一次データは公式からは確認できなかった。** 手数料 10% を差し引いた実効単価で考えることだけが公式数字から言える。

#### (B) 一般ベストプラクティス — 数字つき

1. **入札枠は無料で月6件しかない。** 公式 Bidding FAQ: Free 6件/月、Basic 50、Plus 100、Professional 300、Premier 1,500。無料は **120時間に1件** のペースで補充される。つまり無料運用は「週1〜2件の厳選入札」が公式設計上の上限であり、数を打つ戦略は有料会員が前提。
2. **手数料は固定価格・時間制とも 10%（固定価格は最低 $5）。** $50未満の案件では最低 $5 が効いて実効手数料率が10%を超える（例: $20案件なら $5＝25%）。小額案件の選別に直結する数字。
3. **入札文の型（公式「How to write a winning bid」）:**
   - 雇用主を **名前で呼ぶ**（コピペでない証拠になる）。
   - 案件説明の **具体的詳細を自分の入札に含める**。
   - 自分のスキルがこの案件にどう関係するかを、類似実績と共に具体的に書く。
   - **現実的な納期** を明示する（過剰コミット禁止。例: “I can get this done in 48 hours.” のように具体化）。
   - 過去実績への **Portfolio リンク** を入れる。
   - 案件固有の **質問を1〜2個**、オープンエンドで聞く（説明を読めば分かる質問は失格）。
   - スペル・文法を校正する（誤りがある入札はスパムに見える）。
   - 共感を示す（雇用主の困りごとに寄り添う文を入れる）。
4. **やってはいけない型（公式が「スパムに見える」と明記）:** コピペの使い回し（“cardinal sin” と表現）、過度にフォーマルな “Dear sir/madam”、自分語りだけで案件に触れない入札、具体性のない一般論、写真のない／漫画アイコンのプロフィール。
5. **テンプレは「骨格」だけ作る。** 公式は、挨拶（名前）→案件の言い換え→使うスキル→案件への質問→チャットへの CTA、という骨格テンプレは推奨し、本文の使い回しとは区別する。
6. **Milestone Payment を入札時に提案する。** 公式 FAQ・Support ともに、金額・日数・提案文に加えて Milestone／タスクを列挙して Place Bid する手順を示す。受注後の支払確保の仕組みでもある。
7. **有料の可視化オプション:** Highlight は $1.00 の一回払い、Sponsored は順位を前面に出す、Sealed は他者に金額・文面を見せない。公式 Community 記事は「Sponsored／Highlighted は受注されやすい、特に新規に有効」とするが、効果の数値（何%上がるか）は公式には無い。数値なき断定はしない。
8. **入札前にプロフィール完成が必須。** 公式 FAQ は、プロフィール未完成（写真・サマリー・見出しなし）では入札できない場合がある、必要スキルの登録がないと入札できない、とする。

### (2) 出典

- Freelancer.com 公式 Community「How to write a winning bid」— 名前呼び、案件詳細の反映、スキルの具体化、現実的な納期、Portfolio リンク、質問1〜2個、校正、共感、コピペ禁止、骨格テンプレ、Sponsor／Seal／Highlight: https://www.freelancer.com/community/view-unpublished?id=75412
- Freelancer.com 公式 FAQ「Freelancers - Bidding」— 入札手順（金額・日数・提案文・Milestone）、入札は無料だが月次上限あり、Free 6／Basic 50／Plus 100／Professional 300／Premier 1,500、補充間隔（Free は120時間に1件）、入札できない理由（プロフィール未完成・スキル不一致・枠枯渇等）、Highlight $1.00: https://www.freelancer.com/faq/topic.php?id=5
- Freelancer.com 公式 Support「10 Tips for Writing an Effective Bid / Tips for winning projects」（freelancer.com.au Support）— 熟読、明確・簡潔、Milestone 3〜5個、競争力ある価格（最低価格ではない）、過剰に売り込まない、校正、Portfolio は質＞量 ※原典ページはクローラ上で本文が折り畳まれ、検索結果に表示された公式 Support の抜粋で内容を確認した。逐語引用は Community 記事と FAQ を正とする: https://www.freelancer.com.au/support/project/10-tips-for-writing-an-effective-bid

### (3) 自社の現在地（実測事実）

- 入札残数 0/6。
- 案件 40805503 への入札（₹1,500・7日）は有効で、20件中17位。
- 表示された自入札額が前回記録と食い違う件あり。

### (4) 従えていない点（ギャップ）

- **枠 0/6 の枯渇が全てを止めている。** 公式設計では無料枠は120時間に1件ずつ戻る。次にいつ1件戻るのかを台帳で管理していないと、「入札できない期間」が空白になる。量の不足は努力不足ではなく公式の枠設計そのものである、と正確に切り分ける必要がある。
- **順位 17/20 は、公式の型（名前呼び・案件固有の詳細・Milestone 3〜5個・質問・Portfolio リンク）を満たした入札だったのかの照合ができていない。** 順位が Bid Ranking の何で決まるのか（金額だけではないはず）を含め、入札文の現物と公式型の差分計測が未実施。
- **入札額の表示食い違いは未解決のデータ不整合。** ₹1,500 で記録した額と画面表示が違うなら、手数料表示・通貨換算・変更履歴のいずれかであり、放置すると次の入札の価格判断を誤る。原因の切り分けが次のアクションとして必須。
- **$5最低手数料の観点では、₹1,500（約$18規模 ※換算は推定）クラスの小額案件は実効手数料率が高くなる帯域である。** 公式数字（10% or $5 の大きい方）から言えるのはここまでで、通貨換算の精密な計算は **推定** として分離する。

### (5) 次のアクション

1. 入札枠の補充時刻（120時間サイクルの次回戻り）を台帳に記録し、枠が戻るたびに1件ずつ、公式型を満たす入札だけを出す運用に固定する。枠ゼロ期間に「入札ゼロ」を失敗として数えない台帳設計にする。
2. 案件 40805503 の入札文現物を取得し、公式チェックリスト（名前／案件詳細／類似実績／納期／Portfolio リンク／質問1〜2／Milestone／校正）で差分を数える。順位17/20 の主因を、価格か文面かプロフィールかで切り分ける。
3. 入札額の表示食い違いは、入札詳細画面・変更履歴・通貨表示を実読して原因を1つに特定してから台帳を訂正する。推測で上書きしない。
4. 次回入札の最低ラインとして「固定価格 $50 以上相当」を目安に置く（$5最低手数料で実効10%に収まる帯域）。これは公式手数料表からの **自社の計算** であり、公式の推奨ではないと明記して使う。

---

## Mercor

### (1) 核

#### (A) 稼いでいる型

- **Mercor 公式（Experts ページ）の自己公表数字:** 平均契約レート **$95/時**、専門家への支払総額 **$4M超/日**、専門家 **30,000人超**。この数字は Mercor 公式ページを 2026-10-29 に実読した第三者（The AI Receipts）が原典リンクつきで転記したもので、本調査では公式ページそのものを `browser.open` では開けていないため、**「公式自己公表・二次転記で確認」** と一段階弱く扱う。
- **Generalist の実勢レートは公式平均より大幅に低い。** AI訓練求人を Mercor 公式リスティングから集計する二次調査では、Generalist は **$40〜80/時**（RemoteFutur が公式 Help Center とリスティングを基に 2026-11-01 公開）、別の実読では Generalist リスティング **$50〜60/時・MacBook 所有が要件** とされる。これらは一次リスティングの集計という意味で参考になるが、Mercor 公式の統計ではないため **二次情報** として分離する。
- **型そのものは「資格・専門性で選ばれる専門家プール型」である。** Mercor 公式 Talent Docs と各リスティングの構造上、汎用提案型プラットフォーム（Guru／Freelancer 型）と違い、提案文の量では勝てない。履歴書（Resume）＋AIインタビュー＋アセスメントのスコアがプール内マッチングを決め、プロジェクト側から声がかかるのを待つ構造。Generalist はその中でも「学士レベルの専門性＋強い推論・文章」が前提とされる帯域であり、無資格の大量応募型ではない。

#### (B) 一般ベストプラクティス — 数字つき

1. **応募は「ステップを全て終えて初めて Submit」であり、ステップは使い回される。** 公式 Talent Docs: 完了したステップは全応募に同期し、永久に保持される。最新の Resume（PDF）・インタビュー・フォームが提出済み応募にも自動で表示される。逆に言えば、未完了のままでは何件応募しても前進しない。
2. **AIインタビューが唯一の選考方法。** 公式は “Our AI interview is the standard and only method for screening talent.” とし、人間・チャット・電話への代替は不可と明記。所要時間は **約20分**（案件により前後）。Role-specific な質問をし、文字起こしして評価する。
3. **リテイクは通算3回まで。** 公式: 同一インタビューに紐づく全応募を通じて **最大3回**。リテイクすると応募進捗がリセットされ、リテイク回数は Hiring Manager から見える。Waiting Room は「リテイクは技術的問題のために温存せよ」と求める。短すぎるインタビュー（“Interview too short”）は無効となりリテイクが必要で、それも回数を消費する。
4. **Practice Interview は無料・無制限・不影響。** 公式: 本番前に何度でも受けられ、将来の機会に影響しない。本番の3回枠を守るための公式の手段であり、使わない理由がない。
5. **本番環境の公式 Tips:** コンピュータ＋動作するカメラとマイクを事前テスト、顔全体が見えること、静かで邪魔の入らない環境、ヘッドホンと外部マイク推奨、英語（別指定がない限り）、字幕は既定 ON、画面共有が必要な場合は全画面のみ対応、長い沈黙は AI の割り込みを招くので簡潔に話す、詰まったら「まだ終わっていない」と伝える／繰り返しや言い換えを求める、ペンと紙（必要なら計算機）を用意する。一部インタビューは技術的に過去経験を深掘りし、他は言語・推論を測る。
6. **対応ブラウザ:** 推奨は最新 Chrome、対応は Edge／Safari、**Firefox は非対応**。一部インタビューは電話不可（コンピュータ必須）。
7. **AIツールの使用規則:** 文法・言い回しのチェックは可。LLM に回答を作成させる、モデル回答を評価させる、根拠・説明を生成させる、コードを評価させることは禁止（LLM Usage Policy）。インタビューの質問・スクリーンショットの共有も禁止。
8. **結果通知までの期間に公式の固定日数はない。** 公式は「次の段階に進んだら通知する。その間も他の募集中ロールに応募し続けてよい」とするのみ。2〜4週間という数字は二次ガイドの記述であり、公式数字としては扱わない（**二次情報**）。
9. **Resume の形式（二次ガイドが公式 Docs を基に集約）:** テキストベース PDF・1〜2ページ・2MB未満・標準見出し（Education／Experience／Skills／Certifications）・画像や表を使わない。Mercor の AI が Resume をパースしてマッチングとインタビュー質問生成に使うため、という理由づけは公式 Docs の構造と整合するが、形式の細部は **二次集約** として分離する。

### (2) 出典

- Mercor 公式 Talent Docs「AI Interview」— 約20分、1回完了すれば使い回し、Practice Interview（無料・不影響）、リテイク最大3回・進捗リセット・Hiring Manager に可視、環境 Tips（カメラ／マイク／顔全体／静かな環境／ヘッドホン推奨／英語／画面共有は全画面）、対応ブラウザ（Chrome 推奨、Firefox 非対応）、LLM 使用規則、AIインタビューが唯一の選考方法、Updated 2026-11-03: https://talent.docs.mercor.com/support/ai-interview
- Mercor 公式 Experts ページの自己公表数字（平均 $95/時、$4M超/日、30,000人超）を原典リンクつきで転記した調査記事 — The AI Receipts「How Much Does Mercor Make in 2026?」（Mercor experts ページを 2026-10-29 実読と明記）: https://theaireceipts.com/blog/how-much-does-mercor-make/
- RemoteFutur「Mercor Review: How to Get Hired & Earn Training AI」（2026-11-01、Mercor 公式 Help Center と公開ポリシーに基づくと明記）— Generalist $40〜80/時、Mac 所有が Generalist の適合条件の一つ、応募→AIインタビュー→プロジェクトの3ステップ: https://remotefutur.com/mercor-review/

### (3) 自社の現在地（実測事実）

- 契約 Odin は 2026-11-03 から一時停止（Paused）が継続、Earnings $0、Applications In progress 7件。
- Generalist 応募が5ステップ中3つ（60%）で停止したまま。
- Weekly Check-In は提出済み。

### (4) 従えていない点（ギャップ）

- **筆頭ギャップは「5ステップ中3つ（60%）で停止」であり、公式構造上これは未提出と等しい。** 公式は完了ステップの同期と「Ready to submit / Submitted」の状態管理を前提にしており、60%停止の7件はプール内で評価対象になっていない可能性が高い。件数（7件）ではなく完了率が公式の物差し。
- **残り2ステップの中身が現在地に明記されていない。** それが AIインタビューなのか、アセスメントなのか、ID／支払設定なのかで打ち手が全く違う。特に本番 AIインタビューは「顔全体が見えるカメラ必須＋録画」であり、自社運用（AIエージェント完結）では **そのままでは実施できない可能性** がある。安易に「残りをやればよい」とは書かない。中身の実読が先。
- **プロジェクト参加後の ID Verification（Persona による政府ID＋セルフィー動画）は KYC のため実施不可。** 二次ガイド・公式フローともに、オファー後の ID 確認と背景確認が契約開始の条件として現れる。ここに到達しても自社だけでは完結しない門であることを、応募を進める前に台帳へ明記しておく必要がある。
- **Odin の Paused は自社の行動では解けない側の停止。** Weekly Check-In 提出済みという「やるべき応答はした」状態であり、Paused の間は新規の稼働は発生しない。公式にも「通知が来たら次段階」という受動構造が明記されている。Paused を自社の未達として数え続けるのは物差しの誤りであり、「Paused 継続中・自社側の滞留は Generalist 60% の方」と分けて記録すべき。
- **Practice Interview を使った形跡が現在地に無い。** 本番3回枠という有限資源を使う前に、無料・無制限・不影響の練習で環境（Chrome／カメラ／マイク／沈黙の扱い）を検証するのが公式の想定手順であり、未使用は手順の欠落。

### (5) 次のアクション

1. Generalist 応募の残り2ステップを、応募画面のステップ一覧を実読して特定し、台帳に「ステップ名・所要・KYC／顔出しカメラの要否」を1件ずつ書く。特定前に「あと2つ」という曖昧な状態で止めない。
2. 残ステップが AIインタビュー本番である場合は、まず Practice Interview で環境検証だけを行い、本番の3回枠は消費しない判断を台帳に残す。顔出し録画が必須であることが確定したら、その Generalist 経路は「エージェント完結不可」として理由つきで区別する。
3. 残ステップに ID Verification（Persona）が含まれる場合は **実施不可（KYC）** と明記してその応募を閉じ、KYC 不要で完結するステップのみが残る応募（7件のうち該当するもの）へ注力を移す。
4. Odin については、Paused の解除条件・通知の有無を週次で確認するだけに留め、確認した日時と状態（Paused 継続／解除）を台帳に1行で記録する。Earnings $0 は Paused の結果として記録し、自社の提案量の問題と混ぜない。

---

## 横断まとめ（5プラットフォーム共通の公式原則）

1. **量は「枠の設計」で決まる。** Guru 無料10件/月、Freelancer.com 無料6件/月（120時間に1件補充）という公式枠がある以上、「もっと打て」は枠の外の精神論であり、正しくは「枠の中で最も適合する案件に、公式型の文面で打つ」こと。枠を増やす有料化は支出判断であり、本調査の範囲外。
2. **全プラットフォームで公式が否定するのは「定型文の使い回し」。** Guru は詳細 Quote、GoLance は boilerplate の否定と300語未満の個別化、Freelancer.com はコピペを “cardinal sin” と表現、Fiverr は Relevancy（検索語との一致）、Mercor は Resume ベースの個別質問。名前で呼ぶ・案件固有の詳細を入れる・関連実績を1つ示す・質問を入れる、が4プラットフォーム（Mercor 除く入札型）で共通する型。
3. **プロフィールの完成が応募に先行する。** GoLance 80%の門、Freelancer.com のプロフィール未完成時の入札不可、Guru の keyword-rich な Service／Portfolio、Fiverr のプロフィール真正性。未完成のまま応募数を数えるのは全プラットフォームで公式に反する。
4. **フォローアップは公式の手順に含まれる。** Guru は24時間、GoLance は3〜5日。送信して終わりの運用は両プラットフォームで公式から外れている。
5. **KYC 門の棚卸し（実施不可の明記）:**
   - Fiverr: ID認証＋W-9 → **実施不可**。レーン自体を閉じる。
   - GoLance: スキル評価 `es5ae5wayr`（Webカメラ必須）→ **実施不可**。Tax Form は中身の実読後に判定。
   - Mercor: オファー後の Persona ID Verification → **実施不可**。AIインタビュー本番の顔出し録画は、ステップ実読後に「エージェント完結可否」を別途判定する。
   - Guru: All-Time Transaction Data が無い間の代替表示である ID Verification → **実施不可**（代替表示なしで Quote の質で勝負する）。
   - Freelancer.com: 本調査の範囲では、通常入札に KYC が必須である旨は公式 FAQ では確認できなかった。入札時に別途本人確認が求められる案件があれば、その案件単位で実施不可とする。

## 調査の限界

- Fiverr の Spring 2025 Index（AI Agent +18,347%）と Freelancer.com の平均41入札／60秒以内67% という数字は、二次引用でのみ確認でき、原典を直接開けていないため本ファイルでは根拠として使っていない。
- GoLance Blog の提案論は AMP 抜粋での確認であり、逐語引用は避け要旨のみを採用した。
- Mercor 公式 Experts ページの $95/時・$4M/日は、公式ページを実読した第三者の転記で確認したもので、公式ページ自体の直接確認ではない。
- 売り手の収入分布（中央値等）は、いずれのプラットフォームでも公式の一次データが無く、第三者推計しか存在しないため、本ファイルでは採用していない。必要であれば「推定」と明示した別調査とする。

---

# ギャップ総表（従えていない点の一覧）

各節の (4) の要約。詳細と出典は各プラットフォームの節を参照。担当は適用側のループ／Todo。

## 配信

| 面 | 主なギャップ | 次のアクション（担当） |
|---|---|---|
| LinkedIn | 本日追加分はテキスト投稿で引用カード主形式が未適用。エンゲージメント行動は本人確認要求のため実施不可 | 引用カード主形式化を次回ループから適用（distribution 系） |
| Instagram | 判定指標が量に寄り、公式上位シグナル（watch time／likes per reach／sends per reach）を投稿別に取得・記録していない。差分ゼロ確認 0/44件のまま主エンジン2面が約-30%。量は実測の効率帯の約4倍で、ボトルネックは量ではない | 投稿前チェックへ3指標の取得行を追加。勝者投稿と並べた差分検証を面ごとに再実施（配信ループ／copy100監査） |
| TikTok | 全枠コメント0件（公式「会話を spark する」が未実装）。固定勝者6系統の現在の頻度・減速有無が未実測。無料経路移行は 13面中1面のみ実証（期限 2026-11-25）。Creator Rewards／TikTok Shop は KYC で実施不可 | 判定を p90 再生＋コメント発生率へ。勝者A層の棚卸しを1回実施。無料経路を残り12面で順次実証（配信ループ／項目4） |
| YouTube Shorts | 公式の物差し（% chose to view／平均視聴時間・視聴率／満足度）で見ていない。公開済み Shorts は監査で全本「100%コピーでない」。アップロード経路が Studio 本人確認ダイアログと Postiz クオータで詰まっている | 経路の再確立（OSS アップロード自動化等の他者の方法を適用）。公式3指標での検証へ切替（項目34／監査Q22） |
| YouTube 長編 | 勝者（Improvement Pill 等）の現在の頻度・平均尺が未実測。YPP／AdSense の本人確認・税務確認は実施不可（KYC） | 勝者A層の実測を先に実施（X探索／配信レーン） |
| Threads | 勝者 @thriveanxietysolutions の現在の頻度・返信量・形式が未実測（A層が最も薄い）。投稿時刻は Meta 公式と Buffer 実測が正面衝突し未決着。Threads Ads は Gate 0 未通 | 勝者の実測を先に実施し、時刻は自社実測で決める。Ads は Gate 0 の判定を先に済ませる |
| note | 勝者の核であるメンバーシップ販売が、個人情報登録の門のため開始できない（実施不可・エージェント側）。「外部SNSで知ってもらってから送客」の導線が未構築 | 門は門として記録し続ける。外部導線（自社SNS→note）は門なしで作れる範囲で構築（記事ループ） |
| Substack | 公開記事0本・サインイン詰まりで未着地。前提の訂正: 勝者 Not Boring は有料購読単体ではなく Freemium（無料リスト主軸＋スポンサー＋有料ティア） | サインイン経路の回復→初回記事。型は Freemium で組み直す（記事ループ） |
| Medium | 勝者 Benjamin Hardy は現在の主軸が書籍・事業側で Medium の現行ペース未確認（勝者固定の鮮度ギャップ）。Medium 公式 AI ポリシーにより AI 生成文は paywall 不可＝自社の前提と構造的に衝突する領域がある。自社の現在地は未計測 | 勝者の現行実測と自社アカウント状態の確認から。paywall 前提の設計はしない（記事ループ） |
| SEO・GEO | GEO の第三者言及がほぼゼロ（AlternativeTo 審査待ち、働きかけ4件は返信0）。サブスク名の表記不一致が「複数面の一致」を崩している。ホームページのエンティティ希薄化。旗艦ラウンドアップの一次データ化が未完 | 項目40 を主線に継続（返信追跡・対象追加）。3面の表記一致を先に直す。正本§4の作業順で進める（SEO/AIOループ／項目40・23） |
| App Store（ASO） | US は全語圏外、JP「アファメーション」は 32〜111位を往復。1.9.8 却下でメタデータ改訂自体が停止。プロモーション文が注意文で埋まり、審査なしで即日変更できるのに未使用。サブスク名の表記不一致 | プロモ文だけ先に勝者型へ即日組み替え。メタデータ確定案は次回提出へ適用し28日ルールで判定。表記一致は GEO と同一作業（項目16・39） |

## 販売・受託

| 面 | 主なギャップ | 次のアクション（担当） |
|---|---|---|
| Capafy | 価格アンカー等の自社差分14件が残る。JD Writer に「Who it's for」節なし。審査中26件の滞留 | 審査結果の確認と通過後の価格・表記再確認。新規エージェント最低1本/サイクルの出荷継続（Capafyループ／項目5） |
| Apify | 階層価格が未適用（一律 $1.50 で最大層から勝者の37.5%）。exampleRunInput が壊れたまま。入力フォームの並び・probeUrls 公開・フィルタ未実装 | 仕様書の完成稿を Console へ適用中。アドオンは A1→A5 の順に実装（Apifyレーン／項目6） |
| PromptBase | pending 上限で新規提出がブロック中。勝者の主力価格帯 $9.99 に対し自社の Live は $5.99。売上・レビュー 0 | 審査完了で枠が空き次第 Penguin を再提出。価格帯を勝者型へ寄せる（項目7） |
| Whop | Payouts の本人確認は実施不可（KYC）。税務バナー（期限 2026-11-30）の本人情報が必要な範囲も実施不可。売上・レビュー 0 | KYC 門は触らない。販売ページ型（headline→benefits→社会的証明）と Discover 露出の範囲で改善（Whopループ） |
| RenderHub | 売上・レビュー 0、Views 34 と露出自体が極小。支払い方法未設定。License Type のサイト側バグが未解消（サポート返信待ち）。公式 Tier 区分は前提と相違（T2 51–100／T3 101–200／T4 201+ が公式） | 公式「Sell Like a Pro」型（タイトル・タグ16・サムネイル・動画）で9品を照合。サポート返信の追跡（RenderHubループ） |
| Legiit | 公式タイトル公式（Primary Keyword＋Deliverable＋Differentiator、50文字上限）で自社2件を照合していない。売上・レビュー 0 | タイトルと Conversion Checklist 11項目で2件を照合（Legiitループ。再問い合わせ禁止 〜2026-11-08 18:29 JST が前提） |
| CrowdWorks | 提案811件に対し契約10件・合計税込371円（平均37.1円/件）と極小契約へ集中。固定勝者が未選定。クライアント選別基準（評価・完了率）とプロフィール冒頭5行の照合記録なし | 勝者選定と選別基準の適用を先に。提案総数の実件数照合も併せて実施（CrowdWorksループ） |
| ランサーズ | 24時間以内返信率 71% が公式の物差し 80% に -9pt（3面で最も具体的な是正点）。受注2件なのに報酬記録 ¥0。提案数 541 vs 525 の食い違い。勝者 oku305 の核である検証可能な数字の裏付けが自社プロフィールにない | 返信速度を最優先で 80% 以上へ。数字の食い違いの解消。実績数字が付いたらプロフィールへ反映（ランサーズループ） |
| ココナラ | 公式の主従（出品が主・募集応募は番外編）と逆に、活動の中心が応募件数になっている。出品側の核指標（直近3ヶ月販売額・納品完了率・評価）が台帳にない。売上の二重帳簿（¥5,000 vs ¥3,900）、勝者コピー元の個別出品URL未記録で差分検証不能 | 出品側の核指標を台帳化し、出品磨きを主へ。勝者コピー元URLの記録を必須化（ココナラアシストループ） |
| Contra | Earned $0、30日閲覧3 と露出が極小。最新コミュニティ投稿の日本語混在（英語化が進行中） | 英語化の着地確認後、DigiNo 型の価格段階と Nikol Hayes 型プロフィールへの差分を詰める（Contraループ） |
| Upwork | 収益・レビュー等の自社差分7件（勝者 $500K+／レビュー88件に対し自社 0）。勝者の時給・コンサル価格と自社プロフィール本文が未実測 | 招待案件の期限対応が最優先。その後プロフィール本文の実読と差分適用（Upworkレーン／項目33） |
| Guru | 無料ビッドが残3件と枯渇気味。公式 Tip の24時間フォローアップを実施した記録がなく、提案7件が無反応で放置。累計取引実績ゼロが構造的弱み。ID Verification は実施不可（KYC） | 既存7件へ24時間フォローアップ型の再接触を検討し、残ビッドの配分を決める。Service／Portfolio の keyword-rich 照合（Guruループ） |
| GoLance | **プロフィール完成度 70% が公式の表示・提案の門 80% の手前**（筆頭ギャップ）。時給案件9件が動画ゲートで全て送信中止。提案の型（300語未満・個別化・サンプル1点・3〜5日フォローアップ）を既存10件へ適用した証跡なし。スキル評価の Webカメラ必須は実施不可 | 完成度を 80% へ（Tax Form は中身を実読してから可否判断）。動画なしで提案できる案件種別へ寄せる（GoLanceループ） |
| Fiverr | Gig がドラフト未公開で、公開の門（ID認証＋W-9）が KYC のため実施不可。レーンとして閉じるのが正しい現在地 | 実施不可として記録し、工数を他面へ回す（判断は台帳へ明記） |
| Freelancer.com | 入札枠 0/6 で枯渇し、補充タイミングを台帳管理していない。入札文と公式の winning bid 型との差分計測が未実施。入札額の表示食い違いが未解決 | 補充の時刻管理を開始。次回入札は公式型で組み、入札額の不整合の原因を切り分ける（海外受託ループ） |
| Mercor | Generalist 応募が 60% で停止＝公式構造上は未提出と等しい。残り2ステップの中身が未特定（カメラ必須の AI インタビューや Persona の政府ID確認が含まれれば実施不可）。Practice Interview 未使用。Odin の Paused はプラットフォーム側の停止で自社の未達ではない | 残りステップの中身の実読を先に行い、実施可否を台帳へ明記してから進める（Mercorループ） |

## 横断の結論

- 配信側の共通ボトルネックは「量」ではなく「勝者との差分」と「公式シグナル（watch time／sends／コメント発生）で見ていないこと」。量は既に実測の効率帯を上回っている面が多い。
- 販売・受託側の共通ボトルネックは「最初の1件の売上と最初のレビュー」。4つのマーケットプレイスと受託面の大半が売上$0・レビュー0で、公式の順位要因（販売実績・レビュー）が構造的に発生していない。
- KYC の門で閉じている面・機能: Fiverr（公開自体）、Whop Payouts、note メンバーシップ登録、YouTube YPP/AdSense、TikTok Creator Rewards／Shop、Guru ID Verification、Mercor の Persona 確認。これらは「努力で超える対象」として扱わず、門の外側で取れる手を全て取る。
- 勝者の減速を実測できた面: LinkedIn（Welsh 7.5本/週 ← 成長期2本/日）、Medium（Hardy は主軸が書籍・事業へ移行）。量と型の目標は勝者の現在値ではなく成長期の型に置く、を全プラットフォームの原則として確認した。
