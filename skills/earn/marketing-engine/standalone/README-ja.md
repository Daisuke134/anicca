# Instagram 自動投稿（1ファイル版）

`ig_local_post.py` = Mac のローカルから Instagram にリール／写真／カルーセルを自動投稿する。
依存は `instagrapi` だけ。本番運用しているループ（`../poster.py`）から、実際に効いている部分
＝ **セッションの扱い** だけを抜き出したもの。

## いま最初に知るべきこと（2026-07-29）

**パスワードでログインできないのは、あなたのせいでも、パスワードのせいでも、
アカウントのせいでもない。**

IG 側の変更で `accounts/login/` が壊れていて、正しいパスワードでも `BadPassword` が返る。
upstream で未解決:

- subzeroid/instagrapi#2732（open, 2026-07-19 頃から）
- 報告者の一人: 「instagrapi ではログインできないが、**同じアカウントに PC のブラウザからも
  スマホのアプリからも普通にログインできる**」

なので **アカウントを作り直しても直らない**。むしろパスワードログインを繰り返すほど
IG に怪しまれて悪化する。

## 正しい入口 = ブラウザの sessionid を移植する

壊れているログイン API を通らずに済む。

```bash
pip3 install -U instagrapi browser_cookie3
python3 ig_local_post.py --login-sessionid
```

Chrome（または Safari / Firefox）で instagram.com にログインしてあれば、
**sessionid はスクリプトが Cookie から自動で拾う**。手作業なし。
macOS は初回だけ「Chrome Safe Storage へのアクセス」許可が出るので「常に許可」を押す。

自動で拾えなかった時だけ手貼りにフォールバックする:
Chrome → デベロッパーツール → Application → Cookies → `https://www.instagram.com` →
`sessionid` の Value（`数字%3A...` の形）を貼る。

成功すると `session.json` が作られる。以降はこれを使い回す。

> sessionid はパスワードと同じ強さの資格情報。人に送らない・コミットしない。
> スクリプトは画面に表示せず、`session.json` を 600 で保存する。

## 鉄則（破ると詰む）

| ルール | 理由 |
|---|---|
| `session.json` を消さない | 最初のセッション（golden session）が全て。死ぬと復旧が難しい |
| 一度入れたら二度とパスワードログインしない | 再ログインは challenge を踏んでアカウントを半分殺す |
| `ChallengeRequired` が出たら諦める | リトライすると悪化する。そのアカウントは自動投稿に使えない |
| 新規アカウントで即投稿しない | 作りたてで投稿すると止まる。数日は普通に使って寝かせる |

本番ループが安定して毎日投稿できている理由は、この 4 つを守っているからで、
特別なライブラリを使っているからではない（同じ `instagrapi`）。

## 投稿

```bash
python3 ig_local_post.py --check                                  # 状態確認
python3 ig_local_post.py --post reel.mp4 --caption-file cap.txt   # リール
python3 ig_local_post.py --post photo.jpg --caption "本文"         # 写真
python3 ig_local_post.py --post a.jpg,b.jpg,c.jpg --caption "本文" # カルーセル
```

成功すると最後に投稿 URL を出す。
