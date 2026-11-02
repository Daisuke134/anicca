# AGENTS.md — Codex / 全エージェント向け手順
1. 開始時: `git pull`。docs/team/README → RULES → OWNERSHIP → BOARD → 関連 specs/ を読む。
2. BOARD.md の「タスク」に `[自分の名前]` で claim してから作業。
3. 担当は重複防止の目印であり壁ではない。担当外でも支援・共同作業・引き継ぎを行う。最初に既存owner/進行状態/外部effectを確認し、同じタスクを二重実行しない。枠切れや停止は途中成果・次操作・未確認effectを保存し、受領を確認して担当を移す。
4. 終了時: BOARD.md「ログ」に1行追記、必要なら specs/ を更新 → commit → `git push`。競合したら `git pull --rebase` して再push。
5. 秘密情報は書かない。資格情報は各マシンのローカル（/workspace/.secrets など）をファイル名で参照。
6. 成田さんへは日本語。承認を求めない。無料トライアルは作らない。X投稿は加重≤270。
場所: GitHub Daisuke134/life-manager `docs/team/`（Mac mini は ~/team/BOARD.md がここを指す）。
