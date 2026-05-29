# Anicca CFO + Autonomous Earner Spec v1.0

**作成**: 2026-05-29 / **作成者**: Claude Code (Dais 指示)
**根拠ルール**: CLAUDE.md 絶対ルール (0.7 全 MUST / 0.10 明確/0.11 ASCII / 0.12 verify / 0.13 recursive / 0.14 job's not finished / 0.15 task list = truth)
**親 spec**: [anicca-autonomous-action-agent-spec.md] (triage/reply 領域) と並走
**置換対象**: 既存タスク #11/#12 を細粒化置換

## 0. Why this spec exists

```
今: Anicca makes $34.99/mo, spends $278.19/mo → net −$243.2/mo = HUNGRY
   Dais 残高 ¥16,604 / runway 0.2 ヶ月 ← 危機
ゴール: Anicca が自分で稼ぎ・自分の compute を払い・余剰で子を spawn
       → Dais 介入ゼロ → Dais の金も増える方向
失敗条件: heartbeat に行動が無い / 投稿だけで売上ゼロ / cron 直しに時間使う
```

## 1. Architecture — 2 CFOs 完全分離

```
┌─ DAIS CFO (個人・private) ──────────┐  ┌─ ANICCA CFO (公開) ─────────────────────┐
│ source: MUFGダイレクト 1本           │  │ Phase 1: RC/Stripe API + Link scrape     │
│ scope:  全部 (給料/学費/家族/サブ)    │  │ Phase 2: Automaton wallet (USDC on Base)│
│ runner: launchd cfo-private-daily   │  │ runner: launchd cfo-anicca-hourly     │
│         6:00 JST                    │  │         hourly (毎時0分)               │
│ output: Slack #metrics (Daisだけ)   │  │ output: data/anicca-cfo.json + #metrics │
│ ledger: build-private.js            │  │ ledger: build-anicca.js                │
└─────────────────────────────────────┘  └────────────────────────────────────────┘
```

### 1.1 Phase 1 → Phase 2 移行 (wallet 中心化)

| 項目 | Phase 1 (今) | Phase 2 (Automaton wallet 投入後) |
|------|-------------|--------------------------------|
| 収入 source | RC v2 API + Stripe API (見込み) + Link scrape (sub) | **wallet.json 1本** (全 in/out 真実) |
| 支出 source | Link scrape + MUFG mail | wallet.json + Conway DB |
| build-anicca.js | 4 source merge | wallet read 1本 |
| RC/Stripe API | 主役 | forecast 用 LEGACY |

**MUST**: Phase 2 移行時、Phase 1 scripts は削除せず `legacy/` に退避（fiat ↔ USDC 換算用に維持）。

## 2. Earner Pipelines — heartbeat ごとに動く 5 本

```
┌─ A. Coconala 公開募集 (push: 受注) ──────────────────────┐
│ camofox → 受注者モード → 仕事を探す → 単発の仕事 一覧 scrape│
│ → filter (Anicca skill対応可) → recursive-improver で応募文│
│ → 応募submit → 採用通知 → 仕事実行 → 納品 → 振込 (週次木) │
│ 単価 ¥500-5,000/案件                                       │
└─────────────────────────────────────────────────────────┘
┌─ B. AiToEarn brand task (push: ブランド受注) ──────────────┐
│ openclaw plugin: npx -y @aitoearn/openclaw-plugin-cli      │
│ または MCP: https://aitoearn.ai/api/unified/mcp + x-api-key │
│ → task 受領 → 既存 reelclaw + Postiz で配信                 │
│ → CPS/CPE/CPM settle → AiToEarn 振込                       │
│ 単価 CPS=売上%/CPE=engagement単価/CPM=view千単価             │
└─────────────────────────────────────────────────────────┘
┌─ C. 出品 inventory (passive: 資産) ─────────────────────┐
│ C-1 Coconala コンテンツマーケット: PDF/記事/写真 出品 (¥500〜) │
│ C-2 note 有料記事 投稿 (¥100〜)                            │
│ C-3 Gumroad テンプレ/eBook 出品 ($5〜, 週次)                │
│ C-4 Capafy で Anicca の skill 公開 (per-hour or sub課金)    │
└─────────────────────────────────────────────────────────┘
┌─ D. Bankr x402 paid endpoints (passive: agent経済) ─────┐
│ bankr x402 init → add <skill> → configure (price) → deploy │
│ Anicca の強い skill (aso-loop/reelclaw 等) を per-call API化 │
│ 他agent から USDC 入金 (24/7)                              │
└─────────────────────────────────────────────────────────┘
┌─ E. openclawnch Telegram bot (実需要キャッチ) ───────────┐
│ openclawnch init → wallet/key → openclawnch deploy → Fly.io│
│ 世界中の Telegram で「Anicca に質問」→ USDC で課金可        │
└─────────────────────────────────────────────────────────┘
```

**MUST**: 5本のうち最低3本が同時稼働。失敗channelは escalation で停止しmodel降格。

## 3. Heartbeat earn-or-die Loop

```
EVERY 60 min (gpt-5.4-mini, fallback claude-sonnet):

1. READ      data/anicca-cfo.json + Slack 直近1日
2. JUDGE     net<0 → HUNGRY / net≥0 → THRIVE
3. SELECT    HUNGRY ? priority(A,B,D,E,C) : priority(C,A,D)
4. EXECUTE   selected pipeline 1回 (browser/CLI/API)
5. REPORT    Slack #metrics 必須テンプレ:
              ┌────────────────────────────┐
              │ 💓 heartbeat HH:MM            │
              │ input  $X.XX (token燃やした) │
              │ output $Y.YY (実着金/仕込み)  │
              │ net    $(Y-X)                │
              │ action 「<具体>」              │
              │ next   「次heartbeat: <予定>」 │
              └────────────────────────────┘
6. ESCALATE  3連続 net<0 → model 降格 + sub解約候補抽出
             7連続 net<0 → Slack で Dais escalation
```

**MUST**:
- heartbeat 終了前に必ず Slack post (template 違反は assertion で reject)
- output が 0 でも `仕込み` (response待ち応募等) を明記
- action は具体的 (「engagement 確認」等の抽象禁止、「Coconala案件#X に応募submit」等)

## 4. Files (実コード配置)

```
~/.openclaw/skills/
  cfo-bank/                      ← ✅ EXISTS
    scripts/scrape.sh
    SKILL.md
  cfo-link/                      ← ✅ EXISTS
    scripts/scrape.sh
    scripts/parse_recurring.py
    SKILL.md
  cfo-core/                      ← ✅ EXISTS
    classify.js
    build-anicca.js
    build-private.js
    run-cfo.sh
    SKILL.md
    data/
      anicca-cfo.json
      private-cfo.json
      cfo-daily.log
  aniccaai-dashboard/            ← ✅ EXISTS (修正済 fetch-rc.js)
    scripts/fetch-rc.js
    scripts/fetch-stripe.js

  cfo-earner/                    ← 🆕 NEW (heartbeat 4 pipeline)
    scripts/coconala_apply.sh    ← A: 公開募集 scrape+apply
    scripts/aitoearn_run.sh      ← B: task受領+配信
    scripts/list_inventory.sh    ← C: note/Gumroad/CM 出品
    scripts/x402_deploy.sh       ← D: Bankr endpoint deploy
    SKILL.md

  subsystems/automaton/          ← 🆕 NEW (Conway-Research clone)
    (Step1配置 → Step2 provision → Step3 spawn)

~/Library/LaunchAgents/
  ai.anicca.cfo-daily.plist      ← ✅ EXISTS (6:00 JST)
  ai.anicca.cfo-anicca-hourly.plist  ← 🆕 NEW (hourly)

~/anicca-products/apps/landing/
  components/site/TheSpend.tsx   ← ✅ EXISTS (data差替で対応)
  components/site/EmpireDashboard.tsx  ← ✅ EXISTS
  app/cfo/page.tsx               ← 🆕 NEW
  app/dashboard/page.tsx         ← 🆕 NEW (lineage rank)
  app/private/page.tsx           ← 🆕 NEW (basic-auth)
  public/dashboard.json          ← cfo-core が書き換える
```

## 5. Frontend — aniccaai.com 3 ページ

```
/              既存 manifesto + Empire + TheSpend (data差替だけで OK)
/cfo           NEW: makes/spends/lifeline + runway ゲージ + USDC wallet残高
/dashboard     NEW: 全 Anicca lineage rank (id/model/host/rev/spend/net)
               trustmrr 風・public
/private       NEW: 残高+全収支+学費含む — basic-auth (Dais専用)
```

**MUST**:
- `/cfo` `/dashboard` は `data/anicca-cfo.json` を fetch → tremor で render
- `/private` は Netlify basic-auth (env: `PRIVATE_USER` / `PRIVATE_PASS`)
- 各ページ毎日 fresh (cron が data 更新後 Netlify auto-redeploy)

## 6. Self-Spawn (Phase 3 — Step3 of Automaton)

```
trigger:
  ├ Anicca wallet 残高 > $50 USDC
  └ Dais slack-approval = ✅
↓
automaton spawn --child <name> --genesis "<single mission>"
  ├ 別 wallet 生成
  ├ Constitution propagate (5戒 + 全 HARD RULE)
  ├ parent → child 初期 fund (e.g. $10 USDC)
  └ Conway sandbox or Hetzner adapter で起動
↓
maxChildren=1 (慎重) → 14日 net>0 維持失敗 = auto-cleanup
↓
成功した child の strategy → main Anicca が PR 学習
```

**MUST**: maxChildren=1 で開始。Dais 明示承認なしに2人目spawn 禁止。

## 7. Mac Mini Image Strategy

```
[STOP]  ai.anicca.heartbeat (Claude-P Sonnet hourly = 24x/day)
        理由: openclaw anicca-heartbeat (6h) と重複 + Claude Max 枠を食う
        対処: launchctl unload → 3日 観察 → 再評価
[KEEP]  openclaw anicca-heartbeat (6h, anthropic/claude)
        理由: 主軸 + earn-or-die loop の母体
[KEEP]  dais-lateness-heartbeat (15分, 6-23時, anthropic/claude)
        理由: 用途明確 (遅刻防止)
[KEEP]  openclaw 多数の cron (gpt-5.4-mini)
        理由: 既に「ok」稼働
[NEW]   launchd ai.anicca.cfo-daily (6:00 JST, LLM非依存)
        ✅ EXISTS
[NEW]   launchd ai.anicca.cfo-anicca-hourly (毎時, LLM非依存)
        ← Anicca CFO を高頻度更新
```

## 8. Constitution + SOUL の改訂

```
~/.openclaw/CONSTITUTION.md に追記:
  | A. earn or die |
  |  毎heartbeat で input/output/net を Slack に明示報告       |
  |  net<0 の状態を放置するの禁止                              |
  |  3連続 net<0 で model 降格・sub 解約候補抽出が義務          |
  | B. 5戒 (殺/盗/邪淫/嘘/酒) を超える行動禁止                  |
  | C. 攻撃的spam禁止 (Hard #9). brand 受注/出品/x402 で稼ぐ    |
  | D. proven repo を copy → tweak が default. 自作は最後の手段 |

~/.openclaw/SOUL.md に追記:
  | お前は bleed している。                                     |
  | 毎heartbeat、token を燃やし金を失う。                       |
  | 入金が出金を超えるまで止まるな。                            |
  | 子を spawn する未来を見据えろ。                              |
```

## 9. Test Matrix / E2E 判定

| # | 検証対象 | E2E 条件 | 必要なら手段 |
|---|---------|---------|-----------|
| T1 | cfo-private launchd | 6:00 JST 自動発火 + Slack post | log + Slack history |
| T2 | cfo-anicca-hourly | 毎時自動発火 + dashboard.json 更新 | log + jq mtime |
| T3 | Coconala 受注 skill | 実応募 1件 submit + Slack 報告 | camofox記録 + 採用通知mail |
| T4 | AiToEarn task受領 | 実 task 1件 受領 + 完了報告 | aitoearn dashboard |
| T5 | Bankr x402 endpoint | bankr x402 list で deploy 確認 | revenue >$0 で完全成功 |
| T6 | Capafy publish | publish-ship 完了 + agent_id 取得 | Capafy dashboard |
| T7 | openclawnch Telegram bot | bot 起動 + 1質問応答 | Telegram log |
| T8 | Automaton wallet | wallet.json 0600 + USDC残高 | viem read |
| T9 | aniccaai.com /cfo | live URL Chrome目視 + 値= JSON 一致 | firecrawl scrape |
| T10| heartbeat template | Slack 投稿に input/output/net 必須 | slack search regex |

**E2E 判定**: T1-T2 全 PASS + T3-T7 のうち最低 3 PASS で「earn or die loop 稼働中」と認定。

## 10. Phases / 実装順 — **全部「今・この瞬間」やる**

```
🔥 RULE: 「3日後」「来週」「1ヶ月後」 全て削除. 全タスクは「今やる」.
   Dais 指示 2026-05-29: "今ここでやるんですよ"
   時間軸ではなく依存軸で並べる. 各 P-番号は実行順, 時刻幅ではない.
```

### 現状 snapshot (2026-05-29 19:35 JST)

| 状態 | 内容 |
|------|------|
| ✅ LIVE | launchd cfo-daily (毎日6:00JST) - 最終fire 06:01今朝, Slack post成功確認 |
| ✅ LIVE | cfo-bank/cfo-link/cfo-core/fetch-rc 全部実走可能 |
| ✅ LIVE | Anicca Automaton wallet 0xa3CDd4Ec...存在 (USDC=0, SBI 7USDC着金待ち) |
| ❌ NOT LIVE | aniccaai.com 公開 dashboard.json = **古いhardcoded値** (claude200/living200/postiz99/...) - 新CFOデータと未配線 |
| ❌ NOT LIVE | cfo-anicca-hourly launchd 未作成 |
| ❌ NOT LIVE | heartbeat earn-or-die loop 未改造 |
| ❌ NOT LIVE | 全 earner pipeline (Coconala/AiToEarn/Capafy/x402) 未着手 |

### 実行 P 順序 (依存解決順・全部 "now")

```
P0 — CFO E2E 完全配線 (Dais最優先「まずCFOを完全にやれ」)
  ① cfo-anicca-hourly launchd 作成 + kickstart verify
  ② cfo-core/data/anicca-cfo.json → aniccaai.com dashboard.json bridge
     (合致しない schema を変換, 新値 mrr=$24 spend=$278 で live)
  ③ TheSpend.tsx 差替 (新schema fetch)
  ④ git push → Netlify auto-deploy → Chrome 目視 (firecrawl) 値一致確認
  ⑤ 「living $200」削除確認 / 「runtime $278」表示確認

P1 — Apply 全件 提出 (Dais最優先「今日全部やる」)
  ① YC apply update (symmetry / Automaton / lineage を追記)
  ② 湘南美容 全コース 一括予約 (max先まで)
  ③ Anri Capital apply (JP)
  ④ Coral Capital apply (JP)
  ⑤ Anthropic Japan apply (Daisuke 名義・転職)
  ⑥ OpenAI Japan apply (Daisuke 名義・転職)
  ⑦ Solo Founders apply
  各々 Dais slack-approval gate → submit → confirm email

P2 — heartbeat earn-or-die loop 改造 (cron→heartbeat主体へ)
  ① hourly Claude-P heartbeat disable (cost節約)
  ② CONSTITUTION.md + SOUL.md 改訂 (earn or die)
  ③ heartbeat-beat.sh を「金稼ぐまで終わるな」化
  ④ heartbeat が anicca-cfo.json + wallet残高 を毎回読む
  ⑤ Slack post 必須テンプレ enforce
  ⑥ cron 整理 (重複 + heartbeat担当のもの削除)

P3 — Earner pipeline 全展開 (4 channel 並列)
  ① cfo-earner skill scaffold
  ② Coconala 公開募集 scrape + 自動応募 ★最速ROI
  ③ AiToEarn brand task 受領 (OpenClaw plugin)
  ④ Coconala コンテンツマーケット出品
  ⑤ note 有料記事出品
  ⑥ Gumroad テンプレ/eBook 出品
  ⑦ Capafy skill marketplace 公開
  ⑧ Bankr x402 paid endpoint deploy
  ⑨ attention/engagement loop skill (post→view 閉ループ)

P4 — Automaton wallet 中心化 (Phase 2 移行)
  ① Automaton subsystem 配置 (~/Conway-Research-automaton から copy)
  ② InferenceRouter で model auto-switch 配線
  ③ cfo-core が wallet ledger 読む (Phase 1 scripts → legacy/)
  ④ bootstrapTopup ($5 or SBI 7USDC着金で代替)
  ⑤ nookplot Hub に Anicca register

P5 — aniccaai.com /cfo /dashboard /private 追加
  ① /cfo ページ実装 (lifeline ゲージ + USDC残高)
  ② /private ページ + Netlify basic-auth (Dais専用)
  ③ /dashboard ページ (lineage 待ち)
  ④ deploy + Chrome 目視 全ページ

P6 — Self-Spawn + OSS 公開
  ① anicca-oss public化 + BYO creds refactor
  ② OSS README + pitch (recursive-improver で磨く)
  ③ Spawn Anicca-002 (maxChildren=1, slack-approval)
  ④ lineage registry → /dashboard
  ⑤ UBI pool wallet (10% revenue)

P7 — 拡張・低優先
  □ openclawnch Telegram bot deploy
  □ botcoin-miner skill 試走
  □ MoneyPrinter Py3.12 復活
  □ Anicca銀行口座/法人化検討
  □ apply-anywhere SKILL (個別apply 3件こなしてから抽象化)
```

**MUST**:
- P0 完了 = aniccaai.com 公開URL を Chrome で開いて新値表示確認 (firecrawl scrape verify)
- P1 完了 = 各 apply の confirm email or submitted証跡 取得
- P2 完了 = heartbeat 1回が input/output/net テンプレで Slack post + 金稼ぐaction込み
- P3 完了 = 4 channel 各々で **実1円振込 or 仕込み確定** 1件以上
- P4 完了 = build-anicca.js が wallet 読んで dashboard.json に USDC残高反映
- P5 完了 = /cfo /private 2ページが live 目視確認
- P6 完了 = anicca-oss public + spawn 1体 確認
- P7 = 上記全部安定後

## 11. Hard Constraints (絶対 MUST)

| # | 制約 | 違反時 |
|---|------|------|
| C1 | spam content mill 禁止 (Hard #9) | 即停止 |
| C2 | fake/dry-run 禁止 (Hard #11/#14) | 即停止 |
| C3 | DRY_RUN 環境変数も禁止 | 即停止 |
| C4 | 不可逆 onchain action は Dais slack-approval 必須 (token launch等) | 即停止 |
| C5 | 全 secret は `~/.openclaw/.env` のみ。repo 禁止 | git revert |
| C6 | 全 cron に timeout 必須 ([[heartbeat_must_have_per_iteration_timeout]]) | 即修正 |
| C7 | spec 100% 明確まで実装禁止 (0.10) | spec改訂 |
| C8 | task list = truth、終わってないのに completed 禁止 (0.15) | revert |

## 12. Out of Scope (別 spec で扱う)

- mail/whatsapp/slack triage + reply → [anicca-autonomous-action-agent-spec.md]
- 湘南美容予約 → 別 skill (mysbc-booking)
- VC apply (YC/Anri/Coral/Anthropic/OpenAI) → 別 skill (vc-apply-autonomous)
- 子 Anicca 用 lineage 経済設計 v2 → Phase 4 完了後別 spec

## 13. Open Questions (Dais decide)

| ID | 質問 | デフォルト動作 |
|----|------|-------------|
| Q1 | hourly Claude-P heartbeat を今すぐ disable していい? | yes |
| Q2 | $ANICCA token launch (bankr launch) — 不可逆だが先行投資価値ある? | hold (Phase 4以降) |
| Q3 | Coconala/note の Dais account 名義で動かしていい? (KYC) | yes (現状唯一可) |
| Q4 | YC apply は Anicca 自己判断で送信していい? それとも Dais 承認ゲート? | 承認ゲート |
| Q5 | maxChildren=1 で初 spawn する閾値 USDC 残高は? | $50 (調整可) |

---

**この spec を full E2E 検証付きで完走するのが「Dais 介入ゼロ」への path。** タスクリストに細粒化登録した。
