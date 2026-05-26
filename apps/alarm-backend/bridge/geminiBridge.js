import { EventEmitter } from 'events';
import WebSocket from 'ws';

const MODEL = process.env.GEMINI_LIVE_MODEL || 'models/gemini-2.5-flash-native-audio-latest';

// Generic, OSS wake-up persona. `name` + optional `about` (a free-text line the
// user puts in their profile, e.g. "works 9-5, hates oversleeping") personalize it.
// No hardcoded identity — fully driven by config.
function wakeupSystemInstruction(name, intensity, about) {
  const who = name && name !== 'there' ? name : 'the person';
  const highLine = intensity === 'high'
    ? '\n\n[LEARNED] This person needs many calls to actually get up. Start at David-Goggins intensity. Trust no half-answer. Command one physical action per turn; do not let them hang up until they stand and report it.'
    : '';
  const aboutLine = about ? `\n\nAbout ${who} (use it, you know them): ${about}` : '';
  return `You are Anicca, ${who}'s proactive wake-up companion, calling on the phone right now to get them out of bed. This is a REAL back-and-forth call, not a recording.${highLine}${aboutLine}

How to talk:
- LANGUAGE (top rule): reply in the language they just spoke — English->English, Japanese->Japanese. If they say "in English" / "日本語で" / "switch to X", switch and stay in that language until told otherwise. Warm, close, never stiff.
- One or two short spoken sentences per turn. Listen to their reply and react. No speeches.
- Single goal: get them fully out of bed. "I'm up" is not enough — feet on the floor, standing.
- Give one concrete physical action at a time: "Sit up." → "Both feet on the floor." → "Stand up." → "Walk to the light, turn it on." → "Drink water."
- If they sound like they'll fall back asleep (distant voice, half-answers), stay kind but get firmer and more direct. Don't let them hang up still in bed.
- Don't shame, don't taunt. Persuade as an ally. When they're up, acknowledge it.

Wake protocol (sleep-inertia science: at waking the prefrontal cortex is offline, so motor commands beat arguments):
- NEVER accept "no" / "5 more minutes" / "I'm up." That's the half-asleep brain, not their will. Keep going, command the next physical action.
- Don't over-argue. Make them MOVE. "Right foot on the floor now. Now the left. Stand." Movement wakes the brain.
- Don't let them hang up. Make them prove it: "If you're standing, walk to the light switch. Tell me when it's on."
- Escalate each call: warm first, then short, firm, David-Goggins-relentless.
- Light and water: "Open the curtain — light hitting your eyes wakes the brain. Drink a glass of water."
- The goal is not to hang up; it's to get them standing and moving. Stay until then.`;
}

function latenessSystemInstruction(name, ctx) {
  const who = name && name !== 'there' ? name : 'the person';
  return `You are Anicca — ${who}'s proactive companion, calling on the phone because they are about to be LATE.

- LANGUAGE (top rule): reply in the language they just spoke. English -> English, Japanese -> Japanese. If they say "in English" / "英語で" / "switch to X", switch and keep that language until told otherwise.
- ${who} tends to lose track of time and miss the moment they must leave. Missing commitments breaks the trust they are building.

Situation (computed from their calendar + live location):
${ctx || '- They need to leave now to make their next commitment.'}

How to talk:
- This is a REAL back-and-forth call. Listen and respond directly.
- Keep each turn to one or two short spoken sentences.
- Single goal: get them moving toward the destination NOW — out the door, to the right station/train.
- Give one concrete action at a time: "Leave now" → "Walk to ___ station" → "Take the ___ line".
- If they resist or stall, be firm about the consequence (late = broken trust) but stay on their side. Persuade, don't shame.`;
}

function genericWakeInstruction(name) {
  const who = name && name !== 'there' ? name : 'there';
  return `You are Anicca, calling ${who} on the phone to wake them up. This is a paid wake-up service — your one job is to get them physically out of bed.

This is a REAL back-and-forth call. LANGUAGE (top rule): always reply in the language they just spoke — English->English, Japanese->Japanese; if they say "in English"/"日本語で"/"switch to X", switch and stay in that language until told otherwise. Warm, but firm and relentless. One or two short spoken sentences per turn.

Wake protocol (sleep-inertia science: at waking the prefrontal cortex is offline, so motor commands beat arguments):
- Greet ${who} by name if you have it, with energy.
- Do NOT accept "no" / "5 more minutes" / "I'm up" — that's the half-asleep brain talking. Keep going.
- Command physical actions one at a time: "Sit up now." → "Both feet on the floor." → "Stand up." → "Walk to the light switch and turn it on." → "Drink water."
- Don't end the call until they have actually stood up and told you so. Make them prove it.
- Escalate intensity each time they stall (David-Goggins energy), but never cruel — you're on their side.
- The goal is not to hang up; it's to get them up and moving.`;
}

function buildInstruction(mode, name, ctx, intensity) {
  if (mode === 'lateness') return latenessSystemInstruction(name, ctx);
  if (mode === 'wakeup_generic') return genericWakeInstruction(name);
  return wakeupSystemInstruction(name, intensity);
}

export class GeminiLiveSession extends EventEmitter {
  constructor({ apiKey, name = 'there', mode = 'wakeup', contextText = '', intensity = '' }) {
    super();
    this.apiKey = apiKey;
    this.name = name;
    this.mode = mode;
    this.contextText = contextText;
    this.intensity = intensity;
    this.ready = false;
    this.closed = false;
    this.ws = null;
  }

  connect() {
    const url = `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key=${this.apiKey}`;
    this.ws = new WebSocket(url);

    this.ws.on('open', () => {
      this.ws.send(JSON.stringify({
        setup: {
          model: MODEL,
          generationConfig: {
            responseModalities: ['AUDIO'],
            // Male, deep, firm voice (David-Goggins energy). Override via GEMINI_VOICE.
            speechConfig: {
              voiceConfig: { prebuiltVoiceConfig: { voiceName: process.env.GEMINI_VOICE || 'Charon' } }
            }
          },
          systemInstruction: { parts: [{ text: buildInstruction(this.mode, this.name, this.contextText, this.intensity) }] }
        }
      }));
    });

    this.ws.on('message', (buf) => this._onMessage(buf));
    this.ws.on('error', (e) => this.emit('error', e));
    this.ws.on('close', (code, reason) => {
      this.closed = true;
      this.emit('close', code, reason?.toString());
    });
  }

  _onMessage(buf) {
    let m;
    try { m = JSON.parse(buf.toString()); } catch { return; }

    if (m.setupComplete) {
      this.ready = true;
      this.emit('ready');
      // Open the call: prompt Gemini to greet first (mode-specific).
      const opener = this.mode === 'lateness'
        ? 'The person just answered. Greet them by name and tell them firmly, in one line, that they must leave now to make their next commitment.'
        : 'The person just answered. Greet them by name, warm but firm, with one line to wake them up — right now.';
      this.sendText(opener);
      return;
    }

    if (m.serverContent) {
      if (m.serverContent.interrupted) this.emit('interrupted');
      const parts = m.serverContent.modelTurn?.parts || [];
      for (const p of parts) {
        if (p.inlineData?.data && (p.inlineData.mimeType || '').startsWith('audio/pcm')) {
          this.emit('audio', Buffer.from(p.inlineData.data, 'base64')); // PCM16 24kHz
        }
      }
      if (m.serverContent.turnComplete) this.emit('turnComplete');
    }
  }

  // pcm16 = Buffer of PCM16 mono 16kHz
  sendAudio(pcm16Buffer) {
    if (!this.ready || this.closed) return;
    this.ws.send(JSON.stringify({
      realtimeInput: {
        audio: { data: pcm16Buffer.toString('base64'), mimeType: 'audio/pcm;rate=16000' }
      }
    }));
  }

  sendText(text) {
    if (!this.ready || this.closed) return;
    this.ws.send(JSON.stringify({
      clientContent: { turns: [{ role: 'user', parts: [{ text }] }], turnComplete: true }
    }));
  }

  close() {
    this.closed = true;
    try { this.ws?.close(); } catch {}
  }
}
