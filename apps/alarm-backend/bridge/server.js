import express from 'express';
import http from 'http';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { WebSocketServer } from 'ws';
import { GeminiLiveSession } from './geminiBridge.js';
import {
  mulawBufToPcm16, pcm16ToMulawBuf, upsample8to16, downsample24to8,
  int16ToBuffer, bufferToInt16
} from './audio.js';

const port = Number(process.env.PORT || 8787);
const publicBaseUrl = process.env.PUBLIC_BASE_URL || `http://localhost:${port}`;

function loadGeminiKey() {
  if (process.env.GEMINI_API_KEY) return process.env.GEMINI_API_KEY;
  const env = fs.readFileSync(path.join(os.homedir(), '.openclaw', '.env'), 'utf8');
  const m = env.match(/^GEMINI_API_KEY=(.*)$/m);
  if (!m) throw new Error('GEMINI_API_KEY missing');
  return m[1].trim().replace(/^['"]|['"]$/g, '');
}
const GEMINI_API_KEY = loadGeminiKey();

const app = express();
app.use(express.json());

app.get('/healthz', (_req, res) => {
  res.json({ ok: true, service: 'imokenet', mode: 'realtime-gemini', port, publicBaseUrl });
});

function xmlEscape(s) {
  return String(s).replace(/[<>&"']/g, c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;', "'": '&apos;' }[c]));
}

app.all('/twiml', (req, res) => {
  const name = xmlEscape(req.query.name || 'there');
  const mode = xmlEscape(req.query.mode || 'wakeup');
  const ctx = xmlEscape(req.query.ctx || '');
  // Derive the public wss URL from the request Host so it survives changing
  // tunnel URLs (Twilio fetches this over the public hostname).
  const host = req.headers['x-forwarded-host'] || req.headers.host;
  const wsBase = host
    ? `wss://${host}`
    : publicBaseUrl.replace('http://', 'ws://').replace('https://', 'wss://');
  const twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="${wsBase}/media-stream">
      <Parameter name="name" value="${name}" />
      <Parameter name="mode" value="${mode}" />
      <Parameter name="ctx" value="${ctx}" />
    </Stream>
  </Connect>
</Response>`;
  res.type('text/xml').send(twiml);
});

const server = http.createServer(app);
const wss = new WebSocketServer({ server, path: '/media-stream' });

// Send PCM16 24kHz from Gemini back to Twilio as 20ms mulaw frames.
function sendPcm24ToTwilio(ws, streamSid, pcm24Buffer) {
  const pcm24 = bufferToInt16(pcm24Buffer);
  const pcm8 = downsample24to8(pcm24);          // 24k -> 8k PCM16
  const mulaw = pcm16ToMulawBuf(pcm8);          // -> mulaw 8k
  const FRAME = 160;                            // 20ms @ 8kHz mulaw
  for (let i = 0; i < mulaw.length; i += FRAME) {
    const chunk = mulaw.subarray(i, i + FRAME);
    ws.send(JSON.stringify({
      event: 'media', streamSid, media: { payload: chunk.toString('base64') }
    }));
  }
}

wss.on('connection', (ws) => {
  let streamSid = null;
  let name = 'there';
  let gemini = null;

  ws.on('message', (buf) => {
    let msg;
    try { msg = JSON.parse(buf.toString()); } catch { return; }

    if (msg.event === 'start') {
      streamSid = msg.start?.streamSid || null;
      const cp = msg.start?.customParameters || {};
      name = cp.name || 'there';
      const mode = ['lateness', 'wakeup_generic'].includes(cp.mode) ? cp.mode : 'wakeup';
      const contextText = cp.ctx || '';
      const intensity = cp.intensity || '';   // B6: 'high' => extra-relentless wake persona
      console.log('[imokenet] stream start', { streamSid, callSid: msg.start?.callSid, name, mode, intensity });

      gemini = new GeminiLiveSession({ apiKey: GEMINI_API_KEY, name, mode, contextText, intensity });
      gemini.on('ready', () => console.log('[imokenet] gemini ready'));
      gemini.on('audio', (pcm24) => { if (streamSid) sendPcm24ToTwilio(ws, streamSid, pcm24); });
      gemini.on('interrupted', () => {
        console.log('[imokenet] gemini interrupted -> clear twilio buffer');
        if (streamSid) ws.send(JSON.stringify({ event: 'clear', streamSid }));
      });
      gemini.on('error', (e) => console.error('[imokenet] gemini error', e.message));
      gemini.on('close', (c) => console.log('[imokenet] gemini closed', c));
      gemini.connect();

    } else if (msg.event === 'media') {
      // Twilio inbound: mulaw 8kHz base64 -> PCM16 8k -> upsample 16k -> Gemini
      if (!gemini) return;
      const mulaw = Buffer.from(msg.media.payload, 'base64');
      const pcm8 = mulawBufToPcm16(mulaw);
      const pcm16k = upsample8to16(pcm8);
      gemini.sendAudio(int16ToBuffer(pcm16k));

    } else if (msg.event === 'stop') {
      console.log('[imokenet] stream stop', { streamSid });
      gemini?.close();
    }
  });

  ws.on('close', () => { console.log('[imokenet] websocket closed', { streamSid }); gemini?.close(); });
  ws.on('error', (e) => { console.error('[imokenet] ws error', e.message); gemini?.close(); });
});

server.listen(port, () => {
  console.log(`[imokenet] realtime-gemini bridge listening on :${port}`);
  console.log(`[imokenet] twiml endpoint: ${publicBaseUrl}/twiml?name=there`);
});
