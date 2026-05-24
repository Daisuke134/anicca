---
name: naist-onboarding
description: "[DEPRECATED v1 — replaced by ~/.openclaw/skills/naist/ unified v2; this stub is kept for ledger continuity] {{profile.education.institution}}研究室メンバーのオンボーディング（Gmail-MCPエディション）。{{profile.education.institution}}メールをGmailに転送して読む方式に統一。Slackで「チャンネル作って」「オンボーディング」「メール設定」と言われたら起動。Roundcube直接ログイン方式は廃止。"
metadata:
  source: gmail-mcp + slack-api
  requires:
    bins: [node]
    npm: ["@slack/web-api"]
    env: [SLACK_BOT_TOKEN]
    mcp: ["gmail (mcp__aedf48e3-*)"]
---

# naist-onboarding (Gmail-MCP edition)

{{profile.education.institution}}研究室メンバーが Slack で Anicca を使い始めるためのオンボーディングスキル。

## 重要ルール（不変条件）

- **{{profile.education.institution}}メールは Gmail に転送して読む。** Roundcube は転送ルールを設定する1回だけユーザーが手動で触る。Anicca が Roundcube を駆動することは無い。
- **認証情報をチャットに残さない。** パスワード・TOTPシークレットは扱わない（不要）。
- **マルチユーザー対応。** 状態は `~/.openclaw/state/naist/<slug>/` 以下に保存（`<slug>` は {{profile.education.institution}} username の先頭パート、例: `<username>`）。
- **個人チャンネル限定。** メール設定や個人情報は `#ai-<name>` でのみ受け付ける。`#ai` 共通チャンネルでは Phase 1（チャンネル作成）のみ。
- **失敗時は #metrics ({{profile.channels.reportChannel}}) に1行で警告。** 状態ファイル未作成のため cron が abort した場合も同様。

## 状態ファイル schema

`~/.openclaw/state/naist/<slug>/` 以下に以下を保存:

| ファイル | 内容 | 例 |
|---------|------|-----|
| `{{profile.lateness.stakeholders.channel}}_naist.txt` | {{profile.education.institution}}メールアドレス（1行） | `yamada.taro.xy0@is.naist.jp` |
| `{{profile.lateness.stakeholders.channel}}_gmail.txt` | 個人 Gmail（1行・転送先） | `{{profile.contact.personalEmail}}` |
| `slack_channel.txt` | Slack 投稿先チャンネルID（1行） | `C0XXXXXXXXX` |
| `slack_channel_name.txt` | チャンネル名（参考用・1行） | `ai-<username>` |
| `research_topic.json` | 研究トピックと arXiv カテゴリ | `{"topic": "mind wandering", "categories": ["cs.AI","cs.HC"]}` |
| `send_as_enabled.txt` | "Send mail as" 有効フラグ（`yes`/`no`） | `no` |
| `slug.txt` | この slug 自身（cron スクリプトが自分の slug を確認するため） | `<username>` |

## フロー

### Phase 1: チャンネル作成（`#ai` 共通チャンネル）

ユーザーが `#ai` で以下を言ったとき:

- "make my channel" / "create my channel"
- "チャンネル作って" / "マイチャンネル作って"
- "hi" / "こんにちは"（初回の挨拶でもOK）

**実行:**
```bash
cd /Users/anicca/.openclaw/skills/naist-onboarding/scripts
SLACK_BOT_TOKEN=$SLACK_BOT_TOKEN node onboard.js <slack_user_id>
```

結果: `#ai-<familyname>` チャンネルが作成され、ユーザーが招待される。スクリプトは `parts[0]` から slug を導出（`yamada.taro.xy0` → `<username>`）。

その直後、新チャンネル内でウェルカムメッセージを送り、Phase 2 を促す:

> 👋 ようこそ！メール・論文・締切・予定の自動化をやります。`オンボーディング` と送ってくれたら設定ウィザード始めるね。

### Phase 2: 設定ウィザード（個人 `#ai-<name>` チャンネル）

ユーザーが個人チャンネルで以下を言ったとき:

- "オンボーディング" / "設定して" / "セットアップ"
- "onboarding" / "set me up"
- "メール設定して" / "set up mail"

**AskUserQuestion で5問（Q5は任意）:**

| # | 質問 | 形式 | 保存先 |
|---|------|------|--------|
| Q1 | {{profile.education.institution}}のメールアドレスを教えてください（例: `xxx@is.naist.jp`） | テキスト | `{{profile.lateness.stakeholders.channel}}_naist.txt` |
| Q2 | 転送先の個人 Gmail を教えてください | テキスト | `{{profile.lateness.stakeholders.channel}}_gmail.txt` |
| Q3 | 研究トピックは？（arXiv検索のキーワードに使います） | テキスト + arXivカテゴリ複数選択（cs.AI / cs.HC / cs.CL / cs.LG / cs.CV / stat.ML / その他） | `research_topic.json` |
| Q4 | 投稿先 Slack チャンネルは？（このチャンネルで良ければ "ここ" と答えてください） | "ここ" / 別チャンネル名 | `slack_channel.txt` + `slack_channel_name.txt` |
| Q5（任意） | {{profile.education.institution}}メールのアドレスから Anicca が返信できるようにしますか？ Gmail の「Send mail as」設定が必要です | はい / いいえ | `send_as_enabled.txt` |

**ウィザード実行ロジック:**

1. `slug` を確定する（{{profile.education.institution}}メールの先頭、`@` の前のドット区切り `parts[0]`）
2. `mkdir -p ~/.openclaw/state/naist/<slug>/`
3. Q1〜Q4 の回答を上記ファイルに書き込む
4. `slug.txt` に slug を書き込む
5. Slack channel ID は、現在のチャンネル ID を `read_widget_context` か `chat.postMessage` の応答から取得（"ここ" と答えられた場合）。別チャンネル名を答えられた場合は `conversations.list` で ID 解決
6. **ユーザー側1回限りの手動セットアップ手順を投稿** （次節）
7. ユーザーが「設定した」「done」と返したら、**Gmail MCP で疎通確認** （後節）
8. Q5 が「はい」なら Send mail as 設定手順を投稿（後節）

### Phase 3: ユーザー側 1回限りの手動セットアップ（Roundcube → Sieve filter）

**Anicca はこれを駆動しない。** 以下のメッセージを `#ai-<name>` に投稿し、ユーザーがブラウザで自分の手で実施する:

```
📬 *{{profile.education.institution}}メールを Gmail に転送する設定（1回だけ）*

1. ブラウザで Roundcube を開く: https://mailbox.naist.jp/roundcube/
2. {{profile.education.institution}} IdP でログイン（普段通り）
3. 右上の歯車アイコン → 「設定」
4. 左メニュー「フィルター」を選択
5. フィルターセット「managesieve」（または既定のセット）を選び「作成」
6. フィルター名: `Forward to Gmail`
7. ルール: 「全てのメッセージ」（"all messages" / "すべてのメッセージに対して" を選択）
8. アクション:
   - 「メッセージを転送」/ "Redirect message to" → <個人Gmailアドレス>
   - そのまま受信箱にも残したい場合は「メッセージを保存」/ "Keep" もチェック
9. 「保存」をクリック
10. 完了したら、このチャンネルで `転送設定した` か `done` と送ってください

🧪 確認は私がやります。送ってくれたら 1〜2 分後に私からテスト用メールを送って Gmail で受信できるか確認します。
```

### Phase 4: 疎通確認（Gmail MCP）

ユーザーが「done」「転送設定した」と返したら:

1. ユーザー本人がスマホ等から {{profile.education.institution}} メールアドレス宛に空メールを送るか、または Anicca が `mcp__aedf48e3-*__create_draft` で個人 Gmail から {{profile.education.institution}} メール宛にテストメールを下書き → ユーザーが送信
   - 件名例: `[anicca-ping] <slug> <unix_ts>`
2. 60〜120 秒待機
3. `mcp__aedf48e3-*__search_threads` で `from:*@*naist* subject:"[anicca-ping] <slug>"` と `newer_than:5m` を検索
4. ヒットすれば成功 → `#ai-<slug>` に投稿:

```
✅ Gmail への転送が動いています。
これで毎日朝7時/夜18時にあなたの{{profile.education.institution}}メールをサマリしてここに投稿します。
```

5. ヒットしなければ、ユーザーに以下を確認:
   - Roundcube の「フィルター」設定が「有効」になっているか
   - 転送先 Gmail アドレスが正しいか
   - 数分後に再試行

### Phase 5（任意・Q5=「はい」のみ）: Send mail as 設定

Anicca が {{profile.education.institution}} メールアドレスとして Gmail SMTP 経由で返信できるようにする。**ユーザーが Gmail で1回手動設定する。**

```
📤 *Gmail から {{profile.education.institution}} メールアドレスとして送信できるようにする（任意・1回だけ）*

1. Gmail を開く → 右上歯車 → 「すべての設定を表示」
2. 「アカウントとインポート」タブ
3. 「他のメールアドレスを追加」 → <{{profile.education.institution}}メールアドレス> を入力 → 次へ
4. SMTP サーバー: `smtp.naist.jp`、ポート: `587`、ユーザー名: <{{profile.education.institution}}ユーザー名>、
   パスワード: <{{profile.education.institution}}メールパスワード>、TLS を選択
5. Gmail が確認コードをそのアドレス宛に送信 → 数秒後 {{profile.education.institution}} メールが Gmail に転送されてくる
   → コードをコピーして Gmail の確認画面に貼り付け
6. 「確認」をクリック → 完了
7. 完了したら、このチャンネルで `Send-as 設定した` と送ってください

⚠️ パスワードは Gmail の SMTP 設定にだけ保存され、私は触りません。
```

完了報告を受けたら `send_as_enabled.txt` に `yes` を書き込む。

## 既存スクリプト

`scripts/onboard.js` は Phase 1 専用（Slack チャンネル作成）。Gmail-MCP 移行で変更不要。

## Slack Bot に必要なスコープ

| スコープ | 用途 |
|---------|------|
| `channels:write` | パブリックチャンネル作成 |
| `channels:manage` | チャンネルに招待 |
| `chat:write` | メッセージ送信 |
| `chat:write.public` | 任意のチャンネルに投稿 |
| `users:read` | ユーザー名取得 |

（旧版にあった `files:read` は QR画像解析用だったので不要になった）

## 廃止された要素（参考: 旧 SKILL.md からの差分）

- ❌ `WEBMAIL_USERNAME` / `WEBMAIL_PASSWORD` / `WEBMAIL_TOTP_SECRET` Keychain エントリ
- ❌ `zbarimg` での QR デコード
- ❌ `decode_totp_qr.py`
- ❌ Roundcube への Playwright 直接ログイン
- ❌ パスワード・TOTPシークレットを Slack で扱う

代替: Gmail MCP `search_threads` / `get_thread` / `create_draft` を使う。Roundcube は `roundcube-webmail-skill` に DEPRECATED マークを付けて緊急時用に残す。

## 関連 cron

オンボーディング完了後、以下5つの cron が `~/.openclaw/cron/jobs.json` で稼働する（既に登録済み）:

| id | スケジュール | 機能 |
|----|-------------|------|
| `naist-mail-digest` | `0 7,18 * * *` | {{profile.education.institution}} メールサマリを Gmail から取得して投稿 |
| `naist-papers-daily` | `0 8 * * *` | arXiv 論文を `research_topic.json` で検索して投稿 |
| `naist-funds-weekly` | `0 9 * * 1` | JSPS / 学振 / 科研費 週次ダイジェスト |
| `naist-events-weekly` | `0 10 * * 1` | {{profile.education.institution}} セミナー・カンファレンス週次ダイジェスト |
| `naist-deadline-reminder` | `0 18 * * *` | 翌日の締切リマインド |

各 cron は実行時に `~/.openclaw/state/naist/<slug>/` の存在を確認する。state が無ければ「naist not yet onboarded — run onboarding wizard」を `#metrics` に1行投稿して終了する。
