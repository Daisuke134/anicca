#!/usr/bin/env bats

setup() {
    TEST_DIR=$(mktemp -d)
    export OBSERVER_DIR="$TEST_DIR"
    export OBSERVATION_FILE="$TEST_DIR/observations/test.jsonl"
    mkdir -p "$TEST_DIR/observations"
}

teardown() {
    rm -rf "$TEST_DIR"
}

@test "jq generates valid JSON with special characters" {
    result=$(jq -n \
        --arg ts "2026-02-10T09:00:00Z" \
        --arg type "window" \
        --arg app 'App with "quotes" and \backslash' \
        '{timestamp: $ts, type: $type, data: {app: $app}}')

    # Verify it's valid JSON
    echo "$result" | jq . > /dev/null
    [ $? -eq 0 ]
}

@test "excluded apps are skipped" {
    echo "1Password" > "$TEST_DIR/excluded_apps.txt"

    # Simulate observer with excluded app
    CURRENT_APP="1Password"
    if grep -qxF "$CURRENT_APP" "$TEST_DIR/excluded_apps.txt" 2>/dev/null; then
        SKIPPED=true
    else
        SKIPPED=false
    fi

    [ "$SKIPPED" = "true" ]
}

@test "URL sanitization removes path and query" {
    URL_RAW="https://github.com/user/repo?token=secret"
    SCHEME=$(echo "$URL_RAW" | grep -oE '^https?')
    HOST=$(echo "$URL_RAW" | sed -E 's|^https?://([^/:@]+).*|\1|')
    URL_SANITIZED="${SCHEME}://${HOST}"

    [ "$URL_SANITIZED" = "https://github.com" ]
}

@test "screenshot state prevents duplicates" {
    STATE_FILE="$TEST_DIR/.state.json"

    # First screenshot
    CURRENT_TS=1000
    LAST_SCREENSHOT_TS=0
    SCREENSHOT_INTERVAL=300

    if (( CURRENT_TS - LAST_SCREENSHOT_TS >= SCREENSHOT_INTERVAL )); then
        SHOULD_TAKE=true
    else
        SHOULD_TAKE=false
    fi
    [ "$SHOULD_TAKE" = "true" ]

    # Update state
    LAST_SCREENSHOT_TS=$CURRENT_TS

    # Second attempt within interval
    CURRENT_TS=1100
    if (( CURRENT_TS - LAST_SCREENSHOT_TS >= SCREENSHOT_INTERVAL )); then
        SHOULD_TAKE=true
    else
        SHOULD_TAKE=false
    fi
    [ "$SHOULD_TAKE" = "false" ]
}

@test "observer.sh exists and is executable" {
    [ -x "observer/observer.sh" ]
}

@test "shell-watcher.sh exists and is executable" {
    [ -x "observer/shell-watcher.sh" ]
}
