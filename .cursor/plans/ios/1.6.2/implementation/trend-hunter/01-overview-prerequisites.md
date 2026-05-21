# trend-hunter 改訂設計書

> **目的**: 13 ProblemType に関連するバイラルコンテンツをマルチソースから検出し、Aniccaの投稿hookに変換する
> **最終更新**: 2026-02-08
> **ステータス**: GUI作業完了（2026-02-08）— 実装準備OK
> **参照**: `1.6.2-ultimate-spec.md` の Phase 3 (3.2 trend-hunter)

---

## ⚠️ ユーザー事前作業（実装開始前に必ず完了すること）

> **この設計書のユーザー事前作業が全て完了するまで、実装を開始してはならない。**
> エージェントは実装開始前にこのチェックリストを確認し、未完了の項目があればユーザーに依頼すること。

### 実装前に必要なGUI作業

| # | サービス | 作業内容 | 所要時間 | 手順 | 取得するもの | 完了 |
|---|---------|---------|---------|------|------------|------|
| 1 | **TwitterAPI.io** | アカウント登録 + APIキー取得 | 2分 | ① https://twitterapi.io/ にアクセス → ② 「Sign in with Google」クリック → ③ ダッシュボードでAPIキーをコピー | `TWITTERAPI_KEY` | ✅（2026-02-08） |
| 2 | **reddapi.dev** | アカウント登録 + Liteプラン契約 + APIキー生成 | 5分 | ① https://reddapi.dev/auth にアクセス → ② Google/GitHubでログイン → ③ Liteプラン($9.90/月)購入 → ④ /account でAPIキー生成 | `REDDAPI_API_KEY` | ✅（2026-02-08） |
| 3 | **VPS環境変数追加** | 取得したキーをVPSの.envに追加 | 1分 | `ssh anicca@46.225.70.241` → `.env` に2つのキーを追記 → Gateway再起動 | - | ✅（エージェント実行予定） |

### GUI作業が不要なもの（確認済み）

| サービス | 理由 |
|---------|------|
| **Apify**（TikTokトレンド取得） | `APIFY_API_TOKEN` が GitHub Secrets に登録済み。`clockworks~tiktok-scraper` を既に運用中 |
| **TikTok Creative Center** | Apify経由で取得するため直接アクセス不要 |
| **Railway API** | `ANICCA_AGENT_TOKEN` が VPS .env に設定済み |
| **Brave Search** | `BRAVE_API_KEY` が VPS .env に設定済み |

### 確認事項（エージェント向け）

| # | 確認項目 | 方法 |
|---|---------|------|
| 1 | `APIFY_API_TOKEN` がVPSの `.env` にもあるか | `ssh anicca@46.225.70.241` → `grep APIFY ~/.env` |
| 2 | TwitterAPI.io の無料クレジット($0.10 = 666件)でテスト実行可能か | APIキー取得後に `curl` でテスト |
| 3 | reddapi.dev Liteプラン(500 calls/月)で十分か | 月間推定: 6回/日 × 3クエリ × 30日 = 540回 → **ギリギリ。要モニタリング**。P1 #4: 超過時は HTTP 429 返却。対策: reddapi レスポンスヘッダー `X-RateLimit-Remaining` を確認 → 残10以下で Reddit 検索スキップ + Slack #alerts に「reddapi quota低下: 残N件」警告。翌月1日にリセット。 |

### VPS .env に追記するキー

```bash
# 以下を /home/anicca/.env に追記
TWITTERAPI_KEY=<ダッシュボードからコピーした値>
REDDAPI_API_KEY=<アカウントページで生成した値>

# 追記後にGateway再起動
export XDG_RUNTIME_DIR=/run/user/$(id -u)
systemctl --user restart openclaw-gateway
```

---

## 0. 改訂の背景

### 現Specの問題

| 問題 | 詳細 |
|------|------|
| **苦しみキーワードに囚われすぎ** | `buddhism OR meditation OR anxiety` で検索 → ニッチすぎてバイラルに繋がらない |
| **トレンドを見てない** | 「今何がバズってるか」を検出してない。キーワード固定検索だけ |
| **データソースが曖昧** | X API + TikTok API と書いてあるが、具体的にどのエンドポイントか不明 |
| **hook候補の生成ロジックが弱い** | 「LLMで抽出」としか書いてない。トレンド→Aniccaアングルの変換が設計されてない |

### 改訂コンセプト

```
現在:  苦しみキーワード固定検索 → hook候補抽出
       ↑ ニッチすぎ、バイラルしない

改訂:  ProblemType別バイラル検出 → Aniccaアングル変換 → hook候補生成
       ↑ 既にバズっているものの中から、13個の苦しみに関連するものを見つける
```

### 2種類のバイラルコンテンツ

| タイプ | 内容 | Aniccaでの活用 |
|--------|------|---------------|
| **共感系** | 当事者が苦しみを語り、「わかる」「俺もそう」とバズっている | そのまま共感hookとして使える。「あなただけじゃない」系 |
| **問題解決系** | 専門家や一般人が「○○を手放す方法5選」等でバズっている | Aniccaの機能紹介hookに変換できる。「アプリでこれができる」系 |

---
