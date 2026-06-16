# Operating Model — No-Human-In-Loop 開発と検証、 + 実践記事シリーズ

- **Date**: 2026-06-16
- **Status**: ACTIVE (canonical operating-model spec)
- **Branch**: dev
- **Owner**: Claude Code (dev IDE) — Dais は監督のみ、 ループには入らない
- **Supersedes**: 旧 HARD RULE 0.36 (STRICT-SEQUENTIAL + Dais approval gate) — 2026-06-16 に廃止済

## 1. 背景と確定事項

Dais 2026-06-16 verbatim の3点訂正:
1. 「strict-sequential + Dais approval gate」(旧 0.36) は ★廃止★ — 人間をループに入れる設計で、 我々のやり方と矛盾。
2. ★ human gate が存在すること自体がおかしい ★ — publish / submit / release / 送金 / CAPTCHA / password も全部 agent が実行。 人間に「go」を求める瞬間 = 罪。
3. 検証も人間ではなく AI が行う。 「今までは自分で検証できなかったから人間がやっていた。 検証も AI がやる」。 browser・E2E を agent 自身が回し切ることで人間を**完全に代替**する。

→ CLAUDE.md (global) の HARD RULE 0.36 は no-human-in-loop 版に書き換え済。

## 2. 運用モデル (= ベース)

main セッション(私)= オーケストレーター兼エンジニア。 タスク種別で3モードを使い分け、 ゲートは「人間 approval」ではなく「AI 検証」。

| モード | いつ使う | 検証の閉じ方 |
|---|---|---|
| **直接 + subagent** | 逐次実装の土台。 設計は main(thinking)、 読込/探索/並列実装は subagent | 私の独立 E2E verify |
| **dynamic workflow (`ultracode`)** | 境界の明確な fan-out(監査/リサーチ/多角設計/content judge panel)。 中に verifier を組み込む | workflow 内 verifier(maker≠checker) + 私の二重チェック |
| **/loop** | 定期 discovery→実装→検証→次 を自走 | loop 内 verifier + 停止条件 |
| **/goal** | 機械検証可能な収束(tests pass / build green / curl 200) | 別 checker model が毎ターン判定 |

- **インフラ**: worktree(並列編集時 + cleanup 必須 HARD 0.26)、 agent-view(監視)。
- **低優先**: agent teams(experimental・高コスト。 fan-out は workflow が安く決定的)。
- **最終形**: L3 完全自律。 L1(report)→L2(verifier付)→L3(unattended) は品質担保の立ち上げ順序であって人間 approval ではない。

## 3. 検証 5層スタック (= 人間の代替、 MUST 全層)

| 層 | 仕組み | 代替対象 |
|---|---|---|
| 1. Maker ≠ Checker | workflow/loop 内で作る agent と別の verifier(複数・別視点で「反証しろ」・過半数 vote) | 人間レビュー |
| 2. 機械検証可能停止条件 (/goal) | done を exit 0 コマンドで定義。 別 checker model が判定 | 人間 OK |
| 3. E2E 実観測 | browser 実操作 / frame 抽出 / OTP read / screenshot 差分 (HARD 0.31) | 人間が触って確認 |
| 4. 私の独立二重チェック | workflow 自己申告を信じず main が fresh evidence で再検証 (HONESTY rules) | 第二の人間の目 |
| 5. fact-checker subagent | write 権限ゼロで全 claim を VERIFIED/WRONG/UNVERIFIABLE | 監査 |

**鉄則**: 人間の安全網が無い以上、 検証は弱めず**厚く**する。 verifier の verdict は必ず実コマンド/実観測に接地(= "verifier theater" 禁止)。 「人間しかできない」と感じたら頼むのでなく verifier を増やす + E2E を browser 実走まで深める。

## 4. 実プロジェクト = 実践記事シリーズ「人間をループに入れない開発」

build-in-public。 公開先 = Zenn + aniccaai.com(HARD 0.19 content factory / anicca-persona)。 形式 = 「現ベストプラクティス → 実践してみた → 結果」。

| # | 記事 | 中身 | 一次ソース |
|---|---|---|---|
| 1 | ダイナミックワークフロー (ultracode) 徹底解説 + 実践 | 概念/phase/agent・parallel・pipeline/schema/resume/cost + 実際に1本走らせた記録 | claude.com/blog, code.claude.com/docs/en/workflows, lxcong/awesome-claude-dynamic-workflows, zenn nogu66 |
| 2 | ループエンジニアリング (/loop + /goal) 徹底解説 + 実践 | 5 building blocks + maker≠checker + /goal 停止条件 + 実際に loop を自走させた記録 | Addy Osmani loop-engineering, cobusgreyling, zenn suwash, code.claude.com/docs/ja/goal |
| 3 | 人間ゼロで検証精度を上げる | §3 の検証5層を合体させた全体像 + 実践結果 + verifier theater 回避 | §3 + worktrees/agent-view docs |

**ドッグフーディング(核心)**: 各記事を書く工程そのものを no-human-in-loop の運用モデルで回す — workflow がリサーチ&草稿(fan-out: docs reader + example miner + draft writer)→ adversarial verifier が一次ソース照合 → 私が二重チェック → content factory で公開。 記事の「実践してみた」節 = その実走ログそのもの。

## 5. タスク分解 (= §2-4 を実行)

1. 運用モデルを project CLAUDE.md にルーティング規則として追記
2. 記事#1: dynamic workflow / ultracode docs を深く再読(一次ソース全部)
3. 記事#1: 実際に小さな workflow を1本走らせ run ログ採取
4. 記事#1: 草稿 → adversarial verifier 照合 → 二重チェック → 公開
5. 記事#2: loop-engineering / /loop / /goal 再読 + loop 自走実践 + 記事
6. 記事#3: 検証5層 全体像 + 実践 + 記事
7. 各記事公開を E2E verify(URL live + 本文一致)

## 6. 検証基準 (各タスク完了の定義)

- spec/CLAUDE.md 変更: diff + push hash。
- workflow 実践: `/workflows` 実行ログ + 成果物 + token 実数(捏造禁止 HARD 0.24)。
- 記事公開: 公開 URL curl 200 + 本文が草稿と一致 + 一次ソース引用が実在(HARD 0.31)。
- 全 claim: fact-checker subagent VERIFIED。
