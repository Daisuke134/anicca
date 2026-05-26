// G.711 mu-law codec + linear resampling between Twilio (8kHz mulaw)
// and Gemini Live (PCM16 16kHz in / 24kHz out). Pure JS, no native deps.

const BIAS = 0x84;
const CLIP = 32635;

export function mulawDecodeSample(uVal) {
  uVal = ~uVal & 0xff;
  let t = ((uVal & 0x0f) << 3) + BIAS;
  t <<= (uVal & 0x70) >> 4;
  return (uVal & 0x80) ? (BIAS - t) : (t - BIAS);
}

export function mulawEncodeSample(sample) {
  let sign = sample < 0 ? 0x80 : 0;
  if (sign) sample = -sample;
  if (sample > CLIP) sample = CLIP;
  sample += BIAS;
  let exponent = 7;
  for (let mask = 0x4000; (sample & mask) === 0 && exponent > 0; exponent--, mask >>= 1) {}
  const mantissa = (sample >> (exponent + 3)) & 0x0f;
  return ~(sign | (exponent << 4) | mantissa) & 0xff;
}

// Twilio mulaw bytes -> Int16 PCM (8kHz)
export function mulawBufToPcm16(buf) {
  const out = new Int16Array(buf.length);
  for (let i = 0; i < buf.length; i++) out[i] = mulawDecodeSample(buf[i]);
  return out;
}

// Int16 PCM -> Twilio mulaw bytes
export function pcm16ToMulawBuf(pcm) {
  const out = Buffer.allocUnsafe(pcm.length);
  for (let i = 0; i < pcm.length; i++) out[i] = mulawEncodeSample(pcm[i]);
  return out;
}

// Upsample PCM16 8kHz -> 16kHz (factor 2, linear interpolation)
export function upsample8to16(pcm) {
  const out = new Int16Array(pcm.length * 2);
  for (let i = 0; i < pcm.length; i++) {
    const cur = pcm[i];
    const next = i + 1 < pcm.length ? pcm[i + 1] : cur;
    out[i * 2] = cur;
    out[i * 2 + 1] = (cur + next) >> 1;
  }
  return out;
}

// Downsample PCM16 24kHz -> 8kHz (factor 3, 3-sample average to limit aliasing)
export function downsample24to8(pcm) {
  const n = Math.floor(pcm.length / 3);
  const out = new Int16Array(n);
  for (let i = 0; i < n; i++) {
    const a = pcm[i * 3], b = pcm[i * 3 + 1], c = pcm[i * 3 + 2];
    out[i] = ((a + b + c) / 3) | 0;
  }
  return out;
}

export function int16ToBuffer(int16) {
  return Buffer.from(int16.buffer, int16.byteOffset, int16.byteLength);
}

export function bufferToInt16(buf) {
  return new Int16Array(buf.buffer, buf.byteOffset, Math.floor(buf.byteLength / 2));
}
