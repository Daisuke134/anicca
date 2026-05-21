2026-02-12: `gog auth add keiodaisuke@gmail.com --services gmail,calendar,drive,contacts` を実行したが失敗。
エラー: `keychain access: keychain is locked and no TTY available for password prompt`。
対処: macOS の login keychain (`~/Library/Keychains/login.keychain-db`) をインタラクティブに unlock してから再実行し、`gog gmail search newer_than:1d --max 5` で動作確認する。