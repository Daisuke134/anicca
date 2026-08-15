# domain-skill: browser / CDP

ブラウザ操作で**実際に詰まった**事実だけ。全部 2026-08-05 に実測。

---

## クリックが効かない時

- **ネイティブのファイル選択ダイアログは `el.click()` では開かない。**
  信頼されないイベントだから。順序は:
  1. `Page.setInterceptFileChooserDialog(enabled=true)`
  2. `Input.dispatchMouseEvent`（mousePressed → mouseReleased）で**実マウスクリック**
  3. `Page.fileChooserOpened` を待つ
  4. `DOM.setFileInputFiles(backendNodeId=...)`
  → Meta Business Suite の「写真・動画を追加」はこれでしか通らない。

- クリック座標は**直前の `getBoundingClientRect()`** から取る。
  `captureBeyondViewport` のスクショ座標を使うとズレる。要素を1つ埋めるとレイアウトが動くので毎回測り直す。

- 押す前に `document.elementFromPoint(x,y)` で**当たり判定**を確認する。
  モーダルの backdrop がクリックを吸っていることがある。

## 要素が見つからない時

- **入れ子 Shadow DOM を疑う。** `document.querySelectorAll` は貫通しない。
  LINE Business ID は `toly-button > i18n-message > #shadow-root` にテキストがあり、
  `innerText` は空文字を返す。shadow を再帰的に辿ってテキストを集める。
- テキスト照合は**完全一致**にする。部分一致だと別のボタンを掴む。
  実例: `/メールアドレス/` が「LINEの**メールアドレス**でログイン」（別フロー）にヒットした。

## レンダラが固まった時

- ★入力済みフォームがあるページから `Page.navigate` すると beforeunload が出て
  **レンダラのメインスレッドが停止し、CDP が全滅する**★（`Runtime.evaluate` すら返らない）。
  → 入力途中の composer からは絶対にナビゲートしない。1回の実行で入力〜送信まで通す。
  → 固まったら `GET /json/close/<targetId>` でタブごと閉じる（レンダラの応答が要らない）。

- `Runtime.evaluate` に `Object reference chain is too long` が出たら、
  `window.__x = [DOM要素...]` のように**DOM 配列をグローバルに保持している**。
  毎回セレクタで引き直す。

- `Tab.call()` が応答を待つ間に届いたイベント（`Fetch.requestPaused` 等）は
  **捨てずにキューへ退避する**。捨てると傍受したリクエストが宙吊りになる。

## 入力できないウィジェット

- Meta Business Suite の**時刻ウィジェット**は次の4つを全部拒否する（未解決）:
  数字キーイベント / 矢印キー / `Input.insertText` / value setter。
  → 日付だけ設定して既定時刻で運用する。時刻は予約一覧から個別編集する。

## セッション

- ★セッションはサーバー側で切られる。ブラウザを開いたままでも切れる。★
  facebook.com で `datr`（端末ID・2年）は残るのに `c_user`/`xs` だけ消えるのが典型。
  → 「ブラウザは生きているのになぜ」で止まらない。**再ログインは通常運転**。
- 切り分けは `Network.getAllCookies` で**在否**を見るのが最短（値は読まない）。
- cookie 名は思い込まない。LINE は `line_bid` ではなく **`RSESSION`** だった。

## 共有ブラウザ

- 触る前に必ず `browser-guard.sh acquire <identity>`、終わったら `release`。
- ★`interactive:dais`(:9222) と `coconala:kosuke`(:9223) は別ブラウザ。★
  Meta のセッションは :9222、ココナラと LINE は :9223 にある。
- 自分が作ったタブ以外に触らない。`connect_over_cdp` は既存タブ全部に attach して壊す。
  `/json/new` で自分のタブを作り、その websocket だけを掴む（`/json/new` は Chrome 111+ で **PUT**）。
- instagram.com は両プロファイルとも**凍結アカウントの cookie** が居座り
  `/accounts/suspended/` へ攫われる。公開ページは `Target.createBrowserContext` の
  使い捨て文脈（cookie 無し）で開く。

## 認証

- **REQUIRED:** use [`google-login`](../../google-login/SKILL.md) for Google/Gmail/OAuth/device login（Hermes Codex を含む）。
  このページへ個人の識別子やKeychain参照を複製しない。
- プラットフォーム固有の通常ログイン画面だけを使う。復旧・リセット・待機・ログアウト・アカウントロック変更が表示されたら、画面を記録して停止する。
