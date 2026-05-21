# ビルド/テストコマンド

## iOS
cd aniccaios && FASTLANE_SKIP_UPDATE_CHECK=1 FASTLANE_OPT_OUT_CRASH_REPORTING=1 fastlane test

## API
cd apps/api && npm test
