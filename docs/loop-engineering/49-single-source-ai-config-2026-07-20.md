# Single-source AI config（sync の廃止、2026-07-20 調査+裁定）

## 問いの修正（first principles）
「2つの置き場をどう sync するか」は誤った問い。**実体を1つにして全 agent が symlink で読む** — sync 問題自体を消す。

## 公式根拠（確定）
| 事実 | 出典 |
|---|---|
| Agent Skills 標準は「Build a skill once, use across any skills-compatible agent」。discovery path は各 agent 依存 | agentskills.io/specification |
| Codex user scope = `~/.agents/skills`、symlink 追跡を公式明記 | developers.openai.com/codex/skills |
| Claude personal = `~/.claude/skills/<name>`、per-skill symlink 可、同一 target は1回だけ load | code.claude.com/docs/en/skills |
| Claude は AGENTS.md を CLAUDE.md から @import / symlink で共有可（公式明記） | code.claude.com/docs/en/memory#agents-md |
| **Claude は `.agents/skills` を native discovery しない**（要望 issue #31005 open）— 「将来読む」を前提にしない | github.com/anthropics/claude-code/issues/31005 |
| 実例: HF Transformers（.ai/ 正本 + Makefile symlink）、InstantDB（CLAUDE.md→AGENTS.md）、sushichan044 dotfiles（chezmoi）、riethmayer dotfiles（stow ADR: 実体 .agents/skills、.claude/skills → symlink） | 各 repo |

## 裁定（Fable）
**base 案を採用**: 新 repo を作らず、**`~/.agents/skills` を skills の唯一の実体**とし、`~/.claude/skills/<name>` を per-skill symlink にする。
- 理由: ~/.agents/skills が既に実体57で最大。Codex 公式の user 置き場でもある。新 repo `~/ai-config` は「もう1つの置き場」を増やす = 移行コスト増（best 案は将来の dotfiles 統合時に再検討）。
- ~/.agents/skills を git 化して GitHub (private) へ push（phone からも見える、cloud 資産化）。
- 重複実体（building-agents 等、両側に存在）: diff を取り、**新しい方を勝者**にして片方を symlink 化。diff がある場合は報告後に裁定。
- whole-dir symlink は棄却（plugin/vendor skill の同居を塞ぐ）。per-skill link farm。
- rules: repo レベルは現行維持（AGENTS.md 40行 + CLAUDE.md）。global レベル（~/.claude/CLAUDE.md = Dais 規律集）の単一実体化は **Phase 2**（提案 diff を作り Fable 検分後に適用）。
- settings/hooks/MCP は schema が違うため同一ファイル化しない（vendor 差分として現状維持）。

## TO-BE
```
~/.agents/skills/<name>/SKILL.md   ← 唯一の実体 (git repo, GitHub private push)
~/.claude/skills/<name> ──symlink──↑ (per-skill)
repo/.claude/skills                ← repo 固有はそのまま
AGENTS.md (repo, 40行 curated)     ← Codex rules
CLAUDE.md → 参照1行群 + rules/paths ← Claude rules（既存）
```

## 実施結果（2026-07-20 実測検証済み）
- ~/.claude/skills = 11 symlink（全て ~/.agents/skills 配下向き）、~/.agents/skills = 実体65 + broken 0、重複 0件。Sol 実装（backup: skills.bak-20260720 ×2、broken vendor link は skills.broken-20260720/ へ退避、旧 .git は skills.gitmeta-20260720/ へ退避）。
- claude -p での skill listing 83 unique 確認（Sol 実測）。
- **GitHub sync は既設だった**: `ai.anicca.agents-skills-sync`（launchd、~/.agents 全体 ⇄ private repo anicca-agents-skills、双方向）。新規に作りかけた nested git repo は誤りで除去 → 既存 loop kickstart → remote head 8f38e3a 一致を実測。教訓 = 登録簿を先に引く（掟どおり）。
- gitleaks: 誤検知1件（whisper model 名）を .gitleaksignore 化、0 leaks。

## Phase 2 裁定: chezmoi（2026-07-21 調査確定）
- **採用 = chezmoi (20,758★, v2.71.0) + GitHub private repo + age 暗号化**。全 AI config（~/.claude/CLAUDE.md, settings.json, hooks, rules / ~/.codex/AGENTS.md, config.toml / per-skill symlink 定義）をファイル単位で管理、新 machine/cloud VM は `chezmoi init --apply <repo>` 1コマンドで再現。
- 根拠: `symlink_` prefix で既設 per-skill link farm をそのまま投影可（chezmoi.io/reference/source-state-attributes）。secret は .chezmoiignore + age（OAuth/session/cache は除外し再login、必要 token のみ暗号化）。実例 = Bae-ChangHyun/agent-dotfiles（Claude+Codex+chezmoi+age、pattern のみ copy）。
- 棄却: GNU Stow（secret/template/bootstrap を自作する総コスト高）、bare git（HOME=worktree の誤追跡面）、AI特化新顔（0-9★、未成熟）。
- 注意: directory 丸ごと置換は禁止（per-file/per-link 管理）。Codex→Claude の二段 link は canonical (~/.agents/skills) へ直接化。age key の backup 必須（1Password）。gate = gitleaks + chezmoi diff。

## 誤りの記録
- 「cron で 30分毎 sync」案（cloud-mobile spec #1 の openclaw sync とは別物）を skills 共有に使う発想は誤り。sync は GitHub バックアップ（phone の窓）にだけ使い、agent 間共有には使わない。
- 最初の symlink 向き（~/.agents ← ~/.claude）は逆だった。実体は ~/.agents/skills 側に寄せる。
