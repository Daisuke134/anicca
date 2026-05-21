#!/usr/bin/env node
/**
 * OpenClaw ローカル用: sessions.json 内の sessionFile を相対パス（ファイル名のみ）に正規化する。
 *
 * 原因: OpenClaw は resolvePathWithinSessionsDir で「sessionFile が sessions ディレクトリ内」を検証する。
 * sessionFile が絶対パスのままだと、gateway の OPENCLAW_STATE_DIR 等の解釈と食い違い、
 * "Session file path must be within sessions directory" になることがある。
 *
 * 用法: gateway 停止後に実行し、再起動する。
 *   node scripts/openclaw-vps/local-fix-session-path.js
 * または
 *   OPENCLAW_STATE_DIR=~/.openclaw node scripts/openclaw-vps/local-fix-session-path.js
 *
 * 参照: docs.openclaw.ai (Environment Variables, path-related env vars)
 *       ~/.openclaw/agents/<agentId>/sessions/sessions.json
 */
const fs = require('fs');
const path = require('path');

const stateDir = process.env.OPENCLAW_STATE_DIR?.trim()
  || path.join(process.env.HOME || process.env.USERPROFILE || '', '.openclaw');
const agentsDir = path.join(stateDir, 'agents');

if (!fs.existsSync(agentsDir)) {
  console.error('Agents dir not found:', agentsDir);
  process.exit(1);
}

const agentIds = fs.readdirSync(agentsDir, { withFileTypes: true })
  .filter((e) => e.isDirectory())
  .map((e) => e.name);

let totalFixed = 0;

for (const agentId of agentIds) {
  const sessionsPath = path.join(agentsDir, agentId, 'sessions', 'sessions.json');
  if (!fs.existsSync(sessionsPath)) continue;

  const sessionsDir = path.dirname(sessionsPath);
  const content = fs.readFileSync(sessionsPath, 'utf8');
  let data;
  try {
    data = JSON.parse(content);
  } catch (e) {
    console.warn('Skip (invalid JSON):', sessionsPath, e.message);
    continue;
  }

  let changed = false;
  let fileFixed = 0;

  for (const key of Object.keys(data)) {
    const entry = data[key];
    if (!entry || typeof entry.sessionFile !== 'string') continue;

    const raw = entry.sessionFile.trim();
    if (!raw) continue;
    // 絶対パスなら常に basename に正規化（別マシン/VPS のパスでも解消する）
    if (!path.isAbsolute(raw)) continue;

    const basename = path.basename(raw);
    if (basename === raw) continue;
    entry.sessionFile = basename;
    changed = true;
    fileFixed += 1;
    totalFixed += 1;
  }

  if (changed) {
    fs.writeFileSync(sessionsPath, JSON.stringify(data, null, 2) + '\n', 'utf8');
    console.log('Updated:', sessionsPath, '(' + fileFixed + ' sessionFile(s) normalized)');
  }
}

if (totalFixed === 0) {
  console.log('No absolute sessionFile paths to normalize in', stateDir);
} else {
  console.log('Done. Restart gateway and open http://127.0.0.1:18789/chat?session=agent%3Aanicca%3Amain');
}
