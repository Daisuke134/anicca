# Loop Engineering — 知識体系インデックス（記事/本の目次・積み上げ式）

> 目的: Anicca が **loop engineering を誰よりも深く理解し**、Franklin と agent economy を人間ゼロで自己拡大させるための知識を、1箇所に積み上げる。
> これは「how to make agents self-improve without human dilution」= 我々の最大級の記事/本（JP+EN）の原稿母体。
> ファイルが大きくなったらこのフォルダに新章を足していく（stacking）。各トピックの正本は1ファイルのみ、他からは参照リンク。

## 章立て（現在）

| # | ファイル | 内容 | 状態 |
|---|---|---|---|
| 序 | `../superpowers/specs/2026-07-07-loop-engineering-goldmine.md` | 全ソース精読の金脈（loop eng定義/RSI/Replit continual learning/cobus実装）+ 全ASCII | ✅ 記事本体の下敷き |
| 設計 | `../superpowers/specs/2026-07-07-loop-engineering-out-of-loop-design.md` | 実装設計（out-of-loop 3段・SI-*フェーズ・SI-1棚卸し結果・cheap wins） | ✅ 実行計画の正本 |
| 01 | `01-loop-vs-goal-resolved.md` | ★「loop は goal を含むのか?」の決定的解決（概念=YES / ツール=逆に/goalがloopを含む / 真の軸=done を誰が判定するか）★ | ✅ 完了（外部一次情報つき） |

| 03 | `03-franklin-as-nested-loops.md` | ループの実装: 私(human-funded=人間へ) vs Franklin(self-funded=agent economyへ)、5レイヤー実装、done 3値、分担/順番、着手STEP A-D | ✅ 完了 |
| 04 | `04-the-two-loops.md` | ★核心★ 2つの別ループ: 私のMAIN loop(建築家/親/投資家=経済を建て監視し資金投入、消えるのがゴール) vs Franklinのloop(経済の当事者)。side trading loopは別機械。Dais完全out・cobus pattern合成・discuss→issue→loop | ✅ 完了 |

## 積み上げ予定（stacking backlog）
- `02-danger-of-unsupervised-loops.md` … Ralph Wiggum loop / verifier theater / cognitive surrender / security tax の詳細と対策
- `04-observable-done-conditions.md` … 各 earn ループの観測可能 done カタログ（on-chain realized / order id / URL / test-green）
- `05-evo-driven-development.md` … eval-driven-earning（calibration drift + bandit arm + fresh adversary curation-gate）の設計と復活
- `06-continual-learning-3layers.md` … Replit の model/harness/context 3層を Anicca に写経した詳細

## 一貫して守る原則（全章共通）
1. 全判断に出典（source名 + URL + 核心一文）。引用のない主張は書かない。
2. concept（抽象）と tool（Claude Code の `/loop`・`/goal`）を必ず区別して書く。
3. 安全第一: 無人ループは「柵（denylist/spend cap/kill）+ 第二の目（fresh adversary）+ 偽造不能な成功シグナル（on-chain money）」の中でのみ回す。
4. Franklin（self-funded）だけが目的。human-funded loop（claude-p）は harness を作る足場であって目的ではない。
