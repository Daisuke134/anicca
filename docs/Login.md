• ログインの役割と提示タイミング

  - docs/ios.md のMVP要件（起床シーケンス、日中ナッジ、ボイスクローン、サブスク課金）では、
    ユーザー固有データ（habitSchedules、voice_id、課金トークン）を apps/api でユーザー単位に
    保存する必要があります。このため「Talk to Anicca」ボタンを押す前に確実な本人性を結び付け
    ておくことが必須です。
  - Appleは他社ログインを提供するアプリに Sign in with Apple を同等以上の選択肢とし
    て提示するよう義務付けています。(en.wikipedia.org (https://en.wikipedia.org/wiki/
    Sign_in_with_Apple?utm_source=openai))
  - HIGは「価値と引き換えに認証を求め、できるだけ遅らせる」ことを推奨しているため、オンボー
    ディングの権限リクエスト完了直後（ユーザーが価値を認識した直後）でログインを挿入する
    のが最適です。(miniring.gitbook.io (https://miniring.gitbook.io/hig/user-interaction/
    authentication?utm_source=openai))

  UI/UXベストプラクティス（iOS標準準拠）

  - SignInWithAppleButton(.signIn, .black) をフル幅で配置し、スタック型レイアウトでは常
    に最上段に置きます（Appleが他社ボタンより上に置くよう求めています）。(macrumors.com
    (https://www.macrumors.com/2019/06/05/apple-asks-devs-to-prioritise-its-sign-in-button/?
    utm_source=openai))
  - Apple公式デザイン要件に合わないボタンは審査リジェクトにつながるため、色・角丸半
    径・padding は ASAuthorizationAppleIDButton に一任し、独自描画をしないでください。
    (community.auth0.com (https://community.auth0.com/t/react-native-auth0-app-rejected-by-
    apple-due-to-apple-sign-in-ui-in-universal-login/37949?utm_source=openai))
  - 1タップでサインイン→Face ID認証→同一画面で成功状態を伝えるモーダルの流れとし、成功後は自
    動的に次ステップ（habit設定）へ遷移させます。

  iOSクライアント実装手順（行単位での修正指示）

  1. aniccaios/aniccaios/AppState.swift
      - 8行目付近に enum AuthStatus { case signedOut, signingIn, signedIn(UserProfile) } を
        追加。
      - 9行目に @Published var authStatus: AuthStatus = .signedOut を新設し、UserDefaults
        キー com.anicca.userId を保存・復元するロジックを 25〜63行の defaults 初期化ブロック
        に組み込みます。
      - Appleトークンを保存するため、struct UserProfile { let userId: String; let
        displayName: String; let email: String? } を定義し、authStatus が .signedIn のときに
        habitSchedules の読み書きを許可するガードを 70行・83行などの更新メソッド先頭へ追加し
        てください。
  2. aniccaios/aniccaios/ContentView.swift
      - 13〜18行を if appState.authStatus == .signedIn(_) { SessionView() } else if
        appState.isOnboardingComplete { AuthGateView() } else { OnboardingFlowView() } に書
        き換え、オンボーディング完了済みでも未ログインなら AuthGateView を表示するようにし
        ます。
  3. aniccaios/aniccaios/Onboarding/OnboardingStep.swift
      - 7行目に case account を追加し、列挙順を welcome → microphone → notifications →
        account → habitSetup に揃えます。
  4. aniccaios/aniccaios/Onboarding/OnboardingFlowView.swift
      - 9〜16行の switch に case .account: AuthenticationStepView(next: advance) を追加。
      - 20〜30行の advance() 内で .notifications の次を .account、.account の次
        を .habitSetup に変更。
  5. 新規ファイル aniccaios/aniccaios/Onboarding/AuthenticationStepView.swift を追加
      - SignInWithAppleButton(.signIn, onRequest:onCompletion:) を配置し、
        onRequest で 32バイトのnonceを SecRandomCopyBytes から生成、onCompletion で
        ASAuthorizationAppleIDCredential を AuthCoordinator に橋渡しします。
      - UI構造は GitHubの tmaasen/iOS-SwiftUI-Firebase-Login-Template の
        SignInWithAppleButtonView.swift を参照（同リポジトリはSwiftUI＋Firebase＋Appleログ
        インのベストプラクティス実装を提供）。(github.com (https://github.com/tmaasen/iOS-
        SwiftUI-Firebase-Login-Template?utm_source=openai))
  6. aniccaios/aniccaios/SessionView.swift
      - 8〜44行の body 先頭に guard case .signedIn = appState.authStatus else
        { EmptyStateView(title:"サインインしてください") } を追加し、誤って未認証で音声セッ
        ションを張らないようにします。
  7. aniccaios/aniccaios/SettingsView.swift
      - ツールバー右上ボタン横に「Sign Out」ボタンを追加し、AuthCoordinator.shared.signOut()
        を呼んだのち appState.resetState() を実行。

  バックエンド (apps/api) 側の最小改修

  1. apps/api/src/routes/auth/ に apple.js を新設し、POST /auth/apple でクライアントから受
     け取る identityToken と nonce を検証。Appleの公開鍵 https://appleid.apple.com/auth/keys
     をJWKキャッシュし、JWT検証後に sub を内部ユーザーIDとして users テーブルへ upsert。
  2. apps/api/src/services/authService.ts（既存なら流用）に「nonceのハッシュ照合と有効期限60
     秒」を実装し、apps/api/src/routes/session など全APIで req.userId を必須化。
  3. Appleレスポンスは初回のみ氏名・メールを返すため、apps/api で永続化し、再ログイン時は保
     存済み値を返す（5月3日以降のAppleプライベートリレー仕様変更で userIdentifier が変わる事
     象が報告されているので、apps/api 側で追加キーを保持しておくと復旧が容易）。(reddit.com
     (https://www.reddit.com/r/iOSProgramming/comments/1kg6urt?utm_source=openai))

  セキュリティ実装の要点

  - 毎回ランダムnonceを生成し、ASAuthorizationController に request.nonce = SHA256(nonce)
    を渡します。Firebase公式ドキュメントも同手順を推奨しており、リプレイ攻撃を防
    げます。(firebase.google.com (https://firebase.google.com/docs/auth/ios/apple?
    utm_source=openai))
  - 検証に通った identityToken だけを apps/api に送信し、アプリ内でユーザーID文字列を直接保
    存しない（HIGと同じくサインイン画面を軽量に保ちつつセキュリティを担保）。

  ログインを提示する正確なタイムライン

  1. Welcome → マイク/通知権限取得（価値説明）
  2. AuthenticationStepView で Sign in with Apple（上記UI要件遵守）
  3. Habit/Wake設定→ボイス設定→Trial Paywall
  4. SessionView のボタン解放

  今後の運用ポイント

  - Sign in with Apple は「他社ボタンより上に置く」「純正ボタンをそのまま使用」「初回の
    み姓名が返るので保存する」を満たしていれば審査リスクを最小化できます。(macrumors.com
    (https://www.macrumors.com/2019/06/05/apple-asks-devs-to-prioritise-its-sign-in-button/?
    utm_source=openai))
  - tmaasen/iOS-SwiftUI-Firebase-Login-Template をベースに AuthCoordinator／AuthViewModel
    の構造とCombineでの状態管理を抽象化すれば、既存の AppState との結合もスムーズで
    す。(github.com (https://github.com/tmaasen/iOS-SwiftUI-Firebase-Login-Template?
    utm_source=openai))