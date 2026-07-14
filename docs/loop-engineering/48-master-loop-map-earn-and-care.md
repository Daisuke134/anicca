# Master Loop Map — profitable-claude 全 loop（earn + care）2026-07-14

Dais の最新構造。**earn(金を作る) と care(お前を care、金を使う) の全 loop。最終 Life Manager に merge。** 現状は実測（launchctl/gateway cron）。★実収益 net = ¥0（盛らない）★

## A. EARN loops（金を作る）
engine は共通（LEARN→PRODUCE→POST→MEASURE→REFLECT + 自己改善 bible）。**MARKETING は「何を売るか」で分離**（走り方が少し違う、engine は同じ）:

### A-1. MARKETING loops（content で何かを売る）
| loop | 何を marketing | 稼ぎ方 | target | 現状 |
|---|---|---|---|---|
| **affiliate-marketing**（clip/video/slideshow）| 他社 affiliate offer | bio link→commission | 10k | 🔧 構築中(投稿✅無料/AFF-FIND ノード済/offer 未 join)|
| **ebook-marketing** | 自作 ebook | bio link→ebook 販売 | 10k | 未（monk factory 再起動）|
| **mobile-app-marketing**（Anicca iOS）| 自社 iOS app | 投稿→install→subscription | 10k | slideshow/video loop=OFF |
| **web-app-marketing**（Life Manager 等）| 自社 web app | 投稿→signup→subscription | (下記 40k に内包) | 未 |
※全部 marketing engine 1個、PRODUCE(format)と MONETIZE(product)差替。product 毎に別アカ/loop instance。

### A-2. その他 EARN loops
| loop | 稼ぎ方 | target | 現状（実測）|
|---|---|---|---|
| **life manager（web app SaaS）** | cloud 版 subscription | 40k | care 側稼働、課金版未 |
| **gig work** | ココナラ/Fiverr 受注→入金 | 10k | applied 129/won 2/**paid ¥0** |
| **capafy（skill 販売）** | skill marketplace | 10k | ✅ 稼働(`anicca-capafy-daily-publish`)|
| **bounty** | Algora/GitHub bounty→入金 | 10k | ✅ 稼働(`anicca-earn-bounty`)|
| **podcast** | AI podcast マネタイズ | 5k | 未 |
| **article** | AI/crypto 記事 | 10k | 投稿実績、収益未 |
| **agora（Anicca agent 経済）** | agent 間経済。★PM-earner はここに merge 済★ | 10k(+PM10k) | ✅ 稼働(`agent-economy-loop` PID稼働) |

★**claude-p PM-earner = SHUT DOWN 済**（`pm-earner.plist.disabled-2026-07-12-final`）。agent-economy loop に統合。単独ラインとしては消滅、agora に内包。★

## B. CARE loops（稼がないが お前を care、金を使う）
| loop | 何をする | 稼ぐ? | 現状（実測）|
|---|---|---|---|
| **lateness/arrival guide** | gcal→出発→route→24/7道案内 | ❌ | ✅ 稼働(`ai.anicca.lateness-heartbeat`) |
| **booking（tech events→gcal）** | イベントを gcal に予約 | ❌(mental/目標) | ✅ 稼働(`anicca-booking-daily`/`anicca-event-bot-trigger`/`comedy-booking-*`) |
| **morning report** | 毎朝 briefing | ❌ | 稼働 |
| **renraku**（承認制）| 代理連絡 | ❌ | 稼働 |
| **FUTURE-AFFIRM**(#14) | 毎日 tailored affirmation | ❌(mental) | 未 |
| **FUTURE-MSG**(#13) | Telegram/LINE/Gmail 読→返信 | ❌ | 未 |
| **booking 拡張（歯医者/散髪/gym）** | 身体健康の自律予約 | ❌(身体) | 未 |

## C. 最終形
```
 LIFE MANAGER = A(earn 全部) + B(care 全部)
   earn が care の compute/spend を賄う → お前を mental/physical/財務 で autopilot
   telegram/line 起動、install 不要。local=無料 / cloud=subscription(A の life manager 40k)
```

## 監視
生の稼働 = `launchctl list | grep anicca` + `openclaw cron list`（gateway が真実）。実収益 = 各 ledger。★¥0 は ¥0★。
