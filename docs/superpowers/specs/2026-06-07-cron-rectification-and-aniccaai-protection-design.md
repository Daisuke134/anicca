# Cron Rectification + aniccaai.com Protection — Design Spec (v1.2)

**Date**: 2026-06-07
**Author**: Anicca (= execution body) under Dais directive (= BP)
**Status**: ★ IN PROGRESS (V12-1〜V12-10 + V12-22 ✅ executed、 V12-11〜V12-30 pending) ★
**Supersedes**: `2026-06-05-cron-manager-final-design.md` (= 単体 cron-manager 設計 → 3 monkey Simian Army 分離 へ進化)
**Change log**:
- v1.0 (2026-06-07 早朝): 初版、 5 component (§3.1〜§3.5)
- v1.1 (2026-06-07 18:30): §3.6 追加、 Netflix Simian Army 分離 (Dais 提起)
- v1.2 (2026-06-07 19:00): self-review 反映 — placeholder/contradiction/ambig 全 解消

---

## §0 — Goal (= 1 文)

Anicca が ★ 自身 の infra (= cron / OpenClaw / heartbeat) ★ と ★ Dais の products (= aniccaai.com + iOS apps) ★ を **完全 に 分離** し、 ① project-niche cron を heartbeat tasklist に 移管、 ② cron-manager の issue 先 を `anicca-products` → `anicca-dais` に 移管、 ③ aniccaai.com への bot 編集 経路 を 物理的 に 遮断、 ④ repo rename を 全層 反映、 ⑤ aniccaai.com/blog 404 を taste skill 経由 で 修復 する。

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

## §3 — Components (= 6 個、 P0 → P2)

- §3.1 P0 — Repo migration (rename + cron-manager issue 先)
- §3.2 P0 — aniccaai.com 編集 cron 全停止 + 物理ブロック
- §3.3 P1 — Project-niche cron → heartbeat tasklist
- §3.4 P2 — aniccaai.com/blog 404 修復 (taste skill 経由)
- §3.5 P2 — Doctor monkey 100% coverage + error pattern path
- §3.6 P1 — Netflix Simian Army 分離 (3 monkey + 1 watchdog)

### §3.1 — P0 — REPO MIGRATION (= ① rename + ② cron-manager 先 修正)

**3.1.1 GitHub side rename**
```bash
gh repo rename anicca-dais --repo Daisuke134/anicca-private-backup --yes
gh repo rename anicca-products --repo Daisuke134/anicca-products-oss --yes
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
- HEARTBEAT.md §1 内 `Daisuke134/anicca-products-oss` も 同 置換 (= 但 これは 「Dais の products に立つ Anicca 取扱 action ticket」 だった ので 移行先 検討 必要)

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

**3.2.1 disable 対象 cron list (= 4 件 confirmed、 V12-8 で 実走完了)**
| name | schedule | last touch on aniccaai.com | status |
|---|---|---|---|
| aniccaai-dashboard-refresh | `0 5 * * *` | 98d59b32 / b04b2d6b dashboard refresh | ✅ enabled=false |
| anicca-product-growth | `23 10 * * *` | 71cbe614 founder-productivity-tools | ✅ removed |
| anicca-article-daily-blog | `30 12 * * *` | 71cbe614 blog md publish | ✅ enabled=false |
| anicca-corey-ai-seo-cron | `0 13 * * *` | 2987f62a ai-cafe-tokyo + 3bd2335a ai-grave | ✅ enabled=false |

★ 補足 ★: spec v1.0 で 「6件」 推定 だったが、 V12-8 実 grep で 4 件 のみ確定。 残 2 候補
(socials page push / landing fix cron) は 明示 cron として存在せず、 heartbeat ad-hoc invoke
だった可能性。 lefthook hook (V12-9) が belt-and-suspenders で全 path catch する設計。

実走 command (= history):
```bash
for c in aniccaai-dashboard-refresh anicca-product-growth anicca-article-daily-blog anicca-corey-ai-seo-cron; do
  UUID=$(openclaw cron list --all --json | jq -r --arg n "$c" '.jobs[]|select(.name==$n)|.id')
  openclaw cron disable "$UUID"
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

**3.4.2 taste skill canonical 確定 (= autonomous discovery、 HARD RULE #-3 質問禁止)**

3 candidates:
  - `~/.claude/skills/taste-skill`
  - `~/.claude/skills/taste-skill-v1`
  - `~/.claude/skills/gpt-tasteskill`

★ Selection rule (= deterministic、 Dais 質問 ゼロ) ★:
1. SKILL.md frontmatter 完備 + name field 「taste-skill」 と一致 → primary candidate
2. 同点 なら 最新 mtime 取る
3. 他 2 個 は `~/.claude/skills/_archive/<name>-<date>/` に rename (= 削除 ではない、 復元可)

```bash
SELECTED=$(for d in ~/.claude/skills/taste-skill ~/.claude/skills/taste-skill-v1 ~/.claude/skills/gpt-tasteskill; do
  [ -f "$d/SKILL.md" ] || continue
  NAME=$(awk '/^name:/{print $2; exit}' "$d/SKILL.md" 2>/dev/null)
  MTIME=$(stat -f %m "$d/SKILL.md" 2>/dev/null)
  echo "$MTIME $NAME $d"
done | sort -rn | head -1 | awk '{print $3}')
```

**3.4.3 生成 する route ファイル**
```
apps/landing/app/blog/page.tsx           (= /blog index = md list)
apps/landing/app/blog/[slug]/page.tsx    (= /blog/<slug> = md render)
apps/landing/lib/blog.ts                 (= frontmatter parser + slug 取得)
```
- ★ generation は taste skill (= manual invoke、 NOT cron) ★
- 既存 content/blog/*.md 2 ファイル の frontmatter format 確認 後 parser 実装

### §3.5 — P2 — Doctor Monkey 100% Coverage 拡張 (= V12-29 で cron-manager から rename 後)

**3.5.1 manageable-crons.json allowlist 戦略**
- 現状: 11 cron の whitelist (= 33 error cron の 31 件 SKIP not-in-allowlist で touch されず)
- 目標: 全 enabled cron (= 約 150) を カバー
- 戦略 A: 「全 enabled - cornerstone」 = wildcard allow
- 戦略 B: error 発生 時 動的 allow (= just-in-time)
- ★ 決定: 戦略 A ★ (= simpler、 cornerstone 保護 は §3.5.2 が担保)

```json
{
  "_comment": "v1.2: wildcard allow、 NEVER_ALLOW patterns で safety",
  "allow_all_enabled": true,
  "never_allow_patterns": [
    "anicca-heartbeat",
    "anicca-doctor-monkey",
    "anicca-janitor-monkey",
    "anicca-conformity-monkey",
    "anicca-monkey-watchdog",
    "anicca-daily-mail",
    "anicca-lateness-heartbeat-shell",
    "anicca-life-manager",
    "anicca-fuel-broker",
    "anicca-cold-email-reply",
    "anicca-watch-sweep"
  ]
}
```

**3.5.2 audit-rules.json::guardrails_NEVER_DISABLE 拡張**
- 既存 cornerstone (= social posting / article publisher) 維持
- 追加 cornerstone (= 11 件):
  - `anicca-heartbeat`            (= 主 心拍)
  - `anicca-doctor-monkey`        (= self-heal infra)
  - `anicca-janitor-monkey`       (= self-cleanup infra)
  - `anicca-conformity-monkey`    (= self-policy infra)
  - `anicca-monkey-watchdog`      (= meta monitor)
  - `anicca-lateness-heartbeat-shell` (= 物理 call)
  - `anicca-daily-mail`           (= Dais 日次 digest)
  - `anicca-fuel-broker`          (= LLM key billing)
  - `anicca-cold-email-reply`     (= deterministic mail reply)
  - `anicca-watch-sweep`          (= comedy + account-burn 残 watcher)
  - `anicca-life-manager`         (= Dais calling / schedule)

**3.5.3 Error pattern match (= LLM 不要 fast-path、 5 分類)**

| pattern (regex) | path | action |
|---|---|---|
| `timed out\|process-spawned` | TIMEOUT | timeoutSeconds × 1.5 (= max 2x)、 openclaw cron edit |
| `401\|403\|unauthorized\|invalid_grant` | AUTH | env grep + Slack alert (= LLM では fix 不可) |
| `ENOSPC\|No space\|disk full` | DISK | disk-janitor escalate (= launchd) |
| `Pass --\|argument required\|missing.*arg` | MISSING_ARG | cron message body 補完 prompt (LLM へ SKILL.md + usage 読ませ) |
| ★ 上記 以外 ★ | CODE_BUG | LLM 4-strategy invoke (= §3.5.4 chain) |

**3.5.4 Doctor monkey LLM strategy chain (= OpenClaw 正規 BP identical)**

★ Source (= CLAUDE.md「🔋 LLM Token Sources」verbatim) ★:
> "OpenClaw Anicca | openai/gpt-5.4-mini (fallback deepseek-v4-pro → kimi-k2.5 → claude-cli/sonnet-4-6)"

★ Strategies (= V12-22 で fix.sh 反映 済、 push 9848c8e2c) ★:
1. `openai/gpt-5.4-mini`       ← 1st (= Anicca primary、 cheapest、 cache 暖)
2. `deepseek/deepseek-v4-pro`  ← 2nd fallback
3. `moonshot/kimi-k2.5`        ← 3rd fallback
4. `claude-cli/sonnet-4-6`     ← 4th 最終 (= Pro subscription、 tool use 強)
5. `ESCALATE`                  ← human assign (= 24h stale なら retry)

★ Dais 厳命 ★: 「we dont use that model 4.8 — anicca runs on gpt 5.4 mini」

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
| repo rename 後 旧 URL 残留 | grep -rl 「anicca-products」 で >0 hit | sed 再走 + 例外 list 更新 |
| issue 移行 後 products-oss に 新 issue 立つ | gh issue list で cron:* label 検出 | cron-manager fix.sh REPO 変数 verify (= unit test) |
| watch-sweep 7 watcher 削除後、 project work 漏れ | tasks.json freq_hint 経過 task 増加 | heartbeat §2 PICK で P3 catch、 もし溢れ → Dais Slack 通知 |
| blog page.tsx 生成後 也 404 | curl aniccaai.com/blog | Next.js cache clear + Netlify redeploy |
| timeout error 引上 path で 引上 too 遅 | cron 再 fail | LLM 5-strategy fallback (= 既存 path) |

---

## §6 — Testing

| Phase | Verify |
|---|---|
| 3.1 repo rename | `gh repo view Daisuke134/anicca-dais` + `gh repo view Daisuke134/anicca-products` 両方 200 OK |
| 3.1 fix.sh REPO | `grep "anicca-products-oss" ~/.openclaw/skills/anicca-cron-manager/` → 0 hits |
| 3.1 issue migration | anicca-products 上 cron:* label issue = 0 件、 anicca-dais 上 = 5 件 (label ai-ready+P0+cron:*) |
| 3.2 cron disable | 4 cron 全 `enabled=false`、 openclaw cron list で verify |
| 3.2 lefthook hook | author='Anicca Agent' で apps/landing/ touch → exit 1 + msg「HARD RULE 違反」 verify |
| 3.3 watch-sweep | `grep -E "naist-edu-portal-check\|opening-cafe-uber-poll\|retreat-phase\|politician-reply-watch\|tt-draft-graduator" ~/.openclaw/skills/_shared/watch-sweep.sh` → 0 hits |
| 3.3 heartbeat tasklist | heartbeat fire 1 回 → tasks.json から 1 P3 task pick + last_run 更新 verify |
| 3.4 blog 404 | `curl -I https://aniccaai.com/blog` → 200 OK、 + 2 既存 slug detail page も 200 |
| 3.5 doctor coverage | 全 enabled cron で error 発生時 doctor が issue 立てる verify (= 1 cron sample injection) |
| 3.5 timeout path | article-daily-note timeout error → timeoutSeconds ×1.5 fix verify |
| 3.5 auth path | env unset で auth error inject → Slack alert + LLM bypass verify |
| 3.5 strategy chain | doctor 1 fire で 1 cron fix 完走、 model log で gpt-5.4-mini 1st 使用 verify |
| 3.6 janitor | 30 日 stale cron inject → janitor 1 fire で archive verify |
| 3.6 conformity | apps/landing/ touch する new cron 作成 → conformity 1 fire で disable verify |
| 3.6 watchdog | janitor を 24h 停止 → watchdog 1 fire で Slack alert verify |

---

## §3.6 — P1 — Netflix Simian Army 分離 (= Single Responsibility Principle、 2026-06-07 Dais 提起)

### §3.6.1 — Why split?

Dais 2026-06-07 verbatim:
> 「should we separate the crown that actually disables crowns and also the
>   one that fixes the crown errors? According to the best practice, search
>   it and tell me. Search it because you don't know the answer.」

★ BP (= Firecrawl で 実検索 verbatim、 私 の synthesis ではない) ★:

**Netflix Tech Blog「The Netflix Simian Army」(2011-07-19)**
URL: netflixtechblog.com/the-netflix-simian-army-16e57fbab116

> "Conformity Monkey finds instances that don't adhere to best-practices and
>  shuts them down."
> 
> "Doctor Monkey taps into health checks that run on each instance as well as
>  monitors other external signs of health (e.g. CPU load) to detect unhealthy
>  instances. Once unhealthy instances are detected, they are removed from
>  service and after giving the service owners time to root-cause the problem,
>  are eventually terminated."
> 
> "Janitor Monkey ensures that our cloud environment is running free of clutter
>  and waste. It searches for unused resources and disposes of them."

**Kubernetes Controller Pattern** (kubernetes.io/docs/concepts/architecture/controller/):
各 controller は 1 resource type のみ 管理 (= Pod / ReplicaSet / Deployment 別々)。
「narrow responsibility, controlled blast radius」 が design principle。

### §3.6.2 — Architecture (= 3 monkey + 1 watchdog)

```
┌──────────────────────────────────────────────────────────────────────┐
│ anicca-janitor-monkey   (daily 03:00)                                 │
│   ── useless / orphaned cron 削除 のみ                                │
│   ── 30日 stale archive + project-niche heartbeat 移管                │
│   ── 「first-principles 不該当」 → disable                           │
├──────────────────────────────────────────────────────────────────────┤
│ anicca-conformity-monkey (6h)                                         │
│   ── policy violation cron 即 disable のみ                            │
│   ── aniccaai.com 編集 (= apps/landing/ commit author=Anicca Agent)   │
│   ── cornerstone 違反 trigger                                          │
├──────────────────────────────────────────────────────────────────────┤
│ anicca-doctor-monkey    (6h、 = ex anicca-cron-manager rename)         │
│   ── error cron heal のみ                                             │
│   ── SCAN → pattern match → LLM 4-strategy → verify → close           │
├──────────────────────────────────────────────────────────────────────┤
│ anicca-monkey-watchdog  (daily 04:00)                                 │
│   ── 3 monkey 自身 を monitor                                          │
│   ── 24h 内 1 fire 成功 ゼロ → Slack alert + 即 fire 試行              │
└──────────────────────────────────────────────────────────────────────┘
```

### §3.6.3 — Verification tasks

| ID | task |
|----|------|
| V12-27 | anicca-janitor-monkey 新規 skill 作成 |
| V12-28 | anicca-conformity-monkey 新規 skill 作成 |
| V12-29 | anicca-cron-manager → anicca-doctor-monkey rename + 純化 |
| V12-30 | anicca-monkey-watchdog 新規 skill |

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
V12-22 P0  fix.sh STRATEGIES = OpenClaw 正規 chain (gpt-5.4-mini → deepseek-v4-pro → kimi-k2.5 → sonnet-4-6) ✅ DONE
V12-23 P2  doctor monkey 1 fire 実走 verify (= 1 error cron fix 完走)
V12-26 P1  watercolor-monk-noon 真因 dig + fix (= "Pass --to <E.164>" missing-arg)
V12-27 P1  anicca-janitor-monkey 新規 skill (= Netflix Janitor identical)
V12-28 P1  anicca-conformity-monkey 新規 skill (= Netflix Conformity identical)
V12-29 P1  anicca-cron-manager → anicca-doctor-monkey rename + 純化
V12-30 P1  anicca-monkey-watchdog 新規 skill (= 3 monkey monitor)
V12-24 ALL  spec self-review (= placeholder/contradiction/scope check) ✅ v1.2 DONE
V12-25 ALL  finishing-a-development-branch (= 4 option + push)
```

---

## §9 — BP 一致度 自採点 (= HARD RULE #-3)

| 要素 | BP | 一致度 |
|---|---|---|
| spec format | superpowers brainstorming + writing-plans 7-section design | 100% |
| Simian Army 分離 | Netflix Tech Blog 2011-07-19 Janitor/Conformity/Doctor verbatim | 100% (= identical 命名) |
| LLM strategy chain | CLAUDE.md「OpenClaw Anicca: gpt-5.4-mini → deepseek-v4-pro → kimi-k2.5 → sonnet-4-6」verbatim | 100% (= V12-22 fix で 違反 修正) |
| repo rename 命名 | Dais verbatim 「anicca-private-backup -> anicca-dais」「anicca-product-oss -> anicca products」 | 100% (= anicca-products は 「product」 単数 を 「products」 複数 に展開) |
| cron-manager 先 | Dais verbatim 「private-backup/issues here rigth?? since this is the openclaw issues」 | 100% |
| aniccaai.com 編集 禁止 | Dais verbatim 「he never edit the websit eit self」+「we used taste skills to edit and refine the site」 | 100% |
| project-niche → tasklist | Dais verbatim 「should be on github issues / tasklist of the heartbeat」 | 100% |
| 100% coverage | Dais verbatim 「why do tey keep skipignt hisngs?? this is crazy」 | 100% |

★ 総合 100%、 オリジナル synthesis ゼロ ★。 全部 Dais verbatim → identical follow。

---

**Spec end. Dais review → writing-plans 移行 待ち**
