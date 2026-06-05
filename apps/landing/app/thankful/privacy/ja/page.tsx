export const metadata = { title: 'プライバシーポリシー | Thankful - 感謝日記' };

export default function ThankfulPrivacyJA() {
  return (
    <main className="container mx-auto max-w-3xl px-4 py-24">
      <h1 className="text-3xl font-bold text-foreground">プライバシーポリシー</h1>
      <p className="mt-6 text-muted-foreground">
        本ポリシーは、iOSアプリ「Thankful - 感謝日記」（以下「本サービス」）において、個人情報を含むユーザーデータをどのように取り扱うかを定めるものです。
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">1. 事業者情報</h2>
      <p className="mt-3 text-muted-foreground">成田 大祐（個人事業主） / keiodaisuke@gmail.com</p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">2. 適用範囲</h2>
      <p className="mt-3 text-muted-foreground">
        本ポリシーは、本サービスおよびサポート対応に適用されます。また、本ポリシーへリンクする当方のWebページにも適用されます。
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">3. 取得する情報</h2>
      <ul className="mt-3 list-disc pl-6 text-foreground space-y-2">
        <li>デバイス識別子（identifierForVendor / device-id 等）</li>
        <li>感謝日記エントリーおよびアファメーションデータ（端末内に保存）</li>
        <li>アプリ内の設定・嗜好（例：通知設定、ストリークデータなど）</li>
        <li>アプリの利用状況（例：日記記録セッション、ストリーク、ペイウォール表示などのイベント）</li>
        <li>サブスクリプション状態（App Store / RevenueCat により管理される情報）</li>
        <li>サポート対応（問い合わせメール等）</li>
      </ul>

      <h2 className="mt-10 text-xl font-semibold text-foreground">4. 主な取得方法</h2>
      <ul className="mt-3 list-disc pl-6 text-foreground space-y-2">
        <li>ユーザーがアプリに入力した情報（日記エントリー、アファメーション）</li>
        <li>ユーザーの操作により自動生成されるイベント/ログ</li>
        <li>App Storeおよびサブスクリプション基盤（RevenueCat）から取得する情報</li>
        <li>サポート窓口への問い合わせ内容</li>
      </ul>

      <h2 className="mt-10 text-xl font-semibold text-foreground">5. 利用目的</h2>
      <ul className="mt-3 list-disc pl-6 text-foreground space-y-2">
        <li>本サービスの提供・改善</li>
        <li>ユーザーが許可したリマインダーの配信と、改善のための利用状況分析</li>
        <li>サブスクリプション状態の管理</li>
        <li>不具合解析、セキュリティ対策</li>
        <li>問い合わせ対応および重要なお知らせの送信</li>
      </ul>

      <h2 className="mt-10 text-xl font-semibold text-foreground">6. 第三者提供・委託</h2>
      <p className="mt-3 text-muted-foreground">
        本サービスの提供に必要な範囲で、以下の事業者へ情報を送信する場合があります。
      </p>
      <ul className="mt-3 list-disc pl-6 text-foreground space-y-2">
        <li>Apple（App Store課金、SKAdNetworkアトリビューション等のプラットフォーム機能）</li>
        <li>RevenueCat（サブスクリプション/エンタイトルメント管理）</li>
        <li>Mixpanel（プロダクト分析）</li>
      </ul>

      <h2 className="mt-10 text-xl font-semibold text-foreground">7. データの保存場所</h2>
      <p className="mt-3 text-muted-foreground">
        感謝日記のエントリーや個人のアファメーションは、端末内にのみ保存されます。サーバーへのアップロードは行いません。あなたの感謝データはプライベートに保たれます。
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">8. 取得しない情報</h2>
      <p className="mt-3 text-muted-foreground">
        本サービスは、HealthKitデータ、モーション/アクティビティデータ、スクリーンタイムデータにはアクセスしません。日記エントリーは端末内に保存され、サーバーには送信されません。
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">9. 保存期間と削除</h2>
      <ul className="mt-3 list-disc pl-6 text-foreground space-y-2">
        <li>日記エントリー：端末内に保存されます。アプリ削除時に削除されます</li>
        <li>端末内の識別子：アプリ削除時にリセットされます（IDFVの挙動）</li>
        <li>サポート履歴：対応および記録のため合理的な期間保管します</li>
      </ul>

      <h2 className="mt-10 text-xl font-semibold text-foreground">10. 安全管理措置</h2>
      <ul className="mt-3 list-disc pl-6 text-foreground space-y-2">
        <li>安全な通信（HTTPS/TLS）</li>
        <li>日記データは端末内のみに保存（サーバー送信なし）</li>
        <li>適切なアクセス制御および運用監視</li>
      </ul>

      <h2 className="mt-10 text-xl font-semibold text-foreground">11. 利用者の権利</h2>
      <p className="mt-3 text-muted-foreground">
        ユーザーは自身の情報の開示・訂正・利用停止・削除を請求できます。keiodaisuke@gmail.com までご連絡ください。
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">12. クッキー等</h2>
      <p className="mt-3 text-muted-foreground">ランディングページでは必要最小限のCookieを使用します。Cookie自体に個人情報は含まれません。</p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">13. 未成年者の利用</h2>
      <p className="mt-3 text-muted-foreground">13歳未満の方は保護者の同意がない限り本サービスを利用できません。</p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">14. 法令等の遵守</h2>
      <p className="mt-3 text-muted-foreground">個人情報保護法その他関連法令・ガイドラインを遵守します。</p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">15. 改定</h2>
      <p className="mt-3 text-muted-foreground">改定する場合は本ページで告知し、重要な変更はアプリ内通知等でお知らせします。</p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">16. 問い合わせ</h2>
      <p className="mt-3 text-muted-foreground">keiodaisuke@gmail.com までご連絡ください。</p>

      <p className="mt-12 text-right text-sm text-muted-foreground">最終更新日: 2026年2月24日</p>
    </main>
  );
}
