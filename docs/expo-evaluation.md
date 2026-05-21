# Expo 導入検討ドキュメント v1.0

最終更新日: 2025-11-02（Asia/Tokyo）
作成担当: Codex（GPT-5）
対象読者: Anicca iOS プロダクトマネージャー / iOS 実装担当 / QA / 経営

---

## 1. Expo の概要と適用範囲

Expo は React Native を基盤に、クロスプラットフォーム（iOS / Android / Web）開発を高速化するためのランタイム・ビルドサービス・ホスティングツール群である。主な特徴は以下の通り。

- **JavaScript/TypeScript 単一コードベース**: UI やビジネスロジックを React コンポーネントとして記述し、各プラットフォームへ共通化。
- **Managed / Bare ワークフロー**: Managed はネイティブコードを持たず `app.json`／`app.config.ts` の設定と Expo SDK パッケージのみで構成。Bare は React Native プロジェクトに Expo ランタイムを組み込む方式で、Xcode/Android Studio の完全制御が可能。
- **EAS (Expo Application Services)**: クラウドビルド・OTA アップデート・Submit 自動化など CI/CD を提供。`eas.json` でプロファイル定義、`eas build` や EAS Workflows で本番／開発ビルドを生成。
- **Expo Modules API**: Swift/Kotlin/Java で独自ネイティブモジュールを実装し、JS にエクスポートする仕組み。`expo prebuild` 実行時に `ios/` `android/` ディレクトリへ反映。

Anicca iOS で想定する「音声ファースト」「起床クリティカル通知」「BGTask プリロード」「Core Data＋CloudKit」「CryptoKit AES-GCM」などの高度なネイティブ機能を Expo で実現する場合、Managed ワークフローだけでは不足し、Bare（＝React Native＋Expo Modules）への移行が必須となる。

---

## 2. 開発ワークフロー

### 2.1 プロジェクト初期化
1. `npx create-expo-app` でテンプレート生成。
2. 開発ビルドを前提に `npx expo install expo-dev-client` を追加。
3. LiveKit などネイティブプラグイン利用時は `expo prebuild` に備え `app.json` の `plugins` セクションを整備。

### 2.2 EAS Build
- `eas login` → `eas build --platform ios --profile development` で iOS 開発ビルド（デバイス／シミュレータ）。
- `eas build --platform ios --profile production`＋`eas submit --platform ios` で TestFlight / App Store Connect 連携。
- Workflows YAML で GitHub Actions から fingerprint → 既存ビルド再利用 → OTA update 送信まで自動化可能。

### 2.3 Development Build と Expo Go
- Expo Go 単体では多くのネイティブモジュール（LiveKit、RevenueCat 等）が動作しないため、開発ビルド（`developmentClient: true`）の配布が前提。
- `expo start` で Metro bundler を起動し、`expo run:ios`／`expo run:android` が実行時に `expo prebuild` を暗黙実行してネイティブプロジェクトを再生成する。

### 2.4 Prebuild 運用
- `npx expo prebuild --clean` で `ios/` `android/` を再生成するため、生成前に Git 管理を徹底。
- Config Plugins を活用して Info.plist / entitlements / Gradle 設定を自動挿入。

---

## 3. Expo SDK と周辺ライブラリの機能マトリクス

| 項目 | Expo 公式サポート | 備考 |
| ---- | ----------------- | ---- |
| 通知（ローカル・プッシュ） | `expo-notifications` が Time Sensitive / Critical といった `interruptionLevel` を指定可能。`ios.entitlements` で `aps-environment` を設定する必要あり。 | Critical Alert 審査書類は別途必須。|
| 背景実行 / タスク | `expo-task-manager`、`expo-background-fetch` は **iOS で開発ビルド必須** かつスケジュールは OS の裁量（best effort）。BGTaskScheduler のような精度保証は不可。|
| 音声録音・再生 | `expo-av`、`expo-audio` が音声モード設定（`playsInSilentMode`, `shouldPlayInBackground` 等）を提供。LiveKit Expo プラグインで `AudioSession.startAudioSession()` が利用可能。| VoiceProcessingIO や細かな `AVAudioSessionCategory`／`Mode` 制御は LiveKit SDK の `setAppleAudioConfiguration` を介して達成可能だが、Expo 側で常時 VoiceProcessing を保証するにはネイティブレベルの調整が必要。|
| デバイスセンサー | 多数の Expo SDK が存在（Magnetometer 等）。ただし Android 12+ の高速更新には追加パーミッション設定が必要。|
| 暗号・セキュアストレージ | `expo-crypto` はハッシュ／乱数生成まで。AES-GCM 暗号化は提供されず、CryptoKit 相当を扱うには独自ネイティブモジュールが必要。|
| 課金 | RevenueCat の Expo ガイドあり。`react-native-purchases`＋ Expo Dev Client で対応可能。|
| 認証 | `expo-apple-authentication` による Sign in with Apple。Passkey は公式サポートなし。Clerk など外部 SDK のベータ機能（`@clerk/expo-passkeys`）に依存。|
| データベース | SQLite / MMKV / AsyncStorage レベル。Core Data・CloudKit は Expo SDK に存在せず、ネイティブ実装が必須。|
| OTA アップデート | `expo-updates`／EAS Update が提供。Bare ワークフローでも導入可能。|

---

## 4. Anicca iOS 要件とのギャップ分析

| 要件 | Expo での実現可否 | 詳細 |
| ---- | ------------------ | ---- |
| クリティカルアラート通知 | 条件付きで可能 | `expo-notifications` で `interruptionLevel: "critical"` を指定し、Config Plugin で entitlements 追加。しかし審査説明資料は自前で用意、Critical Alert 承認が下りない場合はフォールバック設計（Time Sensitive）が必要。|
| 起床 ±1 分プリロード（BGTaskScheduler） | 実質不可 | TaskManager/BackgroundFetch はトリガー時刻を OS が決定し、Expo から BGProcessingTaskRequest を直接発行できない。従って就寝前プリロードの SLA を満たせない。|
| 音声パイプライン（LiveKit＋VoiceProcessingIO） | 要追加作業 | LiveKit React Native SDK（Expo プラグイン対応）で入出力は可能。ただし iOS 固有の `AVAudioSessionCategoryPlayAndRecord`＋`mode=voiceChat`＋`VoiceProcessingIO` 有効化には `AudioSession.setAppleAudioConfiguration` を都度呼ぶ必要があり、ネイティブ実装より制御粒度が低い。|
| Core Data＋CloudKit | 不可 | Expo SDK に該当パッケージがなく、Expo Modules API で Swift 実装を丸ごと移植する必要がある。|
| 音声暗号化（CryptoKit AES-GCM） | 不可 | `expo-crypto` は AES-GCM を提供せず、ネイティブモジュール実装が必要。|
| RevenueCat＋StoreKit2 | 可能 | Expo Dev Client で `react-native-purchases` を利用し、EAS Build で配布可能。|
| Passkey＋Passkey 削除 | 部分的 | 公式サポートは未整備。Clerk Expo など外部 SDK 依存で、プロダクション要件を満たすには検証不足。|
| 観測性（OSLog） | 不可 | Expo から OSLog を直接出力する機能はなく、ネイティブモジュール実装が必要。|
| XCUITest E2E | 要工夫 | Bare ワークフローで生成される Xcode プロジェクトに対して手動で UITest ターゲットを追加すれば可能。ただし Expo の自動再生成後に差分が衝突するリスクがある。|

上記の通り、Expo で Anicca iOS の完全仕様を満たすには「Bare ワークフロー＋多数のカスタムネイティブモジュール」を開発する必要があり、Swift ネイティブ実装と同等のコストを要する。

---

## 5. Expo 導入時のリスクと緩和策

1. **ネイティブ API ギャップ**: BGTaskScheduler、Core Data、CryptoKit 等の Apple 専用機能は Expo SDK に存在しない。→ Expo Modules API で Swift 実装を自作し、`expo prebuild` に対して Config Plugin を併用する必要がある。
2. **タスクスケジューリングの不確実性**: `expo-background-fetch` は iOS で「best effort」であり、30 分〜数時間に遅延し得る。→ 起床体験の SLA を満たす保証なし。
3. **音声品質最適化**: LiveKit Expo プラグインはベース機能を提供するが、VoiceProcessingIO や遅延最適化には `AudioSession.configureAudio` を各フローで適切に呼び分ける設計が必要。→ Swift 実装で既に確立している制御ロジックを再構築する必要がある。
4. **プロジェクト運用フロー**: `expo prebuild` を挟むとネイティブディレクトリが再生成されるため、iOS 側の細かな設定（Signing、Push Capability など）が上書きされがち。→ Config Plugins をフル整備し、Git Hooks で `prebuild` の再生成を可視化する運用が必要。
5. **セキュリティ・暗号要件**: AES-GCM 暗号や鍵管理は Expo で標準提供されず、Secure Enclave 連携も不透明。→ Swift ネイティブ実装の方がソリューションが確立している。

---

## 6. Expo の利点（考慮の余地）

- クロスプラットフォーム展開（Android 版を同一コードベースで構築可能）。
- OTA update や EAS Update を活用したリリース頻度向上。
- JavaScript/TypeScript エコシステム、React UI 開発速度。
- LiveKit Agents など Web ベースの SDK 資産との親和性。

※ ただし Anicca の現在の iOS MVP では、外部 OS の拡張よりも iOS ネイティブ品質が優先されるため、利点よりもギャップが大きいと判断される。

---

## 7. 結論

物理的なデバイス起床制御、BGTaskScheduler を用いた前夜プリロード、Core Data／CloudKit のリアルタイム同期、CryptoKit ベースの音声暗号などの要件に対し、Expo Managed/Bare いずれのワークフローでも大幅なネイティブ拡張が必須となる。Expo を選択した場合でも Swift/Objective-C で多数のモジュールを実装し、Expo Modules API へ橋渡しする必要があるため、現行の Swift ネイティブ実装を継続・強化する戦略が最適である。

Expo は将来的な Android 版や軽量ユースケースには有効だが、Anicca iOSの現行 MVP で求められる SLA・セキュリティ・音声品質を満たすにはネイティブ開発を維持することを推奨する。

---

## 8. 付録

1. **主要コマンド**
   - `npx expo prebuild --clean` : ネイティブディレクトリ再生成。
   - `eas build --platform ios --profile production` : iOS 本番ビルド。
   - `eas workflow:run <workflow.yml>` : Workflows 実行。
2. **検証すべき外部 SDK**
   - LiveKit React Native Expo Plugin (`@livekit/react-native-expo-plugin`)
   - RevenueCat `react-native-purchases`
   - Clerk Expo Passkeys（ベータ）
3. **参考資料の整理**
   - Expo 公式ドキュメント（workflows, config plugins, notifications, background-fetch）
   - LiveKit Expo Quickstart
   - RevenueCat Expo ガイド
   - Expo Modules API チュートリアル

以上。
