# Fastlane / App Store 提出でハマったことと学び（2026-02-14）

**目的:** 次に fastlane でリリース・審査提出するエージェントが同じ失敗をしないようにする。

---

## 1. Ruby / Bundler 環境の不一致

| 事象 | 学び・対処 |
|------|------------|
| `bundle exec fastlane test` や `fastlane full_release` で `Could not find 'bundler' (2.7.2)` が出る | Gemfile.lock は Bundler 2.7.2（Ruby ≥ 3.2 前提）。システム Ruby 2.6 では動かない。 |
| デフォルトシェルで `which ruby` が `/usr/bin/ruby`（2.6）になる | **fastlane 実行時は Ruby 3.2+ を明示する。** この環境では Homebrew Ruby を使う。 |
| 実行例 | `export PATH="/opt/homebrew/opt/ruby/bin:$PATH"` してから `bundle exec fastlane <lane>`。または `~/.rbenv/shims` が使える環境なら rbenv の Ruby を使う。 |

**ルール:** fastlane（test / release / submit_review）を叩く前に、`ruby -v` と `bundle -v` を確認する。Bundler 2.7.2 が要求されているなら Ruby 3.2+ のシェルで実行する。

---

## 2. wait_for_processing でループが抜けられない（Fastfile のバグ）

| 事象 | 学び・対処 |
|------|------------|
| ビルドが VALID になっても `✅ Build XXX processing complete!` の直後に `Error checking build: unexpected return` が出て、30秒ごとに同じログが繰り返す | Ruby の `loop do ... end` 内での `return` が、コンテキストによって **LocalJumpError（unexpected return）** になり、rescue されてループが続く。 |
| 修正済み | `aniccaios/fastlane/Fastfile` の `wait_for_processing` レーンで、**ループ内では `return build` を使わない。** `processed_build = build` を代入して `break` で抜け、ループ外で `processed_build` を返す。 |

**ルール:** fastlane のレーンで「同じメッセージが延々繰り返す」場合は、ループ内の `return` を疑い、`break` + 変数で抜けるように書き換える。

---

## 3. full_release がタイムアウトしたときの審査提出

| 事象 | 学び・対処 |
|------|------------|
| `full_release` が長時間でタイムアウトし、審査提出まで届かない | ビルドのアップロードまで成功していれば、**審査提出は単体レーンで実行できる。** |
| 手順 | ビルドが App Store Connect で VALID になっていることを前提に、`cd aniccaios && bundle exec fastlane submit_review` を実行する。 |

**ルール:** ビルドがすでにアップロード済み・VALID なら、`submit_review` だけを再実行すれば審査提出は完了する。

---

## 参照

| 項目 | 場所 |
|------|------|
| Fastlane レーン一覧・絶対ルール | `.claude/rules/tool-usage.md`（xcodebuild 直接禁止、fastlane を使う） |
| App Store Connect メタデータ等 | `.serena/memories/app_store_connect_workflow.md` |

---

**最終更新:** 2026-02-14（1.6.3 提出時のトラブルを反映）
