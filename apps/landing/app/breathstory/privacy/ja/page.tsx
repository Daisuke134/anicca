export const metadata = { title: 'プライバシーポリシー | BreathStory - 呼吸ガイドストーリー' };

export default function BreathStoryPrivacyJA() {
  return (
    <main className="container mx-auto max-w-3xl px-4 py-24">
      <h1 className="text-3xl font-bold text-foreground">プライバシーポリシー</h1>
      <p className="mt-6 text-muted-foreground">
        本ポリシーは、BreathStory iOSアプリ（以下「本サービス」）における個人情報を含むユーザーデータの取り扱いを説明します。
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">1. 事業者情報</h2>
      <p className="mt-3 text-muted-foreground">成田大介（個人事業主）/ keiodaisuke@gmail.com</p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">2. 適用範囲</h2>
      <p className="mt-3 text-muted-foreground">
        本ポリシーは本サービスおよび関連するサポート通信に適用されます。
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">3. 収集する情報</h2>
      <p className="mt-3 text-muted-foreground">
        BreathStoryはプライバシーを最優先に設計されています。収集するデータは最小限です：
      </p>
      <ul className="mt-3 list-disc pl-6 text-foreground space-y-2">
        <li>サブスクリプション状態情報（App Store / RevenueCat経由で管理）</li>
        <li>端末内にローカル保存されるアプリ設定（連続使用日数、オンボーディング完了状態）</li>
        <li>サポートへの問い合わせ内容</li>
      </ul>
      <p className="mt-3 text-muted-foreground">
        分析イベント、クラッシュレポート、広告識別子（IDFA）、その他の個人を特定できる情報は<strong>収集しません</strong>。
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">4. 収集方法</h2>
      <ul className="mt-3 list-disc pl-6 text-foreground space-y-2">
        <li>サブスクリプション検証のためAppleから受信する情報（RevenueCat経由）</li>
        <li>サポートへのお問い合わせ</li>
      </ul>

      <h2 className="mt-10 text-xl font-semibold text-foreground">5. 利用目的</h2>
      <ul className="mt-3 list-disc pl-6 text-foreground space-y-2">
        <li>サブスクリプション管理とプレミアムコンテンツの解放</li>
        <li>サポート対応および重要なお知らせの送信</li>
      </ul>

      <h2 className="mt-10 text-xl font-semibold text-foreground">6. 第三者サービス</h2>
      <p className="mt-3 text-muted-foreground">
        本サービスの運営に以下のサービスを使用しています：
      </p>
      <ul className="mt-3 list-disc pl-6 text-foreground space-y-2">
        <li>Apple（App Store課金および関連プラットフォームサービス）</li>
        <li>RevenueCat（サブスクリプション管理 - 匿名化された購入レシートのみ受信）</li>
      </ul>
      <p className="mt-3 text-muted-foreground">
        分析SDK、広告ネットワーク、クラッシュレポートサービス、トラッキングフレームワークは使用しません。
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">7. データの保存</h2>
      <p className="mt-3 text-muted-foreground">
        すべてのユーザー設定（連続使用日数、サブスクリプション状態キャッシュ、オンボーディング状態）はAppleのUserDefaultsを使用してお使いの端末にローカル保存されます。このデータは当社のサーバーには送信されません。BreathStoryはバックエンドサーバーを持ちません。
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">8. 収集しない情報</h2>
      <p className="mt-3 text-muted-foreground">
        BreathStoryは以下の情報を収集・アクセスしません：HealthKitデータ、位置情報、カメラ・マイクデータ、連絡先、フォトライブラリ、広告識別子（IDFA）、分析・行動データ。
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">9. 保持期間と削除</h2>
      <ul className="mt-3 list-disc pl-6 text-foreground space-y-2">
        <li>端末内ローカルデータ：アプリを削除すると同時に削除されます</li>
        <li>サポート履歴：記録維持のため合理的な期間保存されます</li>
      </ul>

      <h2 className="mt-10 text-xl font-semibold text-foreground">10. セキュリティ</h2>
      <ul className="mt-3 list-disc pl-6 text-foreground space-y-2">
        <li>すべてのデータは端末内にのみ保存（サーバー送信なし）</li>
        <li>サブスクリプション検証はRevenueCatのセキュアなインフラを使用</li>
      </ul>

      <h2 className="mt-10 text-xl font-semibold text-foreground">11. ユーザーの権利</h2>
      <p className="mt-3 text-muted-foreground">
        すべてのデータを削除するには：端末からBreathStoryを削除してください。サポート関連データの削除については keiodaisuke@gmail.com までご連絡ください。
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">12. 未成年者</h2>
      <p className="mt-3 text-muted-foreground">
        BreathStoryは4歳以上対象で全年齢に適しています。13歳未満の方から個人情報を意図的に収集することはありません。
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">13. ポリシーの改訂</h2>
      <p className="mt-3 text-muted-foreground">
        本ポリシーはサービスの進化に伴い更新される場合があります。重要な変更はこのページでお知らせします。変更後も本サービスを継続利用することで変更への同意とみなします。
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">14. お問い合わせ</h2>
      <p className="mt-3 text-muted-foreground">
        本ポリシーに関するご質問：keiodaisuke@gmail.com
      </p>

      <p className="mt-10 text-sm text-muted-foreground">最終更新：2026年3月</p>

      <div className="mt-8 border-t border-border pt-6 text-sm text-muted-foreground">
        <a href="/breathstory/privacy/en" className="underline hover:text-foreground">Privacy Policy (English)</a>
      </div>
    </main>
  );
}
