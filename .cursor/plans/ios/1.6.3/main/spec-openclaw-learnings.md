# 1.6.3 OpenClaw 記事から得た学びと Anicca 向けタスク（参照スペック）

作成: 2026-02-11  
参照元: 横田あかり「OpenClawのビジネス向け環境構築で考える、AIエージェントの倫理とセキュリティ。そしてクローズドループへ」（2026.02.11）  
用途: 後から実装する場合のタスクリスト・用語メモ。いつやるかは未定。

---

## 1. 記事の要約

| 項目 | 内容 |
|------|------|
| やったこと | Mac mini 1 台に OpenClaw を常駐させ、Discord/Telegram を窓口に、音声（ElevenLabs + Whisper/MLX）、Twilio 電話、n8n ワークフロー、Claude Code コンテナ、Grok（X/Web 検索）、Terraform + Tailscale + Keychain + 監視・SAST まで一通り構築。 |
| 方針 | 倫理・人間中心を前提に、Human in the Loop で危ない操作は承認。安全なタスクだけ AI が自律完結する「クローズドループ」を次のステップに設定。 |
| Anicca との違い | 記事は Mac ローカル + Discord/Telegram。Anicca は VPS のみ + Slack。 |

---

## 2. キーワード（超ブレイクダウン）

| キーワード | 一言 | 補足 |
|------------|------|------|
| OpenClaw | AI を常駐させる土台 | Gateway が Slack/Discord と繋ぎ、SOUL.md 等で性格・ルールを固定。 |
| Gateway | OpenClaw の常駐プロセス | 落ちたら誰も返信できないので LaunchAgent 等で自動再起動。 |
| Claude Code | コードを書く・実行する AI CLI | OpenClaw の「実行部隊」。コンテナで常駐させて n8n 等から投げる。 |
| Opus / Sonnet | Claude のモデル（重い/軽い） | 会話は Sonnet、重い作業は Opus と使い分け。 |
| フォールバック | メインが使えなかったら次を使う | Anthropic 制限 → Bedrock → Codex → Gemini など。 |
| Bedrock | AWS の AI モデル呼び出しサービス | Anthropic 直接とは別枠のレート制限。 |
| SOUL.md / USER.md / AGENTS.md | AI の性格・自分情報・起動時手順 | ファイルで永続化し、セッションが変わっても忘れない。 |
| Human in the Loop | AI の結果を一度人間が確認してから次へ | 生成→レビュー→承認なら実行。危ない操作で必須。 |
| n8n | ノードで繋ぐワークフロー（IFTTT 的） | HTTP で Claude Code や Docker API を叩き、承認フローを組む。 |
| Tailscale | 端末同士を VPN でつなぐ | EC2 の 22 番を全閉じして Tailscale 経由のみ SSH。 |
| Keychain | Mac の秘密保存場所 | API キーを .zshrc に書かず Keychain に登録。VPS では .env が中心。 |
| credential_process | AWS 認証をコマンドで動的取得 | ~/.aws/credentials の平文をやめ、Keychain 等を読むスクリプトを指定。 |
| HEARTBEAT.md | 定期的に AI にやらせるチェックリスト | 未読メール・カレンダー・スキャン結果などを周期で確認。 |
| クローズドループ | 人間を挟まず AI が安全なタスクを完結 | スキャン確認・定型レポートなど。危ない操作は Human in the Loop のまま。 |
| tfsec | Terraform の静的セキュリティ解析 | 設計図のチェック。 |
| Prowler | AWS のランタイム CSPM | 実際のリソース状態のチェック。 |
| Semgrep | アプリコードの SAST | 週次でリポジトリをスキャン。 |
| Trivy | Docker イメージの脆弱性スキャン | 週次でローカルイメージをスキャン。 |
| NIST CSF / CIS Controls | セキュリティのフレームワーク | 何をやるかをチェックリスト化。 |

---

## 3. Anicca 向けタスクリスト

実施順は未定。優先度は末尾の表を参照。

### A. モデル・フォールバック

| # | タスク | 内容 |
|---|--------|------|
| A1 | VPS の primary モデルを確認する | `openclaw config get agents.defaults.model.primary` で現状把握。 |
| A2 | フォールバック候補を openclaw.json に列挙する | 例: Sonnet → Bedrock（同 Sonnet）→ Codex。必要なら Bedrock の API キー・region を .env に追加。 |
| A3 | （任意）Slack の軽いやりとり用に軽いモデルを試す | レスポンス速度優先のチャネルで Sonnet 等を検討。 |

### B. ペルソナ・ルールのファイル化

| # | タスク | 内容 |
|---|--------|------|
| B1 | Anicca 用のセキュリティ・倫理ルールを 1 本書く | クレデンシャル読み禁止、外部送信禁止、git push/削除は確認など。VPS の ~/.openclaw/ か workspace に SOUL.md / RULES.md として置く。 |
| B2 | そのファイルを毎セッション読むようにする | openclaw.json の agents や AGENTS.md で「まず SOUL/RULES を読め」と指定。 |
| B3 | （任意）USER.md 相当で Anicca の文脈を書く | プロダクト名・Slack の用途・やってよい範囲を短くまとめる。 |

### C. Human in the Loop

| # | タスク | 内容 |
|---|--------|------|
| C1 | 危ない操作をリスト化する | git push、DB 変更、X 投稿、デプロイ、課金関連 API など。 |
| C2 | 危ない step の前に承認を必須にする | 既存の exec-approvals や API の「承認済みか」チェックと整合。 |
| C3 | 安全だけど自動で回すタスクを 3 つ決める | メトリクス取得、ログ確認、read-only の X 検索など。承認なしでクローズドループ化。 |

### D. 秘密管理

| # | タスク | 内容 |
|---|--------|------|
| D1 | VPS の ~/.openclaw/.env の項目を一覧する | どのキーがどこで使われているか整理。不足・重複を解消。 |
| D2 | ドキュメント・スクリプトからキー直書きを無くす | プレースホルダに置き換え、実際の値は .env のみ。 |
| D3 | （任意）本番と staging で .env を分離しているか確認する | 同じ .env を誤って本番で使っていないか。 |

### E. 監視・検知

| # | タスク | 内容 |
|---|--------|------|
| E1 | VPS で listen しているポートのベースラインを取る | 1 回 `ss -tlnp` や `lsof -i -nP` の結果を保存。変更があれば検知。 |
| E2 | （任意）重要ファイルの変更検知を入れる | openclaw.json, .env の存在確認やハッシュ比較を cron で週 1 回など。 |
| E3 | API リポジトリに Semgrep を 1 回かける | `semgrep --config auto apps/api`。ERROR を潰すか ignore を明示。 |

### F. 証跡・運用ログ

| # | タスク | 内容 |
|---|--------|------|
| F1 | 運用ログを 1 か所に決める | 例: `.cursor/plans/reference/ops-log.md` や既存の deployment-todo に「日付・やったこと・変更ファイル」を追記するルール。 |
| F2 | （任意）今日やったことを Anicca が参照できるようにする | HEARTBEAT や cron でサマリを Momo に追加する、または日次 .md を 1 本更新。 |

### G. X 検索・Grok

| # | タスク | 内容 |
|---|--------|------|
| G1 | xAI API キーを取得する（未所持なら） | x.ai でサインアップ・課金・キー取得。 |
| G2 | Grok を呼ぶスクリプト or スキルを 1 本用意する | クエリで x_search を叩き要約を返す。既存 x-research（生データ）との役割分担を決める。 |
| G3 | VPS の .env に XAI_API_KEY を入れ、OpenClaw のスキル or ツールから呼べるようにする | 記事の「30分で動く」レベルはここまで。 |

### H. インフラのセキュリティ（考え方）

| # | タスク | 内容 |
|---|--------|------|
| H1 | VPS の SSH の公開範囲を確認する | パスワード認証 OFF、鍵のみ。必要なら fail2ban。 |
| H2 | （任意）Tailscale を VPS に入れ 22 番を閉じる | 自分だけ Tailscale 経由で SSH。攻撃面を減らす。 |

---

## 4. 優先度イメージ

| 優先度 | カテゴリ | やること |
|--------|----------|----------|
| 高 | ルール・安全 | B1–B2: セキュリティ・倫理ルールを 1 本の .md にし、毎セッション読ませる。 |
| 高 | 承認 | C1–C2: 危ない操作をリスト化し、その前に承認を必須にする。 |
| 中 | 安定運用 | A1–A2: 現在のモデル確認とフォールバックの追加。 |
| 中 | 秘密 | D1–D2: .env の整理とキー直書きの排除。 |
| 低 | 監視 | E1: リスニングポートのベースライン取得。 |
| 低 | 証跡 | F1: 運用ログを 1 か所に決めて書くルール。 |
| 任意 | X | G1–G3: Grok 用キー・スクリプト・スキル（x-research と役割分担を決めた上で）。 |

---

## 5. 参照

| ソース | 内容 |
|--------|------|
| 記事 | 横田あかり「OpenClawのビジネス向け環境構築で考える、AIエージェントの倫理とセキュリティ。そしてクローズドループへ」2026.02.11 |
| OpenClaw Anicca 運用 SSOT | `.cursor/plans/reference/openclaw-anicca.md` |
| 1.6.3 main 配下の他スペック | `spec-x-article.md`, `deployment-todo.md` 等 |

---

最終更新: 2026-02-11
