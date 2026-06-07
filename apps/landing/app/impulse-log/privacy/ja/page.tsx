export const metadata = { title: 'プライバシーポリシー | ImpulseLog' };

export default function ImpulseLogPrivacyJA() {
  return (
    <main className="container mx-auto max-w-3xl px-4 py-24">
      <h1 className="text-3xl font-bold text-foreground">プライバシーポリシー - ImpulseLog</h1>
      <p className="mt-4 text-sm text-muted-foreground">最終更新日: 2026年2月26日</p>

      <p className="mt-6 text-muted-foreground">
        本ポリシーは、ImpulseLog（以下「アプリ」）がユーザーデータをどのように取り扱うかを説明します。
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">1. 事業者情報</h2>
      <p className="mt-3 text-muted-foreground">成田大介（個人事業主）/ keiodaisuke@gmail.com</p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">2. 収集する情報</h2>
      <ul className="mt-3 list-disc pl-6 text-muted-foreground space-y-2">
        <li>デバイス識別子 - 分析および不正防止のため</li>
        <li>アプリ使用イベント - ログ記録、Paywall操作など</li>
        <li>サブスクリプション状態 - App Store / RevenueCat 経由で管理</li>
      </ul>

      <h2 className="mt-10 text-xl font-semibold text-foreground">3. 収集しない情報</h2>
      <ul className="mt-3 list-disc pl-6 text-muted-foreground space-y-2">
        <li>感情ログの内容やメモ（デバイスにのみローカル保存）</li>
        <li>健康データや生体データ</li>
        <li>位置情報</li>
        <li>連絡先、写真、マイク録音</li>
      </ul>

      <h2 className="mt-10 text-xl font-semibold text-foreground">4. 第三者サービス</h2>
      <ul className="mt-3 list-disc pl-6 text-muted-foreground space-y-2">
        <li><strong>RevenueCat</strong> - サブスクリプション管理（購入履歴）</li>
        <li><strong>Mixpanel</strong> - 匿名使用状況分析</li>
        <li><strong>Apple App Store</strong> - 決済処理</li>
      </ul>

      <h2 className="mt-10 text-xl font-semibold text-foreground">5. データ保持期間</h2>
      <p className="mt-3 text-muted-foreground">
        分析データは最大12ヶ月間保持されます。感情ログはデバイス上にのみ保存され、
        当社サーバーには送信されません。分析データの削除はお問い合わせください。
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">6. お問い合わせ</h2>
      <p className="mt-3 text-muted-foreground">
        メール: keiodaisuke@gmail.com
      </p>
    </main>
  );
}
