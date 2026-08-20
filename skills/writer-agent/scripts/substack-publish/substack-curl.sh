# shellcheck shell=bash
# Run curl normally and retry only a resolver failure through nslookup's IPv4
# answer. The caller supplies the expected TLS host as the first argument.
substack_curl() {
  local host="$1"; shift
  local error_file output rc ip method="GET" url="" body_file="" data_value=""
  local arg next key value config resolve_line
  local -a headers=() passthrough=()
  while [ "$#" -gt 0 ]; do
    arg="$1"; shift
    case "$arg" in
      -X|--request)
        [ "$#" -gt 0 ] || return 2
        method="$1"; shift
        ;;
      -H|--header)
        [ "$#" -gt 0 ] || return 2
        headers+=("$1"); shift
        ;;
      -d|--data|--data-raw|--data-binary)
        [ "$#" -gt 0 ] || return 2
        data_value="$1"; shift
        ;;
      http://*|https://*) url="$arg" ;;
      -sS) passthrough+=("--silent" "--show-error") ;;
      -s|-S|--silent|--show-error|--fail|--fail-with-body) passthrough+=("$arg") ;;
      *) echo "substack_curl: unsupported curl argument: $arg" >&2; return 2 ;;
    esac
  done
  [ -n "$url" ] || { echo "substack_curl: URL is required" >&2; return 2; }
  if [ -n "$data_value" ]; then
    body_file="$(mktemp "${TMPDIR:-/tmp}/substack-curl-body.XXXXXX")" || return 1
    printf '%s' "$data_value" >"$body_file"
  fi
  curl_config_quote() {
    local quoted="$1"
    quoted="${quoted//\\/\\\\}"
    quoted="${quoted//\"/\\\"}"
    printf '"%s"' "$quoted"
  }
  build_config() {
    resolve_line="${1:-}"
    config="silent\nshow-error\n"
    for next in "${passthrough[@]}"; do
      case "$next" in
        --silent) config+="silent\n" ;;
        --show-error) config+="show-error\n" ;;
        --fail) config+="fail\n" ;;
        --fail-with-body) config+="fail-with-body\n" ;;
      esac
    done
    config+="request = $(curl_config_quote "$method")\n"
    [ -n "$resolve_line" ] && config+="resolve = $(curl_config_quote "$resolve_line")\n"
    for key in "${headers[@]}"; do config+="header = $(curl_config_quote "$key")\n"; done
    [ -n "$body_file" ] && config+="data-binary = $(curl_config_quote "@$body_file")\n"
    config+="url = $(curl_config_quote "$url")\n"
  }
  run_config() { printf '%b' "$config" | curl --config - 2>"$error_file"; }
  error_file="$(mktemp "${TMPDIR:-/tmp}/substack-curl.XXXXXX")" || return 1
  build_config
  output="$(run_config)"
  rc=$?
  if [ "$rc" -ne 0 ] && grep -Eiq 'could not resolve host|could not resolve' "$error_file"; then
    ip="$(nslookup -type=A "$host" 2>/dev/null | awk '/^Address: / {print $2}' | tail -1)"
    if ! [[ "$ip" =~ ^[0-9]+(\.[0-9]+){3}$ ]] && command -v dig >/dev/null 2>&1; then
      ip="$(dig +short @1.1.1.1 "$host" A 2>/dev/null | awk '/^[0-9]+(\.[0-9]+){3}$/ {print; exit}')"
    fi
    if [[ "$ip" =~ ^[0-9]+(\.[0-9]+){3}$ ]]; then
      build_config "${host}:443:${ip}"
      output="$(run_config)"
      rc=$?
    fi
  fi
  cat "$error_file" >&2
  rm -- "$error_file"
  if [ -n "$body_file" ]; then rm -- "$body_file"; fi
  [ "$rc" -eq 0 ] || return "$rc"
  printf '%s' "$output"
}
