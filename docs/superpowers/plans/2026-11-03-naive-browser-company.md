# Naïve browser company Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans。primaryが単独実装し、最後にfresh read-only reviewを使う。

**Goal:** Naïve自身のbrowserをLLMが操作して既存の会社業務を完走する。
**Architecture:** 標準pi agentの外部操作はbrowserと本人専用のemail.inboxes/read/send、Computer read/writeは作業メモと成果物に使い、判断は自然言語promptへ置く。APIは基盤設定/実行/証拠読取に限定する。
**Tech Stack:** Naïve標準agent/session/browser、JSON設定。追加依存なし。
**Spec:** docs/superpowers/specs/2026-09-25-life-manager-unified-ssot.md の Naïve browser company 節。

## Global Constraints
- 既存owner・共有profile・既存6agent/cronを変更しない。
- 専用cap月2USD/max_task0.50USD、既存残高内・追加入金なし。
- 秘密値はSSOTとproviderの専用credential経路のみ。modelへ値を送らない。
- business script/APIはagentへ与えない。scopeはbrowserによる画面操作と本人専用メール3機能。通常の登録・認証・商品作成・公開・顧客対応は人間承認なしで実行する。

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
