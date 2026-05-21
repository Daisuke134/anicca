# Daily Dharma - 実装仕様書 v1.0

> **作成日**: 2026-01-13
> **目的**: App Store審査100%通過のための修正仕様書
> **対象**: レビューエージェント・実装エージェント向け

---

## 開発環境セットアップ

### ローカル開発（実機テスト）
```bash
cd /Users/cbns03/Downloads/anicca-project/daily-apps/daily-dhamma-app
npx expo start
```
- QRコードが表示される
- iPhoneのExpo Goアプリでスキャン
- **PCとスマホは同じWiFi/テザリングで接続必須**

### EASビルド（TestFlight/App Store用）
```bash
# プレビュービルド（内部テスト用・サーバー不要で動く）
eas build --profile preview --platform ios

# 本番ビルド（App Store提出用）
eas build --profile production --platform ios

# TestFlight提出
eas submit --platform ios
```

---

## 重要情報

| 項目 | 値 |
|------|-----|
| アプリパス | `/Users/cbns03/Downloads/anicca-project/daily-apps/daily-dhamma-app` |
| Bundle ID | `com.dailydhamma.app` |
| Apple ID | `6757726663` |
| Team ID | `S5U8UH3JLJ` |
| RevenueCat iOS Key | `appl_fHvAqxkeyCBSFIslMvNRuCDjndy` |
| RevenueCat Test Key | `test_xsrRSGvJpoCewrQyLxZUAOFpXXi` |

---

# 問題一覧と修正仕様

## P0-1: Netlify デプロイ失敗（Privacy Policy 404）

### ASIS（現状）
- Netlifyデプロイがsubmoduleエラーで失敗
- `.cursor/plans/ios/marketing/PROMO/awesome-nanobanana-pro` がgitにサブモジュールとして認識されているが、`.gitmodules`に定義がない
- Privacy Policy（`https://aniccaai.com/dailydharma/privacy`）が404
- **App Store審査で即リジェクト**

### TOBE（あるべき姿）
- サブモジュール参照を解除
- Netlifyデプロイ成功
- Privacy Policyが正常に表示される

### 修正パッチ
```bash
# プロジェクトルートで実行
cd /Users/cbns03/Downloads/anicca-project

# 壊れたサブモジュール参照を削除
git rm --cached .cursor/plans/ios/marketing/PROMO/awesome-nanobanana-pro

# 通常のディレクトリとして再追加
git add .cursor/plans/ios/marketing/PROMO/awesome-nanobanana-pro

# コミット＆プッシュ
git commit -m "fix: Remove broken submodule reference for Netlify deploy"
git push origin main
```

---

## P0-2: RevenueCat Product ID 不一致（課金不可）

### ASIS（現状）
コード（`paywall.tsx:45-50`）:
```typescript
const monthlyPackage = currentOffering?.availablePackages.find(
  pkg => pkg.identifier === 'com.dailydhamma.app.monthly' || pkg.identifier === '$rc_monthly'
);
const yearlyPackage = currentOffering?.availablePackages.find(
  pkg => pkg.identifier === 'com.dailydhamma.app.yearly' || pkg.identifier === '$rc_annual'
);
```

RevenueCatの実際のProduct ID（ログから確認）:
```
["daily_dharma_yearly", "daily_dharma_monthly"]
```

**不一致により `[Paywall] No package available` エラーが発生**

### TOBE（あるべき姿）
- Product IDがRevenueCatと完全一致
- 課金フローが正常に動作

### 修正パッチ
**ファイル**: `paywall.tsx`
```typescript
// 修正前（45-50行目）
const monthlyPackage = currentOffering?.availablePackages.find(
  pkg => pkg.identifier === 'com.dailydhamma.app.monthly' || pkg.identifier === '$rc_monthly'
);
const yearlyPackage = currentOffering?.availablePackages.find(
  pkg => pkg.identifier === 'com.dailydhamma.app.yearly' || pkg.identifier === '$rc_annual'
);

// 修正後
const monthlyPackage = currentOffering?.availablePackages.find(
  pkg => pkg.identifier === 'daily_dharma_monthly' || pkg.identifier === '$rc_monthly'
);
const yearlyPackage = currentOffering?.availablePackages.find(
  pkg => pkg.identifier === 'daily_dharma_yearly' || pkg.identifier === '$rc_annual'
);
```

---

## P0-3: RevenueCat Test API Key 使用（本番NG）

### ASIS（現状）
ログ:
```
⚠️ Using a Test Store API key.
The Test Store is for development only. Never use a Test Store API key in production.
Apps submitted with a Test Store API key will be rejected during App Review.
```

コード（`RevenueCatProvider.tsx:11-19`）:
```typescript
function getRCToken() {
  if (__DEV__ || Platform.OS === 'web') {
    return process.env.EXPO_PUBLIC_REVENUECAT_TEST_API_KEY;  // ← 開発時はテストキー
  }
  return Platform.select({
    ios: process.env.EXPO_PUBLIC_REVENUECAT_IOS_API_KEY,     // ← 本番はiOSキー
    // ...
  });
}
```

**`__DEV__`がtrueのため、開発ビルドではテストキーが使用される**

### TOBE（あるべき姿）
- 開発時（npx expo start）: テストキー使用 → OK
- プレビュー/本番ビルド: iOSキー使用 → 現状のロジックで正しい

### 確認事項
- **本番ビルド時は`__DEV__`がfalseになるため、iOSキーが使用される**
- 現在のコードは正しい。ただし本番ビルド後に再度ログを確認すること

---

## P0-4: 設定画面の通知頻度 UI 不整合

### ASIS（現状）
`settings.tsx:119-127`:
```tsx
<FrequencyButton value={5} label="5x" />
<FrequencyButton value={7} label="7x" />
<FrequencyButton value={10} label="10x" />
{!settings.isPremium && (
  <Text style={[styles.premiumNote, { color: colors.gold }]}>
    Free: 3x/day • Premium: Unlimited
  </Text>
)}
```

**問題点**:
- 無料ユーザーにも5/7/10が表示されている
- 無料の「3回」がUIに存在しない
- 仕様（無料は3回固定）とUIが不一致 → **嘘になる**

`notifications.ts:51`:
```typescript
const actualFrequency = isPremium ? frequency : Math.min(frequency, 3);
```
→ ロジックでは無料は最大3回に制限されているが、UIと乖離

### TOBE（あるべき姿）
- **無料**: 3回固定（選択UI非表示 or 3のみ表示）
- **有料**: 3/5/7/10の四択

### 修正パッチ
**ファイル**: `settings.tsx`

```tsx
// 修正前（108-129行目）
<View style={styles.section}>
  <Text style={[styles.sectionTitle, { color: colors.textMuted }]}>STAY PRESENT REMINDERS</Text>
  <View style={[styles.settingCard, { backgroundColor: colors.card, borderColor: colors.border }]}>
    <View style={styles.settingCardHeader}>
      <Bell size={20} color={colors.textSecondary} />
      <Text style={[styles.settingLabel, { color: colors.text }]}>Daily Frequency</Text>
    </View>
    <Text style={[styles.settingDescription, { color: colors.textMuted }]}>
      How many mindfulness reminders per day
    </Text>
    <View style={styles.frequencyButtons}>
      <FrequencyButton value={5} label="5x" />
      <FrequencyButton value={7} label="7x" />
      <FrequencyButton value={10} label="10x" />
    </View>
    {!settings.isPremium && (
      <Text style={[styles.premiumNote, { color: colors.gold }]}>
        Free: 3x/day • Premium: Unlimited
      </Text>
    )}
  </View>
</View>

// 修正後
<View style={styles.section}>
  <Text style={[styles.sectionTitle, { color: colors.textMuted }]}>STAY PRESENT REMINDERS</Text>
  <View style={[styles.settingCard, { backgroundColor: colors.card, borderColor: colors.border }]}>
    <View style={styles.settingCardHeader}>
      <Bell size={20} color={colors.textSecondary} />
      <Text style={[styles.settingLabel, { color: colors.text }]}>Daily Frequency</Text>
    </View>
    <Text style={[styles.settingDescription, { color: colors.textMuted }]}>
      How many mindfulness reminders per day
    </Text>
    {settings.isPremium ? (
      <View style={styles.frequencyButtons}>
        <FrequencyButton value={3} label="3x" />
        <FrequencyButton value={5} label="5x" />
        <FrequencyButton value={7} label="7x" />
        <FrequencyButton value={10} label="10x" />
      </View>
    ) : (
      <View style={styles.frequencyFixed}>
        <Text style={[styles.frequencyFixedText, { color: colors.text }]}>
          3x per day
        </Text>
        <TouchableOpacity onPress={() => router.push('/paywall')}>
          <Text style={[styles.upgradeLink, { color: colors.gold }]}>
            Upgrade for more
          </Text>
        </TouchableOpacity>
      </View>
    )}
  </View>
</View>
```

**追加スタイル**:
```typescript
// styles追加
frequencyFixed: {
  marginLeft: 32,
  flexDirection: 'row',
  alignItems: 'center',
  gap: 12,
},
frequencyFixedText: {
  fontSize: 16,
  fontWeight: '600',
},
upgradeLink: {
  fontSize: 14,
  textDecorationLine: 'underline',
},
```

**型定義の修正**:
```typescript
// handleFrequencyChange の型を修正
const handleFrequencyChange = (frequency: 3 | 5 | 7 | 10) => {
  // ...
};

// FrequencyButton の型を修正
const FrequencyButton = ({ value, label }: { value: 3 | 5 | 7 | 10; label: string }) => {
  // ...
};
```

**AppProvider.tsx の型修正**:
```typescript
// 修正前
notificationFrequency: 5 | 7 | 10;

// 修正後
notificationFrequency: 3 | 5 | 7 | 10;

// defaultSettings修正
notificationFrequency: 3,  // デフォルトを3に
```

**既存ユーザーのマイグレーション** ✅ 完了:
```typescript
// settingsQuery内に追加
if (!parsed.isPremium && parsed.notificationFrequency > 3) {
  console.log('[AppProvider] Migrating free user frequency from', parsed.notificationFrequency, 'to 3');
  parsed.notificationFrequency = 3;
}
```

---

## P1-1: ペイウォール「BEST VALUE」削除

### ASIS（現状）
`paywall.tsx:210-212`:
```tsx
<View style={[styles.bestValueBadge, { backgroundColor: colors.gold }]}>
  <Text style={styles.bestValueBadgeText}>BEST VALUE</Text>
</View>
```

App Store Review Guide:
> 「v1の場合、割引やフェイク緊急ペイウォールを使うな」

### TOBE（あるべき姿）
- 「BEST VALUE」バッジを完全削除
- シンプルに価格のみ表示

### 修正パッチ
**ファイル**: `paywall.tsx`

```tsx
// 削除する箇所（210-212行目）
<View style={[styles.bestValueBadge, { backgroundColor: colors.gold }]}>
  <Text style={styles.bestValueBadgeText}>BEST VALUE</Text>
</View>

// スタイルも削除（408-423行目）
bestValueBadge: {
  // ... 削除
},
bestValueBadgeText: {
  // ... 削除
},
```

---

## P1-2: ペイウォール記載内容の修正

### ASIS（現状）
`paywall.tsx:11-27`:
```typescript
const features = [
  {
    icon: Sparkles,
    title: 'Premium Verse Collection',
    description: 'Access all curated Dhammapada verses',  // ← 「all」は誇張
  },
  // ...
];
```

実際は16個のみ（無料8 + 有料8）

### TOBE（あるべき姿）
- 具体的な数字で表現
- 誇張表現を排除

### 修正パッチ
**ファイル**: `paywall.tsx`

```typescript
// 修正前
const features = [
  {
    icon: Sparkles,
    title: 'Premium Verse Collection',
    description: 'Access all curated Dhammapada verses',
  },
  {
    icon: Bell,
    title: 'More Daily Reminders',
    description: 'Up to 10 mindfulness moments per day',
  },
  {
    icon: Flower2,
    title: 'Verse Bookmarking',
    description: 'Save your favorite teachings',
  },
];

// 修正後
const features = [
  {
    icon: Sparkles,
    title: 'Premium Verses',
    description: 'Unlock 8 additional Dhammapada teachings',
  },
  {
    icon: Bell,
    title: 'More Reminders',
    description: 'Up to 10 mindfulness moments per day',
  },
  {
    icon: Flower2,
    title: 'Bookmarking',
    description: 'Save your favorite verses',
  },
];
```

---

## P1-3: Save 44% 削除（追加発見）

### ASIS（現状）
`paywall.tsx:228-230`:
```tsx
<Text style={[styles.planOptionSavings, { color: colors.gold }]}>
  Save 44%
</Text>
```

App Store Review Guide:
> 「v1の場合、比較対象がないため割引表示は避ける」

### TOBE（あるべき姿）
- 「Save 44%」を削除
- シンプルに価格のみ表示

### 修正パッチ ✅ 完了
BEST VALUEと同時に削除済み

---

## P1-4: サブタイトル修正（追加発見）

### ASIS（現状）
`paywall.tsx:138-140`:
```tsx
<Text style={[styles.subtitle, { color: colors.textSecondary }]}>
  Unlock the complete path to mindfulness
</Text>
```

「complete path」は誇張表現

### TOBE（あるべき姿）
- 具体的で誠実な表現に変更

### 修正パッチ ✅ 完了
```tsx
<Text style={[styles.subtitle, { color: colors.textSecondary }]}>
  Unlock more verses and reminders
</Text>
```

---

## P2-1: ペイウォールのスクロール問題

### ASIS（現状）
- `ScrollView`を使用
- Subscribe Nowボタンがスクロールしないと見えない場合がある
- CTAが押しづらい → 課金率低下

### TOBE（あるべき姿）
- 1画面に収まるコンパクトなUI
- Subscribe Nowボタンが常時表示

### 修正パッチ
**ファイル**: `paywall.tsx`

```typescript
// スタイル修正
heroSection: {
  alignItems: 'center',
  marginBottom: 20,  // 32 → 20
},
iconCircle: {
  width: 80,   // 100 → 80
  height: 80,  // 100 → 80
  borderRadius: 40,  // 50 → 40
  // ...
  marginBottom: 16,  // 24 → 16
},
title: {
  fontSize: 28,  // 34 → 28
  // ...
  lineHeight: 34,  // 42 → 34
  marginBottom: 8,  // 12 → 8
},
featuresSection: {
  marginBottom: 20,  // 32 → 20
},
featureRow: {
  paddingVertical: 12,  // 16 → 12
  // ...
},
```

---

## P2-2: コンテンツ追加（16個→30個）

### ASIS（現状）
`verses.ts`:
- 無料: 8個
- 有料: 8個（合計16個）

### TOBE（あるべき姿）
- 無料: 8個
- 有料: 22個追加（合計30個）

### 修正パッチ
**ファイル**: `verses.ts`

以下のverseを追加（isPremium: true）:

```typescript
// 追加するverse（17-30）
{
  id: 17,
  text: "To keep the body in good health is a duty... otherwise we shall not be able to keep the mind strong and clear.",
  source: "Buddha",
  chapter: "Traditional Teaching",
  verseNumber: "",
  isPremium: true,
},
{
  id: 18,
  text: "In the end, only three things matter: how much you loved, how gently you lived, and how gracefully you let go.",
  source: "Buddha",
  chapter: "Traditional Teaching",
  verseNumber: "",
  isPremium: true,
},
{
  id: 19,
  text: "If you knew what I know about the power of giving, you would not let a single meal pass without sharing it.",
  source: "Buddha",
  chapter: "Traditional Teaching",
  verseNumber: "",
  isPremium: true,
},
{
  id: 20,
  text: "Thousands of candles can be lighted from a single candle, and the life of the candle will not be shortened.",
  source: "Dhammapada",
  chapter: "Chapter 1",
  verseNumber: "Verse 1",
  isPremium: true,
},
{
  id: 21,
  text: "The foot feels the foot when it feels the ground.",
  source: "Buddha",
  chapter: "Traditional Teaching",
  verseNumber: "",
  isPremium: true,
},
{
  id: 22,
  text: "Set your heart on doing good. Do it over and over again, and you will be filled with joy.",
  source: "Dhammapada",
  chapter: "Chapter 9 (Papa Vagga)",
  verseNumber: "Verse 118",
  isPremium: true,
},
{
  id: 23,
  text: "Drop by drop is the water pot filled. Likewise, the wise man, gathering it little by little, fills himself with good.",
  source: "Dhammapada",
  chapter: "Chapter 9 (Papa Vagga)",
  verseNumber: "Verse 122",
  isPremium: true,
},
{
  id: 24,
  text: "Overcome the angry by non-anger; overcome the wicked by goodness; overcome the miser by generosity; overcome the liar by truth.",
  source: "Dhammapada",
  chapter: "Chapter 17 (Kodha Vagga)",
  verseNumber: "Verse 223",
  isPremium: true,
},
{
  id: 25,
  text: "If a man speaks or acts with a pure thought, happiness follows him like a shadow that never leaves him.",
  source: "Dhammapada",
  chapter: "Chapter 1 (Yamaka Vagga)",
  verseNumber: "Verse 2",
  isPremium: true,
},
{
  id: 26,
  text: "The past is already gone, the future is not yet here. There's only one moment for you to live.",
  source: "Buddha",
  chapter: "Traditional Teaching",
  verseNumber: "",
  isPremium: true,
},
{
  id: 27,
  text: "Conquer anger with non-anger. Conquer badness with goodness. Conquer meanness with generosity. Conquer dishonesty with truth.",
  source: "Dhammapada",
  chapter: "Chapter 17",
  verseNumber: "Verse 223",
  isPremium: true,
},
{
  id: 28,
  text: "Even death is not to be feared by one who has lived wisely.",
  source: "Buddha",
  chapter: "Traditional Teaching",
  verseNumber: "",
  isPremium: true,
},
{
  id: 29,
  text: "What we are today comes from our thoughts of yesterday, and our present thoughts build our life of tomorrow.",
  source: "Dhammapada",
  chapter: "Chapter 1",
  verseNumber: "Verse 1-2",
  isPremium: true,
},
{
  id: 30,
  text: "Holding on to anger is like grasping a hot coal with the intent of throwing it at someone else; you are the one who gets burned.",
  source: "Buddha",
  chapter: "Traditional Teaching",
  verseNumber: "",
  isPremium: true,
},
```

**ペイウォールの記載も更新**:
```typescript
description: 'Unlock 22 additional Dhammapada teachings',  // 8 → 22
```

---

## 実装チェックリスト

### P0（必須・即対応）
- [ ] Netlify submodule修正 → git操作
- [x] RevenueCat Product ID修正 → `paywall.tsx` ✅ 完了
- [x] 設定画面の通知頻度UI修正 → `settings.tsx` + `AppProvider.tsx` ✅ 完了

### P1（審査前に対応）
- [x] BEST VALUE削除 → `paywall.tsx` ✅ 完了
- [x] Save 44%削除 → `paywall.tsx` ✅ 完了（追加発見項目）
- [x] ペイウォール記載修正 → `paywall.tsx` ✅ 完了
- [x] サブタイトル修正 → `paywall.tsx` ✅ 完了（追加発見項目）

### P2（可能なら対応）
- [ ] スクロール問題修正 → `paywall.tsx` スタイル調整
- [x] コンテンツ追加 → `verses.ts` ✅ 完了（8→30個）

---

## 動作確認項目

### 開発時（npx expo start）
- [ ] アプリ起動確認
- [ ] オンボーディング完了
- [ ] 設定画面で通知頻度が「3回固定」と表示される（無料時）
- [ ] ペイウォール表示
- [ ] ダークモード切り替え

### 本番ビルド後
- [ ] RevenueCatログで本番APIキー使用を確認
- [ ] サブスク購入フロー
- [ ] 通知が指定時刻に届く
- [ ] Privacy Policyリンクが正常

---

## 参考ファイル

| ファイル | 内容 |
|---------|------|
| `app/paywall.tsx` | ペイウォール画面 |
| `app/settings.tsx` | 設定画面 |
| `providers/AppProvider.tsx` | アプリ状態管理 |
| `providers/RevenueCatProvider.tsx` | RevenueCat連携 |
| `utils/notifications.ts` | 通知スケジューリング |
| `data/verses.ts` | コンテンツデータ |

---

## App Store Review Guide準拠チェック

| 項目 | 状態 | 備考 |
|------|------|------|
| Privacy Policy | ⚠️ | Netlify修正後にOK |
| Terms of Service | ✅ | Apple標準EULA使用 |
| 未完成表示なし | ✅ | |
| 嘘の記載なし | ✅ | ペイウォール修正完了 |
| 緊急訴求なし | ✅ | BEST VALUE + Save 44%削除完了 |
| アカウント削除 | N/A | アカウント機能なし |
| AI使用明記 | N/A | AI機能なし |

---

**最終更新**: 2026-01-13
**次のアクション**: P0-1 Netlify submodule修正 → 本番ビルド
