# Cron Rectification + aniccaai.com Protection — Design Spec (v1.3)

**Date**: 2026-06-07
**Author**: Anicca (= execution body) under Dais directive (= BP)
**Status**: ★ IN PROGRESS (V12-1〜V12-10 + V12-22 ✅ executed、 V12-11〜V12-30 pending) ★
**Supersedes**: `2026-06-05-cron-manager-final-design.md` (= 単体 cron-manager 設計 → 3 monkey Simian Army 分離 へ進化)
**Change log**:
- v1.0 (2026-06-07 早朝): 初版、 5 component (§3.1〜§3.5)
- v1.1 (2026-06-07 18:30): §3.6 追加、 Netflix Simian Army 分離 (Dais 提起)
- v1.2 (2026-06-07 19:00): self-review 反映 — placeholder/contradiction/ambig 全 解消
- v1.3 (2026-06-07 19:30): superpowers:code-reviewer 5 BLOCKING + 6 MAJOR + 4 MINOR 全 反映 (= 1339fd5f レビュー応答)

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

**3.2.2 物理 ブロック (= 3 層 defense-in-depth、 reviewer BLOCKING #3 反映 v1.3)**

★ v1.3 強化 ★: 1 key (= user.name) detection は git config 上書き で bypass 可 → 多 要素 check。

```yaml
# lefthook.yml の aniccaai-landing-guard
aniccaai-landing-guard:
  run: |
    author_name=$(git config user.name)
    author_email=$(git config user.email)
    touched=$(git diff --cached --name-only | grep -c "^apps/landing/" || true)
    [ "$touched" -eq 0 ] && exit 0
    # Layer 1: name check
    is_bot=0
    [ "$author_name" = "Anicca Agent" ] && is_bot=1
    # Layer 2: email check (= bot email pattern)
    case "$author_email" in
      *anicca*bot*|*anicca-agent*|*@anicca.ai|noreply@anthropic.com) is_bot=1;;
    esac
    # Layer 3: parent process check (= interactive shell or claude-cli)
    pname=$(ps -o comm= -p $PPID 2>/dev/null | xargs basename)
    case "$pname" in
      bash|zsh|fish|claude|cursor|code|nvim|vim) : ;;  # interactive、 OK
      *) is_bot=1 ;;                                   # daemon / cron / agent
    esac
    if [ "$is_bot" = "1" ]; then
      echo "❌ HARD RULE 違反: Anicca cron は apps/landing/ 編集禁止"
      echo "  name=$author_name email=$author_email parent=$pname"
      git diff --cached --name-only | grep "^apps/landing/" | head -10 | sed 's/^/   /'
      exit 1
    fi
```

★ Layer 4 (= server-side、 P2 future): GitHub Actions workflow `landing-guard.yml` で
  pull-request author check。 Anicca bot account 直接 push 阻止 (= local hook bypass 防止)。 ★

- ★ Dais 本人 (name=Daisuke Sato OR email=keiodaisuke@gmail.com OR parent=zsh/cursor) → 素通り ★
- ★ taste skill = Dais の interactive shell 経由 invoke、 同様 素通り ★

**3.2.3 保留 候補 (= keep but redirect):**
- 「socials/*.jsonl ローカル data refresh」 = OK、 但し apps/landing/ に push しない、 state/socials/*.jsonl だけ書く
- taste skill が manual invoke 時 に jsonl → /socials page 生成

**3.2.4 §3.2.1 ↔ CLAUDE.md §0.19 矛盾 解消 (= reviewer BLOCKING #4)**

CLAUDE.md §0.19 verbatim: 「article = Zenn/Dev.to/Substack/aniccaai.com/blog」 = aniccaai.com/blog が
article cron の canonical channel 一覧 に 含まれてた。 が、 2026-06-07 Dais 厳命 で 「he never edit
the websit eit self」 が 上書き。

★ 解 ★: aniccaai.com/blog channel を article cron から ★ 完全 退出 ★:
- `anicca-article-daily-blog` = 永久 disable (= NOT 一時、 §3.2.1 通り)
- 残 article cron (devto/note/substack-ja/substack-en/zenn) は 継続 enabled
- CLAUDE.md §0.19 の channel list は 別 spec で 「Zenn/Dev.to/Substack」 4 channel に更新
  (= aniccaai.com/blog 削除、 sister spec `2026-06-XX-content-factory-channels-update.md` 待ち)
- blog content (= content/blog/*.md) は taste skill 経由 で Dais 名義 で apps/landing/ に publish

★ §3.2.1 + §0.19 + V12-15/16/17 (taste skill 経由 blog route 生成) で 全 整合 ★。

### §3.3 — P1 — Project-Niche Cron → Heartbeat Tasklist 移管

**3.3.1 watch-sweep 分離 2 ファイル化 (= reviewer MAJOR 反映)**

★ Old: 単一 watch-sweep.sh が 10 watcher 雑混在 → 削除/維持 区別 不可、 将来 misread 危険 ★
★ New: 2 ファイル分離 ★:

```
~/.openclaw/skills/_shared/
├── watch-sweep.sh          (= old wrapper、 下記 2 ファイル invoke)
├── watch-sweep-infra.sh    (= ★ KEEP ★、 hourly :47、 3 watcher のみ)
│     - comedy-watch-replies         (social reply infra、 X mention monitor)
│     - comedy-recruit-poll          (recruit infra)
│     - account-burn-detector        (SaaS account burn infra)
│
└── watch-sweep-project.sh  (= ★ DELETED ★、 7 watcher は tasks.json へ移管)
      - opening-cafe-uber-poll       → tasks.json project=opening-cafe freq=6h
      - retreat-phase1-reply         → tasks.json project=retreat phase=1
      - retreat-phase2-triage        → tasks.json project=retreat phase=2
      - retreat-phase4-followup      → tasks.json project=retreat phase=4
      - politician-reply-watch       → tasks.json project=politician
      - naist-edu-portal-check       → tasks.json project=naist freq=24h
      - tt-draft-graduator           → tasks.json project=tt-draft
```

- watch-sweep.sh は backward-compat thin wrapper として 残存 (= 既 cron entry 触らず)
- 「将来 engineer が誤って infra watcher 削除」 防止 — infra ファイル は SKILL.md frontmatter で
  `do_not_delete: true` + `pin_to_infra: true` 明示

**3.3.2 tasks.json schema 拡張 (= bounded queue、 reviewer BLOCKING #2 反映)**
```json
{
  "_max_size": 100,
  "_eviction_policy": "oldest_P3_stale_7d_drop_with_slack_notify",
  "fix_tasks": [
    {
      "id": "uuid",
      "project": "opening-cafe",
      "action": "poll uber status",
      "freq_hint": "6h",
      "last_run": "2026-06-07T00:00:00Z",
      "added_at": "2026-06-07T19:00:00Z",
      "priority": "P3"
    }
  ]
}
```
- file: `~/.openclaw/workspace/tasks.json`
- ★ insertion ★: 既 100 件 なら 「最古 P3 で last_run < now-7d」 を 1 件 drop + Slack notify
  (= 「7 日 経って も catch されない project 」 = de facto 廃止候補、 Janitor が拾う)
- ★ 7 日 stale 全件 drop 失敗 → reject insert + Slack alert + Janitor 次 fire で 「queue 飽和」 報告 ★

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
done | sort -k1,1rn -k3,3 | head -1 | awk '{print $3}')
# ★ tiebreak (= reviewer MAJOR 反映) ★: mtime 降順 → mtime 同点 なら path lex 昇順
# = 完全 deterministic、 fresh clone / tar restore でも 同 結果
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

**3.5.1 manageable-crons.json allowlist 戦略 (= reviewer MAJOR 反映、 v1.3 戦略 B invert)**

- 現状: 11 cron の whitelist (= 33 error cron の 31 件 SKIP not-in-allowlist で touch されず)
- 目標: 全 enabled cron (= 約 150) の error を扱う、 但 cornerstone 死守

★ v1.2 戦略 A (wildcard `allow_all_enabled: true` + blacklist) は reviewer が 「typo で
  cornerstone 落ちる」 弱点 指摘 ★。 → v1.3 = ★ 戦略 B invert (JIT auto-allow) 採用 ★。

```json
{
  "_comment": "v1.3: explicit allowlist (= original safety net 維持)、 error 初発 で auto-append",
  "_mode": "just_in_time",
  "allow_explicit": [
    "anicca-article-daily-blog", "anicca-article-daily-devto",
    "anicca-article-daily-note", "anicca-article-daily-substack-en",
    "anicca-article-daily-substack-ja",
    "monk-factory-en-0800", "monk-factory-en-1400",
    "mau-tiktok-en-morning", "watercolor-monk-noon",
    "reelclaw-anicca-ja-wi-cron-20-18", "anicca-comedy-weekly-recap"
  ],
  "auto_append_on_first_error": true,
  "auto_append_require_not_in_never_allow": true,
  "never_allow_patterns": [
    "anicca-heartbeat", "anicca-doctor-monkey", "anicca-janitor-monkey",
    "anicca-conformity-monkey", "anicca-monkey-watchdog",
    "anicca-daily-mail", "anicca-lateness-heartbeat-shell", "anicca-life-manager",
    "anicca-fuel-broker", "anicca-cold-email-reply", "anicca-watch-sweep"
  ]
}
```

★ 動作 ★:
1. Doctor SCAN で error cron X 検出
2. allow_explicit に X が 在る → process
3. 不在 → never_allow_patterns 照合
4. never_allow に 無い → ★ allow_explicit に auto-append + Slack notify ★ + process
5. never_allow に 在る → SKIP + Slack notify (= 「cornerstone error」 = 真 emergency)

★ 利点 ★: typo で cornerstone 落ちない (= 戦略 A の弱点 fix)、 31 SKIP も 1 error 経て 自動 covered。

**3.5.2 audit-rules.json::guardrails_NEVER_DISABLE 拡張 (= reviewer BLOCKING #4 反映、 全面)**

★ v1.2 は infra のみ 11 件 — reviewer 指摘「revenue/growth cornerstone 全 抜け」 ★。 v1.3 で 全網羅:

```json
{
  "guardrails_NEVER_DISABLE": {
    "infra (= 内部 守備)": [
      "anicca-heartbeat",                  // 主 心拍 (rate-limited 1 action/beat)
      "anicca-doctor-monkey",              // self-heal、 ex anicca-cron-manager
      "anicca-janitor-monkey",             // useless cron disposal
      "anicca-conformity-monkey",          // policy violation disable
      "anicca-monkey-watchdog",            // meta monitor
      "anicca-lateness-heartbeat-shell",   // 物理 call (= 遅刻 防止)
      "anicca-daily-mail",                 // Dais 日次 digest (07/22 JST)
      "anicca-fuel-broker",                // LLM key billing fuel guard
      "anicca-cold-email-reply",           // deterministic mail reply (HR#6 exception)
      "anicca-watch-sweep",                // = infra-only 3 watcher 残り後
      "anicca-life-manager",               // Dais calling / schedule
      "anicca-inbox",                      // = anicca-inbox heartbeat (mail autonomy)
      "anicca-genesis-sync"                // Hermes body 3h sync (= 自走 永続性)
    ],
    "revenue/growth (= 収益 / 配信)": [
      "anicca-article-daily-devto",        // Dev.to 配信 (= USEFUL CONTENT FACTORY §0.19)
      "anicca-article-daily-note",         // note 配信
      "anicca-article-daily-substack-ja",  // Substack JA
      "anicca-article-daily-substack-en",  // Substack EN
      "anicca-article-daily-zenn",         // Zenn (= 残 1 channel)
      "anicca-x-direct",                   // X post (= @aniccaxxx)
      "monk-factory-en-0800",              // EN slideshow 朝
      "monk-factory-en-1400",              // EN slideshow 昼
      "mau-tiktok-en-morning",             // TikTok EN
      "watercolor-monk-noon",              // watercolor slideshow 昼
      "reelclaw-anicca-ja-wi-cron-20-18",  // reelclaw JA WI
      "anicca-comedy-weekly-recap",        // comedy recap (= revenue)
      "comedy-recruit-poll",               // = X social posting infra (社員募集系)
      "comedy-watch-replies"               // = X reply infra (social monitoring)
    ],
    "app store / paywall (= mobile 収益)": [
      "aso-loop",                          // App Store Optimization
      "screenshot-ab",                     // screenshot A/B
      "paywall-ab"                         // paywall A/B
    ]
  }
}
```

★ 数: 11 infra + 14 revenue + 3 app-store = ★ 28 cornerstone ★ (= v1.2 比 +17)。
★ 「list に 漏れ た cornerstone を 後発 検出」 path: Janitor が 「disable しよう とした 瞬間
  Doctor の state-change history に 直近 error fix あり → SKIP + Slack alert + add to NEVER_DISABLE 候補」 ★。

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
> "OpenClaw Anicca | openai/gpt-5.4-mini (fallback deepseek-v4-pro → kimi-k2.5 → anthropic/claude-sonnet-4-6)"

★ Strategies (= V12-22 で fix.sh 反映 済、 push 9848c8e2c) ★:
1. `openai/gpt-5.4-mini`       ← 1st (= Anicca primary、 cheapest、 cache 暖)
2. `deepseek/deepseek-v4-pro`  ← 2nd fallback
3. `moonshot/kimi-k2.5`        ← 3rd fallback
4. `anthropic/claude-sonnet-4-6`     ← 4th 最終 (= Pro subscription、 tool use 強)
5. `ESCALATE`                  ← human assign (= 24h stale なら retry)

★ Dais 厳命 ★: 「we dont use that model 4.8 — anicca runs on gpt 5.4 mini」

**3.5.5 Sonnet-4-6 budget breaker (= reviewer MINOR、 v1.3 反映)**

anthropic/claude-sonnet-4-6 は Anthropic Pro plan 込み だが 「quota 焼き切り → 32h cooldown 全 Anicca
思考停止」 incident (2026-05-29) の根因。 → ★ daily budget breaker ★:

```bash
# fix.sh: strategy 4 (sonnet-4-6) 実行 前 daily count check
SONNET_DAILY_MAX=5
SONNET_LOG="$HOME/.openclaw/state/doctor-monkey/sonnet-calls-$(date +%Y-%m-%d).log"
SONNET_TODAY=$(wc -l < "$SONNET_LOG" 2>/dev/null || echo 0)
if [ "$STRATEGY" = "anthropic/claude-sonnet-4-6" ] && [ "$SONNET_TODAY" -ge "$SONNET_DAILY_MAX" ]; then
  echo "Sonnet daily budget exhausted ($SONNET_TODAY/$SONNET_DAILY_MAX). Skipping to ESCALATE."
  STRATEGY=ESCALATE
fi
echo "$(date -Iseconds) $CRON_NAME" >> "$SONNET_LOG"
```

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

### §3.6.2 — Architecture (= 3 monkey + 1 launchd watchdog、 v1.3 reviewer BLOCKING #5 反映)

★ v1.2 watchdog が openclaw cron だった → 循環依存 (= watchdog 死亡 検出 不能) ★
★ v1.3 解 = ★ watchdog を launchd plist に out-of-band 設置 ★ (= disk-janitor と同 architecture、
  既証明済)。 加 cross-monitor: Doctor が watchdog を 「特殊 cornerstone」 として扱う。

★ Schedule 衝突 防止 (= reviewer MAJOR 反映) ★:

```
03:00  janitor-monkey         (= 30 日 stale archive、 早朝 disk空き作る)
03:30  ── 30 分 隔離 ────────  (= janitor 完了待ち)
04:00  monkey-watchdog        (= launchd、 全 3 monkey 24h fire 確認)
06:30  doctor-monkey          (= 30 */6 = 06:30/12:30/18:30/00:30)
12:30  doctor-monkey
18:30  doctor-monkey
00:30  doctor-monkey
00:00  conformity-monkey      (= 0 */6 = 00:00/06:00/12:00/18:00)
06:00  conformity-monkey
12:00  conformity-monkey
18:00  conformity-monkey
```

```
┌──────────────────────────────────────────────────────────────────────┐
│ anicca-janitor-monkey   (openclaw cron、 0 3 * * *)                   │
│   ── useless / orphaned cron 削除 のみ                                │
│   ── 30日 stale archive + project-niche heartbeat 移管                │
│   ── 「first-principles (revenue/physical/infra) 不該当」 → disable  │
│   ── ★ Doctor state-change author check ★ (= §3.6.4 contract):       │
│      対象 cron の last_modified_by が "anicca-doctor-monkey" + 直近   │
│      24h 内 → SKIP (= Doctor が 直そう としてる、 Janitor は触らない)  │
├──────────────────────────────────────────────────────────────────────┤
│ anicca-conformity-monkey (openclaw cron、 0 */6 * * *)                │
│   ── policy violation cron 即 disable のみ                            │
│   ── aniccaai.com 編集 (= apps/landing/ commit author=Anicca Agent)   │
│   ── cornerstone NEVER_DISABLE 違反 trigger                            │
│   ── ★ Doctor との 競合 防止 ★: cornerstone 検出 時、 Slack のみ alert │
│      (= disable は しない、 cornerstone は §3.5.2 で守る)              │
├──────────────────────────────────────────────────────────────────────┤
│ anicca-doctor-monkey    (openclaw cron、 30 */6 * * *、 = 6h offset)   │
│   ── error cron heal のみ (= ex anicca-cron-manager rename)            │
│   ── SCAN → pattern match → LLM 4-strategy → verify → close           │
│   ── ★ Janitor archive check ★ (= §3.6.4 contract):                   │
│      対象 cron が 24h 内 Janitor archive 済 → SKIP + issue 自動 close │
│      (= 不要 だから archive された の を Doctor が resurrect しない)   │
├──────────────────────────────────────────────────────────────────────┤
│ anicca-monkey-watchdog  (launchd plist、 0 4 * * *、 out-of-band)      │
│   ── 3 monkey 自身 を monitor (= out-of-band で 自己循環 回避)         │
│   ── ~/Library/LaunchAgents/ai.anicca.monkey-watchdog.plist           │
│   ── 24h 内 各 monkey が 1 fire 成功 ゼロ → Slack alert + 即 fire 試行 │
│   ── ★ Doctor の cornerstone list に watchdog 自体 含む ★ (cross-mon) │
│   ── reference: Netflix Atlas (= Simian Army を外部 monitor) pattern  │
└──────────────────────────────────────────────────────────────────────┘
```

### §3.6.4 — Coordination contract (= reviewer BLOCKING #1 反映、 新規)

★ Janitor + Doctor の 同 cron への並列 write を 防ぐ provenance 規約 ★。

**state metadata 拡張 (= cron payload に追加)**:
```json
{
  "id": "uuid",
  "name": "anicca-foo",
  "enabled": false,
  "last_modified_by": "anicca-janitor-monkey",
  "last_modified_at": "2026-06-07T03:15:22Z",
  "last_modified_reason": "30d stale archive"
}
```

**Janitor rules**:
- Read target cron の `last_modified_by`
  - 値 = `"anicca-doctor-monkey"` + `last_modified_at` < 24h前 → ★ SKIP ★ (= Doctor が直そう としてる)
  - 値 = `"Dais"` (manual edit) + `last_modified_at` < 7d 前 → ★ SKIP ★ (= 人間意思 尊重)
  - その他 → 通常 archive

**Doctor rules**:
- Read target cron の `last_modified_by`
  - 値 = `"anicca-janitor-monkey"` + `last_modified_at` < 24h 前 → ★ SKIP + issue 自動 close ★
    (= Janitor が archive した cron を Doctor が resurrect しない)
  - その他 → 通常 fix

**Conformity rules**:
- 常に `last_modified_by` を check (= 上 2 と同 ロジック)
- cornerstone (= §3.5.2 NEVER_DISABLE) → ★ disable しない、 Slack alert のみ ★

★ 全 monkey は cron 編集 前 に 必ず `last_modified_by` を 更新 ★ (= openclaw cron edit
  に metadata field 追加 で 永続化)。 これで race condition 完全 解消。

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
- ★ Hermes / oss-anicca side 同 ロジック 反映 ★ (= sister spec 予定:
  `docs/superpowers/specs/2026-06-XX-hermes-simian-army-design.md`、 v1.3 反映)
- ★ Dais の Cursor / Claude Code IDE 設定 変更 ★ (= user space、 触らない)
- ★ products-oss 上 既存 NON-cron issue ★ (= Dais 用 product issue、 触らない)
- ★ CLAUDE.md §0.19 channel list 更新 ★ (= sister spec 予定:
  `docs/superpowers/specs/2026-06-XX-content-factory-channels-update.md`、
  aniccaai.com/blog 削除 + Zenn/Dev.to/Substack 4 channel 化、 §3.2.4 から forward-ref)

---

## §8 — Verification Plan (= V12-1 〜 V12-30、 dependency arrow 付き v1.3)

★ 実行 順序 (= reviewer MINOR 反映、 依存 明示) ★:

```
═════════ DONE (= push 済) ═════════
V12-1  ✅ gh repo rename × 2
V12-2  ✅ local origin url 更新 × 2
V12-3  ✅ fix.sh REPO 変数 置換
V12-4  ✅ HEARTBEAT.md REPO 置換
V12-5  ✅ 5 violation issue 移行 (products → anicca-dais)
V12-6  ✅ grep + sed 全層 置換 (CLAUDE.md / memory / docs / skills)
V12-7  ✅ push CLAUDE.md + memory + spec
V12-8  ✅ 4 aniccaai.com 編集 cron disable
V12-9  ✅ lefthook hook 設置 + test (single layer、 v1.3 で 3 layer 強化 予定)
V12-22 ✅ fix.sh STRATEGIES = OpenClaw 正規 chain
V12-24 ✅ spec self-review (v1.2) + code-reviewer 反映 (v1.3)

═════════ PHASE 1 (= P1 dep ordering) ═════════
V12-12 ─→ V12-13 ─→ V12-14
(tasks.json schema 拡張 → HEARTBEAT.md §2 PICK P3 → heartbeat 1 fire verify)

V12-12 ─→ V12-11
(schema 先 → 7 watcher を tasks.json へ移管 + watch-sweep 2 ファイル分離)

V12-11 ─→ V12-27 (Janitor は tasks.json 既存 を 前提、 reviewer MINOR 反映)

═════════ PHASE 2 (= P0 強化、 V12-9 v1.3 反映 + V12-26) ═════════
V12-9 v1.3 (= lefthook hook 3-layer hardening)
V12-26 watercolor-monk-noon 真因 dig + fix

═════════ PHASE 3 (= P1 Simian Army 新規 4 skill) ═════════
V12-29 ─→ V12-27 ─→ V12-28 ─→ V12-30
(cron-manager → Doctor rename 先 → Janitor → Conformity → Watchdog 順)
注: V12-30 watchdog は launchd plist (= 別 path、 openclaw cron ではない)

═════════ PHASE 4 (= P2 強化) ═════════
V12-18 ─→ V12-19 ─→ V12-20 ─→ V12-21 ─→ V12-23
(allowlist JIT → NEVER_DISABLE 28 件 → error pattern → timeout 引上 → 1 fire verify)

═════════ PHASE 5 (= P2 blog 404 修復) ═════════
V12-15 ─→ V12-16 ─→ V12-17
(taste skill canonical → blog route 生成 → curl 200 verify)

═════════ PHASE 6 (= 完成) ═════════
V12-25 finishing-a-development-branch (= 4 option + push)
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
