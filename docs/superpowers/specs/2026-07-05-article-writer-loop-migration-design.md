# ai-entity-article-writer → claude-p 6本目ループ移植 — Design

**Date**: 2026-07-05 · **Branch(作業先)**: `~/anicca` (`Daisuke134/anicca.git`, canonical) ·
**Owner**: 私(myclaude, human-funded) · **Trigger**: Dais の一連の指摘(2026-07-04〜05、要旨):

> battle-testedな`ai-entity-article-writer`があるのに、なぜ別repo(`~/anicca-human-funded`)に
> `profitable-article-writer`という新skillをゼロから作ったのか。openclawは明日消す。
> claude-pループとして、私(Dais)がloopに入らずに記事を書いて金にする仕組みにしろ。

## 0. 前提の事実訂正(このセッション内で確認済み、推測ゼロ)

| # | 事実 | 確認方法 |
|---|---|---|
| 1 | `~/anicca-human-funded` = `~/anicca`の**正規git worktree**(`git worktree list`で確認、`gitdir: .../anicca/.git/worktrees/anicca-human-funded`)、branch `feature/human-funded`。別repoではない | `git worktree list` |
| 2 | にも関わらず、その中に`skills/profitable-article-writer`という**別物の新skillをVCSDD strictでゼロから4日間構築**してしまった(誤り) | 会話履歴 |
| 3 | `ai-entity-article-writer`本体は`~/.openclaw/skills/ai-entity-article-writer/`(**明日削除予定**、DeepSeek課金のopenclaw配下) | `ls` / `git log` |
| 4 | `~/.claude/skills/ai-entity-article-writer`は**symlink**(`→ ~/.openclaw/skills/ai-entity-article-writer`)。コピーではなく実体が1つ。**openclaw削除で道連れにdead linkになる** | `ls -la` |
| 5 | `~/.claude/skills/`はgit管理外・このMac1台限定。他のswarm instanceに配れない | `git rev-parse --is-inside-work-tree` → fatal |
| 6 | 稼働中のclaude-pループは5本、全て`~/anicca/skills/earn/{clip,affiliate,video,bounty,gig}/`、雛形= `<name>-cli.sh`(tmux常駐、`claude -p`起動)+`<name>-healthcheck.sh`+`launchd/*.plist`+`loop-report.sh`(mail報告、evidence_url付き) | `find`, `~/Library/LaunchAgents/` |
| 7 | `~/anicca/skills/registry.json`に`earn/clip`等は登録済みだが`earn/article`は無い | `grep` |
| 8 | `ai-entity-article-writer`は`SKILL.md`形式(Claude Code純正Skill)。bashを1から書く必要はなく、`claude -p`セッションが`Skill: ai-entity-article-writer`をagenticに呼べば動く(clip等のbash直叩き型とは方式が違う) | `SKILL.md` frontmatter確認 |
| 9 | 現状の唯一の人間ループ = `scripts/note-publish/publish_guard.py`(手動sentinelファイル必須)+`toggle-plan.py`(メンバーシップ固定、単発課金なし) | `grep` |

## 1. 何が間違いだったか(1行)

既存の battle-tested skill を**編集**すべきところを、別worktree内に**複製**して新skillをゼロから作った。かつ編集先の候補として明日消える`~/.openclaw`をそのまま残す提案もした。

## 2. あるべき姿(ASCII)

```
今日中に必須(openclaw削除前)
┌─────────────────────────────┐        ┌──────────────────────────────────┐
│ ~/.openclaw/skills/           │  git   │ ~/anicca/skills/earn/article/      │
│  ai-entity-article-writer/    │ ─mv→   │  (実体、以後ここが正本、push済み)    │
│  (明日消える)                  │        │                                    │
└─────────────────────────────┘        └──────────────────────────────────┘
                                                       │
                                     ~/.claude/skills/ai-entity-article-writer
                                     symlinkを新パスへ張り替え(私はこれで今後も呼べる)

移植と同時に3箇所だけ書き換え(新規コード無し、既存資産を活かす)
  publish_guard.py  人間sentinel必須       → 自動ゲート(freshness/seo/language-purity/
                                             bookmark-gate)全PASSで発行するトークンに置換
  toggle-plan.py     メンバーシップ固定    → note記事タイプ=有料、¥500単発
  run.sh             人間が公開ボタンを押す→ このステップ自体を削除(ゲートPASS=即公開)

claude-p 6本目ループとして常駐(既存5本と同型)
  ~/anicca/skills/earn/article/
    ├── article-cli.sh          tmux常駐、claude -p 起動、STARTUP="Skill: ai-entity-
    │                            article-writer を呼んで1本書いて公開してreportして"
    ├── article-healthcheck.sh  launchd 5分毎、死んでたら再起動
    ├── launchd/*.plist         Mac起動時に自動起床
    └── (移植された run.sh/gates/*/note-publish/* 一式、上記3箇所修正済み)

  registry.json に "earn/article" slot 追加(既存 earn/clip と同じ形)

1 wake の流れ(人間ゼロ)
  launchd→tmux→article-cli.sh(claude -p)
    → Skill: ai-entity-article-writer 呼び出し
    → TOPIC(モデル自身が選ぶ)→RESEARCH(context7+firecrawl)→WRITE(既存プレイブック20-30条)
    → GATE(freshness/seo/language-purity/bookmark、fail-closed、最大3回)
       FAIL×4 → 公開せず終了(嘘をつかない)
    → PRICE(¥500単発)→PUBLISH(ゲートPASS即時)
    → VERIFY(別プロセス、ログアウト状態でcurl、200+content-match)
    → loop-report.sh → Daisへmail(DID/RESULT/EARNED/EVIDENCE_URL=公開記事URL)
    → 翌日以降のwakeでnote売上API確認→入金検知→earn-ledger.jsonl記帳 = DONE(V4)
```

## 3. TODO(正しい順序、依存関係順。このままTaskCreateに登録する)

1. **`~/anicca-human-funded` worktree(`feature/human-funded`)を畳む** — `profitable-article-writer`
   skillと分岐したregistry.jsonの編集を破棄。worktree remove、branch削除は remote に history
   を残したままlocalのみ整理(取り消し可能な形で)。
2. **openclaw削除前の退避(★今日中、最優先★)**: `~/.openclaw/skills/ai-entity-article-writer/`
   の全ファイルを`~/anicca/skills/earn/article/`へコピー、`~/anicca`側でgit add+commit+push。
   移動前後で[[feedback_move_refcheck_must_cover_skill_scripts_and_home_forms]]に従い、
   3形式(`$HOME`/`~`/絶対パス)全てで旧パス参照が無いかgrep確認。
3. **symlink張り替え**: `~/.claude/skills/ai-entity-article-writer` → 新パス
   (`~/anicca/skills/earn/article`)を指すよう再作成。
4. **人間ループ除去(3箇所、コード修正)**:
   a. `publish_guard.py`: 手動sentinelファイル必須 → 既存ゲート(freshness/seo/
      language-purity/bookmark-gate)全PASS時に自動発行するトークンに置換。
   b. `toggle-plan.py`(+ `set-membership.py`): メンバーシップ固定 → 記事タイプ=有料・
      ¥500単発(価格入力+有料エリア指定ラインの自動化)。
   c. `run.sh`: 人間が公開ボタンを押すステップを削除、ゲートPASSから直接publishへ接続。
5. **claude-pループ雛形の追加**(既存`clip-cli.sh`/`clip-healthcheck.sh`/`launchd/*.plist`を
   コピーして名前だけ`article`に変更): `article-cli.sh`(STARTUP prompt = Skill呼び出し
   指示)、`article-healthcheck.sh`、`launchd/*.plist`。
6. **`loop-report.sh`配線**: 各wake終了時に呼ぶ1行を追加(DID/RESULT/EARNED/EVIDENCE_URL=
   公開記事URL)。他5ループと同じ呼び出し形。
7. **registry.json登録**: `~/anicca/skills/registry.json`に`earn/article`slotを追加
   (`earn/clip`と同じフォーマット: track/dir/entrypoint/status/owner/spec/summary)。
8. **launchd登録+tmux起動+CronCreate**: 既存5ループと同じ手順で起動、`launchctl list`で
   確認。
9. **初回wake E2E確認(fresh evidence、テストモードでなく実ゲート)**: 実際に1本記事が
   書かれ、ゲートを通り、¥500単発設定で公開され、`verify-note.py`/`verify-public.py`相当の
   独立検証(200+content-match)が通ることを確認。
10. **mail報告のfresh evidence確認**: `loop-report.sh`経由でDaisのメールに
    DID/RESULT/EARNED/EVIDENCE_URLが実際に届くことを確認(Task #3/#4と同じ確認方式)。
11. **money check(V4、DONEの定義)**: 翌日以降のwakeでnote売上APIを読み、実際の¥入金を
    検知して`earn-ledger.jsonl`に記帳するところまで確認。ここまでで初めて「金になった」
    と言える。

## 4. スコープ外(今回やらない、方針記録のみ)

- クラウド化(5層分解、`2026-07-04-openclaw-claude-p-merge-design.md` §15)は別タスク。
  まずローカルclaude-pループとして人間ゼロを確立してから着手。
- 個別AI自己記事化(§10.3)・swarm highlight記事(§10.4)は`ai-entity-article-writer`が
  6本目ループとして安定稼働した後の次段。
