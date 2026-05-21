import http2 from 'http2';
import { SignJWT, importPKCS8 } from 'jose';
import baseLogger from '../../utils/logger.js';

const logger = baseLogger.withContext('ApnsClient');

function apnsHost(endpoint) {
  return endpoint === 'development'
    ? 'https://api.sandbox.push.apple.com'
    : 'https://api.push.apple.com';
}

export class ApnsError extends Error {
  constructor({ status, reason, apnsId, body }) {
    super(`APNs error: ${status} ${reason || ''}`.trim());
    this.name = 'ApnsError';
    this.status = status;
    this.reason = reason || null;
    this.apnsId = apnsId || null;
    this.body = body || null;
  }
}

export default class ApnsClient {
  constructor({ teamId, keyId, privateKeyP8, topic, endpoint }) {
    this.teamId = teamId;
    this.keyId = keyId;
    this.privateKeyP8 = privateKeyP8;
    this.topic = topic;
    this.endpoint = endpoint || 'production';

    this._jwt = null;
    this._jwtExpMs = 0;
    this._keyPromise = null;
  }

  static fromEnv() {
    const teamId = process.env.APNS_TEAM_ID || '';
    const keyId = process.env.APNS_KEY_ID || '';
    const topic = process.env.APNS_TOPIC || '';
    const endpointRaw = process.env.APNS_ENDPOINT || '';
    if (!endpointRaw) {
      // Require explicit endpoint to avoid sandbox/prod drift.
      throw new Error('Missing APNS_ENDPOINT (must be development|production)');
    }
    const endpoint = String(endpointRaw).toLowerCase();
    if (!['development', 'production'].includes(endpoint)) {
      throw new Error(`Invalid APNS_ENDPOINT: ${endpointRaw} (must be development|production)`);
    }

    const p8 = process.env.APNS_PRIVATE_KEY_P8 || '';
    if (!teamId || !keyId || !topic || !p8) {
      throw new Error('Missing APNs env vars (APNS_TEAM_ID/APNS_KEY_ID/APNS_TOPIC/APNS_PRIVATE_KEY_P8)');
    }
    return new ApnsClient({ teamId, keyId, privateKeyP8: p8, topic, endpoint });
  }

  async _getKey() {
    if (this._keyPromise) return this._keyPromise;
    const pkcs8 = String(this.privateKeyP8 || '').trim();
    // Support raw p8 content OR a single-line env with \n escapes.
    const normalized = pkcs8.replace(/\\n/g, '\n');
    this._keyPromise = importPKCS8(normalized, 'ES256');
    return this._keyPromise;
  }

  async _getJwt() {
    const now = Date.now();
    if (this._jwt && now < this._jwtExpMs - 60_000) return this._jwt;
    const key = await this._getKey();
    const iat = Math.floor(now / 1000);
    const exp = iat + 50 * 60; // 50min
    const jwt = await new SignJWT({})
      .setProtectedHeader({ alg: 'ES256', kid: this.keyId })
      .setIssuer(this.teamId)
      .setIssuedAt(iat)
      .setExpirationTime(exp)
      .sign(key);
    this._jwt = jwt;
    this._jwtExpMs = exp * 1000;
    return jwt;
  }

  async sendAlert({ deviceToken, payload, apnsIdempotencyKey }) {
    const jwt = await this._getJwt();
    const authority = apnsHost(this.endpoint);
    const client = http2.connect(authority);

    try {
      const body = JSON.stringify(payload);
      const headers = {
        ':method': 'POST',
        ':path': `/3/device/${deviceToken}`,
        authorization: `bearer ${jwt}`,
        'apns-topic': this.topic,
        'apns-push-type': 'alert',
        'apns-priority': '10',
      };
      if (apnsIdempotencyKey) headers['apns-collapse-id'] = String(apnsIdempotencyKey).slice(0, 64);

      const req = client.request(headers);

      let data = '';
      req.setEncoding('utf8');
      req.on('data', (chunk) => { data += chunk; });

      const result = await new Promise((resolve, reject) => {
        req.on('response', (respHeaders) => {
          req.on('end', () => resolve({ respHeaders, data }));
        });
        req.on('error', reject);
        req.end(body);
      });

      const status = Number(result.respHeaders[':status'] || 0);
      const apnsId = result.respHeaders['apns-id'] ? String(result.respHeaders['apns-id']) : null;

      if (status >= 200 && status < 300) {
        return { ok: true, apnsId };
      }

      let reason = null;
      try {
        const parsed = JSON.parse(result.data || '{}');
        reason = parsed?.reason || null;
      } catch {
        reason = null;
      }
      throw new ApnsError({ status, reason, apnsId, body: result.data });
    } finally {
      try { client.close(); } catch (e) { logger.debug('apns client close failed', e); }
    }
  }
}
