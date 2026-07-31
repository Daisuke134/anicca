# 発注: spec §10 順8a — LM-33a panel 認証（TG /panel → 単回 opaque token → session）

正本: /Users/anicca/anicca-project/docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md
必読節: §9.9（panel = 鏡）、§10.1 U5（採用設計: /panel → 5分・単回・128bit+ opaque token URL → HttpOnly/Secure/SameSite session 交換後 token 無し URL へ redirect。token は hash 保存 + chat_id/expires_at/used_at 束縛。/lm?tg= と長寿命 JWT は廃止）。
役割: Sol = build+execute+verify+spec 更新+commit+push。質問 = bash ~/.agents/skills/agmsg/scripts/send.sh lm-p0 sol-order8a fable-main '<msg>'。
対象: anicca-products、worktree .worktrees/lm-p0-order8a（base = 最新 origin/dev）、branch feature/lm33a-panel-auth → PR to dev。GHA 追加可。

## 仕様
1. TG /panel コマンド → opaque token(crypto.randomBytes 32) 生成、sha256 hash + uid + expires_at(5min) + used_at を新テーブル lm_panel_tokens に保存（additive migration、SQL は PR に含め適用は Fable E2E 時） → 単回 URL を TG 返信。
2. GET /panel?t=<token>: hash 照合 + 未使用 + 期限内 → used_at 焼き → session cookie(HttpOnly/Secure/SameSite=Lax、有効24h、値は別の random、lm_panel_sessions か signed cookie どちらか — 実装が単純な方を選び PR に理由1行) → /panel へ redirect。
3. /panel (session 必須): 順8b が来るまで placeholder ページ（「Anicca Life Manager」+ uid 表示のみ）。
4. 旧 /lm?tg= の panel 用途があれば剥がす（onboarding 用途は残す — 実読で区別せよ）。
5. negative tests: token 再利用→403 / 期限切れ→403 / 改竄→403 / session 無し /panel→401。

## 検証
npm test 全 green + negative 4本 green（実出力）。staging は Railway BLOCKED-on-Dais のため skip 可（PR に明記）。

## 禁止
prod deploy / prod webhook 変更 / 長寿命 JWT / secret 出力。

DONE 報告 agmsg: test 実出力 + PR URL。
