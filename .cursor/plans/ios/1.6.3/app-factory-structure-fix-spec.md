# app-factory-structure-fix — Spec

**作成日:** 2026-02-28

---

## 1. 概要（What & Why）

### What
app-factory で作るアプリのスペック・コード・アセットが、リポジトリ内の複数の異なるフォルダに分散している。全アプリを `daily-apps/{slug}/` 1フォルダに統一する。

### Why
- スペックとコードが別々のフォルダにあると、どのアプリのどのファイルか追えない
- `daily-apps/` に揃えることで Mac Mini も含めた全環境でアプリの所在が明確になる
- mobileapp-builder SKILL.md が間違ったパスを指定しているため、次回以降のアプリ生成が壊れる

---

## 2. 受け入れ条件

| # | 条件 |
|---|------|
| 1 | `anicca-project/daily-apps/breath-calm/` にスペック4ファイルとXcodeプロジェクト両方が存在する |
| 2 | `anicca-project/.cursor/app-factory/breath-calm/` は削除されている |
| 3 | `anicca-project/breath-calm-app/` は削除されている |
| 4 | `daily-apps/breath-calm/spec/02-spec.md` の `output_dir` が `daily-apps/breath-calm/BreathCalmios` を指している |
| 5 | `/Users/cbns03/Downloads/mobileapp-builder/SKILL.md` の spec パスが `daily-apps/{slug}/spec/` に更新されている |
| 6 | `/Users/cbns03/Downloads/mobileapp-builder/SKILL.md` の `output_dir` が `daily-apps/{slug}/` に更新されている |
| 7 | `/Users/cbns03/Downloads/mobileapp-builder/SKILL.md` の worktree パスが `anicca-project` 内の `daily-apps/{slug}/` を使う形に更新されている |
| 8 | 全変更が GitHub に push されている（`anicca-project` dev ブランチ + `mobileapp-builder` main ブランチ） |
| 9 | Mac Mini で `git pull` すれば同じ構造になる |

---

## 3. As-Is / To-Be

### As-Is（現状）

```
anicca-project/
├── .cursor/app-factory/breath-calm/   ← スペック4ファイル（ここ）
│   ├── 01-trend.md
│   ├── 02-spec.md   (output_dir = breath-calm-app/ ← 間違い)
│   ├── 03-plan.md
│   └── 04-tasks.md
├── breath-calm-app/                   ← Xcodeプロジェクト（ここ）
│   └── BreathCalmios/
│       └── BreathCalm.xcodeproj
└── daily-apps/
    ├── daily-dhamma-app/
    └── rork-thankful-gratitude-app/   ← breathcalmはここにない
```

mobileapp-builder/SKILL.md の間違いパス：
```
spec 読み取り: .cursor/app-factory/{slug}/02-spec.md  ← 旧パス
output_dir:    {任意}/                                 ← 未統一
worktree:      ~/Downloads/anicca-{slug}               ← リポジトリ外
```

### To-Be（正しい状態）

```
anicca-project/
└── daily-apps/
    ├── daily-dhamma-app/
    ├── rork-thankful-gratitude-app/
    └── breath-calm/                   ← 全部ここに統一
        ├── spec/
        │   ├── 01-trend.md
        │   ├── 02-spec.md   (output_dir = daily-apps/breath-calm/BreathCalmios)
        │   ├── 03-plan.md
        │   └── 04-tasks.md
        └── BreathCalmios/
            └── BreathCalm.xcodeproj
```

mobileapp-builder/SKILL.md の正しいパス（更新後）：
```
spec 読み取り: daily-apps/{slug}/spec/02-spec.md
output_dir:    daily-apps/{slug}/
worktree:      anicca-project 内（F6ルールに従い branch = app-factory/{slug}）
```

---

## 4. テストマトリックス

| # | To-Be | 確認方法 |
|---|-------|---------|
| 1 | breath-calm/spec/ に4ファイル存在 | `ls daily-apps/breath-calm/spec/` |
| 2 | breath-calm/BreathCalmios/ に xcodeproj 存在 | `ls daily-apps/breath-calm/BreathCalmios/` |
| 3 | 旧フォルダ2つが消えている | `ls .cursor/app-factory/breath-calm/` → not found |
| 4 | SKILL.md のパス更新確認 | `grep "daily-apps" /Users/cbns03/Downloads/mobileapp-builder/SKILL.md` |
| 5 | GitHub push 確認 | `git log --oneline -1` |

---

## 5. 境界

### やること
- `breath-calm-app/` → `daily-apps/breath-calm/BreathCalmios/` に移動
- `.cursor/app-factory/breath-calm/` → `daily-apps/breath-calm/spec/` に移動
- `02-spec.md` の `output_dir` フィールドを更新
- `mobileapp-builder/SKILL.md` の spec パス・output_dir・worktree パスを更新
- `git add -A && git commit && git push` （anicca-project dev ブランチ）
- `git add -A && git commit && git push` （mobileapp-builder main ブランチ）

### やらないこと
- BreathCalm の Swift コードは一切触らない
- Xcodeプロジェクト設定（xcodeproj の中身）は変えない
- 他のアプリ（daily-dhamma-app, rork-thankful等）は移動しない
- Mac Mini への SSH は不要（GitHub push → Mac Mini が git pull するだけ）

---

## 6. 実行手順

### Step 1: anicca-project でフォルダ移動
```bash
cd /Users/cbns03/Downloads/anicca-project

# 新フォルダ作成
mkdir -p daily-apps/breath-calm/spec

# スペック移動
mv .cursor/app-factory/breath-calm/01-trend.md daily-apps/breath-calm/spec/
mv .cursor/app-factory/breath-calm/02-spec.md daily-apps/breath-calm/spec/
mv .cursor/app-factory/breath-calm/03-plan.md daily-apps/breath-calm/spec/
mv .cursor/app-factory/breath-calm/04-tasks.md daily-apps/breath-calm/spec/
rmdir .cursor/app-factory/breath-calm

# コード移動
mv breath-calm-app/BreathCalmios daily-apps/breath-calm/BreathCalmios
rmdir breath-calm-app
```

### Step 2: spec の output_dir を更新
```
daily-apps/breath-calm/spec/02-spec.md の output_dir を
  旧: /Users/cbns03/Downloads/anicca-project/breath-calm-app
  新: /Users/cbns03/Downloads/anicca-project/daily-apps/breath-calm
に変更
```

### Step 3: mobileapp-builder/SKILL.md を更新
以下3箇所を更新：
1. PHASE 0 PRE-FLIGHT STEP 0 の spec 読み取りパス
2. PHASE 0.5 の output_dir デフォルト値
3. worktree のパス

### Step 4: 両リポジトリを push
```bash
# anicca-project
cd /Users/cbns03/Downloads/anicca-project
git add -A && git commit -m "refactor(app-factory): move breath-calm to daily-apps/" && git push origin dev

# mobileapp-builder
cd /Users/cbns03/Downloads/mobileapp-builder
git add -A && git commit -m "fix: update spec/output_dir paths to daily-apps/{slug}/" && git push origin main
```

### Step 5: Mac Mini で確認（不要 — Mac Mini は自動 git pull しない）
Mac Mini は anicca-project を毎日 pull していない。必要なら手動で：
```bash
ssh anicca@100.99.82.95 "cd /path/to/anicca && git pull origin dev"
```

---

## E2E判定

| 項目 | 値 |
|------|-----|
| UI変更 | なし |
| 新画面 | なし |
| 結論 | Maestro E2E不要（ファイル移動のみ）|
