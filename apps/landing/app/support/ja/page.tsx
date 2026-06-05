export const metadata = {
  title: 'サポート | Anicca',
  description: 'Aniccaのヘルプ - 音声で習慣を整えるコーチ'
};

export default function SupportJA() {
  return (
    <main className="container mx-auto max-w-3xl px-4 py-24">
      <h1 className="text-3xl font-bold text-foreground">サポート</h1>
      <p className="mt-6 text-muted-foreground">
        Aniccaについてお困りですか？お手伝いします。
      </p>

      <section className="mt-10">
        <h2 className="text-xl font-semibold text-foreground">お問い合わせ</h2>
        <p className="mt-3 text-muted-foreground">
          サポートに関するお問い合わせ、機能リクエスト、または一般的な質問については、以下までご連絡ください：
        </p>
        <p className="mt-4">
          <a 
            href="mailto:keiodaisuke@gmail.com" 
            className="text-primary hover:underline font-medium"
          >
            keiodaisuke@gmail.com
          </a>
        </p>
        <p className="mt-2 text-sm text-muted-foreground">
          通常、2営業日以内にご返信いたします。
        </p>
      </section>

      <section className="mt-10">
        <h2 className="text-xl font-semibold text-foreground">よくある質問</h2>
        <div className="mt-6 space-y-6">
          <div>
            <h3 className="font-semibold text-foreground">Aniccaはどのように動作しますか？</h3>
            <p className="mt-2 text-muted-foreground">
              Aniccaは、リアルタイムの会話を通じてあなたを導く音声ベースの習慣形成コーチです。
              起床時刻、トレーニングスケジュール、就寝習慣を設定してください。Aniccaは設定した時刻にリマインドし、
              音声会話を通じて良い習慣を築き、悪い習慣を断つお手伝いをします。
            </p>
          </div>

          <div>
            <h3 className="font-semibold text-foreground">Aniccaにはどのような権限が必要ですか？</h3>
            <p className="mt-2 text-muted-foreground">
              Aniccaは音声会話のためにマイクアクセス、設定した時刻にリマインドを送信するために通知権限が必要です。
              すべての権限はオンボーディング中にリクエストされます。
            </p>
          </div>

          <div>
            <h3 className="font-semibold text-foreground">データはプライベートですか？</h3>
            <p className="mt-2 text-muted-foreground">
              はい。Aniccaはプライバシー第一のアプローチを採用しています。音声データはリアルタイムで処理され、恒久保存されません。
              プロフィールデータは安全に保存され、パーソナライズされたガイダンスを提供するためにのみ使用されます。
              詳細については、<a href="/privacy/ja" className="text-primary hover:underline">プライバシーポリシー</a>をご覧ください。
            </p>
          </div>

          <div>
            <h3 className="font-semibold text-foreground">複数のデバイスでAniccaを使用できますか？</h3>
            <p className="mt-2 text-muted-foreground">
              はい。プロフィールと設定はアカウントを通じてデバイス間で同期されます。
              同じアカウントでiOSとデスクトップ（Mac）の両方のデバイスでAniccaを使用できます。
            </p>
          </div>
        </div>
      </section>

      <section className="mt-10">
        <h2 className="text-xl font-semibold text-foreground">その他のリソース</h2>
        <ul className="mt-4 space-y-2 text-muted-foreground">
          <li>
            <a href="/privacy/ja" className="text-primary hover:underline">プライバシーポリシー</a>
          </li>
          <li>
            <a href="/terms" className="text-primary hover:underline">利用規約</a>
          </li>
          <li>
            <a href="/faq" className="text-primary hover:underline">FAQ</a>
          </li>
          <li>
            <a href="https://github.com/Daisuke134/anicca.ai" className="text-primary hover:underline" target="_blank" rel="noreferrer">
              GitHubリポジトリ
            </a>
          </li>
        </ul>
      </section>
    </main>
  )
}










