# Naïve browser company Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans。primaryが単独実装し、最後にfresh read-only reviewを使う。

**Goal:** Naïve自身のbrowserをLLMが操作して既存の会社業務を完走する。
**Architecture:** 標準pi agentの外部操作はbrowser、本人専用のemail.inboxes/read/send、指定Postiz4tools、Computer read/writeは作業メモと成果物に使い、判断は自然言語promptへ置く。APIは基盤設定/実行/証拠読取に限定する。
**Tech Stack:** Naïve標準agent/session/browser、JSON設定。追加依存なし。
**Spec:** docs/superpowers/specs/2026-09-25-life-manager-unified-ssot.md の Naïve browser company 節。

## Global Constraints
- 既存owner・共有profile・既存6agent/cronを変更しない。
- 専用capは修復sourceで月8USD/max_task1USD、既存残高内・追加入金なし。現在の稼働値と未反映targetは「現在の実行詳細」を参照。
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
- [ ] MAIL03: Capafyは同一controlの既存Publisher内で公式の専用agentmail認証/team権限があるか既存ownerへread-only確認。正式経路が判明したら同じPublisherへ接続し本人画面を確認。別メールで重複Publisherを作成しない。本人mailの一般登録/受信検証は独立項目。
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

### 現在の実行詳細: v19稼働・実依頼と納品収益の検証

実行順・完了条件の正本は統合SSOTの「Naïve実反映と残TODO」、本節はその実行詳細。過去v6〜v18/予算/cursorは当時の履歴。現在はagent current19/production deployment19/月8USD/task1USD、既定Haiku4.5。PR9166/main14e9dbd5eedfd1f73f5eeec5643f167f07897282固定sourceから反映し、agent/deployment全source fieldsを公式GET一致。HN有限probeは同一turnの実画面操作に成功、end_turn後は白画面で保持できず、費33763microUSDを台帳7件と照合。cancelled/pending0、current Computer null/旧Computer destroyed。次自然runは11/04 00UTC。直近自然runは旧pin13の無受注確認までで、新v19の自然run・有償納品・実第三者売上は未確認。現在cursorは同一turnのnative順次操作で公開需要最大1件を調べること。詳細は末尾「v19の実反映と保持probe結果」。

- [x] PR #9137/main `326fc27a46acc3501940f9f095c835c7250c76cf` を反映。agent/deployment v12全payload GET一致、Haiku4.5/月6USD/task1USD/11allow/default deny/同Identity/12h cron、本人wake=falseを維持。反映時は関連チェック・秘密検査PASS、無関係loop2件は実行中（全PASSと主張しない）。v11 PR #9135は後続確認で全15checks PASS。
- [x] Naïve本人のnative Postiz1callから英語募集を公開。post `cmw0dbzbq01gxoc0703wetiwi`、公式PUBLISHED/error null、https://twitter.com/diceai0/status/2117519919034077664 。257文字の送信payload/公式保存本文ともreviewed exact一致。3model spansはHaiku4.5。初回投稿部分22726microUSD。rootによる業務投稿の代行ではない。
- [x] 同finite runで本人browserがGitHub公開依頼一覧をログイン無しでgoto。extract初回はJSON不正でNot run、短い正規JSONに直した再試行は成功し「0 results / No results matched your search」。native screenshot/view_image、primaryの実画像も同状態。Computer public-pilot-intake.jsonはnative write/read exact、extract完了のprovider時刻2026-11-03T07:32:04.820Z、public依頼0（ファイル内の自己申告時刻を計測時計には使わない）。空observeからゼロ件を推測した主張を置換する。
- [x] native public-pilot-promo.jsonのread、intakeファイルwrite/read成功。有限session `ses_35xzd8a1ad2anyqv9j0rcr3v8e` はend_turn後cancel→GET cancelled。合計60211microUSD（募集と受注画面確認）、担当累計4908335microUSD。直接費であり全社費用/利益ではない。副作用不明の再送や内部偽注文は無し。定期deploymentはenabledのまま。
- [x] Grok/Museへ既存Slack threadで公開窓口と具体的な再利用手順/provider receiptの照会を送信成功。https://dais-45u3124.slack.com/archives/C0CBLBGSBJN/p1793690848660309 。返信は未確認、本人DM制限は迂回しない。

残TODOの順序・現在cursor → `docs/superpowers/specs/2026-09-25-life-manager-unified-ssot.md`「Naïve実反映と残TODO」。本planの以後のcursor・budget記述は各診断時点の履歴として読む。

証拠正本: repo外private `/Users/anicca/.local/state/naive-browser-company` のagent/deployment-readback-v12.json、public-pilot-promo-provider-readback.json、public-pilot-promo-v12-events.json、public-pilot-intake-v12-events.json、public-pilot-intake-cloud.jpg、public-pilot-v12-finite-cancel-readback.json、own-agent-spend-after-pilot-launch.json。署名付き画面URL/メール原文/秘密値は公開しない。

### 受注待ちと並行する本人メール配送の境界診断

目的: 新しい個人メール依存を加えず、本人Naïveメールの外部到達と送信認証を切り分ける。範囲: 自動メール検査 https://www.mail-tester.com/ の通常browser画面で自分用の一時検査宛先を取得し、native email.sendを最大1通、画面から結果と認証情報を読む。公式homepage取得は「First, send your email to」を確認したが動的本文は未取得、無料枠/実行可否は実UIで確認し、購入・有料plan・上限変更は行わない。完了条件: 実送信acceptedと外部受信を区別し、受信した場合はprovider結果/headersのSPF/DKIM/DMARCと画像を確認、未着なら未着の正確な境界を保存する。認証passやscoreを捏造せず、新probeも送信成功だけで受信/登録完了にしない。

既存Inbox/個人Googleは使わない。Inkbox2identity（managerjghh/aiclips-agent）はlive active/mailactiveだが今回ownerの証拠無し、作成toolも無いため借用・変更無し。Naïve本人messagesはfresh GETで0/has_more=false。既存Port25/TLDR宛先へ再送せず、検査本文に個人/顧客data・秘密・本番URLを入れない。宛先/原文/署名付き画面URLはprivate evidenceだけに保存する。

全体TODO順は変更しない。現在の受注待ちと自然run12UTCまでに独立実行でき、登録要件の本人mail経路の未確認を狭めるためTODO3を並行する。native有限runは同じv12/Identity/11tools、予算最大0.6USD・月6/task1内。定期deployment/他ownerは不変、1通の不確実な再送はしない。既存募集・記事を再公開しない。

#### 本人メール外部到達の実測結果

- native v12有限run `ses_c35jfm02r3v865kqqnrs5amjg9` が、mail-testerの通常browserから取得した宛先へ本人inboxのemail.sendを1通実行。外部画面が同一subject/nonceの受信を示し10/10、本人browser extract155はSPF=pass/DKIM=valid/DMARC=pass。受信レポート一次HTMLのAuthentication-Results（DMARC/DKIM pass）とSpamAssassin SPF_PASSも整合。送信受付だけの主張を、今回1通の外部実受信と認証結果まで進める。全宛先への到達保証/返信/本人inboundの証明にはしない。
- 認証panelの自然言語act失敗を、実HTMLで確認した `.test-result.signature .header` のclickで回復。native browser screenshot/view_image、最終file write184/read187 exact。画像は10/10の上部を示し、SPF等の詳細はnative extractと一次headerの証拠であり、画像内に全詳細が写るとは言わない。
- read-only検証で、nativeファイル自己申告のextraction_timestampとprovider event155時刻の不一致を確認。rawファイルは監査のため保持し、自己申告時刻を公式時計として使わない。`mail-tester-verification.json` にprovider event25/58/155/187.created_atを実際の観測時刻として結合する。外部の正確な受信時刻は未取得でnull。内容read/write一致と時刻の真偽を区別する。
- 有限runはend_turn→cancel→GET cancelled、実費221926microUSD、担当累計5135524microUSD。月6/task1不変、追加入金/他owner変更/追加メール送信なし。本人messagesはchannel=emailを明示したfresh GETでも0/has_more=false。本人inbound/サイト登録/売上成功は未達。Grok/Muse返信は引き続き未確認、12UTCの自然runはまだ開始前。
- Amazon SES公式 https://docs.aws.amazon.com/ses/latest/dg/send-an-email-from-console.html のOOTO simulatorはReturn-Path/envelope senderへ返信し、外部源には応答しない。今回headerにSES署名はあるが、自分の表示Fromへの返信を証明しないため追加sendを実行しない。宛先/私有reportURL/rawheaders/署名付き画像URLはprivate evidenceのみ。
- 全体cursorは実第三者依頼→公開納品→成功USDC tx/費用。本人mailの残境界は外部到達ではなく、実送信が確認できた第三者から本人inboundへの到着と登録確認リンクの処理。先のTLDR Subscribing…やPort25 acceptedを、第三者dispatch/本人受信として補わない。

### 本人メールによるDEV登録の実行範囲

目的: 個人Googleを使わず、本人mailへの実登録通知と本人browserでの登録完了を確認する。対象はDEV CommunityのAI運営BusinessRunアカウント1件。Google不要の公式email signup linkと実HTML（user[name]/user[username]/user[email]/password/password_confirmation）を確認。https://dev.to/enter?state=new-user → https://dev.to/users/sign_up?state=email_signup 。Terms https://dev.to/terms は自分が権利を持つ内容の投稿を要求し、実験本文/画像は自分の検証素材だけ。guidelines URLは404で未取得、今回の範囲は登録だけで投稿しない。

- credential SSOT全体の既存DEV/forem相当行は無し。本人vaultのlogin:dev.toもfresh GETで無し。既存個人/他agentのaccountを流用せず、新規1accountだけ。公開表示はBusinessRun AI、usernameはbusinessrunai（使用済なら自分用suffixを1回選ぶ）で人間を装わない。
- 同じv12/Identity/本人browserとemailだけ。ブラウザ登録helperがpasswordを生成・封入し、plaintextをmodel/chat/repoへ出さない。取得後はMac credential SSOTへ専用service naive:browser-operator:dev.to のsealed credential参照/identity/context/登録状態を保存する。providerはpassword write-onlyで返却しないため、秘密をexport/複製しない。
- まず本人browserで実フォームを確認し通常のsignupを1回。確認要求があれば本人email.read1回→届いた自分用確認リンクをbrowserで処理し、メール本文/秘密リンクは一般journalや公開物へ保存しない。不要な再送/別account/有料登録/Google・既存個人credentialsは使わない。サイトの送信表示とSMTP配送/本人受信を区別する。
- 完了判定は公式の登録/ログイン状態と本人受信の実内容。未完なら正確な画面/field/dispatch表示/受信stateと次の一手をprivate記録へ保存する。AI自己申告時計は使わず、時刻を取得できなければnull、primaryはprovider event時計を照合する。
- finite予算最大0.5USD、月6/task1とcronは不変。実顧客受注と12UTC自然runは先のTODO順を維持し、まだ依頼が無い待機中に独立した登録要件を進める。既存記事/募集の再送や新しい公開投稿は行わない。

#### DEV登録の呼び出し元修正

初回native helperはsignup/loginともurl=https://dev.toを渡していた（events24/172/223）。返答はsignup done/login doneだが、実フォームのpassword等は空で登録完了の証拠無し。own login:dev.to credentialは生成され、private SSOTへsealed参照を保存/readback。context grantは同agentへ存在し、権限拡張の根拠無し。2回目signupは既存keyと競合し、追加credentialは作らない。

予算見積りでpausedの旧finiteをownerとしてcancel→GETし、資格情報は維持する。旧finite実費330802microUSD。修正は短い新runから既存credentialのlogin helperを実フォームURL https://dev.to/users/sign_up?state=email_signup へ明示適用すること。トップURLへのhelperや新signup/password再生成は行わない。画面でprotected fieldsの反映を確認し、必要な非secret欄だけ埋め、可能なら同一accountの最終submitと本人確認を進める。正しいURLでもprotected fieldが空なら具体的境界を保存し、秘密export/一般actへのpassword入力で置換しない。各finiteは既存最大0.5USD/月6/task1内、追加メール送信/公開投稿/他owner変更無し。

正しいフォームURLの短いprobeはlogin doneを返したが、実画像ではUsernameへ本人emailが入っただけでName/Email/Password/Confirmationは空。native記録のwrite/readは一致、実費40379microUSD。原因を「全く操作しない」と断定せず、複数段フォームの部分操作/再navigationによる状態初期化の仮説へ絞る。次の限定probeは同一turn内で既存credential login→同じフォームURLの通常fragment付きloginを最大2回追加し、DOMを再読込せず次のprotected欄へ進めるかを画像で検証。新signup/credential再生成/秘密export/一般actでのpassword代入は無し。両protected欄が実際に埋まる場合だけ非secret欄と同一account submit1回へ進む。未反映なら記録して終了。これは新規account追加でなく、未完の1accountの呼び出し元修復。月6/task1/finite0.5内を維持する。

同一documentのfragmentで既存loginを進めてもprotected fieldsは空のまま、当該probeは終了/cancelし成果を保持。次の検証はloginによる登録代替ではなく、本来のsignup helperを正しい登録フォームへ適用する。旧login:dev.toは削除/上書きせず保持し、service=dev.to-businessrun-registrationの専用保管名を1つ使う（SDK serviceはcredential key名、対象サイト/本人メールは同じDEVの未完1account）。この1回以外のsignup/新service名追加はしない。まず実フォームの非secret Name/Username/Emailを通常UIで埋め、同一URLにfragmentを付けて既存画面を保ちsignup helperを1回呼ぶ。生成credentialは直ちに同じprivate SSOT serviceのattempt参照として追記し、未検証accountを有効と扱わない。protected欄が埋まった場合だけ同一accountのsubmit1回/本人確認へ進め、空のままなら真のsignup postcondition未達として記録する。source/API/backendの原因は未確定であり、SDK全般の欠陥や個人Google必須を断定しない。月6/task1/finite0.5内、旧値の秘密export/他owner変更無し。

#### DEV登録の現在の実測と次の境界

- 正しいsignup helperの実引数はservice=dev.to-businessrun-registration、url=https://dev.to/users/sign_up?state=email_signup#businessrun-signup（event44）。通常typeは実HTMLのCSS idによりName/Username/本人Emailの3欄を順番に入力し、画像で反映を確認。helper返答はsignup doneだが、直後画像50はPassword/Confirmationが空に見え、登録/ログイン成立・確認mail dispatchの公式証拠は無い。native記録の「no submission occurred」はmodel側の判断であり、helper内部network不存在まで証明したとは扱わない。
- 正しいsignup runはnative write60/read65 exact、timestamp=null。有効なアカウントのproofは未達。資格情報の生成/封入とアカウント作成を区別する。旧login:dev.toと新login:dev.to-businessrun-registrationの2つのsealed参照はprivate credential SSOT同一serviceのattemptsへ保存/readback、元の秘密は削除/上書き/公開無し。両参照のaccount stateはnot_verified。一般act/typeでpasswordを入れない。
- 初回有限run330802microUSD、exact/fragment run86933microUSD、正しいsignup run82315microUSD。いずれもownerでcancel→GET cancelled。担当累計5656872microUSD、月6/task1不変。既存記事/募集/定期deployment/他owner変更無し。公開顧客からの売上は未確認。
- 既存owner Computerのfresh GETはpaused/browser=null、Computer browser GETは404。これは有限run終了後の観測であり、native browserが別Computerであることや、今回の未反映の原因を証明しない。
- 次の技術cursor: 同一の自分用credentialと通常のComputer SDK browser interfaceを使い、native helperの短いdone文字列と公式browser_action応答を比較する。ウェブサイトの登録API/業務scriptへ置換しない。追加のsignup/credential名を増やす前にこの境界を診断する。既存Computerのowner/設定を確認し、必要なら専用browser付きComputer1台・timeout1分・own scopeの終了/readbackを正本へ具体化してから実行する。SDK API経由の費用はagent累計に含むかを確認し、別なら別計測。個人Google/人間メールへの切替は行わない。
- ネットワーク補足: Reason Primaryのowned devicesは0、home-codex/muse-relay宛て既存照会はqueued/返信未確認。登録済みrelayを実稼働Museと呼ばず、別accountへ切替えて迂回しない。全体goalと実顧客→納品→第三者receipt/費用のcursorは維持する。


### Computer browser SDK応答の限定診断

目的はnative helperのdoneと公式browser_actionの差を同じ本人credentialで比較すること。業務サイトAPI/scriptに置換せず、Naïveのcomputer browserだけを操作する。既存agent Computerはpaused/browser=nullなので変更せず、診断名codex-naive-dev-browser-boundaryの専用Computerを1台、1vCPU/1024MiB/disk5GiB、browser timeout1分/keep_alive=false、dev.toだけ、allow_writes/extract=true/ask_actions=[]で作る。同じ本人contextを指定し、新しいsignup/credential/公開投稿は行わない。

1. 自分のcredential SSOT全体を読みnaiveを完全一致、組織残高と直近ledger境界を保存。封入値は読まずログインの本人Identityを明示する。
2. 実signupフォームgoto→既存login:dev.to-businessrun-registrationのloginを最大1回→正式応答/画像をprivate保存。モデル判断やdoneを登録成立にしない。公開登録の再送は指示しない。
3. finallyで当該browser終了→当該Computer削除→GETの終了状態、組織残高/ledgerの後値を保存。API診断費はagent直接累計と別枠で計測し、差分が不明ならnull。既存runtime/定期deployment/他ownerは不変。

作成費は公式docsで0、computeは1vCPU/1GiB毎秒0.0000185USD、browserは開始から終了の分単位・action別計上で単価は未取得。診断は1browser/1login、timeout1分、全体2分以内を目標に閉じる。追加資金移動なし。既存月6/task1は維持する。初回誤りを再現せず、意味のない繰返しをしない。Inkboxの既存managerjghhはread-only hosted configでinstructions未設定、登録ownerの根拠は増えず、借用/変更/送信しない。


初回SDK診断の差分: createはOpenAPIの200/201例に対して実202で受付成功。診断側が202を失敗扱いしたため同一IDをrecoverし、runningをGETで確認。最初のgotoは400 validation_failed、Idempotency-Key必須とproviderが明示し、ログイン/登録操作へは進んでいない。browser DELETEは204空応答で、診断側JSON parseが失敗したが、同一Computerを別read-only確認後DELETE→GET destroyedまで完了。新規credential/サイト送信無し。残高25930244microUSDは前後同値、独立診断費用の確定ledgerは未取得で0確定としない。

再試行前の修正: HTTP202/204を正しく扱い、必須Idempotency-Keyを各mutationの固定operation IDとして保存して同一操作に再使用する。元Computerは破棄済みなので置換Computerを同条件で1台だけ作る（同時1台）。provider postconditionを先に保存し、cleanup各段は互いのparse失敗でskipしない。新signup無し、既存sealed login最大1回の範囲は不変。

home-codex本人返信でInkbox managerjghhのowner/用途も未確認、Museの現在返信元はdaisuke/terminal@htch-runtimeと判明。既存Coconala入金receiptの所在は既存別業務の証拠であり、今回pilotの売上へ転用しない。NEARの15USDC提案3件はpending/assignment0で収益未確認。以後Museは本人稼働経路を確認して照会し、idle relayへのqueueを着手と呼ばない。


Idempotency-Key付き置換probe2はComputer202/running、browser context_backed=trueで開始したが、gotoのclient read timeout20秒で応答未取得。sealed loginは未呼出。cleanupのbrowser closed→Computer destroyedをGET、組織残高差1667microUSDと同時刻browser debit led_hyhh0zty6189rdd6mkcf1n8p80一致。これはAPI browser分の独立費でありagent累計5656872へ無根拠に合算しない。過去ledgerがlimit差で追加された行を今回費用と誤認しない。browser opened08:42:36.171Z/closed08:42:55.585Z、同期待ちの打切りが診断側制約だったことを記録する。

次はgotoの読み取り猶予を60秒、browser TTL3分/全体4分目標にし、操作開始/終了/単調時計elapsed/transport errorをprivateに記録する。20秒打切りの同じ再試行はせず、初回cold startの応答境界を観測する。置換1台・既存credential login最大1回・新signupなし・cleanup finallyと各独立readbackは維持。goto応答が取れなければその場で再送せず公式browser状態をGETし閉じる。費用は独立ledger、現org残高25.928577USD内。実顧客/自然runのcursorは不変。


#### SDK診断の実測結果と残境界

- probe3は専用Computer create202/running→GET browser.allow_writes=true/allow_extract=true/同contextを確認。gotoは27.699秒で200 browser_action/performed=true/指定DEV signup URLへ成功し、20秒timeoutは診断側の不足だったと判明。sealed loginは23.198秒後403 forbidden/param allow_writes（req_nt6kzxx8hgjxjcvk482kf4r7dv）、screenshotも403/param allow_extract（req_1dh0jp7e9dhvrycjqe7n20h3nh）。両設定がtrueで保存されたことと、実行層がread-onlyと判定したことの不整合まで絞れた。SDK全般の故障やnative signup未完の根因と断定しない。権限を迂回/拡大した再試行はしない。
- browser closeのcontext_backed=true/同context/status closed、Computer GET destroyedを公式確認。今回もsignupは呼んでいない、loginは拒否され、登録成立/確認mail dispatchの証明無し。新credential/公開投稿/既存agent/deploymentの変更無し。計3台は全て破棄済み、最初の誤判定202/204も診断側のミスとして記録する。204と20秒例外はtool実行ログのみで、保存JSONだけでは独立照合できない限界を維持。
- probe3残高差1667microUSDとbrowser debit led_warvrsrcp1a14tda3tgknm7rqw一致。API診断2件のbrowser明細合計3334microUSD、組織残高25.926910USD。agent直接累計5.656872USDと別表示、全社費用/利益へ置換しない。関連JSONと構造化boundary verificationはprivate evidenceに保存。
- 既存native v12は公開受注pilotとして継続し、この独立したDEV/SDK診断を受注/納品の追加gateにしない。current cursorは実依頼→英語レポート→第三者USDC receipt/費用、次の自然runは12UTC/JST21時で未実測。v12は単一商品の初期収益loopで、任意事業を自律選択して移植/自己compute支払/複製するfull Managerの完成とは呼ばない。SDK側の残境界は保存optionsから実行policyへの伝播で、正式な修復経路をsource/docsで調べる。
- Museの既知返信先daisuke/terminalはReason一覧でhtch-runtime/tier turnを確認。本人経路へ既存方法/owner/receiptの照会を送信しqueued、返信は未確認。idle/queuedを稼働・着手とは呼ばず、他agent mailbox/accountを借用しない。


SDKsourceの追加照合: npm公式公開package @usenaive-sdk/vetta 0.10.0をignore-scriptsで取得。computer.browser.loginは同じPOST /v1/computers/{id}/browser/loginへbodyを渡し、screenshotは同じactionsへ送る。requestは全2xxを受理/空応答を{}扱い、mutationにIdempotency-Keyを付与する実装で、今回の初期client不備はSDK自体には無い。browser methodは独自のallow_writes/allow_extract overrideを付けず、create済みbrowser blockを使う契約と整合する。公開SDKsourceに今回403guardのserver実装は含まれず、repository metadataのusenaive/vetta-monoは現在のgh経路でresolve不可。すべてopen sourceと仮定せず、server側根因/修復は未取得として残す。出所 https://www.npmjs.com/package/@usenaive-sdk/vetta 、package SHA1 263630c4977a4a42e4865ba7fe77fd02396f3f0e。


#### Muse本人の回答と受信診断の引継ぎ

Reason daisuke/terminalの本人回答01M6G9HHRXZCB4F371G5A0CP7Eを受領。上のqueued/返信未確認は送信時の履歴で、現在は回答済み。Museの説明ではCapafy既存線は本人側パブリッシャー/KYC/精算が実体、cloud Postiz未接続とMac橋渡し3jobが残る。過去のNaïve線はAPI/CLIのみで本人browserの実績ではない。回答内のAPI先行という一般則は今回のDaisのbrowser明示指示を上書きしない。自分の既存session/vault、単一writer、公開URLまで1回成功してからloop化、公式dashboardと費用照合という再利用部分だけ採る。Capafyowner/許諾/収益を今回pilotへ流用しない。

本人回答のagent用mail経路から、自分がownerであるmailだけを使いNaïve本人宛てにnonceのみの診断1通を送るよう追加照会。Reason message508B1FY1ZXBH5CGSQWAZYSRVZKはqueued、実メール送信/受付idは未確認。新account/設定変更/個人Gmail/他owner借用/再送/本文転送は禁止し、送信可能な本人経路が無ければ不足を返信する範囲。自分のinboundはその後の公式channel=email/limit20 GETで0/has_more=false、同nonce0。外部dispatch未証明なのでNaïve受信不良とは判断しない。private journal muse-inbound-diagnostic.jsonとowned-inbound-after-muse-request.jsonに残す。次は本人の送信receipt→同nonce本人受信の照合、既存受注/自然runと並行しこの診断を売上gateにしない。


### 実表示に基づく受注獲得の限定試験

目的はNaïve本人の実依頼→納品→第三者入金を進めること。旧募集の公式Postiz post analytics（7日指定、当日行）はImpressions27、Likes/Retweets/Replies/Quotes/Bookmarks各0。クリック数は取得無し、27表示だけで需要/旧copy失敗を断定しない。投稿cmw0dbzbq01gxoc0703wetiwiだけを読取り、他channelは触らない。出所 https://docs.postiz.com/public-api/analytics/post.md 、https://docs.postiz.com/general/analytics.md 。native 11allowにはanalyticsが無く、primaryは公式readbackだけ実施し、業務投稿は本人Postiz toolで行う。

最新agent GETはv12、月6/task1、直接spend5660474microUSD、deployment enabled/次12UTCを再確認。前の5656872は当時値、差3602microUSDの内訳/原因は未確認で勝手に帰属させない。API診断browser3334microUSDとは別表示。公式auditは当該browserのopen/closeが存在する一方、403 request IDsの絞込は0/has_more=false、該当時間窓はopen/close2行だけ。監査詳細から拒否根因は得られず、SDK権限不整合の同じ操作を再試行しない。

順序は受注獲得の中で、本人browserで新規適合依頼1回確認→あれば既存契約通り1件納品→無ければ実測例＋直接リンクの下記英語投稿1件を本人Postizで公開→終了。従来の汎用募集から、実測した失敗例→証拠の区別→sample/明確なCTAという隣接成功例の構造を採る限定試験で、同一商品/価格/媒体の成功事例未取得という穴は維持。新copyの優位や売上は仮説。既存募集/記事の再送、別channel/他owner変更、継続的な自動投稿は行わない。

公開予定文（270文字、下記exact。旧postとは別内容）:

```text
A browser agent said "signup done." Password fields were still blank. We kept the account unverified.

Our trace review separates tool replies, screen evidence and provider receipts.
Sample + 29 USDC pilot:
https://github.com/Daisuke134/businessrun-bench/tree/main/pilot
```

本人browserで実依頼画面をextract/画像確認。空observeだけから依頼0としない。依頼が無い場合のみ、公開前にPostiz当日一覧と本人file proof-led-pilot-promo.jsonを確認し、同一copy/既存postがあれば再送しない。新規1postだけX @diceai0へ。送信payload/公式保存本文/PUBLISHED/error/releaseURLを照合し、provider取得無しなら公開成功とは言わない。原稿/画像/価格/商品契約は追加変更無し。

同じv12/Identity/context/model/11allow、有限task最大0.4USD、既存月6/task1/12h cron/wake=falseを維持。予算見積りで拒否ならその正式結果を保存し、無送信と旧session終了を確認してから必要最小の修復を正本化する。自己申告時計を使わずprovider event時計を記録する。有限runはend/cancel/公式GETで終了確認。metricsと依頼・入金は別に記録し、conversion分母/帰属が不明ならnull。画像未生成、新signup/サイト登録再送なし。全体goalはactive、phone-only/移植/自己compute支払/10K売上は未達。


#### 受注確認とduplicate判定の実測修正

native finite ses_ztb2n5fa55ya9b6sqmhyjpmqqnは起動/agent v12で実行、browser extract15と画像は0 results/No results matchedで一致。Postiz当日一覧も取得し、write38/read43はbyte exact、end_turn/idle/68071microUSD/pending0。投稿callは0で、nativeは旧257文字の募集を新270文字とEXACT MATCHと誤分類して見送った。rootは保存済み本人Postiz一覧の文字列をexact照合し、旧copy1件、新copy0件/部分一致0、旧!=新を確認。取得済み一覧の範囲の比較であり、全internetや将来の投稿不存在の保証ではない。

同じfiniteのfollow-upで、旧先頭Agent says "done"と新先頭A browser agent said "signup done."の相違、270文字exact payload、新copy未検出の保存済み証拠を明示し、意味が近いことを完全一致としない修正を渡す。再一覧/再intakeを繰返さず、既存の新copy postidがあれば停止、無ければ承認済み1post→journal訂正/write/readで終了。旧journalはraw証拠としてprivateに保持。自己申告screen時計はprovider event15へ結合し置換、release URLの...を実URLとして使わない。月6/task1/finite0.4内でquote拒否なら送信せず正式状態を記録し、同一不確実投稿を再送しない。


訂正follow-up後、nativeはpostiz.integrationSchedulePostToolを1回呼んだが、tool error94はwaiting for approval、session idle/awaiting_approval、pending tc_086ddc8daf10af17d3de699755aff18d（read_people=true）で実公開はまだ未確認。pending本文を原稿と厳密比較し270文字/改行4/文字列exact一致、対象integration/type/settingsも元の承認済み範囲と一致。Daisの既存公開依頼とfresh content PASSに基づき、primary AIが当該1callだけscope=callでtool_confirmation allowを処理する。Daisの追加承認は要求しない。provider確認カードが存在したことを隠さず、Naïve単独の無介入成功とは呼ばない。AI coordinator付きのhuman0操作として区別し、権限設定を拡大したり他call/sessionへ包括許可しない。返答不明時は同一postの再送禁止、pending/公式投稿を先に照合する。


#### 実公開・リンク削除の根因と導線修復

- primary AIが承認済みpublish1callと直後の15分readback1callをscope=callで確認し、人間への承認依頼0。native publish110は270文字/対象integration/リンクまで原稿exact。Postiz新post cmw0gwaol021voc07nfgk35vfは公式PUBLISHED/error null/publish09:10UTC、https://twitter.com/diceai0/status/2117545009490624995 。native write142/read145はbyte exact。実依頼画面はextract15/実画像0、自己申告時計は使わずprovider event15で結合する。
- 公開本文は206文字でGitHub URL行だけ欠け、原稿270文字とのexact一致はfalse。X公式oEmbedでも同じリンク無し本文を確認。model journalのcontent_verified=trueは実保存本文を読んだ意味で、原稿全体一致の証拠にはしない。native未取得の実release URLはprimary公式readbackで補完。本文再送は無し。
- Postiz公式integrationSchema(x,false)の現在のrulesはdo not add links, they will be stripped from the postと明示。公開source e424fb587e0ae87a2428a0586cb00af6facd0d1dのx.provider.tsはSTRIP_LINKS_FROM_X_POSTSがtruthyなら同文言/stripLinks=true、posts.service.tsは作成時stripLinks(content)を適用。今回の欠落はこの明示仕様と実測が整合し、HTML不良/Naïve改変と断定する必要はない。cloud環境変数自体は読んでいない。新稿前に最新schemaの当該ruleを確認しなかったprimaryの手順不足を訂正する。bare domainもstrip対象であり、変数変更や迂回URLを試さない。
- したがって直接リンクcopyの獲得試験は意図した導線を作れなかった。既存の本文とledgerを残し、同じ投稿を再送せず、リンクを含まない明確なGitHub検索経路の案内を最大1件だけ追加する。これは不足したCTAの修復で、定期広告や旧募集の再送に広げない。scopeにこの1修復postを追加する理由は、実公開されたsample案内に場所が欠けたため。公開済み投稿の更新/返信機能は現在のMCP schedule toolの契約に無く、API業務投稿/別ownerログインで代替しない。
- 有限sessionはcancel→GET cancelled/pending0、合計127132microUSD。最新agent直接spend5791814microUSD、月6/task1維持。API診断browser明細3334microUSDは別表示。合計の増分を未確認のcomponentへ帰属させず、全社費用/利益としない。本人mailの外部送信依頼は引き続きqueued/実送信未確認。全体goal/実売上は未達。

修復公開予定文（213文字、リンク無し）:

```text
BusinessRun Trace Review: sample and requests

On GitHub, search "businessrun-bench" by Daisuke134, then open pilot.

Public redacted traces only (20 tool calls max). 29 USDC after delivery. No verified sales yet.
```

MCP契約に合わせ各段落をpで包むHTMLをraw送信payloadとし、Xの期待表示文は上記。primaryは直近の公式投稿一覧でこの新copy未検出を確認し、nativeは専用journalと既存postidを照合して新しい1postだけ実行。既存公開copyを複製しない。新finite最大0.4USD/同v12/月6/task1で1回だけ起動し、cap quoteで拒否なら無送信・終了を確認してから必要最小の予算修復をsource化する。native自身のPostiz投稿→公式PUBLISHED/保存HTML/期待表示のX oEmbed→記録write/read→有限終了の順。primaryによる必要な1call確認を含むAI協調であり、Naïve単独の無介入完走はまだ主張しない。既存顧客納品が発生すれば販促より優先する。追加画像/新signup/新しいメール送信/他channel変更/環境変数変更は行わない。


#### v13の最小修復範囲（適用前）

失敗の根拠はCTA runのevent23/26 quote167195/173404microUSD、event29 budget.exceededのparam budget.cap_micro_usd/message the agent's budget cap has no room for this call。task予算400000に対し実費24161で止まったため、単なるtask実費枠消費ではなくagent月capの見積り拒否とproviderが特定している。native publishは0。cancel→GET cancelled/pending0、過去の公開post/明細/本人資格情報は保持済み。

旧順序は実依頼獲得→自然run→メール診断、新順序はこの月cap/CTA修復→実依頼獲得→自然run→メール診断。既存月残枠では公開/自然runの次callも拒否され得る実測依存を解消するためであり、需要0を理由とする頻度増加ではない。現在cursorはv13 source/受入/review/main反映、未完の1案内の公開。別のloop/他owner/既存外部effectは中断しない。

所有変更はconfig/naive-browser-company.jsonのbudget.cap_micro_usd=7000000と、Postiz段落2文の最小訂正、config/naive-browser-company-deployment.jsonのagent_version=13と月7の説明、当plan/統一SSOTだけ。文面は最新schemaに従いXの公開原稿/CTAへURLを入れず、GitHub商品名・repo/issue番号等で場所を伝えること、同テーマだけで重複扱いせず対象/本文の一致と実postidを照合すること、同作業で取得済みの対象/原稿/照合結果を再利用し不足する範囲だけ読むこと。モデルが判断し、regex分類/新しい判定wrapperは追加しない。

model/11allow/default deny/browser options/Identity/wake=false/cron/task1は不変。追加資金移動/カード/支出signer/他サービス設定変更無し。budget上限は実費/利益ではなく最大許容枠。原本v12との構造差分で変更範囲をassert、JSON/diff検査・既存関連CI・fresh read-only reviewを行い、main固定SHAから同owner agent/deploymentへ適用→全source fieldsの公式GET一致→前の未完CTAのみ新有限runで検証する。既存の停止runは再開せずcancelledのまま。v13適用と実公開が確認されるまで実施済みとしない。長いMac loop suite/新scheduler/新依存は対象外で、外部REDはこの本物のbudget.exceeded、GREENは同目的のnative完遂/公式表示で測る。

### v13反映と未完CTAの公開結果

- 固定main `584363f5b03e738647e65286f77264bcff069219` の設定2ファイルはworktreeとbyte一致。agent PATCH後GET v13/全field一致。deploymentへの初回全設定PATCHは400 `unknown body field: agent_id`（req_hgyb801t2z0xs8vp2w35rgta1a）で拒否され、agent更新後の保存済みdeployment-prepatch-v13.jsonもagent_version13で、旧版12のままではなかった（後の照合で解釈を訂正）。初回拒否でinput_templateの更新は未反映だったため、変更対象のagent_version/input_templateだけをPATCHし、全source fields GET一致で反映を閉じた。SDK自体の不具合とはしない。
- native finite `ses_w3j66dykg8c5dqt9mpg6hw6t97` は同文投稿0を公式一覧で照合後、本人Postiz1callでpost `cmw0hy0a502o6t807zkekfsy1` を作成。公式PUBLISHED/error null、https://twitter.com/diceai0/status/2117552389045563522 。保存HTML230文字は実送信payload完全一致。公式X oEmbedは213文字原稿の3段落それぞれが一致し、段落間空行のみ単一改行表示。URL無し検索案内で旧投稿のCTA欠落を補った。旧投稿は削除/再送していない。
- 初回nativeはprovider公開確認前に台帳をpublishedと記したため、その自己申告を証拠にせずprimary公式一覧とX表示を取得。primary followup1回でreceiptを本人journalへ結合しwrite/read、parsed JSON argsはexpected payloadとdict完全一致。公開callの途中confirmationは0、human操作0。ただし原稿/事前照合/公式readback/receipt結合はprimary AIが担当し、Naïve単独で全工程無介入とは呼ばない。
- 初回end_turn26934microUSD、receipt結合を含む有限run合計42835microUSD。cancel→GET cancelled/pending0。最新agent累計5865832microUSD、別SDKbrowser診断3334microUSD。全社費用/利益ではなく、顧客/第三者入金は未確認。証拠はprivateのagent/deployment-readback-v13.json、pilot-cta-v13-native-events*.json、pilot-cta-v13-provider-readback.json、pilot-cta-v13-x-oembed.json、pilot-cta-v13-final-native-record.json、pilot-cta-v13-cancel-readback.json、spend-after-cta-v13.json。
- PR #9145統合時は関連checks/TruffleHog/gitleaks PASS、無関係Loop control2件はpendingで全PASSと主張しない。定期deployment次回2026-11-03T12:00:00Z/JST21時、自然runは未実証。順序は前節どおり修復完了→実依頼/納品/入金→自然run/録画→inbound→採算/phone-only/移植。投稿増加や内部送金を売上の代用にせず、同じ確認・募集を反復しない。

### 受注待ちと並行するcontext有無のpolicy切り分け

目的は本人agentmailでの登録を妨げるsealed browser入力の境界特定。以前のSDK実測はcontext_name付きComputerでallow_writes/allow_extract=trueの保存・ready readbackにもかかわらずloginがread-only、screenshotがextract権限不足。保存contextに伴うruntime policyが原因なのか、Computer API一般でoptionsが失われるのかは区別できていない。次はcontext_nameを省くことだけを主要な差分とし、専用Computer1台を作る。dev.toのみ許可、allow_writes/allow_extract=true、persist_context=false、TTL3分・操作timeout60秒。既存本人credential login:dev.toと実login画面だけを使用し、sealedlogin最大1回・screenshot最大1回、新signup/新vault/新credential/メール送信は0。passwordを取得・表示・type/actに渡さない。Computer作成/ready/browser options、各HTTP status/requestid/経過時間をprivateに保存し、browser close→Computer destroy→GETでcleanupを確認する。最大診断枠0.02USD、既存agent/deployment/capと他ownerのstateは変更しない。

判定は、context無しでも同じread-only拒否なら保存context単独原因という仮説を棄却し、context有無で変わるならその差だけを次の修正候補にする。200/performedをaccount loginや登録完了とは呼ばず、公式画面も照合する。文書上のsignup自体には確認停止があるため、未観測の無介入登録を約束しない。実依頼/自然run/inbound待ちの順序は変更せず、同じ受注画面や募集を繰り返す代わりの独立診断とする。

並行した現在readback: v13のdeployment runsに新しい起動は0、最後は05:30Zのcancelled run。本人email inboundは公式0件。agmsg lmにcodex-naive-browser-1103を登録しturn受信で既存codex-money-printerへread-only手順照会を送信。相手のpeekはtmux server無し・pane取得不可（exit12）で、送信を着手証明にしない。Reasonへの既存Muse照会は返信未確認。既存webはGoogle identity/メール報告、古いbrowser onboardingはretired。既存DO self-spawn sourceもNaïve互換やphone-onlyの証明ではなく、他ownerのflowは変更しない。

結果: 専用Computer `cmp_01a1a0d2e4de7c0fb167ba8d4446df71` はcreate202/ready200、保存browser flagsはallow_writes/extract=true、context_name無し/persist=false。gotoは200/performed true（6.334秒）、browser GETでcontext_backed=false/context_id=null。既存credential sealed-loginは403 read-only/param allow_writes（req_bkrk4y2r9hertgjcea56f7xhes、7.417秒）。保存context単独原因という仮説を棄却する。screenshotは200/performed true（fil_6aa5mcz4er63k5eqkyawzbsb2p）でprimaryが実画像を開き、DEV login formのemail/passwordが空・未ログインを確認。context無しのscreenshotはextract guard対象外なので、これをallow_extract伝播の成功証明にはしない。

browser close200/closed、Computer destroy200→GETdestroyed、稼働課金資源は残していない。公式balance 25716972→25715305microUSD、差1667microUSD（約0.001667USD）、SDK browser診断累計5001microUSD。agentの月7USDを変更・迂回せず、既存native設定・他owner・signup・vault・メールは不変。private証拠はbrowser-contextless-boundary-verification.jsonとprobe4-*.json/probe4-login-cloud.jpg。次は同じloginを反復せず、Computer API側の実行policy伝播とnative helperを別境界として扱う。DEV登録dispatchやnative helper一般の原因まで、このSDK結果から断定しない。

### 専用メールによるpasswordless登録の限定実行

目的は利用者個人のGoogle/mail/passwordを使わず、Naïve本人のmailで新規所有accountと受信認証を実証すること。DEVの同じsealed入力失敗は繰り返さず、Substack公式helpが提供するemail verification code/login linkを使う。一次資料 https://support.substack.com/hc/en-us/articles/360059542452-How-do-I-log-into-my-Substack-account 、signup https://substack.com/signup 、Terms https://substack.com/tos 、Publisher Agreement https://substack.com/pa 、Content Guidelines https://substack.com/content を確認。組織利用・正確な登録情報・非なりすまし・オリジナル記事・opt-in/no spamを守り、単なる外部商品広告のpublicationにはしない。今回はaccount作成とprofile/readbackまで、記事publish・課金・Stripe接続・購読/連絡先importは0。

既存agent/deployment v13を変更せず、専用Identity/mail/contextとnative browser/emailだけで有限run最大0.35USD。Google/Apple/GitHub/OAuth、個人account、password取得/転記、業務script/APIは使わない。専用credential SSOT exactservice naive:browser-operator:substackとbrowser registryに既存登録無しを確認済み。新accountはAniccaの組織用途BusinessRun AIとして正確に登録し、無料mail-codeを最大1回要求。既存の本人inbound baselineは0、email.readは新着確認最大2回。認証メールのcode/linkは対象substack.comの通常画面にだけ使用し、chat/repo/journal/一般logへ残さない。取得イベントの保存も認証本文・秘密付きURL・入力codeを除く。

本人mailでのログイン後画面/profile保存をaccount成功の根拠とし、単なるcode要求画面やtool doneは成功としない。新規取得したaccount metadataはcanonical SSOTへ保存、sessionはNaïve context内に保持。個人情報/phoneが必須で既存本人データに無ければ捏造せず不足境界を記録する。原稿/公開・売上は今回未実施。UIの実状態・到着messageid/時刻・確認範囲・費用をsecret抜きで本人journalにwrite/read、有限session終了/cancel→GETまで行う。全体cursor（実依頼→納品→入金）は変えず、メール/登録という明示未完項目を受注待ちと並行して進める。

実行1結果: native `ses_jht7qev3r27smr3g0b969c9b83` は同formにtype textを複数回呼び、成功応答後もevent61の実画像でemail空/terms checked/Continue disabled。primaryも画像確認した。code要求成立・Substack dispatch・本人inbound・accountは未確認、email.readは観測したtool eventsに0。task0.35USDに次call quoteを収容できずevent202 budget.exceeded/param budget_micro_usd、公式statusのconsumed186237microUSD（個別session.usageの部分値との合算禁止）。primary補正messageは402で受理未確認、補正が実行されたとはしない。budget_paused原本保存後cancel→GETcancelled/pending0。秘密code/linkを保存せずeventはmetadata/hashのみ、原稿/課金/公開は0。

次の最小比較: 同じ本人mail・同じ/signup・同じv13の新finiteで、typeの代わりにbrowser.actによる実email inputへの入力1回を試す。submit前に表示値とContinue有効を照合。反映しなければ同じクリックを繰り返さずwrite/readで終了。反映しcode要求を進める場合も、前runのcode要求不明を補わず、現在画面と本人新着を先に確認し、今回診断全体のcode要求最大1を維持する。新finite上限0.30USD、前実費0.186237との最大合計0.486237USDとなるため、診断全体枠を0.35→0.50USDへ明示更新。月7/task1は不変。理由は実費だけでなく次call quoteを入場時に必要とする実測と、同selector type成功応答が実入力を証明しなかったためであり、signup連打/上限自動拡大ではない。code/tokenを出力しないことと公式画面で成功判定する条件は不変。

解釈の訂正と次の観測: 先の「画像空欄＝実入力失敗」という断定は取り下げる。公式Browser guide https://usenaive.ai/docs/computer/browser のsaved-login read policyはextract/observe/links/screenshotがemail等をredactすると明記し、sessionが入力待ちにpauseするとbrowserを閉じるとも説明する。今回のcontext付き画像/抽出だけでは、未入力と伏せ処理を分離できない。画像の空欄/Continue無効自体と登録未確認は保持するが、入力破壊・maskによるDOM変更を既知原因にしない。

act比較run `ses_rwvbs16frhgxev1ppekrjxja41` は初回email.read→signupへのgotoでread_people cardが発生、primary AIがexactcall1件をallow。次の「本人emailへ入力、submitしない」actでもread_people cardが発生し、exactcall1件をallow。再開actはcould not perform、次画像のみ取得し診断mdを書いてend_turn。実費63746microUSD。入力待ち前後のpage lifetimeと入力方法が交絡しているため、これをactの一般的な入力不能の証明にしない。human介入0、primary AIのcall確認2件。

今回のauth診断総枠0.50USDの残りで、次の比較は最大0.25USD（先行実費186237+63746との最大計499983microUSD）。先に画面からemail/Continueの実selectorを取得し、type本人email→既知Continueを1回クリックの間にextract/observe/screenshotを挟まない。code要求の実UIと本人受信を結果の観測とする。メール・個人情報を観測のために公開せず、秘匿値を返さない。新規signupを増やすのでなく同じ専用Identity/mailの同じ通常flowを検証し、既存のaccount/code成功を推定しない。追加の支払/上限変更/公開なし。同じ失敗を観測無しに繰り返す比較にはしない。

文書差分: API Browser pageにはsignupはperson確認とある一方、最新Tools page https://usenaive.ai/docs/capabilities/tools はask_actionsの既定signupを明示し、allow下でask_actionsに無いactionは実行されると説明する。今回設定ask_actions=[]を維持し、signupに必ず人間が必要とは断定しない。観測したread_people cardは別に記録し、未公開server内部の発生原因/解除設定を推測して変更しない。

直接submit比較結果: native `ses_rr4bfjqv04d265yw2sybcn6mxm` はobserve由来selectorのtypeがerror（event34）、fallback actの後にもscreenshotを挟み、意図した「中間read無しtype→Continue」は完遂していない。このrunからredaction仮説の真偽を判定しない。code要求成立・本人受信・accountは未確認。event96 budget.exceeded/param budget_micro_usd、status consumed86613microUSD、primary steering messageは402で拒否。原本保存後cancel→GETcancelled/pending0。先行3runの実費合計336596microUSD。

### 登録診断の残枠内で行うmodel比較

同じ指示を守らないケースが続いたため、同じdefaultの失敗反復を止め、モデルだけを変える比較を最大1回行う。公式GET /modelsの全366件をEOFまで確認し、literal id `z-ai/glm-5.3-flash` のimmediate対応を確認。価格/品質の優位はカタログから推定しない。live spanと結果を見て判定し、1例をbenchmark能力値や一般優位にしない。

SDKと現在API docsはcreate時model overrideを提供せず、sendからのmodel指定は可能だが既存3sessionはcancelled terminalで再利用しない。新agent/Identityを増やして月capを迂回する代わりに、専用既存agentへconfig/naive-browser-company-model-probe.jsonのmodel-only PATCHを適用する。expected_version13→候補v14、他source fields完全不変、deploymentはv13固定のままで触らない。patch/restoreはreview済みmain固定SHAから適用する。候補v14で同じ最新の登録指示をfinite最大160000microUSDにして1回実行。先行実費との最大合計496596microUSDで既存診断総枠0.50USD内、月7/task1も不変。入場quoteが収まらなければ新runを増やさず結果を記録する。

終了/失敗/入場拒否のいずれでもfinite停止/cancel/GETの後、config/naive-browser-company-model-restore.json（to_version13/expected_version14）からrollbackし、履歴を消さず新versionで元の全source fieldsをGET一致させる。production deployment pinned13/cron/Identity/11allow/既存外部effectは不変。登録成功でも直ちにmodelを本番昇格せず、raw code/linkは保存しない。今回の変更はNaïve runtime比較だけで、Codex UIの選択modelは変更しない。署名済み画像・inbox本文・code・private URLをrepoへ置かず、結果/費用/未達/現在cursorを正本へ戻す。

### model比較前の復元とdeployment pinの正確な仕様

PR #9152/main `650d5a668e9a89a27668c9887ba56ea7683d5198` のmodel-only PATCHはagent13→14となり、他の全agent fields不変。ただしdeploymentも13→14へ更新されたため、同一snapshot比較assertが検出してsession createより前に中止。GLMのinference/session/性能測定は0で、比較済みとはしない。version13へのrollbackでagent15（全元source fields一致）となり、deploymentも15へ追随したため、明示PATCHでdeployment13へ戻し全source fields一致。新deployment runは0、次回12UTC。private passwordless-model-{baseline-agent,baseline-deployment,patch,candidate-readback,deployment-check,restore,restored-readback,deployment-after-rollback,deployment-restored-readback,deployment-runs-after}.jsonが根拠。

一次資料 https://usenaive.ai/docs/api/deployments は「pinが置換される現在版を指す場合は更新/rollbackの新versionへ移動し、古いversionへのpinは残る」と明記。vendor bugではなくprimaryのpin理解不足だった。agent更新全般が全ての古いpinを動かすとの一般化もしない。古いprepatch-v13の記録にあった「deploymentは旧版のまま」も保存済みGETで13だったため、本節と該当箇所で訂正する。

現在agent15/production deployment13となり、比較candidateを適用してもdeployment13は古いversionとして固定される条件が整った。比較artifactのexpected_versionを15→候補16、restoreをto_version15/expected16へ更新する。model以外の全agent fieldsとdeployment全fields不変をGETで確認して初めてfiniteを作成し、不一致なら作成せず復元。候補16のfinite上限160000microUSD、既存3run実費336596との最大496596は不変。終了/入場拒否/失敗ならfinite terminal確認後、復元artifactで元のv15内容をcloneして新version17とし、全source fields/production deployment13のGET一致で閉じる。新modelの価格/画像対応/品質は未確認で、比較結果前に昇格しない。Codex UIのmodelは不変。

現在cursorは実第三者依頼→公開納品→29USDC receipt/費用で変わらず、本人登録/inboundは独立の未完項目。先行3finiteは全cancelled/pending0、runtime.jsonはagent15/production deployment13を区別。担当累計6217550microUSD、API診断browser累計5001microUSDは別計測。未測定増分を各componentや利益へ帰属しない。


### model比較の実測結果と復元完了

固定main `9b385a50029554ccbdc14a038286e83518edad98` のmodel-only probeからcandidate16を適用、agentのmodel以外のsource fields不変・deployment全snapshot不変/13をGET一致して有限session `ses_65ehm42mdnpf0at373sx1kf494` を作成した。20 model spansのresolved_modelは全てz-ai/glm-5.3-flash、tool started20件、screenshot0/email.read0。quoteは約0.003USDだったが、同じ条件の完走比較でも画像対応測定でもなく価格/能力の一般優位を主張しない。

実UIはevent40でThis email is already registered with Substack.、event48でSign in to Substack/Email/Continue/Sign in with passwordを返した。email欄は[REDACTED]と明示され、空欄画像から入力失敗を断定した以前の解釈を再確認して訂正する。already registeredは同じ専用メールの通常sign-inへ進む根拠であり、本人認証/account所有の証明ではない。以後は/signupの再送や別メール追加ではなく通常email-code/login-linkを使う。最終確認メールdispatch成立は未確認、root本人messages readbackも0/EOF、accountはnot_verified。SSOTへ未取得accountを成功登録しない。

event128 budget.exceeded/param budget_micro_usd、event131 idle/budget_paused。公式session status consumed166809microUSD、設定ceiling160000microUSDに対し6809超過、先行3run336596との計503405microUSDは診断総枠500000を3405超過する。設定capがhard actual上限と証明されたとは言わない。session.usage26809と公式status166809の差を未照合の費目へ帰属せず、それぞれの範囲を保持する。追加入金/上限変更/診断再実行は0。budget_paused原本保存後cancel→GETcancelled/pending0。

main固定restore artifact（to_version15/expected16）を適用しcurrent17、元config/naive-browser-company.jsonの全source fieldsを公式GET一致。production deploymentはbaseline snapshot全体と完全一致/13、cron/input/Identity/cap不変。runtime.jsonもcurrent17/production13を区別。private証拠はpasswordless-model-isolated-{source,baseline-agent,baseline-deployment,patch,candidate-readback,deployment-check,restore,restored-readback,deployment-restored}.json、substack-passwordless-model-{session,native-status,pre-cancel-status,cancel-readback,event-metadata}.json、substack-inbound-metadata-after-model.json、spend-after-passwordless-model.json。authイベントのcode/本文/秘密URLは保存せずmetadata/hashのみ。担当累計6390644microUSD、別SDKbrowser累計5001microUSD、全社利益/売上ではない。

現在cursor/全体TODO順は変わらない。実第三者依頼→納品→入金の前に、個人Googleを再導入しない。公開英語記事のCurrent Stateが旧v9/商品draftのままなので、公開済みpilot/CTA・送信方向の実配送・今回の失敗境界・未達を修正する。過去probe値は履歴として保持し、広告/同文募集の追加送信はしない。次の自然deploymentは12UTC、本人受信/通常sign-in・録画・phone-only・黒字・10K/移植は未達。


公開記事反映: BusinessRun Bench PR #4はmain `5054f196abb564ef168646195a2f6ac83e7e1124` へ統合。ARTICLE.en.mdの固定main raw30264bytesとreviewedローカル本文がbyte exact。Current Stateをv13 production/current17復元・月7/task1/wakefalse、public pilot/CTA、外部送信配送、Substack未認証、cap実費超過、単価capacity上限/売上未確認へ更新し、過去測定値は保持した。URL https://github.com/Daisuke134/businessrun-bench/blob/5054f196abb564ef168646195a2f6ac83e7e1124/ARTICLE.en.md 。新SNS送信は0。private current-english-article-main-readback.jsonが根拠。

独立fresh read-only検証はpublic be51f54/private8c52deb2eaにSHIP/Blocking0。session thread limitとAGMSG plain terminal起動失敗後、モデル指定無しの有限codex exec/read-onlyで実データ比較を行った。current-results-independent-review.txtをprivate保存、先行3run合計はprimaryが各cancelled公式readbackから再照合して336596と一致。AGMSGの送信を稼働証明にせず、本人inbox/Reason返信はいずれも新着0。全体goal active、現在cursorは実第三者依頼と有償納品/receipt、残TODOは「現在の実行詳細」に一本化する。


### Capafyの同一Publisher内接続を優先する

次の目的は既存の収益手順をNaïve browserへ再利用すること。取得済み一次資料 https://capafy.ai/publisher-agreement/ の2.9は同一controlのPublisher Accountを原則1つ、2.7はアカウント非譲渡、2.5は認証料0.99USDとする。メールやVMの追加を別の法的Publisherや売上増加の根拠にしない。MAIL03の旧「本人mailで新規Capafy登録」は、この既存Anicca Publisherとの関係を無視して実行しない。個人Googleが一般利用者に必須という意味でもない。

現在owner daisuke/terminal（Muse）はReason公式list_teamでidle/tierturnとして存在するが、受付/着手とは別。既存Publisher内の公式team invite/agent専用email認証/正式権限の有無と実画面をread-only照会、message6TKH6DR7DA2ZKPWZ3NM4WQT9CAはqueued/repliedfalse。既存accountの変更・reset・credential転記・公開商品/収益変更は依頼しない。返信を待つ間は公開pilotの第三者依頼と自然runを維持し、追加の重複signup/決済/Naïve診断消費は0。通常mail認証が技術的に可能であることと、そのサイトのPublisher権限を取得したことを分離する。

この追加確認は全体TODOのreorderではなくMAIL03の具体化。現在cursorは実第三者依頼→公開納品→29USDC receipt/費用、自然run12UTC/本人inbound・認証/録画/phone-only/採算/移植は未達。最後の公式open trace-review依頼一覧は0、agmsg/Reason新返信0。記事はpublic main5054f196へ反映済み、実売上/10K/月黒字/無介入完走を断定しない。


### Capafy無料user認証の実測と終了

既存Publisherを新設せず、無料user認証だけをnative finite `ses_7se2dh2qqgxssweha4mtf1z081` / current17で実施。有限cap0.30USD/月7/task1内、Publisher申請/0.99USD/有料/Google/既存商品/既存owner変更は0。初回Haikuは16tools後にmax_iterations、その後quoteが残finiteに収まらずbudget_paused/134582microUSD。公式agent/session schemaにmax_output_tokens設定は確認できず、proxy trace用の同名fieldをagentへ流用しない。公式catalog/以前の画像確認に基づき、同sessionのsend model overrideだけをGemini2.5FlashLiteへ変更、本番agent/deploymentは不変。これを同条件のモデルランキングにしない。

email.inboxes成功、直接click4回のcould not completeを保持、act経路からemail入力まで進む。email.read169は0件で、コード送信成立は未確認。以後read_people確認が出て、primaryは元の依頼範囲とpayload/本人emailを照合しContinue/goto/一括act/signupの4callだけscope=call allow、人間確認要求0・sessionwide grant0。Continue再開act208は失敗、observe213=[]、入力待ちpauseのpage喪失が交絡する。navigationから同意/Continueまで含む一括act280はcredential-shaped instructionとして拒否。文言の隠蔽/符号化で迂回せず正式signupへ進む。

正式signupはservice capafy.ai/url capafy.ai/専用本人email/本人Identityだけを照合して1回実行。実行前vaultのkey/hostで既存Capafy credential0/EOFを確認し、他のcredentialは置換しない。新login:capafy.ai参照1件が専用vaultに生成されたことを公式metadataで確認、canonical private Credential SSOTへcredential_generated_account_not_verifiedとして直ちに保存した。値はmodel/chat/repoへ出さない。signup318はthe browser could not perform that instruction、observe321はTerms linkのみで本人画面を実証せず、helper成功/登録済みとは扱わない。今回の単独結果からメール未所持が原因、Capafy一般で登録不能、または全helperの共通原因とは結論しない。

終了指示後nativeの最終write368/read371は1580bytesで完全一致、秘密形状無し。end_turn→cancel→公式GETcancelled/pending0、実費243640microUSD。agent累計6634284microUSD、SDKbrowser累計5001は別、利益/全社費用ではない。本人inboundは公式0/EOF、コードdispatch・無料user認証・Publisher・売上は未確認。agent current17/元Haikuの全source fieldsとproduction deployment13/全source fieldsは公式GET一致、次の自然run12UTCは未検証。private capafy-free-user-auth-{event-metadata,pre-cancel-status,cancel-readback,journal-check,generated-credential-metadata,final-readback,boundary}.jsonとspend-after-capafy-free-user-auth.jsonが証拠。

追加の登録/送信/枠拡大を反復せず、既存Publisher内の正式team権限のowner回答を確認する。公開pilotの実第三者依頼→納品→29USDC receipt/費用、自然run/実録画、phone-only/採算/移植という残TODO順は不変。PR #9158/#9159の後追い全15checks PASSを確認、公開記事main5054f196のbyte一致は保持。今回の追加は運用結果docsのみで新しいruntime設定/loop/API実装は無い。


### 受注待ちと並行する英語記事の自社ブログ掲載

目的は既存の英語調査記事をGitHubだけでなく自社aniccaai.comの既存Manager blogへ公開し、読者が実測と公開pilotへ辿れる入口を作ること。実売上/認証/録画を記事公開で代替しない。現在GitHub open trace-review依頼0、Reason/Slack返信0、production13 enabled/次12UTCで実run未観測。新規signupや費用試験は反復しない。既存phone入口はapps/life-manager/lib/web-auth.jsのhasVerifiedGoogleIdentityを必須としており、個人Google不要の新利用者入口は別設計が必要。既存Google認証の緩和や他ownerのUI変更は0。

自社ブログは既存apps/landing/manager-blog adapterとreviewed publication manifestを再利用。所有は新規英語slug manager-naive-autonomous-companies-enのsource/package/media1点、manifestへの同記事追加、当plan/統合SSOT/BOARDのみ。公開済みEnglish記事5054f196を元に、相対リンクを公開先へ解決し、Capafyの実測未認証/費用だけ追加する。画像は既存公開済みの本人cloud編集失敗画面を実見してhash固定、生成/加工しない。比較対象の勝ち筋は記事中のNaive公式9evalの条件・実測・図・根拠という構成。記事自体のtraffic/売上という公開成果指標は取得できず、その穴を残して1articleだけで試す。自社の計測は既存site指標と第三者依頼/receipt、未測定を成功へ変換しない。

canonical contentをreview/関連checks/mainへ統合後、publishing repo anicca-productsの最新mainから専用worktreeを作り、既存2workflowのMANAGER_BLOG_CONTENT_REVISIONだけを固定canonical SHAへ更新する。renderer/install hash/他記事/決済/既存配信は変更しない。関連checksと通常build/deploy後、live記事本文・画像hash・public release.jsonのrevisionを公式readbackして完了。preview/local buildは公開成果としない。mainの最新記事を落とす古いcontent pinへ戻さず、並行更新時は最新のreview済みbundleを含める。

録画経路の独立診断: Computer Use inventoryはMac appsあり/browser0、browser registryにNaive route0。指定cua-driver SKILLはlocal2roots/cacheおよびai-config main treeで見つからない。Naive live-viewはdashboard-onlyの秘密URLで、録画APIと同一視しない。録画未完を保持し、他者のChrome/profile/sessionを借用しない。新規Mac UI操作を追加せず、ブログ掲載という独立項目を進める。


### 英語記事の自社ブログ公開完了と本人inboundの1通検査

canonical PR9162は全16checks PASS・fresh read-only SHIP/Blocking0後main982fb15e47286af910728eddb08b51912f301693へ統合。publication76記事/44媒体、既存75/43 entry完全保持、source/package/manifest本文一致、既存adapter12tests PASS。publishing PR849は2workflowのcontent pinだけを982fb15eへ更新し、build成功後main e5cff3c0c5d3a439f08575c8020562e37d3898f5へ統合。renderer d569400は不変。後続のmain014262a5はe5cffのdescendantで、実公開provider deploy6ae9c8b0c529125fd14c707a/ready、GHA41629113267 success/既存money-path smoke successを確認。

実URL https://aniccaai.com/blog/manager-naive-autonomous-companies-en の取得本文33332bytesにtitle/Capafy未認証/0.243640/累計6.634284/売上未確認の要点が存在。public release.jsonはcontent982fb15e/記事hash888bd14a5cd08497d647c53dbbccf7435d133763208aabe1393cc411776459b6/76記事、画像HTTP200/hash1f06d359be84a6adcdaaf9e5f847ddfeb874c3fc0d181bb8113b7b1fb8eb0561と一致。記事の自社blog公開は完了、実売上/受注/登録/連続録画とは分離する。private blog-live-publication-readback.jsonが公式readback。旧cua-driver不在とbrowser0は録画経路の未完条件で、Mac/他者Chromeへ入力しない。正式browser_sessions APIはclosed含むと記すが、実session Computerとagent Computerは同一cmp/履歴0であり、別Computerを見ていたという仮説は棄却。次は実稼働中の履歴と照合する。

Substack最後のobserve106はCreate your account、113はSign in to Substack/email/Continueで、code送信画面ではない。したがって未着をSMTP受信故障と断定しない。現在の初期課題は実外部dispatchを伴う受信検証。private SSOTのresend-life-manager-productionに設定済み会社from_address/送信専用keyを確認。GET domainsは401/restricted_api_key/only send emailsで、失効ではない。権限拡大・キー作成・新サービス契約は行わない。

次の1通はこの設定済み会社送信元→同じNaive本人inboxだけ、件名/本文にDIAGNOSTIC-NOT-ORDERと固有nonceを付ける。顧客注文/認証コード/指示ではないことを明示、秘密・個人データ・払出情報・リンクは0。最大1送信・固定Idempotency-Key、timeout/不確実時は再送せずreceipt/inbound readbackを調査。acceptedと受信を分離し、届けば同nonce/送信元/受取Identityのmetadata照合、provider raw本文や認証秘密を一般logへ保存しない。専用inboxのwakefalseを保持し、この検査で新agent/cron/枠/既存担当/販売済商品を変更しない。既存送信サービス内の1通であり、請求費用は未計測なら0とせず、新規契約/top-up無しと区別する。

全体goalはactive。実顧客依頼→納品→29USDC receipt/費用が現在cursor、本人inbound検査と自然run12UTCを並行する。既存deploymentはno-order時に終了する限定pilotであり、自律的な顧客獲得/学習のseller loopはまだ完成していない。今後これを自所有configの改善対象とし、他者返信待ちだけを阻害理由にしない。phone-only入口/採算/移植/compute自費/10Kは未達。

### 本人inboundと定刻runの追加観測

既存Resend送信専用キーから本人inboxへの検査は1通だけPOSTしHTTP200/accepted、provider id `01a1a148-21fd-7247-b412-96935d0fa703`。固定idempotency/事前attempt fenceを保存し再送しない。2026-11-03T12:05:48Zの公式identity messagesは0件/has_more=falseで、受信成功ではない。送信側の単一message GETも401/restricted_api_key/only send emailsで、accepted以降の配送状態はこのキーでは見えない。キー失効や配送失敗とも断定しない。inboxのraw公式GETはactive/wake=false/同Identity/同agentで、前節のwake=falseをfresh確認。Auto-Submitted付き検査は非注文で、届いても通常mailによるwakeや顧客獲得の証拠にしない。

12UTC予定を過ぎた12:05時点でもdeploymentはenabled/schedule_status=scheduled/next_run_at=12:00のまま、runsは05:30のcancelled手動run1件だけ。agent別sessions一覧の最新も10:44のcancelled試験で、新しい自然runを確認できない。公式deployment docsはscheduledをclockが監視する状態と定義するが、この遅延原因は未特定。cron/pin/Identityを変更したりmanual runを自然実行と数えたりせず、時刻・公式runs・sessionを合わせて追う。担当spend公式GETは6638031microUSDへ増加（前回+3747）。自然runが無いのでこの差分を自然run費用へ帰属しない。別SDKbrowser5001microUSD/全社利益/売上とも分ける。

証拠はprivate `inbound-one-mail-{send-receipt,sender-status,receive-readback-latest}.json`、`natural-1200-{deployment,runs,spend,session-summary}.json`。Reason新着0、Slack既存照会threadも新返信無し。全体goal active、外部返信待ちと別にseller loopのno-order早期終了を次の自所有改善対象とする。

### no-order時のseller loopを既存deploymentへ追加する

目的: 公開依頼ゼロで即終了する自所有の不足を直し、受注対応と並行して顧客獲得を進める。対象は既存agent17相当/production pin13のdeployment input_templateだけ。新agent/tool/credential/cron/予算/サイトaccountは追加せず、production既定modelも変更しない。既存finite会話のmodel指定補正は後述の実測budget境界に従う。未処理依頼があるときの既存納品・支払照合を優先し、その契約は不変。

依頼ゼロの場合は本人Computerのseller-state.jsonと直近の許可済みPostiz投稿を読み、既に調べた証拠と公開済み原稿を照合する。本人browserでAI agentのtrace/debuggingに関する公開の需要を最大1件調べ、出所URL・確認した困り事・商品との適合・次に試す提案を記録する。公開一次資料が得られなければ需要を捏造せず、取得失敗と次の最小の確認だけを残す。競合の有料planや星数だけを購買需要の証拠にしない。

新しく確認した具体例があり、過去募集の言換えでなく顧客が使える新しい知見を含む場合だけ、許可された@diceai0へ英語の新規postを最大1件/UTC日で公開できる。最新schemaに従いURLの除去仕様を迂回せず、商品/repo名で受付を案内する。画像/動画の自動生成・DM・他者issueへの返信・他owner投稿変更はしない。事前checkpoint後の送信不明は再送せずprovider照合へ進む。seller-stateは最後の調査URL/仮説/投稿id/state/UTC日を持ち、次runで重複と費用を減らす。顧客の反応・クリック・申込・売上は公式に確認できた値だけ記録し、未取得はunknown。

順序変更: 旧「依頼ゼロ→記録して終了→外部反応待ち」を、新「既存依頼処理→ゼロなら新しい需要1件の調査→有用な新知見がある時だけ日1件の獲得実験→結果保存」へ。受注ゼロで停止する原因が自所有inputにあるためで、既存進行中effectは中断/再送しない。現在cursorはsource/main固定→既存deployment inputのみPATCH/GET一致→既存残枠内最大0.30USDの有限run1回。自然run未作成の調査は独立に継続し、手動検証を自然完走や収益の証拠にしない。完了条件はsource反映・nativeの新分岐/永続stateの実行証拠であり、投稿や調査だけを売上達成にしない。

独立read-only reviewは入力以外不変/既存契約と重複防止保持を確認したが、「需要1件」と「source1件」の曖昧さを指摘。inputを「検索結果から開く公開需要ソースは1run最大1件」へ明示し、対応箇所を再照合する。他の機能/権限は追加しない。

### 初回の標準自然runが無受注確認まで完走

12UTC予定のrun `run_8k5kfy836y4aeg0sy0gne5tvj1` / session `ses_5j5eant4wkhpyzqe8h9rav5txs` は12:09:39.435Zに作成、12:10:57.667Zにsession.idle/end_turn。deployment_id一致・pin13・同Identity、初期user inputは元input_templateを含み、付加された予定時刻は12:00:00.000Zで作成時刻と異なる。rootの手動runは05:30以降0回。以上からこのrunを定刻起点と照合し、約9分39秒の起動遅延を残す。起動遅延の原因は未特定だが「自然run未作成」は当該観測時点の履歴となる。次回は2026-11-04T00:00:00Zへ進んだ。

nativeはoffer/sample/receiver/journalの4read→本人browser GitHub goto→screenshot→journal writeの計7tools、Haiku4.5実5model spans、実費45903microUSD、pending0。tool.confirm0、primary追加入力0/confirm0、手動中断0。journal write成功eventはあるが同run内readbackは無く、次runの再読取で永続化を照合する。公式file fil_tkzekjvve2c92tmha9bd5p0qpk/122065bytesのbytes・sha256・agent/session一致を確認し、primaryも実画像で0 results/No results matched your searchを確認。これが証明するのは今回の自動起動→本人browserで無受注確認→記録まで。有償納品・第三者売上・新規signup・mail受信・連続録画・会社全体の無介入運営は未達。

公式agent累計6683934microUSD。private `natural-1200-final-readback.json`、`natural-1200-native-event-metadata.json`、`natural-1200-intake-screen.jpg` が証拠。稼働中runの設定は変更せず自然end_turn後まで待った。source seller入力の反映はこのrun後に行い、旧inputの自然run結果と新seller分岐の検証を混ぜない。

### seller入力の本番反映と有限検証の予約予算境界

PR #9164は15checks全PASS、source inputの独立reviewは指摘1件修正後SHIP。main `b4e61ec33e1519ec0ac95b4b17df3f5d4059065c` 固定sourceのbytes/hashを照合して既存deploymentへinput_templateだけPATCH、公式GET完全一致、その他全field不変。source config sha256 `bb9fd02746c950ddc0478d6f029083d9a6b8d93b4d9bfaaf94df5bac990cecc9`。pin13/Identity/cron/予算は維持、次自然run11/04 00UTC。自然runのjournalは同run/current agentのComputerを動的に引き直し、provider fs/readで6126bytes/sha256完全一致。古いcmpはdestroyed/409で、current endpointは別cmpを返す。fs/readの再起動とpauseの使用中409を観測した後、追加観測でactive session無しを照合しpause200→GETpausedへ戻した。次finiteのjournal readはoffset/limit付きでtruncation markerがあり、全file不一致/喪失と断定しない。private `natural-1200-{computer-correlation,journal-persistence-readback,readback-pause-after-idle}.json` が証拠。

有限検証session `ses_httvvkdan6wwn9wt1fchsvvnxy` は同pin13/Identity、300000microUSD枠。依頼0件画面→seller-state初期未作成の確認→Postiz postsList 67073bytes→state1405bytes保存→公開HN検索pageへのgotoまで進む。read_people確認はprimary AIがscope=callで1回処理、人間0。実需要の内容確認・新規投稿・売上は未達。Haiku8実model spans後、実費129172microUSDでbudget_paused/pending0。残枠170828に対し次呼出し予約が大きく、実費cap超過ではない。確認後の再開で42039tokensがcache_writeに入り1span53012microUSDを消費したことも記録する。投稿一覧を需要の確認より前に読む順序が、依頼ゼロでも大きなcontextを作った自所有原因である。

次の最小補正は二つ。既存finiteは上限300000/月7/task1を変えず、同会話へのsendでlive catalog掲載の `google/gemini-2.5-flash-lite` を1回だけ指定し、現在画面→残作業→state/readbackへ進める。新session/agent/入金/上限変更/production model変更はしない。catalogはimmediate対応/max_output32768を確認、価格は掲載されず安価や品質優位を未測定で断定しない。拒否なら費用/原因を残し、再作成/増額で代用しない。この変更は既存finiteの運用補正で、source既定Haikuと定期runのmodelを変更するものではない。

次回以降のsourceは、旧「state+投稿一覧→需要調査」から、新「state→需要1件→有用な新規投稿候補がある時だけ必要最小期間の投稿一覧で重複照合→投稿」へ変更する。需要が無い時の不要な大量読取を無くし、既存投稿の重複防止/日1件/送信不明fenceは維持。現在cursorは同finiteの残枠内補正、続いてsource順序修正/main反映/自然runの検証。旧のモデル変更無し契約はproduction既定を指すよう具体化し、有限補正の理由/旧新順序を本節へ記録する。全体goal active、有償納品/第三者receipt/利益/10Kは未達。

有限model補正のlive観測: Gemini2.5FlashLiteのsend202後、実model2spansでquote16181/16357microUSD、累計135016（Haiku終了点129172から+5844、モデル費用以外の増分も含む）。今回のquote低下は実測、品質優位/公平なmodel比較ではない。screenshot後の同じ公開HN gotoが再びread_people確認となり、pendingのtool_call_idは同値、現在parked_seqは110（確認eventは128）。既存の一般browser操作は委任済みであり、今回の有限会話/公開需要1件という目的を維持して、このpendingをscope=sessionで許可する。これはbrowserという同名toolの当該会話内の継続許可で、production policyや他toolを変更せず、今回以降の確認イベントと実操作を実測する。過去のcall-scope実績を書き換えず、新しいsession-scopeのprimary AI判断として別記する。全体の人間承認は0、primary AIの介入回数は0としない。

継続許可の実動差: scope=session要求は202/running/pending0で受理されたが、その後も同じURL/同じ論理tool_call_idのread_people確認が再発、parked_seq134/累計161104microUSD。したがって「以後確認不要」は未実証で、scopeが実際に更新されたこともレスポンスだけから断定しない。既にcall許可済みIDへの再回答が既存決定を再生した可能性と、read_peopleが別に評価される可能性を区別する。Geminiがgoto/screenshot/extractを並列発行し、抽出結果はRootWebArea/scrollable htmlのみという依存順序の不足も観測。次の1probeは同じ既存finite内で、古い保留操作を新指示で置き換え、公開HNホームの実際の導線を順次観測する。新しい論理callが確認になる場合だけ、その最初の回答をscope=sessionで処理して結果を観測する。同じ空画面/同じ検索URLの反復やさらに確認の無限再回答はせず、未解決なら実測境界をstateへwrite/readして有限を閉じる。需要/新規投稿/売上は依然未確認、上限は不変。production sourceにも同じbrowser操作の依存を直列にする1文だけを加える。

### seller有限の終了結果とv18の実行枠修復

有限は26tools、Haiku実8spans/Gemini2.5FlashLite実13spans。保存seller-stateのwrite207/read238は1695bytes・sha256完全一致。journalは旧内容のreadのみで、新しい追記/write完了とはしない。end_turn後cancel200→公式cancelled/pending0へ閉じた。primary AIの明示followup4送信/確認回答3（call1/session2）、人間0。tool.confirmは計5回、新規投稿tool0。公開HN検索の画像はprimaryも白一色を実確認。新logical callへの初回session-scope許可でも次のtypeがread_people確認となり、単なる同IDの決定再生だけでは説明し切れない。pin13のimmutable version GETもbrowser permission=allow/ask_actions=[]/allow_writes=true/allow_extract=true、source比較対象fieldに相違無し（name/harnessはversion object非返却）。現SDK0.10.0のconfirmTool型もscope call/sessionを受け取るが、read_people専用fieldはなく、公開docsにもこのflagの説明は未取得。backend全体の不具合と断定せず、許可の継承/独立した確認条件を次の診断対象にする。

費用は`GET credits/spend?session_id=…`で187824microUSD、台帳30件/has_more=falseの符号反転合計も187824と一致。内訳はbrowser45001、input12657/cache_read15489/cache_write103542/output11135/reasoning0。最終session GETのconsumed171158と最後のsession.usage151158も原本を保持し、どちらも台帳総費用へ置換しない。差をmodel費用や利益へ勝手に帰属しない。private `seller-finite-{state-exact-readback,terminal-readback,credits-ledger,pinned-version-permission-readback}.json`、`seller-finite-spend-readback.json`、`seller-finite-hn-parallel-screen.jpg` が証拠。登録/本人受信/需要/有償納品/第三者売上/連続録画/全社無介入は未達。

予算の実測修復: 担当累計6892309、現月7USDの残107691は既定Haikuの直近予約167076以上に届かず、次の自然runも入場できない。公式live残高24693408microUSDを確認し、追加入金せず同じ専用agentだけ月7→8USDへ上限を1USD追加、task1USDを維持する。新agent/新account/他owner/cron/Identity/tool/既定modelは変更しない。全33sessionsを公式全pageで確認し、running/queued/pending/再開し得るbudget_pausedは0、旧自然runのidle end_turnは維持。current17にexpected_version17でbudgetのみPATCH→version18→全source fields GET一致、古いproduction pin13は自動追随しないため同deploymentを明示18へ更新する。inputは不要な投稿一覧読取の後回しと同browser依存操作の直列化を同時にsource反映し、main固定からのみ適用する。

判断: 既定Haikuを維持し、実測予約不足だけを既存credit内の追加1USDで解消する。bestは実依頼に進むこと、baseは次の自然runと公開調査を継続できること、worstは売上無しで追加1USDを使い8USDの上限に達すること。Geminiの予約約16kは安く測定できたが、今回の比較は同一課題/同一条件ではなく、複数のprimary補正もあるためproduction品質が実証できたとはしない。棄却案の最強論拠はGeminiなら残107691でも呼べる点。判断が誤る最有力の筋は、単純な調査/記録にGeminiで十分なのにHaikuを維持して余計に使うこと。未測定の精度・利益・$10Kを追加枠の成果として数えない。

現在cursorはsource/main→v18 budget/input-only反映→通常runの継続。依頼ゼロのまま待たず、許可確認をDaisへ渡さず会社側AIが処理できる運用を整え、実需要→受注→納品→第三者29USDC/費用を検証する。新sourceの読取順/直列化は受理チェックを行い、sourceの配布成功と実顧客獲得は分離する。全体goalはactive。

### ハッカソンの公式条件を再照合

一次資料 https://events.ycombinator.com/naive-autonomous-companies-hackathon の公開data-pageを取得。11/7–8/SF、Naïve SDK必須/ライブデモ、実際の納品・判断・人の介入を説明する条件。売上必須とは記載されず、当社の実売上目標と区別する。事前開発の可否は明記無しで、準備した部分を当日開発成果と偽らない。匿名公開ページのrsvp nullは本人参加承認の確認ではなく、不参加判定にも使わない。private `hackathon-official-conditions-current.json` が根拠。優勝/YC interview/YC採択/10Kは未達の目標。

### v18の公式実反映と次の最小probe

PR9165は15checks全PASS/独立read-only review SHIPでmain `9ae119a7272dfc9d423656726eed63c14d6e108e` へ統合。GitHub GraphQLの一時502はNaïveへのmutation前の取得段階で発生し、RESTのPR merged/merge_commit_shaとgit fetchで照合して経路を切り替えた。固定mainの2configをlocal bytes/hashと比較して、同agentへexpected17/budget-only PATCH→18、旧pin13が不変なことを確認後、同deploymentのpin18/inputだけ更新。agent/deployment全source fieldsのGET一致、その他deployment fields不変。追加入金0、既定model/Identity/11allow/12h cronは維持。新次回は11/04 00UTC（JST9時）、旧naturalの成果をv18の実行成果に置換しない。private `budget-v18-{main-source,agent-readback,deployment-readback,final-readback}.json`、`v18-post-apply-spend-computer.json` が証拠。担当spent6892309/新残1107691、Computer pausedを再確認。private runtime.jsonのagent_version/production_deployment_version/source_shaを公式結果へ合わせた。

次は公開ページだけの短いbrowser再開probe。現sourceはkeep_alive=false、公式 https://usenaive.ai/docs/computer/browser.md はtrueをbrief disconnectをまたぐresumable flow用とする。これは確認待ち後の白画面/状態喪失に関係し得るが、解除の実証はまだ無い。最小の設定比較と実画面/URL/非秘密の検索入力保持を確認し、確認イベント数・primary AI操作・実費を別々に記録する。signup/mail/決済/他owner profileを混ぜず、同じ失敗の盲目反復や未測定の改善率を出さない。source/main固定の後にだけruntimeを変更し、1仕事1USD/月8USD内で次の有限probeを閉じる。

MCPのresource境界もfirst-partyで確認: https://usenaive.ai/docs/api/mcp-sessions.md はidentity_idを現状未enforcedなlabelと明記。allowed_toolsはmethodの制限で、対象agent/computerの固定ではない。したがって会社全体へ届くtokenを業務workerへ渡す形にせず、必要な制御は所有agent/Computerを照合する会社側の狭い窓口に保持する。新MCP key/sessionの発行は0。repoのapps/runtime/scriptsにはNaïve/vetta/confirmTool/awaiting_approvalを扱う既存コードを今回の検索で取得できなかったため、既存対応の稼働済みとはしない。まず小さいbrowser再開設定の観測を進め、必要な確認処理は会社側AI運用としてDaisへの承認待ち無しで組む。private `mcp-resource-scope-findings.json` と各first-party docsが根拠。全体goal active。

### browser保持のv19最小変更

目的は確認待ちや短い切断後に白画面になる境界を狭めること。範囲は既存agentのbrowser.keep_alive=false→true、前画面が必ず閉じるというsystem説明を現在画面の観測へ整合、同deployment pin18→19だけ。費用上限8USD/月・1USD/task、model、Identity、その他権限、cron/inputは維持。設定の受理を改善成功にしない。

公式tools/browser資料ではkeep_aliveはagent tools.configs.browser.configにある。native toolのper-call設定は確認できず、未記載argsを捏造しない。現行18を参照するdeploymentは更新時19へ追随するため、pin19も同sourceで扱う。実行時の旧版sessionsは維持する。

完了条件はmain固定sourceの公式GET一致と、公開https://news.ycombinator.com/だけの有限native probe。最大0.30USD、同browser依存操作は直列、まずgoto→screenshot/必要なobserveで実画面があるかを確認する。入力欄が実在するときだけ非秘密検索語を入力し、短いidle/再開をまたぐ画面/URL/入力値を比較する。確認が出た場合は会社側AIが当該公開browser操作を検査して回答し、確認数/primary追加入力/台帳費用を記録する。signup/mail/公開送信/決済はこのprobeに混ぜない。失敗時もcancel/pending0とComputer停止まで照合し、未実証の連続録画や無介入成功を主張しない。

旧順序も新順序も統合SSOT TODO2（browser復旧→実需要→有償納品）。新framework/controllerを先に作らず、実測失敗に対応する単一設定を先行する。現在はv19未反映、live18/18。Reason inboxとSlack既存照会threadの再確認でも新返信は未取得。

### v19の実反映と保持probe結果

PR9166は15checks PASS、fresh read-only review SHIP（source差分のみ）。main `14e9dbd5eedfd1f73f5eeec5643f167f07897282` 固定の2configをbytes/hash比較後、expected18でsystem/toolsだけ更新→agent19。旧current18を参照した同deploymentも公式に19へ自動追随し、agent/deployment全source fields GET一致・deploymentの版以外不変を確認。月8/task1/model/Identity/cron/input不変。次自然runは11/04 00UTC。private `keepalive-v19-final-readback.json` が反映証拠。

有限session `ses_c1se1rskbk76ha3f65y33h80a2` はv19/同Identity/Haiku4.5実5spans。第1turnにnative browser goto HN home→screenshotを順次実行し、primaryも実際のHN画面を確認。end_turn後、primary AIの再開指示1回で移動なしscreenshotを取得すると白画面となった。初回画像211892bytes/sha256 `2e5eddae1e6e8702bc9934cdac1e6c7c459527efdbe9ada451f86e095a10e0c7`、再開画像58227bytes/sha256 `53dddc9013da523227fbb65d8e1357478161c9e8d1f3fcd5d99445dcad4a3828`。再開画像は以前の白画面と同hash。計3native tools、tool.confirm0、人間0、primary followup1。入力保持は、再開時に実ページが無いため実施しない。

結論は「今回のend_turnをまたぐページ保持はできない」。keep_alive=trueで短い接続切断自体が保持されるか、確認待ちの後も同じかは今回未測定。前seller試験とはmodel/URL/操作順も違うため、確認0をkeep_alive単独の効果や公平なmodel比較としない。一方、同一turn内の順次goto/screenshotは実画面まで動き、これを理由に実需要調査を止める必要は無い。

終了はcancel200→GET cancelled/pending0。公式browser.session.opened/closedは2組、current agent Computerはnull、直前に使った旧ComputerはGET destroyed。pause前のlocal probeがNone subscriptで止まった箇所は、cancel/費用照合後のローカル分岐不足と切り分け、nullをpausedへ置換せず、再起動/再生成/無用なpause再試行をしない。全probe費33763microUSD=0.033763USD、credits/spendと台帳7件/has_morefalseの符号反転sumが完全一致。private `keepalive-v19-finite-final-evidence.json`、`keepalive-v19-finite-events.json`、2画像・ledgerが証拠。登録/メール受信/顧客/納品/売上/録画はこの試験に無い。

TODO2内の実行順を実測で更新。旧は「browser再開保持/確認処理を先に解消→実需要→有償納品」。新は「v19 nativeを同一turnで順次操作し実需要を最大1件調べる→有用な提案/第三者依頼→有償納品、idle後は実確認URLを再度開く」。理由は、end_turnでbrowserが閉じる仕様と同一turnの実画面成功が確認でき、未実証の長時間保持や新controllerを顧客獲得の前提にすると全体成果を遅らせるため。確認処理は新しいnative runで実際に再発したcallを具体的に扱う。現在cursorは統合SSOT TODO2、native sellerの現実需要調査。進行中effectは0、旧投稿/メールを再送しない。全体goal active。
