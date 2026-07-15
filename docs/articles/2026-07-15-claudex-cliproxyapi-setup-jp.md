# Claude Code で GPT-5.6 を呼ぶ「Claudex」構築 — 実際にやって踏んだ罠3つ

**概要**

- Claude Code を毎日使っていると、週後半になるほど rate limit が近づいてくる不安がつきまといます。
- 解決策は、CLIProxyAPI というローカルプロキシを立てて、Claude Code の接続先を Claude と GPT-5.6 の間で切り替えられるようにすることです。X（旧Twitter）で theo 氏が紹介していた構成を、実際に Mac Mini でセットアップしました。
- セットアップ自体は Homebrew と OAuth ログイン数回で終わります。ただし、実際にやってみると罠が3つありました。この記事はその実測記録です。

## なぜこれが要るのか

Claude Code は便利ですが、Anthropic の利用枠には上限があります。特に、週の後半にコードをたくさん書く日が続くと、rate limit の壁が見えてきます。作業が乗っているときに限って「しばらくお待ちください」と出るのは、地味につらいものです。

一方で OpenAI 側には GPT-5.6（コード名 sol）というモデルがあり、Codex CLI 経由で使えます。だったら、Claude Code のインターフェースはそのまま使いながら、裏側の呼び出し先だけを Claude と GPT-5.6 で切り替えられればいい。そのための橋渡し役が CLIProxyAPI です。

X でこの構成を紹介していたのは theo 氏の投稿でした。Claude Code のフロントエンドと Anthropic の API 形式に依存しない後ろ側を分離する、という発想自体はシンプルです。実際に手を動かしてみると、思ったより早く動きました。

## 仕組み

CLIProxyAPI は、ローカルの `127.0.0.1:8317` で待ち受けるプロキシサーバーです。Claude Code から見ると、通信先が Anthropic の本番エンドポイントではなく、この足元のプロキシに変わるだけです。プロキシの中で、Anthropic 形式のリクエストを OpenAI 形式に翻訳して Codex 側へ流したり、そのまま Anthropic へ流したりします。

```
Claude Code
    |
    | ANTHROPIC_BASE_URL を書き換えるだけ
    v
CLIProxyAPI (127.0.0.1:8317)
    |
    +--> Anthropic API   (claude-fable-5 など)
    |
    +--> OpenAI API      (gpt-5.6-sol など)
```

面白いのは、この切り替えが zshrc の関数3つだけで完結する点です。中身は環境変数を3行セットしているだけです。

```
ANTHROPIC_BASE_URL="http://127.0.0.1:8317"   # 通信先をプロキシへ
ANTHROPIC_AUTH_TOKEN="<proxyキー>"            # プロキシの入場キー
CLAUDE_CODE_SUBAGENT_MODEL="gpt-5.6-sol"     # subagent に使うモデル
```

`claudex` はメインも subagent も GPT-5.6 で回す関数、`claudefable` はプロキシ経由で Fable 5 だけを回す関数、`claudexmix` はメインを Fable にしつつ subagent だけ GPT-5.6 に逃がす関数、という具合に、環境変数の値を変えて `claude` コマンドを呼ぶだけです。難しいラッパーは何もありません。

## セットアップ手順

実際に Mac Mini で通した手順をそのまま書きます。

### 1. インストール

```bash
brew install cliproxyapi
```

手元では `7.2.75` が入りました。

### 2. 設定ファイル

設定は `$(brew --prefix)/etc/cliproxyapi.conf` にあります。ここで詰まりやすい点が2つあります。

まず `host` の値です。

```
host: "127.0.0.1"
```

このとき、引用符の中に先頭スペースを入れてはいけません。`host: " 127.0.0.1"` のように空白が混ざっていると、起動時に無言でおかしな挙動になります。地味ですが、コピペで発生しやすいミスです。

次に `api-keys` です。プロキシへのアクセスキーは自分で生成します。

```bash
openssl rand -hex 32
```

このキーを設定ファイルの `api-keys` に登録するのですが、テンプレートに最初から入っている `your-api-key-1` のようなサンプル値は、必ず全部消してください。1つでも残っていると、起動はするのに API が `unsafe_example_api_key` というエラーを返して止まります。「動いているように見えて実は死んでいる」状態になるので、設定を書いた直後に必ず確認する価値があります。

### 3. OAuth ログイン

Codex 側と Claude 側、それぞれログインします。

```bash
cliproxyapi --codex-login
```

これはコールバックにポート 1455 を使います。ブラウザが開くので、OpenAI の OAuth 承認画面を1クリックするだけです。既にブラウザでログイン済みならパスワード入力すら不要でした。

```bash
cliproxyapi --claude-login
```

こちらはコールバックにポート 54545 を使います。同じく、既ログインならクリック1回で終わります。

### 4. サービス起動

```bash
brew services start cliproxyapi
```

### 5. 動作確認

```bash
curl -s http://127.0.0.1:8317/v1/models \
  -H "Authorization: Bearer $KEY"
```

モデル一覧が JSON で返ってくれば、プロキシは生きています。

### 6. zshrc への組み込み

キーを平文で zshrc に書くのは避け、別ファイルに置いて権限を絞る方式にしました。

```bash
echo "<proxyキー>" > ~/.cli-proxy-api-key
chmod 600 ~/.cli-proxy-api-key
```

```bash
export CLIPROXY_API_KEY="$(cat ~/.cli-proxy-api-key 2>/dev/null)"

# GPT-5.6 Sol のみで動かす
claudex() {
  env \
    ANTHROPIC_BASE_URL="http://127.0.0.1:8317" \
    ANTHROPIC_AUTH_TOKEN="$CLIPROXY_API_KEY" \
    CLAUDE_CODE_SUBAGENT_MODEL="gpt-5.6-sol" \
    CLAUDE_CODE_ALWAYS_ENABLE_EFFORT=1 \
    CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY=3 \
    ENABLE_TOOL_SEARCH=false \
    claude --model "gpt-5.6-sol" "$@"
}

# Claude Fable 5 のみで動かす（プロキシ経由）
claudefable() {
  env \
    ANTHROPIC_BASE_URL="http://127.0.0.1:8317" \
    ANTHROPIC_AUTH_TOKEN="$CLIPROXY_API_KEY" \
    CLAUDE_CODE_SUBAGENT_MODEL="claude-fable-5" \
    CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY=3 \
    claude --model "claude-fable-5" "$@"
}

# メイン Fable 5、サブエージェント GPT-5.6 Sol
claudexmix() {
  env \
    ANTHROPIC_BASE_URL="http://127.0.0.1:8317" \
    ANTHROPIC_AUTH_TOKEN="$CLIPROXY_API_KEY" \
    CLAUDE_CODE_SUBAGENT_MODEL="gpt-5.6-sol" \
    CLAUDE_CODE_ALWAYS_ENABLE_EFFORT=1 \
    CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY=3 \
    ENABLE_TOOL_SEARCH=false \
    claude --model "claude-fable-5" "$@"
}
```

ポイントは `export` ではなく `env` で環境変数を渡していることです。`export` を関数の中に書くと、関数を一度呼んだ後もシェル全体に変数が残り、素の `claude` コマンドまでプロキシを向いてしまいます。`env` なら、その1回の起動にだけ変数が効きます。鍵はファイルから読む形にしておけば、ローテーションしても関数の中身を書き換える必要がありません。

ここまでで、公式ドキュメント（[help.router-for.me](https://help.router-for.me/)）の Quick Start が案内している macOS = Homebrew のルートをなぞった形になります。CLIProxyAPI 自体のコードとイシューは GitHub（[router-for-me/CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI)）で確認できます。

## 踏んだ罠3つ

ここからが実測の本題です。手順通りに進めても、この3つには必ず引っかかります。

### 罠1: free アカウントには gpt-5.6-sol がいない

`--codex-login` を無料の ChatGPT アカウントで通すと、`/v1/models` を叩いたときに `gpt-5.6-luna` や `gpt-5.6-terra` は見えるのに、目当ての `gpt-5.6-sol` だけがリストに出てきません。最初は設定ミスかと思って設定ファイルを何度も見直しましたが、原因はプラン側でした。

Plus 以上の課金アカウントで `--codex-login` をやり直すと、`gpt-5.6-sol` が一覧に現れます。ログイン画面で別アカウントに切り替えるには、OpenAI のログイン画面で「別のアカウントにログインする」を選び、Google アカウントの選択画面から目的のアカウントを選ぶ流れになります。モデル名だけ見て「対応していないのか」と早合点しないほうがいいです。まずアカウントのプランを疑う、が正しい順番でした。

### 罠2: Claude 側の quota 切れは、フリーズに見える

一番厄介だったのがこれです。Claude 側の quota を使い切った状態で `claudex` や `claudexmix` から Claude モデルを呼ぶと、Claude Code の画面は止まったまま何も返ってきません。エラーも出ません。ただ黙って固まって見えます。

裏で何が起きているかというと、プロキシは実際には 429 を返しています。

```
"All credentials for model claude-fable-5 are cooling down via provider claude"
```

Claude Code 側はこの 429 を受け取ると、静かにリトライを繰り返します。ユーザー側からは進捗も出ないので、フリーズと区別がつきません。ここで固まったら、まずログを見ます。

```
~/.cli-proxy-api/logs/error-v1-messages-*.log
```

このログに 429 と cooldown の文言が出ていれば、原因は quota 切れです。プロキシやネットワークの障害ではなく、単純に枠を使い切っているだけなので、時間を空けるか別のモデルに切り替えれば解決します。フリーズだと思ってプロキシを再起動しても直りません。原因の切り分けにログを見る、という順番を覚えておくと時間を無駄にしません。

### 罠3: アカウント設計を先に決めないと、財布が1つになる

これが一番効きました。Claude 用と GPT 用を別のアカウントにしておくと、財布が2つになります。片方の quota を使い切っても、もう片方でそのまま作業を続けられます。

逆に、プロキシ経由の Claude と普段使いの Claude Code が同じ Claude アカウントを指していると、quota は完全に共有されます。プロキシ経由で呼んでいるからといって別枠になるわけではなく、同じ財布から引き落とされます。これはセットアップの最後に気づいて、慌ててプロキシ用の Claude アカウントを別で用意し直しました。最初にアカウント設計、つまり「どのアカウントがどの財布か」を決めてからログインする、という順番のほうが後戻りが少ないです。

## 使い分け表

3つの関数をどう使い分けているかをまとめます。

| コマンド | 中身 | 向く場面 | Claude quota |
|---|---|---|---|
| `claudex` | GPT-5.6-sol 単体 | 仕様が明確な実装、大量の一括修正、テスト書き、リファクタ | 消費ゼロ |
| `claudefable` | 通常の Claude Fable 5 | 設計、重要なレビュー、判断が要る作業 | 消費する |
| `claudexmix` | メインは Fable、subagent は sol | 大きい新機能。Fable が設計と判断を持ち、sol が手を動かす | メインのみ消費 |

`claudexmix` の構成は、Cognition が公開しているブログ記事の検証内容と近い発想です。強いモデル（Fable）をリード役に置き、安価なモデル（sidekick）に実作業を渡すと、性能をほぼ落とさずにコストだけ下げられる、という趣旨の記事です（[Cognition: Making Fable cheaper than Opus](https://cognition.com/blog/making-fable-cheaper-than-opus)）。実際に手元で回してみても、設計判断が絡む部分だけ Fable に残し、機械的な実装を sol に流すやり方は、体感の速度とコストのバランスが良い印象でした。

## 注意点

いくつか、使う前に知っておいたほうがいいことがあります。

CLIProxyAPI は Anthropic や OpenAI の公式製品ではなく、第三者が作っている OSS です。便利ですが、公式サポートは受けられません。

OAuth の資格情報は `~/.cli-proxy-api/` に平文で保存されます。他のユーザーやプロセスから読めないように、権限を絞っておく必要があります。

```bash
chmod -R go-rwx ~/.cli-proxy-api
```

また、「ローカルプロキシ」という言葉から誤解しがちですが、推論そのものはクラウド側で実行されます。ローカルにあるのはあくまで通信の中継役であって、モデルの計算がローカルで動いているわけではありません。

最後に、`~/.claude/settings.json` にこの設定をグローバルで書き込むのはやめたほうがいいです。書いてしまうと、プロキシを経由しない普段の `claude` コマンドまで巻き込まれて壊れます。今回のように、シェル関数のスコープ内だけで環境変数を有効にする形にしておけば、通常の Claude Code の挙動には一切影響しません。

## まとめ

`claudex` / `claudefable` / `claudexmix` の3コマンドを用意しておくだけで、Claude の quota を気にせず作業を続けられる場面が増えました。セットアップ自体は Homebrew と OAuth ログインで数分もかかりませんが、実際に動かしてみるまで気づけない罠が3つありました。free アカウントには sol がいないこと、Claude quota 切れは無言のフリーズに見えること、そしてアカウント設計を先に決めないと財布が1つになってしまうこと。この3つさえ押さえておけば、週後半の rate limit に怯える理由はかなり減らせます。
