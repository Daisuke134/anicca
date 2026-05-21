# Makefile — l.md Bible 100%
# pipeline: xcodebuild test → xcresulttool → PIL process_screenshots.py
# Usage: make generate-store-screenshots

BUNDLE_ID := ai.anicca.app.ios

generate-store-screenshots:
	# 1. クリーンアップ
	rm -rf docs/screenshots/raw/* docs/screenshots/processed/* docs/screenshots/output.xcresult
	mkdir -p docs/screenshots/raw docs/screenshots/processed

	# 2. XCUITestでスクリーンショット撮影 → output.xcresult（l.md Step2）
	xcodebuild test \
	  -project aniccaios/aniccaios.xcodeproj \
	  -scheme aniccaios \
	  -destination 'platform=iOS Simulator,name=iPhone 17' \
	  -only-testing:aniccaiosUITests/ScreenshotTests \
	  -resultBundlePath docs/screenshots/output.xcresult \
	  -testLanguage ja

	# 3. xcresultから画像抽出（l.md Step3）
	python3 docs/screenshots/scripts/extract_screenshots.py \
	  docs/screenshots/output.xcresult \
	  docs/screenshots/raw

	# 4. PIL合成（l.md Step4）
	cd docs/screenshots && python3 scripts/process_screenshots.py

# デザイン変更のみ再実行（raw/ 撮影済み → 数秒で完了）
process-only:
	cd docs/screenshots && python3 scripts/process_screenshots.py
