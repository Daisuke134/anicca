const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const https = require('https');

const ROOT = '/Users/anicca/.openclaw/workspace/tiktok-marketing';
const WORK = '/Users/anicca/anicca-project/work/reelclaw-widget-en-92c13cc2';
const ENV_PATH = '/Users/anicca/.openclaw/.env';
const HOOK_SRC = path.join(ROOT, 'work/reelclaw-ja-1/hooks/hook-trim.mp4');
const DEMO_SRC = '/Users/anicca/anicca-project/assets/reelclaw/en-widget-videos/styaling-up-late.MP4';
const BGM = path.join(ROOT, 'music/bgm-cta.mp3');
const FONT_EN = '/Users/anicca/Library/Fonts/TikTokSansDisplayBold.ttf';
const CAPTION = 'how to put affirmations on your lockscreen\n\n#affirmations #lockscreen #selfcare #mentalhealth #selflove #fyp';
const TIKTOK_ID = 'cmn8y47do02mmo70yckb46dyu';
const INSTAGRAM_ID = 'cmn8y95rg02d2qx0y09bbk5pb';
const ROTATION_PATH = path.join(ROOT, 'reelclaw-widget-rotation.json');
const OUT = path.join(WORK, 'reel-final.mp4');
const HOOK_OUT = path.join(WORK, 'hook-trimmed.mp4');
const DEMO_OUT = path.join(WORK, 'demo-as-is.mp4');
const CONCAT_OUT = path.join(WORK, 'reel-text.mp4');

function sh(cmd, args) { execFileSync(cmd, args, { stdio: 'inherit' }); }
function loadEnv() {
  const text = fs.readFileSync(ENV_PATH, 'utf8');
  for (const line of text.split(/\r?\n/)) {
    const m = line.match(/^([A-Za-z_][A-Za-z0-9_]*)=(.*)$/);
    if (!m) continue;
    const k = m[1];
    let v = m[2];
    if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) v = v.slice(1, -1);
    process.env[k] = v;
  }
}
function upload(filePath, filename) {
  return new Promise((resolve, reject) => {
    const boundary = '----openclaw' + Date.now();
    const file = fs.readFileSync(filePath);
    const head = Buffer.from(`--${boundary}\r\nContent-Disposition: form-data; name="file"; filename="${filename}"\r\nContent-Type: video/mp4\r\n\r\n`);
    const tail = Buffer.from(`\r\n--${boundary}--\r\n`);
    const body = Buffer.concat([head, file, tail]);
    const req = https.request({ hostname: 'api.postiz.com', path: '/public/v1/upload', method: 'POST', headers: { Authorization: process.env.POSTIZ_API_KEY, 'Content-Type': `multipart/form-data; boundary=${boundary}`, 'Content-Length': body.length } }, res => {
      let out=''; res.on('data', c => out += c); res.on('end', () => { if (res.statusCode >= 200 && res.statusCode < 300) resolve(JSON.parse(out)); else reject(new Error(`upload failed ${res.statusCode}: ${out}`)); });
    });
    req.on('error', reject); req.write(body); req.end();
  });
}
function postJson(body) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const req = https.request({ hostname: 'api.postiz.com', path: '/public/v1/posts', method: 'POST', headers: { Authorization: process.env.POSTIZ_API_KEY, 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) } }, res => {
      let out=''; res.on('data', c => out += c); res.on('end', () => { if (res.statusCode >= 200 && res.statusCode < 300) resolve(JSON.parse(out)); else reject(new Error(`post failed ${res.statusCode}: ${out}`)); });
    });
    req.on('error', reject); req.write(data); req.end();
  });
}
(async () => {
  loadEnv();
  if (!process.env.POSTIZ_API_KEY) throw new Error('POSTIZ_API_KEY missing');
  sh('ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', '-i', HOOK_SRC, '-ss', '0', '-to', '3', '-vf', `scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps=30,drawtext=text=Put affirmations:fontfile=${FONT_EN}:fontsize=44:fontcolor=white:borderw=4:bordercolor=black:x=(60+(900-text_w)/2):y=320:enable='between(t,0,2.8)',drawtext=text=on your lockscreen:fontfile=${FONT_EN}:fontsize=44:fontcolor=white:borderw=4:bordercolor=black:x=(60+(900-text_w)/2):y=380:enable='between(t,0,2.8)'`, '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-movflags', '+faststart', HOOK_OUT]);
  sh('ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', '-i', DEMO_SRC, '-vf', 'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps=30', '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-movflags', '+faststart', DEMO_OUT]);
  sh('ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', '-i', HOOK_OUT, '-i', DEMO_OUT, '-filter_complex', '[0:v][1:v]concat=n=2:v=1:a=0[outv]', '-map', '[outv]', '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-movflags', '+faststart', CONCAT_OUT]);
  const duration = Number(execFileSync('ffprobe', ['-v', 'quiet', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', CONCAT_OUT], { encoding: 'utf8' }).trim());
  const fadeOutStart = Math.max(0, Math.floor(duration - 1));
  sh('ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', '-i', CONCAT_OUT, '-i', BGM, '-map', '0:v', '-map', '1:a', '-af', `afade=t=in:st=0:d=0.5,afade=t=out:st=${fadeOutStart}:d=1,volume=0.8`, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k', '-shortest', '-movflags', '+faststart', OUT]);
  const uploaded = await upload(OUT, 'reel-final.mp4');
  const base = { type: 'now', date: new Date().toISOString(), shortLink: false, tags: [] };
  const tiktok = await postJson({ ...base, posts: [{ integration: { id: TIKTOK_ID }, value: [{ content: CAPTION, image: [{ id: uploaded.id, path: uploaded.path }] }], settings: { __type: 'tiktok-standalone', post_type: 'post', privacy_level: 'PUBLIC_TO_EVERYONE', content_posting_method: 'DIRECT_POST', autoAddMusic: 'no', duet: false, stitch: false, comment: false, brand_content_toggle: false, brand_organic_toggle: false } }] });
  fs.writeFileSync(path.join(WORK, 'tiktok-postiz-result.json'), JSON.stringify(tiktok, null, 2) + '\n');
  const instagram = await postJson({ ...base, posts: [{ integration: { id: INSTAGRAM_ID }, value: [{ content: CAPTION, image: [{ id: uploaded.id, path: uploaded.path }] }], settings: { __type: 'instagram-standalone', post_type: 'post', type: 'now' } }] });
  fs.writeFileSync(path.join(WORK, 'instagram-response.json'), JSON.stringify(instagram, null, 2) + '\n');
  const rotation = JSON.parse(fs.readFileSync(ROTATION_PATH, 'utf8'));
  rotation.lastUsed = rotation.lastUsed || {};
  rotation.lastUsed['reelclaw-anicca-en-widget-2'] = 'W4';
  rotation.history = rotation.history || [];
  rotation.history.push({ date: '2026-05-24', cron: 'reelclaw-anicca-en-widget-2', hookId: 'W4', demoVideo: 'styaling-up-late.MP4' });
  fs.writeFileSync(ROTATION_PATH, JSON.stringify(rotation, null, 2) + '\n');
  const summary = { hookId: 'W4', demoVideo: 'styaling-up-late.MP4', hookTrimmedToSeconds: 3, demoUntrimmed: true, hookPreserved: true, noCTA: true, tiktokDirectPostSucceeded: true, tiktok, instagram, uploaded };
  fs.writeFileSync(path.join(WORK, 'summary.json'), JSON.stringify(summary, null, 2) + '\n');
  console.log(JSON.stringify(summary, null, 2));
})().catch(err => { console.error(err); process.exit(1); });
