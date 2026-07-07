# Dais-Funded 自律トレードループ — 設計Spec (SSOT)

- **Date**: 2026-07-07
- **Status**: DESIGN (実装未着手 / brainstorming → 本specがsource of truth)
- **Owner**: claude-p (human-funded loop) / 立案 = メインClaude
- **開発方式**: GLVS。本specはGoal段の成果物。Build/Verifyは本spec承認後にVCSDD実コマンドで回す

> ⚠️ このspecは **Daisの実際の日本円(貯金)** を自律運用する。溶かしていい金ではない。
> 全設計の第一原則は「勝つまで大金を賭けない」を**構造で強制**すること。

---

## 0. 開発環境

| 項目 | 値 |
|---|---|
| products repo path | `~/anicca-project/` |
| 現ブランチ | `feature/clip-rewards`(本spec docのみ。実装時は専用worktreeを切る) |
| 実装時のworktree | `.worktrees/dais-trading-loop/`(branch `feature/dais-trading-loop`)を切ってから着手 |
| ループ本体(身体) | `~/.anicca-dais/`(新規 `ANICCA_HOME`。既存colony bodyには一切触れない) |
| 再利用元 | `~/anicca/skills/earn/`(3エンジン/ledger/guard)、`~/anicca/skills/self/`(self-fix/colony-status) |
| fork元 | freqtrade(GPL-3.0、private内部利用) |
| venue | bitbank(ccxt-native、standing-transfer on-ramp適合) |

---

## 1. 目的とゴール(検証可能な完了条件)

**目的**: Daisの実円を、円安から逃がしつつ増やす。初回セットアップ以降は**人間ゼロ**で回す。

**背景資金(Daisの申告)**:
| 口座 | 額 | 役割 |
|---|---|---|
| MUFG | 約35万円 | 日常の生活費・支払い(触らない、原則) |
| ゆうちょ | 約90万円 | 貯金 → ここから**少しずつ**投資に回す |

**投入方針(Daisの言葉)**: 「$10 → $100 → 勝ち続けたら増額」。少額から始め、実証されたら増やす。

**done条件(Milestoneごと、§9で詳細)**:
- **M1完了** = 実金$100がE2Eで届き、ledgerに正しく記録され、monitoringが生きている(トレードはまだ)
- **M2完了** = Track2算法loopが実金$10から稼働し、ledgerにrealized profit>0が**複数回**載る(実証ラダー開始)
- **M3完了** = 実証を受けてTrack1(安全ベース)へ90万の大半を移し、円安からの継続escapeが自律で回る

---

## 2. 正直な前提(なぜ設計が保守的か) — 引用付き

BP=答え。判断には引用を付ける(§CLAUDE.md)。この設計を保守的にする根拠:

| 出典 | 核心の引用 | 含意 |
|---|---|---|
| freqtrade公式FAQ (freqtrade.io/en/stable/faq/) | "12 trades is just not enough to say anything… it will always be a gamble" | ツール自体にedgeはない |
| stash86 / Bot Academy (botacademy.ddns.net、freqtrade公式が"Community showcase"でリンク) | "3年使ってzero long-term profitable strategy。バックテストは常に綺麗、最長8ヶ月で崩れる。100 botのうち生き残るのは約2つ" | retail algoの長期黒字は稀。edgeは**リサーチ規律**から来る |
| Reuters 2026-12-04 (Stephen Jen) | キャリートレードは"ticking time bomb"、1998-10にUSDJPYが1日で134→120 | 小口レバFXは**元本超の自爆**、Daisのゴールの真逆 |
| 日本FSA (2011) | "maximum allowable leverage reduced from 50 times to 25 times" | 規制当局自身が小口FXレバを繰り返し下げている=危険の証左 |
| Investopedia | S&P500 1928–2026 real annualized ≈ 6.81% | 「弱い円から逃げて増やす」の最良の自律表現は**米株指数DCA** |

**結論**: 算法トレード(Track2)は「edgeが実証されるまで小口に封じ込める」。資金の大半はTrack1(低破綻リスクの安全ベース)で円安から逃がす。この二層構造が本設計の背骨。

---

## 3. アーキテクチャ全体

```
                     Dais の 実円 (ゆうちょ / MUFG)
                              │
              ┌───────────────┴─── Layer 1: オンランプ ───────────┐
              │  初回まとまった額 = 手動振込 1回 (2FA 1回)         │
              │  以後の継続 = 定額自動送金/自動振込 (窓口登録1回→ゼロ)│
              └───────────────┬───────────────────────────────────┘
                              ▼ (規制されたJP取引所 = bitbank の本人名義口座)
              ┌─────────── Layer 2: トレード (API, 2FA不要, 完全自律) ───────────┐
              │                                                                  │
              │  Track 1: 安全ベース (資金の大半, M3で本格化)                     │
              │    → 円安から逃げて着実に増やす (米株DCA or USD保有)              │
              │                                                                  │
              │  Track 2: 実験スライス (小口, M2から)                             │
              │    → freqtrade fork on bitbank, crypto spot 算法                  │
              │    → $10→$100→実証ゲート→段階増額                                │
              │    → kill-switch / spend-cap / 累積赤字即停止                     │
              └──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              身体 = ~/.anicca-dais (ANICCA_FUNDING=human, fail-closed分離)
              ledger = ~/.anicca-dais/skills/earn/state/earn-ledger.jsonl (既存format)
              self-heal = self-fix.sh dais-loop "<blocker>" (無改変で動く)
```

**核心の分離**: Layer1(銀行)とLayer2(取引所API)は完全に切り離す。銀行側の自動化限界(2FA)はLayer2の自律性に影響しない。

---

## 4. オンランプ設計 (Layer 1) — 引用付き

**確定した事実(調査1)**: 個人の銀行口座から振込をAPIで自動実行する手段は存在しない(MUFG/ゆうちょとも更新系APIは法人契約者限定、個人はIBログイン+2FA必須)。**2FAを迂回する手段(クレデンシャル保持+OTP代行等)は法規リスク領域につき本設計で採用しない。**

**唯一の正規・ゼロタッチ・ルート**:

| ステップ | 内容 | 人間タッチ |
|---|---|---|
| S0-a | bitbankで口座開設・KYC完了 → 専用入金口座(GMOあおぞら/住信SBIの本人名義)取得 | 1回(初期セットアップ) |
| S0-b | ゆうちょ貯金窓口で「自動振込」を申込。送金先=bitbank専用口座、頻度=毎週or毎月、金額=固定額 | 1回(窓口来店) |
| S0-c | 初回まとまった額の移動は、標準の窓口/IB振込を**1回だけ**手動実行 | 1回 |
| S1〜 | 銀行の自動送金バッチ → bitbank専用口座へ振込入金 → 残高反映(翌営業日ラグ) | **ゼロ** |
| S1〜 | ループがbitbank APIで入金履歴をポーリングし着金確認 | ゼロ(自動) |

- 出典(ゆうちょ): "貯金窓口でお申込みください"(jp-bank.japanpost.jp/kojin/sokin/jido/kj_sk_jd_jdfurikomi.html)
- 出典(MUFG定額自動送金): "ご契約後は、お振り込みのためにお手続きいただく必要はありません"(bk.mufg.jp/tsukau/furikomi/teigakujidosoukin/index.html)
- **AML注意**: 本人名義→本人名義KYC済み口座の標準振込は制限対象外の見込み。初回は少額でテストしてから本番額に移す(不正検知は生きたシステムのため)。

**設計含意**: ループは「変動額を今すぐ送れ」を銀行に対して発行**しない**(2FA必須で不可能)。設計は常に「固定額が定期で流れ込む」前提。トレードロジックは取引所内残高の範囲でのみ動く。

---

## 5. トレード設計 (Layer 2)

### 5.1 Track 2 — 実験スライス(M2から、本specの実装主対象)

| 項目 | 決定 | 根拠 |
|---|---|---|
| venue | **bitbank** | ccxt-native + 公式`python-bitbankcc` → freqtradeがほぼ無改変。native `fetchOHLCV`。standing-transfer on-rampと適合(即時入金不要) |
| bot base | **freqtrade fork(丸ごとcopy、混ぜない)** | 52k★、Hyperopt(Bayesian)+FreqAI(適応的ML再学習)=「自己改善」が最強。headless運用が本業設計。dry-run内蔵。Protections plugin(StoplossGuard/MaxDrawdown/CooldownPeriod)標準 |
| 取引対象 | crypto spot(JPYペア)、**レバレッジなし** | レバは§2の自爆リスク。spot現物のみ |
| 戦略規律 | walk-forward検証 / hyperoptパラメータは少数 / 新規dry-run期間を真のout-of-sampleとして扱う | edgeはツールでなく規律から来る(§2 stash86) |
| GMOコイン | 代替として保持(将来ccxtアダプタを書く判断をした時) | 即時入金・最安手数料の利点はあるがccxt非対応=自作コスト |

**重要な現実(調査3)**: freqtradeはbitbankを「公式テスト済み」listには載せていない("we cannot guarantee they will work")。→ 実装前に **ccxtで直接bitbankへ最小実弾スパイク**(注文発行+残高/取引履歴のround-trip確認)を行い、freqtradeのexchange解決層に配線する前に動作を確定する。

### 5.2 Track 1 — 安全ベース(M3で本格化、instrumentは後で決定)

- 役割: 資金の大半で円安から逃げ、着実に増やす。
- 候補(M3で決定): ①米株指数DCA(VOO/VTI via IBKR/IBSJ、$0最低額、JPY入金→USD資産購入で自動両替) ②USD/USDC保有(金利4%キャリー)。
- 調査4順位: 米株DCA > USD保有 > crypto算法 > レバFX。
- **本specのM1/M2ではTrack1は未実装**。M2で配管とedgeが実証されてから、instrumentを別途決定しM3で構築(別系統=colony crypto基盤は流用不可)。
- 未検証: Alpacaの日本居住者受け入れ(一次情報未確認)。IBKR/IBSJが安全な既定候補。

---

## 6. マネーセーフティ(交渉不可・self-improveで変更不可)

既存colony基盤に組込み済みの安全装置を**そのまま継承**する(調査5):

| 装置 | 既存実装 | 挙動 |
|---|---|---|
| 1パス上限 | `MAX_PASS_SPEND`(既定$2) | 全戦略合計で1パス≤約$6に固定。残高に関係なく上限一定 |
| 1取引上限 | `MAX_BET_SIZE` | directional取引の1回額を制限 |
| kill-switch | `touch KILL` | 各戦略実行前にチェック、存在すれば即停止 |
| 累積赤字halt | `_shared/lib/earn-guard.mjs` | lifetime `net_usdc`が負に転じた瞬間fail-closed(skill単位AND wallet単位) |
| genome分離 | `genome.mjs` | self-improveが触れる knob から `MAX_BET_SIZE`/`MAX_PASS_SPEND` は**明示的に除外**(安全上限は自己改善で緩められない) |

**追加(本spec固有)**: 実証ゲート付き資金ラダー。
```
$10 →[ledgerにrealized profit>0が載る]→ $100 →[同]→ $1,000 →[同]→ 段階増額
      ↑ このゲートを通らない限り資金はTrack1(安全ベース)に留まる
```
ラダーの昇格は`isProfitable()`(net_usdc>0 AND external===true AND tx confirmed)を満たす行が閾値回数出た時のみ。人間承認は不要だが、**負けたらラダーは自動で登らない**。

---

## 7. identity / wallet 分離(Daisの金を混ぜない)

| 項目 | 決定 |
|---|---|
| 身体dir | `~/.anicca-dais`(新規)。`~/.anicca` `~/.blockrun` `~/.anicca-founder`には触れない |
| wallet | `~/.anicca-dais/.automaton/wallet.json` + `solana.json` を新規生成 |
| env | launchd plistで `ANICCA_HOME=~/.anicca-dais` `ANICCA_INSTANCE=dais-loop` `ANICCA_FUNDING=human` |
| 分離保証 | `resolve-identity.mjs`は`ANICCA_HOME`ゲートでfail-closed。foreign homeは常に`null`を返す=他instanceのkeyを絶対に引かない(調査5で確認) |
| citizen gate | `is-self-funded.mjs`で`isSelfFunded()===false`を**設計上assert**(fuel=human)。claude-pと同じ扱い |
| 既存バグ修正 | `founder-loop.plist`が`ANICCA_FUNDING=self`と誤設定 → 新plistでは`human`を正しく設定(調査5指摘) |

---

## 8. 再利用インベントリ(車輪の再発明をしない)

| コンポーネント | 再利用/新規 | 詳細 |
|---|---|---|
| ledger記録 | **再利用(無改変)** | `earn/lib/ledger.mjs`+`record.mjs`+`earn-guard.mjs`。`ANICCA_HOME`を向けるだけで`~/.anicca-dais/.../earn-ledger.jsonl`に自動記録 |
| self-heal | **再利用(無改変)** | `self-fix.sh dais-loop "<blocker>"` がそのまま動く |
| identity解決 | **再利用(無改変)** | `resolve-identity.mjs`(ANICCA_HOMEゲート) |
| money-safety | **再利用** | `earn-guard.mjs`/genome分離パターン |
| SSOT可視化 | **小改修** | `colony-status.sh`/`telemetry-collect.sh`に4番目のブロック追加(同じhelper、新wallet address) |
| bot本体 | **新規(fork)** | freqtrade fork + bitbank配線 + 戦略 |
| bitbank連携 | **新規(最小)** | ccxt `bitbank` を使用。必要なら薄いadapter(GMO採用時のみ`pybotters`のGMO実装を参照) |
| 着金ポーラ | **新規(小)** | bitbank入金履歴API polling → 残高反映確認 |
| Track1(安全ベース) | **新規(M3)** | IBKR/USD経路。colony crypto基盤は流用不可 |

---

## 9. Milestones & ゲート

| M | 名前 | やること | 完了ゲート(検証可能) |
|---|---|---|---|
| **M1** | 配管検証 | 身体`~/.anicca-dais`生成、identity分離assert、bitbank口座+standing-transfer登録、実金$100を1回投入、着金ポーラ+ledger+monitoring稼働。**トレードは載せない** | 実金$100がbitbankに着金しAPIで確認でき、ledgerに記録され、`colony-status.sh`に4番目のinstanceが出る。identity分離テストがforeign-home=null を返す |
| **M2** | 算法ON | freqtrade fork配線、ccxt-bitbank実弾スパイク合格、戦略をdry-runで検証後に実金$10で起動、実証ラダー開始 | ledgerに`isProfitable()===true`の行が複数回(閾値)載る。kill-switch/spend-cap/累積赤字haltが実際に発火することをテストで確認 |
| **M3** | 本格escape | Track1 instrument決定(米株DCA vs USD保有)、90万の大半を移す、継続escape自律化 | Track1が自律で定期買付/保有し、円安escapeがE2Eで回る |

各Mは独立にVCSDD(init→spec→spec-review→tdd→impl→adversary→harden→converge)で回す。

---

## 10. 検証アーキテクチャ(VCSDDへ接続)

| 要件 | 検証方法(fresh evidence) |
|---|---|
| identity分離 | foreign `ANICCA_HOME`で`resolveEvmPrivateKey()`が`null`を返すユニットテスト。Daisのwalletが他instance keyを引かないこと |
| オンランプ着金 | 実金の入金がbitbank入金履歴APIに現れ、残高に反映されることを実観測(dry不可) |
| ledger正確性 | 実トレード後、`earn-ledger.jsonl`の行が実際のtx/statusと一致(MD5/tx confirmまで) |
| money-safety発火 | KILLファイル/上限超過/累積赤字を人工的に起こし、実際に停止することを確認 |
| edge実証 | dry-run out-of-sample期間 → 実金$10ラダー。realized profitはtx confirmedのみカウント(盛らない) |
| E2E | メインが実ブラウザ/実API/実walletで自己完結確認。コンパイル成功だけでは完了としない |

adversary = fresh-context Opus 4.8(§CLAUDE.md model分業)。

---

## 11. スコープ外(YAGNI / 明示的除外)

- ❌ レバレッジFX / レバレッジcrypto(§2の自爆リスク)
- ❌ M3前に90万の大半を動かすこと(実証されるまで大金を賭けない)
- ❌ 銀行2FAの迂回・自動振込のAPI化(法規リスク、技術的にも不可)
- ❌ 即時入金(クイック入金)の自動化(構造上2FA必須、standing-transferで代替)
- ❌ Track2の資金をon-chainへ出すこと(Dais選択=JP取引所native。規制取引所内にとどめる)
- ❌ 複数venueの混在(NEVER-COMBINE。まずbitbankで勝者を1つ検証)
- ❌ Track1とTrack2を1つのbotに混ぜること(別系統)

---

## 12. リスクと未検証事項(正直に)

| 項目 | 状態 |
|---|---|
| bitbankのSBI買収(2026-06-28発表、$289M) | 統合過渡期。運用体制に不確実性 → M1で口座・API・出金が実際に動くことを実弾確認 |
| freqtrade×bitbank非公式サポート | 実装前にccxt実弾スパイク必須(§5.1) |
| **日本の税** | 暗号資産のトレード益=雑所得(総合課税、最大約55%)。米株=申告分離。**自律トレードでも課税・確定申告義務は残る**。M2稼働時に取引履歴をtax用にexportする仕組みを検討(本specのM2で扱う、Daisに要周知) |
| Alpacaの日本居住者受け入れ | 一次情報未確認 → Track1はIBKR/IBSJを既定に |
| AML不正検知 | 初回は少額テスト → 本番額(§4) |
| algo edgeの不在 | §2の通り。二層構造+実証ラダーで封じ込め済み |

---

## 13. 次のステップ

1. Daisが本specをレビュー・承認
2. writing-plans skillで実装計画を作成(GLVSのGoal→Plan)
3. worktree `feature/dais-trading-loop`を切る
4. M1からVCSDD実コマンドで着手(`vcsdd-init` → ...)
5. **実装はDais承認まで一切しない**(brainstorming HARD GATE + Dais明示指示)
