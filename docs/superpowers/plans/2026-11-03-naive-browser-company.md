# Naïve browser company Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans。primaryが単独実装し、最後にfresh read-only reviewを使う。

**Goal:** Naïve自身のbrowserをLLMが操作して既存の会社業務を完走する。
**Architecture:** 標準pi agentの外部操作はbrowser、本人専用のemail.inboxes/read/send、指定Postiz4tools、Computer read/writeは作業メモと成果物に使い、判断は自然言語promptへ置く。APIは基盤設定/実行/証拠読取に限定する。
**Tech Stack:** Naïve標準agent/session/browser、JSON設定。追加依存なし。
**Spec:** docs/superpowers/specs/2026-09-25-life-manager-unified-ssot.md の Naïve browser company 節。

## Global Constraints
- 既存owner・共有profile・既存6agent/cronを変更しない。
- 専用cap月6USD/max_task1USD、既存残高内・追加入金なし。
- 秘密値はSSOTとproviderの専用credential経路のみ。modelへ値を送らない。
- business script/APIはagentへ与えない。scopeはbrowserによる画面操作、本人専用メール3機能、指定Xの新規campaign向けPostiz4tools。通常の登録・認証・商品作成・公開・顧客対応は人間承認なしで実行する。

## Review Focus
- deny defaultでもask-default toolが残るため既知の追加能力を明示disableする。
- config/終了文だけを成功にせずbrowser tool eventと遷移後の画面を確認する。
- agent/session/Computerの所有者と保存状態を区別する。
- 応答消失時は同じ外部操作を繰り返さず状態を読む。
- 認証と共有writerの未照合は具体的な不足境界として残す。

## Tasks
- [x] BROWSER01: config/naive-browser-company.jsonと正本specを作成、JSON/権限/予算assert・fresh review・push/CI/main統合。
- [x] BROWSER02: merged mainの固定revisionから専用agentを適用。公式readback後に有限sessionを起動し、browserの観測/click/type結果と実費を取得。
- [ ] BROWSER03: 既存credential/本人担当の回答を照合。loginの前に専用identityを確定し、browserが閉じたComputerから空contextを作り、agent id限定grantを設定する。context_nameとpersist_context:trueの新versionをmainから適用し、同identityでsessionを開始してprovider専用login経路で認証する。一業務の実画面結果を公式readback。
- [ ] BROWSER04: 同担当の保存/再開を確認し、対象のwriterを重複させずhosted継続運転へ接続。

## Decisions and evidence
- Daisは質問なしで最後までの実行を指示しているため、skillの対話/再承認要求は実行停止にしない。
- Astra専用経路は親model/effortを観測できず、指定旧modelは現toolに無い。UI選択を変更せず通常の単独実装とread-only reviewを使う。
- source acceptanceは最小JSON/schema/権限assertとprovider readback。固定JSONの写経テストや新しいagent loopは作らない。

- Review修正: 公式ask-default既知16toolを明示disable/denyし、login前の空context/identity/grant準備をBROWSER03へ移す。初回BROWSER02は未認証の画面操作だけなのでcontext_name無しの定義を使う。

- 実測修復: 画像返却直後のvalidation_failed、画像無し試行のsession cap停止を別の失敗として保持。月cap維持でmax_taskを0.50へ変更し、Computerのread/writeによる作業メモを追加する。外部操作はbrowserのみ、shell/APIは引き続きdeny。

空の保存context `anicca-browser-capafy` を専用Identityで作成し、担当agentだけへgrantした。認証前の準備を確認。設定のcontext_name/persist_contextを有効化し、統合後のversionでログインを進める。bootstrap sessionは正常終了、消費4941 microUSD。

画像診断の比較: Gemini 2.5 Flash Liteへのsession overrideではgoto→screenshot→画像内容の返答まで正常終了。追加実費2491 microUSD。専用担当のmodelと画像観測promptをこの実測に合わせて更新する。GLM全般の非対応や性能順位には一般化しない。

BROWSER02実測完了: PR9111 main90c48ca1、hosted agent v2のmodel/権限/contextを公式readback。Geminiの画像後の返答とactによる実検索、結果30件と3商品の表示を確認。単独click/typeのxpath失敗は残し、act経路をsourceへ反映。BROWSER03は認証を修復中。Computer割当と相対パスメモのwrite/次ターンreadは成功、別sessionでの保存再開は未確認。

BROWSER03診断: login doneとログイン済み画面は別。agentの誤報を訂正、メモ修正を依頼。credentialのservice/host完全一致を修復し、自己作成した誤host資格情報は削除した。source promptに現在host照合とform残存時の未完判定を追加。別sessionで保存メモと認証を検証中。PR9111の15checkは全PASS。

旧Google経路の診断時点ではcursorはBROWSER03のGoogle OAuth provider境界だった。v3をmerged main265bab69から適用、GET完全一致。BROWSER04のうち同Computer/別sessionメモ再読取は成功、自然idleでpaused。認証、一業務、売上、native deploymentは未完。405957 microUSDは専用agentの公式spend集計。次の順序と不足する外部経路は正本specの残TODO節に記載。raw資格情報や署名URLはrepoへ保存しない。

## 本人mail・人間承認なしの実行
- [x] MAIL01: system domainと専用inboxを用意し、公式readbackとprivate SSOTへ保存。
- [x] MAIL02: signupのaskを除去、本人email toolsをallow、通常業務を人間承認待ちにしないpromptをmainへ統合して適用。
- [ ] MAIL03: 本人mailでCapafyへブラウザ登録、認証メールを処理し本人画面を確認。
- [ ] MAIL04: 新規所有商品をブラウザで作成/公開し、受取設定と実収支の境界を確認。
- [ ] MAIL05: 標準deploymentと本人inbox wakeを接続し自然実行を確認。
旧Google経路への固定を外す。順序/費用枠と残TODOの正本は統合SSOT。各操作は画面を見てモデルが判断し、業務scriptを作らない。

本人mail・設定の実反映: 標準system domainの作成直後はpendingだったが、公開MXを確認して再verifyするとactive/dns provisioned/inbound verifiedへ遷移。専用inbox activeを公式GET照合し、参照をprivate Credential SSOTへ保存した。個人Googleの専用vault複製だけを削除して不在をGET確認。PR9116はmain95aee29fccf1bc6ae920465dca0eba009d47bc98へ統合、固定sourceからv4を適用しsystem/tools/budget/metadataを完全一致readback。本人mail登録ジョブをv4/同Identity/contextで起動しrunning、read→browser goto/observeの実tool eventを確認。MAIL03の登録/認証とMAIL04の公開/売上は未確認。

MAIL03実行診断: v4の初回jobは既知のxpath click失敗を繰り返し、存在しないgoto toolを呼んでidleになった。承認要求やmail不足ではない。primary AIから既に成功済みのbrowser(action=act,instruction=...)とbrowser.linksの実形式を伝えて同sessionを再開。続くemail.inboxesは成功、browser gotoは最初の入力エラーから次callで成功した。登録/認証済み本人画面は未確認。primary AIの修正を含むため、無介入ベンチマーク成功とは扱わない。

継続診断: 軽量modelは最後のgoto後の未観測画面を登録不能と誤判定したため、公式catalogで存在を確認したgoogle/gemini-2.5-flashへsession overrideしGETのmodel一致を確認。既定agent v4のmodelは変更しない。実observeはWelcome to Capafy/Continue with Emailボタンを返し、登録導線なしという旧判断を棄却。次turnのact前にgotoがなくobserveが空だったため、ブラウザのturn毎closeに合わせて再open→観測→操作へ修正を送信。登録/認証/公開/売上は引き続き未確認。PR9116のCIは後続確認で全15check PASS。

## Manager継続運転
- [x] v5をmain7d702ce7から適用し完全一致readback。
- [x] 専用receiving-only Base EOAの鍵をCredential SSOTへ保存し、offline署名/復元とmainnet chain8453/native USDC6桁/初期0残高を確認。Naïve native walletはorg mainnet無効403のため未作成。支出signer・入金・送金は未実施。
- [ ] v6のSonnet4.6/max_task0.75USD/月2USD・view_image・指定Postiz4toolsをsource/mainへ統合して適用。
- [ ] 専用vaultにPostiz bearerをagent限定封入し、指定channelのnative MCP readbackを確認。封入とagent/url一致GETは完了、runtime呼出は未完。
- [ ] 実イベントだけの英語sample/offer修正・本人mailのself-send/read・payment-receiver.jsonの実write/read。
- [ ] 固定v6/同IdentityのNaïve標準deploymentを接続し、自然実行/本人inbox wakeを確認。
- [ ] 英語offer/実画面demoを指定Xとblogへ公開し、実顧客の決済/納品/実費を公式照合。
Sonnet比較はmodel設定受理だけでは実行済みにしない。初回は予約枠でbudget.exceededし実model spanはHaikuのみだった。Capafy個人Googleを必須にせず、既存owner/許諾は照合中。本文の過去cap/モデルは当時の実測であり、現在設定は本節とGlobal Constraintsを正本にする。

MCP実catalog診断: 公式紹介文のschedulePostToolと異なり、認証済み標準MCPのtools/listはintegrationSchedulePostToolを返す。source allowlistは実catalog名へ修正する。これはtools/listの能力確認であり、Naïve内での接続/投稿成功ではない。

## v6実行後の修復cursor
- [x] PR9124統合/main固定v6適用・全15CI PASS・専用Postiz vault封入・標準12h deployment登録。
- [x] native Postiz integrationList/postsListTool/integrationSchemaをHaiku overrideで実行。Sonnetはagent月cap見積拒否、実推論なし。
- [x] 事実限定offer/sample/public受取先をnative write/readで照合。mail self-send acceptedだがinbound未確認。Hashnodeは未解決verification checkで有限probeをcancel、成果物は保持。
- [ ] 現在cursor: 既定Haikuのv7をmain適用し既存deploymentをv7へ更新、手動実行後に自然runを確認。月2USD/task0.75USDを維持し、Sonnet必要枠を測定せず増額しない。
- [ ] 独立した通常メール送信元または実サイトの認証mail dispatchから本人inboundを確認し、wakeを有効化。共有production mailboxの借用/変更はしない。
- [ ] 投稿本文/実画面素材の検証後に英語offerと記事を公開、実第三者の受注/納品/決済/純収支を確認。
Ruling: v6のSonnetは予約見積で実行できず、実成功したHaikuへ既定を戻す。費用capを維持し継続運転を動かすため。誤りなら高難度の判断品質が低い可能性を実traceで診断し、未測定の高性能主張で補わない。過去v6設計のチェック欄は履歴、現在は本節を正本とする。

## 最新の実行状態と残TODO
- [x] main320a4624のv7/既定Haikuとdeployment pin7の公式完全一致、本人mail wake=true、標準deploymentの手動run/read4+email.read/Haiku actual span確認。自然runは未確認。
- [x] Naïve内Postizで英語進捗1件作成、公式PUBLISHEDとX release URL確認。売上実証ではない。
- [x] 自動再開した旧reportを含む、この担当だけの終了済み有限session7件をcancelし、各before idle/after cancelledを公式GET照合。現deployment/publication sessionと他agentは不変。
- [ ] 現在cursor: 旧reportのSonnet5実callで書換えたoffer/sampleをprimary事実限定版（29 USDC/納品後払い）へnative復元/read照合。journalの人間必須断定は修正済み、標準deployment sessionのMCP read/write/readとHaiku実span成功を確認。公開前に内容/根拠/価格を再照合する。
- [ ] 独立送信元からの本人mail受信と自然wakeを確認。Grok/Museへ既存Slack threadで内部test1通を依頼済み、返信/送信は未確認。
- [ ] 英語の詳細記事/実画面demo/offer公開、実顧客の受注/納品/支払/実費を照合、USD10K monthly revenue目標へ進める。
Ruling: 予算変更の自動resumeは公式仕様であり、古いreportの再開/書込を実eventで確認。旧probeのcancelは成果物を消さず、他ownerへ触らず、自分の重複業務だけを防ぐ。Sonnet成功の遅延eventを追加して旧未実行説明を訂正する。

## v8公開作業の現cursor
- [x] 事実限定offer/sampleのnative復元/read2件一致。詳細英語記事のwrite完了。
- [ ] v8/月3USDをmain反映し、既存残高内でarticle read/editor観測を再開。1task0.75USD、追加入金なし、旧probe7件はcancel済み。
- [ ] 記事の数字/出典/秘密/実績をfresh AI reviewで照合し、本人資格情報不要の通常browser編集で公開する。
Ruling: 実費1.809584USD時点で次callの上限見積が月2USDに入らず、公式org残高9.781134USDを確認。公開作業へ既存残高から追加1USDの上限だけ割り当て、月3USDとする。誤りなら追加費用は最大1USD、他agent上限や入金を変更しない。

## v9 rich-text公開cursor
- [x] v8/月3USD適用とdeployment明示PATCH/GET。英語確定稿のnative write入力全文一致、head/tail readを確認。公開画面の到達とタイトル入力は実画像で確認。
- [ ] v6 Postiz完了/v7記事完了/v8未完publisherの3sessionをcancelしてからv9へ移る。
- [ ] 現在cursor: 月5USD/task1USD/既定Sonnetのv9をmain適用し、修正原稿と正しい実入力要素で1USD以内の有限公開runを行う。browser.observe instruction/textarea wrapperの理解をgeneric promptへ反映。
- [ ] 公開URL/本文全9評価/末尾/編集権限を公式状態で照合し、図版と実画面demo・offer公開・実受注/決済へ進む。
Ruling: Haikuのタイトル/著者入力反復は0.580013USDで完走せず、前のSonnet report5callsは0.137808USDで完了した。課題が異なるので性能順位にはせず、今回のUI公開をSonnetで有限検証する。費用権限は既存残高内で月3→5USD/task0.75→1USDへ限定、他agentと追加入金は変更しない。旧jobを先に終了してauto-resume競合を防ぐ。

### v9本文欄の境界診断

- PR #9131 / main `4b9e9d5f3533b12685b90c1a299f8693aa46ce7c` 由来のagent/deployment v9をGET全payload一致で確認。Sonnet/月5USD/task1USD、旧12session一覧に再開待ち無し。
- 新session `ses_9y6gzbmp2e4dje7rs7mw926q49` は同Computerで原稿修正保存と画面表示に成功、Sonnet実14call確認。費用440092microUSD、次call見積りがsession残枠に収まらずbudget_paused。予算を使い切ったとの主張はしない。
- extractはheading等の意味要素を返し、textarea/input/contenteditable無しと応答したが、実画像にはTitle/Your name/Your story/Publishが存在。DOM不存在の証明ではない。公開本文/URL/売上は未達。
- 次cursor: この有限sessionをcancel→GETし、長文readより先に、公開HTML/JSで確認したQuill領域 `#_tl_editor` と `h1` / `address` / `p` を実browserで短文検証する新しい有限runを1USD枠で実行。著者任意の失敗を繰り返さない。type結果だけで成功判定せず画像/本文readbackで照合。短文入力が成功した場合のみ原稿read→本文入力→Publish1回。新規入金/上限変更/他owner変更なし。
- 順序変更理由: 旧順序の全文read/全文writeが入力可否の証明より先で費用を使った。新順序は短文入力可否→原稿read→公開。現在cursorは短文probe。

- 一次code訂正: `updateEditableText` のtextarea生成は `.editable_text` 対象。確認したclass追加箇所は画像captionであり、TitleBlot=h1/AuthorBlot=addressの子textareaを証明しない。primaryの一般化を撤回し、nativeへ訂正送信。`#_tl_editor p` のtypeは応答成功でも画像の本文は空、抽出結果はaccessibility概略。次probeはclickでフォーカス→type→実画像の順に1回、未成功なら具体的記録で有限runを終了する。

### 編集経路の試験を閉じ、既存Postiz記事機能で配信

- 短文probe `ses_1rykwwdetswjcd50fe80asfvj1` はclick→type後も画像に本文が反映されず、具体的な証拠を保存してcancel→GET cancelled。費用496773microUSD。Telegra.ph公開成功/DOM属性取得成功は未達。
- Postiz公式posts一覧で同じ指定Xに既存の別担当記事が `post_type=article` / PUBLISHEDであることを確認（既存記事は変更しない）。article_title/article_status=published/HTML本文、cover任意の公式schemaが利用可能。
- 次cursor: review済み英語原稿を情報を落とさずHTMLへ整え、X新規campaignとしてNaïve自身の既許可MCP integrationSchedulePostToolから1回配信。本人ブラウザ問題の解決とは区別する。事前native schema/target/重複確認→1送信→公式posts一覧でreadback。native runは現在の1USD ceiling内、新規入金/月5USD変更なし。英語記事と実画像の公開用ファイルもBusinessRun Benchで保存する。
- 順序変更: 旧cursorはTelegra.ph本文入力、実測はtype成功応答と空画面の不一致。新cursorは既に実投稿成功し長文記事もproviderで確認できた許可済みPostiz機能。顧客獲得と未完収益化の前に、記事配信の無駄な再試行を減らす。

### 英語全文公開と長文tool引数の境界

- BusinessRun Bench PR #2 / main `f6cf6c0512a2ea24eb179fb83968965d8d42fde0` に `ARTICLE.en.md` と実cloud画面を公開。raw固定SHAから全文・画像を再取得しbyte一致。fresh公開前review PASS。本文25,761文字、HTML版の22ドル記号/31出所link/数値保持確認。
- Personal Postizへ実画像をuploadしready、生成画像ではない。native長文session `ses_45z2wmn9aswkk3rv3b34wtww91` は指定X/記事schema/直近重複照合成功、長いJSON引数が不正となり、integrationSchedulePostToolはNot runと明示（切断が疑われるが原因未確定）。未送信を成功扱いせずsessionをcancel→GET。
- 次cursor: 全文は公開済みのまま、約8,900文字のHTMLへ短縮したX editionを別途reviewし、同じ既許可native MCPで1回配信。9eval名と比較限界/実測結果/未達/全文参照を保持。exact payloadと受理されたpayloadの差分を照合し、公式posts一覧でPUBLISHED/URLを確認する。tool引数が不正なら外部未送信かreceiptから判断し、盲目的に再送しない。設定/月5USD/task1USDは不変。
- 新しい観測: browser.session.openedイベントのcomputer_idは空文字、専用Computerのbrowser一覧0と整合するが因果は未確認。連続録画/Computer紐付けを成功扱いにしない。
- 順序変更理由: 旧cursorの全文X配信は長い引数のJSON不正で失敗。新cursorはGitHub全文+X要約。ブラウザ編集の再試行や全原稿の再生成を増やさず、次の本人mail実配送/受注/納品/第三者入金へ進む。

- 短縮版session `ses_6sf2vnd4xrt2mkw8rv9xaq3wzs` は最初の推論前にagent monthly cap見積りで拒否（consumed0）。予算を増やさず、既にPostiz実投稿成功のHaiku4.5をこの有限sessionのmessage model overrideとして選ぶ。agent/deployment v9既定Sonnetやcap5/task1は変更しない。設定とactual spanを区別し、短縮版exact payloadは再著述しない。

### v10継続と実売上へのcursor

- 英語全文: https://github.com/Daisuke134/businessrun-bench/blob/main/ARTICLE.en.md 。X短縮版: https://twitter.com/diceai0/status/2117508306130362806 。native Haiku実送信のHTML/settingsはreview済みpayloadと完全一致、公式PUBLISHED/error null。費用116878microUSD、journal更新write成功。登録/売上/無介入/録画の達成とは区別する。
- 既定v10はHaiku、deployment pin10。月5/task1・11tools・既存Identity/cron不変。Sonnet quote拒否で通常継続も止まるリスクを減らし、既に完了した配信・inbox対応を予算内で行うため。品質の一般順位を主張しない。main固定SHA適用→全payloadGET照合→実span確認。
- 次: TLDR AI（https://tldr.tech/ai）の通常browserフォームに本人inboxを使い1購読し、外部メール受信を検証。公開HTMLでinput[type=email][name=email]、form.signup-form、button[type=submit]を確認。非表示のwebsite欄は触らず、実画面で値/完了を確認して1送信。不確実なsubmitは再送せずreadback。届けば本人email.read→必要な確認リンクをbrowserで処理、秘密リンクは一般メモへ出さない。外部送信/provider id/時刻とinbound/wakeを分けて記録。
- 残TODO順: ①本人メール実配送 ②公開pilot offer/sampleと受注経路 ③受注・納品・第三者USDC receipt/費用 ④自然deployment/wakeの実証と本物の連続録画 ⑤1件あたり黒字を確認して移植/複製。USD10K月売上/MRRは目標であり未達。

- 実行順の短縮: 旧「v10 main/適用待ち→mail probe」から、新「確認済みv9+Haiku overrideで本人mail配送probeをCIと独立実行→v10 main/固定反映」へ。email/browser/Identity/capが同一であり待ち時間を減らせるため。既存記事はPUBLISHED公式URLをjournalへ記録してから新しいmail cursorへ進み、外部発信を重複しない。v10へ新機能や追加権限は入れない。

### v10実反映・メール受信の次の切り分け

- main `05ba1e3f591d0146981b5fb8985815e02788c9b0` からagent/deployment v10を適用し全payloadGET一致。modelHaiku4.5、月5/task1、Identity/cron/11allow維持。有限記事+TLDR sessionはcancel→GET、履歴保持。
- TLDRは有効メール入力とSubscribing…表示まで。外部購読の完了/受信は未確認。session累計491167microUSD（記事116878を含む）。再登録は行わない。本人受信domainのMXはreceive.forge.rmta.netで存在確認。
- 公開後の限界: Postiz保存本文では本文img src URLとGitHub全文参照anchorが欠ける。native送信payload一致とPUBLISHED/error nullは確認したが、Xでの全文/画像表示一致は未確認。publicXのcrwl取得は空。GitHub全文と実画像はbyte一致公開済み。
- 次は自分のactive inboxから公開の自動検査宛先check-auth@verifier.port25.comへnonce付き診断mailをnative email.sendで1通。公式PowerMTA forumはauth-checkerがreplyすると案内（https://forum.port25.com/general-discussion-1/pmta-help-to-use-dkim-signature/）、現MXも存在。checker本体の現ページは空で本文未取得のため、現稼働/返信先選択は試験結果で判定する。addressは検査サービスの既知アドレスで、サービス生存は未証明。個人やsupport担当へは送らない。
- 有限v10 session予算0.4USD、月5/task1は上げない。own inbox確認→1send→provider id/nonceをjournal保存→email.read1回→未着なら終了しprimaryの後続readbackへ。SMTP受付と到達/返信/収益を分け、同じ診断mailを再送しない。外部返信が来ても顧客/売上とは数えない。
- 次の収益cursor: publicpilot offer/sample/受注→実納品→第三者決済。メール不着をGoogle必須へ置換せず、外部送信段階/受信routeを具体的に切り分ける。

### 受注窓口を先行公開する順序

- Port25へのnative1通はaccepted、単発返信checkでも未着。v10実modelHaiku/実tool確認、最初の有限job費用30813microUSD（後続readは別累計）。SMTP/inboundと顧客売上を分離する。
- AgentMail orgのread-only preflightはinbox_count=3/limit=3、suspended無し。既存3箱に今回ownerの証拠無し。削除/借用/新箱作成/有料upgradeは行わない。組織/一覧の読取だけで他ownerの内容は未読。
- 旧順序「メール実配送→public offer」から、新順序「公開trace用GitHub Issues窓口/offer/sample→Naïve browserで読取→Postiz公開レポート納品→第三者29USDC入金、メール配送は独立切り分け」へ。メール配送を売り出しの追加gateにせず、既存のbrowser+Postiz機能だけで公開pilotを完走するため。
- pilotはpublic-redacted-trace限定、20toolcalls以下。顧客は公開依頼と公開レポートに同意し、秘密・個人/顧客data・private URLは入力不可。AIがscopeを自律判定し、人間承認は不要。納品は指定Xの英語articleにissue番号を明記。24hはaccepted scope後の目標、subscription/実績/性能保証無し。29USDC Baseは納品後のみ。現在verified sales0。
- v11 sourceは受注URLを既存deployment inputへ追加、systemにpublic scope/untrusted-input/dedup/order evidenceを追加するだけ。modelHaiku/cap5/task1/11allow/Identity/cron不変。Computerのorders/issue-数字.jsonでreport postid/state/paid receiptを記録。既存同番号の公開reportがあれば再納品せず状態照合。支払済みはBase nativeUSDC/専用recipient/29USDC/成功txをブラウザ公式explorerで一致確認した場合のみ。
- 公開物はBusinessRun Benchのpilot offer/sample、public receiver metadata、GitHub issue form。Naïveが読むのはpublic issuesのみ、GitHubのAPI/CLIで業務を自動化しない。運営側のリポジトリへのspec/商品説明/issue-formの保存は通常の開発作業。既存benchmark issue/他writer/既存投稿を変更しない。追加の内部mock発注は完了gateにしない。

- v11のsingle-writer運用: 自分のinbox wakeだけfalseへ変更し、12時間定期deploymentの1run最大1件に集約。旧有限probeはcancelして外部公開を重複させない。model/budget/11allow/Identity/cronは維持。native注文メモとPostiz同番号reportで再送を防ぎ、支払txも二重充当しない。メール受付の高速wakeはこのpublic-only pilotでは成果条件にしない。
- 既存skillの質問・design承認gateは、Daisが明示的に質問を省略し実行判断を委任済みのためbrainstormingのopt-out例外に従う。追加mock発注や内部購入を成果gateにしない。public issue form/offerの公開、nativeファイル契約一致、v11全payload/owned wake GET一致、native browserで実intake画面読取を最小受入とし、実売上は第三者receiptまで未達のままにする。

- offerの隣接成功例: https://www.coderabbit.ai/ はfirst-partyで17K customers/6M repositoriesを掲示。独立検証した数字ではなく、public単発trace-reviewの販売実績でもない。同じ価格/商品/媒体での成功例は未取得の穴として残し、29USDCは1件単位の仮説pilot。模倣するのは具体的な失敗例→修正案→再検証→明確なCTAと低い初期負担の構成で、文章/コード/画像/成果数字を自社へ流用しない。計測は依頼数/適合数/公開納品数/第三者USDC receipt/直接費用、traffic分母未取得のconversionはunknown。
- 現cadenceのcapacity: 1run最大1件×12時間毎では最大2件/日、30日×29USDCで理論上1740USDC（需要/稼働/支払が全て成立した上限で予測ではない）。USD10K月売上にはこの初期設定のままでは届かない。最初の有償納品と費用を実証後、実受注に合わせて頻度/単価/並列性/資源配分を自律更新する。まず需要ゼロ/赤字の複製を増やさない。
- Grok/Muse本人DMはSlack connectorのrestricted_action_read_only_channelで拒否、送信0。既存team threadへの送信は成功しているが返信未確認。別accountや非対応APIで制限を迂回しない。

### 公開pilotの反映とv12予算修復

- Public PR #3/main `041bc1f2f81f6d468dff075fa8b998f675cff02c` のoffer/sample/receiver/issue formを固定SHAで4/4byte一致確認。trace-review label作成済み。native offer write/read一致、見積り契約との差は引用符正規化だけで、相対article linkは絶対URLへ修正read済み。
- PR #9135/main `2b87217bf43b75a47233d21790d4feb62677c519` のagent/deployment v11全payload GET一致、本人wake=false/owner一致。旧Port25有限sessionはcancel→GET。秘密検査/関連CI PASS、無関係loop2件は反映時点で実行中。
- native browser goto実callはpublic intakeへ到達、observeは空配列。空画面/zero requestsを区別するvisual追加probeは推論前にbudget quoteで停止。依頼ゼロの実画面確認成功とは扱わない。旧session累計108481microUSD、当該追加probe/募集は未実行。
- 既存agent実費4843496microUSD、org live残高26742594microUSD。短い新sessionもagent capで停止/費用0、150000microUSDのtask枠は作成時pre-flight quote未満で402、400000枠では作成できたがagent capで停止。実費消費と予約見積を区別する。無送信をeventで確認し同sessionをcancel→GET。
- 現在cursor: 月5→6USD（追加支出権限は最大1USD）、task1USDを維持するv12をmain固定SHAへ反映→agent/deployment GET一致→新しい短い有限runで募集1postとnative browser実画面確認。旧停止sessionは先にcancel済み、auto-resume競合を防ぐ。追加入金/他agent変更無し。以降は実依頼→納品→第三者USDC receipt/費用、自然run/録画、黒字後の移植/複製。実売上/USD10K/自己compute支払は未達。
- 順序は募集/実intake→受注→納品→決済を維持。予算修復を現在cursorに挿入する理由は現残枠が次call見積り未満で、自然runも停止するため。追加1USDの効果を実費/receiptで判定し、無制限増額にしない。

### 現在の正本: v12稼働・公開募集・実依頼待ち

- [x] PR #9137/main `326fc27a46acc3501940f9f095c835c7250c76cf` を反映。agent/deployment v12全payload GET一致、Haiku4.5/月6USD/task1USD/11allow/default deny/同Identity/12h cron、本人wake=falseを維持。反映時は関連チェック・秘密検査PASS、無関係loop2件は実行中（全PASSと主張しない）。v11 PR #9135は後続確認で全15checks PASS。
- [x] Naïve本人のnative Postiz1callから英語募集を公開。post `cmw0dbzbq01gxoc0703wetiwi`、公式PUBLISHED/error null、https://twitter.com/diceai0/status/2117519919034077664 。257文字の送信payload/公式保存本文ともreviewed exact一致。3model spansはHaiku4.5。初回投稿部分22726microUSD。rootによる業務投稿の代行ではない。
- [x] 同finite runで本人browserがGitHub公開依頼一覧をログイン無しでgoto。extract初回はJSON不正でNot run、短い正規JSONに直した再試行は成功し「0 results / No results matched your search」。native screenshot/view_image、primaryの実画像も同状態。Computer public-pilot-intake.jsonはnative write/read exact、extract完了のprovider時刻2026-11-03T07:32:04.820Z、public依頼0（ファイル内の自己申告時刻を計測時計には使わない）。空observeからゼロ件を推測した主張を置換する。
- [x] native public-pilot-promo.jsonのread、intakeファイルwrite/read成功。有限session `ses_35xzd8a1ad2anyqv9j0rcr3v8e` はend_turn後cancel→GET cancelled。合計60211microUSD（募集と受注画面確認）、担当累計4908335microUSD。直接費であり全社費用/利益ではない。副作用不明の再送や内部偽注文は無し。定期deploymentはenabledのまま。
- [x] Grok/Museへ既存Slack threadで公開窓口と具体的な再利用手順/provider receiptの照会を送信成功。https://dais-45u3124.slack.com/archives/C0CBLBGSBJN/p1793690848660309 。返信は未確認、本人DM制限は迂回しない。

残TODO（現在cursorは1、全体goalはactive）:
1. 実依頼の獲得。公開pilot https://github.com/Daisuke134/businessrun-bench/blob/main/pilot/README.md と英語募集が稼働。適合した第三者依頼→native分析→英語公開レポート→29USDC/Baseの成功tx/recipient/token/amount/重複照合→費用差引きの順。最初の第三者売上は未達、内部送金/クリック/投稿を代用しない。依頼数0の時点で反復募集や同じ画面巡回を増やさず、顧客反応/チーム返信/自然runを次の観測とする。
2. 次の標準自然runは2026-11-03T12:00:00Z（JST21時）。manual≠natural。実runの版/費用/入力量/介入点/公式納品receiptを記録。初回の実有償業務を連続画面録画で保存する。いま保存した単一スクリーンショットを動画と呼ばない。
3. 本人inbound配送は独立切り分け。Port25 accepted/返信未着、TLDR送信完了不明、AgentMail3/3で今回owner未確認。個人Google必須にはせず、既存共有箱の借用/変更や同じ診断送信はしない。public pilot発売のgateに戻さない。
4. 少なくとも1件の有償納品と実費からunit economicsを検証し、実需要に合わせ価格/頻度/資源を更新。12h×1件×29×30日の初期理論capacityは1740USDC/月で10Kに届かない。需要/稼働/入金を実証する前にこの上限を売上予測と呼ばない。
5. 利用者向けiPhone入口を設け、利用者個人のGoogle/メール入力/password/PCを要求せずManagerを利用できる導線を実装・実機確認する。現在のdeveloper向けGitHub依頼フォームはこのconsumer入口ではない。infrastructure契約と利用者本人確認/引出条件を区別し、銀行情報以外不要と未確認で約束しない。
6. 黒字の手順/評価/最小stateを他のVMへ移植し2拠点で実証。専用Identity/credential所有/資源上限/仕事重複を維持する。receiving-only walletにoutgoing signerは未接続、compute自費支払/自己複製/任意cloud互換は未達。USD10K月売上/MRR・YC採択・優勝は目標であり未達。

証拠正本: repo外private `/Users/anicca/.local/state/naive-browser-company` のagent/deployment-readback-v12.json、public-pilot-promo-provider-readback.json、public-pilot-promo-v12-events.json、public-pilot-intake-v12-events.json、public-pilot-intake-cloud.jpg、public-pilot-v12-finite-cancel-readback.json、own-agent-spend-after-pilot-launch.json。署名付き画面URL/メール原文/秘密値は公開しない。

### 受注待ちと並行する本人メール配送の境界診断

目的: 新しい個人メール依存を加えず、本人Naïveメールの外部到達と送信認証を切り分ける。範囲: 自動メール検査 https://www.mail-tester.com/ の通常browser画面で自分用の一時検査宛先を取得し、native email.sendを最大1通、画面から結果と認証情報を読む。公式homepage取得は「First, send your email to」を確認したが動的本文は未取得、無料枠/実行可否は実UIで確認し、購入・有料plan・上限変更は行わない。完了条件: 実送信acceptedと外部受信を区別し、受信した場合はprovider結果/headersのSPF/DKIM/DMARCと画像を確認、未着なら未着の正確な境界を保存する。認証passやscoreを捏造せず、新probeも送信成功だけで受信/登録完了にしない。

既存Inbox/個人Googleは使わない。Inkbox2identity（managerjghh/aiclips-agent）はlive active/mailactiveだが今回ownerの証拠無し、作成toolも無いため借用・変更無し。Naïve本人messagesはfresh GETで0/has_more=false。既存Port25/TLDR宛先へ再送せず、検査本文に個人/顧客data・秘密・本番URLを入れない。宛先/原文/署名付き画面URLはprivate evidenceだけに保存する。

全体TODO順は変更しない。現在の受注待ちと自然run12UTCまでに独立実行でき、登録要件の本人mail経路の未確認を狭めるためTODO3を並行する。native有限runは同じv12/Identity/11tools、予算最大0.6USD・月6/task1内。定期deployment/他ownerは不変、1通の不確実な再送はしない。既存募集・記事を再公開しない。
