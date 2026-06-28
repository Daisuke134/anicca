# Spec: CLAUDE.md ダイエット (Qiita「お前のClaude Codeの使い方は間違っている」#1 適用) — 2026-06-28

## Goal
記事 (https://qiita.com/tehito/items/356e5f1dba112a075be1) のミス#1「CLAUDE.md を全部入りの聖書にする」を是正。
「特定作業のときだけ要る知識」を Agent Skill (`.claude/skills/`) に逃がし、CLAUDE.md は毎ターン効く憲法に保つ。
情報損失ゼロ (= verbatim 移植) が絶対条件。削除ではなく引っ越し。

## 現状 (実測 2026-06-28)
- global `~/.claude/CLAUDE.md` = 184行 (git 管理外 = push 不可)
- project `~/anicca-project/CLAUDE.md` = 642行 (anicca-products repo, push 可) ← 肥大の本体
- 全 CLAUDE.md 群 ≈ 97,000 字 ≈ 24,000 token / 毎ターン

## 振り分け基準 (記事の基準 = 「特定作業のときだけ要る知識」か)
| 判定 | 内容 | 行き先 |
|---|---|---|
| MOVE | TIER A bypass patterns (CapSolver/camofox/3DS curl, project 260-372, 112行) | skill `tier-a-bypass` |
| MOVE | funder-apply 0.27 詳細 (global 126-153, 28行, 既に memory+CONSTITUTION+application-kit に triple-sync) | pointer 化 |
| KEEP | HONESTY / VERIFICATION / FABRICATION GUARD / FACT-CHECKER (毎ターンの行動規律) | CLAUDE.md |
| KEEP | HARD RULE #-3/#-2/#-1/#0 + 0.00/0.24/0.36/0.37/0.38/0.40 (行動憲法) | CLAUDE.md |
| KEEP | disk-hygiene 0.26 (= 受動的・毎ターン規律。skill化すると invoke されず ENOSPC 再発 = Dais激怒incidentの再現) | CLAUDE.md |
| KEEP | push map / folder tree / architecture / branch flow / tool priority (project固有・頻出参照) | CLAUDE.md (今回は触らない) |

## 変更 (MUST)
1. MUST `~/anicca-project/.claude/skills/tier-a-bypass/SKILL.md` を作成し、TIER A Pattern 1-4 + 適用範囲を verbatim 収録。frontmatter description に「CAPTCHAだから諦め と言う前に invoke」guard を明記。
2. MUST project CLAUDE.md の TIER A ブロック (260-372) を ~5行 pointer に置換。pointer は (a) 行動 guard「『CAPTCHAだから諦め』『OAuthは人』と言う前に tier-a-bypass skill を引け」を保持 (b) skill path + memory runbook path を指す。
3. MUST global CLAUDE.md funder 0.27 (126-153) を 4行 pointer に置換。detail は memory + CONSTITUTION + application-kit に既存。
4. MUST `/compact` 規律を project 絶対ルール 0.8 に明文化 = 「実装途中の手動 compact 禁止、コミット直後のみ。長作業は計画を spec/plan file に永続化」(記事ミス#3)。

## 検証アーキテクチャ (invariant = grep で機械検証)
- INV1: skill 内に Pattern 1-4 の全コードが存在 (`grep AntiTurnstileTaskProxyLess`, `grep 'gog gmail get'`, `grep RecaptchaV2TaskProxyless` が skill にヒット)。
- INV2: project CLAUDE.md に「tier-a-bypass」pointer が存在し、curl/CapSolver の生 bash は CLAUDE.md から消えている (`grep 'api.capsolver.com' CLAUDE.md` = 0 hit)。
- INV3: 全 HARD RULE 見出し (#-3,#-2,#-1,#0,0.x) が project CLAUDE.md に残存 (移動前後で見出し数が funder/TIER以外 不変)。
- INV4: project CLAUDE.md 行数が削減 (642 → ~535 前後)。
- INV5: global CLAUDE.md に funder pointer 存在 + KIT.md 参照保持。
- INV6: disk-hygiene 0.26 と 0.24 NO-FAKE は global にそのまま残存 (誤移動していない)。

## 検証主体 (VCSDD)
- Builder = 私 (main agent)。
- Adversary = fresh `vcsdd:vcsdd-adversary` (disk-only, builder context ゼロ)。INV1-6 を binary PASS/FAIL で判定。「looks good」不可。
- 私自身の独立 verify = INV1-6 の grep を live 実行 + 行数 diff。
- DONE = adversary PASS + 私の grep 全 green + commit+push (project repo)。

## 非対象 (今回やらない)
- global ~/.claude は git 管理外 → push しない (ローカル編集のみ、funder pointer 化だけ)。
- architecture ASCII diagram / folder tree の trim は別 pass (project固有・頻出参照のため保留)。
