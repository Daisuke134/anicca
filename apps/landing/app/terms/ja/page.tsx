export const metadata = { title: '利用規約 | Anicca' };

export default function TermsJA() {
  return (
    <main className="container mx-auto max-w-3xl px-4 py-24">
      <h1 className="text-3xl font-bold text-foreground">利用規約</h1>
      <p className="mt-6 text-muted-foreground">
        本規約は、iOSアプリ「Anicca」（以下「本サービス」）の利用条件を定めるものです。ユーザーは本規約に同意のうえ本サービスを利用するものとします。
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">1. 事業者情報</h2>
      <p className="mt-3 text-muted-foreground">成田 大祐（個人事業主） / keiodaisuke@gmail.com</p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">2. サービス概要</h2>
      <p className="mt-3 text-muted-foreground">
        本サービスは、通知およびアプリ内コンテンツを通じて行動変容を支援するものです。医療・心理・法律その他の専門的助言を提供するものではありません。
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">3. アカウント</h2>
      <p className="mt-3 text-muted-foreground">
        本サービスはサインインなしでも利用できます。Sign in with Apple を利用する場合、端末およびアカウントの管理はユーザーの責任で行うものとします。
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">4. 課金（iOS）</h2>
      <p className="mt-3 text-muted-foreground">
        サブスクリプション（提供される場合）は、App Storeを通じてApple IDに課金されます。解約および返金はAppleの規約・手続に従います。
      </p>
      <p className="mt-3 text-muted-foreground">
        参照:{' '}
        <a className="text-primary underline" href="https://www.apple.com/legal/internet-services/itunes/dev/stdeula/" target="_blank" rel="noreferrer">
          Apple Standard EULA
        </a>
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">5. 禁止事項</h2>
      <ul className="mt-3 list-disc pl-6 text-foreground space-y-2">
        <li>法令または公序良俗に違反する行為</li>
        <li>本サービスの運営を妨害する行為、不正アクセス</li>
        <li>リバースエンジニアリング、濫用的な利用</li>
        <li>第三者の知的財産権・プライバシー等を侵害する行為</li>
      </ul>

      <h2 className="mt-10 text-xl font-semibold text-foreground">6. 知的財産権</h2>
      <p className="mt-3 text-muted-foreground">
        本サービスに関する知的財産権は当方または正当な権利者に帰属します。許諾なく複製・改変等をしてはなりません。
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">7. 免責・責任制限</h2>
      <p className="mt-3 text-muted-foreground">
        本サービスは現状有姿で提供されます。法令で認められる範囲で、当方は間接損害・特別損害等について責任を負いません。
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">8. 規約・サービスの変更</h2>
      <p className="mt-3 text-muted-foreground">
        当方は必要に応じて本サービスまたは本規約を変更できます。重要な変更は本ページへの掲示および／またはアプリ内で告知します。
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">9. 準拠法・裁判管轄</h2>
      <p className="mt-3 text-muted-foreground">
        本規約は日本法を準拠法とし、本サービスに関して紛争が生じた場合は東京地方裁判所または東京簡易裁判所を第一審の専属的合意管轄裁判所とします。
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">10. 問い合わせ</h2>
      <p className="mt-3 text-muted-foreground">keiodaisuke@gmail.com までご連絡ください。</p>

      <p className="mt-12 text-right text-sm text-muted-foreground">最終更新日: 2026年1月26日</p>
    </main>
  );
}

