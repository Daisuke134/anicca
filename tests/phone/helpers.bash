#!/usr/bin/env bash
# Test helpers for phone bats suite.
# We fake tmux + date so we can assert calls without spawning real sessions.

setup_phone_test_env() {
  export PATH="$BATS_TEST_TMPDIR/fake-bin:$PATH"
  mkdir -p "$BATS_TEST_TMPDIR/fake-bin"
  export TMUX_CALLS="$BATS_TEST_TMPDIR/tmux-calls.log"
  : > "$TMUX_CALLS"

  cat > "$BATS_TEST_TMPDIR/fake-bin/tmux" <<EOF
#!/usr/bin/env bash
echo "\$@" >> "$TMUX_CALLS"
case "\$1" in
  ls)
    if [ -f "$BATS_TEST_TMPDIR/tmux-ls-output" ]; then
      cat "$BATS_TEST_TMPDIR/tmux-ls-output"
    fi
    ;;
  *)
    : # no-op
    ;;
esac
EOF
  chmod +x "$BATS_TEST_TMPDIR/fake-bin/tmux"

  cat > "$BATS_TEST_TMPDIR/fake-bin/date" <<EOF
#!/usr/bin/env bash
if [ "\$1" = "+%s" ]; then
  echo "1780900000"
else
  /bin/date "\$@"
fi
EOF
  chmod +x "$BATS_TEST_TMPDIR/fake-bin/date"

  # Force the phone script to use our fake tmux via TMUX_BIN env
  export TMUX_BIN="$BATS_TEST_TMPDIR/fake-bin/tmux"
}
