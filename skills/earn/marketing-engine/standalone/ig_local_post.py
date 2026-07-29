#!/usr/bin/env python3
"""ig_local_post.py — 1ファイル完結の Instagram 自動投稿（instagrapi）

本番ループ（skills/earn/marketing-engine/poster.py）から「golden session ドクトリン」だけを
抜き出した個人用スクリプト。依存は instagrapi のみ。

★ 2026-07-29 の重要な変更 ★
  IG 側の変更で `POST /api/v1/accounts/login/`（＝パスワードログイン）が壊れており、
  パスワードが正しくても `BadPassword` が返る。upstream で未解決（subzeroid/instagrapi#2732、
  2026-07-19 頃から発生。ブラウザ／公式アプリでは同じ資格情報で正常にログインできる）。
  → 本スクリプトの既定の入口は `--login-sessionid`（ブラウザの sessionid を移植）。
    パスワードログインは壊れている間は使わない。

## セッションの鉄則（これを破ると詰む）
  1. 最初に取れたセッション（golden session）を死なせない。session.json を消さない。
  2. 一度使えたら、二度とパスワードログインしない。再ログインは challenge を踏んで
     アカウントを半分殺す。作り直しても同じことをすれば同じ結果になる。
  3. ChallengeRequired が出たアカウントは諦める。リトライしない。

## 使い方
    pip install -U instagrapi
    python3 ig_local_post.py --login-sessionid          # 初回だけ（sessionid を貼る）
    python3 ig_local_post.py --check                    # ログインできているか確認
    python3 ig_local_post.py --post reel.mp4 --caption-file cap.txt
    python3 ig_local_post.py --post a.jpg,b.jpg --caption "本文"

## sessionid の取り方（Mac / Chrome）
    1. Chrome で instagram.com にいつも通りログイン
    2. 表示 → 開発／管理 → デベロッパーツール
    3. Application タブ → 左の Cookies → https://www.instagram.com
    4. `sessionid` の Value をコピー（`数字%3A...` という形）
  ※ sessionid はパスワードと同じ強さの資格情報。人に見せない・貼らない・コミットしない。
"""
import argparse
import getpass
import json
import os
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
SESSION_FILE = os.path.join(HERE, "session.json")


def log(msg):
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}")


def die(msg, code=1):
    log(f"中止: {msg}")
    sys.exit(code)


def new_client():
    from instagrapi import Client

    cl = Client()
    cl.delay_range = [2, 5]
    return cl


def save_session(cl):
    cl.dump_settings(SESSION_FILE)
    os.chmod(SESSION_FILE, 0o600)
    log(f"セッションを保存: {SESSION_FILE}（このファイルは絶対に消さないこと）")


def load_session():
    """tier1: 保存済みセッションを読み、読み取り専用の呼び出しで生死を確認する。

    ここで失敗しても絶対にパスワードログインへ落ちない（それが golden session を殺す）。
    """
    from instagrapi.exceptions import ChallengeRequired

    if not os.path.exists(SESSION_FILE):
        die("session.json が無い。まず `--login-sessionid` を実行する。")

    cl = new_client()
    cl.load_settings(SESSION_FILE)
    try:
        info = cl.account_info()  # 読み取り専用
    except ChallengeRequired:
        die(
            "ChallengeRequired。このアカウントは自動投稿には使えない状態。"
            "再ログインを試さないこと（悪化する）。"
        )
    except Exception as e:
        die(
            f"保存済みセッションが使えない: {type(e).__name__}: {e}\n"
            "        → パスワードで入り直さないこと。ブラウザで instagram.com に\n"
            "          ログインし直してから `--login-sessionid` をやり直す。"
        )
    log(f"ログイン確認 OK: @{info.username}")
    return cl


def cmd_login_sessionid():
    """ブラウザの sessionid を移植する。壊れている login エンドポイントを通らない。"""
    log("Chrome の DevTools → Application → Cookies → instagram.com → sessionid をコピー")
    sessionid = getpass.getpass("sessionid を貼り付け（画面には表示されません）: ").strip()
    if len(sessionid) < 30 or not sessionid[:1].isdigit():
        die("sessionid の形式が違う（`数字%3A...` の形をそのまま貼る）")

    cl = new_client()
    if not cl.login_by_sessionid(sessionid):
        die("sessionid でのログインに失敗。ブラウザで入り直して取り直す。")
    info = cl.account_info()
    log(f"ログイン成功: @{info.username}")
    save_session(cl)
    log("以降このセッションを使い回す。パスワードログインは二度と実行しないこと。")


def cmd_login_password():
    """パスワードログイン。2026-07-29 現在 upstream で壊れている。"""
    log("警告: パスワードログインは現在 IG 側で壊れている（instagrapi#2732）。")
    log("      正しいパスワードでも BadPassword が返る。`--login-sessionid` を使うこと。")
    ans = input("それでも実行する？ [y/N]: ").strip().lower()
    if ans != "y":
        die("中止した（正しい判断）。")
    if os.path.exists(SESSION_FILE):
        die("session.json が既にある。再ログインはアカウントを壊す。--check を使う。")

    from instagrapi.exceptions import BadPassword, ChallengeRequired

    username = input("Instagram ユーザー名 (@なし): ").strip()
    password = getpass.getpass("パスワード（画面には表示されません）: ")
    cl = new_client()
    try:
        cl.login(username, password)
    except BadPassword:
        die(
            "BadPassword。パスワードが違うとは限らない（instagrapi#2732 の既知の障害）。\n"
            "        ブラウザでは同じ資格情報でログインできるはず。"
            "`--login-sessionid` に切り替える。"
        )
    except ChallengeRequired:
        die("ChallengeRequired。このアカウントでの自動ログインは諦める。")
    save_session(cl)


def cmd_check():
    load_session()
    log("このアカウントは投稿できる状態。")


def cmd_post(target, caption):
    from instagrapi.exceptions import ChallengeRequired, FeedbackRequired

    paths = [p.strip() for p in target.split(",") if p.strip()]
    for p in paths:
        if not os.path.exists(p):
            die(f"ファイルが無い: {p}")

    cl = load_session()
    try:
        if len(paths) == 1 and paths[0].lower().endswith((".mp4", ".mov")):
            log(f"リールを投稿: {paths[0]}")
            media = cl.clip_upload(paths[0], caption)
        elif len(paths) == 1:
            log(f"写真を投稿: {paths[0]}")
            media = cl.photo_upload(paths[0], caption)
        else:
            log(f"カルーセルを投稿: {len(paths)} 枚")
            media = cl.album_upload(paths, caption)
    except ChallengeRequired:
        die("ChallengeRequired。投稿はできなかった。リトライしないこと。")
    except FeedbackRequired as e:
        die(f"FeedbackRequired（IG による一時的な動作制限）: {e}。数日空ける。")

    url = f"https://www.instagram.com/p/{media.code}/"
    log(f"投稿完了: {url}")
    print(json.dumps({"ok": True, "post_url": url, "media_id": str(media.pk)}))


def main():
    ap = argparse.ArgumentParser(description="Instagram 自動投稿（instagrapi / 1ファイル版）")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--login-sessionid", action="store_true", help="ブラウザの sessionid でログイン（推奨）")
    g.add_argument("--login", action="store_true", help="パスワードでログイン（現在壊れている）")
    g.add_argument("--check", action="store_true", help="ログイン状態を確認")
    g.add_argument("--post", metavar="FILE[,FILE...]", help="mp4 / 画像（複数はカンマ区切り）")
    ap.add_argument("--caption", default="", help="本文")
    ap.add_argument("--caption-file", help="本文をファイルから読む")
    args = ap.parse_args()

    caption = args.caption
    if args.caption_file:
        with open(args.caption_file, encoding="utf-8") as f:
            caption = f.read().strip()

    if args.login_sessionid:
        cmd_login_sessionid()
    elif args.login:
        cmd_login_password()
    elif args.check:
        cmd_check()
    else:
        cmd_post(args.post, caption)


if __name__ == "__main__":
    main()
