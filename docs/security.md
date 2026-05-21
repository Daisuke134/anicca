はじめに
Electronを用いたMacアプリ開発は、Web技術の知識を活かしてクロスプラットフォームなデスクトップアプリを手軽に作れる点が魅力です。しかし、デスクトップアプリならではのセキュリティリスクも多く存在します。

本記事では、Electronアプリ開発におけるセキュリティ対策として特に見落としがちな以下の2点について解説します。

アプリのソースコードやシークレット情報が漏洩するリスク
アプリの認可フローにおけるトークン窃取のリスク
前提として、Electronアプリは配布時にtarやasar形式でパッケージ化されますが、これらは簡単に展開・解析できるため、 アプリに含めたコードやシークレット情報は基本的にユーザーに全て晒される 前提で設計・開発する必要があります。
特にハードコーディングしたAPIキーやパスワードなどは絶対に含めないよう注意しましょう。



Electronアプリの中にある、アプリ名/Contents/Resources/app.asarを展開すると、アプリのソースコードや設定ファイルが丸見えになります。



実際に解答するコマンド👇

asar extract app.asar app/

これにより、悪意のあるユーザーがアプリの内部構造を解析し、セキュリティホールを突いたり、個人情報を盗み出したりする可能性があります。

アプリの保存内容が漏洩するリスク
アプリの保存内容が漏洩するリスクは、特に個人情報や機密情報を扱うアプリにとって深刻な問題です。例えば、ユーザーのパスワードやクレジットカード情報が漏洩すると、悪意のある第三者による不正利用や詐欺行為が発生する可能性があります。

特にローカルで利用するデスクトップアプリの場合、データは他のアプリからもアクセス可能な場所に保存されることが多く、セキュリティ対策が不十分な場合、データ漏洩のリスクが高まります。したがって、アプリの保存内容を適切に暗号化し、アクセス制御を強化することが重要です。

ElectronのsafeStorageを使った安全なシークレット管理
ElectronのsafeStorageは、OSのセキュアなキーチェーン（macOSの場合はKeychain）を利用して、アプリごとに暗号化・復号化を行うAPIです。
この仕組みの最大の特徴は、暗号化・復号化に使われる鍵がOSのユーザーごと・アプリごとに管理されており、Macの場合、他のアプリやプロセスからはアクセスできない点です。

具体的な仕様
safeStorage.encryptString(str)で文字列を暗号化し、復号化はsafeStorage.decryptString(buffer)で行います。
暗号化されたデータはアプリごとに異なる鍵で保護されます。
OSのキーチェーンや資格情報ストアを利用するため、他のアプリやプロセスからは復号できません。
コード例
毎回、safeStorageを使って暗号化・復号化するのは時間がかかるため、アプリ起動時に一度だけUUIDを生成し、safeStorageで暗号化して保存します。次回以降はこのUUIDを使って別途、node:cryptoのcreateHashを使ってハッシュ化したものを保存します。これにより、UUIDを直接保存することなく、セキュリティを強化できます。

import { app, safeStorage } from 'electron'
import { randomUUID, createHash } from 'node:crypto'
import { writeFileSync, existsSync, readFileSync } from 'node:fs'
import path from 'path'

export const generateOrRetrieveSystemKey = () => {
  // このencryption.txtは外部に漏れたとしても復元が不可能
  const keyFile = path.join(app.getPath('userData'), 'encryption.txt')

  if (existsSync(keyFile)) {
    const base64 = readFileSync(keyFile, 'utf-8')
    const buffer = Buffer.from(base64, 'base64')
    const decryptedKey = safeStorage.decryptString(buffer)
    if (decryptedKey) {
      return decryptedKey
    }
  }

  const randomId = randomUUID()
  const buffer = safeStorage.encryptString(randomId)
  const base64 = buffer.toString('base64')

  writeFileSync(keyFile, base64)

  return randomId
}

この関数は、アプリごとに一意なシークレット（UUID）を生成し、safeStorageで暗号化して保存します。
復号時もsafeStorageを使うため、他のアプリやプロセスからはこのシークレットを取得できません。

次にsafeStorageで守られたシークレットを使ったAES-256-CBC暗号化を行います。

なぜ二重の暗号化が必要か？

safeStorageは「アプリ内で使うシークレットの保管」には最適ですが、大量のデータやDBの全データを直接safeStorageで暗号化・復号するのは現実的ではありません。
そこで、safeStorageで守られたシークレットをAES-256-CBCの鍵として利用し、アプリ内の他のデータ（例：DBのカラム値など）を暗号化します。

AES-256-CBCの仕様
256ビット（32バイト）の鍵と、16バイトの初期化ベクトル（IV）を利用
暗号化ごとにランダムなIVを生成し、暗号文と一緒に保存
復号時はIVと暗号文を分離して利用
コード例
import { createCipheriv, createDecipheriv, randomBytes, createHash } from 'node:crypto'

export const encryptString = (str: string) => {
  const keyString = generateOrRetrieveSystemKey()
  const key = createHash('sha256').update(keyString).digest() // 32 bytes
  const iv = randomBytes(16) // 16 bytes for AES-256-CBC

  const cipher = createCipheriv('aes-256-cbc', key, iv)
  let encrypted = cipher.update(str, 'utf8', 'base64')
  encrypted += cipher.final('base64')

  // 返却値は「IV:暗号文」のbase64連結
  const result = iv.toString('base64') + ':' + encrypted
  return result
}

export const decryptString = (data: string) => {
  const keyString = generateOrRetrieveSystemKey()
  const key = createHash('sha256').update(keyString).digest() // 32 bytes

  const [ivBase64, encrypted] = data.split(':')
  const iv = Buffer.from(ivBase64, 'base64')

  const decipher = createDecipheriv('aes-256-cbc', key, iv)
  let decrypted = decipher.update(encrypted, 'base64', 'utf8')
  decrypted += decipher.final('utf8')

  return decrypted
}

流れ的には以下の画像のようになります。



アプリの認可フローにおけるトークン窃取のリスク
次に気にすべきは、アプリの認証フローです。
アプリでWeb APIを使って認証して利用するものは多いですが、その時に見落としがちなのが認証フローのセキュリティです。
アプリ独自のユニバーサルリンクを利用して認証を行う場合、特に注意が必要です。
第三者のアプリが同じユニバーサルリンクを利用することで、リダイレクト先を操作されるリスクがあります。

この時にリダイレクト先ですぐにtokenを取得するのではなく、アプリに戻るための一時的なトークンを発行し、アプリ側でトークンを交換することでセキュリティを強化できます。
この方法はPKCE（Proof Key for Code Exchange）と呼ばれ、OAuth 2.0のセキュリティ強化策として広く利用されています。

フロー概要


アプリ側でランダムなcode_verifierを生成し、ハッシュ化したcode_challengeを認可リクエストに含める
認可サーバーはcode_challengeを記録し、認可コードを発行
認可サーバーからのリダイレクト後アプリ側では認可コードとcode_verifierを使ってトークンをリクエスト
サーバーはcode_verifierを検証し、トークンを発行
こうすることで、第三者のアプリはcode_verifierを知らないため、認可コードを使ってトークンを取得できません。

コード例
let code_verifier: string | null = null
let code_challenge: string | null = null

// 認可リクエストを行う
ipcMain.handle('login', async () => {
  code_verifier = crypto.randomBytes(32).toString('base64url')
  code_challenge = crypto.createHash('sha256').update(code_verifier).digest('base64url')
  // code_challengeは認可リクエストに含める
  const authUrl = `${import.meta.env.VITE_API_ENDPOINT}/signup?code_challenge=${code_challenge}&code_challenge_method=S256`
  shell.openExternal(authUrl)
})

// 認可サーバーからのリダイレクト後の処理
app.on('open-url', async (_event, url) => {
  const code = new URL(url).searchParams.get('code')
  if (code && code_verifier) {
    // 認可コードとcode_verifierを使ってトークンを取得
    await authUser(code, code_verifier)
    mainWindow.webContents.send('login-success')
    code_verifier = null
  }
})

まとめ
本記事では、Electronアプリ開発におけるセキュリティ対策として、暗号化の実装例やPKCE認証フローの安全な設計について解説しました。これらの対策を講じることで、アプリのセキュリティを強化し、ユーザーのデータを守ることができます。
Webサービスの経験しかないと、デスクトップアプリのセキュリティ対策は疎かになりがちです。

この他にもWebアプリでは当たり前のように行なっているXSSやその他のセキュリティ対策も考慮する必要があります。
## 運用ポリシー（追記）
- デスクトップブリッジ共有鍵（BRIDGE_AUTH_TOKEN）はアプリ初回起動時に生成し、Electron safeStorage で暗号化保存する。配布バイナリやCIの extraMetadata には絶対に埋め込まない。
- Proxy API へのツールリクエストはすべて短命JWT（Authorizationヘッダー）を必須とし、`userId` が送られてきた場合はサーバー側で `token.sub` と一致しないリクエストを拒否する。

## Supabase 秘密情報の扱い
- Supabase の URL / anon key はリポジトリには含めず、CI の Secrets から electron-builder に注入する。
- ローカル開発時は各自の .env で staging 用を設定する。
