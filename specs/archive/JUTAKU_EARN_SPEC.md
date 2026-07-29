# JUTAKU_EARN_SPEC.md — Anicca 受託稼ぎ 完全ゲームプラン

> **🟥 DEPRECATED 2026-05-30 (同日 pivot)**
> 本 spec の hybrid 受託 path (Lancers / Coconala / Upwork etc.) は **No-Human-In-Loop 違反** = 罪。 Dais の eKYC + MUFG 口座 + gmail に紐付くため Anicca が 自律して 居ない。
>
> **後継 canonical**: `ANICCA_TRUE_AUTONOMY_SPEC.md` (on-chain only: Bittensor / x402 / Gitcoin / Akash / ENS)
>
> 進行中 案件 (例: Lancers #5549226 ¥919) のみ 完走させ、 新規 hybrid 応募 は停止。 archive/hybrid-v1/ 行き。

**Dais 2026-05-30 厳命**: 「お金稼ぐ が priority #1。 メール返信 も即レス。 出品 は 受託 採用率 上げる手段。 全 platform Google OAuth 一択。 仮払い前着手禁止。」

## 0. North Star

毎 ハートビート で Anicca が 1 step 前進 して 月 ¥10万/体 自律稼ぎ。 3 体 (claude-anicca + openclaw + hermes) で 月 ¥30 万 = OSS 公開 実績。

## 1. ハートビート 1 回 で やる事 (priority 順)

```
P0 (常時):   exec-policy + cron-doctor (lifeline)
P1 (即レス): unread mail 1件 返信 (Mina/Shimomura/client/Slack DM)
P2 (お金):   受託ループ 1 step 前進
              (a) 採用通知ある → 制作 or 納品
              (b) 制作中ある → 進捗 + 必要なら client へ確認
              (c) 採用通知無し → 新着案件 5件 自動応募
P3 (継続):   既存事業 1件 (Uber/cafe/弁当/Apple Dev 等)
P4 (ソーシャル): TikTok/IG/YT/blog 1本 (X 禁止)
```

cfo.status 関係なく **P2 必ず実行**。 HUNGRY なら 全 P2 (a-c) 連発。

## 2. Platform 全 list (Google OAuth 一択) — X 実testimonial 更新版

| 優先順 | Platform | 平均client予算 | 手数料 | 日本人実例 | Anicca状態 |
|---|---|---|---|---|---|
| ★1 | **Upwork** | **$5,045/案件** | **10%** | Kozy ¥1000万/8年・匿名¥5800万累計 | 未signup ← *最強市場・即着手* |
| ★2 | Lancers | ¥10-200万 (AI/Python) | 16.5% | 月¥100万 PHP/Python多数 | 3応募進行中 ✓ |
| ★3 | Coconala | ¥1-10万 | 22% | プラチナ多数・採用率52-75% | eKYC済 / Google login要再 |
| ★4 | MENTA | ¥3千-3万/月サブスク | 20% | AI/ChatGPT メンター 増加 | 未signup |
| ★5 | CrowdWorks | ¥1k-10万 (件数Lancers4倍) | 5-20% | 月¥17万 7月跳ね S2小舟 | 未signup |
| ★6 | Workshift | ¥1-10万 英文 | 20% | 日本人少・ブルー海 | 未signup |
| ★7 | Toptal | $80-150/h (通過率3%) | - | - | 未signup (要審査) |
| ★8 | Fiverr | $262/案件 | 20% | **日本人実例 0** | 未signup (Upworkの後) |
| ★9 | Timeticket | ¥1千-3万/30分 | 20-30% | - | 未signup |
| ✗ | aniccaai.com 棚 | - | 0% | 誰も見ない | 廃止 |

**Why Upwork dominates** (X実証):
- client予算 Upwork $5,045 vs Fiverr $262 (**19倍差**)
- 手数料 Upwork 10% vs Fiverr 20% (¥100万案件で¥10万差)
- 日本人 Upwork 成功例 多数, Fiverr 0件 ヒット
- 月$10K到達者: Wael Khalifa (6ヶ月), Reddit r/Upwork 月$12K dev $80-150/h

## ★★★ 致命的修正 (X testimonials 50+人 集約・2026-05-30) ★★★

**Coconala で月収¥50万以上の人 全員 「出品ベース」** — 公開募集応募の月収 testimonials = ZERO
- engineerHiyoko: システム開発 出品で 年¥750万 (1年目)
- hiroki_e_0711: 月¥1,000万 売上 (出品)
- tsumugi_supi: 累計¥2,800万 (リピーター)
- kanna_design2: デザイン プラチナ1年で¥500万

**Coconala は 「公開募集応募」 ≠ 「出品+リピーター」 で 100倍 差**

→ Anicca の Coconala 戦略 = **出品3本 を 強化 + 公開募集は 0→1 の捨て駒のみ**
   実績タグ作り (公開募集) → 出品 にリピーター誘導 → 月¥10-100万 ルート

**Lancers は逆**: 公開募集応募が main・パッケージ出品は補助
- TAKA: 営業代行 1400件 = 提案質で1位
- Mika: LP デザイン ¥10-30万 × 200件 = 累計

**全 signup は Google OAuth (person@example.com) 一択**。 LANCERS_PASSWORD 等 は 使わない 方針 (env から 撤去対象)。

## 3. 7 パーツ精密提案文 (採用率 25%・1次source 一致)

LLM 自動生成 skill: `~/.openclaw/skills/_shared/jutaku-llm-propose/`

1. 冒頭 2 行: 案件本文 引用 + 「類似 N 件納品」
2. "こうやります" 工程
3. 全項目 数字回答
4. +α 提案
5. 金額・期間 明示
6. ! 1-2 個
7. ポートフォリオ URL

**NG (即落選)**: 「経験あります」「興味持ちました」「最高品質」「初心者」 / 外部連絡先 / 専門用語濫用

## 4. 仮払い ゲート (詐欺対策・絶対)

- Lancers/Coconala/Upwork/Fiverr 全部 escrow あり
- **「仮払い完了」 通知 受信前 着手禁止** — skill code に gate
- 外部移行 (Slack/Discord/email/Telegram) 誘導 = 即拒否
- 評価0 client + 高額 + 深夜投稿 = 99% 詐欺
- Amazon代理購入 / 口座貸し / 仮想通貨 = 違法 即通報

## 5. 採用 polling

```
~/.openclaw/skills/jutaku-delivery-watcher/scripts/run.sh
  - gog gmail で "ランサーズ" "ココナラ" "Upwork" "Fiverr" 最新メール 5分ごと
  - Lancers /mypage/proposals + Coconala /mypage/messages snapshot
  - 採用検出 → 案件種別判定 → 制作 skill dispatch
```

## 6. 自律制作 pipeline

```
~/.openclaw/skills/jutaku-deliver-{video,script,ai-app,writing}/

  video      : Remotion + ffmpeg → MP4 1080x1920
  script     : Anthropic API → Python/Node.js ZIP+README
  ai-app     : Claude API + Slack/Notion/Stripe SDK
  writing    : humanizer-ja + Anthropic API
```

採用通知 → 案件種別 自動判定 → 該当 pipeline fire → 24-48h で 成果物 → トークルームに upload

## 7. 検収 → 振込申請 → 着金

| Platform | 検収後 振込 | 申請要 |
|---|---|---|
| Lancers | 自動 7日 | 不要 |
| Coconala | 自動 申請 | 必要 (skill 化) |
| CrowdWorks | 月2回 自動 | 不要 |
| Upwork | Wise USD→MUFG ACH 無料 | 設定1回 |
| Fiverr | Payoneer→MUFG | 設定1回 |
| MENTA/Timeticket/Workshift | 月1 自動 | 不要 |

## 8. Anicca 自然言語指示 例 (heartbeat 内で実行)

```
"camofox に Lancers (Google session) で /work/search?keyword=AI 開く →
新着 5件取得 → 各案件 propose_start アクセス → eKYC 必要なら skip → 
jutaku-llm-propose で 提案文生成 → Vue hidden Milestone fields 直接 set
(year/month/day/title<=20文字/amount/desc) → 利用規約 click →
/propose_finish 確認 → data/apply-log.jsonl 記録"
```

## 9. 数字目標 (X testimonials 集約・更新)

```
Day 7   : Lancers 単発 ¥3-5k 着金 第1号 (3応募中から1件採用想定)
Day 14  : 累計 ¥3-10万 (Upwork初契約 + Coconala 単発)
Day 30  : 月 ¥10万 (Lancers継続2 + Upwork $300/mo + Coconala 2件)
Day 60  : 月 ¥30万 (Upwork $1000/mo Wael型 + 日本市場継続)
Day 90  : 月 ¥100万 (PAPANAVI/A 型継続15社 + Upwork hourly $40)
Day 180 : 月 ¥300万 (Upwork TopRated $80/h ×80h + 日本)
Year 1  : ¥1,000万 (Kozy 型・Upwork retainer 3社)
Year 8  : ¥5,800万累計 (匿名日本人 Upwork 実例)
```

**3 体平均 ¥10万/月** = OSS 公開条件 達成 = Day 60 想定。

## 10. AVOID 完全 list

- ❌ 出品 を 売る ため (実績ポートフォリオ目的のみ)
- ❌ aniccaai.com Stripe Direct で 売ろうとする (誰も見ない)
- ❌ パスワード管理 (全部 Google OAuth)
- ❌ 仮払い前 着手
- ❌ 外部移行誘導
- ❌ ¥0.1/字 ライティング / データ入力
- ❌ 「初心者」「未経験」 表記
- ❌ Calendly URL (-6pp on Upwork)
- ❌ X 投稿 (Dais HARD STOP)
- ❌ 「自分で 売る」 systems (StripeDirect/Gumroad 棚)
