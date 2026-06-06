#!/usr/bin/env bats

load helpers

setup() {
  setup_phone_test_env
  PHONE_BIN="/Users/anicca/bin/phone"
}

@test "phone with no arg creates a new tmux session named phone-<ts>" {
  run "$PHONE_BIN"
  [ "$status" -eq 0 ]
  grep -qE "new-session.*phone-1780900000" "$TMUX_CALLS"
}

@test "phone ls invokes tmux ls and filters phone-*" {
  printf 'phone-1780000000: 1 windows (created Thu)\nphone-1780900000: 1 windows (created Fri)\nother: 1 windows\n' > "$BATS_TEST_TMPDIR/tmux-ls-output"
  run "$PHONE_BIN" ls
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "phone-1780000000"
  echo "$output" | grep -q "phone-1780900000"
  ! echo "$output" | grep -q "^other:"
}

@test "phone <name> attaches to that named session" {
  run "$PHONE_BIN" phone-1780000000
  [ "$status" -eq 0 ]
  grep -qE "attach -t phone-1780000000" "$TMUX_CALLS"
}

@test "phone kill <name> kills that session" {
  run "$PHONE_BIN" kill phone-1780000000
  [ "$status" -eq 0 ]
  grep -qE "kill-session -t phone-1780000000" "$TMUX_CALLS"
}

@test "phone kill with no arg prints usage and exits 1" {
  run "$PHONE_BIN" kill
  [ "$status" -eq 1 ]
  echo "$output" | grep -q "usage: phone kill"
}

@test "phone last attaches to the most-recent phone-* session" {
  printf 'phone-1780000000: 1 windows\nphone-1780900000: 1 windows\n' > "$BATS_TEST_TMPDIR/tmux-ls-output"
  run "$PHONE_BIN" last
  [ "$status" -eq 0 ]
  grep -qE "attach -t phone-1780900000" "$TMUX_CALLS"
}

@test "phone with no arg exports MOSHI_PHONE=1 into the new tmux session" {
  run "$PHONE_BIN"
  [ "$status" -eq 0 ]
  # tmux -e MOSHI_PHONE=1 form OR set-environment form acceptable
  grep -qE "MOSHI_PHONE=1" "$TMUX_CALLS"
}

@test "phone strips inherited \$TMUX env var (socket collision regression)" {
  # When invoked from inside an existing tmux session, $TMUX is the socket
  # path. Phone must NOT pass that into the new tmux client (would fail with
  # 'Socket operation on non-socket').
  # We assert this by checking the script source uses 'env -u TMUX'.
  grep -q 'env -u TMUX' "$PHONE_BIN"
}
