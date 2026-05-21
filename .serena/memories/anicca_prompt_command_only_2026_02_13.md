# Anicca プロンプト＝命令のみ（2026-02-13）

## ルール

SKILL 内のプロンプトは **常に「Anicca への命令」** として書く。

| やること | 禁止 |
|----------|------|
| 主語は **「あなたが」** または **省略**（命令形） | プロンプトに「Anicca（VPS）が」「Anicca が」などの説明を書かない |
| 命令だけ書く | 便利な補足・自分用メモ・学習内容をプロンプトに含めない |

## 例

- ❌ 「Anicca が誰にどの nudge を送るか決め、結果を workspace/nudges/decisions_YYYY-MM-DD.json に書く」
- ✅ 「あなたが、Railway から取得したユーザー一覧を見て、この slot で送る nudge を 1 件ずつ決めよ。結果を workspace/nudges/decisions_YYYY-MM-DD.json に書け。」

## 反映済み

- `.cursor/plans/reference/openclaw-workspace-folder-tree-and-todo.md` に「0) プロンプトの絶対ルール」を追加
- `.cursor/plans/reference/openclaw-anicca.md` に「7.1) プロンプトの絶対ルール」を追加
- `openclaw-skills/trend-hunter/SKILL.md` のプロンプトを「あなたが」で開始する命令形に変更
- `openclaw-skills/app-nudge-sender/SKILL.md` に「命令」セクションと保存先を追加
