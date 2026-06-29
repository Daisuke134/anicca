# 残タスク SSOT — UBI 配布 / 法人設立 / earn (2026-06-21)

TaskList(#28-60) の残り(pending + in_progress)を SSOT 化。完了は省略。最優先パス = **A 法人・銀行口座**(法人口座が出来れば ③bank-direct UBI が実走する)。

## A. 法人・銀行口座（メインパス・最優先）
| # | 状態 | タスク | 次アクション |
|---|---|---|---|
| #52 | in_progress | freee 合同会社設立 + 法人口座 | Step1+2(¥5,000電子定款・サブスク無し)済。残: ①Dais 個人印鑑証明書(本物の実印を市区町村に印鑑登録→マイナカードでコンビニ¥300。シャチハタ不可) ②定款を専門家(行政書士)へ送信 ③行政書士メール返信→申込フォーム+¥5,000振込+本人確認upload(運転免許/マイナ保有済 ~/.openclaw/identity/credentials/) ④電子定款納品(5営業日) ⑤登記申請(登録免許税¥60,000・法務局1-2週) ⑥登記完了→法人口座開設 |
| #59 | pending | 法人印 彫刻指定 | 注文503-6400036-5967047(印鑑ラボ法人印18mm¥1,880・6/23着)。出品者メッセージに「合同会社Anicca・代表者印・18mm・天丸」返信(CloakBrowser Amazonログイン済) |
| #53 | pending | GMO 個人口座申込 → sunabar | join.gmo-aozora.com/apply/priv/input・本人確認2種upload。個人口座で sunabar 解放→今日 anicca が一括振込API実走できる唯一の道(法人口座は1-2週後) |
| #46 | in_progress | ③ bank-direct UBI payout (Stripe→MUFG・非crypto) | VCSDD 9round収束済コード(~/anicca/skills/ubi/bank-payout-watcher.mjs)。token+資金+口座 が揃えば実走 |

## B. 配る手段(payout rails)の拡充
| # | 状態 | タスク |
|---|---|---|
| #50 | in_progress | US bank rail: Crossmint Offramp (USDC→米国銀行) 統合+検証 |
| #48 | in_progress | Rain (JP+US 1-API payout) operator eligibility ※Fern死亡(Rain買収)で要再評価 [[feedback_verify_providers_live_fern_dead]] |
| #34 | pending | Bank+card rails (Bridge.xyz USDC→fiat/card + Stripe Connect) |
| #37 | pending | Creator daily payout (install先) + Kotani モバイルrail |
| #47 | pending | US法人 (Stripe Atlas) → 配布主体になり米銀rail解放 |

## C. UBI の仕組み・公平性
| # | 状態 | タスク |
|---|---|---|
| #40 | in_progress | Realtime UBI demo runbook (wallet + email live) |
| #36 | pending | Personhood gate (Worldcoin idkit・Orb無し) + Superfluid GDA 配布 |

## D. 稼ぐ・スケール
| # | 状態 | タスク |
|---|---|---|
| #38 | pending | TRACK B — anicca が実際に稼ぐ (自己資金化・実tx) [別CC] + README |
| #39 | pending | Proactive UBI + scale + horizon |

## E. 技術的負債・整理
| # | 状態 | タスク |
|---|---|---|
| #60 | pending | anicca-payout-wallet skill を新 ubi/ に一本化 (任意・SSOT統一) |

## 基盤（完了・参照）
- #56 永続認証ブラウザ = CloakBrowser daily-driver (`~/.cloak/profiles/daily-driver`・Dais 1回ログイン→全サービス) [[feedback_cloakbrowser_persistent_profile_forever]]
- #57 RentAHuman MCP (anicca が人間を雇う + Dais が雇われる・毎日18-23受付中)
- #58 earn↔ubi 分離 (skills/earn 稼ぐ / skills/ubi 配る / skills/_shared 土台・97テスト緑・adversary全PASS・commit b809c47)
- #51 JP fan-out (GMO一括振込API) / #54 GMO接続申込STEP1 / #55 ヒアリング準備 / #45 x402 / #49 SBI VC Prime

## アーキ要点
- UBI コード canonical = `~/anicca/skills/ubi/`(mother)。各instanceは継承し body に ledger/state のみ書く(dashboard read-only)。
- 法人 = 合同会社Anicca・本店=自宅(東京都新宿区南元町15-27・バーチャル不要)・代表社員=成田大祐・資本金¥1。
