最近、海外を中心に OpenClaw（旧Clawdbot）がかなり話題になっています。

私も先日導入してみたのですが、

いつものSlackから普通にチャットするだけで指示が通る
裏でClaude Codeみたいなエージェントが動いてる
放っておいても勝手に作業が進んでいく
という体験がなかなか衝撃的で、「あ、これ仕事のやり方変わるな」と思いました。

ただ、いざ導入しようとすると、

「公式ドキュメントが英語で分かりにくい」
「どこから手をつければいいか分からない」

という声をよく聞きます。

そこで今回は、プログラミング経験ゼロでも迷わずOpenClawを導入し、Slackと連携するまでの全手順を、実際の画面に沿ってまとめました。

まず結論：何ができるようになるのか
設定が終わると、こんな感じでSlackからAIに指示できるようになります：

あなた: @OpenClaw 今週の売上データをまとめて
OpenClaw: 承知しました。売上データを集計中です...
         [5分後]
         完了しました。今週の売上は前週比+12%で...

普通にSlackでやり取りしてるだけなのに、裏ではAIがファイルを編集したり、Webを調べたりしてくれる。

しかも一度繋げば、ブラウザ操作もファイル管理も全部Slackから完結。

必要なもの
始める前に、以下を用意してください。

パソコン

Mac、Windows（WSL2経由）、Linuxのいずれか
古いMac miniでも全然動きます
APIキー

Anthropic API（推奨）：https://console.anthropic.com/
または OpenAI API
Slack

アプリを追加できる権限があればOK
作業時間

45分〜1時間（初回のみ）
Part 1: OpenClawをインストールする
Node.jsを入れる
OpenClawはNode.js上で動きます。まずはこれを入れます。

Macの場合

ターミナルを開いて（Cmd + Space → 「ターミナル」で検索）、以下をコピペ：

curl -fsSL https://fnm.vercel.app/install | bash

実行したら、ターミナルを一度閉じて開き直す。これ重要です。

次に：

fnm install 22
fnm use 22

確認：

node --version

v22.x.x と出ればOK。

Windowsの場合

PowerShellを管理者として開いて：

wsl --install

再起動後、スタートメニューから「Ubuntu」を開いて、Mac同様のコマンドを実行。

OpenClawを入れる
ここからが本番。といっても、コマンド一発です。

curl -fsSL https://openclaw.bot/install.sh | bash

数分待つと完了。確認：

openclaw --version

バージョンが出れば成功。

初期設定
openclaw onboard

対話形式のウィザードが立ち上がります。

聞かれること：

Setup mode → QuickStart を選択（デフォルトでOK）
Authentication → Anthropic API key を選択
APIキー入力 → 事前に取得したキーを貼り付け
Background service → Yes を選択
これで基本設定は完了。

試しにブラウザでAIと会話してみたい場合：

openclaw dashboard

ブラウザが開いて、チャット画面が出ます。ここまで来れば、あとはSlack連携だけ。

Part 2: Slackと連携する
ここからがちょっと面倒ですが、一度やれば終わりです。

Slackアプリを作る
https://api.slack.com/apps にアクセス。

「Create New App」→「From a manifest」を選択。

ワークスペースを選んで、以下をそのまま貼り付け：

{
  "display_information": {
    "name": "OpenClaw",
    "description": "AIアシスタント"
  },
  "features": {
    "bot_user": {
      "display_name": "OpenClaw",
      "always_online": false
    },
    "app_home": {
      "messages_tab_enabled": true,
      "messages_tab_read_only_enabled": false
    }
  },
  "oauth_config": {
    "scopes": {
      "bot": [
        "chat:write",
        "channels:history",
        "channels:read",
        "groups:history",
        "groups:read",
        "groups:write",
        "im:history",
        "im:read",
        "im:write",
        "mpim:history",
        "mpim:read",
        "mpim:write",
        "users:read",
        "app_mentions:read",
        "reactions:read",
        "reactions:write",
        "pins:read",
        "pins:write",
        "emoji:read",
        "commands",
        "files:read",
        "files:write"
      ]
    }
  },
  "settings": {
    "socket_mode_enabled": true,
    "event_subscriptions": {
      "bot_events": [
        "app_mention",
        "message.channels",
        "message.groups",
        "message.im",
        "message.mpim",
        "reaction_added",
        "reaction_removed",
        "member_joined_channel",
        "member_left_channel",
        "channel_rename",
        "pin_added",
        "pin_removed"
      ]
    }
  }
}

「Create」で作成完了。

このマニフェストを使えば、権限設定を一つずつポチポチやる必要がなくなります。かなり楽。

トークンを2つ取得する
ここ、ちょっとややこしいですが、要は2つのトークンをコピーするだけです。

① App Token

左メニュー「Basic Information」→ 下にスクロール →「App-Level Tokens」→「Generate Token and Scopes」

Token Name: 適当に socket とか
Add Scope: connections:write を選択
Generate
出てきた xapp- で始まるやつをコピー。

② Bot Token

左メニュー「OAuth & Permissions」→「Install to Workspace」→ 許可

「Bot User OAuth Token」の xoxb- で始まるやつをコピー。

この2つ、メモ帳かどこかに貼っておいてください。

OpenClawに設定を入れる
openclaw configure

「Channels」を選択
「Slack」を選択
App Token、Bot Tokenをそれぞれ貼り付け
あとはデフォルトでEnter連打
設定を反映：

openclaw gateway restart

動作確認
Slackで適当なチャンネルを開いて：

/invite @OpenClaw

これでボットがチャンネルに入ります。

あとはメンションするだけ：

@OpenClaw こんにちは、自己紹介して

返事が来れば成功！🎉

補足：セキュリティについて
ここまで読んで「便利そう」と思った方、ちょっと待ってください。

OpenClawは便利な反面、設定を間違えるとかなり危険です。

というのも、

フルシェルアクセス（コマンド実行し放題）
ブラウザ操作（ログイン済みセッション含む）
ファイル読み書き
24時間常時稼働
という「権限を持った自律エージェント」だからです。

最低限やっておくべきこと：

グループチャットには入れない（個人DMで使う）
メインPCではなく専用環境で動かす（古いMac miniとか）
最初は通知・要約・リマインドだけに留める
ファイル操作やブラウザ自動化は、理解してから段階的に解放
感覚的には「自分のPCを他人に自由に触らせる」のと同じ。

「これ、他の人に任せて大丈夫か？」と一回立ち止まるくらいがちょうどいいです。

Gateway Dashboardは意外とちゃんとしていて、GUI上で細かい権限設定ができます。AIに聞きながらでも設定できますが、権限周りは一つずつ理解して進めるのが吉。

よくあるトラブル
ボットが反応しない

openclaw gateway status
openclaw health

で状態確認。大体はGateway再起動で直る：

openclaw gateway restart

DMしたらコードが送られてきた

初回DMはペアリング認証があります。表示されたコードを：

openclaw pairing approve slack <コード>

で承認。

メンションなしで反応してほしくない

設定ファイル ~/.openclaw/openclaw.json に追記：

{
  "channels": {
    "slack": {
      "channels": {
        "#general": { "allow": true, "requireMention": true }
      }
    }
  }
}

まとめ
OpenClawは、使い方次第で生産性が爆上がりする一方、雑に扱うと事故るタイプのツールです。

正しく設定すれば、Slackで指示するだけで勝手に仕事が進む。寝てる間にタスクが片付いてる、みたいな体験ができます。

ただ、「とりあえず全部許可」でやると痛い目を見ます。

・最初は機能を絞って使う
・権限は「本当に必要か？」を都度確認
・迷ったら許可しない

この辺を意識しておけば、かなり頼れる存在になると思います。

参考リンク

OpenClaw公式: https://docs.openclaw.ai



