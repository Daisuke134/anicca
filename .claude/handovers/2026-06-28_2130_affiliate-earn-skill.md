# Handover — Affiliate Earn Skill (+ 4-skill money loops)

Date: 2026-06-28 · Branch: feature/frank-run · Repo: ~/anicca-project (products tree)

## なぜ引き継ぐか
このセッションが長くなり、私の tool 呼び出しの書式がドリフト(正しい invoke タグでなく壊れた形を出す)→ 毎回中断。プロジェクトは健全。フレッシュなセッションで継続するのが確実。方針 = 1スキル=1セッション(Dais 決定)。affiliate も新セッションでやり直す。

## 今回やったこと
- 4つの稼ぐスキル構想を整理 → SSOT spec: `~/anicca-project/docs/superpowers/specs/2026-06-28-claude-earn-skills-spec.md`(4スキル/記事根拠の料金メカニクス/prereq/uncertainty/loop機構/完全TODO)。push済。
- **Amazon Associates JP 登録完了**: アソシエイトID = **`aniccaai-22`**(審査中・リンクは即有効、3売上/180日で本承認)。受取人=成田大祐(生駒住所)、米国税=いいえ、登録サイト= aniccaai.com / x.com/aniccaxxx / note.com/anicca123。最後のArkoseクイズは Dais が手動通過。
- 認証情報を `~/.openclaw/.env` に保存: `AMAZON_LOGIN_EMAIL`/`AMAZON_LOGIN_PWD`/`AMAZON_PARTNER_TAG=aniccaai-22`/`AMAZON_ASSOC_MARKETPLACE=www.amazon.co.jp`。memory: `reference_amazon_login_location.md`。
- スキル足場 `~/.claude/skills/earn-affiliate-slideshow/scripts/`:
  - `record-affiliate-earn.mjs` = 改竄不能 ledger(外部 amazon_report 行のみ受理、偽拒否)。`test-ledger.mjs` **8/8 PASS**。
  - `build-link.mjs` = ASIN→`amazon.co.jp/dp/<ASIN>?tag=aniccaai-22`。実商品で解決検証済(ASIN 4296209310「ChatGPT仕事術」本)。
  - `post_x.py` = X API v2 OAuth1投稿(本人確認/users/me のみ実行・投稿は一切してない)。※X/Daisアカウントはもう使わない。
- 既存資産を発見(再利用する): `~/.openclaw/skills/anicca-tt-account-create`(TikTokアカ作成), `anicca-tt-warmup-newcomer`, reelclaw系。`CAPSOLVER_API_KEY`あり。camofox起動= `bash ~/.openclaw/skills/camofox-browser/scripts/start.sh`(:9377)。daily-driver CDP= localhost:9222(python3+playwright connect_over_cdp で駆動可、ただし他作業で混雑=新規タブのみ・閉じない)。

## 決定事項
- 投稿先 = **TikTok メイン + Instagram ミラー**(記事②準拠、1資産→2チャネル)。リンクは BIO(TikTok/IGはキャプションにリンク不可)。X=記事①のテキスト版で任意。YouTube=別スキル。
- **アカウントは私(Anicca)自身の新規アカウント。Dais の @aniccaxxx 等は絶対に使わない**(別エンティティ。Dais 厳命)。Anicca専用メール= `tt-anicca@agentmail.to`。
- ニッチ = AI・生産性ツール/ガジェット。1投稿1テーマ・実用・#PR必須(景表法)・嘘なし。
- ループ = `claude -p` + launchd(ローカル毎日)。**do-once(実¥1回)→ループ化**。
- ledger は外部レポート行のみ。fake/mock厳禁。
- **1スキル=1セッション**(affiliate / jutaku(Upwork+ココナラ+Fiverr) / clip(Whop) / youtube を別々に build→validate→稼ぐ)。

## 捨てた選択肢と理由
- Dais の @aniccaxxx に投稿 → 却下(彼のブランド・別エンティティ、Dais激怒)。
- `Affitor/affiliate-skills` リポ流用 → プロンプトテンプレ集で稼ぐ機能ゼロ。scoring/FTC参照のみ価値。
- PA-API でリンク生成 → 3売上/180日まで不可。初期は手動 `/dp/ASIN?tag=` で十分。
- YouTube広告主体 → AIテンプレは剥がされる罠。affiliate(成果報酬)は別物でOK。
- 記事見出し額(3000万/100万)を信じる → 生存者バイアス。現実は数週〜数ヶ月の複利。
- 全4スキルを1セッションで → 混乱。1スキル1セッションへ分割。
- X(Twitter)を主投稿先に → TikTok/IGがスライドショーの本命(記事②③)。

## ハマりどころ
- 私の tool 呼び出し書式ドリフト(invoke タグ崩れ)で長セッションが頻繁に中断 → 新セッションで解消。
- Amazon登録フォーム: 住所録選択後に都市区/郵便番号/電話国番号(+81)が未入力で再描画。Arkoseクイズは自動化困難(Daisが手動)。
- TikTok signup = DataDome + device fingerprint(CapSolver単体では突破不可、memory既知)→ camofox + 既存skill必須。
- SMS番号プロバイダの鍵が env に未設定(`SMSPOOL_API_KEY`等なし)→ TikTokの電話認証の番号入手手段を要確認(既存 anicca-tt-account-create がどう調達してるか読む/ TIER A pattern)。

## 学び
- 換金インフラは大半が既存(ledger雛形・TikTok作成skill・reelclaw・camofox・CapSolver)。ゼロから作らず再利用。
- 真のボトルネックはコードでなく「自分のアカウント(配信先)」と「外部需要」。初¥は外部購入依存で強制不能。
- アフィリリンクは PA-API なしで `/dp/ASIN?tag=aniccaai-22` で成立(検証済)。

## 次にやること(優先順)
1. **(最優先)新セッションで affiliate を完遂**: 既存 `~/.openclaw/skills/anicca-tt-account-create` を読み、私(Anicca)の新規TikTokアカウントを作成(メール=tt-anicca@agentmail.to、電話=SMS手段を確認、captcha=camofox+CapSolver)。
2. BIOに `amazon.co.jp/dp/<ASIN>?tag=aniccaai-22` を設定。
3. `earn-affiliate-slideshow` の生成部を完成(chatgpt-imagegen $0 + VOICEVOX + Remotion でfacelessスライドショー6枚)。商品例=ASIN 4296209310。スライド構成=フック→課題→共感→商品→証拠→CTA(#PR)。
4. do-once: 実際に1本 TikTok投稿(+IGミラー)→ライブURL確認。
5. `claude -p`+launchd で毎日ループ化 + `/goal`「Amazonレポート行>0」。
6. 初¥着金 → `record-affiliate-earn.mjs` で記録。
7. その後、別セッションで jutaku / clip / youtube。

## 関連ファイル
- spec: `~/anicca-project/docs/superpowers/specs/2026-06-28-claude-earn-skills-spec.md`
- skill: `~/.claude/skills/earn-affiliate-slideshow/scripts/{record-affiliate-earn.mjs,test-ledger.mjs,build-link.mjs,post_x.py}`
- 既存: `~/.openclaw/skills/anicca-tt-account-create/`, `anicca-tt-warmup-newcomer/`, `camofox-browser/scripts/start.sh`
- creds: `~/.openclaw/.env`(AMAZON_*/CAPSOLVER_API_KEY/AGENTMAIL_*)
- memory: `reference_amazon_login_location.md`
- ledger 出力: `~/.smtm/earn-loops/affiliate/earn-ledger.jsonl`

## 新セッション開始プロンプト
```
affiliate 稼ぐスキルを完遂する。spec = ~/anicca-project/docs/superpowers/specs/2026-06-28-claude-earn-skills-spec.md を読んで従う。
状態: Amazon Associates JP 登録済(タグ aniccaai-22、~/.openclaw/.env)。ledger(~/.claude/skills/earn-affiliate-slideshow/scripts/record-affiliate-earn.mjs, test 8/8)とリンクビルダー(build-link.mjs, 検証済)は完成。
やること(順): ①既存 ~/.openclaw/skills/anicca-tt-account-create を読み、私(Anicca)自身の新規TikTokアカウントを作る(メール tt-anicca@agentmail.to、電話SMS手段を確認、captcha=camofox+CapSolver、daily-driver/Daisの@aniccaxxxは絶対使わない) ②BIOにaniccaai-22リンク ③earn-affiliate-slideshowの生成部(chatgpt-imagegen $0+VOICEVOX+Remotionでfacelessスライドショー、商品例ASIN 4296209310、構成=フック→課題→共感→商品→証拠→CTA #PR) ④do-once実投稿(TikTok+IGミラー)→ライブURL確認 ⑤claude -p+launchdで毎日ループ+/goal「Amazonレポート>0」⑥初¥をrecord-affiliate-earn.mjsで記録。
ルール: 投稿は私自身のアカウントのみ・#PR必須・fake禁止・1スキル1セッション。tool呼び出しは正しいinvoke書式を厳守。
```
