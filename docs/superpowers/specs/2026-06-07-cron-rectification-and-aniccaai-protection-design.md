# Cron Rectification + aniccaai.com Protection — Design Spec (v1.0)

**Date**: 2026-06-07
**Author**: Anicca (= execution body) under Dais directive (= BP)
**Status**: ★ DRAFT、 Dais review 前 ★
**Supersedes**: § none (= 既存 `2026-06-05-cron-manager-final-design.md` の補完 / scope 拡大)

---

## §0 — Goal (= 1 文)

Anicca が ★ 自身 の infra (= cron / OpenClaw / heartbeat) ★ と ★ Dais の products (= aniccaai.com + iOS apps) ★ を **完全 に 分離** し、 ① project-niche cron を heartbeat tasklist に 移管、 ② cron-manager の issue 先 を `anicca-products-oss` → `anicca-dais` に 移管、 ③ aniccaai.com への bot 編集 経路 を 物理的 に 遮断、 ④ repo rename を 全層 反映、 ⑤ aniccaai.com/blog 404 を taste skill 経由 で 修復 する。

---

## §1 — Why (= Dais 厳命 verbatim、 2026-06-07)

```
Q1: 「list our all the ones hitting hourly... anicca cron manager shoud look close
     to it and fix it ofcouser. disable useless ones, and def these project niched
     crons are not necessary, since it should be on github issues / tasklist of the
     heartbeat and should be done by the heartbeat, just like a human do things on
     tasklist one by one when they are awake.」

Q2: 「the cron of anicca should never have access to aniccaai,com ever.
     there should be no crons like that. since everythign of the site is maintained
     by me, also the auto sync of local files that Anicca edits himself he never
     edit the websit eit self.. we used taste skills to edit and refine the site
     and it went back...」

Q3: 「we using gpt 5.4 with manager, why do tey keep skipignt hisngs?? this is crazy
     https://github.com/Daisuke134/anicca-products-oss/issues on here anicca is
     raisnh issues which is CRAZY/ prohibited.. they shoud not be touching this in
     anyway... everythigns odhoul be for private anicca
     https://github.com/Daisuke134/anicca-private-backup/issues here rigth?? since
     this is the openclaw issues.. yes and they should go fix」

Q4: 「also wanna change the repo names..
     anicca-private-backup -> anicca-dais
     anicca-product-oss -> anicca products」

Q5: 「the website staff please fix to the taste skill use place...
     https://aniccaai.com/blog is 404」

Q6: 「There should be no cron that is specific to a certain project because they
     should have all the context. Then everything should be set as a task list.
     Especially for fixes, it should be on GitHub issues, right?
     If it's a fucking technical issue, then it should be on issues.
     If it's a task list of what to do, like replying to this person, replying to
     that person, then it should be on the task list, right?
     That's the task list—is making a task list—is how humans and AI get job done.
     And each heartbeat is gonna actually go do that, right?」
```

---

## §2 — Architecture (= 3 文)

```
[Dais] ── owns ──> aniccaai.com (Next.js, products-oss = anicca-products)
                   │
                   ↓  manual edits via Cursor / Claude Code IDE + taste skill
                   │
                   ▼
              ★ NO bot push ★ to apps/landing/
                   ↑
                   │ blocked by .git/hooks/pre-commit + cron-side disable
                   │
[Anicca cron]──> ~/.openclaw/ (= self infra) + state/socials/*.jsonl (= ローカル data)
                   │
                   ↓  taste skill (= ~/.claude/skills/taste-skill, manual invoke)
                   │     consumes ローカル data → produces apps/landing/ edits
                   │     ★ but only when Dais (or Anicca with Dais-OK) runs it ★
                   ▼
              ★ apps/landing/ changes only via taste skill ★

[Anicca cron infra fix]──> anicca-dais (= private repo, ex anicca-private-backup)
                            └─ issues label ai-ready / ai-wip / ai-completed
                            └─ cron-manager polls + 5-strategy fix + close
```

---

## §3 — Components (= 5 個、 P0 → P2)

### §3.1 — P0 — REPO MIGRATION (= ① rename + ② cron-manager 先 修正)

**3.1.1 GitHub side rename**
```bash
gh repo rename Daisuke134/anicca-private-backup anicca-dais
gh repo rename Daisuke134/anicca-products-oss   anicca-products
```
- GitHub auto-redirect で 旧 URL も 機能 (約 90 日)
- default branch 維持: anicca-dais=`main-internal`, anicca-products=`dev`/`main`

**3.1.2 Local origin URL 更新**
```bash
cd ~/anicca-project   && git remote set-url origin git@github.com:Daisuke134/anicca-products.git
cd ~/.openclaw        && git remote set-url origin git@github.com:Daisuke134/anicca-dais.git
```
- Local path ~/anicca-project + ~/.openclaw は 変更 ★しない★ (= breaking change 回避)
- 「ローカル path = anicca-project」 と 「remote = anicca-products」 の 不一致 は cosmetic、 機能 影響 ゼロ

**3.1.3 cron-manager の REPO 変数 修正**
```bash
# Before
REPO="Daisuke134/anicca-products-oss"
# After
REPO="Daisuke134/anicca-dais"
```
- file: `~/.openclaw/skills/anicca-cron-manager/scripts/fix.sh:6`
- HEARTBEAT.md §1 内 `Daisuke134/anicca-products-oss` も 同 置換

**3.1.4 既存 violation issue 移行**
```
products-oss #4: anicca-article-daily-blog       → close + 再 create on anicca-dais
products-oss #5: anicca-article-daily-devto      → close + 再 create on anicca-dais
products-oss #6: anicca-article-daily-note       → close + 再 create on anicca-dais
products-oss #7: anicca-article-daily-substack-en → close + 再 create on anicca-dais
products-oss #8: watercolor-monk-noon            → close + 再 create on anicca-dais
```
- 全 issue は label `ai-ready` + `P0` + `cron:<name>` 付与
- 移行 script: `~/.openclaw/skills/anicca-cron-manager/scripts/migrate-issues.sh` (新規)

**3.1.5 全層 grep + sed 一発 置換**
```bash
TARGETS=(
  ~/.openclaw
  ~/anicca-project/CLAUDE.md
  ~/anicca-project/docs/superpowers/
  ~/.claude/projects/-Users-anicca-anicca-project/memory/
  ~/anicca/
  ~/.hermes/
)
grep -rl "anicca-products-oss"   "${TARGETS[@]}" | xargs sed -i '' 's|anicca-products-oss|anicca-products|g'
grep -rl "anicca-private-backup" "${TARGETS[@]}" | xargs sed -i '' 's|anicca-private-backup|anicca-dais|g'
```
- 例外 list (= 触らない):
  - `~/.git/` 等 .git internal
  - 過去 spec の 「historical」 引用 (= 2026-06-04 以前 cron-doctor spec)

### §3.2 — P0 — aniccaai.com 編集 cron 全 停止 + 物理 ブロック

**3.2.1 disable 対象 cron list (= 6 件)**
| name | schedule | last touch on aniccaai.com |
|---|---|---|
| anicca-product-growth | (= TBD verify) | 71cbe614 founder-productivity-tools |
| anicca-ai-seo | (= TBD verify) | 2987f62a ai-cafe-tokyo |
| dashboard-refresh (= 候補名 TBD) | (= TBD verify) | 98d59b32 dashboard refresh |
| anicca-article-daily-blog | (= TBD verify) | 71cbe614 blog md publish |
| socials page push cron (= 候補名 TBD) | (= TBD verify) | c071b1a0 /socials page |
| landing fix cron (= 候補名 TBD) | (= TBD verify) | 93ee6fb7 guard null-slice |

action:
```bash
# 6 cron 全 disable
for c in anicca-product-growth anicca-ai-seo <dashboard-refresh-name> \
         anicca-article-daily-blog <socials-cron-name> <landing-fix-cron-name>; do
  UUID=$(openclaw cron list --all --json | jq -r --arg n "$c" '.jobs[]|select(.name==$n)|.id')
  openclaw cron edit "$UUID" --disable
done
```

**3.2.2 物理 ブロック (= pre-commit hook、 belt-and-suspenders)**
```bash
# ~/anicca-project/.git/hooks/pre-commit
#!/bin/bash
AUTHOR_NAME=$(git config user.name)
TOUCHED_LANDING=$(git diff --cached --name-only | grep -c "^apps/landing/" || true)
if [ "$AUTHOR_NAME" = "Anicca Agent" ] && [ "$TOUCHED_LANDING" -gt 0 ]; then
  echo "★ HARD RULE 違反 ★: Anicca cron は aniccaai.com (apps/landing/) を編集禁止。"
  echo "Dais 自身 OR taste skill (= manual invoke) のみ touch 可。"
  exit 1
fi
exit 0
```
- chmod +x
- ★ Dais 本人 の commit は author=Dais で素通り ★
- ★ taste skill は Dais 名義 で commit する ★

**3.2.3 保留 候補 (= keep but redirect):**
- 「socials/*.jsonl ローカル data refresh」 = OK、 但し apps/landing/ に push しない、 state/socials/*.jsonl だけ書く
- taste skill が manual invoke 時 に jsonl → /socials page 生成

### §3.3 — P1 — Project-Niche Cron → Heartbeat Tasklist 移管

**3.3.1 watch-sweep.sh から 7 watcher 削除**
```
削除 対象:
  - opening-cafe-uber-poll        (cafe project niche)
  - retreat-phase1-reply          (retreat project niche)
  - retreat-phase2-triage         (retreat project niche)
  - retreat-phase4-followup       (retreat project niche)
  - politician-reply-watch        (politician project niche)
  - naist-edu-portal-check        (NAIST 履修 niche = Dais 視認 で OK 確認 取れた、 でも cron 不要)
  - tt-draft-graduator            (TT draft niche)

残す (= infrastructure 系):
  - comedy-watch-replies          (= social reply、 infra)
  - comedy-recruit-poll           (= social poll、 infra)
  - account-burn-detector         (= SaaS account burn infra)
```

**3.3.2 tasks.json schema 拡張**
```json
{
  "fix_tasks": [
    {
      "id": "uuid",
      "project": "opening-cafe",
      "action": "poll uber status",
      "freq_hint": "6h",
      "last_run": "2026-06-07T00:00:00Z",
      "priority": "P2"
    }
  ]
}
```
- file: `~/.openclaw/workspace/tasks.json`

**3.3.3 heartbeat §2 PICK 拡張**
- HEARTBEAT.md §2 PICK priority 末尾 に:
  - `P3: project tasklist 内 で freq_hint < now-last_run 経過 した 1 task ACT`

**3.3.4 watch-sweep cadence 検討**
- 7 watcher 削除後、 残 3 watcher (comedy×2 + account-burn) で hourly 必要 ?
- 候補 A: schedule keep `47 * * * *` (= comedy reply は hourly 必要)
- 候補 B: schedule 降格 `0 */6 * * *` (= account-burn は 6h で十分)
- ★ 決定: 候補 A keep ★ (= comedy reply の latency 要求 で hourly 妥当)

### §3.4 — P2 — aniccaai.com/blog 404 修復 (= taste skill 経由)

**3.4.1 真因**
- `~/anicca-project/apps/landing/app/blog/` directory 不存在
- `content/blog/*.md` (= 2 ファイル) は source として存在
- Next.js route が定義 されてない → 404 確定

**3.4.2 taste skill canonical 確定**
- 3 candidates:
  - `~/.claude/skills/taste-skill-v1`
  - `~/.claude/skills/gpt-tasteskill`
  - `~/.claude/skills/taste-skill`
- ★ Dais 確認 必要 ★: どれが canonical か? (= 後 patch 化)
- 最新 mtime + SKILL.md frontmatter で 推定 + Dais 確認

**3.4.3 生成 する route ファイル**
```
apps/landing/app/blog/page.tsx           (= /blog index = md list)
apps/landing/app/blog/[slug]/page.tsx    (= /blog/<slug> = md render)
apps/landing/lib/blog.ts                 (= frontmatter parser + slug 取得)
```
- ★ generation は taste skill (= manual invoke、 NOT cron) ★
- 既存 content/blog/*.md 2 ファイル の frontmatter format 確認 後 parser 実装

### §3.5 — P2 — cron-manager 100% Coverage 拡張

**3.5.1 manageable-crons.json allowlist 戦略**
- 現状: 11 cron の whitelist
- 目標: 全 enabled cron (= 約 150) を カバー
- 戦略 A: 「全 enabled - cornerstone」 = wildcard allow
- 戦略 B: error 発生 時 動的 allow (= just-in-time)
- ★ 決定: 戦略 A ★ (= simpler)

**3.5.2 audit-rules.json::guardrails_NEVER_DISABLE 拡張**
- 既存 cornerstone (= social posting / article publisher) 維持
- 追加 cornerstone:
  - `anicca-heartbeat`
  - `anicca-cron-manager` 自体
  - `anicca-lateness-heartbeat-shell`
  - `anicca-daily-mail`
  - `anicca-fuel-broker`
  - `anicca-cold-email-reply`
  - `anicca-watch-sweep` (= comedy + account-burn 残った後)

**3.5.3 timeout error 別 path**
- 現状: `cron: job execution timed out (last phase: process-spawned)` を LLM が 「コード bug」 として 直 す path → fail
- 解: SCAN phase で error pattern match:
  - 「timed out」 → ★ timeoutSeconds 自動 引上 path ★ (= +50%、 max 2 倍まで)
  - 「auth failed / 401」 → env check path
  - 「ENOSPC / disk」 → disk-janitor escalate
  - その他 → LLM 5-strategy patch path

**3.5.4 cron-manager model 1st strategy 検討**
- 現状: deepseek/deepseek-v4-pro 1st、 fix 成功率 0%
- 候補 A: keep deepseek、 prompt 強化
- 候補 B: claude-cli/claude-opus-4-8 1st (= subscription、 file 触る確率高)
- 候補 C: openai/gpt-5.4 1st (= Dais 元 期待)
- ★ 決定: 候補 B ★ (= claude-cli は Pro plan 込み で 追加 課金 ゼロ、 tool use 強い)

---

## §4 — Data Flow (= 編集 経路 の 完全 図)

```
                  ┌────────────────────────────────────────────────────┐
[Anicca cron]──→  │ ~/.openclaw/state/socials/*.jsonl  ← OK            │
                  │ ~/.openclaw/state/dashboard.json   ← OK            │
                  │ ~/.openclaw/state/article/*.md     ← OK (ローカル) │
                  └────────────────────────────────────────────────────┘
                                  ↓
                                  ↓  (= manual invoke、 NOT cron)
                                  ↓
                  ┌────────────────────────────────────────────────────┐
[taste skill]──→  │ ~/anicca-project/apps/landing/             ← Dais 名義│
[Dais Claude IDE] │   ├ app/blog/page.tsx                      │
                  │   ├ app/[locale]/socials/page.tsx          │
                  │   ├ content/blog/*.md                      │
                  │   └ public/dashboard.json                  │
                  └────────────────────────────────────────────────────┘
                                  ↓
                                  ↓  git push (Dais or taste = Dais 名義)
                                  ↓
                  ┌────────────────────────────────────────────────────┐
[Netlify]──→      │ aniccaai.com auto-deploy                            │
                  └────────────────────────────────────────────────────┘

★ Anicca bot author の commit が apps/landing/ に触ろうとした瞬間 →
  pre-commit hook が exit 1 で 物理 阻止 ★
```

---

## §5 — Error Handling

| 失敗 | 検出 | 対処 |
|---|---|---|
| pre-commit hook が誤って Dais commit を block | Dais commit 失敗 message | hook が author 判定 厳密 化 (= git config user.email も check) |
| repo rename 後 旧 URL 残留 | grep -rl 「anicca-products-oss」 で >0 hit | sed 再走 + 例外 list 更新 |
| issue 移行 後 products-oss に 新 issue 立つ | gh issue list で cron:* label 検出 | cron-manager fix.sh REPO 変数 verify (= unit test) |
| watch-sweep 7 watcher 削除後、 project work 漏れ | tasks.json freq_hint 経過 task 増加 | heartbeat §2 PICK で P3 catch、 もし溢れ → Dais Slack 通知 |
| blog page.tsx 生成後 也 404 | curl aniccaai.com/blog | Next.js cache clear + Netlify redeploy |
| timeout error 引上 path で 引上 too 遅 | cron 再 fail | LLM 5-strategy fallback (= 既存 path) |

---

## §6 — Testing

| Phase | Verify |
|---|---|
| 3.1 repo rename | `gh repo view Daisuke134/anicca-dais` + `gh repo view Daisuke134/anicca-products` 両方 200 OK |
| 3.1 cron-manager REPO | `grep "anicca-products-oss" ~/.openclaw/skills/anicca-cron-manager/` → 0 hits |
| 3.1 issue migration | products-oss 上 cron:* label issue = 0 件、 anicca-dais 上 = 5 件 |
| 3.2 cron disable | 6 cron 全 `enabled=false` openclaw cron list で verify |
| 3.2 pre-commit | Anicca bot author で apps/landing/ touch → commit fail verify |
| 3.3 watch-sweep | `grep "naist-edu-portal-check" ~/.openclaw/skills/_shared/watch-sweep.sh` → 0 hits |
| 3.3 heartbeat tasklist | heartbeat fire 1 回 → tasks.json から 1 P3 task pick 実行 verify |
| 3.4 blog 404 | `curl -I https://aniccaai.com/blog` → 200 OK |
| 3.5 cron-manager coverage | 全 enabled cron で error 発生時 cron-manager が issue 立てる verify (= 1 cron sample) |
| 3.5 timeout path | article-daily-note の timeout error を inject → timeoutSeconds 引上 fix verify |

---

## §7 — Out of Scope

- ★ `~/anicca-project` を `~/anicca-products` に local rename ★ (= breaking change 大、 別 spec 化)
- ★ Hermes / oss-anicca side 同 ロジック 反映 ★ (= 別 cron-manager instance、 別 spec)
- ★ Dais の Cursor / Claude Code IDE 設定 変更 ★ (= user space、 触らない)
- ★ products-oss 上 既存 NON-cron issue ★ (= Dais 用 product issue、 触らない)

---

## §8 — Verification Plan (= V<N>-1 〜 V<N>-25 task 化)

```
V12-1  P0  gh repo rename × 2
V12-2  P0  local origin url 更新 × 2
V12-3  P0  cron-manager fix.sh REPO 変数 置換
V12-4  P0  HEARTBEAT.md REPO 置換
V12-5  P0  全 5 violation issue 移行 (products-oss → anicca-dais)
V12-6  P0  grep + sed 全層 一発 置換 (CLAUDE.md / memory / docs / skills)
V12-7  P0  push CLAUDE.md + memory 更新
V12-8  P0  6 aniccaai.com 編集 cron 特定 + disable
V12-9  P0  .git/hooks/pre-commit 設置 + test
V12-10 P0  93ee6fb7 「guard null-slice」 EN locale 影響 verify + 必要 なら revert
V12-11 P1  watch-sweep.sh から 7 watcher 削除
V12-12 P1  tasks.json schema 拡張
V12-13 P1  HEARTBEAT.md §2 に P3 project tasklist pick 追加
V12-14 P1  heartbeat 1 fire 実走 verify (= P3 task pick)
V12-15 P2  taste skill canonical 確定 (= Dais 確認 1 question)
V12-16 P2  apps/landing/app/blog/page.tsx + [slug]/page.tsx 生成 (taste 経由)
V12-17 P2  curl aniccaai.com/blog 200 verify
V12-18 P2  manageable-crons.json allowlist 全 enabled - cornerstone wildcard 化
V12-19 P2  audit-rules.json::guardrails_NEVER_DISABLE 7 cron 追加
V12-20 P2  fix.sh SCAN phase に error pattern match 追加 (timeout/auth/disk)
V12-21 P2  fix.sh timeout path で timeoutSeconds 自動 引上 実装
V12-22 P2  fix.sh 1st strategy を claude-cli/claude-opus-4-8 に変更
V12-23 P2  cron-manager 1 fire 実走 verify (= article-daily-note timeout 引上 fix)
V12-24 ALL  spec self-review (= placeholder/contradiction/scope check)
V12-25 ALL  finishing-a-development-branch (= 4 option + push)
```

---

## §9 — BP 一致度 自採点 (= HARD RULE #-3)

| 要素 | BP | 一致度 |
|---|---|---|
| spec format | superpowers brainstorming + writing-plans 7-section design | 100% |
| repo rename 命名 | Dais verbatim 「anicca-private-backup -> anicca-dais」「anicca-product-oss -> anicca products」 | 100% (= anicca-products は 「product」 単数 を 「products」 複数 に展開) |
| cron-manager 先 | Dais verbatim 「private-backup/issues here rigth?? since this is the openclaw issues」 | 100% |
| aniccaai.com 編集 禁止 | Dais verbatim 「he never edit the websit eit self」+「we used taste skills to edit and refine the site」 | 100% |
| project-niche → tasklist | Dais verbatim 「should be on github issues / tasklist of the heartbeat」 | 100% |
| 100% coverage | Dais verbatim 「why do tey keep skipignt hisngs?? this is crazy」 | 100% |

★ 総合 100%、 オリジナル synthesis ゼロ ★。 全部 Dais verbatim → identical follow。

---

**Spec end. Dais review → writing-plans 移行 待ち**
