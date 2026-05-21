## 目的

ユーザーが **App Store Connect（GUI）** で迷わず、PPOテスト（スクショ1枚目差し替え）を **作成 → 開始 → 勝ち適用** まで実行できる手順をまとめる。

参照:
- クリエイティブ仕様: `.cursor/plans/PROMO/ss1-hero-spec.md`
- 制作手順: `.cursor/plans/PROMO/ss1-hero-canva-figma-howto.md`
- PPO設計: `.cursor/plans/PROMO/ppo-ss1-benefit-test.md`

---

## 事前に用意するファイル（手元）

- `ss1_benefit_jp_1290x2796.png`
- `ss1_benefit_en_1290x2796.png`

※ 2枚目以降は触らない（現状維持）

---

## PPOテスト作成（App Store Connect）

1. [App Store Connect](https://appstoreconnect.apple.com/) にログイン
2. 対象アプリを選択
3. 左ナビから **Product Page Optimization** を開く
4. **Create Test** をクリック

### 1) テスト基本情報

画面の指示に従って以下を入力/選択:

- **参照名（Name）**: `ppo_2024-12-14_JPEN_ss1_benefit`
- **トリートメント数（Treatments）**: `1`
- **トラフィック割合（Traffic）**: `100%`
- **ローカリゼーション（Localizations）**: `Japanese` / `English`
- **Expected Improvement**: `30%`

### 2) Treatment（差分の作成）

1. Treatment を開く
2. 「Screenshots（or App Previews）」のセクションへ
3. **JPローカリゼーション**:
   - **Screenshot 1** を新しい画像に差し替え（`ss1_benefit_jp_1290x2796.png`）
   - **Screenshot 2+** は変更しない
4. **ENローカリゼーション**:
   - **Screenshot 1** を新しい画像に差し替え（`ss1_benefit_en_1290x2796.png`）
   - **Screenshot 2+** は変更しない

チェック:
- JP/ENともに **1枚目だけ**が変わっている
- 画像サイズが **1290×2796** になっている

### 3) 保存

- 画面右上の **Save**（または画面下の保存ボタン）で保存

---

## テスト開始

1. テストの概要画面に戻る
2. 内容（差分）が正しいことを再確認
3. **Start Test** をクリック

### 審査が挟まる場合

- Apple側の審査/反映待ちになることがある
- その場合はステータスが動くまで待機

---

## 進捗の見方（週1回だけチェック）

1. App Store Connect → **Product Page Optimization**
2. 該当テストを開く
3. 以下を見る:
   - Conversion Rate（Impressions → App Units）
   - Confidence（信頼度）

運用ルール（推奨）:
- **最低14日**は回す（母数が小さいので短期で切らない）
- 毎日見ない（ブレで判断が狂う）

---

## 勝ちの適用（Apply Treatment）

条件（推奨）:
- **Confidence 90%以上**で Treatment が Baseline を上回る

手順:
1. 該当テストを開く
2. **Apply Treatment** をクリック
3. 適用対象（JP/EN）が正しいことを確認して確定

---

## テスト終了（勝ち/負け/差が出ない）

### 負け

- Confidence 90%以上で Treatment が下回る → **Stop Test**

### 差が出ない

- 14〜28日で差が出ない → **Stop Test**
- 次テストの変更点は「コピー/スクリム強度/背景の明暗」など **1点だけ**変える

---

## よくあるミス（チェックリスト）

- **JPだけ差し替えてENを忘れる**
- Screenshot 1以外も触ってしまう
- 画像サイズが違う（1290×2796になっていない）
- 文字が背景に埋もれて読めない（10%チェック未実施）


