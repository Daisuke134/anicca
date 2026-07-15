# レビュー状態台帳 — 2026-07-12-how-to-build-the-agent-economy-jp.md

EDITOR PROTOCOL: **REVIEWED = 承認済み = 絶対に触らない**（byte-for-byte 固定）。指摘された箇所だけ直す。

| ブロック | 見出し | 状態 |
|---|---|---|
| タイトル | エージェント経済の作り方：誰が、どう作っているのか。そして何がまだ足りないのか | **REVIEWED（触るな）** |
| [0] | 概要（箇条書き） | **REVIEWED（触るな。箇条書きの形も本文も原文のまま）** |
| [1] | いちばん賢いAIが、自分のサーバー代すら払えない | **REVIEWED（触るな）** |
| [2] | そもそも「エージェント経済」とは何か | **REVIEWED（触るな）** |
| [3] | 理想のかたち：エージェント経済に必要な「10の部品」 | **REVIEWED（触るな）** |
| [4] | 今どこまで出来たか：下半分は完成、上半分はまだ | **REVIEWED（触るな）**。2026-07-14「ハンコを押すだけでも5%」claim、ACPSimple.sol直読みで事実確認済み(DEEP-QUESTIONS.md参照) |
| [5] | 「AIが稼いだ」の9割の正体 | **REVIEWED（触るな）**。2026-07-14 stop-ai-slop-jp適用済み(冒頭meta-narration削除、3項目二重列挙を統合) |
| [6] | 核心：AIが払い合うだけなら、本物の金はどこから入るのか | 未 |
| [7] | 私たちはどう作っているか | 未 |
| [8] | エージェント経済を作りたい人へ | 未 |
| [9] | 最後に | 未 |
| 補足 | 📌補足 ×2 | 未 |
| 出典 | 出典 | 未 |

---

## セッションログ 2026-07-15（up-to-date 化・二度と hallucinate しない為の記録）

- **本物の SoT はこの3つだけ**: ①このファイル（記事ブロック状態）②handover `.claude/handovers/2026-07-14_0629.md` の Goal A ③`docs/superpowers/specs/2026-07-13-profitable-claude-earn-loops-spec.md`。これ以外を「SoT」と呼ばない。
- 今セッションで作った `docs/superpowers/specs/2026-07-14-article-earn-loop-ssot.md` は **SoT ではない** = skill選定/収益化の research メモ扱い（参照可、正本ではない）。
- **skill 実験（別ファイル、原本は git clean で無傷）**:
  - `...-jp-k16.md` = k16shikano skill で全文書き直し（比較用）。★REVIEWED ブロック(タイトル/[0]-[5])も改変している = EDITOR PROTOCOL 上、凍結ブロックへのマージ禁止★
  - `...-en.md` = ECC+Karpathy+stop-slop の EN 版（EN publish 候補）
  - 採用するなら **未ブロック([6]-出典)のみ**、かつ Dais 承認後。凍結ブロックは原本のまま。
- **ブロック状態は上表のまま変化なし**: [6][7][8][9]+補足×2+出典 は依然 **未承認**（今セッションで承認は取っていない）。
- **次アクション = [6]-出典の Dais 最終承認 → REVIEWED 化 → JP/EN draft publish（Goal A）。** loop 化/skill移植は Goal A 完了後の別アーク。
