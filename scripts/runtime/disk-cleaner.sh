#!/bin/bash
# disk-cleaner.sh v9 — Mac Mini 自動ディスククリーナー (統合版、5分毎 launchd、LLM トークン 0)
#
# v8→v9 (2026-07-04、Dais指摘「クリーナーが複数あると複雑でバグの温床になる」):
#   同じ ~/.cache/anicca-clones を3つの独立クリーナーが別ロジックで掃除していた
#   (com.anicca.disk-cleaner 1h毎 / ai.anicca.disk-janitor 5分毎 / OpenClaw cron
#   anicca-disk-hourly 10分毎、うち2つは.venv保護が無く producer.sh の engine venv
#   を実際に繰り返し破壊していた= タスク#9 incident の真因)。
#   → 3つを本スクリプト1本に統合。他2つは無効化(disable、削除ではなく復元可能に)。
#
# v7→v8 (2026-07-04、タスク#9): anicca-clones sweep が producer.sh の engine venv
#   を消していた件、is_protected に .venv パターン追加(このv9でも継続)。
# v6→v7 (2026-06-19): .git bloat 対策(THROTTLED git gc)+ var/folders T/C 掃除。
#   保護は「場所」でなく「種類(kind)」で行う: source/.env/key/identity/state.jsonl/
#   cron/ model cache(whisper/huggingface) は名前で必ず保護。
#
# 起動: launchd com.anicca.disk-cleaner (StartInterval 300 = 5分毎)。

set -u
LOG_FILE="$HOME/.openclaw/logs/disk-cleaner.log"
mkdir -p "$HOME/.openclaw/logs" "$HOME/.openclaw/state" 2>/dev/null
export PATH=/opt/homebrew/bin:/opt/homebrew/sbin:/usr/bin:/bin:/usr/sbin:/sbin
log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG_FILE"; }

# F7 fix (2026-07-04, spec 2026-07-01-openclaw-self-heal-design.md): shared
# path-manifest guard (state/protected-paths.json), same one skills/disk-janitor/run.sh
# now uses — replaces the hand-typed `! -name 'reelclaw-assets'` exclusion below so a
# future glob edit can't reintroduce the same bug in only one of the two scripts.
# shellcheck disable=SC1091
. "$HOME/.openclaw/skills/_shared/lib/protected-paths-guard.sh" 2>/dev/null || true

# ★ 二重起動防止 ★ (macOSに flock 無し → mkdir atomic lock。2026-07-04: 実行が
# 300秒間隔に対して重く(HOME全体find等)、前回が終わる前に次回が起動し9重に
# 積み重なった事故を実機確認、以後これで防ぐ)
LOCK_DIR="$HOME/.openclaw/state/.disk-cleaner.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  OLD_PID=$(cat "$LOCK_DIR/pid" 2>/dev/null || echo "")
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    exit 0   # 前回インスタンスがまだ稼働中 → skip (ログも出さずサイレント終了)
  fi
  rm -rf "$LOCK_DIR"; mkdir "$LOCK_DIR" 2>/dev/null || exit 0
fi
echo $$ > "$LOCK_DIR/pid"
trap 'rm -rf "$LOCK_DIR"' EXIT

free_gb() { df -g /System/Volumes/Data 2>/dev/null | awk 'NR==2{print $4}'; }
free_kb() { df -k / | awk 'END{print $4}'; }
GITGC_THROTTLE_MARKER="$HOME/.openclaw/state/.last-gitgc"
GITGC_MIN_INTERVAL=3600   # git gc は最頻でも 1 時間に 1 回 (CPU 配慮)
THRESH_CRIT_GB=6

# ── 種類で守る (= 絶対に消さない) ───────────────────────────────────────────
is_protected() {
  case "$1" in
    *.swift|*.ts|*.tsx|*.js|*.jsx|*.py|*.sh|*.md|*.json|*.toml|*.yaml|*.yml) return 0 ;;
    */.env|*.key|*.pem|*/auth.json|*/.config/gh/*) return 0 ;;
    */.openclaw/identity/*|*/.openclaw/cron/*|*/.openclaw/.env) return 0 ;;
    */.openclaw/skills/*/state/*|*/state/*.jsonl) return 0 ;;
    *.sqlite|*.db) return 0 ;;
    */.cache/whisper/*|*/.cache/huggingface/*|*/.cache/kokoro-onnx/*) return 0 ;;
    */.cache/anicca-clones/*/.venv/*) return 0 ;;  # 永続 engine venv (producer.sh 等が daily cron で再利用)
    */.camofox/*|*/.cloakbrowser/*|*cloak_*profile*) return 0 ;;
    */Library/Caches/camoufox/*) return 0 ;;  # camoufox 本体バイナリ/資産 (2026-07-05 保護穴修正)
    */LaunchAgents/ai.*.plist|*/LaunchAgents/com.anicca.*.plist) return 0 ;;
    */.git/*) return 0 ;;  # .git は file 単位で触らない (git gc に任せる)
  esac
  return 1
}

# ── 名前で消す (= 再生成可能な大物だけ、age 条件付き) ────────────────────────
sweep() {
  local target="$1" age="$2"
  [ -e "$target" ] || return 0
  find "$target" -mindepth 1 -mtime "+${age}" \( -type f -o -type d \) 2>/dev/null | while read -r p; do
    is_protected "$p" && continue
    rm -rf "$p" 2>/dev/null
  done
}

# anicca-clones 専用: clone ディレクトリ単位で判定し、.venv を持つ永続 engine と
# .anicca-keep marker 持ち(= 作業中と宣言された clone、spec §10 H7)は丸ごと保護、
# それ以外は one-off clone として24h超で丸ごと削除。
# 2026-07-04 incident: W1 作業中の polymarket-agent (venv 無し) を24h経過で削除し
# タスクを中断させた → 使用側が `touch <clone>/.anicca-keep` で保護を宣言する。
# aggressive=1 (2026-07-12 incident: 空き0GBが1時間超続きFranklinのledger/harness-
# failures書き込みがENOSPCで連続失敗、原因は当日clone(<24h)がこの猶予で保護され
# 続けたこと): 24h猶予を無視して即掃除する。.venv/.anicca-keep保護は常に維持。
clean_anicca_clones() {
  local root="$HOME/.cache/anicca-clones"
  local aggressive="${1:-0}"
  [ -d "$root" ] || return 0
  local find_args=(-mindepth 1 -maxdepth 1 -type d)
  [ "$aggressive" != "1" ] && find_args+=(-mtime +0)
  find "$root" "${find_args[@]}" 2>/dev/null | while read -r d; do
    [ -d "$d/.venv" ] && continue
    [ -e "$d/.anicca-keep" ] && continue
    rm -rf "$d" 2>/dev/null
  done
}

BEFORE=$(free_gb); BEFORE=${BEFORE:-0}
log "=== v9 start | free ${BEFORE}GB ==="

# 0-pre) ★ PREVENTIVE MODE ★ — 空き<20GB で回収する (2026-07-13)
# なぜ: 従来は free<3GB でしか積極回収せず、そこへ落ちた時点で既に手遅れだった。
# 2026-07-13 に free が 0〜2GB まで落ち、gig loop が ENOSPC で死んだ
# (OSError: [Errno 28] '/Users/anicca/loops/gig/state/core-status.json')。
# 事後処理をやめ、余裕があるうちに常時回収する。ここで消すのは全て再生成可能な物のみ。
PREVENT_GB=20
BEFORE_KB=$(free_kb); BEFORE_KB=${BEFORE_KB:-0}
PREVENT_KB=$((PREVENT_GB * 1024 * 1024))
if [ "$BEFORE_KB" -lt "$PREVENT_KB" ]; then
  log "PREVENTIVE MODE (free ${BEFORE}GB < ${PREVENT_GB}GB)"
  brew cleanup -s --prune=1 >/dev/null 2>&1
  npm cache clean --force >/dev/null 2>&1
  find /private/tmp/claude-501 -mindepth 2 -type f \( -name '*.output' -o -name '*.jsonl' \) -mmin +120 -delete 2>/dev/null
  find "$HOME/Library/Caches" -maxdepth 1 -mindepth 1 -mtime +7 -not -name camoufox -exec rm -rf {} + 2>/dev/null
  # 2026-07-16: セッション消失インシデントの調査で「/resume で過去セッションが消える」
  # 原因の一つと特定されたため無効化(削除ではなくコメントアウト)。Claude のセッション
  # 履歴(*.jsonl)は再生成不能。Claude Code 本体が settings.json の cleanupPeriodDays
  # (公式デフォルト30日、本件は誤って3に落ちていたため99999へ復旧)で既に管理しており、
  # このスクリプトが独自の10日ルールで二重に消す必要はない。memory/ は別ディレクトリで無傷。
  # find "$HOME/.claude/projects" -name '*.jsonl' -mtime +10 -delete 2>/dev/null
  find "$HOME/.claude/token-optimizer/checkpoints" -type f -mtime +3 -delete 2>/dev/null
  rm -rf "$HOME/.bun/install/cache" "$HOME/.cargo/registry/cache" 2>/dev/null
  # Chromium profile の再生成可能キャッシュ (Cookies/Local Storage/Login Data は触らない)
  for prof in "$HOME"/.cloak/*/; do
    for c in "Cache" "Code Cache" "GPUCache" "ShaderCache" "DawnGraphiteCache" "DawnWebGPUCache"; do
      [ -d "$prof/Default/$c" ] && rm -rf "$prof/Default/$c" 2>/dev/null
    done
  done
  # 人間の置き場 (Desktop/Downloads/Archive) は放っておくと無限に太る。再取得できる物だけ、古い物だけ。
  find "$HOME/Downloads" -maxdepth 1 \( -name '*.dmg' -o -name '*.pkg' -o -name '*.zip' \) -mtime +7 -delete 2>/dev/null
  find "$HOME/Downloads" -maxdepth 1 -mtime +30 -exec rm -rf {} + 2>/dev/null
  find "$HOME/Desktop" -maxdepth 1 \( -name 'Screenshot*' -o -name 'スクリーンショット*' -o -name '*.mov' \) -mtime +14 -delete 2>/dev/null
  # Archive は「捨てる前の一時退避」。30日残ったものは要らなかったということ。
  find "$HOME/Archive" -maxdepth 1 -mindepth 1 -mtime +30 -exec rm -rf {} + 2>/dev/null
  # 2026-08-01 撤去: ここには「docker ps が失敗したら ~/.colima と ~/.lima を rm -rf」
  # という行があった。危険なので消した。理由:
  #   - `docker ps` は VM が不要なときだけでなく、colima の起動途中・socket 混雑・
  #     daemon 再起動中でも失敗する。このスクリプトは 300 秒ごとに走る。
  #   - 作り直されるのは VM の殻だけで、**中のデータボリュームは戻らない**。
  #     現に life-manager の postgres と minio がこの VM の中で本番稼働している。
  #   - 一度の誤判定で復旧不能な破壊が起きる操作を、無人ループに置いてはいけない。
  # VM が本当に不要かどうかは人間か、コンテナの中身を見た上での判断に委ねる。
  log "PREVENTIVE done | free $(free_gb)GB"
fi

# 0) ★ EMERGENCY MODE ★ — 空き<3GB なら最速で効く物から先に削る (2026-06-24 ENOSPC 再発防止)
EMERG_KB=$((3 * 1024 * 1024))
if [ "$BEFORE_KB" -lt "$EMERG_KB" ]; then
  log "EMERGENCY MODE (free ${BEFORE}GB < 3GB)"
  find /private/tmp/claude-501 -mindepth 2 -type f \( -name '*.output' -o -name '*.jsonl' \) -mmin +60 -delete 2>/dev/null
  rm -rf "$HOME/Library/Developer/Xcode/DerivedData"/* "$HOME/Library/Caches/com.apple.dt.Xcode"/* 2>/dev/null
  clean_anicca_clones
  rm -rf "$HOME/.npm/_cacache" 2>/dev/null
  find "$HOME/Library/Caches" -maxdepth 1 -mindepth 1 -mtime +1 -not -name camoufox -exec rm -rf {} + 2>/dev/null
  find /private/var/folders/*/*/[CX] -maxdepth 1 -type d -name '*code_sign_clone*' -mmin +5 -exec rm -rf {} + 2>/dev/null
fi

# 0b) ★ ULTRA-EMERGENCY ★ — 空き<1GB (2026-07-12 incident: この状態が1時間超続き
# Franklinのledger/harness-failures書き込みがENOSPCで連続失敗した実例あり) は
# anicca-clones の24h猶予も無視して即掃除する(.venv/.anicca-keep保護は維持)。
ULTRA_EMERG_KB=$((1 * 1024 * 1024))
if [ "$BEFORE_KB" -lt "$ULTRA_EMERG_KB" ]; then
  log "ULTRA-EMERGENCY (free ${BEFORE}GB < 1GB) — aggressive anicca-clones sweep (ignoring 24h grace)"
  clean_anicca_clones 1
fi

# 1) 一時ファイル (active session は mtime 新しいので残る) ──────────────────
sweep /private/tmp 1
sweep /private/tmp/claude-501 1
for vf in /private/var/folders/*/*/T /private/var/folders/*/*/C; do
  sweep "$vf" 1
done
rm -f /tmp/*.md /tmp/x_thread_*.json /tmp/sao_draft_*.json /tmp/jobs.json.* 2>/dev/null

# 2) 再生成可能なビルド/ランタイムキャッシュ (名前で、age 7日)
#    ★ $HOME 全体でなく既知のプロジェクトルートのみ (旧: $HOME 全体スキャンが
#    I/O律速で5分超かかり、5分毎launchdで前回インスタンスと重複起動する事故
#    (最大9重積み)を実機確認。~/Library, ~/.cache 等 非開発ディレクトリまで
#    舐める必要は無い。2026-07-04 v9) ★
#    ★ 2026-07-16 incident: 旧版は `\( -name node_modules -o ... -o -name dist ... \) -mtime +7 -prune`
#    と書いていた。-prune は先行条件が全て真の時しか実行されないので、node_modules 自体が
#    npm install で mtime 新鮮だと -mtime +7 に外れ、prune されず、find が node_modules の
#    "中" へ降りた。中の各パッケージの dist/ は publish 時の古い mtime を持つため必ず +7 に
#    該当し、rm -rf された。結果 x402-express/dist (7/16 01:40) と @solana/codecs-numbers/dist
#    が消え、全 seller と wallet ツールが ERR_MODULE_NOT_FOUND で死んだ。
#    is_protected も無力だった (全パターンが *.js 等のファイル向けで、dist という
#    ディレクトリ名にはどれも一致しない)。
#    → node_modules は「中へ降りない」を最優先で prune する。node_modules 自体は
#      生きた依存であり消さない (再生成可能だが、消せば colony が npm install まで全停止する)。
for root in "$HOME/anicca-project" "$HOME/anicca" "$HOME/.openclaw" "$HOME/.hermes" "$HOME/Downloads"; do
  [ -d "$root" ] || continue
  find "$root" \
    -type d -name node_modules -prune -o \
    -type d \( \
      -name .venv -o -name venv -o -name __pycache__ -o \
      -name .build -o -name build -o -name DerivedData -o -name SourcePackages -o \
      -name .next -o -name dist -o -name .turbo -o -name .parcel-cache \
    \) -mtime +7 -print 2>/dev/null | while read -r d; do
    case "$d" in */node_modules/*) continue ;; esac   # 二重防御: 依存の中身は決して消さない
    is_protected "$d" && continue
    rm -rf "$d" 2>/dev/null
  done
done
npm cache clean --force >/dev/null 2>&1
clean_anicca_clones
sweep "$HOME/.cache/uv" 14
sweep "$HOME/.cache/puppeteer" 30
sweep "$HOME/.cache/codex-runtimes" 14
sweep "$HOME/.cache/openai-curated" 14
sweep "$HOME/.openclaw/agents/anicca/agent/codex-home/sessions" 7
sweep "$HOME/Library/Caches/ms-playwright" 30
sweep "$HOME/Library/Application Support/Claude/vm_bundles" 7
sweep "$HOME/Library/Developer/Xcode/DerivedData" 1
xcrun simctl delete unavailable >/dev/null 2>&1

# Chrome/Chromium code_sign_clone orphans (agent-browser/playwright が per-launch で
# 複製する ~450MB framework、reap されないと最大の disk 食い)。60分超のみ。
for vf in /private/var/folders/*/*/X /private/var/folders/*/*/C; do
  [ -d "$vf" ] || continue
  find "$vf" -maxdepth 1 -type d -name '*code_sign_clone*' 2>/dev/null | while read -r cl; do
    find "$cl" -mindepth 1 -maxdepth 1 -mmin +60 -exec rm -rf {} + 2>/dev/null
  done
done

# 3) content-factory 系ワークスペース (age条件つき、再生成可能なもののみ) ──────
rm -rf "$HOME/anicca-project/sao-content-factory/remotion/out" "$HOME/anicca-project/sao-content-factory/remotion/.cache" 2>/dev/null
find "$HOME/anicca-project/sao-content-factory/assets" -type d -name output -mtime +2 -exec rm -rf {} + 2>/dev/null
find "$HOME/anicca-project/sao-content-factory/assets" -type f -name 'yt_full.mp4' -mtime +2 -delete 2>/dev/null
find "$HOME/anicca-project/sao-content-factory/assets" -type f -name 'bgm_*_full.mp3' -mtime +2 -delete 2>/dev/null
find "$HOME/.openclaw/skills/sao-content-factory/output" -mindepth 3 -type d -mtime +2 -exec rm -rf {} + 2>/dev/null
find "$HOME/.openclaw/workspace/tiktok-marketing" -maxdepth 1 -type d \( \
  -name '*2026*' -o -name 'morning-*' -o -name 'afternoon-*' -o -name 'evening-*' -o -name 'reelclaw-*' -o -name 'work-*' -o -name 'slideshow-*' -o -name 'test-*' -o -name 'demo-reel-*' \
\) -mtime +2 -exec rm -rf {} + 2>/dev/null
find "$HOME/.openclaw/workspace/tiktok-marketing/posts" -mindepth 1 -maxdepth 1 -type d -mtime +3 -exec rm -rf {} + 2>/dev/null
find "$HOME/.openclaw/workspace/honne-ai" -mindepth 1 -maxdepth 1 -type d \( \
  -name 'runs' -o -name 'work' -o -name 'exports' -o -name 'build' -o -name 'builds' -o -name 'out' -o -name 'output' -o -name 'render' -o -name 'renders' -o -name 'reelclaw-runs' -o -name 'reelclaw-work' -o -name '_reelclaw_tmp' -o -name 'tmp' -o -name 'sample-renders' -o -name 'finals' -o -name '*run*' -o -name '*work*' -o -name '*render*' -o -name '*export*' -o -name '*build*' \
\) -mtime +3 -exec rm -rf {} + 2>/dev/null
find "$HOME/.openclaw/workspace/mau-tiktok/output" -type f -mtime +7 -delete 2>/dev/null
# NOTE: reelclaw-assets/ は永続アセットストア(music/hooks-symlinks/video seeds、
# 6 reelclaw posting families 全部が参照)であり使い捨て run/work dir ではない。
# 2026-07-04 incident(disk-janitor skill側で実際に発生): 'reelclaw*' glob が
# reelclaw-assets/ ごと削除し card-en/card-ja/widget-en/widget-ja/honne-en/honne-ja
# の video seed を全損させた。ここでも同じ glob を使う為、F7 fix: 除外は
# hand-typed `! -name` でなく state/protected-paths.json 由来の is_protected_path()
# で行う(disk-janitor/run.sh と共通のマニフェスト、DRY化)。
find "$HOME/.openclaw/workspace" -maxdepth 1 -type d \( \
  -name 'reelclaw*' -o -name 'slideshow-*' -o -name 'TODAY-*' -o -name '*-run' -o -name '*-work' -o -name '*-test*' \
\) -mtime +2 -print0 2>/dev/null | while IFS= read -r -d '' _cand; do
  if command -v is_protected_path >/dev/null 2>&1 && is_protected_path "$_cand"; then
    log "protected-paths.json: skipping $_cand"
    continue
  fi
  rm -rf "$_cand" 2>/dev/null
done

# OpenClaw sessions.json 肥大化対策 (2026-05-20 177MB→V8 heap枯渇でgateway crash事故)
for SJ in "$HOME"/.openclaw/agents/*/sessions/sessions.json; do
  [ -f "$SJ" ] || continue
  SZ=$(stat -f%z "$SJ" 2>/dev/null || stat -c%s "$SJ" 2>/dev/null || echo 0)
  if [ "$SZ" -gt $((50 * 1024 * 1024)) ]; then
    gzip -c "$SJ" > "${SJ}.archive-$(date -u +%Y%m%dT%H%M%SZ).gz" && printf '[]' > "$SJ" && chmod 600 "$SJ" 2>/dev/null
  fi
done

# 4) ★ THROTTLED git gc — 肥大 .git を統合 (真の bloat 源) ────────────────────
NOW=$(date +%s)
LAST=0; [ -f "$GITGC_THROTTLE_MARKER" ] && LAST=$(cat "$GITGC_THROTTLE_MARKER" 2>/dev/null || echo 0)
if [ $((NOW - LAST)) -ge "$GITGC_MIN_INTERVAL" ]; then
  for repo in "$HOME/.openclaw" "$HOME/.hermes" "$HOME/anicca-project" "$HOME/anicca"; do
    [ -d "$repo/.git" ] || continue
    PACK_KB=$(du -sk "$repo/.git/objects/pack" 2>/dev/null | awk '{print $1}')
    PACK_KB=${PACK_KB:-0}
    if [ "$PACK_KB" -gt 3145728 ]; then   # >3GB の .git のみ gc
      log "git gc $repo (.git pack ${PACK_KB}KB)"
      git -C "$repo" gc --prune=now >> "$HOME/.openclaw/logs/gc-$(basename "$repo").log" 2>&1
    fi
  done
  echo "$NOW" > "$GITGC_THROTTLE_MARKER"
fi

AFTER=$(free_gb); AFTER=${AFTER:-0}
FREED=$((AFTER - BEFORE))
log "=== v9 done | before ${BEFORE}GB | after ${AFTER}GB | freed +${FREED}GB ==="

# 5) 深刻時のみ Slack 通知 (ノイズ回避: 毎回報告ではなく閾値超過時のみ) ─────────
if [ "$AFTER" -lt "$THRESH_CRIT_GB" ]; then
  TOKEN=$(grep -E "^SLACK_BOT_TOKEN=" "$HOME/.openclaw/.env" 2>/dev/null | cut -d= -f2- | tr -d '"')
  [ -n "$TOKEN" ] && curl -s -X POST "https://slack.com/api/chat.postMessage" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d "{\"channel\":\"C091G3PKHL2\",\"text\":\"🔴 Mac Mini disk CRITICAL: ${AFTER}GB free after clean. .git bloat? check gc logs.\"}" >/dev/null 2>&1
fi
exit 0
