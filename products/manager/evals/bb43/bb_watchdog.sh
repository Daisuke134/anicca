#!/usr/bin/env bash
# BehaviorBench watchdog (Issue anicca-ops#43). Generic version.
# env: LLAMA_SERVER EVAL_DIR OUT_DIR GGUF [LORA] ARM TASK DATA_PATH TEMP
#      [MAXATT=8] [ATT_TIMEOUT=18000] [LPORT=8080] [PPORT=8001] [MAX_TOKENS=1024]
# llama-server is supervised (restart on death / failed /health); eval goes
# through cache_proxy.py so a failed attempt resumes from the per-request cache.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
LPORT=${LPORT:-8080}; PPORT=${PPORT:-8001}; MAXATT=${MAXATT:-8}; ATT_TIMEOUT=${ATT_TIMEOUT:-18000}
MAX_TOKENS=${MAX_TOKENS:-1024}; THREADS=${THREADS:-$(nproc)}
mkdir -p "$OUT_DIR"; L=$OUT_DIR
log(){ echo "$(date -u '+%FT%TZ') $*" | tee -a "$L/watchdog.log"; }
start_server(){
  pkill -f "llama-server.*--port $LPORT" 2>/dev/null; sleep 2
  local extra=(); [ -n "${LORA:-}" ] && extra=(--lora "$LORA")
  nohup "$LLAMA_SERVER" -m "$GGUF" "${extra[@]}" --port $LPORT --host 127.0.0.1 \
    -c 8192 -np 4 -t $THREADS --seed 42 --alias "$ARM" >> "$L/llama-server.log" 2>&1 &
  echo $! > "$L/llama.pid"
  for i in $(seq 1 180); do curl -sf http://127.0.0.1:$LPORT/health >/dev/null && { log "llama-server up"; return 0; }; sleep 2; done
  log "llama-server failed to start"; tail -20 "$L/llama-server.log"; return 1
}
start_proxy(){
  pkill -f "cache_proxy.py $PPORT" 2>/dev/null; sleep 1
  nohup python3 "$HERE/cache_proxy.py" $PPORT http://127.0.0.1:$LPORT "$L/cache.jsonl" >> "$L/proxy.log" 2>&1 &
  echo $! > "$L/proxy.pid"; sleep 2
}
health_loop(){ while true; do sleep 30
  curl -sf -m 30 http://127.0.0.1:$LPORT/health >/dev/null || { log "health FAIL -> restart llama-server"; start_server; }
  kill -0 "$(cat "$L/proxy.pid")" 2>/dev/null || { log "proxy died -> restart"; start_proxy; }
done; }
log "START arm=$ARM task=$TASK data=$DATA_PATH temp=$TEMP max_tokens=$MAX_TOKENS"
start_server || exit 1; start_proxy; health_loop & HL=$!; trap 'kill $HL 2>/dev/null' EXIT
cd "$EVAL_DIR"
for a in $(seq 1 $MAXATT); do
  log "attempt $a"
  timeout $ATT_TIMEOUT .venv/bin/behaviorbench-eval --task "$TASK" --data-path "$DATA_PATH" --model-type local \
    --model-name "$ARM" --api-base http://127.0.0.1:$PPORT/v1 --temperature "$TEMP" --max-tokens $MAX_TOKENS \
    --concurrency 4 --seed 42 --timeout 900 --output-dir "$L/out" > "$L/attempt$a.log" 2>&1
  rc=$?; f=$(ls -t "$L/out/$ARM/"*.json 2>/dev/null | head -1)
  tail -1 "$L/attempt$a.log"
  if [ $rc -eq 0 ] && [ -n "$f" ]; then log "DONE file=$f stats=$(curl -s http://127.0.0.1:$PPORT/stats)"; echo "$f" > "$L/result_path"; exit 0; fi
  log "attempt $a FAILED rc=$rc stats=$(curl -s http://127.0.0.1:$PPORT/stats) -> resume from cache"; tail -5 "$L/attempt$a.log"
  curl -sf -m 30 http://127.0.0.1:$LPORT/health >/dev/null || start_server
  sleep 10
done
log "GAVE UP after $MAXATT attempts"; exit 1
