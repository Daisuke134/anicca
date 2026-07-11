# M1: gig を profitable-claude 版(env-u修正済)に一本化 — evidence 2026-07-11

## 根因(確定)
anicca版 gig-cli.sh に `env -u ANTHROPIC_API_KEY` が無い → .openclaw/.env が同keyをleak → headless claude が API-key promptで24hハング → .last-pass 7/8停止・earnings.jsonl 7/7以降0行(4日$0)。PC版 gig-cli.sh line43 は env-u 済だが plist未installで死蔵。

## 実行(own-eyes)
1. PC plist の Label中身が旧`ai.anicca.gig-*`のままだった→`hf-gig-*`に修正(衝突源除去)
2. anicca版 bootout ×3 (gig-auditor/gig-core-healthcheck/gig-proactive、file削除せずreversible)
3. ハング中 anicca-gig-core session を kill
4. PC hf-gig plist を ~/Library/LaunchAgents に設置+bootstrap(plutil -lint OK)
5. `launchctl list | grep gig` = hf-gig-auditor + hf-gig-core-healthcheck のみ(anicca gig消滅)
6. gig-cli.sh --restart → core ALIVE

## 検証(pane実測、45秒後capture)
🟢 API-key prompt hang **なし**(env-u OK)。core が実際にSTARTUP処理中:
「Coconala gig loop定期実行トリガー…cron確認後1パスをbrowser自動化subagentに委任」+ Running shell commands + Forming(thinking)。

## 残(次)
- L1: pass完走後 applied.jsonl/.last-pass 更新 + reality-verifierで実出品/提案をCoconala実確認
- flag: gig core pane に `PreToolUse:Bash hook error node...loader:1458`(non-blocking) → hook環境調査
- M4b: PC gig の tmux SESSION名が anicca-gig-core共有 → hf-gig-core に分離(完全独立)
