// Run with npm ci && CHROMIUM_PATH=/path/to/chrome npm test.
// Loads the shipping bytes in the official WASM runtime, without any CDN assets.
import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { chromium } from 'playwright-core';

const asset = new URL('../../aniccaios/Views/Feed/Rive/living_home.riv', import.meta.url);
const bytes = await readFile(asset);
assert.ok(bytes.length > 8, 'living_home.riv must be a real asset, not a placeholder');
assert.equal(bytes.subarray(0, 4).toString(), 'RIVE');
assert.equal(bytes[4], 7, 'Rive major version 7');
const runtime = new URL('node_modules/@rive-app/canvas-advanced/', import.meta.url);
const files = {
  '/': ['text/html', Buffer.from('<canvas width="390" height="844"></canvas>')],
  '/living_home.riv': ['application/octet-stream', bytes],
  '/runtime.mjs': ['text/javascript', await readFile(new URL('canvas_advanced.mjs', runtime))],
  '/rive.wasm': ['application/wasm', await readFile(new URL('rive_fallback.wasm', runtime))],
};
const server = createServer((req, res) => {
  const file = files[req.url];
  res.writeHead(file ? 200 : 404, { 'Content-Type': file?.[0] ?? 'text/plain' });
  res.end(file?.[1]);
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
let browser;
try {
  browser = await chromium.launch({
    executablePath: process.env.CHROMIUM_PATH,
    headless: true,
    args: ['--no-sandbox'],
  });
  const page = await browser.newPage();
  await page.goto(`http://127.0.0.1:${server.address().port}`);
  const result = await page.evaluate(async () => {
    const { default: Rive } = await import('/runtime.mjs');
    const rive = await Rive({ locateFile: () => '/rive.wasm' });
    const file = await rive.load(new Uint8Array(await (await fetch('/living_home.riv')).arrayBuffer()), undefined, false);
    const require = (condition, message) => { if (!condition) throw Error(message); };
    require(file, 'Official runtime must import the asset');
    const artboard = file.artboardByName('LivingHome');
    require(artboard, 'LivingHome artboard');
    const definition = artboard.stateMachineByName('Living');
    require(definition, 'Living state machine');
    const machine = new rive.StateMachineInstance(definition, artboard);
    const control = file.artboardByName('LivingHome');
    const controlMachine = new rive.StateMachineInstance(control.stateMachineByName('Living'), control);
    const trigger = Array.from({ length: machine.inputCount() }, (_, i) => machine.input(i))
      .find(input => input.name === 'WordChanged');
    require(trigger?.type === rive.SMIInput.trigger, 'WordChanged must be a trigger');
    const canvas = document.querySelector('canvas');
    const renderer = rive.makeRenderer(canvas);
    const states = [];
    const step = seconds => {
      for (let i = 0; i < Math.round(seconds * 60); i++) {
        machine.advance(1 / 60);
        artboard.advance(1 / 60);
        controlMachine.advance(1 / 60);
        control.advance(1 / 60);
        for (let j = 0; j < machine.stateChangedCount(); j++) states.push(machine.stateChangedNameByIndex(j));
      }
    };
    const pixels = (target = artboard) => {
      renderer.clear();
      target.draw(renderer);
      rive.resolveAnimationFrame();
      return canvas.getContext('2d').getImageData(0, 0, 390, 844).data;
    };
    const diff = (a, b) => a.reduce((n, value, i) => n + (value !== b[i] ? 1 : 0), 0);
    step(1 / 60);
    require(states.includes('Ambient'), 'Entry must start Ambient');
    const first = pixels();
    require(first.some((v, i) => i % 4 === 3 && v > 0), 'Artwork must draw visible pixels');
    require(first.some((v, i) => i % 4 === 3 && v === 0), 'Artwork must preserve transparency');
    const startX = artboard.node('Sage').x;
    step(4);
    const ambientDifference = diff(first, pixels());
    require(ambientDifference > 1000, 'Ambient must visibly animate');
    require(Math.abs(artboard.node('Sage').x - startX) > 1, 'Ambient must move shapes');
    trigger.asTrigger().fire();
    step(0.2);
    require(states.includes('WordChange'), 'WordChanged must enter WordChange');
    const pulsePixels = pixels();
    const preview = canvas.toDataURL('image/png');
    const pulseDifference = diff(pulsePixels, pixels(control));
    require(pulseDifference > 1000, 'WordChanged must visibly change pixels against the untriggered control');
    const pulseScale = artboard.node('Ripple').scaleX;
    trigger.asTrigger().fire();
    step(1 / 60);
    require(artboard.node('Ripple').scaleX < pulseScale, 'Trigger during pulse must restart it');
    step(0.8);
    require(states.at(-1) === 'Rest', 'Pulse must return to Rest with Ambient still running');
    require(diff(pixels(), pixels(control)) === 0, 'Ripple must disappear without resetting Ambient');
    trigger.asTrigger().fire();
    step(0.2);
    require(states.at(-1) === 'WordChange', 'Later triggers must still work');
    step(24);
    require(pixels().some((v, i) => i % 4 === 3 && v > 0), 'Ambient must continue after multiple loops');
    const result = { artboard: 'LivingHome', machine: 'Living', trigger: trigger.name,
      ambientDifference, pulseDifference, states, animations: artboard.animationCount(), preview };
    machine.delete(); controlMachine.delete(); artboard.delete(); control.delete(); file.delete(); renderer.delete();
    return result;
  });
  const { preview, ...evidence } = result;
  if (process.env.RIVE_PREVIEW_PATH) {
    await writeFile(process.env.RIVE_PREVIEW_PATH, Buffer.from(preview.split(',')[1], 'base64'));
  }
  console.log(JSON.stringify({ bytes: bytes.length, ...evidence }, null, 2));
} finally {
  await browser?.close();
  await new Promise(resolve => server.close(resolve));
}
