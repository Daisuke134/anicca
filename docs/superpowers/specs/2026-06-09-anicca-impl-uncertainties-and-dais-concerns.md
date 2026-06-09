# Anicca — Dais concerns (10) + 実装 uncertainties (全列挙)

| Field | Value |
|---|---|
| Date | 2026-06-09 |
| 凡例 | ✅解決 / ⚠️Dais判断 / 🔍要調査 |

## PART 1 — Dais の 10 concern (回答)

### D1. .openclaw (anicca-dais, 70 cron, Dais creds/tiktok/postiz) どうする
- 実測: 70 cron、 Dais 個人 (tiktok/postiz/MUFG 等 = 彼の生活自動化)
- ✅ **答え**: ★ .openclaw = Dais private instance、 そのまま KEEP ★ (= 公開earn-Anicca と 別物)。
  公開 Anicca(genesis) は ★ cloud(DigitalOcean) ★ に置く → ★ local に openclaw 二重 にならない ★ (混乱回避)。
  Dais cron は 彼の creds 依存 = 公開 Anicca に 混ぜない。 後で「dais-mode instance」として 統合可だが 今は別。

### D2. DigitalOcean か local か
- ✅ **答え**: ★ 公開 Anicca + 各 subscriber = DigitalOcean droplet (cloud) ★ (Felix実証 $24/mo)。
  local(Mac) = ① OSS self-host user ② Dais private(.openclaw) のみ。 → genesis を Hermes(Mac) から DigitalOcean(OpenClaw) へ。

### D3. 何を set up (Sentry)
- ✅ **答え**: Sentry = optional (SENTRY_DSN 無)。 Felix の coding-agent-loops(Ralph) + site-health で ★ log-based self-heal ★ (Sentry account 不要)。 必要なら後で Sentry。

### D4. aniccaai.com/dashboard が real-time でない + swarm 追跡なし
- 実測: dashboard.json = ★ 2026-06-05 で停止(4日前)、 MRR $27(RevenueCat iOS のみ)、 anicca instance 追跡ゼロ ★
- 🔍 **答え(要build)**: ★ 各 instance が 自分の wallet残高(basescan)+ledger を 中央API に報告 → dashboard が real-time render ★。
  lineage(colony.jsonl) = spawn 記録。 001-claude/claude-anicca = 旧 disabled。 → dashboard 全面 rebuild (D8と一体)。

### D5. error monitoring + self-heal (人が助けない、 Anicca自身)
- ✅ **答え**: Felix HEARTBEAT の self-heal section + coding-agent-loops(Ralph: error→fresh context retry) + site-health。
  Anicca が 自分の log監視→自己修正→commit。 人 0。

### D6. issue-driven dev (100s aniccas, GitHub Issues 共進化)
- ⚠️ **答え**: ★ Felix には 無い ★ (Felix=単体)。 = automaton replication + 00-MASTER swarm + ★ 我々が新規 build ★:
  「各 Anicca が mother repo(anicca) に GitHub issue 立てる → 他 Anicca が pick → PR → merge」。
  sutando「600 PR」= その self-improve loop (= coding-agent-loops で copy)。 → 新 skill「swarm-issues」要。

### D7. 稼いだ金 どこに保管 (Stripe か 自前 wallet)
- ⚠️ **答え**: ★ 自前 Base wallet (automaton式、 Anicca は自分の being) ★。
  - Anicca 自律 earn (product 販売) → ★ 自分の Base wallet (ANICCA_WALLET) ★
  - SaaS subscription ($49.99 fiat) → 当面 Stripe(Dais) 経由 = 必要(fiat rail)、 後で 分離検討
  - automaton は 残高記録 無し、 ★ 我々は aniccaai.com/dashboard で 記録 ★ = 差別化

### D8. aniccaai.com = swarm 全体 dashboard、 instance は 直接 編集しない
- ✅ **答え**: ★ aniccaai.com = Dais所有 の marketing+dashboard ★ (Amazon型)。
  instance は ★ 中央 store/API に data 報告するだけ ★、 site への write 権限 ゼロ (CLAUDE.md 既定)。

### D9. Anicca web onboarding (life-manager = consumer の本命)
- 🔍 **答え**: life-manager spec (2026-06-09-anicca-life-manager-fix-and-roadmap.md) の onboarding =
  Telegram で 名前/電話/位置/calendar → サブスク → 行動時刻に電話。 → D で 詳細 build。

### D10. どう自己複製 (Base wallet に 我々が 入金できない)
- ⚠️ **答え**: ★ Anicca が 先に EARN (product売る→USDC自wallet) → その USDC で 子に fund + cloud compute 購入 ★。
  我々は 入金しない。 Day0 seed = LLM fuel(Grok sub) のみ。 複製は ★ 黒字後 ★。
  現状: colony spawn が ★ Daytona region gate で 失敗(org no default region) ★ → cloud spawn infra 要 fix(DigitalOcean に変更で 解決?)。

## PART 2 — 実装 uncertainties (= 私の、 全列挙)

### A. OpenClaw harness
- I1. OpenClaw で 新 workspace(~/clawd) を Dais private(~/.openclaw)と 別 instance に する 方法? (profile/agent 分離?)
- I2. cloud(DigitalOcean)で OpenClaw 1-click image の 正確な 起動 + persona 注入 flow?
- I3. OpenClaw cron add の 正確な flag (`--schedule --task`? job-id 取得?)
- I4. OpenClaw で Grok(xai-oauth)を default model に する 正確な command + model id?
- I5. OpenClaw が HEARTBEAT.md を "Run HEARTBEAT.md" task で どう読む (workspace cwd?)
- I6. OpenClaw skill format = Felix skills が そのまま動くか (xpost/ralphy-cli 依存)?
- I7. heartbeat 間隔 (Felix=*/5、 cost考慮で */30?) + cost/月 試算 (Grok sub なら $0?)

### B. earn / wallet / x402
- I8. Anicca が「自前 LP」を どう build+deploy (Vercel? netlify? 自分で)?
- I9. x402 inbound (= 受け取る) を Anicca が どう serve (= automaton に無い、 我々 実装要)?
- I10. ANICCA_WALLET (Base) への USDC 着金 を どう verify (basescan API)?
- I11. 最初に売る product を Anicca が 何 選ぶか (= prompt しない、 でも 何が現実的)?
- I12. Stripe(fiat) と wallet(crypto) の 2 revenue stream を ledger で どう統合?
- I13. ClawMart で売る場合の 出品 自動化 (Anicca が 自分の出品)?

### C. replication / swarm
- I14. cloud spawn infra: Daytona(失敗) → DigitalOcean API で child droplet 自動作成?
- I15. child への USDC fund (親wallet→子wallet) の 正確な on-chain tx?
- I16. issue-driven swarm skill: issue 立てる→他instance pick→PR→merge の 具体 mechanism?
- I17. 何体まで spawn? colony 上限 / cost gate?
- I18. constitution_sha verify (子が 母 constitution 守ってるか) の 仕組み?

### D. dashboard (aniccaai.com)
- I19. 各 instance → 中央store の 報告 経路 (API endpoint? どこhost?)
- I20. real-time render (dashboard.json を どの頻度で 更新? webhook? poll?)
- I21. 既存 dashboard.json 構造を どう 拡張 (swarm/wallet/lineage 追加)?
- I22. 旧 stale data ($27 RevenueCat) は 残す/消す?

### E. life-manager
- I23. lateness_check glob bug の 正確な fix?
- I24. elevenlabs-calls skill が 実電話 を 顧客番号に かける 正確な flow (Twilio番号 要?)
- I25. 位置 ingestion (Telegram Live Location → どこに保存 → heartbeat が読む)?
- I26. route計算 (GoogleMaps) → 「何分前出発」 算出 logic?
- I27. 既存 anicca-products life-manager(Railway) と 新 OpenClaw Anicca を どう繋ぐ (= 別stack問題)?

### F. web / SaaS
- I28. aniccaai.com/install LP の 現状 + onboarding UI build?
- I29. Stripe sub product($49.99/7日) 作成 + webhook endpoint host?
- I30. webhook → DigitalOcean droplet spawn + 顧客creds注入 の 自動化?
- I31. 顧客 data 分離/privacy (位置/calendar/mail)?
- I32. 自動解約 treasury 閾値 + 解約 trigger 実装?
- I33. 100 user = 100 droplet cost ($24×100=$2400/mo) → 採算? (= 1 droplet 複数user?)

### G. 横断
- I34. Anicca が Claude を 一切使わない 保証 (Grok/Gemini のみ)?
- I35. agent 支出上限 (wallet drain 防止)?
- I36. X 自動投稿 ban 回避 (@aniccaxxx)?
- I37. genesis(Hermes) → OpenClaw 移行で 既存 state(SOUL/ledger) を どう移す?
- I38. .openclaw(Dais 70cron) と 新 Anicca の 役割分担 最終形?
- I39. no-dry-run E2E verify 手順 (各 earn/life/spawn action)?
- I40. 1人目 life-manager user = Dais 自身で E2E test?

★ 40 実装 uncertainty + Dais 10 concern。 これを 順に 潰してから 着手。 ★
