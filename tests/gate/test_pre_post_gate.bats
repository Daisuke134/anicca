#!/usr/bin/env bats

PPG="$HOME/.openclaw/skills/_shared/lib/pre-post-gate.sh"

setup() {
  export FAKE_INT=cmnit95mg015rrm0ye5vm8dhl
  TMPDIR_T="$BATS_TEST_TMPDIR"
}

@test "ppg_check blocks JA caption with --language en (TikTok incident)" {
  printf 'これは日本語のキャプションです' > "$TMPDIR_T/cap.txt"
  run "$PPG" --platform TikTok --account "@anicca.en" \
    --integration-id FAKE_INT --language en \
    --caption-file "$TMPDIR_T/cap.txt" --asset-manifest ""
  [ "$status" -eq 2 ]
  echo "$output" | grep -qF "lang mismatch"
}

@test "ppg_check allows EN caption with --language en" {
  printf 'Hello world from Anicca' > "$TMPDIR_T/cap.txt"
  run "$PPG" --platform TikTok --account "@anicca.en" \
    --integration-id FAKE_INT --language en \
    --caption-file "$TMPDIR_T/cap.txt" --asset-manifest ""
  [ "$status" -eq 0 ]
}

@test "ppg_check blocks missing integration env var" {
  printf 'Hello world' > "$TMPDIR_T/cap.txt"
  run "$PPG" --platform TikTok --account "@anicca.en" \
    --integration-id NONEXISTENT_ENV_VAR_xyz --language en \
    --caption-file "$TMPDIR_T/cap.txt" --asset-manifest ""
  [ "$status" -eq 1 ]
}

@test "ppg_check blocks caption with filename leak" {
  printf 'Hello world /Users/anicca/foo.png' > "$TMPDIR_T/cap.txt"
  run "$PPG" --platform TikTok --account "@anicca.en" \
    --integration-id FAKE_INT --language en \
    --caption-file "$TMPDIR_T/cap.txt" --asset-manifest ""
  [ "$status" -eq 4 ]
}

@test "ppg_check blocks over-length X caption" {
  python3 -c "print('a' * 300)" > "$TMPDIR_T/cap.txt"
  run "$PPG" --platform X --account "@aniccaxxx" \
    --integration-id FAKE_INT --language en \
    --caption-file "$TMPDIR_T/cap.txt" --asset-manifest ""
  [ "$status" -eq 4 ]
}

@test "ppg_check blocks missing asset declared in manifest" {
  printf 'Hello world' > "$TMPDIR_T/cap.txt"
  printf '{"images":["%s/missing.png"]}' "$TMPDIR_T" > "$TMPDIR_T/manifest.json"
  run "$PPG" --platform TikTok --account "@anicca.en" \
    --integration-id FAKE_INT --language en \
    --caption-file "$TMPDIR_T/cap.txt" --asset-manifest "$TMPDIR_T/manifest.json"
  [ "$status" -eq 3 ]
}

@test "ppg_check blocks account string without @ prefix" {
  printf 'Hello world' > "$TMPDIR_T/cap.txt"
  run "$PPG" --platform TikTok --account "anicca-en" \
    --integration-id FAKE_INT --language en \
    --caption-file "$TMPDIR_T/cap.txt" --asset-manifest ""
  [ "$status" -eq 5 ]
}
