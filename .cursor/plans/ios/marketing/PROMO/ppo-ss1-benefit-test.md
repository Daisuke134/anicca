## 目的

App Store Product Page Optimization（PPO）で、**スクショ1枚目の“ベネフィット訴求”差し替え**がCVRを改善するかを検証する。

対象クリエイティブ仕様: `.cursor/plans/PROMO/ss1-hero-spec.md`

---

## テスト設計（最終）

### 仮説

- **検索結果サムネで読める一言ベネフィット**にすることで、プロダクトページ遷移後の意思決定が速まり、**CVR（Impressions → App Units）が上がる**。

### 変更点（Treatmentで変えるもの）

- **変更するのはスクリーンショット1枚目のみ**
  - JP: 「夜更かしが、やめられる。」
  - EN: 「Finally stop staying up late.」
- **2枚目以降は現状維持**

### 計測ローカリゼーション

- **日本語（JP）**
- **英語（EN）**

### テスト設定（App Store Connect入力値）

- **参照名（固定）**: `ppo_2024-12-14_JPEN_ss1_benefit`
- **トリートメント数**: **1**
- **トラフィック割合**: **100%**
- **期待改善率（Expected Improvement）**: **30%**

#### 補足（重要）

- App Store Connectの「トラフィック割合 100%」は、**“テストに参加する流入の割合”**。
- トリートメントが1つの場合、テスト参加流入の中で **Baseline と Treatment が概ね 50/50** に割り振られる想定。
- 「Expected Improvement」はサンプルサイズ見積もり用の入力で、**勝敗判定ルールそのものではない**。

---

## 成功指標（Primary）

- **Conversion Rate（Impressions → App Units）**

補助（Secondary・参考）:
- Product Page Views
- Conversion Rate（Product Page Views → App Units）

---

## 判定ルール（運用ルール）

### 最低運用期間

- **最低 14日**は回す（母数が小さいため、短期のブレを避ける）

### 勝ち（採用）

- **Confidence 90%以上**で Treatment が Baseline を上回る
- 上記を満たしたら **Apply Treatment**（反映）へ進む

### 負け（却下）

- **Confidence 90%以上**で Treatment が Baseline を下回る → 停止し、次の仮説へ

### 差が出ない（保留）

- 14〜28日回しても明確差が出ない → 停止し、「コピー or 背景 or スクリム強度」を変えて次のテストへ

---

## リスクと対策（今回の規模向け）

- **母数が小さい**: 100% trafficで最短化（ただしBaselineが50%に割れる点は前提）
- **JP/ENがさらに分割される**: 結論は「合算」で見つつ、JP/ENで明らかな逆方向がないかだけチェック
- **季節性/外部流入**: 週次だけで判断せず、最低2週間の窓で見る

---

## 記録テンプレ（貼り付け用）

### テスト開始情報

- Start Date:
- Baseline（Control）: 現行スクショ
- Treatment: ss1 hero（JP/EN差し替え）
- Traffic: 100%

### 週次チェック（毎週1回だけ）

| Week | Impressions | Product Page Views | App Units | CVR (Imp→Unit) | Confidence | メモ |
|---|---:|---:|---:|---:|---:|---|
| W1 |  |  |  |  |  |  |
| W2 |  |  |  |  |  |  |
| W3 |  |  |  |  |  |  |
| W4 |  |  |  |  |  |  |


