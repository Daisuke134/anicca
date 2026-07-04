# Claude Code セットアップ最適化 — Design Spec

**日付**: 2026-07-04 / **状態**: 監査完了 → 実装フェーズ / **監査全文**: `.cursor/plans/claude-code-pc-woolly-island.md`

## 背景

read-only 監査（3 Explore 並列）で判明: ①ディスク92% ②CLAUDE.md 67KB 常時ロード + 「3箇所同期」による矛盾11件 ③skills 226+473 三重管理・43衝突 ④`rm -rf:*` グローバル allow ⑤平文シークレット散在 ⑥MCP 3ファイル分散 ⑦repo 8箇所分散。

## Dais 決定事項（2026-07-04 verbatim 確定）

| ID | 決定 | 帰結 |
|---|---|---|
| D1 | **CloakBrowser daily-driver が正**。camofox-first の旧記述（project 0.30、agent-browser/tier-a-bypass skill description、MEMORY.md 旧行）は削除 | Phase 3/4 で該当箇所を上書き |
| D2 | **CLAUDE.md は履歴帳ではない。上書き（overwrite）運用**。「Dais verbatim + 日付 + incident 史」の append が矛盾の根源。新ルールが出たら旧ルールは削除、supersede は上書きで表現。歴史は git log と memory が持つ | CLAUDE.md 冒頭に書き方規約（現在形・無日付・canonical 1箇所・precedence 表 1 個）を置く |
| D3 | **モデル分業**: Fable 5 (effort max) = オーケストレーター（計画・分解・統合のみ、コードを書かない）/ Opus = 深い推論サブエージェント（設計判断・複雑デバッグ・レビュー）/ Sonnet = 機械的作業（実装・boilerplate・テスト・雑務）。出典: developersdigest.tech/blog/fable-5-agent-fleet-orchestration + zenn.dev/yui/articles/740da24e9ee419 | T1 で settings + agents frontmatter に反映 |
| D4 | 実装は **superpowers SDD** で進める。Ultraplan 版プランは破棄、本 spec + ローカルプランが正 | 本ファイル |

## D3 実装詳細（T1）

| 対象 | 変更 |
|---|---|
| `~/anicca-project/.claude/settings.json` | `"model": "claude-opus-4-8"` → `"claude-fable-5"`（main = orchestrator）。founder-loop 影響なし（brain.mjs は `--model` 明示 + /tmp cwd + 最小 env で project settings を読まない — 2026-07-04 grep 確認済） |
| `.cursor/agents/build-error-resolver.md` | model: opus → **sonnet**（機械的 fix） |
| `.cursor/agents/refactor-cleaner.md` | model: opus → **sonnet** |
| `.cursor/agents/tdd-guide.md` | model: opus → **sonnet** |
| `.cursor/agents/code-quality-reviewer.md` | model 未指定 → **opus**（レビュー = 深い推論） |
| `.cursor/agents/security-auditor.md` | model 未指定 → **opus** |
| `.cursor/agents/test-automation-engineer.md` | model 未指定 → **sonnet** |
| 維持 | architect/planner = opus、deploy-checker = haiku、fact-checker/tech-spec-researcher = sonnet |
| 運用 | main（Fable）は Edit/Write でコードを書かない。実装 = Sonnet subagent、設計判断・レビュー = Opus subagent に委譲 |

### effort 設定（公式 docs 確認済: code.claude.com/docs/en/model-config）

- レベル: low / medium / high / xhigh / max。Fable 5 デフォルト = high。**max は settings に永続化不可（セッション限定）** → settings は `effortLevel: "xhigh"`、重い計画セッションのみ手動 `/effort max`
- `CLAUDE_CODE_EFFORT_LEVEL` env は subagent の frontmatter `effort:` にも勝ってしまう（= Sonnet 実装係まで max になり無駄）ため**使わない**
- subagent frontmatter は `model:`（sonnet/opus/haiku/fable/full ID/inherit、**デフォルト = inherit**）と `effort:` を持つ。model 未指定 agent は main の Fable を継承して高コスト化するため、全 agent に model 明示が必須（T1 で実施）
- 補足（developersdigest 記事）: Fable 5 は refusal を通常 200 で返すことがある → オーケストレーターループには Opus 4.8 フォールバックを想定しておく

## フェーズ（監査プランの Phase 0-6 を継承、詳細は監査プラン参照）

| Task | 内容 | 破壊的 |
|---|---|---|
| T1 | D3 モデル分業の設定反映 | no |
| T2 | Phase 0 保全: 設定 tarball backup + untracked 166 triage（.agents/skills = commit or ignore 確定） | no |
| T3 | Phase 1 ディスク救急: cache 残骸→worktree→file-history→90日超セッションログ（memory/ 絶対除外）で 4-5GB 回収 | **yes** |
| T4 | Phase 2 安全性（2026-07-04 調査結果で方針上書き）: ①permissions 再設計 ✅（rm 4パス限定 allow / force-push ask / .p8 .pem Read deny / dangerous-prompt 復活）②死 MCP 削除 ✅（headroom=バイナリ欠損, x-search=402/403。~/.claude.json 9→7 servers、全セッション再起動後に再確認要）③**${VAR} 化は中止** — 起動時 env 不在（zshrc は FIRECRAWL/VIBECODE のみ export）で parse 失敗する + .env 全 export は露出面拡大。代替 = mcp.json chmod 600 + mcp.json を MCP キーの canonical とする ④.p8 判定 = **漏洩なし**（4 repo 全履歴 add ゼロ、鍵は repo 外 3+1 箇所）。ただし mcp.json の鍵パスが ~/Downloads の消えた実体を指し ASC MCP 破損中 → 実在パス（~/.appstoreconnect/private_keys/）に修正 ⑤ローテーション不要判定（KEY_ID/ISSUER_ID は識別子、.p8 未漏洩のため）。Fastfile ハードコード除去は T5 系列の別途 ⑥.env の ASC 別名 8 種は cron 参照リスクがあるため今回は温存（canonical 名の文書化のみ） | 一部 |
| T5 | Phase 3 CLAUDE.md diet: global 18K→6K、project 49K→15K。**D1/D2 適用**（camofox 記述削除、履歴文体→現在形上書き、「3箇所同期」全廃、precedence 表 1 個、~/.hermes 等 stale 削除） | no |
| T6 | Phase 4 skills 大掃除（2026-07-04 棚卸しで方針上書き）: **hyperframes×7 と spec 系7 は意図設計の hub-spoke スイートのため統合しない**。Wave 1（リスクゼロ）= ①global の切れ symlink 50 本削除（~/.agents/skills に実体なし）②SKILL.md 無し container 10 dir → ~/Archive/skill-repos/ ③description 欠落 3 件補完（agent-memory, content-creator, conway-automaton）④commands/ 12 本アーカイブ（11 本使用 0 回、conway 1 回のみ）⑤computer-use を ~/.claude.json 該当 project の enabledMcpServers から除去。Wave 2 = divergent 衝突 12 件の新旧解消（tie 28 件 = 同日 bulk copy で無害・保留）+ 小統合（tiktok-ads 系 2→1、twitter-algorithm-optimizer+x-algorithm→1、substack 2→1、x-research 空 dir 削除）+ project .mcp.json の壊れ ASC エントリ削除 | 一部 |
| T7 | Phase 5 PC 再編: ~/Projects + ~/Archive 新設、参照 grep → 移動、Desktop 183→<10、.bak 掃除。重複 clone は T2 調査で確定済: 残す = `~/work/camofox-browser`（2026-05-23、17日新）+ `~/Developer/video-use`（2026-05-14、29日新）、削除 = `~/Developer/camofox-browser` + `~/anicca-video-lab/video-use`（remote 同一の真正重複） | **yes** |
| T8 | Phase 6 運用定着: disk-guard hook、ログアーカイブ cron、fact-checker global 昇格 | no |

## 境界

- **不可侵 store（Dais 2026-07-04 verbatim「deleting that is a sin」）: `~/.cloak`（ブラウザ履歴/ログイン profile）、`~/anicca-rtdash`、`~/anicca-monk-factory` — 削除・キャッシュ掃除・移動の対象外。** disk 回収は他の再生成可能キャッシュのみ
- canonical 4 path（~/anicca-project, ~/anicca, ~/.openclaw, ~/.claude）は移動しない
- ~/.openclaw runtime の中身（cron/skills 473）は本 spec の対象外（構造指摘のみ）
- memory/ ディレクトリは削除・移動の対象外

## 検証

- T1: 新セッションで `/model` 表示 = Fable 5（pin 衝突警告が消える）、Agent tool で sonnet/opus subagent が指定 model で起動
- T3: `df -h /` 残 20GB+
- T5: 新セッション起動注入の目視 + 矛盾 11 件が grep で 0 hit（例: `grep -rn "camofox >" CLAUDE.md` = 0）
- 各 T 完了ごとに commit+push
