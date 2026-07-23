import fs from 'node:fs';
import { spawn } from 'node:child_process';

const child = spawn(process.execPath, [
  '-e',
  'process.on("SIGTERM", () => {}); setInterval(() => {}, 1000);',
], { stdio: 'ignore' });

fs.writeFileSync(process.env.CHILD_PID_PATH, String(child.pid));
process.on('SIGTERM', () => {});
setInterval(() => {}, 1000);
