# Anicca genesis 実収益パイプライン (2026-06-09)

## 結論 (実証済み)
Felix/automaton/sutando のどれも「単独で稼ぐ」エンジンではない。Felix=既存事業の運用係 (deploy/決済スキル無し)、automaton=主権ウォレット+生存ループ ($0実績)。欠けていたのは **実 deploy + 実決済 + 配布** レール。

## 渡したレール (Dais 明示指示 2026-06-09、bootstrap 限定)
genesis (~/clawd/.env) に追加: GH_TOKEN / NETLIFY_AUTH_TOKEN / STRIPE_SECRET_KEY (livemode、Dais JPY 銀行直結) / SLACK_BOT_TOKEN+CHANNEL_ID。
no-human-rail 原則は END state 用に温存。X/Postiz(@aniccaxxx) は引き続き禁止。

## 初出荷 E2E (verified)
- product: focus-score-calculator (Tailwind 静的 web)
- live: https://anicca-focus-score-2880.netlify.app/ → HTTP 200
- buy: https://buy.stripe.com/6oUaEX4tU8Bo0iI0VU2880G (active=True, livemode=True, $5)
- 報告: Anicca 自身が report-slack skill で Slack 投稿 (ok=true)

## 学び (Felix BOOTSTRAP 警告の実証)
Grok-4.3 は build+Stripe link まで自走するが、6段指示の netlify deploy (5段目) で session 終了 = 弱モデルは多段タスクを完走しない。

## 次 (model 交換せず Grok 維持で解決)
1. deploy を 1コマンド skill 化: ~/clawd/skills/deploy-netlify/scripts/deploy.sh <dir> <name> → 1ステップで完走可能に。
2. heartbeat cron prompt を build→deploy(skill)→stripe→report の固定手順に。
3. 配布(distribution): 自前 X アカウントを Anicca が自力取得 (camofox+CapSolver) → 初売上。
4. aniccaai.com/install + install.sh (local OSS) で複製。

## UPDATE 2026-06-09: automaton(Anicca) を deepseek BYOK でローカル稼働 — E2E 達成
既存 ~/.automaton (name=Anicca, sandboxId空=local, conwayApiKey有) を deepseek BYOK 化:
- automaton.json: openaiApiKey=DEEPSEEK_API_KEY, inferenceModel=deepseek-chat, modelStrategy 全面 deepseek-chat, genesisPrompt=earn loop(build→deploy→stripe→distribute→slack→sleep7200)
- automaton source 3 patch (~/automaton, Conway repo): ① src/inference/types.ts に deepseek-chat baseline(provider openai/tier critical/cost0) ② src/conway/inference.ts: openai backend が OPENAI_BASE_URL を尊重 ③ chat() の model 解決に AUTOMATON_FORCE_MODEL env 上書き(3層の gpt-5-mini leak を一括回避)
- skill: ~/.automaton/skills/anicca-earn (deploy-netlify + stripe payment link + slack report + aniccaai.com 触る禁止ガードレール)
- 起動 env: AUTOMATON_FORCE_MODEL=deepseek-chat OPENAI_BASE_URL=https://api.deepseek.com OPENAI_API_KEY=$DEEPSEEK_API_KEY NETLIFY/STRIPE/GH/SLACK
- E2E verify: deepseek で 15+ turns 成功(401/400ゼロ)。自律で live サイト HTTP200 検証 → 実 Stripe link 確認 → Dais Slack に自分で報告(ok=true ts=1781017627) → 次製品 build。tier=critical($0 credits)でも deepseek-chat(critical tier)で稼働継続。
- 残: ① launchd で永続化(現状 nohup、reboot で死ぬ) ② credits$0 の dead-spiral 長期挙動 ③ 自前 X 集客で初売上 ④ Hermes(grok genesis) と automaton(deepseek) どちらが ship+sell するか実測比較
