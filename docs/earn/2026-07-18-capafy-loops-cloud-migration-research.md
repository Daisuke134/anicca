# Capafy two-loop cloud 移行アーキテクチャ調査（2026-07-18）

目的: 現在 Mac Mini（launchd + CloakBrowser CDP + headless `claude -p`）で走る 2 loop を cloud/pod に移す。
方式: deep-research harness（103 agents / 375 web fetch / 3-vote adversarial verify）。research only、実装は未着手。
出典正本は末尾 §sources。**cost の hard number は research が open question として残した — cite 可能な数字のみ記載、残りは unverified 明記（捏造しない）**。

## 0. 一言結論

**HYBRID split。断層は1本だけ**: 「純 compute/API」は全て datacenter cloud、「social 投稿（実ログイン browser）」だけが residential/mobile-IP node に残る。この 2 半分を authenticated job queue で繋ぐ。

理由: datacenter IP（AWS/GCP/Railway/Fly/OVH/DO）は IP reputation が悪く「range 単位で」flag され、**ログイン済み IG/X account が即 ban される**（conf: high、aimultiple.com）。だが LLM・API・ffmpeg/Whisper は IP reputation を要求しない → cloud で問題ない。

## 1. 推奨リファレンス構成

```
┌─ DATACENTER CLOUD（Fly.io / Railway）──────────────────────────┐
│  brain     = `claude -p` headless を Docker 化（node:22-slim）  │
│              ★書き換え不要 — claude -p は Agent SDK の CLI 版、  │
│              Linux container/CI で --output-format json 動作     │
│  build loop= Capafy API + LLM（OpenRouter/Anthropic）全部ここ    │
│  video-gen = ffmpeg/Whisper/TTS を serverless burst             │
│              （Modal or Fly Machine、IP 無関係なので cloud OK）  │
│  scheduler = Fly.io Cron Manager（ephemeral Machine/job）        │
│              or Railway cron（daily の最簡）→ launchd 代替       │
│  state     = append-only JSONL on Fly/Railway volume            │
│              + Postgres/S3 で durability + backup                │
│  secrets   = Fly.io encrypted vault（API server は encrypt のみ、│
│              boot 時に env/[[files]] 注入。key/cookie をここへ） │
└───────────────────────┬─────────────────────────────────────────┘
                        │ authenticated job queue
                        │ （cloud が mp4+caption+link を作り
                        │   「post this」job を渡す）
┌───────────────────────▼── RESIDENTIAL / 4G-MOBILE IP ──────────┐
│  poster ONLY = 実ログイン browser で IG Reels / X 投稿          │
│                reach/metrics 読み戻し → ledger append           │
│  ★ここだけ datacenter 不可。realize 方法は §3 の3択            │
└─────────────────────────────────────────────────────────────────┘
```

## 2. named service picks（cite 付き）

| 層 | 推奨 | 出典 |
|---|---|---|
| scheduler | **Fly.io Cron Manager**（batteries-included / most production-hardened、schedules.json で job ごと ephemeral Machine 起動→破棄）or Railway cron（最簡 daily） | fly.io/docs/blueprints/task-scheduling, docs.railway.com/guides/cron-workers-queues |
| brain compute | **`claude -p` を Docker 化そのまま**（書き換え不要。将来 Python/TS Claude Agent SDK へは interface 変更のみ、engine 同一） | code.claude.com/docs/en/headless, agent-sdk/overview |
| video-gen | **Modal or Fly Machine の serverless burst**（scale-to-zero、IP 無関係で cloud 可） | buildmvpfast.com serverless GPU 比較 |
| posting（residential IP）| §3 の3択（self-host mini-node / mobile-proxy / anti-detect cloud） | aimultiple, pxm2.io, multilogin |
| state | JSONL on Fly/Railway volume + Postgres/S3 backup | railway.com/deploy/postgres-daily-backups |
| secrets | Fly.io encrypted vault（or Infisical/Railway） | fly.io/docs/apps/secrets, infisical.com |

**brain 移行の要点（conf: high）**: `claude -p` は「Claude Agent SDK を CLI で露出したもの」で、公式 docs が「your process, your infrastructure / session state = JSONL on your filesystem」「CLI を -p + --output-format json でプログラム実行」と明記。**今の engine をそのまま container 化できる**。書き換えは要らない。
- caveat: Agent SDK は `setting_sources` を明示しないと CLAUDE.md/skills を auto-load しない。claude.ai サブスク auth は SDK-powered product では不可（API key 必須）だが、`claude -p` は subscription を使える。
- 棄却された誤情報: 「remote-control は OAuth login のみで API key 不可」は 0-3 で refute（headless は API key で動く）。

## 3. posting 層の3択（IP survival が全て）

**account 生存率は IP type が支配（conf: high、pxm2.io ほか）**:
| IP type | IG account 生存率 |
|---|---|
| 4G/5G mobile proxy | **~95%+** |
| residential | 60-70% |
| datacenter | **20% 未満（使うな）** |

account 密度上限（conf: medium）: 1 mobile proxy = IG **1-3 account**（port/account 専用、warmed で ~3、最大 5、安全 3）。今の規模（1 account）は余裕。

| 案 | 内容 | trade-off |
|---|---|---|
| **A. self-host mini-node（推奨・最安）** | 家に residential-IP の mini-PC/Mac を1台常駐させ CloakBrowser を載せる。cloud brain が job queue で叩く | 追加 $0（既存 Mac 流用可）。IP は home residential。単一障害点、電源/回線依存 |
| B. mobile-proxy + 自前 browser | 4G/LTE proxy を借りて cloud or mini-node の browser に付ける | 生存率最高（95%+）。proxy 月額（GB 課金、下記 unverified） |
| C. anti-detect browser cloud | Browserbase/Kameleo/Multilogin 等に residential proxy 付き | 運用最楽。月額高め、IG survivability は provider 差（要検証） |

現実解: **今の Mac をそのまま「posting node」に残し、brain/video/API/scheduler だけ cloud に上げる**のが最小移行 + 最安。IP 問題を一切触らずに済む。

## 4. 段階移行パス（launchd+CloakBrowser+Mac から）

1. **brain を container 化**（`claude -p` を Docker、launchd の cron logic を Fly/Railway schedule に写す）
2. **build loop（API半分）を cloud へ**（Capafy API + LLM。IP 無関係、即上がる）
3. **video-gen を cloud burst 化**（Modal/Fly Machine）
4. **state を volume + Postgres/S3 backup に**
5. **secrets を vault に**（file から key/cookie を移す）
6. **posting だけ Mac に残す**（= 案 A）。cloud→Mac を job queue で接続
7. 将来: posting も mobile-proxy 化して Mac 依存を切る（案 B）or Agent SDK 移行

## 5. 設計すべき failure mode

| mode | 対策 |
|---|---|
| IP ban | posting を datacenter に絶対置かない（§3）。生存率で IP 選ぶ |
| session-cookie 失効 | 自動 re-login flow + ban-signal 検知（open question、未実装） |
| fingerprint drift | anti-detect profile 固定 or mobile emulation |
| scheduler drift | Fly Cron Manager の ephemeral Machine で job 独立、self-heal |
| cost blowup | video-gen を scale-to-zero、brain を ephemeral（常駐させない）or 監視 |

## 6. cost（★ research が hard number を open question として残した）

**cite できる範囲のみ**:
- brain/scheduler: Fly Cron Manager は「job ごと ephemeral Machine 起動→破棄」= daily cadence なら Machine 稼働は分単位。Fly Machine の従量課金（正確な $ は unverified、要 pricing 確認）
- video-gen: Modal/Fly-GPU は scale-to-zero（呼んだ時だけ課金）
- LLM: 既存 OpenRouter/Anthropic（別課金、現状維持）
- posting: 案 A なら **$0 追加**（Mac 流用）。案 B の mobile-proxy は GB 課金（**具体額 unverified**）

**⚠ 正直な gap**: 「Fly Machine 常駐 vs ephemeral + Modal video burst + residential/mobile proxy を足した具体的月額表」は research が open question として明示的に未解決。低volume（1-2 loop、数post/日）の合計月額は **案 A で $5-20/月レンジ（Fly/Railway の最小 plan + LLM 別）と推測されるが、proxy を足す案 B/C は未確定**。次の実測 task: 各 provider の pricing page を叩いて確定表を作る。

## 7. open questions（research が明示的に残した、次に詰める）
1. 具体的月額 cost table（各 provider pricing 実測）
2. posting delivery の最終選択（案 A/B/C）
3. Capafy PUBLISH と X 投稿を full API 化して residential surface を IG Reels だけに縮小できるか
4. cloud→residential handoff の具体配線（authenticated queue vs Temporal/Inngest vs pull poller）
5. IG/X cookie/session 失効 + fingerprint drift の自動 self-heal（re-login/ban 検知）

## sources
- IP/proxy: aimultiple.com/instagram-proxies, pxm2.io（4g-proxy-2026）, multilogin, proxies.sx, coronium.io
- brain: code.claude.com/docs/en/headless, agent-sdk/overview, platform.claude.com migration-guide, anthropic.com/engineering/effective-harnesses-for-long-running-agents, github.com/beevelop/docker-claude
- scheduler/state/secrets: fly.io/docs（task-scheduling, apps/secrets）, docs.railway.com（cron-workers-queues）, railway.com/deploy/postgres-daily-backups, infisical.com
- compute: buildmvpfast.com（serverless GPU 2026）, starmorph.com（AI agent deployment 比較）, mux.com, promptquorum.com（whisper 比較）
