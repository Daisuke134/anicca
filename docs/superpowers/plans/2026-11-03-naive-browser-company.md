# Naïve browser company Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans。primaryが単独実装し、最後にfresh read-only reviewを使う。

**Goal:** Naïve自身のbrowserをLLMが操作して既存の会社業務を完走する。
**Architecture:** 標準pi agentの外部操作はbrowser、本人専用のemail.inboxes/read/send、指定Postiz4tools、Computer read/writeは作業メモと成果物に使い、判断は自然言語promptへ置く。APIは基盤設定/実行/証拠読取に限定する。
**Tech Stack:** Naïve標準agent/session/browser、JSON設定。追加依存なし。
**Spec:** docs/superpowers/specs/2026-09-25-life-manager-unified-ssot.md の Naïve browser company 節。

## Global Constraints
- 既存owner・共有profile・既存6agent/cronを変更しない。
- 専用cap月2USD/max_task0.75USD、既存残高内・追加入金なし。
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
