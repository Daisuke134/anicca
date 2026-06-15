# Git Trunk Reconciliation Implementation Plan ([1]#9)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. これはコード機能でなく **git整流 runbook**。TDDの代わりに各Phase末に **build/test verification gate** を置く。

**Goal:** `dev` を唯一の統合trunkとして確立し（dev←main, dev←release/1.8.7 を収束）、build/test 通過後に `dev→main`（本番）を PR 経由で反映する。以降 release/1.8.7 へ非リリース作業を積まない。

**Architecture:** dev は既に main比 423 ahead / 37 behind＝事実上のtrunk。①dev←main で main-only 37commit取込 ②dev←release/1.8.7 で release-only 69commit取込（conflictはdevで解決） ③dev で build/test ④dev→main を PR 経由（lefthookがmain直pushをblockするため）。apps/api 24ファイル変更が main 反映時に Railway 自動deployされる＝Phase 4 は本番デプロイとして gate する。

**Tech Stack:** git / lefthook(導入済) / gh CLI / apps/api(Node) build・test / aniccaios は対象外検証(コンパイルのみ任意)

**前提状態(2026-06-04実測):**
- dev=1ead7b8c (origin/dev=349b30b7 ＝ローカル先行・未push commitあり) / main=beb1ba38 / release/1.8.7=0a744103
- dev↔main: 423 ahead / 37 behind ／ dev↔release/1.8.7: 147 ahead / 69 behind
- CLAUDE.md: dev=363行(復元済) / release/1.8.7=95行(gutted) → **conflict時は dev(363) を採用**
- release/1.8.7→main code diff: 224ファイル(apps/ aniccaios/)、うち apps/api=24 (Railway自動deploy対象)

---

## File Structure（このplanが触る対象）

| 対象 | 責務 |
|---|---|
| branch `dev` | 唯一trunk。全mergeの収束先 |
| branch `main` | 本番。dev→PRでのみ更新 |
| branch `release/1.8.7` | 凍結（新規作業禁止）。内容はdevへ収束 |
| `CLAUDE.md` | conflict確実 → dev版(363行・HARD RULE #0あり)を採用 |
| `lefthook.yml` `commitlint.config.mjs` | dev固有・維持 |

---

## Task 1: dev のローカル未push commit を origin/dev に同期

**Files:** none（git操作）

- [ ] **Step 1: dev の未push確認**

Run:
```bash
cd ~/anicca-project && git branch --show-current && git log --oneline origin/dev..dev
```
Expected: `dev` 表示 + 未pushコミット列挙（GATE1 spec等）

- [ ] **Step 2: push（lefthook pre-push通過＝devは許可branch）**

Run:
```bash
git push -u origin dev 2>&1 | tail -3
git log --oneline origin/dev..dev
```
Expected: push成功 + 2行目の出力が空（=同期完了）

---

## Task 2: dev ← main マージ（main-only 37commit 取込）

**Files:** 複数（main側の更新）

- [ ] **Step 1: 作業前バックアップtag**

Run:
```bash
git tag backup/dev-pre-reconcile-2026-06-04 dev && echo "tagged"
```
Expected: `tagged`（事故時 `git reset --hard backup/dev-pre-reconcile-2026-06-04` で復旧可）

- [ ] **Step 2: dev に main を merge**

Run:
```bash
git checkout dev && git merge --no-ff main -m "merge: main into dev (trunk reconcile)" 2>&1 | tail -15
```
Expected: クリーンmerge or conflict列挙。**CLAUDE.md conflict が出たら Step 3**

- [ ] **Step 3: conflict解決（出た場合のみ）**

CLAUDE.md は必ず dev版(363行)を採用:
```bash
git checkout --ours CLAUDE.md && git add CLAUDE.md
# 他conflictは内容を読んで新しい/正しい方を採用。解決後:
git status --short | grep -E '^(U|AA|DD)' || echo "no remaining conflicts"
```
Expected: `no remaining conflicts` まで解決

- [ ] **Step 4: merge完了 + CLAUDE.md健全性確認**

Run:
```bash
git commit --no-edit 2>/dev/null; grep -c "HARD RULE #0" CLAUDE.md
```
Expected: HARD RULE #0 が 1以上（363行版維持）

---

## Task 3: dev ← release/1.8.7 マージ（release-only 69commit 取込）

**Files:** 多数（content/spec/seo + apps/aniccaios コード）

- [ ] **Step 1: 取込まれる内容を事前把握（commit分類）**

Run:
```bash
git log dev..release/1.8.7 --oneline | sed -E 's/^[0-9a-f]+ //; s/[:(].*//' | awk '{print $1}' | sort | uniq -c | sort -rn | head
git diff dev..release/1.8.7 --name-only | grep -cE '^apps/api/'
```
Expected: カテゴリ集計 + apps/api 変更数（本番影響の把握）

- [ ] **Step 2: dev に release/1.8.7 を merge**

Run:
```bash
git merge --no-ff release/1.8.7 -m "merge: release/1.8.7 into dev (trunk reconcile)" 2>&1 | tail -20
```
Expected: conflict列挙（CLAUDE.md確実 + 重複編集ファイル）

- [ ] **Step 3: conflict解決**

```bash
git checkout --ours CLAUDE.md lefthook.yml commitlint.config.mjs 2>/dev/null; git add CLAUDE.md lefthook.yml commitlint.config.mjs 2>/dev/null
# 残りは1つずつ git diff で確認し新しい/正しい方を採用
git diff --name-only --diff-filter=U
```
Expected: 最終的に上記が空（全conflict解決）

- [ ] **Step 4: merge commit + 健全性**

Run:
```bash
git commit --no-edit 2>/dev/null; grep -c "HARD RULE #0" CLAUDE.md; git status --short | head
```
Expected: HARD RULE #0 ≥1 / working tree clean（untracked除く）

---

## Task 4: dev の verification gate（build/test）— **本番反映前の関門**

**Files:** apps/api（Railway自動deploy対象）

- [ ] **Step 1: apps/api 依存・build**

Run:
```bash
cd ~/anicca-project/apps/api && npm ci 2>&1 | tail -3 && npm run build 2>&1 | tail -10
```
Expected: build成功（exit 0）。失敗なら systematic-debugging で修正してから先へ（赤のままdev→main禁止）

- [ ] **Step 2: apps/api test**

Run:
```bash
cd ~/anicca-project/apps/api && npm test 2>&1 | tail -20
```
Expected: test pass（exit 0）。test scriptが無ければ「test未定義」と記録し build成功を関門とする

- [ ] **Step 3: 本番反映される apps/api 差分をレビュー（自分の目で）**

Run:
```bash
cd ~/anicca-project && git diff origin/main..dev -- apps/api --stat | tail -30
```
Expected: 変更ファイル一覧を読み、破壊的/未完成な本番変更が無いか確認。疑わしい変更があれば該当commitを特定し、dev→main前に解決 or revert

- [ ] **Step 4: dev を push**

Run:
```bash
git push origin dev 2>&1 | tail -3
```
Expected: push成功（lefthook pre-push通過）

---

## Task 5: dev → main を PR 経由で反映（本番デプロイ）

**Files:** none（main更新＝Railway自動deploy）

- [ ] **Step 1: PR作成（lefthookがmain直pushをblockするためPR必須）**

Run:
```bash
gh pr create --base main --head dev --title "merge: dev trunk reconcile → main (2026-06-04)" --body "dev=唯一trunk確立。main←(main+release/1.8.7収束)。apps/api変更含む=Railway自動deploy。build/test pass済(Task4)。" 2>&1 | tail -3
```
Expected: PR URL 出力

- [ ] **Step 2: PR merge（build/test pass確認済を前提に）**

Run:
```bash
gh pr merge --merge --delete-branch=false 2>&1 | tail -3
git fetch origin && git rev-list --left-right --count origin/main...origin/dev
```
Expected: merge成功 + `0	0`（main と dev が一致＝収束完了）

- [ ] **Step 3: 本番(main)反映の事後確認**

Run:
```bash
git checkout main && git pull --ff-only && grep -c "HARD RULE #0" CLAUDE.md && git log --oneline -1
git checkout dev
```
Expected: main に HARD RULE #0 復活(≥1) + 最新commit確認。Railway deploy はダッシュボードで別途緑確認（任意）

---

## Task 6: release/1.8.7 凍結ポリシーの徹底

**Files:** none（運用ルール）

- [ ] **Step 1: release/1.8.7 は App Store 1.8.7 提出専用・新規作業禁止を宣言**

release/1.8.7 の中身は dev/main に収束済。今後の作業は **dev のみ**。release/1.8.7 は 1.8.7 が App Store でship後に `git branch -d release/1.8.7` で削除（本planでは削除しない＝提出中の可能性）。lefthook が release/* への直commit/pushを既にblock済。

- [ ] **Step 2: 完了記録**

Run:
```bash
echo "git trunk reconcile done $(git rev-parse --short origin/main)" 
```
Expected: 完了ログ。task #9 を completed に。

---

## Self-Review

- **Spec coverage** (master §2 Git方針): dev=trunk確立(Task2,3) ✓ / main=PR-only(Task5 PR経由) ✓ / release凍結(Task6) ✓ / lefthook既導入 ✓ / GitHub Pro server-side ruleset=別途(master §3 task[1]⑥・本planでは無料local層で運用、Pro加入は任意後続)
- **Placeholder scan**: 全Stepに具体git/npmコマンド+expected。conflict解決の「1つずつ確認」は手順を明示(diff確認→採用)で具体 ✓
- **Risk**: 最大リスク=dev→mainでapps/api 24変更がRailway本番deploy。Task4のbuild/test gate + apps/api差分目視 + PR経由 で多層防御。backup tag(Task2 Step1)で復旧可 ✓
- **整合**: branch名・HEAD・ahead/behind は実測値。CLAUDE.md conflict解決方針(dev363採用)を全mergeで統一 ✓

## 未確定（実行時に判断）
- apps/api の test script 有無（Task4 Step2で分岐）
- release/1.8.7 merge の conflict 件数（実行して判明・Task3で1つずつ解決）
</content>
