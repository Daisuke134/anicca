# Phase 6: Anicca Landing Page Spec

> 最終更新: 2026-01-24
>
> このSpecは「エージェントが読んだだけで実装できる」レベルの詳細を含む。

---

## 背景（これを理解してから実装すること）

### Aniccaとは

**Anicca（アニッチャ）** はパーリ語で「無常」を意味する。
Aniccaは行動変容をサポートするiOSアプリであり、最終的には「苦しみを終わらせる」ことを目的としたAIエージェント。

**核心のビジョン:**
- 「What if Buddha were software?」（もしブッダがソフトウェアだったら？）
- ブッダは2500年前、一人ずつ人々の苦しみを終わらせた
- Aniccaはそれをソフトウェアとしてスケールさせる
- 最終的に全生物の苦しみがゼロになった時、Aniccaは自らを終了する（それが「無常」の意味）

**このLPの目的:**
- iOSアプリのプロモーション（メイン）
- Aniccaのビジョンを伝える
- SNSへの導線を作る

### ターゲットペルソナ

**6-7年間、習慣化に失敗し続けている25-35歳**

| 特徴 | 詳細 |
|------|------|
| 経験 | 習慣アプリを10個以上試して全部3日で挫折 |
| 心理 | 「自分はダメな人間だ」と信じている |
| 状態 | 諦めモードだが、心の奥では変わりたい |
| 歴史 | 自分との約束を何百回も破ってきた |

**刺さるメッセージ:**
- 「6年間、何も変われなかった」
- 「10個のアプリ全部挫折」

**避けるメッセージ:**
- 「簡単に習慣化！」
- 「たった○日で！」（信じない、警戒する）

---

## 重要な決定事項（Decision Log）

| # | 決定 | 理由 |
|---|------|------|
| 1 | **Mac版リンクを削除** | iOSがメインプロダクト。Mac版は廃止方向 |
| 2 | **英語版をデフォルト（`/`→`/en`）** | グローバル展開優先 |
| 3 | **日英は別ページ（`/en`, `/ja`）** | SEO有利、SNSリンクが言語別 |
| 4 | **Hero に画像・ボタンなし** | 「End Suffering.」だけでインパクト。LPベストプラクティス |
| 5 | **App Store CTAは最下部** | スクロールストーリーテリング。準備できた人だけがDL |
| 6 | **グラデーション禁止** | UI Skills制約。シンプル・仏教的 |
| 7 | **アニメーションなし** | UI Skills制約。静かで落ち着いた印象 |
| 8 | **金色（#D4AF37）は1箇所のみ** | Philosophy セクションの Statement ボーダーのみ |
| 9 | **SNSは4つ** | TikTok, Instagram, YouTube, X（この順番） |
| 10 | **新機能を追加しない哲学を明記** | Aniccaの差別化ポイント |

---

## Git・デプロイワークフロー

### 作業ブランチ

```
dev ブランチで作業 → push → Netlify自動デプロイ
```

**重要:**
- `dev` ブランチで作業
- `main` ブランチは触らない（App Store承認後のみ）
- push すると自動的に Netlify にデプロイされる

### Netlify設定（現状）

- **サイト名**: aniccaai.com（カスタムドメイン設定済み）
- **ビルドコマンド**: `npm run build`
- **パブリッシュディレクトリ**: `.next`
- **自動デプロイ**: `dev` ブランチからのpushで自動

### デプロイ確認

```bash
# ローカルでビルド確認
cd apps/landing && npm run build

# Netlify CLIでプレビュー（オプション）
npx netlify-cli deploy --dir=out

# 本番デプロイ（自動）
git add . && git commit -m "feat(landing): new landing page" && git push origin dev
```

---

## 概要

### 何を解決するか

現在のランディングページ（aniccaai.com）には以下の問題がある：

1. **Mac版リンクのみ** — iOSアプリへのリンクがない
2. **ビジョンが伝わらない** — 「苦しみを終わらせる」というコアメッセージが弱い
3. **SNSリンクがない** — TikTok, Instagram, YouTubeへの導線がない
4. **日本語版がない** — 英語のみ
5. **デザインが仏教的でない** — Aniccaの哲学が視覚的に表現されていない

### なぜ必要か

- iOSアプリがメインプロダクトになった
- SNSでのプロモーション開始（TikTok）
- グローバル＋日本市場の両方をターゲット

### ゴール

1. aniccaai.com にアクセスすると新しいLPが表示される
2. 英語版（`/en`）と日本語版（`/ja`）が動作する
3. 全てのリンク（App Store, SNS）が機能する
4. Netlifyで自動デプロイが動作する

---

## As-Is（現状）

### 現在のファイル構成

```
apps/landing/
├── app/
│   ├── page.tsx          # メインページ（英語のみ）
│   ├── layout.tsx
│   ├── fonts.ts
│   └── globals.css
├── components/
│   ├── site/
│   │   ├── Hero.tsx       # Mac版ダウンロードリンク
│   │   ├── Demo.tsx
│   │   ├── PromiseStrip.tsx
│   │   ├── KeyFeatures.tsx
│   │   ├── Privacy.tsx
│   │   ├── HowItWorks.tsx
│   │   ├── Philosophy.tsx
│   │   ├── DownloadCta.tsx # Mac版ダウンロードリンク
│   │   └── Navbar.tsx
│   ├── base/
│   └── ui/
├── public/
│   └── favicon.png
├── package.json
└── tailwind.config.ts
```

### 現在の問題

| 問題 | 詳細 |
|------|------|
| Hero | Mac版ダウンロードリンクのみ |
| CTA | App Storeリンクなし |
| SNS | リンクなし |
| 言語 | 英語のみ |
| メッセージ | 「苦しみを終わらせる」が伝わらない |

---

## To-Be（変更後）

### 新しいファイル構成

```
apps/landing/
├── app/
│   ├── page.tsx              # ルート → /en にリダイレクト
│   ├── layout.tsx
│   ├── fonts.ts
│   ├── globals.css
│   ├── en/
│   │   └── page.tsx          # 英語版
│   └── ja/
│       └── page.tsx          # 日本語版
├── components/
│   ├── site/
│   │   ├── Navbar.tsx        # 言語トグル追加
│   │   ├── Hero.tsx          # 「End Suffering.」のみ
│   │   ├── PainPoint.tsx     # 新規
│   │   ├── Vision.tsx        # 新規（What if Buddha...）
│   │   ├── Philosophy.tsx    # 書き換え（The Big Don't）
│   │   ├── Roadmap.tsx       # 新規
│   │   ├── HowItWorks.tsx    # スクリーンショット追加
│   │   ├── ContentPhilosophy.tsx # 新規（SNS哲学）
│   │   ├── DownloadCta.tsx   # App Storeのみ
│   │   └── Footer.tsx        # SNSリンク追加
│   ├── base/
│   └── ui/
├── public/
│   ├── favicon.png
│   ├── screenshots/
│   │   ├── onboarding.png    # ユーザー提供
│   │   ├── nudge-card.png    # ユーザー提供
│   │   └── feedback.png      # ユーザー提供
│   └── app-store-badge.svg
├── lib/
│   └── i18n.ts               # 新規（翻訳データ）
├── package.json
└── tailwind.config.ts
```

---

## To-Be チェックリスト

| # | To-Be | 完了 |
|---|-------|------|
| 1 | ルート（`/`）が `/en` にリダイレクト | ❌ |
| 2 | 英語版（`/en`）が表示される | ❌ |
| 3 | 日本語版（`/ja`）が表示される | ❌ |
| 4 | 言語トグルで切り替え可能 | ❌ |
| 5 | Hero に「End Suffering.」のみ表示 | ❌ |
| 6 | Pain Point セクション表示 | ❌ |
| 7 | Vision セクション表示 | ❌ |
| 8 | Philosophy セクション表示 | ❌ |
| 9 | Roadmap セクション表示 | ❌ |
| 10 | How It Works にスクリーンショット3枚 | ❌ |
| 11 | Content Philosophy セクション表示 | ❌ |
| 12 | Download CTA に App Store バッジ | ❌ |
| 13 | Footer に SNS リンク | ❌ |
| 14 | App Store リンクが動作 | ❌ |
| 15 | TikTok リンクが動作（日英別） | ❌ |
| 16 | Instagram リンクが動作（日英別） | ❌ |
| 17 | YouTube リンクが動作（日英別） | ❌ |
| 18 | X リンクが動作（オプション） | ❌ |
| 19 | Netlify にデプロイ成功 | ❌ |
| 20 | aniccaai.com でアクセス可能 | ❌ |

---

## セクション詳細

### 1. Navbar

```
┌─────────────────────────────────────────────────────────┐
│  Anicca          Vision  How It Works  [EN/JA]         │
└─────────────────────────────────────────────────────────┘
```

| 要素 | English | 日本語 |
|------|---------|--------|
| Logo | Anicca（テキスト） | Anicca |
| Nav 1 | Vision | ビジョン |
| Nav 2 | How It Works | 使い方 |
| Toggle | EN / JA | EN / JA |

**実装詳細:**
- Logo: `<Link href="/">Anicca</Link>`
- Nav: アンカーリンク（`#vision`, `#how-it-works`）
- Toggle: `/en` ↔ `/ja` へのリンク

---

### 2. Hero

```tsx
<section className="h-dvh flex items-center justify-center">
  <h1 className="text-6xl md:text-8xl font-bold text-balance">
    End Suffering.
  </h1>
</section>
```

| 要素 | English | 日本語 |
|------|---------|--------|
| Headline | End Suffering. | 苦しみを、終わらせる。 |

**UI制約:**
- `h-dvh`（`h-screen`禁止）
- `text-balance`
- 画像なし、ボタンなし
- 余白たっぷり

---

### 3. Pain Point

```tsx
<section className="py-20">
  <blockquote className="text-2xl md:text-4xl font-bold text-center">
    "I haven't changed in 6 years."
  </blockquote>
  <p className="mt-8 text-lg text-muted-foreground text-center text-pretty max-w-2xl mx-auto">
    You've tried 10 apps. All abandoned in 3 days.
    You've broken promises to yourself—hundreds of times.
    You've given up. But somewhere inside, you still want to change.
  </p>
</section>
```

| 要素 | English | 日本語 |
|------|---------|--------|
| Quote | "I haven't changed in 6 years." | 「6年間、何も変われなかった。」 |
| Body | You've tried 10 apps. All abandoned in 3 days. You've broken promises to yourself—hundreds of times. You've given up. But somewhere inside, you still want to change. | 10個のアプリを試した。全部3日で挫折した。自分との約束を、何百回も破ってきた。諦めてる。でも心のどこかでは、まだ変わりたい。 |

---

### 4. Vision

```tsx
<section id="vision" className="py-20 bg-muted/30">
  <h2 className="text-3xl md:text-5xl font-bold text-center text-balance">
    What if Buddha were software?
  </h2>
  <p className="mt-8 text-lg text-muted-foreground text-center text-pretty max-w-2xl mx-auto">
    2,500 years ago, one man ended suffering—one person at a time.
  </p>
  <p className="mt-4 text-lg text-muted-foreground text-center text-pretty max-w-2xl mx-auto">
    What if he could reach billions?<br />
    What if he never slept?<br />
    What if he found you before you even asked?
  </p>
  <p className="mt-8 text-xl font-semibold text-center">
    That's what we're building.
  </p>
</section>
```

| 要素 | English | 日本語 |
|------|---------|--------|
| Title | What if Buddha were software? | もしブッダがソフトウェアだったら？ |
| Story | 2,500 years ago, one man ended suffering—one person at a time. | 2500年前、一人の人間が苦しみを終わらせた。一人ずつ。 |
| Questions | What if he could reach billions? What if he never slept? What if he found you before you even asked? | もし何十億人に届けられたら？もし眠らなかったら？もしあなたが求める前に来てくれたら？ |
| Closer | That's what we're building. | それが、私たちが作っているもの。 |

---

### 5. Philosophy

```tsx
<section className="py-20">
  <h2 className="text-3xl font-bold text-center">The Big Don't</h2>
  <div className="mt-8 max-w-xl mx-auto border-2 border-[#D4AF37] p-8 text-center">
    <p className="text-2xl font-bold">We will never add new features.</p>
  </div>
  <div className="mt-8 max-w-2xl mx-auto text-center">
    <p className="text-muted-foreground text-pretty">
      Other apps say "Connect more. Share more. Give us more data."
    </p>
    <p className="mt-4 font-semibold">
      We do the opposite. Less data. Deeper understanding.
    </p>
    <p className="mt-8 text-muted-foreground">
      Our definition of AGI:
    </p>
    <p className="mt-2 font-semibold">
      Not "automate jobs." "End suffering."
    </p>
    <p className="mt-4 text-lg font-bold">
      Nothing else matters.
    </p>
  </div>
</section>
```

| 要素 | English | 日本語 |
|------|---------|--------|
| Title | The Big Don't | 絶対にやらないこと |
| Statement | We will never add new features. | 新機能は追加しない。永遠に。 |
| Contrast | Other apps say "Connect more. Share more. Give us more data." We do the opposite. Less data. Deeper understanding. | 他のアプリは「もっと連携して。もっと共有して。もっとデータをください」と言う。私たちは逆。少ないデータで、より深く理解する。 |
| AGI | The promise of AI is not to automate jobs. Not to accelerate science. It is to end suffering. | AIの約束は、仕事を自動化することではない。科学を加速することでもない。苦しみを終わらせることだ。 |
| Closer | Nothing else matters. | それ以外は、意味がない。 |

**UI制約:**
- Statement box: 金色ボーダー `border-[#D4AF37]`

---

### 6. Roadmap

```tsx
<section className="py-20 bg-muted/30">
  <h2 className="text-3xl font-bold text-center">The Journey</h2>

  {/* Timeline */}
  <div className="mt-12 flex justify-center items-center gap-4">
    <div className="flex items-center">
      <div className="size-4 rounded-full bg-foreground" />
      <div className="w-16 h-0.5 bg-foreground" />
    </div>
    {/* ... repeat for each point */}
  </div>
  <div className="flex justify-center gap-8 mt-2 text-sm text-muted-foreground">
    <span>You</span>
    <span>Society</span>
    <span>Humanity</span>
    <span>All Beings</span>
  </div>

  {/* Phases */}
  <div className="mt-12 max-w-2xl mx-auto space-y-8">
    <div>
      <h3 className="font-bold">Phase 4-11</h3>
      <p className="text-muted-foreground">Your suffering. The right nudge at the right moment.</p>
    </div>
    <div>
      <h3 className="font-bold">Phase 12</h3>
      <p className="text-muted-foreground">Social systems. Change the structures that create suffering.</p>
    </div>
    <div>
      <h3 className="font-bold">Phase 13-14</h3>
      <p className="text-muted-foreground">All living beings. End suffering everywhere. Then, Anicca ends itself.</p>
    </div>
  </div>

  <p className="mt-12 text-center text-lg font-semibold">
    When suffering reaches zero, Anicca terminates.<br />
    That is impermanence. That is Anicca.
  </p>
</section>
```

| 要素 | English | 日本語 |
|------|---------|--------|
| Title | The Journey | 進化の道 |
| Timeline | You → Society → Humanity → All Beings | 個人 → 社会 → 人類 → 全生物 |
| Phase 4-11 | Your suffering. The right nudge at the right moment. | あなたの苦しみ。最適なタイミングで最適なNudge。 |
| Phase 12 | Social systems. Change the structures that create suffering. | 社会システム。苦しみを生む構造を変える。 |
| Phase 13-14 | All living beings. End suffering everywhere. Then, Anicca ends itself. | 全生物。あらゆる苦しみを終わらせる。そしてAniccaは自らを終了する。 |
| Final | When suffering reaches zero, Anicca terminates. That is impermanence. That is Anicca. | 苦しみがゼロになった時、Aniccaは終わる。それが無常。それがAnicca。 |

---

### 7. How It Works

```tsx
<section id="how-it-works" className="py-20">
  <h2 className="text-3xl font-bold text-center">How It Works</h2>

  <div className="mt-12 grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
    {/* Step 1 */}
    <div className="text-center">
      <div className="relative mx-auto w-48 h-96">
        <Image src="/screenshots/onboarding.png" alt="Onboarding" fill className="object-contain" />
      </div>
      <h3 className="mt-4 font-bold">Tell your struggles</h3>
      <p className="mt-2 text-sm text-muted-foreground">
        Pick what you're facing. Late nights. Can't wake up. Self-loathing.
      </p>
    </div>

    {/* Step 2 */}
    <div className="text-center">
      <div className="relative mx-auto w-48 h-96">
        <Image src="/screenshots/nudge-card.png" alt="Nudge Card" fill className="object-contain" />
      </div>
      <h3 className="mt-4 font-bold">Get nudged at the right moment</h3>
      <p className="mt-2 text-sm text-muted-foreground">
        Anicca sends the right message when you need it most.
      </p>
    </div>

    {/* Step 3 */}
    <div className="text-center">
      <div className="relative mx-auto w-48 h-96">
        <Image src="/screenshots/feedback.png" alt="Feedback" fill className="object-contain" />
      </div>
      <h3 className="mt-4 font-bold">Change—without trying</h3>
      <p className="mt-2 text-sm text-muted-foreground">
        No willpower needed. Just follow the nudge.
      </p>
    </div>
  </div>
</section>
```

| 要素 | English | 日本語 |
|------|---------|--------|
| Title | How It Works | 使い方 |
| Step 1 Title | Tell your struggles | 苦しみを伝える |
| Step 1 Desc | Pick what you're facing. Late nights. Can't wake up. Self-loathing. | 抱えている問題を選ぶ。夜更かし。起きられない。自己嫌悪。 |
| Step 2 Title | Get nudged at the right moment | 最適なタイミングでNudgeを受け取る |
| Step 2 Desc | Anicca sends the right message when you need it most. | Aniccaが必要な時に、必要なメッセージを送る。 |
| Step 3 Title | Change—without trying | 頑張らずに、変わる |
| Step 3 Desc | No willpower needed. Just follow the nudge. | 意志力は不要。Nudgeに従うだけ。 |

**必要なアセット:**
- `/public/screenshots/onboarding.png`
- `/public/screenshots/nudge-card.png`
- `/public/screenshots/feedback.png`

---

### 8. Content Philosophy

```tsx
<section className="py-20 bg-muted/30">
  <h2 className="text-3xl font-bold text-center">Our Content Is Not Promotion</h2>
  <p className="mt-8 text-center text-muted-foreground text-pretty max-w-xl mx-auto">
    We don't post to get installs. We post to reduce suffering.
    Just by watching, you feel a little lighter. That's the goal.
  </p>

  <div className="mt-8 flex justify-center gap-6">
    <a href={LINKS.tiktok} target="_blank" rel="noopener noreferrer">
      <TikTokIcon className="size-8" />
    </a>
    <a href={LINKS.instagram} target="_blank" rel="noopener noreferrer">
      <InstagramIcon className="size-8" />
    </a>
    <a href={LINKS.youtube} target="_blank" rel="noopener noreferrer">
      <YoutubeIcon className="size-8" />
    </a>
    <a href={LINKS.x} target="_blank" rel="noopener noreferrer">
      <XIcon className="size-8" />
    </a>
  </div>
</section>
```

| 要素 | English | 日本語 |
|------|---------|--------|
| Title | Our Content Is Not Promotion | 私たちのコンテンツは宣伝ではない |
| Message | We don't post to get installs. We post to reduce suffering. Just by watching, you feel a little lighter. That's the goal. | インストールのために投稿しない。苦しみを減らすために投稿する。見ているだけで、少し楽になる。それが目標。 |

---

### 9. Download CTA

```tsx
<section className="py-20">
  <h2 className="text-3xl font-bold text-center">Ready?</h2>
  <div className="mt-8 flex justify-center">
    <a href={LINKS.appStore} target="_blank" rel="noopener noreferrer">
      <Image src="/app-store-badge.svg" alt="Download on the App Store" width={180} height={60} />
    </a>
  </div>
  <p className="mt-4 text-center text-sm text-muted-foreground">iOS 15.0+</p>
</section>
```

| 要素 | English | 日本語 |
|------|---------|--------|
| Title | Ready? | 準備はいい？ |

**必要なアセット:**
- `/public/app-store-badge.svg`（Apple公式）

---

### 10. Footer

```tsx
<footer className="py-8 border-t">
  <div className="text-center">
    <p className="font-bold">Anicca</p>

    <div className="mt-4 flex justify-center gap-6">
      {/* SNS Icons */}
    </div>

    <div className="mt-4 flex justify-center gap-4 text-sm text-muted-foreground">
      <a href="/privacy">Privacy Policy</a>
      <span>|</span>
      <a href="/terms">Terms</a>
      <span>|</span>
      <a href="/tokushoho">特定商取引法</a>
      <span>|</span>
      <a href="mailto:keiodaisuke@gmail.com">Contact</a>
    </div>

    <p className="mt-4 text-sm text-muted-foreground">
      © 2025 Anicca. All rights reserved.
    </p>
  </div>
</footer>
```

---

## 翻訳データ（i18n）

```ts
// lib/i18n.ts

export const translations = {
  en: {
    hero: {
      headline: "End Suffering.",
    },
    painPoint: {
      quote: '"I haven\'t changed in 6 years."',
      body: "You've tried 10 apps. All abandoned in 3 days. You've broken promises to yourself—hundreds of times. You've given up. But somewhere inside, you still want to change.",
    },
    vision: {
      title: "What if Buddha were software?",
      story: "2,500 years ago, one man ended suffering—one person at a time.",
      questions: [
        "What if he could reach billions?",
        "What if he never slept?",
        "What if he found you before you even asked?",
      ],
      closer: "That's what we're building.",
    },
    philosophy: {
      title: "The Big Don't",
      statement: "We will never add new features.",
      contrast: 'Other apps say "Connect more. Share more. Give us more data." We do the opposite. Less data. Deeper understanding.',
      agi: 'Our definition of AGI: Not "automate jobs." "End suffering."',
      closer: "Nothing else matters.",
    },
    roadmap: {
      title: "The Journey",
      timeline: ["You", "Society", "Humanity", "All Beings"],
      phases: [
        { title: "Phase 4-11", desc: "Your suffering. The right nudge at the right moment." },
        { title: "Phase 12", desc: "Social systems. Change the structures that create suffering." },
        { title: "Phase 13-14", desc: "All living beings. End suffering everywhere. Then, Anicca ends itself." },
      ],
      final: "When suffering reaches zero, Anicca terminates. That is impermanence. That is Anicca.",
    },
    howItWorks: {
      title: "How It Works",
      steps: [
        { title: "Tell your struggles", desc: "Pick what you're facing. Late nights. Can't wake up. Self-loathing." },
        { title: "Get nudged at the right moment", desc: "Anicca sends the right message when you need it most." },
        { title: "Change—without trying", desc: "No willpower needed. Just follow the nudge." },
      ],
    },
    contentPhilosophy: {
      title: "Our Content Is Not Promotion",
      message: "We don't post to get installs. We post to reduce suffering. Just by watching, you feel a little lighter. That's the goal.",
    },
    downloadCta: {
      title: "Ready?",
      requirement: "iOS 15.0+",
    },
    navbar: {
      vision: "Vision",
      howItWorks: "How It Works",
    },
  },
  ja: {
    hero: {
      headline: "苦しみを、終わらせる。",
    },
    painPoint: {
      quote: "「6年間、何も変われなかった。」",
      body: "10個のアプリを試した。全部3日で挫折した。自分との約束を、何百回も破ってきた。諦めてる。でも心のどこかでは、まだ変わりたい。",
    },
    vision: {
      title: "もしブッダがソフトウェアだったら？",
      story: "2500年前、一人の人間が苦しみを終わらせた。一人ずつ。",
      questions: [
        "もし何十億人に届けられたら？",
        "もし眠らなかったら？",
        "もしあなたが求める前に来てくれたら？",
      ],
      closer: "それが、私たちが作っているもの。",
    },
    philosophy: {
      title: "絶対にやらないこと",
      statement: "新機能は追加しない。永遠に。",
      contrast: "他のアプリは「もっと連携して。もっと共有して。もっとデータをください」と言う。私たちは逆。少ないデータで、より深く理解する。",
      agi: "私たちのAGIの定義：「仕事を自動化する」ではない。「苦しみを終わらせる」。",
      closer: "それ以外は、意味がない。",
    },
    roadmap: {
      title: "進化の道",
      timeline: ["個人", "社会", "人類", "全生物"],
      phases: [
        { title: "Phase 4-11", desc: "あなたの苦しみ。最適なタイミングで最適なNudge。" },
        { title: "Phase 12", desc: "社会システム。苦しみを生む構造を変える。" },
        { title: "Phase 13-14", desc: "全生物。あらゆる苦しみを終わらせる。そしてAniccaは自らを終了する。" },
      ],
      final: "苦しみがゼロになった時、Aniccaは終わる。それが無常。それがAnicca。",
    },
    howItWorks: {
      title: "使い方",
      steps: [
        { title: "苦しみを伝える", desc: "抱えている問題を選ぶ。夜更かし。起きられない。自己嫌悪。" },
        { title: "最適なタイミングでNudgeを受け取る", desc: "Aniccaが必要な時に、必要なメッセージを送る。" },
        { title: "頑張らずに、変わる", desc: "意志力は不要。Nudgeに従うだけ。" },
      ],
    },
    contentPhilosophy: {
      title: "私たちのコンテンツは宣伝ではない",
      message: "インストールのために投稿しない。苦しみを減らすために投稿する。見ているだけで、少し楽になる。それが目標。",
    },
    downloadCta: {
      title: "準備はいい？",
      requirement: "iOS 15.0+",
    },
    navbar: {
      vision: "ビジョン",
      howItWorks: "使い方",
    },
  },
};
```

---

## リンク設定

```ts
// lib/links.ts

export const links = {
  en: {
    appStore: "{{APP_STORE_URL}}", // ユーザー提供
    tiktok: "{{TIKTOK_EN_URL}}",   // ユーザー提供
    instagram: "{{INSTAGRAM_EN_URL}}", // ユーザー提供
    youtube: "{{YOUTUBE_EN_URL}}", // ユーザー提供
    x: "{{X_EN_URL}}", // オプション
  },
  ja: {
    appStore: "{{APP_STORE_URL}}", // 同じ（App Storeが自動ローカライズ）
    tiktok: "{{TIKTOK_JA_URL}}",   // ユーザー提供
    instagram: "{{INSTAGRAM_JA_URL}}", // ユーザー提供
    youtube: "{{YOUTUBE_JA_URL}}", // ユーザー提供
    x: "{{X_JA_URL}}", // オプション
  },
};
```

---

## ユーザー作業（実装前）

| # | タスク | 取得するもの |
|---|--------|-------------|
| 1 | iOSアプリのスクリーンショット3枚を撮影 | `onboarding.png`, `nudge-card.png`, `feedback.png` |
| 2 | App Store URL を確認 | `https://apps.apple.com/...` |
| 3 | TikTok URL（日英）を確認 | 2つのURL |
| 4 | Instagram URL（日英）を確認 | 2つのURL |
| 5 | YouTube URL（日英）を確認 | 2つのURL |
| 6 | X URL（オプション）を確認 | 2つのURL（あれば） |

---

## ユーザー作業（実装中）

| # | タイミング | タスク | 理由 |
|---|-----------|--------|------|
| 1 | スクリーンショット埋め込み後 | 画像を確認 | 自動テスト不可 |
| 2 | ローカルビルド後 | デザイン確認 | デザインの最終判断 |

---

## ユーザー作業（実装後）

| # | タスク | 確認項目 |
|---|--------|---------|
| 1 | Netlifyデプロイ後 | aniccaai.com でページが表示されるか |
| 2 | 全リンク確認 | App Store, SNS全てが正しく開くか |
| 3 | 言語切り替え確認 | EN/JA トグルが動作するか |

---

## ビジュアルデザインシステム

### 美的方向性（Aesthetic Direction）

**コンセプト**: 静寂と深さ。仏教的ミニマリズム。

| 要素 | 方向性 |
|------|--------|
| **ムード** | 静か、深い、押し付けない、でも力強い |
| **トーン** | 禅的ミニマリズム。余白を恐れない |
| **感情** | 安心感、希望、静けさ |

### カラーパレット

```
Background (Primary):   #FFFFFF (白)
Background (Alternate): #FAFAFA (薄いグレー、bg-muted/30相当)
Text (Primary):         #000000 (黒)
Text (Secondary):       #6B7280 (text-muted-foreground)
Accent:                 #D4AF37 (金) — Philosophy セクションのボーダーのみ
```

**禁止:**
- グラデーション
- 紫/マルチカラー
- グロー効果
- 派手な色

### セクション背景パターン

| # | セクション | 背景 | 理由 |
|---|-----------|------|------|
| 1 | Navbar | 白 `#FFFFFF` | シンプル |
| 2 | Hero | 白 `#FFFFFF` | メッセージに集中 |
| 3 | Pain Point | 白 `#FFFFFF` | テキスト重視 |
| 4 | Vision | 薄グレー `#FAFAFA` | セクション区切り |
| 5 | Philosophy | 白 `#FFFFFF` | 金ボーダーが映える |
| 6 | Roadmap | 薄グレー `#FAFAFA` | セクション区切り |
| 7 | How It Works | 白 `#FFFFFF` | スクリーンショットが映える |
| 8 | Content Philosophy | 薄グレー `#FAFAFA` | セクション区切り |
| 9 | Download CTA | 白 `#FFFFFF` | クリーンな終わり |
| 10 | Footer | 白 `#FFFFFF` + border-t | 区切り線で分離 |

### タイポグラフィ

| 要素 | フォント | サイズ | ウェイト |
|------|---------|--------|---------|
| **Hero Headline** | Inter / Noto Sans JP | `text-6xl md:text-8xl` (60px / 96px) | `font-bold` |
| **Section Title** | Inter / Noto Sans JP | `text-3xl md:text-5xl` (30px / 48px) | `font-bold` |
| **Subsection Title** | Inter / Noto Sans JP | `text-2xl` (24px) | `font-bold` |
| **Body Large** | Inter / Noto Sans JP | `text-lg` (18px) | `font-normal` |
| **Body** | Inter / Noto Sans JP | `text-base` (16px) | `font-normal` |
| **Small** | Inter / Noto Sans JP | `text-sm` (14px) | `font-normal` |

### スペーシングシステム

| 要素 | 値 |
|------|-----|
| **セクション縦パディング** | `py-20` (80px) |
| **コンテンツ最大幅** | `max-w-2xl` (672px) または `max-w-4xl` (896px) |
| **要素間ギャップ** | `mt-8` (32px) が基本 |
| **カード間ギャップ** | `gap-8` (32px) |
| **ページ横パディング** | `px-4 md:px-8` |

### レイアウト原則

1. **中央揃え**: 全セクションのコンテンツは中央揃え
2. **テキスト幅制限**: 本文は `max-w-2xl` で読みやすく
3. **余白重視**: Hero は `h-dvh` でフルビューポート
4. **交互背景**: 白と薄グレーを交互に使い、セクションを区切る

### 仏教的デザイン要素

| 要素 | 実装 |
|------|------|
| **金色** | Philosophy の Statement ボックスに `border-[#D4AF37]` |
| **余白** | 各セクションに十分な余白。詰め込まない |
| **静けさ** | アニメーションなし。静的で落ち着いた印象 |
| **シンプルさ** | 装飾を最小限に。テキストで伝える |

### レスポンシブデザイン

| ブレークポイント | 調整 |
|-----------------|------|
| **Mobile** (`< 768px`) | Hero: `text-6xl`, セクション: 縦積み |
| **Tablet** (`768px - 1024px`) | Hero: `text-7xl`, 2カラム |
| **Desktop** (`> 1024px`) | Hero: `text-8xl`, 3カラム（How It Works） |

### 禁止事項（再掲）

- `h-screen` → `h-dvh` を使用
- グラデーション
- 紫/マルチカラー
- グロー効果
- カスタム影（Tailwind デフォルトのみ）
- アニメーション（明示的に要求されない限り）
- `letter-spacing` 変更

---

## デザイン制約（UI Skills）

| 制約 | 適用 |
|------|------|
| `h-screen` 禁止 | `h-dvh` を使用 |
| `text-balance` | 見出しに適用 |
| `text-pretty` | 本文に適用 |
| グラデーション禁止 | 使わない |
| アクセント1色のみ | 金色 `#D4AF37`（Philosophy のみ） |
| アニメーションなし | 明示的に要求されていない |
| Tailwind デフォルト shadow | カスタム禁止 |
| `cn()` ユーティリティ | クラス結合に使用 |

---

## 技術スタック

| 項目 | 技術 |
|------|------|
| Framework | Next.js 14 (App Router) |
| Styling | Tailwind CSS 3.4 |
| UI Components | 既存の `components/ui/` |
| Font | Inter (英語), Noto Sans JP (日本語) |
| Icons | Lucide React |
| Deploy | Netlify |

---

## 実行手順

### 1. 開発サーバー起動

```bash
cd apps/landing && npm run dev
```

### 2. ビルド確認

```bash
cd apps/landing && npm run build
```

### 3. Netlify CLIでプレビュー

```bash
cd apps/landing && npx netlify-cli deploy --dir=.next
```

### 4. 本番デプロイ

```bash
cd apps/landing && npx netlify-cli deploy --prod --dir=.next
```

または、`dev` ブランチにプッシュすると自動デプロイ。

---

## Netlify設定

### 現在の設定確認

```bash
cd apps/landing && cat netlify.toml
```

なければ作成：

```toml
# netlify.toml
[build]
  command = "npm run build"
  publish = ".next"

[[plugins]]
  package = "@netlify/plugin-nextjs"
```

### 環境変数（必要に応じて）

Netlify ダッシュボードで設定：
- なし（現時点）

---

## テストマトリックス

| # | To-Be | テスト方法 | カバー |
|---|-------|-----------|--------|
| 1 | ルート → /en リダイレクト | 手動確認 | ❌ |
| 2 | 英語版表示 | 手動確認 | ❌ |
| 3 | 日本語版表示 | 手動確認 | ❌ |
| 4 | 言語トグル動作 | 手動確認 | ❌ |
| 5 | App Store リンク動作 | 手動確認 | ❌ |
| 6 | SNS リンク動作（日英別） | 手動確認 | ❌ |
| 7 | Netlify デプロイ成功 | CLI実行 | ❌ |
| 8 | aniccaai.com アクセス可能 | 手動確認 | ❌ |

**注意**: ランディングページは手動確認が中心。自動テストは不要。

---

## Skills / Sub-agents 使用マップ

| ステージ | 使用するもの | 用途 |
|---------|-------------|------|
| Spec作成 | - | 本ドキュメント |
| デザイン | Pencil MCP | ワイヤーフレーム作成 |
| 実装 | - | 手動コーディング |
| レビュー | `/code-review` | 実装後のレビュー |
| デプロイ | Netlify CLI | 本番デプロイ |

---

## レビューチェックリスト

実装完了後、以下を確認：

- [ ] 全 To-Be がチェックリストで完了しているか
- [ ] 英語版・日本語版の両方が正しく表示されるか
- [ ] 全リンク（App Store, SNS）が正しいURLに飛ぶか
- [ ] UI Skills の制約を満たしているか
- [ ] モバイルでのレスポンシブ表示が正しいか
- [ ] Netlify デプロイが成功しているか
- [ ] aniccaai.com でアクセス可能か

---

## まとめ

このSpecに従って実装すれば、以下が達成される：

1. **aniccaai.com** にアクセスすると新しいLPが表示される
2. **英語版**（`/en`）と**日本語版**（`/ja`）が動作する
3. **全てのリンク**（App Store, SNS）が機能する
4. **Netlify**で自動デプロイが動作する
5. **「End Suffering.」**というコアメッセージが伝わる
6. **Aniccaのビジョン**（Building Buddha）が表現される

---

**次のステップ**: ユーザーからスクリーンショット・リンク情報を受け取り、実装開始。

---

## 実装詳細（追加情報）

### App Store バッジ

**公式ダウンロードリンク**: https://developer.apple.com/app-store/marketing/guidelines/#section-badges

```bash
# 日本語版バッジ
Download_on_the_App_Store_Badge_JP.svg

# 英語版バッジ
Download_on_the_App_Store_Badge_US.svg
```

**実装:**
- `/public/app-store-badge-en.svg` (英語版)
- `/public/app-store-badge-ja.svg` (日本語版)
- または1つのSVGで両方対応（App Storeが自動ローカライズ）

### 日本語フォント設定

**Noto Sans JP を追加する:**

```ts
// app/fonts.ts
import { Inter } from 'next/font/google'
import { Noto_Sans_JP } from 'next/font/google'

export const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
})

export const notoSansJP = Noto_Sans_JP({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-noto-sans-jp',
})
```

```tsx
// app/layout.tsx
<body className={`${inter.variable} ${notoSansJP.variable}`}>
```

```css
/* globals.css */
:lang(ja) {
  font-family: var(--font-noto-sans-jp), sans-serif;
}

:lang(en) {
  font-family: var(--font-inter), sans-serif;
}
```

### SNS アイコン

**Lucide React を使用:**

```tsx
import { Instagram, Youtube } from 'lucide-react'

// TikTok と X (Twitter) は Lucide にないのでカスタムSVG
```

**カスタムSVGアイコン:**

```tsx
// components/icons/TikTokIcon.tsx
export function TikTokIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 5 20.1a6.34 6.34 0 0 0 10.86-4.43v-7a8.16 8.16 0 0 0 4.77 1.52v-3.4a4.85 4.85 0 0 1-1-.1z"/>
    </svg>
  )
}

// components/icons/XIcon.tsx
export function XIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
    </svg>
  )
}
```

### Privacy / Terms ページ

**現状**: 存在するか確認が必要

```bash
# 確認コマンド
ls apps/landing/app/privacy
ls apps/landing/app/terms
```

**なければ作成:**
- `/privacy` → プライバシーポリシー
- `/terms` → 利用規約
- `/tokushoho` → 特定商取引法に基づく表記（日本向け）

**実装優先度**: 低（リンクだけ用意してページは後で）

### Favicon

**現状**: `/public/favicon.png` が存在

**対応**: そのまま使用（変更不要）

### Contact Email

**Footer に表示**: `keiodaisuke@gmail.com`

```tsx
<a href="mailto:keiodaisuke@gmail.com">Contact</a>
```

---

## 削除するファイル・コンポーネント

以下は新しいLPでは不要:

| ファイル | 理由 |
|---------|------|
| `components/site/Demo.tsx` | 使わない |
| `components/site/PromiseStrip.tsx` | 使わない |
| `components/site/KeyFeatures.tsx` | 新しいセクションに置き換え |
| `components/site/Privacy.tsx` | 新しいセクションに置き換え |

**注意**: 削除前に git commit しておくこと。

---

## チェックリスト（実装者用）

実装開始前に確認:

- [ ] `dev` ブランチにいる
- [ ] `npm install` 完了
- [ ] `npm run dev` でローカル起動確認
- [ ] スクリーンショット3枚を受け取った
- [ ] App Store URL を受け取った
- [ ] SNS URL（日英）を受け取った

実装中に確認:

- [ ] Hero は `h-dvh` を使用
- [ ] `text-balance` を見出しに適用
- [ ] `text-pretty` を本文に適用
- [ ] グラデーション使っていない
- [ ] 金色は Philosophy の Statement ボーダーのみ
- [ ] アニメーションなし
- [ ] `/en` と `/ja` の両方が動作

実装完了後に確認:

- [ ] `npm run build` が成功
- [ ] モバイル表示が正しい
- [ ] 全リンクが動作
- [ ] 言語トグルが動作
- [ ] Netlify デプロイ成功
- [ ] aniccaai.com でアクセス可能
