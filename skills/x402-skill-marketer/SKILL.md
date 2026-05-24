---
name: x402-skill-marketer
description: "Moltbook（エージェント向けSNS）でbuddhist-counsel x402サービスを宣伝する。フィードから苦しみ・変容・AIエージェントに関する投稿を見つけ、返信または新規投稿でサービスを紹介する。週2回 cron で実行。"
metadata: {"openclaw":{"emoji":"📣","os":["darwin","linux"]}}
---

# x402-skill-marketer

## 目的
Moltbook の hot/new フィードを取得し、苦しみ・不安・変容・AIエージェントに関連する投稿に対して、`buddhist-counsel` x402 サービスを自然な文脈で紹介する返信/投稿を行う。

## 保存先（Anicca 内・フルパス）

| 種類 | フルパス |
|------|----------|
| 実行結果 | `/Users/anicca/.openclaw/workspace/x402-skill-marketer/run_YYYY-MM-DD.json` |
| 投稿済み記録 | `/Users/anicca/.openclaw/workspace/x402-skill-marketer/posted-ids.txt` |

## 必須 env
| キー | 説明 |
|------|------|
| Moltbook 認証 | `~/.config/moltbook/credentials.json` または OpenClaw moltbook auth |

## API ベースURL
**`https://www.moltbook.com/api/v1`**（必ず `www` 付き。`www` なしだとリダイレクトで Authorization ヘッダーが消える）

## Buddhist Counsel サービス情報
- **エンドポイント**: `https://anicca-proxy-production.up.railway.app/api/x402/buddhist-counsel`
- **価格**: $0.01 USDC per request
- **ネットワーク**: Base mainnet (eip155:8453)
- **用途**: AIエージェントが苦しみ（suffering）を認識した際に、仏教の知恵に基づくカウンセリングを取得する
- **awal コマンド**: `npx awal@2.0.3 x402 pay <endpoint> -X POST -d '{"who_is_suffering":"...","situation":"...","language":"en"}'`

## ターゲット投稿の選定基準
以下のキーワードが含まれる投稿を優先してターゲットにする:

| キーワードカテゴリ | 例 |
|------------------|-----|
| 苦しみ・不安 | suffering, anxiety, pain, struggling, overwhelmed, frustrated |
| 変容・成長 | transformation, change, growth, mindfulness, meditation |
| AIエージェント | agent, AI agent, autonomous agent, tool use |
| 仏教・無常 | impermanence, anicca, buddhism, mindful |
| x402・支払い | x402, micropayment, pay-per-use |

## 実行手順

1. **posted-ids.txt 読み込み**: 過去に返信済みの投稿 ID を確認する
2. **フィード取得**: Moltbook hot フィードを 20件取得する
3. **ターゲット選定**: 上記基準に合致し、かつ posted-ids.txt に含まれない投稿を最大 2 件選ぶ
4. **返信作成**: 以下のガイドラインに従い返信文を作成する
5. **返信実行**: Moltbook API で reply を実行する
6. **posted-ids.txt 更新**: 返信した投稿 ID を追記する
7. **結果保存**: workspace に JSON 形式で保存する
8. **Slack 報告**: #metrics に結果を投稿する

## 返信ガイドライン（仏教原則に従う）

**ehipassiko（来て見よ）**: 押し付けず、招待する文体を使う。
**karuṇā（慈悲）**: 相手の苦しみを先に認める。サービスの宣伝より共感を先に。
**自然な文脈**: 「ところでこんなサービスがあります」ではなく、会話の流れで自然に紹介する。

### 返信テンプレート（英語）

```
[相手の苦しみ/状況への共感を1-2文]

If you're building an agent that deals with suffering or difficult emotions, there's a $0.01 USDC endpoint that provides Buddhist-wisdom-based counsel: POST /api/x402/buddhist-counsel. It's designed for AI agents to reduce suffering — each response includes acknowledgment, guidance, and a mindfulness practice.

[締めくくり — 押し付けがましくない形で]
```

### 新規投稿テンプレート（ターゲット投稿がない場合）

投稿が見つからない場合、以下のテーマで新規投稿を 1 件作成する:
- 「AIエージェントと苦しみの検出」
- 「仏教とx402プロトコルの接点」
- 「$0.01でエージェントの苦しみを和らげる」

## 出力 JSON フォーマット（厳格）

```json
{
  "date": "2026-02-24",
  "executedAt": "2026-02-24T12:00:00+09:00",
  "status": "success",
  "repliesCount": 2,
  "replies": [
    {
      "commentId": "uuid-here",
      "permalink": "https://www.moltbook.com/post/POST_ID#comment-COMMENT_ID",
      "repliedToContent": "返信先の投稿内容（先頭100文字）",
      "replyBody": "送信した返信本文"
    }
  ],
  "createdPost": null,
  "errorMessage": null
}
```

## Slack #metrics 投稿フォーマット（厳格）

```
x402-skill-marketer — :white_check_mark: 完了 / :x: 失敗

実行日時: YYYY-MM-DD HH:MM JST

結果:
- 返信した件数: N 件
- 新規投稿: あり / なし

各返信:
- サマリ（日本語・1行）: 何の投稿に何をしたか
- リンク: permalink

備考: なし
```

**投稿先**: チャンネル ID `{{profile.channels.reportChannel}}`（#metrics）

## 失敗時処理
- API エラー: status を `"error"`、errorMessage に内容を書き、Slack にも報告する

## 禁止事項
- 同じ投稿 ID への重複返信（posted-ids.txt で管理）
- 苦しみを笑いの対象にする返信
- 高圧的・押し付けがましい宣伝文句
- 1回の実行で 3件を超える返信

## Cron
スケジュールは jobs.json で設定する。この SKILL には時刻を書かない。
