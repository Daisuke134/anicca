# Ops タスクループ設計案 — 24/365 自律改善の鍵

> 元メモ: anicca.md L454–497。OpenClaw 公式・Dev.to「Cheap Checks First」・Reddit 実例を踏まえた提案。

---

## 1. いま起きていること

- **workspace/ops/heartbeat_state.json** と **proposals.json** を **誰も書いていない**。
- そのため **ops-heartbeat**（読むだけ）は「次にやること」を生み出せず、**mission-worker** が読む **steps.json** も常に空のまま。
- 24時間365日「自分を改善し続ける」ためには、「**やるべきタスクを集める**」層が必須。

---

## 2. OpenClaw まわりで調べたこと

| ソース | 要点 |
|--------|------|
| [OpenClaw Heartbeat](https://docs.openclaw.ai/gateway/heartbeat) | Heartbeat は「定期でチェックリストを読んで HEARTBEAT_OK かアラートを返す」だけ。**固定時刻は cron を使う**。コスト注意: 毎回フルコンテキストで LLM を叩くと高額。 |
| [Dev.to: Cheap Checks First](https://dev.to/damogallagher/heartbeats-in-openclaw-cheap-checks-first-models-only-when-you-need-them-4bfi) | **まず安いチェック（スクリプト・API）で「変化あり/なし」だけ判定**。アラートが出たときだけ LLM で要約・判断。頻度は「重要なものを取りこぼさない」程度に（5–15分 / 30分 / 1–2時間など）。 |
| Reddit 実例 | 「cron heartbeats 15分」「**役割ごとにエージェントを分ける**（content, research, systems）」が現実的な運用として言及されている。 |
| Zenn 記事（$20 一晩で消失） | 30分ごとに Opus + 12万トークン送ると約 $0.75/回。**VPS 上の JSON だけ読んで LLM を叩かない「ローカル heartbeat」** にすれば同じ失敗は防げる（現状の ops-heartbeat 方針と一致）。 |

---

## 3. 提案: 3 層 + 1 ストア

| 層 | 役割 | 推奨名前 | 頻度・やり方 |
|----|------|----------|----------------|
| **タスク集め** | いろんな場所を探し、「やるべきこと」を **書くだけ**。実行しない。 | **task-collector**（スキル名） | cron 5–15分 or 30分。Slack・ユーザー依頼・メトリクス・trend-hunter 結果・「Paywall CVR 低い」等を **todo.json（後述）に追記**。 |
| **決定** | todo / proposals / heartbeat_state を読んで「次にどれを steps に 1 件出すか」を決める。 | **decider**（ops-heartbeat の名前変更候補） | cron 5–10分。**中身はルール＋軽いチェック優先**。必要時だけ小さいモデルで優先順位付け。**steps.json に 1 件ずつ追加**。 |
| **実行** | steps.json を読んで 1 件実行し、結果を completed に書き steps から削除。 | **executor**（mission-worker の名前変更候補） | cron 5–10分。実行係のみ。 |

**1 ストア:** **workspace/ops/todo.json**（あるいは tasks.json）。「今日やるべきタスク」のキュー。**書くのは task-collector、読むのは decider**。

---

## 4. JSON 案

### todo.json（タスクストア）

**書く人:** task-collector のみ。**読む人:** decider。

```json
{
  "tasks": [
    {
      "id": "uuid",
      "source": "user_request | metrics | trend_hunter | paywall_low | onboarding_low | ...",
      "summary": "1行要約",
      "detail": "任意の詳細やリンク",
      "priority": "high | medium | low",
      "createdAt": "ISO8601",
      "status": "pending"
    }
  ],
  "lastUpdated": "ISO8601"
}
```

- **task-collector:** ユーザー依頼・Slack・メトリクス（Paywall CVR 等）・trend-hunter の結果・「TikTok 複数アカウント」「英語投稿」などの気づきを **pending で追加**。
- **decider:** todo を読んで「今やる 1 件」を選び、**steps.json に 1 件追加**。必要なら todo の該当を `status: "in_progress"` などに更新（任意）。

### steps.json（現状のまま）

- **書く人:** decider のみ。**読む人:** executor。
- 形式は cron-skills-fix.md の 5.6 のとおり。executor が 1 件実行したら steps から削除し、結果を completed に追記。

### heartbeat_state.json / proposals.json

- **書く人:** decider（従来の ops-heartbeat の「評価・書く」部分）。
- 中身は現行仕様のまま。**proposals は「やりたいこと候補」、heartbeat_state は「状態・連続OK 数」**。decider が「proposals や todo を見て、次に steps に何を 1 件積むか」を決める。

---

## 5. スキル名・ジョブ名の整理

| 現状 | 提案（意図が伝わる名前） |
|------|---------------------------|
| ops-heartbeat | **decider**（何をいつやるか決める） |
| mission-worker | **executor**（決まった 1 件を実行する） |
| （なし） | **task-collector**（タスクを探して todo に追加する） |

- ジョブ ID は `decider` / `executor` / `task-collector` のままでもよいし、`ops-heartbeat` を残して「中身だけ decider 役」にしてもよい。
- SKILL.md の名前は **task-collector**, **decider**, **executor** にすると役割が明確になる。

---

## 6. 一つのエージェント vs サブエージェント（特化）

- **一つのエージェント:** メトリクス・Paywall・Onboarding・OpenClaw ユースケース・トレンドを全部見て「今一番やるべき 1 件」を決める。**入力が一箇所に集約できるなら、設計はシンプルで運用しやすい。**
- **サブエージェント特化:** Paywall 特化・Onboarding 特化・OpenClaw 新ユースケース特化など。**役割がはっきり分かれ、並列で回せるが、優先順位の調整と結果のフィードバック設計が増える。**

**推奨（現段階）:**  
まずは **一つの「タスクを集める」スキル（task-collector）** で、**入力源を複数持つ**形にする。

- 入力: ユーザー依頼（Slack 等）・メトリクス（Paywall/Onboarding 等）・trend-hunter / daily-memory の結果・「やるべきリスト」のファイル等。
- 出力: **todo.json に pending で追加**するだけ。  
そのうえで **decider が todo + proposals + heartbeat_state を読んで steps に 1 件ずつ積み、executor が実行**。  
ドメイン特化（Paywall 専用エージェント等）は、todo が増えすぎて優先度付けが重くなってから検討するのが現実的。

---

## 7. 頻度・コスト

- **task-collector:** 5分〜30分ごと。**中身は「ファイル・API・Slack を見て todo に追記」が中心。LLM は「要約や優先度をつけるとき」だけ使うとコストを抑えられる（Cheap Checks First に合わせる）。
- **decider:** 5–10分ごと。**heartbeat_state / proposals / todo を読むだけならスクリプトで十分。**「次に steps に何を 1 件積むか」をルール＋軽いロジックで決め、必要時だけ小さいモデルで判断。
- **executor:** 5–10分ごと。steps が空なら何もしない。**1 件実行したら steps から削除**し、結果は completed に書く。

これで **「誰かが todo に書く → decider が steps に 1 件積む → executor が実行」** のループが成立する。

---

## 8. 次のアクション（MUST）

| # | やること |
|---|----------|
| 1 | **workspace/ops/todo.json** のスキーマを決め、VPS に初期ファイルを置く。 |
| 2 | **task-collector スキル**を新規作成。入力源（Slack・メトリクス・trend 結果・ユーザー依頼メモ等）を列挙し、**todo に追記するだけ**の手順を SKILL に書く。cron で 5–30分ごとに実行。 |
| 3 | **decider**（現 ops-heartbeat）の SKILL を更新。**todo.json を読む**ことを明記し、「todo の pending から 1 件選び steps.json に 1 件追加する」条件を書く。heartbeat_state / proposals の更新は現行どおり。 |
| 4 | **executor**（現 mission-worker）は steps を読んで 1 件実行するだけなので、名前と SKILL の説明を **executor** に揃える。 |
| 5 | 名前を変える場合: ジョブ ID を `decider` / `executor` / `task-collector` にし、SKILL フォルダ名も合わせる（任意。後からでも可）。 |

---

## 9. 参照

- anicca.md L454–497（タスクリスト・Decider/Executor・24/365・サブエージェントのメモ）
- cron-skills-fix.md §5.6（heartbeat_state / proposals / steps の仕様）
- https://docs.openclaw.ai/gateway/heartbeat
- https://dev.to/damogallagher/heartbeats-in-openclaw-cheap-checks-first-models-only-when-you-need-them-4bfi
