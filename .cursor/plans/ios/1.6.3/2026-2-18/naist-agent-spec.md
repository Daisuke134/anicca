# NAIST Agent — 完全仕様書

**作成日**: 2026-02-22
**最終更新**: 2026-02-24（全スキル実装完了）
**ステータス**: ✅ 全スキル完了（ClawHub公開待ち）
**目的**: NAISTの全学生が、Slackチャットだけで大学関連の全タスク（履修・課題・メール・研究・ファンド申請）を完全自動化できるシステム。OpenClawスキルとしてOSS公開。

---

## 概要（What & Why）

| 項目 | 内容 |
|------|------|
| What | NAIST学生向けAIエージェント。`#ai` チャンネルに話しかけるだけで全て完了 |
| Why | 大学院生の雑務（メール確認・履修登録・課題提出・科研費申請）は全て自動化可能。研究に集中させる |
| 誰が動かすか | **Anicca（Mac Mini上のOpenClaw）** が全ユーザーを一括管理 |
| OSS公開先 | `Daisuke134/anicca-products` + ClawHub |
| 技術スタック | OpenClaw + Playwright + gog CLI + arxiv + notion-cli-agent + Slack API |

---

## スキルソース調査結果（2026-02-23）

**ClawHub（`clawhub search`）+ skill.sh（`npx skills find`）の両方を検索済み。**
オリジナルゼロ。全て既存スキルのコピー・改変のみ。

| # | スキル名 | 採用ソース | インストール数 | セキュリティ | インストールコマンド |
|---|---------|-----------|-------------|------------|-------------------|
| 1 | `naist-onboarding` | `vamseeachanta/workspace-hub@slack-api`（skill.sh）のAPIパターンを参照 | 19 | ✅ 低リスク | 参照のみ |
| 2 | `naist-mail` | **`roundcube-webmail`**（既インストール済みスキル） | — | ✅ 既存 | コピーのみ |
| 3 | `naist-calendar` | **`odyssey4me/agent-skills@google-calendar`**（skill.sh） | **88** | ✅ 安全 | `npx skills add odyssey4me/agent-skills@google-calendar` |
| 4 | `naist-papers` | **`karpathy/nanochat@read-arxiv-paper`**（skill.sh、Karpathy製） | **162** | ✅ 安全 | `npx skills add karpathy/nanochat@read-arxiv-paper` |
| 5 | `naist-portal` | **`playwright-cli`**（既インストール済みスキル） | — | ✅ 既存 | 不要（既存） |
| 6 | `naist-deadline` | **`refoundai/lenny-skills@managing-timelines`**（skill.sh） | **336** | ✅ 安全 | `npx skills add refoundai/lenny-skills@managing-timelines` |
| 7 | `naist-funds` | **`davila7/claude-code-templates@research-grants`**（skill.sh） | **140** | ✅ 安全 | `npx skills add davila7/claude-code-templates@research-grants` |
| 8 | `naist-events` | **Firecrawl CLI**（naist.jp/events/ スクレイプ）+ `gog-calendar`（既存） | — | ✅ 既存ツール | 不要（既存） |
| 9 | `naist-qa` | **`actionbook/actionbook@deep-research`**（skill.sh） | **135** | ✅ 安全 | `npx skills add actionbook/actionbook@deep-research` |
| 10 | `naist-thesis` | **`jamditis/claude-skills-journalism@academic-writing`**（skill.sh） | **182** | ✅ 安全 | `npx skills add jamditis/claude-skills-journalism@academic-writing` |
| 11 | `naist-metrics` | **`apify/agent-skills@apify-content-analytics`**（skill.sh、Apify製） | **553** | ✅ 安全 | `npx skills add apify/agent-skills@apify-content-analytics` |
| 12 | `skill-for-you` | **`steipete/clawdis@session-logs`**（75★、verified）+ skill.sh/ClawHub 検索 | **75** | ✅ 安全（Snyk High=誤検知。jq/rg でローカル読取のみ） | `npx skills add steipete/clawdis@session-logs`（インストール済み） |
| 13 | `auto-skill-creator` | **`sickn33/skill-creator`**（250★、init_skill.py等3本実在確認）+ `find-skills`（既存） | **250** | ✅ 安全（Low Risk） | `npx skills add sickn33/antigravity-awesome-skills@skill-creator`（インストール済み） |

**全スキルのセキュリティチェック完了（2026-02-23）。⚠️なし。実装開始可能。**

| スキル | 確認結果 | 備考 |
|--------|---------|------|
| `jezweb/playwright-local` | ❌ 該当スキルなし | → `playwright-cli`（既存）に変更 |
| `cclank/news-aggregator-skill` | ✅ Gen=Safe, Socket=0 | HN/GitHub向け。naist-eventsには不採用（Firecrawlで代替） |
| `davila7/browser-automation` | ✅ Gen=Safe, Socket=0 | 知識スキルのみ。実行不可のため不採用 |

**スコープ外（スペックには残す）**:

| スキル | 理由 |
|--------|------|
| `naist-wiki`（Notion） | Notion token未取得。今は使わない |
| `auto-skill-builder` | 作業量大。`skill-creator`で代替できる |

---

## Anicca ↔ Claude Code 分業モデル

**Anicca は 24/7 稼働。Claude Code は必要なときだけ起こす。**

| 主体 | 役割 | 例 |
|------|------|-----|
| **Anicca（Mac Mini、24/7）** | cron実行・Slack送受信・ボタン処理・シンプルなAPI呼び出し | メール通知、カレンダー確認、ボタン承認受信 |
| **Claude Code（必要時のみ）** | 重い推論・複雑なタスク・スキル作成 | 論文校正、DC1申請書生成、auto-skill-creator |
| **どちらでもいい** | タスクの性質による | Aniccaがまずやってみる。重ければClaude Codeに委譲 |

**Anicca → Claude Code への委譲方法**:
```bash
# OpenClaw の exec ツールで claude CLI を呼ぶ
exec: claude --message "thesis.texの第3章を校正して。結果を#ai-daisに送って"

# Anicca が 3am にトリガーしてもいい
# Claude Code は起こされたら即実行、終わったら終了
```

**設計原則**: Anicca がデフォルト実行者。Claude Code は「重い仕事の下請け」。どちらでもいい場面ではAniccaが自分でやる。

---

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│              NAIST AGENT (Anicca / Mac Mini)                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Cron Jobs（任意・ユーザーが明示的に有効化）│  On-Demand (Slack Chat)        │
│  ──────────────────────────────────────  │  ─────────────────────         │
│  デフォルト: 全て無効                      │  User → #ai-<name>             │
│  「毎朝メールを通知して」で有効化           │   └ Anicca 応答                 │
│  09:00 naist-mail    ← ユーザーが有効化   │                                 │
│  09:05 naist-calendar ← ユーザーが有効化  │  Approval Flow:                │
│  09:10 naist-papers  ← ユーザーが有効化   │  Anicca提案                    │
│  09:25 naist-metrics      │   → [送信する][キャンセル]       │
│  23:00 deadline-check     │   → 承認 → 実行                  │
│  Weekly: naist-wiki       │                                 │
│                           │                                 │
├─────────────────────────────────────────────────────────────┤
│  Skills                                                     │
│  ├── naist-mail          (roundcube-webmail-skill コピー)   │
│  ├── naist-calendar      (gcal-digest コピー)               │
│  ├── naist-papers        (arxiv ClawHub 新規)               │
│  ├── naist-deadline      (quick-reminders ClawHub ベース)   │
│  ├── naist-portal        (Playwright 新規)                  │
│  ├── naist-funds         (firecrawl + arxiv 新規)           │
│  ├── naist-wiki          (notion-cli-agent ClawHub 新規)    │
│  ├── naist-events        (firecrawl + gcal 新規)            │
│  ├── naist-qa            (OpenClaw LLM 新規)                │
│  ├── naist-thesis        (arxiv + LLM 新規)                 │
│  ├── naist-metrics       (tiktok-scraper 既存)              │
│  └── naist-onboarding    (Slack API 新規)                   │
└─────────────────────────────────────────────────────────────┘
```

---

## ユーザー体験（UX）— 全スキル詳細

### Skill 1: naist-mail（毎朝09:00 自動 + オンデマンド）

**ベース**: `roundcube-webmail-skill`（Mac Mini既存・完全流用）

**24/7 自動体験（ダイスは何もしない）**:
```
[09:00 JST] Aniccaが #ai-dais に自動投稿

📬 NAISTメール 本日の未読（3件）

[1] Re: 研究室輪講スケジュール変更
    from: yamada-sensei@is.naist.jp  /  2時間前

[2] 【締切3日】JST研究費申請書提出のお願い
    from: soumu@naist.jp  /  昨日 17:30

[3] DC1採択通知について（重要）
    from: gakusei@naist.jp  /  昨日 14:05

全文を読むには「メール1を読んで」と言ってください。
```

**オンデマンド（チャット操作）**:
```
ダイス: 「メール2を読んで」
→ Anicca: 本文全文を展開

ダイス: 「山田先生にメール2を返信して。来週月曜が都合いいです、と」
→ Anicca: 返信内容を確認してください:
          宛先: yamada@is.naist.jp
          本文: お世話になっております。来週月曜日が
                都合よろしい状況でございます...

          [送信する] [編集する] [キャンセル]

→ ダイス: [送信する]
→ Anicca: ✅ 返信を送信しました
```

| 項目 | 値 |
|------|-----|
| ツール | `roundcube-webmail-skill`（Playwright + SAML + TOTP + otplib） |
| 承認 | `request-approval`（ClawHub）+ Block Kit buttons |
| cron | `0 9 * * *`（毎朝09:00 JST） |

---

### Skill 2: naist-calendar（毎朝09:05 自動 + オンデマンド）

**ベース**: `gcal-digest`（Mac Mini既存・完全流用）

**24/7 自動体験**:
```
[09:05 JST] Aniccaが #ai-narita に自動投稿

📅 本日 2/22（土）のスケジュール

09:30  輪講（D207）
13:00  指導教員ミーティング（Zoom: meet.google.com/xxx）
17:00  〆切: プログレスレポート提出

📅 明日 2/23（日）
→ 予定なし
```

**オンデマンド**:
```
成田さん: 「来週月曜10時に論文ゼミを追加して、場所はD207」
→ Anicca: ✅ Googleカレンダーに追加しました
          2/24（月）10:00 論文ゼミ @ D207
```

| 項目 | 値 |
|------|-----|
| ツール | `gcal-digest`（gog CLI経由） |
| cron | `5 9 * * *`（毎朝09:05 JST） |

---

### Skill 3: naist-papers（毎朝09:10 自動 + オンデマンド）

**ベース**: `arxiv` v1.0.4（ClawHub）— 旧: latest-papers（x-researchのみ）から変更

**24/7 自動体験**:
```
[09:10 JST] Aniccaが #ai-dais に自動投稿

📄 昨日の新着論文（arXiv cs.AI + cs.LG）

[1] "Efficient Attention Mechanisms for Long-Context NLP"
    著者: Chen et al.  |  arXiv: 2402.xxxxx
    要約: Transformerの注意機構を改善し、10Kトークン以上の
          長文処理でFlash Attentionより20%高速化を達成...
    💡 ダイスの研究テーマ「長文理解」と関連度: 高

[2] "Self-Supervised Learning without Data Augmentation"
    著者: Kim et al.  |  arXiv: 2402.xxxxx
    要約: データ拡張なしでSSLを実現する手法を提案...
    💡 輪講で取り上げ候補

「論文1を要約して」「論文1のbibtexをコピーして」で追加操作可能。
```

**オンデマンド**:
```
ダイス: 「マインドワンダリングの最新論文を5本まとめて」
→ Anicca: arXivとX(Twitter)を横断検索...
           [5本の要約リスト]
```

| 項目 | 値 |
|------|-----|
| ツール | `arxiv` v1.0.4（ClawHub、新規採用）+ x-research（X/Twitter補完） |
| cron | `10 9 * * *`（毎朝09:10 JST） |

---

### Skill 4: naist-deadline（締切トラッカー、オンデマンド登録 + cron通知）

**ベース**: `quick-reminders` v1.1.4（ClawHub）

**登録体験**:
```
成田さん: 「3月15日締切でDC1の申請書を追加して」
→ Anicca: ✅ 登録しました
           リマインダー設定:
           - 3/8  (7日前)  → 最初のリマインド
           - 3/12 (3日前)  → 2回目
           - 3/14 (前日)   → 最終警告
           - 3/15 09:00    → 締切当日通知
```

**cron通知体験（成田さんは何もしない）**:
```
[3/8 09:00] Aniccaが #ai-narita に自動投稿

🔔 締切アラート（7日前）

📋 DC1申請書 — 残り7日
締切: 2026年3月15日

「進捗報告」で今の状態を記録できます。
「申請書の作成を手伝って」でnaist-researcherが起動します。
```

| 項目 | 値 |
|------|-----|
| ツール | `quick-reminders`（ClawHub、新規採用）+ cron |
| cron | `0 9 * * *` 全締切を毎日チェック |

---

### Skill 5: naist-portal（新規、オンデマンド）

**技術**: Playwright + SAML + TOTP（`roundcube-webmail-skill` と同じ認証パターン）

**体験**:
```
ダイス: 「今学期の時間割を見せて」
→ Anicca: 🔐 NAISTポータルにログイン中...
           ✅ ログイン完了

           📖 2026年春学期 時間割

           月  09:30  機械学習特論（A201）
           火  13:00  分散システム論（D302）
           木  10:00  研究ゼミ（指導教員室）
           金  14:00  輪講（D207）

ダイス: 「情報倫理学を履修登録して」
→ Anicca: 確認します:
           科目: 情報倫理学（2単位）
           担当: 鈴木教授
           曜日: 水曜 15:00-16:30

           [登録する] [キャンセル]

→ ダイス: [登録する]
→ Anicca: ✅ 履修登録が完了しました
```

| 項目 | 値 |
|------|-----|
| ツール | Playwright + otplib + macOS Keychain |
| 承認 | 全操作で `request-approval` または Block Kit buttons |

---

### Skill 6: naist-funds（毎週月曜・木曜09:15 自動 + オンデマンド）

**ベース**: Firecrawl CLI + `arxiv`（新規）

**24/7 自動体験**:
```
[月曜 09:15 JST] Aniccaが #ai-dais に自動投稿

💰 今週の奨学金・研究費情報

[1] 情報処理学会 研究奨励賞  ← NEW
    締切: 3月31日  |  対象: 学生会員
    申請: ipsj.or.jp/...

[2] JST ACT-X（若手研究者支援）
    締切: 4月15日  |  金額: 300万円/2年
    分野: 情報科学

「これを申請手順リストにして」で詳細を展開。
「DC1申請書を書いて」でnaist-researcherが起動。
```

| 項目 | 値 |
|------|-----|
| ツール | Firecrawl CLI（JSPS / JST / jfund.or.jp）+ x-research（X検索） |
| cron | `15 9 * * 1,4`（月・木09:15 JST） |

---

### Skill 7: naist-wiki（毎週月曜 + オンデマンド）

**ベース**: `notion-cli-agent` v1.0.0（ClawHub、新規採用）

**オンデマンド体験**:
```
成田さん: 「今日の輪講まとめをwikiに追加して。
           発表者:成田。論文:Efficient Attention。
           要点:Flash Attentionより20%高速、メモリ半減。
           次回担当:田中」

→ Anicca: Notionの「輪講記録」ページに以下を追加しますか？

           日付: 2026-02-22
           発表者: 成田
           論文: Efficient Attention Mechanisms...
           要点: Flash Attentionより20%高速, メモリ半減
           次回担当: 田中

           [追加する] [編集する]

→ 成田さん: [追加する]
→ Anicca: ✅ Notionの輪講記録に追加しました
           👉 https://notion.so/...
```

| 項目 | 値 |
|------|-----|
| ツール | `notion-cli-agent`（ClawHub、新規採用） |

---

### Skill 8: naist-events（毎週月曜09:20 自動）

**ベース**: Firecrawl CLI + `gog-calendar`（新規）

**24/7 自動体験**:
```
[月曜 09:20 JST] Aniccaが #ai-narita に自動投稿

📢 今週のNAISTイベント

[1] 招待講演: 東大 山本教授「LLMの可能性と限界」
    日時: 2/25（火）15:00-17:00  |  場所: 大講義室
    参加: 自由（事前申込不要）

[2] 学生研究発表会
    日時: 2/28（金）13:00-17:00  |  場所: D棟

「イベント1をカレンダーに追加して」で即座に登録可能。
```

| 項目 | 値 |
|------|-----|
| ツール | Firecrawl CLI（naist.jp/events/）+ `gog-calendar` |
| cron | `20 9 * * 1`（毎週月曜09:20 JST） |

---

### Skill 9: naist-qa（オンデマンド）

**ベース**: OpenClaw LLM（Anthropic Claude）+ Firecrawl CLI

**体験**:
```
成田さん: 「DC1の申請って日本語で書くべき？英語？」

→ Anicca: DC1申請書について:

           ✅ 日本語が標準です。

           根拠:
           • 審査員は日本語ネイティブの研究者が多数
           • 英語も可能だが、日本語の方が評価のブレが少ない
           • JSPSガイドラインでも日本語を推奨

           「採択された申請書の書き方のコツを教えて」で
           追加情報を取得できます。
```

| 項目 | 値 |
|------|-----|
| ツール | OpenClaw LLM + Firecrawl CLI（NAIST公式・JSPS等） |

---

### Skill 10: naist-thesis（オンデマンド）

**ベース**: OpenClaw LLM + `arxiv`（新規）

**体験**:
```
ダイス: 「thesis.texの第3章を校正して」

→ Anicca: 第3章「提案手法」を校正しました（23箇所）

           重要な指摘:
           [1] p.47 "we propose" → "This thesis proposes"
               （一人称禁止）
           [2] p.52 参考文献 [Chen2023] が本文中で引用されていない
           [3] p.55 図3.4のキャプションが不完全

           📊 可読性スコア: 73/100（前回比 +5）
           文字数: 12,847語（目標20,000語まで: 7,153語不足）

           「[1]を全自動修正して」で一括修正可能。
```

| 項目 | 値 |
|------|-----|
| ツール | OpenClaw LLM + `arxiv`（参考文献検索）+ Firecrawl CLI |

---

### Skill 11: naist-metrics（毎朝09:25 自動）

**ベース**: `tiktok-scraper`（Mac Mini既存）

**24/7 自動体験（ダイス専用）**:
```
[09:25 JST] Aniccaが #ai-dais に自動投稿

📊 TikTok昨日のパフォーマンス

再生数: 12,847 (+23% vs 前日)
フォロワー増: +48
コメント: 23件（ポジ: 89%）
最高動画: 「AIエージェントの使い方」(45k再生)

X(Twitter):
インプレッション: 8,420 / いいね: 127

💡 Anicca考察: 「AIエージェント系」コンテンツが今週好調。
   明日の投稿テーマ提案: 「OpenClawの活用法」
```

| 項目 | 値 |
|------|-----|
| ツール | `tiktok-scraper`（既存）+ `twitter-automation` |
| cron | `25 9 * * *`（毎朝09:25 JST） |

---

### Skill 12: naist-onboarding（新規、オンデマンド）

**新規ユーザーが参加したときの体験**:

**設計原則**: 構造化されたセットアップウィザードは起動しない。Aniccaは普通に話しかける。credentialsは必要になった瞬間に初めて聞く。cronはデフォルト無効。ユーザーが「毎朝通知して」と言って初めて有効化する。

```
[#ai チャンネル]

成田さん: @Anicca make my channel

→ Anicca: ✅ #ai-narita 作ったよ！そっちで話しかけて。

[#ai-narita チャンネルに移動]

Anicca: yo 👋

成田さん: 「何ができるの？」

Anicca: メール読んだり、カレンダー確認したり、
        最新論文まとめたり、Notionに議事録書いたり、
        締切リマインドしたり。

        まず何か試してみる？

─────（NAISTアカウントが必要な機能を初めて使うとき）─────

成田さん: 「未読メール見せて」

Anicca: NAISTのアカウント情報が必要。
        IDとパスワードをDMで送ってくれたら繋ぐ。
        （送ったらすぐ消すね）

成田さん: [DM: s2410023 / p@ssword123]

→ Anicca: ✅ 受信しました。安全に保存しています...
           メッセージを削除しました。

成田さん: [QRコードスクショ送信]

→ Anicca: ✅ TOTPシークレットを抽出・保存しました。
           メッセージを削除しました。

成田さん: 「マインドワンダリング、EEG、注意制御」

→ Anicca: ✅ 完了。じゃあメール見てくるね…

           📬 未読メール（3件）
           …
```

| 項目 | 値 |
|------|-----|
| ツール | Slack API（conversations.create / invite / delete）+ macOS Keychain |

---

### Skill 13: skill-for-you（毎朝09:30 自動）

**ベース**: `steipete/clawdis@session-logs`（75★）+ skill.sh（primary）/ ClawHub（secondary）検索

**動作**: Aniccaが過去7日間のセッションログを `jq` でパースし、ユーザーが繰り返しリクエストしているタスクを抽出 → skill.sh / ClawHub を検索 → 解決できるスキルを1件だけ提案。

**Slackでの出力（必須フォーマット）**:
```
[09:30 JST] Aniccaが #ai-dais に自動投稿

📦 あなたにおすすめのスキル

[1] karpathy/nanochat@read-arxiv-paper
    🔗 https://skills.sh/karpathy/nanochat/read-arxiv-paper
    できること: arXiv論文を自動取得・Markdown要約→Slack通知
    あなたに有益な理由: 過去7日で11回「論文を調べて」と依頼している。
                        毎朝自動で届くようになれば手動依頼が不要になる。

    [✅ インストールして使う] [❌ スキップ]
```

**ボタン押下後**:
```
✅ インストール完了: karpathy/nanochat@read-arxiv-paper
   明日09:10から自動で届きます。

❌ スキップしました。明日は別のスキルを提案します。
```

**出力ルール（絶対）**:

| 項目 | ルール |
|------|--------|
| リンク | skill.sh の正式URL（必須） |
| 名前 | `owner/repo@skill-name` 形式（必須） |
| できること | 1行で具体的に（抽象表現禁止） |
| 有益な理由 | セッションログの実データ引用（「〜回依頼している」等） |
| 提案数 | 毎回1件のみ。複数提案禁止 |
| Back-and-forth | 禁止。ボタン1回で完結 |

| 項目 | 値 |
|------|-----|
| ツール | `steipete/clawdis@session-logs`（jq + rg でJSONL解析） + `npx skills find`（skill.sh）+ `clawhub search` |
| ソース | `/Users/anicca/.openclaw/agents/anicca/sessions/*.jsonl`（検証済み） |
| cron | `30 9 * * *`（毎朝09:30 JST） |
| 承認 | Block Kit buttons（[インストールして使う] / [スキップ]） |

---

### Skill 14: auto-skill-creator（オンデマンド）

**ベース**: `find-skills`（既存）+ `sickn33/skill-creator`（250★）

**動作**: ユーザーが「このスキルを作って」「毎日Xして」とチャットで依頼 → skill.sh / ClawHub を先に検索 → 見つかればinstall → 見つからなければ skill-creator 6フェーズでビルド → テスト → 結果を即チャット報告。**back-and-forth ゼロ。入力1回→出力1回で完結。**

**フロー A: スキルが既存だった場合**:
```
ダイス: 「毎日Hacker Newsのトップ10を要約してSlackに送るスキルを作って」

→ Anicca: 🔍 skill.sh と ClawHub を検索中...

          ✅ 既存スキルが見つかりました

          cclank/news-aggregator-skill
          🔗 https://skills.sh/cclank/news-aggregator-skill
          できること: HN・GitHub Trending・ProductHuntを毎日取得→要約→Slack通知

          ⬇️ インストール中...
          ✅ インストール完了

          [テスト結果]
          $ node scripts/fetch_news.py --test
          ✅ HN TOP 10 取得成功（4.2秒）
          ✅ Slack送信テスト成功

          🎉 完成。明日09:00から自動で届きます。
          「今すぐ送って」と言えばすぐ実行できます。
```

**フロー B: スキルが存在しない場合（新規ビルド）**:
```
ダイス: 「NAISTの時間割をGoogleカレンダーに自動同期するスキルを作って」

→ Anicca: 🔍 skill.sh と ClawHub を検索中...
          ❌ 該当スキルなし。新規ビルドします。

          ─── 製作中（skill-creator 6フェーズ） ───

          Phase 1/6 Brainstorming...  ✅
          Phase 2/6 Prompt Enhancement...  ✅
          Phase 3/6 File Generation...  ✅
          Phase 4/6 Validation...  ✅
          Phase 5/6 Installation...  ✅
          Phase 6/6 Complete

          ─── テスト実行 ───
          $ node scripts/sync-timetable.js --dry-run
          ✅ NAISTポータル接続成功
          ✅ 時間割パース: 月曜09:30 機械学習特論...（4科目）
          ✅ Google Calendar 追加テスト成功

          ─────────────────────────────────────
          🎉 スキル完成: naist-timetable-sync [インストール済み]

          使い方: 「時間割をカレンダーに同期して」と話しかけてください。
          毎週月曜に自動同期したい場合は「毎週月曜に自動同期して」と言ってください。
```

**出力ルール（絶対）**:

| ルール | 内容 |
|--------|------|
| Back-and-forth 禁止 | 「ダウンロードしました。実行しますか？」は禁止。インストール→テスト→報告を連続実行 |
| テスト必須 | コードを書いただけで完了にしない。`node scripts/xxx.js --test` を実際に実行して出力を確認 |
| テスト失敗時 | チャットに「テスト失敗: [エラー内容]」を報告。「完了」とは言わない |
| 検索順序 | skill.sh（primary）→ ClawHub（secondary）→ 両方なければ新規ビルド |
| 入力 | ユーザーのSlackメッセージ1回のみ |
| 出力 | Slackに結果1回のみ。途中報告は進捗バー形式（back-and-forth禁止） |

| 項目 | 値 |
|------|-----|
| ツール | `find-skills`（既存）+ `sickn33/skill-creator`（250★）+ `clawhub search` + `npx skills find` |
| スクリプト | `init_skill.py` / `quick_validate.py` / `package_skill.py`（実在確認済み） |
| 承認 | 不要。全自動実行（ビルド・インストール・テストまで） |

---

## Cron（任意）— ユーザーが明示的に有効化するまで無効

**デフォルトは全cron無効。ユーザーがチャットで「毎朝〜して」と言ったときに初めて有効化する。**

```
成田さん: 「毎朝メール通知して」
→ Anicca: ✅ 毎朝09:00に通知するようにした。

成田さん: 「毎日論文も送って」
→ Anicca: ✅ 毎朝09:10にarXiv新着を送るようにした。

成田さん: 「やっぱり論文はいらない」
→ Anicca: ✅ 止めた。
```

**有効化できるcron一覧（ユーザーが選ぶ）**:

| 有効化の言い方（例） | スキル | 時刻 |
|--------------------|--------|------|
| 「毎朝メールを通知して」 | naist-mail | 09:00 JST |
| 「毎日スケジュールを送って」 | naist-calendar | 09:05 JST |
| 「毎日論文を送って」 | naist-papers | 09:10 JST |
| 「毎週奨学金情報を送って」 | naist-funds | 月・木 09:15 JST |
| 「毎週イベント情報を送って」 | naist-events | 月 09:20 JST |
| 「毎朝メトリクスを送って」 | naist-metrics | 09:25 JST |

---

## 共有ユーティリティ: `slack-approval`

**全スキル（NAIST / mobile-app-factory / その他全て）が使う共通承認パターン。**

### ソース（コピー元）

**オリジナルゼロ。既存スキルをコピーする。**

| スキル | URL | 採用理由 |
|--------|-----|---------|
| **`sickn33/antigravity-awesome-skills@slack-bot-builder`** | https://skills.sh/sickn33/antigravity-awesome-skills/slack-bot-builder | **253インストール。Block Kit interactive buttons + Approve/Reject パターン実装済み。これ一択** |

**`npx skills add sickn33/antigravity-awesome-skills@slack-bot-builder` でインストール → SKILL.md を読んでパターンをコピー。**

### 実行環境

**OpenClaw（Mac Mini Anicca）が全て直接実行する。Claude Code は経由しない。**

| 項目 | 値 |
|------|-----|
| 送信 | OpenClaw `slack` ツール（profile:full）+ `SLACK_BOT_TOKEN` |
| 受信 | Socket Mode + `SLACK_APP_TOKEN`（xapp-...）→ `block_actions` イベント |
| Claude Code の役割 | 開発時のみ。Mac Mini の 24/7 実行とは無関係 |
| Rube MCP / mcporter | **不要**。Mac Mini に token が既にある |

### ボタンの動作（`slack-bot-builder` パターンをコピー）

```
1. OpenClaw の slack ツールで blocks 付きメッセージを投稿
         ↓
2. Slack に表示
   ┌─────────────────────────────────┐
   │  📧 メール返信                    │
   │  宛先: 山田教授                   │
   │  本文: お世話になっております...   │
   │                                 │
   │  [✅ 実行する]  [❌ キャンセル]    │
   └─────────────────────────────────┘
         ↓
3. ユーザーがボタンを押す
         ↓
4. Socket Mode（SLACK_APP_TOKEN）が block_actions を受信
   allow_once → 実行 → chat.update で「✅ 実行しました」
   deny       → 停止 → chat.update で「❌ キャンセルしました」
```

**戻り値は `approved` / `denied` の2択のみ。timeout なし。**

### 適用スキル一覧

| スキル | 承認が必要な操作 |
|--------|---------------|
| `naist-mail` | メール返信送信 |
| `naist-portal` | 履修登録・成績確認 |
| `naist-wiki` | Notion書き込み |
| `skill-for-you` | スキルインストール |
| `mobile-app-factory` | ビルド実行・デプロイ・ストア提出 |
| **全ての新規スキル** | 外部への書き込み・送信・投稿を伴う全操作 |

### 実装順序

**Phase 1 の最初に作る。全スキルより先。**

| # | タスク | 状態 |
|---|--------|------|
| 0 | `slack-bot-builder` インストール → Block Kit パターンをコピーして `slack-approval` として配置 | ⏳ **最優先** |
| 1 | `naist-onboarding` でテスト | ⏳ |
| 2〜 | 残り全スキルで流用 | ⏳ |

---

## 承認フロー（Approval）

### 採用する承認パターン（優先順位順）

| # | パターン | いつ使う | 実装 |
|---|---------|---------|------|
| 1 | **チャット直接実行** | ユーザーが明示的に指示した場合 | 設定不要。デフォルト |
| 2 | **Block Kit Buttons** | 外部書き込み・送信・インストール等の重要操作 | `sickn33/slack-bot-builder` パターンをコピー |
| 3 | **Emoji Reaction（👍/👎）** | 軽量な確認（cron の有効化等） | Slack reactions.get でポーリング |

**`request-approval`（ClawHub）は使わない。** Preloop MCP サーバーが必要で OpenClaw 非対応。
**戻り値は `approved` / `denied` の2択のみ。timeout なし。**

### Block Kit 送信テンプレート（send.js 内部）

```javascript
const blocks = [
  {
    type: "section",
    text: { type: "mrkdwn", text: `*${title}*\n${detail}` }
  },
  {
    type: "actions",
    block_id: `approval_${Date.now()}`,
    elements: [
      { type: "button", action_id: "allow_once", style: "primary",
        text: { type: "plain_text", text: "✅ 実行する" } },
      { type: "button", action_id: "deny", style: "danger",
        text: { type: "plain_text", text: "❌ キャンセル" } }
    ]
  }
];
// allow_once → chat.update で「✅ 実行しました」
// deny       → chat.update で「❌ キャンセルしました」
```

---

## スキル一覧 — ソース完全明記

**原則: オリジナルゼロ。全スキルをClawHub/既存からコピーして最小限だけ変える。**
**パス: 全スキルは独立フラット構造。naist-agent/ サブフォルダにしない。**

| # | スキル名 | 何を解決するか | ソース（コピー元） | オリジナル度 |
|---|---------|--------------|-----------------|------------|
| 1 | `naist-onboarding` | `@Anicca make my channel` で #ai-<name> 作成 + credentials収集 | `slack-api` v1.0.7（ClawHub）のAPI呼び出しパターンをコピー | 低 |
| 2 | `naist-mail` | NAISTメールを読む・返信する | **`roundcube-webmail`**（インストール済みスキル）をそのままコピー。credentials対応のみ追加 | 極低 |
| 3 | `naist-calendar` | Google Calendarを読む・追加する | **`gcal-digest`**（Mac Mini既存）をそのままコピー | 極低 |
| 4 | `naist-papers` | 研究分野の最新arXiv論文を届ける | **`arxiv` v1.0.4**（ClawHub）をコピー。検索クエリをユーザー研究テーマに差し替えるだけ | 極低 |
| 5 | `naist-portal` | NAISTポータルで履修確認・成績確認 | **`playwright-cli`（既インストール済み）** + `roundcube-webmail` のSAML+TOTPパターンをコピー。URLとセレクタのみ変更 | 低 |
| 6 | `naist-deadline` | 締切を登録→7日前・3日前・前日・当日通知 | **`quick-reminders` v1.1.4**（ClawHub）をそのままコピー | 極低 |
| 7 | `naist-funds` | 科研費・奨学金の新着情報を週次で届ける | `deep-research-pro` v1.0.2（ClawHub）の調査パターンをコピー + Firecrawl CLI | 低 |
| 8 | `naist-events` | NAISTイベント・招待講演を週次で届ける | `email-to-calendar` v1.13.1（ClawHub）のパターン参照 + Firecrawl + `gog-calendar` | 低 |
| 9 | `naist-qa` | 大学のこと何でも答える。履修相談・DC1相談 | `academic-deep-research` v1.0.0（ClawHub）をコピー。NAISTコンテキストを追加 | 低 |
| 10 | `naist-thesis` | 論文を校正する。一人称チェック・参考文献整合性 | **`academic-writing-refiner` v1.0.0**（ClawHub）をコピー。日本語理工系論文ルールを追加 | 低 |
| 11 | `naist-metrics` | TikTok/Xパフォーマンスレポート（ダイス専用） | **`tiktok-scraper`**（Mac Mini既存）をそのままコピー | 極低 |
| 12 | `skill-for-you` | 作業ログから最適なスキルを毎朝提案→承認でinstall | **`steipete/clawdis@session-logs`**（75★）のjqクエリでユーザーリクエストを抽出 + skill.sh（primary）/ ClawHub（secondary）検索 | 極低 |
| 13 | `auto-skill-creator` | 「このスキルを作って」「毎日Xして」に応えてスキルを探す→なければ作る→テスト→結果報告 | **`find-skills`**（既存）+ **`sickn33/skill-creator`**（250★、init_skill.py/quick_validate.py/package_skill.py実在確認済み） | 低 |

### スコープ外（スペックには残す・今は作らない）

| スキル | 理由 |
|--------|------|
| `naist-wiki`（Notion） | Notion token未取得。使う人もまだいない |
| `auto-skill-builder` | 作業量大。`skill-creator`スキルで代替できる |

---

## パス構造（全スキル独立・フラット）

```
全スキルは独立した個別スキル。
→ 個別に clawhub install できる
→ Anicca に1個ずつコピーできる
→ OSS として1個ずつ公開できる

開発・テスト（Claude Code / ダイス自身が先に使う）:
/Users/cbns03/Downloads/anicca-project/.claude/skills/
├── slack-approval/SKILL.md          ← 全スキル共通（最優先）
│   └── scripts/send.js + listen.js
├── naist-onboarding/SKILL.md
├── naist-mail/SKILL.md
├── naist-calendar/SKILL.md
├── naist-papers/SKILL.md
├── naist-portal/SKILL.md
├── naist-deadline/SKILL.md
├── naist-funds/SKILL.md
├── naist-events/SKILL.md
├── naist-qa/SKILL.md
├── naist-thesis/SKILL.md
├── naist-metrics/SKILL.md
├── skill-for-you/SKILL.md
└── auto-skill-creator/SKILL.md

テスト通ったら → Mac Mini（Anicca）にコピー:
/Users/anicca/.openclaw/skills/<skill-name>/

OSS公開:
Daisuke134/anicca-products/skills/<skill-name>/
clawhub publish <skill-name>
```

---

## 実装ルール（絶対）

| ルール | 内容 |
|--------|------|
| 1スキルずつ | 前のスキルがテストPASSするまで次に進まない |
| ダイス自身でテスト | 実際に使って動作確認。コード書いただけで完了にしない |
| コピー優先 | ソースが見つかったらそのままコピー。アレンジしない |
| ClawHub → install | `clawhub install <name>` で入れてから参照する |

---

## 多ユーザー管理

### credentialsストレージ構造

```
/Users/anicca/.openclaw/workspace/naist-agent/users/
├── narita/
│   ├── config.json         ← Slack channel ID、研究テーマ等
│   └── gog-account.json    ← Gmail/Calendar アカウント
├── tanaka/
│   ├── config.json
│   └── gog-account.json
└── ...
```

### config.json 形式

```json
{
  "naist_id": "s2310001",
  "slack_channel_id": "C123ABC456",
  "slack_user_id": "U987DEF012",
  "naist_mail_url": "https://mailbox.naist.jp/roundcube/",
  "totp_secret": "KEYCHAIN:naist-narita-totp",
  "password": "KEYCHAIN:naist-narita-password",
  "research_topics": ["mind wandering", "EEG neurofeedback", "attention control"],
  "research_topics_ja": ["マインドワンダリング", "脳波ニューロフィードバック"]
}
```

**TOTP・パスワードは macOS Keychain に保存（平文禁止）**:
```bash
security add-generic-password -a "naist-narita" -s "WEBMAIL_PASSWORD" -w "パスワード"
security add-generic-password -a "naist-narita" -s "WEBMAIL_TOTP_SECRET" -w "base32シークレット"
```

---

## セキュリティリスク一覧

| # | リスク | 深刻度 | 対策 |
|---|--------|--------|------|
| 1 | NAISTパスワード・TOTPシークレットの平文保存 | CRITICAL | macOS Keychain必須（`security add-generic-password`）。config.jsonに平文禁止 |
| 2 | `.session.json`（Playwright認証セッション）が実行後も残存 | HIGH | `finally { fs.unlinkSync(SESSION_FILE) }` で自動削除 |
| 3 | OpenClaw `.env` をgitにコミットするリスク | CRITICAL | `.gitignore`確認。`.env.example`のみgit管理 |
| 4 | Slack DMで受け取ったcredentialsが残る | HIGH | `chat.delete` APIで受信後即削除 |
| 5 | `notion-cli-agent`（ClawHub製）の信頼性不明 | MEDIUM | SKILL.mdを読んでから使用。Notion APIキーをKeychainで管理 |
| 6 | `arxiv`スキルが想定外の通信を行う可能性 | LOW | arXiv APIはpublic。SKILL.mdを確認してから採用 |
| 7 | 複数ユーザーのKeychain情報が同一Mac Miniに混在 | HIGH | per-userのKeychainアカウント名で分離（`naist-<username>`） |
| 8 | Playwright認証情報がメモリに残る | MEDIUM | ブラウザを非持続モードで起動。実行後 `browser.close()` 必須 |
| 9 | あるユーザーが他ユーザーのチャンネルにアクセス | HIGH | Anicca は自分の `#ai-<name>` チャンネルのみアクセス。bindings設定で分離 |

**最優先対策**: NAISTパスワードとTOTPをKeychain移行。`setup-keychain.sh`（`roundcube-webmail-skill` v2に存在）をテンプレートとして使用。

---

## 実装順序（MUST）

**1スキル作る → ダイス自身でテスト → PASS → 次へ。スキップ禁止。**

| # | タスク | ソース | 状態 |
|---|--------|--------|------|
| 0 | `slack-approval` | 新規（Socket Mode + Block Kit） | ✅ 完了 |
| 1 | `naist-onboarding` | `slack-api`（ClawHub）コピー | ✅ 完了 |
| 2 | `naist-mail` | `roundcube-webmail-skill`（Mac Mini既存）= naist-mail そのもの。コピー不要 | ✅ 完了（= roundcube-webmail-skill） |
| 3 | `naist-calendar` | `gcal-digest`（Mac Mini既存）コピー | ✅ 完了 |
| 4 | `naist-papers` | `arxiv`（ClawHub）コピー | ✅ 完了 |
| 5 | `naist-portal` | `playwright-cli` + SAML+TOTP | ✅ 完了 |
| 6 | `naist-deadline` | `quick-reminders`（ClawHub）コピー | ✅ 完了 |
| 7 | `naist-funds` | Firecrawl CLI + cron（月・木09:15）| ✅ 完了（20 tests GREEN） |
| 8 | `naist-events` | Firecrawl + gog + cron（月09:20）| ✅ 完了（24 tests GREEN） |
| 9 | `naist-qa` | OpenClaw LLM + Firecrawl CLI | ✅ 完了（7 tests GREEN） |
| 10 | `naist-thesis` | OpenClaw LLM + arxiv | ✅ 完了（9 tests GREEN） |
| 11 | `naist-metrics` | `tiktok-scraper`（Mac Mini既存）コピー | ✅ 完了（9 tests GREEN） |
| 12 | `skill-for-you` | `session-logs`（既存）+ `npx skills find` | ✅ 完了（8 tests GREEN） |
| 13 | `auto-skill-creator` | `find-skills`（既存）+ `skill-creator` | ✅ 完了（5 tests GREEN） |
| 14 | ClawHub に公開（各スキル個別） | `clawhub publish <skill-name>` | ⏳ |

---

## 境界（やらないこと）

| やらないこと | 理由 |
|------------|------|
| 論文投稿・学会発表の自動化 | 研究成果は人間が判断するべき |
| VPN/内部ネットワーク対応 | Tailscaleで回避可能（Mac Mini使用） |
| 複数大学対応（v1） | まずNAISTのみ。汎用化は後 |
| バックエンドAPIサーバー | Mac Mini + OpenClaw のみ。Railwayは不要 |
| モバイルアプリ | Slackがインターフェース |
| 勝手な課題提出・メール返信 | 全操作でユーザー承認必須 |
| Slack以外の通知（SMS/メール等） | Slackに集約 |

---

## OSS公開戦略

| チャネル | 対象 | 方法 |
|---------|------|------|
| GitHub OSS | NAISTのエンジニア学生 | `Daisuke134/anicca-products/skills/<skill-name>/`（個別） |
| ClawHub | OpenClawユーザー全般 | `clawhub publish <skill-name>`（個別） |
| NAIST Slack #ai | NAIST Slack全員 | 完成後に告知投稿 |

### インストール方法

```bash
# OpenClawユーザー
clawhub install naist-agent

# Claude Codeユーザー
git clone https://github.com/Daisuke134/anicca-products
cp -r anicca-products/skills/naist-agent ~/.openclaw/skills/
```

### NAIST Slack告知文（完成後）

```
🤖 NAIST AIエージェント、ベータ公開！

Slackだけで大学の雑務を全部やってくれます。

できること:
• 毎朝09:00 未読メールを要約してSlack通知
• メール返信を承認するだけで自動送信
• 授業スケジュールをGoogleカレンダーに自動登録
• 締切7日前・3日前・前日に自動リマインド
• 研究分野の最新arXiv論文を毎日要約
• 科研費・奨学金の申請情報を毎週お届け
• NAISTイベント・セミナーを毎週月曜に告知
• ゼミWiki（Notion）を音声メモ感覚で更新

使い方: #ai チャンネルに「こんにちは！[名前]です」と投稿するだけ。
セットアップは5分。パスワードはMac Miniのローカルに保存。外部送信なし。

Source: https://github.com/Daisuke134/anicca-products
```

---

## 参照スキル（Mac Mini既存）

| スキル名 | パス | 参照目的 |
|---------|------|---------|
| `roundcube-webmail-skill` | `/Users/anicca/.openclaw/skills/roundcube-webmail-skill/` | SAML認証・メール操作・Keychainパターン |
| `gmail-digest` | `/Users/anicca/.openclaw/skills/gmail-digest/` | gog CLI パターン |
| `gcal-digest` | `/Users/anicca/.openclaw/skills/gcal-digest/` | Google Calendar パターン |
| `tiktok-scraper` | `/Users/anicca/.openclaw/skills/tiktok-scraper/` | SNSメトリクスパターン |

## ClawHubからインストールするスキル（実装時）

| スキル | コマンド | 用途 |
|--------|---------|------|
| arxiv | `clawhub install arxiv` | 論文検索 |
| request-approval | `clawhub install request-approval` | Slack承認フロー |
| notion-cli-agent | `clawhub install notion-cli-agent` | ゼミWiki更新 |
| quick-reminders | `clawhub install quick-reminders` | 締切リマインダー |
