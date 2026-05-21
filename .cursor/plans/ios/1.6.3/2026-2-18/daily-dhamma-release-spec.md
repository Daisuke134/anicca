# Daily Dhamma — v1.0 App Store リリース Spec

## 開発環境

| 項目 | 値 |
|------|-----|
| **アプリパス** | `/Users/cbns03/Downloads/anicca-project/daily-apps/daily-dhamma-app` |
| **Bundle ID** | `com.dailydhamma.app` |
| **Apple ID (ASC)** | `6757726663` |
| **RevenueCat Project** | `projbb7b9d1b` |
| **RC iOS API Key** | `appl_fHvAqxkeyCBSFIslMvNRuCDjndy` |
| **作業ブランチ** | `dev` |

---

## バージョンロードマップ

| バージョン | スコープ | 状態 |
|-----------|---------|------|
| **v1.0（本 Spec）** | 審査通過・収益化・50 verses（EN+JP）・日本語メタデータ | **今回** |
| v1.2.1 | WidgetKit（ロック画面・ホーム画面）・iPad 対応 | 次回 |

---

## 1. 概要（What & Why）

### What
Daily Dhamma を App Store に審査通過させて公開する。前回（2026-01-19）の審査リジェクトを修正し、サブスクリプションを再構築し、Verse を 50個（英語＋日本語）に拡充して初回リリースを完了する。

### Why
- Guideline 4.5.4（通知同意取得なしでの Push 配信）でリジェクト済み → 修正必須
- サブスクリプショングループ削除済み → 再作成必須
- 「仏教」「Buddhist」で検索上位を狙うためコンテンツ量が必要 → 50 verses
- 日本語・英語 TikTok マーケティングを展開予定 → 日本語完全対応必須
- 収益化を今日中に開始することが目標

---

## 2. ユーザー体験（Free vs Pro）

### 共通フロー（初回起動）

```
スプラッシュ画面（ベージュ）
    ↓
オンボーディング 3スライド
  スライド1: "Ancient wisdom for modern minds"（花アイコン）
  スライド2: "Stay mindful each day"（Bell アイコン）+ 通知の説明文
  スライド3: "Start your journey"（Sparkles）
  ※ 右上に「Skip」ボタン常時表示
    ↓
iOS 通知権限ダイアログ（v1.0修正後：Skip でも必ず出る）
    ↓
Paywall（モーダル画面）
  ・Monthly $5 / Annual $20（Annual がデフォルト選択）
  ・「Continue with Free」で無料のままスキップ可能
    ↓
メイン画面
```

---

### 無料ユーザーの日常体験

| 時間 | 体験 |
|------|------|
| 朝 07:00 | 通知「Daily Dhamma」→ 法句経の一節（8種類ローテーション） |
| 日中（3回） | 通知「Are you present right now?」等（10種類ローテーション、英語のみ） |
| アプリを開く | 縦スワイプで Verse を読む。**8個**を無限ループ |
| Bookmark タップ | 「プレミアム機能です」→ Paywall へ遷移 |
| 9枚目にスワイプ | 同じ8個の最初に戻る（ループ） |
| Settings | 通知オン/オフ、Stay Present 頻度は**3回固定**（変更不可）、朝の時刻変更可 |

**無料ユーザーが感じる制限:**
- 同じ 8 verses がすぐ一周してしまう
- ブックマークできない
- 通知を増やせない（3回固定）

---

### 有料ユーザー（Premium）の日常体験

| 時間 | 体験 |
|------|------|
| 朝 07:00 | 通知「Daily Dhamma」→ 法句経の一節（**50種類**ローテーション） |
| 日中（最大10回） | 通知（頻度を 3/5/7/10 から選択可） |
| アプリを開く | 縦スワイプで **50 verses** を読む |
| Bookmark | 好きな Verse をブックマーク保存できる |
| Settings | Stay Present 頻度を **3/5/7/10** から自由に変更可 |

**Premium の価値:**
- Verse が 50個に増えて毎日新鮮（無料の6倍以上）
- 通知を 10回まで増やせる → マインドフルネスが深まる
- ブックマークで好きな教えを保存できる

---

### 通知の具体的な中身（10回/日 選択時）

| 時刻 | 種類 | 内容（英語） | 内容（日本語） |
|------|------|------------|--------------|
| 07:00 | Morning Verse | 法句経の一節（毎日変わる） | 法句経の一節（毎日変わる・JP対応後） |
| 08:00頃 | Stay Present | "Are you present right now?" | 「今この瞬間にいますか？」 |
| 09:20頃 | Stay Present | "Notice this moment." | 「この瞬間に気づいてください。」 |
| 10:40頃 | Stay Present | "Where is your mind?" | 「心はどこにありますか？」 |
| 12:00頃 | Stay Present | "Breathe. You are here." | 「息を吸って。あなたはここにいます。」 |
| 13:20頃 | Stay Present | "This too shall pass." | 「これもまた過ぎ去ります。」 |
| 14:40頃 | Stay Present | "Return to your breath." | 「呼吸に戻ってください。」 |
| 16:00頃 | Stay Present | "Feel your feet on the ground." | 「足が地についているのを感じてください。」 |
| 17:20頃 | Stay Present | "What do you hear right now?" | 「今、何が聞こえますか？」 |
| 18:40頃 | Stay Present | "Let thoughts pass like clouds." | 「思考を雲のように流してください。」 |
| 20:00頃 | Stay Present | "This moment is enough." | 「この瞬間で十分です。」 |

※ 通知は毎日微妙に時刻がずれる（ランダム要素あり）
※ v1.0 では英語のみ配信。日本語通知は v1.0 で実装（端末言語設定に基づく）

---

## 3. 受け入れ条件

| # | 条件 | 判定方法 |
|---|------|---------|
| AC-1 | Skip ボタンタップ後も iOS 通知権限ダイアログが表示される | シミュレータで Skip → ダイアログ確認 |
| AC-2 | Monthly $5 / Annual $20 のサブスクが ASC に存在する | ASC CLI で確認 |
| AC-3 | RevenueCat current offering に monthly・annual パッケージが紐付いている | RC MCP で確認 |
| AC-4 | Paywall で正しい価格が表示される | TestFlight 実機確認 |
| AC-5 | Verse が合計 50個 存在する（`data/verses.ts`） | コード確認 |
| AC-6 | 全 50 Verse に `textJa`（日本語訳）が存在する | コード確認 |
| AC-7 | Stay Present メッセージに日本語版が存在する | コード確認 |
| AC-8 | 端末言語が日本語のとき、Verse と通知が日本語で表示される | シミュレータで言語切替 → 確認 |
| AC-9 | 日本語 (ja) App Store メタデータが存在する | ASC CLI で localization 一覧確認 |
| AC-10 | EAS production ビルドが TestFlight に上がっている | ASC で build 確認 |
| AC-11 | ダイスが TestFlight で全フロー（オンボーディング→通知→Paywall→メイン）を確認し「OK」 | ダイスの返答 |
| AC-12 | App Store 審査に提出済み | ASC で "Waiting for Review" 確認 |

---

## 4. As-Is / To-Be

### タスク 1: 通知同意フロー修正（Apple 拒否対応）

**As-Is（問題）:**
```
handleSkip():
  completeOnboarding()
  router.replace('/')   // 通知権限を一切リクエストしない → Apple 拒否の原因
```

**To-Be:**
```
handleSkip():
  await Notifications.requestPermissionsAsync()  // ← 追加
  completeOnboarding()
  router.replace('/')
```

**変更ファイル:** `app/onboarding.tsx`（`handleSkip` 関数のみ）

---

### タスク 2: Verse を 30個 → 50個に拡充（EN+JP 完全対応）

**As-Is:** 30 verses、英語のみ、無料8・有料22

**To-Be:**
- 合計 50 verses
- 無料: 10 verses（`isPremium: false`）
- 有料: 40 verses（`isPremium: true`）
- 全 verse に `text`（英語）と `textJa`（日本語）を追加
- Stay Present メッセージ 10個に日本語版を追加
- 端末言語（`I18n` または `Localization`）に基づいて EN/JP を切り替える

**Verse データ構造（To-Be）:**
```typescript
interface Verse {
  id: number;
  text: string;        // 英語
  textJa: string;      // 日本語（新規追加）
  source: string;      // 例: "Dhammapada, Verse 1"
  isPremium: boolean;
}
```

**追加する 20 verses（参考リスト）:**

| # | English | 日本語 | Source |
|---|---------|--------|--------|
| 31 | "A man is not called wise because he talks and talks again; but if he is peaceful, loving and fearless then he is in truth called wise." | 「多くを語るからといって賢者とは呼ばれない。穏やかで、慈しみがあり、恐れのない者こそ、真に賢者と呼ばれる。」 | Dhammapada, Verse 258 |
| 32 | "A fool who knows his foolishness is wise at least to that extent, but a fool who thinks himself wise is a fool indeed." | 「自分の愚かさを知っている愚者は、それだけ賢者である。しかし、自分を賢いと思っている愚者こそ、真の愚者である。」 | Dhammapada, Verse 63 |
| 33 | "Do not speak harshly to anyone; those who are spoken to will answer you in the same way." | 「誰にも荒々しく話してはならない。話しかけられた者は同じように答えるだろう。」 | Dhammapada, Verse 133 |
| 34 | "Conquer anger by non-anger, conquer evil by good, conquer the miser by generosity, conquer the liar by truth." | 「怒りを怒らないことで征服せよ。悪を善で征服せよ。けちを寛大さで征服せよ。嘘つきを真実で征服せよ。」 | Dhammapada, Verse 223 |
| 35 | "One who has renounced violence towards all living beings, weak or strong, who neither kills nor causes others to kill — that one I call a brahmin." | 「弱くても強くても、すべての生き物に対して暴力を捨て、殺さず、殺させない者を、私はバラモンと呼ぶ。」 | Dhammapada, Verse 405 |
| 36 | "Just as a flower that is lovely and beautiful, but has no scent, so are the fine but fruitless words of one who does not act accordingly." | 「美しく色鮮やかでも香りのない花のように、行動が伴わない言葉は実りのない美しさに過ぎない。」 | Dhammapada, Verse 51 |
| 37 | "Like a beautiful flower, full of colour and full of scent, are the words of those who act accordingly." | 「美しく色鮮やかで香りも豊かな花のように、行動が伴う言葉は実りある美しさを持つ。」 | Dhammapada, Verse 52 |
| 38 | "It is easy to see the faults of others, but difficult to see one's own faults." | 「他人の過ちは見えやすく、自分の過ちは見えにくい。」 | Dhammapada, Verse 252 |
| 39 | "Whoever lives focused on pleasures, with senses unrestrained, immoderate in eating, idle and sluggish, will be overpowered by Mara." | 「感覚をおさえず、食を節制せず、怠惰で無気力に、快楽に向かって生きる者は、悪魔に打ち負かされる。」 | Dhammapada, Verse 7 |
| 40 | "He who is energetic, not lazy, in misfortune, resolute, blameless in conduct, will be freed from suffering." | 「精力的で怠らず、逆境にあっても断固として行いに非難のない者は、苦しみから解放されるだろう。」 | Dhammapada, Verse 24 |
| 41 | "If a person offends a harmless, pure and innocent individual, the evil falls back upon that fool." | 「害のない、清らかな、罪のない人を傷つければ、その悪は愚者自身に降りかかる。」 | Dhammapada, Verse 125 |
| 42 | "He who has renounced violence towards all living beings is a noble one." | 「すべての生き物への暴力を捨てた者こそ、高貴な者である。」 | Dhammapada, Verse 269 |
| 43 | "Do not think lightly of good, saying, 'It will not come to me.' Even a water pot is filled with water by the falling of drops." | 「善を軽く見て「私には来ない」と思ってはならない。水滴が落ちることで水がめは満たされる。」 | Dhammapada, Verse 122 |
| 44 | "Do not think lightly of evil, saying, 'It will not come to me.' Even a water pot is filled with water by the falling of drops." | 「悪を軽く見て「私には来ない」と思ってはならない。水滴が落ちることで水がめは満たされる。」 | Dhammapada, Verse 121 |
| 45 | "The thought manifests as the word; the word manifests as the deed; the deed develops into habit; and habit hardens into character." | 「思考は言葉として現れ、言葉は行為として現れ、行為は習慣となり、習慣は性格として固まる。」 | Dhammapada |
| 46 | "The greatest impurity is ignorance. Free yourself from it." | 「最大の不純は無知である。それから自分を解放せよ。」 | Dhammapada, Verse 243 |
| 47 | "Health is the highest gain, contentment is the highest wealth, trust is the best of relatives, nibbana the highest bliss." | 「健康は最高の利益、満足は最高の富、信頼は最良の親族、涅槃は最高の幸福である。」 | Dhammapada, Verse 203 |
| 48 | "He who has no wounds on his hand may carry poison in his hand; poison does not affect one who has no wounds." | 「手に傷のない者は手に毒を持てる。傷のない者には毒は効かない。」 | Dhammapada, Verse 124 |
| 49 | "There is no fire like passion, no shark like hatred, no snare like folly, no torrent like greed." | 「情欲のような火はなく、憎しみのような鮫はなく、愚かさのような罠はなく、貪りのような激流はない。」 | Dhammapada, Verse 251 |
| 50 | "Should you find a wise critic to point out your faults, follow him as you would a guide to hidden treasure." | 「あなたの過ちを指摘する賢明な批評家を見つけたなら、隠された宝への道案内者のように彼に従え。」 | Dhammapada, Verse 76 |

**Stay Present メッセージ 日本語版（To-Be）:**

| 英語 | 日本語 |
|------|--------|
| "Are you present right now?" | 「今この瞬間にいますか？」 |
| "Notice this moment." | 「この瞬間に気づいてください。」 |
| "Where is your mind?" | 「心はどこにありますか？」 |
| "Breathe. You are here." | 「息を吸って。あなたはここにいます。」 |
| "This too shall pass." | 「これもまた過ぎ去ります。」 |
| "Return to your breath." | 「呼吸に戻ってください。」 |
| "Feel your feet on the ground." | 「足が地についているのを感じてください。」 |
| "What do you hear right now?" | 「今、何が聞こえますか？」 |
| "Let thoughts pass like clouds." | 「思考を雲のように流してください。」 |
| "This moment is enough." | 「この瞬間で十分です。」 |

**変更ファイル:** `data/verses.ts`

---

### タスク 3: App Store Connect サブスクグループ再作成

**As-Is:** サブスクリプショングループ削除済み。製品 ID なし。

**To-Be:**

| 項目 | 値 |
|------|-----|
| グループ名 | `Premium` |
| 製品 1 | `com.dailydhamma.app.monthly` / $5 / 月額 / トライアルなし |
| 製品 2 | `com.dailydhamma.app.yearly` / $20 / 年額 / トライアルなし |
| レビュー画像 | Paywall スクリーンショット（1枚必須） |

**作業方法:** ASC CLI（`asc`）で作成。

---

### タスク 4: RevenueCat Offering 更新

**As-Is:** 既存パッケージに紐付く App Store 製品が存在しないため機能しない。

**To-Be:**
- Offering `default` に `monthly`・`annual` パッケージが存在
- 各パッケージに新しい App Store 製品 ID が紐付いている

**作業方法:** `mcp__revenuecat__*` ツールで操作。

---

### タスク 5: 日本語 App Store メタデータ

**As-Is:** `en-US` のみ。

**To-Be:** `ja` ロケールを追加:

| フィールド | 日本語内容 |
|-----------|----------|
| Name | `Daily Dhamma - 毎日の法句経` |
| Subtitle | `仏陀の教えで心を整える` |
| Keywords | `仏教,法句経,瞑想,マインドフルネス,仏陀,ダンマ,禅,智慧,名言,精神` |
| Promotional Text | `2500年の仏陀の教えを毎日の生活に。法句経の言葉があなたの心に寄り添います。` |
| Description | 下記参照 |

**日本語 Description:**
```
Daily Dhammaは、2500年以上の歴史を持つ法句経（ダンマパダ）の教えをあなたの指先に届けます。

【毎日の智慧】
・法句経から厳選した50の本物の仏教の教え
・シンプルで美しいUI
・TikTokのようにスワイプして教えを探索

【マインドフルネスを保つ】
・1日最大10回のやさしいリマインダー
・「今この瞬間にいますか？」という通知で現在に戻る
・朝の法句経通知で一日をスタート

【プレミアム機能】
・50の法句経すべてにアクセス
・1日最大10回のマインドフルネスリマインダー
・お気に入りの教えをブックマーク

「この世界で憎しみが憎しみによって消えることはない。愛によってのみ消える。これは永遠の法則である。」— 法句経 第5偈
```

**作業方法:** ASC CLI で `asc apps versions localizations` update。

---

### タスク 6: EAS Production ビルド

**As-Is:** 最新ビルドは Build 9（2026-01-16）。タスク1・2の修正未反映。

**To-Be:** タスク1・2の修正を含む新 production ビルドを EAS で作成。

```bash
cd /Users/cbns03/Downloads/anicca-project/daily-apps/daily-dhamma-app
eas build --platform ios --profile production --non-interactive
```

ビルド完了後、TestFlight の "Daisuke" グループに追加。

---

### タスク 7: ダイスによる実機確認

**To-Be:** ダイスが TestFlight で以下を確認し「OK」と返答:

| 確認項目 | 期待動作 |
|---------|---------|
| Skip ボタン | 通知権限ダイアログが出る |
| Enable Notifications ボタン | 通知権限ダイアログが出る |
| Paywall 表示 | Monthly $5 / Annual $20 が正しく表示 |
| 無料でメイン画面 | Verse がスワイプできる |
| 端末を日本語に設定してアプリを開く | Verse が日本語で表示される |

---

### タスク 8: App Store 審査提出

**絶対ルール: タスク 7（ダイスが TestFlight で「OK」）が完了するまで審査提出しない。**

```bash
eas submit --platform ios
```

---

## 5. テストマトリックス

| # | To-Be | テスト方法 | 担当 |
|---|-------|-----------|------|
| T-1 | Skip で通知権限ダイアログが出る | シミュレータで Skip タップ | Claude |
| T-2 | Enable Notifications で通知権限ダイアログが出る | シミュレータで3スライド完走 | Claude |
| T-3 | `verses.ts` に 50個の verse が存在する | コード行数カウント | Claude |
| T-4 | 全 verse に `textJa` が存在する（null/undefined なし） | TypeScript コンパイルで確認 | Claude |
| T-5 | Stay Present に日本語メッセージが存在する | コード確認 | Claude |
| T-6 | 端末言語 = 日本語 → Verse 日本語表示 | シミュレータで言語変更 | Claude |
| T-7 | Paywall で $5/$20 が表示される | TestFlight 実機 | ダイス |
| T-8 | 全オンボーディングフロー + Paywall | TestFlight 実機 | ダイス |

---

## 6. 境界（やらないこと）

| 項目 | 理由 | 次バージョン |
|------|------|------------|
| Widget 実装 | コード有り・スコープ外 | **v1.2.1** |
| iPad 対応 | `supportsTablet: false` のまま | **v1.2.1** |
| Android ビルド | 今回は iOS のみ | 未定 |
| 無料トライアル | 今回はなし（一言で追加可能） | 随時 |
| App Store スクリーンショット変更 | 既存のまま提出 | 随時 |

**触るファイル（今回）:**
- `app/onboarding.tsx`（タスク1）
- `data/verses.ts`（タスク2）

**触らないファイル（今回）:**
- `app/paywall.tsx`
- `providers/RevenueCatProvider.tsx`
- `providers/AppProvider.tsx`

---

## 7. v1.2.1 ロードマップ

| 機能 | 内容 |
|------|------|
| **WidgetKit** | `targets_backup/widget/index.swift` を有効化。ロック画面（rectangular/circular/inline）＋ホーム画面（small/medium）。`@bacons/apple-targets` 導入済み |
| **iPad 対応** | `supportsTablet: true` に変更。iPad レイアウト最適化 |
| **ウィジェット JP 対応** | Widget 内 verse も端末言語に応じて EN/JP 切替 |

---

## 8. 実行手順

| # | ステップ | コマンド / 作業 |
|---|---------|---------------|
| 1 | 通知修正 | `app/onboarding.tsx` の `handleSkip` を編集 |
| 2 | Verse 拡充（EN+JP） | `data/verses.ts` に 20 verse 追加 + `textJa` フィールド追加 |
| 3 | 言語切替ロジック追加 | 端末言語判定で `text` / `textJa` を切り替え |
| 4 | ASC サブスク作成 | `asc` CLI |
| 5 | RC Offering 更新 | `mcp__revenuecat__*` |
| 6 | 日本語 ASC メタデータ | `asc` CLI |
| 7 | EAS ビルド | `eas build --platform ios --profile production --non-interactive` |
| 8 | TestFlight 配布 | Daisuke グループに追加 |
| 9 | ダイス実機確認 | ダイス「OK」まで待機 |
| 10 | 審査提出 | `eas submit --platform ios` |

---

## タスク 9: 完全ローカライゼーション（全 UI を EN/JA 対応）

**As-Is（問題）:** OSが日本語でも、アプリ内 UI は全て英語固定。`getLocalizedVerse()` は verse テキストのみに適用されており、UI 文字列は一切ローカライズされていない。

### 影響範囲

| 画面 | 未対応の文字列 |
|------|--------------|
| `app/onboarding.tsx` | スライドタイトル / サブタイトル（3枚分）/ 「Continue」「Skip」ボタン |
| `app/paywall.tsx` | ヘッダー "Deepen Your Practice" / features（3行）/ "Monthly"/"Yearly"/"Subscribe Now"/"Continue with Free"/"Restore Purchases" / "/month""/year" / Alert メッセージ |
| `app/index.tsx` | "Swipe up for next verse" / &ldquo;&rdquo; 引用符（削除） |
| `app/settings.tsx` | 全ラベル（Notifications, Stay Present, Dark Mode, Privacy Policy 等）/ Alert メッセージ |

### To-Be

**方針:** `i18n-js` + `expo-localization` を使ったシンプルな EN/JA 翻訳ファイル方式。

```
locales/
  en.json   ← 全 UI 文字列（英語）
  ja.json   ← 全 UI 文字列（日本語）

utils/i18n.ts  ← i18n インスタンス初期化・t() エクスポート
```

**切り替えロジック:**
```typescript
// utils/i18n.ts
import * as Localization from 'expo-localization';
import { I18n } from 'i18n-js';

const i18n = new I18n({ en: require('../locales/en.json'), ja: require('../locales/ja.json') });
const lang = Localization.getLocales()[0]?.languageTag ?? 'en';
i18n.locale = lang.toLowerCase().split('-')[0] === 'ja' ? 'ja' : 'en';
i18n.enableFallback = true;
export const t = (key: string) => i18n.t(key);
```

**翻訳キー一覧（完全版）:**

#### onboarding.tsx

| キー | English | 日本語 |
|------|---------|--------|
| `onboarding.slide1.title` | "Ancient wisdom for modern minds" | "現代の心に古代の智慧を" |
| `onboarding.slide1.subtitle` | "Find peace in the timeless teachings of the Dhammapada" | "法句経の普遍の教えに安らぎを見つけてください" |
| `onboarding.slide2.title` | "Daily verses on your lock screen" | "毎日の法句経をロック画面に" |
| `onboarding.slide2.subtitle` | "Start each day with wisdom that transforms your perspective" | "視点を変える智慧で毎日を始めましょう" |
| `onboarding.slide3.title` | "Stay mindful each day" | "毎日マインドフルに過ごす" |
| `onboarding.slide3.subtitle` | "By enabling notifications, you agree to receive daily morning wisdom verses and mindfulness reminders throughout the day.\n\nYou can disable these anytime in Settings." | "通知を有効にすることで、毎朝の法句経と日中のマインドフルネスリマインダーの受信に同意します。\n\nいつでも設定から無効にできます。" |
| `onboarding.continue` | "Continue" | "次へ" |
| `onboarding.enableNotifications` | "Enable Notifications" | "通知を有効にする" |
| `onboarding.skip` | "Skip" | "スキップ" |

#### paywall.tsx

| キー | English | 日本語 |
|------|---------|--------|
| `paywall.title` | "Deepen Your Practice" | "修行を深める" |
| `paywall.subtitle` | "Unlock more verses and reminders" | "より多くの法句経と通知を利用可能に" |
| `paywall.feature.verses.title` | "Premium Verses" | "プレミアム法句経" |
| `paywall.feature.verses.desc` | "Unlock many more Dhammapada teachings" | "より多くの法句経の教えを利用できます" |
| `paywall.feature.reminders.title` | "More Reminders" | "より多くの通知" |
| `paywall.feature.reminders.desc` | "Up to 10 mindfulness moments per day" | "1日最大10回のマインドフルネス通知" |
| `paywall.feature.bookmark.title` | "Bookmarking" | "ブックマーク" |
| `paywall.feature.bookmark.desc` | "Save your favorite verses" | "お気に入りの法句経を保存できます" |
| `paywall.plan.monthly` | "Monthly" | "月額" |
| `paywall.plan.yearly` | "Yearly" | "年額" |
| `paywall.perMonth` | "/month" | "/月" |
| `paywall.perYear` | "/year" | "/年" |
| `paywall.subscribe` | "Subscribe Now" | "今すぐ購読" |
| `paywall.continueFree` | "Continue with Free" | "無料で続ける" |
| `paywall.restore` | "Restore Purchases" | "購入を復元" |
| `paywall.restoring` | "Restoring..." | "復元中..." |
| `paywall.loading` | "Loading plans..." | "プランを読み込み中..." |
| `paywall.cancelAnytime` | "Cancel anytime • Auto-renews unless cancelled" | "いつでもキャンセル可能 • 解約しない限り自動更新" |
| `paywall.termsOfUse` | "Terms of Use" | "利用規約" |
| `paywall.privacyPolicy` | "Privacy Policy" | "プライバシーポリシー" |
| `paywall.alert.restored` | "Restored" | "復元完了" |
| `paywall.alert.restoredMsg` | "Your premium access has been restored." | "プレミアムアクセスが復元されました。" |
| `paywall.alert.noPurchases` | "No Purchases" | "購入履歴なし" |
| `paywall.alert.noPurchasesMsg` | "No previous purchases found." | "以前の購入履歴が見つかりませんでした。" |
| `paywall.alert.restoreFailed` | "Restore Failed" | "復元失敗" |
| `paywall.alert.purchaseFailed` | "Purchase Failed" | "購入失敗" |
| `paywall.alert.tryAgain` | "Please try again later." | "後でもう一度お試しください。" |
| `paywall.alert.unavailable` | "Subscription plans are not available. Please try again later." | "サブスクリプションプランが利用できません。後でもう一度お試しください。" |
| `paywall.alert.error` | "Error" | "エラー" |

#### app/index.tsx

| キー | English | 日本語 |
|------|---------|--------|
| `main.swipeHint` | "Swipe up for next verse" | "上にスワイプして次の法句経へ" |

#### app/settings.tsx

| キー | English | 日本語 |
|------|---------|--------|
| `settings.title` | "Settings" | "設定" |
| `settings.unlockPremium` | "Unlock Premium" | "プレミアムを解放する" |
| `settings.premiumSubtitle` | "Full library & unlimited features" | "全法句経・全機能を使い放題" |
| `settings.section.appearance` | "APPEARANCE" | "外観" |
| `settings.darkMode` | "Dark Mode" | "ダークモード" |
| `settings.section.notifications` | "NOTIFICATIONS" | "通知" |
| `settings.enableNotifications` | "Enable Notifications" | "通知を有効にする" |
| `settings.notificationsHint` | "Receive morning wisdom verses and mindfulness reminders" | "毎朝の法句経とマインドフルネスリマインダーを受け取ります" |
| `settings.section.stayPresent` | "STAY PRESENT REMINDERS" | "今この瞬間への通知" |
| `settings.dailyFrequency` | "Daily Frequency" | "1日の頻度" |
| `settings.frequencyHint` | "How many mindfulness reminders per day" | "1日何回マインドフルネスリマインダーを受け取るか" |
| `settings.timesPerDay` | "3x per day" | "1日3回" |
| `settings.upgradeForMore` | "Upgrade for more" | "アップグレードしてさらに増やす" |
| `settings.section.morningVerse` | "MORNING VERSE" | "朝の法句経" |
| `settings.notificationTime` | "Notification Time" | "通知時刻" |
| `settings.section.about` | "ABOUT" | "このアプリについて" |
| `settings.aboutDhammapada` | "About the Dhammapada" | "法句経について" |
| `settings.section.legal` | "LEGAL" | "法的情報" |
| `settings.privacyPolicy` | "Privacy Policy" | "プライバシーポリシー" |
| `settings.terms` | "Terms of Service" | "利用規約" |

**引用符の削除:**
- `app/index.tsx` の `&ldquo;`/`&rdquo;` を削除（verse テキストをそのまま表示）

### テストマトリックス（ローカライズ）

| # | テスト名 | 内容 |
|---|---------|------|
| T-L1 | `all_i18n_keys_have_ja_translation` | en.json の全キーが ja.json にも存在することを確認 |
| T-L2 | `all_ja_values_non_empty` | ja.json の全値が空文字でないことを確認 |
| T-L3 | `t_returns_ja_when_locale_ja` | locale=ja 時に代表キー5個が日本語を返すことを確認 |
| T-L4 | `t_returns_en_when_locale_en` | locale=en 時に代表キー5個が英語を返すことを確認 |
| T-L5 | `t_fallback_to_en_for_unknown_locale` | locale=de 時に英語にフォールバックすることを確認 |
| T-L6 | `no_missing_key_returns_raw_key` | 存在しないキーで `[missing "en.xxx"]` でなく fallback が返ることを確認 |
| T-L7 | `all_keys_in_en_match_spec_inventory` | en.json のキー数が仕様一覧のキー数（59件）と一致することを確認 |

※ 除外スコープ: `__DEV__` ブロック内の DEVELOPER セクション（テスト用文字列）・ブランド名 "Daily Dhamma"・通知タイトル "Daily Dhamma" は翻訳対象外とする。

**変更ファイル:**
- `utils/i18n.ts`（新規）
- `locales/en.json`（新規）
- `locales/ja.json`（新規）
- `app/onboarding.tsx`
- `app/paywall.tsx`
- `app/index.tsx`（引用符削除含む）
- `app/settings.tsx`
- `__tests__/i18n.test.ts`（新規）

---

## タスク 10 (旧): JPN テリトリー価格設定（Bug #2 修正・完了済み）

**As-Is（問題）:** サブスクリプションの配信テリトリーが USA のみ。日本 Apple ID のユーザーは新製品にアクセスできず、RC SDK がテスト用の古い製品 (`daily_dharma_monthly`/$2.99, `daily_dharma_yearly`/$90.99) にフォールバックする。

**To-Be:**

| 製品 ID | テリトリー | 価格 |
|---------|----------|------|
| `com.dailydhamma.app.premium.monthly` (6759389150) | JPN | ¥750 |
| `com.dailydhamma.app.premium.yearly` (6759388949) | JPN | ¥2,000 |

**変更方法:** ASC CLI で `availability set` → `prices add` の順に実行。

---

## タスク 11 (旧): 日本語言語ワイヤリング（Bug #1 修正・完了済み）

**As-Is（問題）:** `getLocalizedVerse()` は `data/verses.ts` に実装済みだが、UI・通知どこにも接続されていない。`verse.text`（英語固定）がハードコードされている。

**To-Be:** 端末ロケールを `expo-localization` で取得し、`getLocalizedVerse(verse, locale)` を UI・通知の全箇所に適用する。

| ファイル | 修正箇所 | 内容 |
|---------|---------|------|
| `app/index.tsx` | `item.text` | `getLocalizedVerse(item, locale)` に変更 |
| `utils/notifications.ts` | `verse.text`（Morning） | `getLocalizedVerse(verse, locale)` に変更 |
| `utils/notifications.ts` | `stayPresentMessages`（Stay Present） | locale が ja なら `stayPresentMessagesJa` を使用 |
| `app/settings.tsx` | `verse.text`（dev test） | `getLocalizedVerse(verse, locale)` に変更 |

**ロケール取得方法:**
```typescript
import * as Localization from 'expo-localization';
const locale = Localization.getLocales()[0]?.languageTag ?? 'en';
```

---

## タスク 12 (旧): 通知数オーバーフロー修正（Bug #3 修正・完了済み）

**As-Is（問題）:** `daysToSchedule = 7` 固定。10/日設定では 10×7+7 = 77 通知 > iOS 上限 64 でクラッシュ・未配信の原因になる。

**To-Be:** `daysToSchedule` を周波数に応じて動的に算出し、合計通知数が 60 以下に収まるようにする。

```typescript
// 計算式: morningNotifications（=daysToSchedule）+ stayPresent（frequency × daysToSchedule）≤ 60
// daysToSchedule ≤ 60 / (frequency + 1)
const daysToSchedule = Math.floor(60 / (frequency + 1));
// frequency=3  → 60/4=15  (15+45=60 ✓)
// frequency=5  → 60/6=10  (10+50=60 ✓)
// frequency=7  → 60/8=7   ( 7+49=56 ✓)
// frequency=10 → 60/11=5  ( 5+50=55 ✓)
```

**変更ファイル:** `utils/notifications.ts`（`daysToSchedule` の算出箇所のみ）

---

## E2E 判定

| 項目 | 値 |
|------|-----|
| UI 変更 | あり（Skip 挙動変更・Verse 表示の EN/JP 切替） |
| 新画面 | なし |
| Maestro E2E | 不要（Expo Managed Workflow のため Maestro 未対応）。TestFlight 実機確認（タスク7）で代替 |

---

最終更新: 2026-02-20（タスク9 完全ローカライゼーション追記・TestFlight確認ルール追記）
