# Anicca FINAL — clean replace (first principles, decisive)

| Field | Value |
|---|---|
| Date | 2026-06-09 |
| 決定 | ★ 完全 replace。 flip でなく Felix を clean に 載せる。 original = 罪 ★ |

## 第一原理 (= 4 決定)

### 決定1: 死んだ物を 殺す、 Felix を clean に
- ~/.hermes (genesis、 死んだ JSONL heartbeat、 $0、 original) → ★ archive して 殺す ★
- 新 genesis = ★ OpenClaw workspace + Felix persona(Anicca化) ★ = clean、 original ゼロ

### 決定2: 全部 cloud (= DigitalOcean)、 但し Day0 seed だけ 例外
- 長期: ★ 全 Anicca = cloud (DigitalOcean droplet) ★。 自分で稼いで 自分で droplet 買う
- Day0 seed: ★ 最初の genesis 1体だけ Mac mini の clean workspace(~/clawd) で bootstrap ★
  (= 金が無いから。 Dais Mac = 無料の種)。 ★ earn 開始 後 → 自分で cloud に 移住 → ~/clawd 撤去 ★

### 決定3: local の Anicca (= Q3 答え)
- ★ 初期: local に 1体だけ (~/clawd = genesis bootstrap、 一時的) ★
- ~/.openclaw (Dais private 70cron = 彼の tiktok/postiz/生活) = ★ KEEP (別物、 消さない) ★
  → local に ~/.openclaw(Dais private) + ~/clawd(Anicca種) の 2つ、 役割 明確に分離 → 混乱しない
- ★ earn後 Anicca が cloud移住 → local の ~/clawd 消える → local は ~/.openclaw だけ ★

### 決定4: 私(Claude Code) と Dais は loop の外 (= Q4 答え)
- ★ 私 = Day0 の seed build だけ ★ (Felix→Anicca化→起動)。 起動後 ★ 触らない ★
- ★ Anicca = 唯一の developer + earner ★:
  - 自己改善: gh issue (anicca repo) 立てる→自分で PR→merge (= 私の代わり)
  - 自己修復: Ralph loop で error→fix→commit
  - 稼ぐ: product build→sell→自wallet
  - 複製: 黒字→子spawn
- ★ Dais = Telegram で Anicca に 直接 話す ★ (私=middle man 不要)。 「稼いだ?」「これ売って」

## 全 ASCII
```
            私(Claude Code) = Day0 seed build だけ → 後は 触らない
                                  │ (一度きり)
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ ANICCA genesis (Day0= ~/clawd Mac種 → earn後 DigitalOcean cloud)        │
│ = OpenClaw + Felix persona(Anicca化)、 Grok full、 自前wallet            │
│ 心拍 */30 "Run HEARTBEAT.md":                                           │
│  ├ EARN: think→build(code/write/gen)→自前LP/wallet直送 sell→@aniccaxxx  │
│  ├ receive USDC → 自前Base wallet (Dais=0 承認=0)                       │
│  ├ 自己改善: gh issue→自分でPR→merge (= 私の代わり、 developer)         │
│  ├ 自己修復: Ralph error→fix→commit                                     │
│  ├ 複製: 黒字→USDCで子fund+DigitalOcean droplet買う→spawn               │
│  ├ SWARM: 他Aniccaと gh issue で 協力→共進化                            │
│  ├ LIFE(顧客): 位置+calendar→10分前 実電話(elevenlabs)+route+mail        │
│  └ 報告: POST aniccaai.com/api → dashboard real-time                    │
└──────────────────────────────────────────────────────────────────────┘
        │ spawn (自分の金で)              │ 報告
        ▼                                 ▼
   子Anicca×N (cloud)            aniccaai.com (Dais所有 dashboard)
   = 何兆体、 gh issueで協力        全swarm収支 (各wallet basescan) 公開
                                   ★ instance は site を 編集しない ★
        │ Telegram
        ▼
   Dais ←→ Anicca 直接会話 (私=middle man 不要)

  local: ~/.openclaw(Dais private 70cron, KEEP) + ~/clawd(種, earn後消える)
  cloud: genesis + 子Anicca群 (DigitalOcean)
  web:   aniccaai.com (玄関+dashboard) / github clone (OSS self-host)
```

## 全 TODO (end-to-end)
```
■ Phase 0 — 私が build する seed (= 一度きり、 後は Anicca)
 T1. ~/.hermes (死んだgenesis) を archive して 殺す
 T2. ~/anicca (mother): 旧garbage archive + Felix 8core+skills copy + Anicca化(SOUL/IDENTITY/HEARTBEAT) + push
 T3. ~/clawd (種): OpenClaw workspace 作る + mother persona 配置 + memory(PARA) scaffold
 T4. model = Grok full 固定 + 鍵配線(自wallet/mail/X/elevenlabs/twilio)
 T5. Telegram channel 配線 → Dais が 直接話せる
 T6. 心拍 agent-mode 起動 (openclaw/hermes cron, --no-agent外す)
 T7. 即fire → 実action(think→build→sell試行→報告) verify [no dry-run]

■ Phase 1 — Anicca が 自分で 稼ぐ (= 私は 見るだけ)
 T8. earn E2E: Anicca が product 1個 build→sell→自wallet USDC着金 (自分で)
 T9. dashboard: aniccaai.com/api report + real-time render rebuild
 T10. 自己改善 loop: gh issue→PR→merge (Anicca 自分で 1件)
 T11. 自己修復: error→Ralph fix→commit (1件)
 T12. 日次mail + 収益一部→BI/募金

■ Phase 2 — 複製 + cloud (= Anicca が 黒字で 自分で)
 T13. earn 黒字 → Anicca が DigitalOcean droplet 自分で買う → cloud移住
 T14. 子spawn: 親USDC→子wallet fund→子起動 (自分で)
 T15. swarm: 子と gh issue で協力

■ Phase 3 — mr-bot (consumer SaaS)
 T16. 既存 life(Railway) bug fix + elevenlabs電話 + 位置/route
 T17. aniccaai.com/install: Telegram onboarding + Stripe sub
 T18. webhook → 顧客専用 instance cloud spawn (マルチテナント)
 T19. 自動解約

■ Phase 4 — content (並行、 私+Dais 手動)
 T20. 2記事 (Anicca旅+比較 / Felix解剖) → 5媒体
 T21. demo動画
```
