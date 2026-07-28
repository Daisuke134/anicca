# Life Manager — 発表ノート

## 30秒要約

Life Manager は、カレンダー・場所・会話・本人の意図を理解し、財務・身体・精神の未処理を自律的に片付ける生活OSです。主UIは電話とTelegramで、Webは許可・停止・証拠を見るコントロールパネルです。私はこの開発を、ChatGPTのスマホアプリからMac mini上のCodexへ指示する形で進めています。

## 現在地

| 区分 | 状態 | 根拠 |
|---|---|---|
| DAILY core | 本番実証済み | calendar / travel / call / Telegram / email の依存監査 |
| 音声 | 本番実証済み | Telnyx + Gemini Live、実通話・録音 |
| 個人パネル | 本番実証済み | canonical `/panel`、TG WebAppと通常browser |
| 接続・設定 | 本番実証済み | panel/chatの双方向状態同期 |
| organ score | 本番実証済み | outcome-based、対象0件は insufficient data |
| UX/privacy | 本番実証済み | raw log・secret・内部名を画面から除外 |
| 現行Codexスレッド | active | `Life Manager` スレッドが現在も実行中 |

## 残TODO

### push済み正本の順序

| 順 | ID | 内容 |
|---:|---|---|
| 1 | 8i | ONE-REPO統合。`anicca-products`からcanonical `life-manager`へ正本・実装・deploymentを一本化 |
| 2 | 9b–9f | MARKETING。動画生成、IG/TikTok配信、metric取得、self-improve、one-time X launch |
| 3 | 10a–10f | DEV LOOP。feedback/errorをPII scrubし、issue→PR→merge→deploy→回復確認 |
| 4 | 10g–10i | BRAIN。intent-aware context graphとproactive opportunity engine |
| 5 | 11a–11d | PHYSICAL。未ケア検知、候補選定、cloud browser/email予約、事後報告 |
| 6 | 12a–12c | MENTAL。schedule/location由来trigger、文面生成、実Telegram配信 |
| 7 | 13a–13d | FINANCIAL。agent wallet、送金先登録、収益台帳、user walletへの実送金 |
| gate | 8e / 8f | real inbox readbackとreal location inputが得られたらCORE L3をclose |

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

ライブキューは別branchまたは未push作業を含む可能性があるため、push済み正本の完了状態とは混同しません。

## 話す順番

1. 人間の頭が生活のscheduler・operator・CFOになっている。
2. Life Managerは頭脳と三臓器を持つ。
3. スマホからMac mini上のCodexへ指示して開発している。
4. DAILY coreと個人パネルは、実世界のreceiptまで確認済み。
5. 次はrepo統合、marketing、self-build、brain、body、mind、financeの順。
6. 最終的には、AIが自分のcomputeとcloudを払い、利用者負担を縮める。

## スライド設計の根拠

| 原則 | 採用 |
|---|---|
| 1枚1メッセージ | 各スライドの見出しを結論文にした |
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
