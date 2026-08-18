#!/usr/bin/env node
/**
 * premiere-cli - drive a local Adobe Premiere Pro through the MCP CEP bridge.
 *
 * Why this exists: the same three mistakes cost hours twice. They are now
 * impossible to repeat because the CLI hard-codes the answers.
 *
 *   1. The bridge talks over FILES in ONE directory. It is /tmp/premiere-mcp-bridge,
 *      the path `premiere-pro-mcp --install-cep` prepares. Point it anywhere else
 *      and every call dies with "Bridge response timeout" and no other clue.
 *      Proof it is the right one: that directory holds the responses Premiere
 *      wrote during the working v76-v79 runs on 2026-08-16.
 *   2. The CEP panel has AutoVisible=false / Type=Custom, so it never appears in
 *      Window > Extensions. That is BY DESIGN - it auto-starts invisibly. Do not
 *      "fix" the manifest; the 2026-08-17 03:03 export succeeded with it as-is.
 *   3. Premiere can wedge in an uninterruptible exit (ps STAT "UE") that kill -9
 *      cannot clear. `open -a` then refuses to start a replacement. Use
 *      `premiere-cli launch` which forces a separate instance with `open -n`.
 *
 * Usage:
 *   premiere-cli doctor
 *   premiere-cli launch [--project FILE]
 *   premiere-cli open FILE
 *   premiere-cli info
 *   premiere-cli graphics                 # every text graphic with track/clip/time
 *   premiere-cli retime SPEC.json         # move/trim clips by clip name
 *   premiere-cli export OUT.mp4 [--preset EPR]
 *   premiere-cli collect DEST_DIR
 *   premiere-cli close
 *   premiere-cli eval 'return String(app.project.name);'
 */
import { PremiereProBridge } from '/opt/homebrew/lib/node_modules/adobe-premiere-pro-mcp/dist/bridge/index.js';
import { execFileSync, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const BRIDGE_DIR = '/tmp/premiere-mcp-bridge';
const APP = 'Adobe Premiere Pro 2026';
const DEFAULT_PRESET =
  '/Applications/Adobe Premiere Pro 2026/Adobe Premiere Pro 2026.app/Contents/Settings/IngestPresets/Transcode/Match Source - H.264 High Bitrate.epr';

process.env.PREMIERE_TEMP_DIR = BRIDGE_DIR;

function die(msg) {
  console.error(`premiere-cli: ${msg}`);
  process.exit(1);
}

function healthyPids() {
  const out = spawnSync('pgrep', ['-x', APP], { encoding: 'utf8' }).stdout || '';
  return out
    .split('\n')
    .filter(Boolean)
    .filter((pid) => {
      const st = spawnSync('ps', ['-o', 'stat=', '-p', pid], { encoding: 'utf8' }).stdout.trim();
      return st && !st.includes('E'); // "UE"/"ZE" = exiting; not usable
    });
}

async function connect() {
  if (!fs.existsSync(BRIDGE_DIR)) fs.mkdirSync(BRIDGE_DIR, { recursive: true });
  if (healthyPids().length === 0) die(`no healthy ${APP} process. run: premiere-cli launch`);
  const bridge = new PremiereProBridge();
  await bridge.initialize();
  return bridge;
}

async function run(script, timeout = 180000) {
  const bridge = await connect();
  const raw = await bridge.executeScript(script, timeout);
  const text = typeof raw === 'string' ? raw : raw && raw.result !== undefined ? raw.result : raw;
  try {
    return typeof text === 'string' && text.trim().startsWith('{') ? JSON.parse(text) : text;
  } catch {
    return text;
  }
}

const cmds = {
  async doctor() {
    const pids = healthyPids();
    const responses = fs.existsSync(BRIDGE_DIR)
      ? fs.readdirSync(BRIDGE_DIR).filter((f) => f.startsWith('response-')).length
      : 0;
    let reachable = false;
    if (pids.length) {
      try {
        await run('return "ping";', 45000);
        reachable = true;
      } catch {
        reachable = false;
      }
    }
    console.log(JSON.stringify({ bridgeDir: BRIDGE_DIR, healthyPids: pids, priorResponses: responses, reachable }, null, 1));
    if (!reachable) process.exit(2);
  },

  async launch(args) {
    // `open -n` because a wedged instance makes plain `open -a` a no-op
    const project = args.includes('--project') ? args[args.indexOf('--project') + 1] : null;
    const argv = ['-n', '-a', APP];
    if (project) argv.push(project);
    execFileSync('open', argv);
    console.log(JSON.stringify({ launched: true, project: project || null }));
  },

  async open(args) {
    const file = args[0];
    if (!file || !fs.existsSync(file)) die(`project not found: ${file}`);
    const r = await run(
      `var ok = app.openDocument(${JSON.stringify(path.resolve(file))});
       return JSON.stringify({openResult: String(ok)});`,
      300000,
    );
    console.log(JSON.stringify(r));
    if (!r || String(r.openResult) !== 'true') process.exit(3);
  },

  async info() {
    console.log(
      JSON.stringify(
        await run(`var s = app.project.activeSequence;
        return JSON.stringify({
          project: String(app.project.name),
          path: String(app.project.path),
          sequence: s ? String(s.name) : null,
          videoTracks: s ? s.videoTracks.numTracks : null,
          audioTracks: s ? s.audioTracks.numTracks : null
        });`),
        null,
        1,
      ),
    );
  },

  async graphics() {
    console.log(
      JSON.stringify(
        await run(
          `var s = app.project.activeSequence, rows = [];
           for (var t = 0; t < s.videoTracks.numTracks; t++) {
             var tr = s.videoTracks[t];
             for (var c = 0; c < tr.clips.numItems; c++) {
               var cl = tr.clips[c];
               rows.push({track: t, clip: c, name: String(cl.name),
                          start: Number(cl.start.seconds), end: Number(cl.end.seconds)});
             }
           }
           return JSON.stringify({count: rows.length, clips: rows});`,
          240000,
        ),
        null,
        1,
      ),
    );
  },

  async retime(args) {
    const spec = args[0];
    if (!spec || !fs.existsSync(spec)) die(`spec not found: ${spec}`);
    // [{ "name": "...", "track": 3, "start": 5.16, "end": 7.34 }, ...]
    const moves = JSON.parse(fs.readFileSync(spec, 'utf8'));
    const r = await run(
      `var moves = ${JSON.stringify(moves)};
       var s = app.project.activeSequence, done = [], missed = [];
       for (var i = 0; i < moves.length; i++) {
         var m = moves[i], hit = false;
         var tr = s.videoTracks[m.track];
         for (var c = 0; c < tr.clips.numItems && !hit; c++) {
           var cl = tr.clips[c];
           if (String(cl.name) !== String(m.name)) continue;
           cl.start = m.start; cl.end = m.end;
           done.push({name: m.name, start: m.start, end: m.end}); hit = true;
         }
         if (!hit) missed.push(m.name);
       }
       return JSON.stringify({moved: done.length, missing: missed});`,
      300000,
    );
    console.log(JSON.stringify(r, null, 1));
    if (r && r.missing && r.missing.length) process.exit(4);
  },

  async export(args) {
    const out = args[0];
    if (!out) die('usage: premiere-cli export OUT.mp4 [--preset EPR]');
    const preset = args.includes('--preset') ? args[args.indexOf('--preset') + 1] : DEFAULT_PRESET;
    if (!fs.existsSync(preset)) die(`preset not found: ${preset}`);
    fs.mkdirSync(path.dirname(path.resolve(out)), { recursive: true });
    const r = await run(
      `var s = app.project.activeSequence;
       var res = s.exportAsMediaDirect(${JSON.stringify(path.resolve(out))},
                                       ${JSON.stringify(preset)}, app.encoder.ENCODE_ENTIRE);
       return JSON.stringify({exportResult: String(res), outputPath: ${JSON.stringify(path.resolve(out))}});`,
      1800000,
    );
    console.log(JSON.stringify(r, null, 1));
    if (!fs.existsSync(path.resolve(out))) die('export reported but file is missing');
    console.log(JSON.stringify({ bytes: fs.statSync(path.resolve(out)).size }));
  },

  async collect(args) {
    const dest = args[0];
    if (!dest) die('usage: premiere-cli collect DEST_DIR');
    fs.mkdirSync(path.resolve(dest), { recursive: true });
    // Settings live on pm.OPTIONS, not on pm itself. Writing them on pm makes
    // process() return "0" while producing nothing at all - a silent no-op that
    // looks exactly like success. Verified against work/premiere-v98-project-manager.mjs,
    // the script whose run on 2026-08-17 03:10 produced a real collected folder.
    const target = path.resolve(dest);
    const r = await run(
      `var pm = app.projectManager, o = pm.options;
       o.destinationPath = ${JSON.stringify(target)};
       o.includeAllSequences = true;
       o.excludeUnused = true;
       o.clipTransferOption = o.CLIP_TRANSFER_COPY;
       o.includePreviews = false;
       o.includeConformedAudio = false;
       o.renameMedia = false;
       o.convertAECompsToClips = false;
       o.convertImageSequencesToClips = false;
       o.convertSyntheticsToClips = false;
       var seq = app.project.activeSequence;
       if (!seq) throw new Error('no active sequence');
       var res = pm.process(app.project, seq);
       var errs = [];
       for (var k in pm.errors) errs.push(String(pm.errors[k]));
       return JSON.stringify({processResult: String(res), errorCount: errs.length,
                              errors: errs, destination: ${JSON.stringify(target)}});`,
      3600000,
    );
    console.log(JSON.stringify(r, null, 1));
    if (!r || String(r.processResult) !== '0') process.exit(5);
    // process() lies on a no-op, so confirm a project file actually landed
    const found = fs.existsSync(target)
      ? fs.readdirSync(target).some((d) => {
          const p = path.join(target, d);
          return fs.statSync(p).isDirectory() && fs.readdirSync(p).some((f) => f.endsWith('.prproj'));
        })
      : false;
    console.log(JSON.stringify({ collectedProjectFound: found }));
    if (!found) die('collect reported success but no .prproj landed in the destination');
  },

  async close() {
    console.log(JSON.stringify(await run('app.project.closeDocument(0,0); return JSON.stringify({closed:true});', 120000)));
  },

  async eval(args) {
    console.log(JSON.stringify(await run(args.join(' '), 300000), null, 1));
  },
};

const [, , cmd, ...rest] = process.argv;
if (!cmd || !cmds[cmd]) die(`unknown command "${cmd || ''}". see --help in the header of this file`);
cmds[cmd](rest).catch((e) => die(e.message || String(e)));
