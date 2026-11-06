# BusinessRun Bench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. State and task order remain in the unified SSOT.

**Goal:** 既存の自律企業評価を実際に実行し、再利用できるOSS/cloud runnerと実測記事を提供する。

**Architecture:** Python標準ライブラリのrunnerから固定した公式checkoutのCLIを呼ぶ。Business Bench/CoffeeBench/YC-Benchのscoreを保持し、独自graderを重複実装しない。Naïveの非公開環境はaccess条件を記録する。

**Tech Stack:** Python 3.12、Bash、GitHub Actions、公式上流requirements。native CLIのモデル既定を変更しない。

**Spec:** `docs/superpowers/specs/2026-11-02-businessrun-bench-design.md`

## Global Constraints

- canonical sourceは `products/businessrun-bench/`。run state/secret/third-party checkoutはrepo外。
- run IDは新規専用directory、公開receiptはallowlist、未知の費用はnull。
- official full protocolと短縮pilot、scriptとLLM、local developmentと隔離cloudを分ける。
- 他者のloop/secret/spend-capを変更しない。UIモデル設定を上書きしない。

## Review Focus

- exit0でもmissing/failed taskを成功としない。
- API費用推計が無いmodel runを0ドルとしない。
- 既存runの上書き・別protocolの結果混在を拒否する。
- raw model outputやERP tokenを公開artifactへ入れない。
- 上流変更・未完trial・非公開suiteを隠して比較しない。

## Task 1: catalogと実行/receipt契約

Owned files: `products/businessrun-bench/{catalog.json,bench.py,test_bench.py,README.md,LICENSE}`。

1. falsy passed、unknown cost、missing artifacts、repeat run拒否、公開allowlistの失敗テストを書く。
2. `python3 -m unittest discover -s products/businessrun-bench -p 'test_*.py'` をRED確認。
3. 最小runner、pin、既存CLIへのadapter、receiptを実装し同テストをGREEN。
4. 上流公式baselineを実行しreceiptを作る。spec状態を更新しcommit/push。

## Task 2: 実modelとcloud

Owned files: `products/businessrun-bench/native_adapter.sh`, `products/businessrun-bench/.github/workflows/benchmark.yml`。

1. native adapterがモデルを強制せず、失敗がそのままtrial結果へ残ることを確認する。
2. Business Bench実model試行を走らせ、state/grader/usageから結果を確認する。APIアクセス不能なら境界を追加観測し、他の利用可能routeを使う。
3. Ubuntu Actionsで同じbaselineを実行。private sourceから公開用subtreeをreviewしてmirrorし、run artifactと公開readbackを確認。

## Task 3: 実測と記事

Owned files: `docs/research/2026-11-02-naive-autonomous-companies.md`, `docs/articles/2026-11-02-naive-autonomous-company-ja.md`, unified SSOT本lane節。

1. Naïve全9評価の比較条件と恣意的選択/未公開の限界、追加catalog、Grok/Museの新証拠を更新。
2. 実行済み/失敗/未実行、コマンド、run条件、結果、費用の限界を記事へ記載。
3. 独立read-only review、focused tests/CI、main統合、公開source/Actions readbackを実施。

## 実行記録

- 設計判断: Business Bench Processに相当課題があるため、新しい事業simulatorは作らず上流を利用する。無駄な再実装を避ける。独自課題/managed SaaS全体の未完は保持する。
- 初回probe: Claude CLIはOAuth expiredで認証不能。CoffeeBenchの90日passive/heuristic baselineは完走。YCの初回direct invocationはSTRATEGIES値のtupleをcallableとして渡して失敗したため、型を確認して修正して再実行する。
- 訂正/進行: Coffeeの2試行は全5背景actorをpassiveにした環境controlであり、公式Sonnet背景baselineとは別条件。YCはtupleを展開してdefault世界・4script×3seedsを再実行し全12試行のterminalを取得。Codex native probeは成功、ClaudeはOAuth expiredを保持する。
- Task1: runner欠落をassertする6テストがRED→最小runnerで6/6 GREEN。独立builder checkの新規cwd・費用unknown・背景条件・答案隔離の4点を設計と実装へ反映する。
