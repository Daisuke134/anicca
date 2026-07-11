# Loop Engineering — INDEX / MAP（正本の地図。まずここを読む）

anicca の「毎日 自走し、自分で壊れを直し、自分で改善する loop」の設計・真実監査・BP を1箇所に地図化。
**目的**: no-human-loop（Dais は loop の外、何もしない）を実現する loop を設計・運用する。他 agent(記事執筆の別 Claude 含む)はまずこの README で「どこに何があるか」を知り、必要な file だけ読む。

## 🧭 どこに何があるか

| 知りたいこと | file | 種別 |
|---|---|---|
| **loop 全体の設計 SSOT**（2系統分離 / to-be ASCII / 全 TODO / verifier 原則） | `23-anicca-loop-architecture-redesign.md` | ★正本(最新) |
| **全 loop 共通 verifier の設計**（OSS 調査→ProofShot+Base MCP+evaluator-optimizer を copy+tweak、全 loop へ配布） | `24-shared-ground-truth-verifier-design.md` | ★正本(verifier) |
| **loop 設計の BP**（Anthropic/AWS 一次ソース + 我々の設計評価 + /loop 活用） | `22-anthropic-bp-loop-verification-review-2026-07-11.md` | 参考(引用付) |
| **全 loop の真実監査**（報告 vs 実 side-effect、どれが壊れ/嘘か、browser/on-chain 実確認） | `../superpowers/evidence/LOOPS-TRUTH-AUDIT.md` | ★真実(最新) |
| **嘘防止の鉄則**（report/ledger/test-green ≠ working、own-eyes 必須） | memory `feedback_never_claim_working_without_own_eyes_verification.md` | ★行動則 |
| loop 運用判定・out-of-loop 3段 | `../../<memory>reference_loop_engineering_out_of_loop_architecture` | 参考 |
| Loop Engineering 9-source synthesis | memory `reference_loop_engineering` | 参考 |
| /loop コマンド詳細 | `~/.claude/references/loop-command.md` | 参考 |
| 過去の status-quo 監査 | `18-status-quo-audit-2026-07-11.md` 等 | 履歴 |

## 🎯 3つの核心原則（bake 済、全 loop に適用）
1. **verifier は report を読まない**。executor と別 fresh context で、実 side-effect(投稿URL logged-out / on-chain tx / ledger 実増 / gcal readback / exit code)を決定的にチェック。done = 検証コマンド出力、text match 禁止。（出典=22, 実装雛形=connector_streak_verify.py）
2. **no human in loop**: loop が毎日 自走→実成果→自己検証→自己修復→再発防止を code に焼く。Dais は外。
3. **fix パターン**: 私(agent)が手で直す→own-eyes で working 確認→**その検証を loop の verifier に焼く**→以後 loop が自分でやる（babysitting 消滅）。

## 📌 運用ルール（Dais 2026-07-11）
- **folder を作ったら必ず README(この形式の mapping)を置く**。散らばり防止。file を足したらこの表を更新。
- 「最新/SSOT」を明示（古いのは履歴と分かる様に）。
