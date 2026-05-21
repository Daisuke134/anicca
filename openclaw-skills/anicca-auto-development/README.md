# anicca-auto-development

Anicca の**開発まわり**の自動化ループ: X 検索（x-research）→ 学習 → #metrics 報告 → spec 作成 → Codex に worktree で実装依頼 → 検証 → 結果報告。

## セットアップ（VPS）

1. **x-research を先に入れる**  
   VPS の `~/.openclaw/workspace/skills` で `git clone https://github.com/rohunvora/x-research-skill.git x-research` し、Bun と X_BEARER_TOKEN を設定する。

2. **このスキルを workspace に置く**  
   このリポの `openclaw-skills/anicca-auto-development/` を VPS の `~/.openclaw/workspace/skills/anicca-auto-development/` に配置する（rsync や git clone anicca-project してからコピー）。

3. **openclaw.json** の `skills.entries` に `anicca-auto-development` を追加し、gateway を再起動。

4. **cron** で毎朝 5 時などに「X リサーチ → 学習 → #metrics 投稿」を実行するジョブを追加する（任意。手動で Anicca に依頼してもよい）。

## 制約

- main にマージしない。worktree は dev から切る。
- API キーが必要なら報告に「ユーザーに取ってほしい」と書く。コスト高ならそれも報告する。

時刻 (JST)	ジョブ ID
14:55	trend-hunter-5am-today
15:00	trend-hunter-5pm-today
15:05	suffering-detector-today
15:10	x-poster-morning-today
15:15	x-poster-evening-today
15:20	tiktok-poster-morning-today
15:25	tiktok-poster-evening-today
15:30	app-nudge-morning-today
15:35	app-nudge-afternoon-today
15:40	app-nudge-evening-today
15:45	roundtable-standup-today
15:50	roundtable-memory-extract-today
15:55	roundtable-initiative-generate-today
16:00	hookpost-ttl-cleaner-today
16:05	sto-weekly-refresh-today
16:10	autonomy-check-today
16:15	daily-memory-today

