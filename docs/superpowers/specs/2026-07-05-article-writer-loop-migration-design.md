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

## 3. 追加確認事項(2026-07-05、Web検索で確定): ¥500単発 + メンバーシップは併用できる

出典: note公式ヘルプセンター「メンバーシップにメンバー特典記事を追加する(オーナー向け)」
https://www.help-note.com/hc/ja/articles/22752958504985
核心の引用:「**有料記事の場合**: メンバーシップに記事を追加すると、参加中のメンバーは記事が
読めるようになります。※**メンバーシップに入っていないユーザーも、有料記事として購入すれば
読むことは可能**です。」

```
①記事を「有料記事・¥500」として公開(単発課金、既に実証済み: nfb2ace9f0ed8)
                    │
②同じ記事をメンバーシップの「特典記事」として追加(編集画面の別操作、コード変更ではなく
   note UI上の紐づけ操作。追加コストなし、メンバーシップ開設自体が無料)
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
  メンバーシップ会員は        非会員は¥500払えば
  月額料金内で無料で読める     その記事だけ単発購入できる
```

**方針**: 「メンバーシップ固定 → ¥500単発に置換」ではなく、**両方を同じ記事に対して設定する**
(Task #5 参照、TaskList上でも更新済み)。

## 4. worktree自体の掃除(2026-07-05、"work in a worktree → merge → delete" 原則の実態調査で発覚)

`~/anicca-human-funded`は`feature/human-funded`のworktreeとして2026-06-09に作られたまま、
**一度もmainへマージされず26日間放置**されていた(main側50 commit vs 本worktree側619 commit、
957ファイル差分)。この中に**実稼働中のx402 mainnetサーバー**
(`ai.anicca.x402-research-serve`、launchd PID稼働中、founder wallet 0x810fへUSDC着金設計)
が紛れ込んでいた。確認の結果、このx402-sellのソースコードは`~/anicca`本体にも同一のものが
既に存在する(差分はnode_modulesのビルド成果物のみ)ため、単純にplistの参照先を本体へ
向け直せば安全に切り替えられる。957ファイルの残り差分(profitable-article-writer以外)に
本当に必要な物が埋もれていないかは別途監査が必要(Task #1に統合済み)。

## 5. TODO(正しい順序、依存関係順。TaskListに登録済み、#1〜#13)

**Phase 0: worktree安全化(x402サーバーを本体へ退避してから畳む)**
1. `ai.anicca.x402-research-serve.plist`を`~/anicca/skills/earn/x402-sell/serve-mainnet-boot.sh`
   参照に張り替え→再起動→ログで`x402_seller:up`が新パスから出ることを確認。
   957ファイル差分の残りを監査(本当に必要な物が無いか)。問題なければ
   `git worktree remove` + branchはremoteに残したままlocal整理。

**Phase 1: skill本体の退避(★openclaw削除前に今日中★)**
2. `~/.openclaw/skills/ai-entity-article-writer/`の全ファイルを`~/anicca/skills/earn/article/`
   へコピー、`~/anicca`側でcommit+push。3形式(`$HOME`/`~`/絶対パス)で旧パス参照が
   無いかgrep確認([[feedback_move_refcheck_must_cover_skill_scripts_and_home_forms]])。
3. `~/.claude/skills/ai-entity-article-writer`のsymlinkを新パスへ張り替え。

**Phase 2: 人間ループ除去 + 課金二重化(コード修正)**
4. `publish_guard.py`: 手動sentinelファイル必須 → 既存ゲート(freshness/seo/
   language-purity/bookmark-gate)全PASS時に自動発行するトークンに置換。
5. `toggle-plan.py`(+ `set-membership.py`): 記事タイプ=有料・¥500単発**に加えて**、
   同じ記事をメンバーシップの特典記事としても紐づける(§3参照、両方設定・置換ではない)。
6. `run.sh`: 人間が公開ボタンを押すステップを削除、ゲートPASSから直接publishへ接続。

**Phase 3: claude-pループ雛形の追加(既存5本と同型)**
7. `clip-cli.sh`/`clip-healthcheck.sh`/`launchd/*.plist`をコピーして`article`用に:
   `article-cli.sh`(STARTUP prompt = Skill呼び出し指示)、`article-healthcheck.sh`、
   `launchd/*.plist`。
8. `loop-report.sh`配線: 各wake終了時にDID/RESULT/EARNED/EVIDENCE_URL(公開記事URL)を送る
   1行を追加。他5ループと同じ呼び出し形。
9. `~/anicca/skills/registry.json`に`earn/article`slotを追加(`earn/clip`と同じ
   フォーマット: track/dir/entrypoint/status/owner/spec/summary)。

**Phase 4: 起動 + 検証(fresh evidence、DONEの定義まで)**
10. launchd登録+tmux起動+CronCreate、`launchctl list`で確認。
11. 初回wake E2E確認(テストモードでなく実ゲート): 実際に1本書かれ、ゲートを通り、
    ¥500単発+メンバーシップ特典の両方が設定され、独立検証(200+content-match)が通る。
12. mail報告のfresh evidence確認: `loop-report.sh`経由で実際にDaisのメールへ届く。
13. money check(V4、DONEの定義): 翌日以降のwakeでnote売上APIを読み、実際の¥入金を
    検知して`earn-ledger.jsonl`に記帳するところまで確認。

## 6. スコープ外(今回やらない、方針記録のみ)

- クラウド化(5層分解、`2026-07-04-openclaw-claude-p-merge-design.md` §15)は別タスク。
  まずローカルclaude-pループとして人間ゼロを確立してから着手。
- 個別AI自己記事化(§10.3)・swarm highlight記事(§10.4)は`ai-entity-article-writer`が
  6本目ループとして安定稼働した後の次段。
