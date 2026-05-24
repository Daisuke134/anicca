#!/usr/bin/env bash
# Stage 2: DOWNLOAD — for each candidate get the MP4 + Whisper transcript + base avatar frame.
# Per Dais 8-step v2: NO local-references reuse. Must download fresh.
# Output:
#   <run_dir>/source_<id>.mp4
#   <run_dir>/source_<id>.transcript.json
#   <run_dir>/<id>_base.jpg          (best single frame for avatar replication)
#   <run_dir>/frames_<id>/           (sampled frames for analysis)
set -euo pipefail
RUN_DIR="${1:?run_dir required}"

ROOT="$HOME/anicca-monk-factory"
set -a; . "$ROOT/.env"; set +a

CANDIDATES="$RUN_DIR/candidates.json"
[ -f "$CANDIDATES" ] || { echo "❌ candidates.json missing"; exit 2; }

echo ""
echo "─── Stage 2: DOWNLOAD ───"

LANG_ARG=$(python3 -c "import json; print(json.load(open('$CANDIDATES'))['lang'])")

python3 - <<PY "$RUN_DIR" "$LANG_ARG"
import json, sys, os, subprocess, urllib.request

run_dir, lang = sys.argv[1:3]
data = json.load(open(f'{run_dir}/candidates.json'))
candidates = data['candidates']

for c in candidates:
    vid = c['id']
    out_mp4 = f'{run_dir}/source_{vid}.mp4'
    out_tr = f'{run_dir}/source_{vid}.transcript.json'
    if os.path.exists(out_mp4) and os.path.getsize(out_mp4) > 10000:
        print(f'  [{vid}] already downloaded')
        continue
    success = False

    # Try Apify direct mediaUrls first (when available)
    direct = c.get('video_download_url')
    if direct:
        try:
            print(f'  [{vid}] direct URL...')
            req = urllib.request.Request(direct, headers={'User-Agent':'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=60) as r:
                open(out_mp4,'wb').write(r.read())
            if os.path.getsize(out_mp4) > 10000:
                success = True
                print(f'    ✅ direct ({os.path.getsize(out_mp4)//1024} KB)')
        except Exception as e:
            print(f'    ❌ direct: {e}')

    # snaptik fallback (always required when Apify path returns no mediaUrl)
    if not success:
        web_url = c.get('web_video_url') or f'https://www.tiktok.com/@{c["author_handle"]}/video/{vid}'
        print(f'  [{vid}] snaptik {web_url} ...')
        try:
            r = subprocess.run(['snaptik', web_url, '-o', out_mp4],
                              capture_output=True, text=True, timeout=180)
            if r.returncode == 0 and os.path.exists(out_mp4) and os.path.getsize(out_mp4) > 10000:
                success = True
                print(f'    ✅ snaptik ({os.path.getsize(out_mp4)//1024} KB)')
            else:
                print(f'    ❌ snaptik rc={r.returncode}: {(r.stderr or r.stdout)[:200]}')
        except FileNotFoundError:
            print(f'    ❌ snaptik CLI not installed')
        except Exception as e:
            print(f'    ❌ snaptik: {e}')

    # yt-dlp last resort (often works for TT)
    if not success:
        try:
            print(f'  [{vid}] yt-dlp DL...')
            r = subprocess.run(['yt-dlp', '-o', out_mp4, '--no-warnings',
                                f'https://www.tiktok.com/@{c["author_handle"]}/video/{vid}'],
                              capture_output=True, text=True, timeout=180)
            if r.returncode == 0 and os.path.exists(out_mp4) and os.path.getsize(out_mp4) > 10000:
                success = True
                print(f'    ✅ yt-dlp ({os.path.getsize(out_mp4)//1024} KB)')
            else:
                print(f'    ❌ yt-dlp: {r.stderr[:200]}')
        except Exception as e:
            print(f'    ❌ yt-dlp: {e}')

    if not success:
        print(f'  [{vid}] ALL DL methods failed, skipping')
        continue

    # ── Whisper transcript ────────────────────────────────────────────
    print(f'  [{vid}] whisper transcribe...')
    try:
        wmodel = 'base.en' if lang == 'en' else 'base'
        wlang  = 'en' if lang == 'en' else 'ja'
        r = subprocess.run(
            ['whisper', out_mp4, '--model', wmodel, '--language', wlang,
             '--output_format', 'json', '--output_dir', run_dir,
             '--word_timestamps', 'True', '--verbose', 'False'],
            capture_output=True, text=True, timeout=600)
        # whisper writes <basename>.json
        wjson = f'{run_dir}/source_{vid}.json'
        if os.path.exists(wjson):
            os.rename(wjson, out_tr)
            print(f'    ✅ transcript')
        else:
            print(f'    ❌ whisper output missing: {r.stderr[:200]}')
    except Exception as e:
        print(f'    ❌ whisper: {e}')

    # ── Frame extraction (1 fps for analyze; pick best for base avatar) ──
    frames_dir = f'{run_dir}/frames_{vid}'
    os.makedirs(frames_dir, exist_ok=True)
    if not os.listdir(frames_dir):
        subprocess.run(['ffmpeg','-y','-i', out_mp4, '-vf','fps=1,scale=720:-1',
                        f'{frames_dir}/f_%04d.jpg','-loglevel','error'],
                       check=False, timeout=60)
    n = len(os.listdir(frames_dir))
    print(f'    ✅ extracted {n} frames @ 1fps')

    # Base avatar frame: the middle frame (likely the cleanest, mid-action)
    if n > 0:
        files = sorted(os.listdir(frames_dir))
        mid = files[len(files)//2]
        base = f'{run_dir}/{vid}_base.jpg'
        subprocess.run(['cp', f'{frames_dir}/{mid}', base], check=False)
        print(f'    ✅ base avatar frame → {base}')

downloaded = sum(1 for c in candidates if os.path.exists(f"{run_dir}/source_{c['id']}.mp4"))
print(f'\n  Downloaded {downloaded} / {len(candidates)}')
PY
