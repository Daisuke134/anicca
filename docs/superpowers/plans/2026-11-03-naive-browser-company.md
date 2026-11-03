# Naïve browser company Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans。primaryが単独実装し、最後にfresh read-only reviewを使う。

**Goal:** Naïve自身のbrowserをLLMが操作して既存の会社業務を完走する。
**Architecture:** 標準pi agentの外部操作はbrowser、本人専用のemail.inboxes/read/send、指定Postiz4tools、Computer read/writeは作業メモと成果物に使い、判断は自然言語promptへ置く。APIは基盤設定/実行/証拠読取に限定する。
**Tech Stack:** Naïve標準agent/session/browser、JSON設定。追加依存なし。
**Spec:** docs/superpowers/specs/2026-09-25-life-manager-unified-ssot.md の Naïve browser company 節。

## Global Constraints
- 既存owner・共有profile・既存6agent/cronを変更しない。
- 専用cap月7USD/max_task1USD、既存残高内・追加入金なし。現在値は「現在の正本」を参照。
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

### 現在の正本: v13稼働・実依頼と納品収益の検証

現在の状態・残TODO順は本節、以後の診断節は追加証拠。前のv6〜v11/cursor/予算記述は当時の履歴。現在はproduction deployment v13/月7USD/task1USD、agent current v17はv13同内容のrollback版。全source fields/dep v13をGET一致、担当累計6390644microUSD、実第三者売上は未確認。

- [x] PR #9137/main `326fc27a46acc3501940f9f095c835c7250c76cf` を反映。agent/deployment v12全payload GET一致、Haiku4.5/月6USD/task1USD/11allow/default deny/同Identity/12h cron、本人wake=falseを維持。反映時は関連チェック・秘密検査PASS、無関係loop2件は実行中（全PASSと主張しない）。v11 PR #9135は後続確認で全15checks PASS。
- [x] Naïve本人のnative Postiz1callから英語募集を公開。post `cmw0dbzbq01gxoc0703wetiwi`、公式PUBLISHED/error null、https://twitter.com/diceai0/status/2117519919034077664 。257文字の送信payload/公式保存本文ともreviewed exact一致。3model spansはHaiku4.5。初回投稿部分22726microUSD。rootによる業務投稿の代行ではない。
- [x] 同finite runで本人browserがGitHub公開依頼一覧をログイン無しでgoto。extract初回はJSON不正でNot run、短い正規JSONに直した再試行は成功し「0 results / No results matched your search」。native screenshot/view_image、primaryの実画像も同状態。Computer public-pilot-intake.jsonはnative write/read exact、extract完了のprovider時刻2026-11-03T07:32:04.820Z、public依頼0（ファイル内の自己申告時刻を計測時計には使わない）。空observeからゼロ件を推測した主張を置換する。
- [x] native public-pilot-promo.jsonのread、intakeファイルwrite/read成功。有限session `ses_35xzd8a1ad2anyqv9j0rcr3v8e` はend_turn後cancel→GET cancelled。合計60211microUSD（募集と受注画面確認）、担当累計4908335microUSD。直接費であり全社費用/利益ではない。副作用不明の再送や内部偽注文は無し。定期deploymentはenabledのまま。
- [x] Grok/Museへ既存Slack threadで公開窓口と具体的な再利用手順/provider receiptの照会を送信成功。https://dais-45u3124.slack.com/archives/C0CBLBGSBJN/p1793690848660309 。返信は未確認、本人DM制限は迂回しない。

残TODO（現在cursorは2、全体goalはactive）:
1. [完了] 実行予算と導線の修復。PR #9145/main `584363f5b03e738647e65286f77264bcff069219` からv13を適用、agent/deploymentの全source fieldsを公式GETで一致確認。月7/task1、同Identity/11allow/cronを維持。未完CTA案内はnative1callから公開し、Postiz保存HTML exact・X本文3段落の一致・native journal write/readを確認。現在cursorは次項の実依頼獲得。
2. 実依頼の獲得。公開pilot https://github.com/Daisuke134/businessrun-bench/blob/main/pilot/README.md と英語募集が稼働。適合した第三者依頼→native分析→英語公開レポート→29USDC/Baseの成功tx/recipient/token/amount/重複照合→費用差引きの順。最初の第三者売上は未達、内部送金/クリック/投稿を代用しない。依頼数0の時点で反復募集や同じ画面巡回を増やさず、顧客反応/チーム返信/自然runを次の観測とする。
3. 次の標準自然runは2026-11-03T12:00:00Z（JST21時）。manual≠natural。実runの版/費用/入力量/介入点/公式納品receiptを記録。初回の実有償業務を連続画面録画で保存する。いま保存した単一スクリーンショットを動画と呼ばない。
4. 本人inbound配送は独立切り分け。送信方向は後続のmail-tester1通で実受信10/10とSPFpass/DKIMvalid/DMARCpassを確認済み（詳細は末尾の実測結果）。受信方向/登録完了は未達。Port25 accepted/返信未着、TLDR送信完了不明、AgentMail3/3で今回owner未確認。個人Google必須にはせず、既存共有箱の借用/変更や同じ診断送信はしない。public pilot発売のgateに戻さない。
5. 少なくとも1件の有償納品と実費からunit economicsを検証し、実需要に合わせ価格/頻度/資源を更新。12h×1件×29×30日の初期理論capacityは1740USDC/月で10Kに届かない。需要/稼働/入金を実証する前にこの上限を売上予測と呼ばない。
6. 利用者向けiPhone入口を設け、利用者個人のGoogle/メール入力/password/PCを要求せずManagerを利用できる導線を実装・実機確認する。現在のdeveloper向けGitHub依頼フォームはこのconsumer入口ではない。infrastructure契約と利用者本人確認/引出条件を区別し、銀行情報以外不要と未確認で約束しない。
7. 黒字の手順/評価/最小stateを他のVMへ移植し2拠点で実証。専用Identity/credential所有/資源上限/仕事重複を維持する。receiving-only walletにoutgoing signerは未接続、compute自費支払/自己複製/任意cloud互換は未達。USD10K月売上/MRR・YC採択・優勝は目標であり未達。

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
