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
pip install -U instagrapi
python3 ig_local_post.py --login-sessionid
```

sessionid の取り方（Chrome）:

1. Chrome で instagram.com にいつも通りログインする
2. 表示 → 開発／管理 → デベロッパーツール
3. **Application** タブ → 左の **Cookies** → `https://www.instagram.com`
4. `sessionid` の Value をコピー（`数字%3A...` という形）

貼り付けると `session.json` が作られる。以降はこれを使い回す。

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
