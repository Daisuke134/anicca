# Life Manager — 発表ノート

## 30秒要約

Life Managerは、予定と場所を読み、必要な連絡や予約を先回りして片づけます。普段の連絡は電話とTelegram。Webは、許可を変えたり、止めたり、実行結果を確認したりするときに使います。開発の指示は、ChatGPTのiPhoneアプリからMac mini上のCodexへ出しています。

## 現在地

| 区分 | 状態 | 根拠 |
|---|---|---|
| 毎日の予定 | 本番で確認済み | カレンダー、移動、電話、Telegram、メール |
| 電話 | 本番で確認済み | Telnyx + Gemini Live、実際の通話と録音 |
| 個人パネル | 本番で確認済み | `/panel`、Telegram WebApp、通常のブラウザ |
| 接続と設定 | 本番で確認済み | パネルとチャットで同じ状態を表示 |
| 結果の集計 | 本番で確認済み | 4領域の結果を集計し、対象0件も区別 |
| 画面の安全 | 本番で確認済み | ログ、秘密情報、内部名を画面から除外 |
| 別のCodexスレッド | 稼働中 | Life Managerの続きを処理中 |

## 残TODO

### push済み正本の順序

| 順 | ID | 内容 |
|---:|---|---|
| 1 | 8i | リポジトリ統合。`anicca-products`から`life-manager`へ正本、実装、配備先を一本化 |
| 2 | 9b–9f | 集客。動画作成、InstagramとTikTokへの投稿、数値の取得、内容の修正、Xでの初回告知 |
| 3 | 10a–10f | 開発の自動修復。不具合の個人情報を除き、issue作成、PR、merge、配備、回復確認まで進める |
| 4 | 10g–10i | 判断。予定と本人の意図から、次に処理する用事を選ぶ |
| 5 | 11a–11d | 健康。ケアの抜けを探し、候補を選び、ブラウザやメールで予約して報告 |
| 6 | 12a–12c | 心。予定と場所に合わせて文面を作り、Telegramで送る |
| 7 | 13a–13d | お金。AI用ウォレット、送金先登録、収益台帳、本人への実送金 |
| 条件待ち | 8e / 8f | 実際の受信箱を読み返せて、位置情報を受け取れたら、本番確認を閉じる |

### 別のLife Managerスレッドのライブキュー

| 担当 | 残作業 |
|---|---|
| agent | H3 checkup spec → builder |
| agent | H5 relations |
| agent | crypto handoff |
| loop | 9d Day 2–7 / self-build台帳 |
| loop | 11a scan → 検知日に11b→11c |
| loop | diet / precepts 初配信 |
| ops | Telnyx残高を自動入金で自己回復 |
| human boundary | Life Manager専用Instagramアカウント作成 |

この一覧には、別ブランチや未pushの作業も含みます。GitHubで確認できるまでは完了扱いにしません。

## 話す順番

1. 次の予定、出発時刻、予約、連絡を、ずっと気にしている。
2. Life Managerには、健康、心、お金の用事を任せたい。
3. スマホからMac mini上のCodexへ指示して開発している。
4. 毎日の予定と個人パネルは、本物の電話やメールまで確認済み。
5. 次はリポジトリ統合、集客、自動修復、判断、健康、心、お金の順。
6. 最後は、AIが自分のモデル代とサーバー代を払い、利用料を下げる。

## スライド設計の根拠

| 原則 | 採用 |
|---|---|
| 1枚1メッセージ | 各スライドで伝える内容を1つに絞った |
| 18pt以上 | 本文は原則18pt以上 |
| 強いコントラスト | 暗背景 + オフホワイト、役割別アクセント |
| 余白 | 1枚の情報量を抑え、カード間隔を統一 |
| 未来と事実の分離 | BUILT / NEXT / VISIONを色とラベルで区別 |

参考:

- Naegle et al., “Ten simple rules for effective presentation slides”  
  https://pmc.ncbi.nlm.nih.gov/articles/PMC8638955/
- Microsoft, “Make your PowerPoint presentations accessible”  
  https://support.microsoft.com/en-us/accessibility/powerpoint/make-your-powerpoint-presentations-accessible-to-people-with-disabilities
- W3C, “Understanding Success Criterion 1.4.3: Contrast (Minimum)”  
  https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum
