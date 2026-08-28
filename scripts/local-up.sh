#!/usr/bin/env bash
# One command to run Life Manager on your own machine.
#
#   git clone https://github.com/Daisuke134/life-manager && cd life-manager
#   ./scripts/local-up.sh
#
# It creates the local env file if you don't have one (generating a password for the
# local object store rather than shipping a real one), brings up the compose stack, and
# waits until every service reports healthy before telling you it worked. A stack that
# is "up" but not healthy is the failure this script exists to catch -- printing URLs the
# moment `compose up` returns would report success before anything can serve a request.
#
# Subcommands: up (default) | down | status | logs
#
# Overrides, mainly for testing an isolated copy next to a running one:
#   LM_LOCAL_PROJECT   compose project name       (default: life-manager-local)
#   LM_LOCAL_API_PORT / LM_LOCAL_WORKER_HEALTH_PORT / LM_LOCAL_MINIO_PORT / LM_LOCAL_MINIO_CONSOLE_PORT
#   LM_LOCAL_NO_BUILD=1  reuse the existing runtime image instead of rebuilding

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
COMPOSE_FILE="$REPO/deploy/local/compose.yaml"
ENV_FILE="$REPO/deploy/local/.env"
ENV_EXAMPLE="$REPO/deploy/local/.env.example"
PROJECT="${LM_LOCAL_PROJECT:-life-manager-local}"
READY_TIMEOUT_SECONDS="${LM_LOCAL_READY_TIMEOUT:-300}"

say() { printf '%s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

compose() {
  docker compose -p "$PROJECT" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

require_docker() {
  command -v docker >/dev/null 2>&1 || die "docker is not installed. Install Docker Desktop, colima, or another Docker engine, then run this again."
  docker compose version >/dev/null 2>&1 || die "this Docker has no 'compose' subcommand. Update Docker, or install the compose plugin."
  docker info >/dev/null 2>&1 || die "the Docker daemon is not running. Start it (Docker Desktop, or 'colima start'), then run this again."
}

# A password that never leaves this machine, but is still not a value someone can guess
# from having read the repository.
generate_password() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 24
  else
    head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n'
  fi
}

ensure_env_file() {
  [ -f "$ENV_FILE" ] && return 0
  [ -f "$ENV_EXAMPLE" ] || die "missing $ENV_EXAMPLE -- this is not a complete checkout."
  local password
  password="$(generate_password)"
  # Replace the placeholder rather than appending, so the file keeps one value per key.
  sed "s|^MINIO_ROOT_PASSWORD=.*|MINIO_ROOT_PASSWORD=${password}|" "$ENV_EXAMPLE" > "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  say "created deploy/local/.env with a generated object-store password (chmod 600)"
}

# `compose up --wait` already blocks on healthchecks, but it exits non-zero without saying
# which service failed, so report that ourselves.
report_unhealthy() {
  say ""
  say "these services did not become healthy:"
  compose ps --format '{{.Service}}\t{{.State}}\t{{.Status}}' 2>/dev/null | awk -F'\t' '$2 != "running" || $3 !~ /healthy/ {print "  " $1 "  " $2 "  " $3}'
  say ""
  say "logs from the last minute:"
  compose logs --since 60s --tail 40 2>/dev/null | tail -60
}

cmd_up() {
  require_docker
  ensure_env_file

  local up_args=(--wait --wait-timeout "$READY_TIMEOUT_SECONDS" -d --no-build)
  if [ "${LM_LOCAL_NO_BUILD:-0}" != "1" ]; then
    say "building the shared runtime image once"
    compose build api || die "the runtime image did not build."
  fi

  say "starting Life Manager (project: $PROJECT) -- first run builds the image and can take a few minutes"
  if ! compose up "${up_args[@]}"; then
    report_unhealthy
    die "the stack did not come up healthy. The output above says which part."
  fi

  local api_port worker_port console_port
  api_port="$(grep -E '^LM_LOCAL_API_PORT=' "$ENV_FILE" | cut -d= -f2)"
  worker_port="$(grep -E '^LM_LOCAL_WORKER_HEALTH_PORT=' "$ENV_FILE" | cut -d= -f2)"
  console_port="$(grep -E '^LM_LOCAL_MINIO_CONSOLE_PORT=' "$ENV_FILE" | cut -d= -f2)"
  api_port="${LM_LOCAL_API_PORT:-${api_port:-18788}}"
  worker_port="${LM_LOCAL_WORKER_HEALTH_PORT:-${worker_port:-18790}}"
  console_port="${LM_LOCAL_MINIO_CONSOLE_PORT:-${console_port:-19001}}"

  say ""
  say "Life Manager is running."
  say "  API             http://localhost:${api_port}"
  say "  worker health   http://localhost:${worker_port}"
  say "  object store    http://localhost:${console_port}  (console)"
  say ""
  say "Your data stays in this stack's postgres and object store. Nothing is sent anywhere by running it."
  say "To talk to it from Telegram, add your own bot token as a secret reference -- see apps/life-manager/.env.example."
  say ""
  say "  ./scripts/local-up.sh status    what is running"
  say "  ./scripts/local-up.sh logs      follow the logs"
  say "  ./scripts/local-up.sh down      stop it (your data survives)"
}

cmd_down() {
  require_docker
  [ -f "$ENV_FILE" ] || die "no deploy/local/.env -- this stack was never started from here."
  compose down
  say "stopped. Volumes are kept; 'docker compose -p $PROJECT -f $COMPOSE_FILE down -v' also deletes the data."
}

cmd_status() {
  require_docker
  [ -f "$ENV_FILE" ] || die "no deploy/local/.env -- this stack was never started from here."
  compose ps
  say ""
  say "runtime owners:"
  compose exec -T scheduler node -e '
    const e = process.env;
    console.log(JSON.stringify({role:e.LM_DEPLOYMENT_ROLE,owner:e.LM_SCHEDULER_OWNER,
      loops_enabled:e.LIFE_RUN_LOOPS==="true",effects:{
        financial:Boolean(e.LM_RUNTIME_TENANT_ID),
        marketing_generation:e.LM_MARKETING_GENERATION_ENABLED==="true",
        marketing_publication:e.LM_MARKETING_PUBLICATION_CHAIN_ENABLED==="true",
        marketing_observation:e.LM_MARKETING_OBSERVATION_ENABLED==="true"}}));'
  compose exec -T worker node -e "fetch('http://localhost:8790/health').then(r=>r.text()).then(console.log)"
  compose exec -T marketing-liveness node -e "fetch('http://localhost:8791/health').then(r=>r.text()).then(console.log)"
}

cmd_logs() {
  require_docker
  [ -f "$ENV_FILE" ] || die "no deploy/local/.env -- this stack was never started from here."
  compose logs -f --tail 100
}

case "${1:-up}" in
  up) cmd_up ;;
  down) cmd_down ;;
  status) cmd_status ;;
  logs) cmd_logs ;;
  -h|--help|help) sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//' ;;
  *) die "unknown command '${1}'. Use: up | down | status | logs" ;;
esac
