---
name: premiere
description: Drive a local Adobe Premiere Pro from the command line - open a project, list clips, retime them, export an mp4, and run Project Manager to collect a deliverable folder. Use when a video gig requires an editable Premiere project as the deliverable, not just a rendered file.
---

# premiere

`premiere-cli.mjs` drives Premiere through the MCP CEP bridge
(`adobe-premiere-pro-mcp`). It exists because three failure modes cost hours
twice, and each one now has its answer compiled into the tool.

## Commands

```bash
CLI=~/anicca/skills/premiere/premiere-cli.mjs

node $CLI doctor                       # reachable? healthy pid? prior traffic?
node $CLI launch --project FILE        # forces a NEW instance (open -n)
node $CLI open FILE.prproj
node $CLI info
node $CLI graphics                     # every clip: track, index, name, start, end
node $CLI retime SPEC.json
node $CLI export OUT.mp4 [--preset EPR]
node $CLI collect DEST_DIR
node $CLI close
node $CLI eval 'return String(app.project.name);'
```

Always run `doctor` first. It exits non-zero when the bridge cannot answer, so a
loop can stop before doing damage.

## The three traps

**1. One bridge directory: `/tmp/premiere-mcp-bridge`.**
The bridge is a FILE channel. Point it anywhere else and every call fails with
`Bridge response timeout` and no other hint. The CLI sets `PREMIERE_TEMP_DIR`
itself, so never set it from outside. That directory holds the responses
Premiere wrote during the working runs on 2026-08-16, which is how the path was
confirmed.

**2. The CEP panel is invisible on purpose.**
`AutoVisible=false` / `Type=Custom`, so it never shows under
Window > Extensions. It auto-starts anyway. Do NOT "fix" the manifest - the
2026-08-17 03:03 export succeeded with it exactly as shipped. If the bridge is
unreachable, the cause is a wedged Premiere, not the manifest.

**3. Premiere can wedge in an uninterruptible exit.**
`ps -o stat` shows `UE`; `kill -9` does nothing and `open -a` silently refuses
to start a replacement. `doctor` filters those pids out, and `launch` uses
`open -n` to force a separate instance. The wedged one can be ignored.

## Project Manager settings live on `pm.options`

Setting them on `pm` itself makes `process()` return `"0"` while producing
nothing - a silent no-op that reads exactly like success. `collect` therefore
checks that a `.prproj` actually landed in the destination and fails if not.
Never trust `processResult` alone.

## Retime spec

```json
[{ "name": "グラフィック", "track": 3, "start": 5.16, "end": 7.34 }]
```

Move clips on one track from the LAST one backwards when targets shift later,
or a clip lands on a neighbour that has not moved yet.

## What this does not do

It does not edit the text inside a Premiere text graphic - that content is
binary in the `.prproj` and is not reachable from ExtendScript. When captions
need different wording or different line breaks, render them as PNG overlays and
place those instead. That is how the LBJ v107 package was built: the baked-in
graphics were deleted and 15 approved PNGs were placed at measured times.

## Packaging a deliverable

After `collect`, add a preview mp4 and a readme inside the collected folder,
then zip with Python's `zipfile` setting `flag_bits |= 0x800`. macOS `zip`
writes Japanese filenames without the UTF-8 flag and a Windows client sees
mojibake.
