/**
 * no-human.mjs — D4 audit: prove the slot has ZERO human-in-the-loop steps.
 *
 * The loop spawns run.sh with stdin IGNORED, so the slot CANNOT block on human input.
 * This audit is defense-in-depth: it scans the slot's EXECUTABLE files for any pattern
 * that implies waiting on a human, and fails the build if found. A skill with a human
 * step cannot be a slot (CC contract #2). No-human MECHANISMS the slot relies on:
 *   captcha → CapSolver (CAPSOLVER_API_KEY)   OTP/codes → gog gmail / AgentMail auto-read
 *   login   → stored creds (~/.openclaw/.env)  publish → CDP browser (daily-driver) autonomous
 *   keys    → loop scrubs *_WALLET_KEY; wallet read as ADDRESS from standard path
 *
 * Pure: caller passes file contents; auditNoHuman returns violations[].
 */

// Patterns that imply a human step in EXECUTABLE code (stdin reads / interactive prompts /
// explicit "ask a human" instructions). Comments/docs are stripped before scanning.
const FORBIDDEN = [
  { re: /process\.stdin/i, why: 'reads stdin (would block on human input)' },
  { re: /readline|prompts?\(|inquirer/i, why: 'interactive prompt library' },
  { re: /read\s+-p|read\s+-r?p/i, why: 'bash read -p (human prompt)' },
  { re: /\bask (the )?(user|human|dais)\b/i, why: 'asks a human' },
  { re: /wait(ing)? for (a )?(human|user|dais|approval|manual)/i, why: 'waits for human approval' },
  { re: /manual(ly)? (enter|type|tap|click|solve|input)/i, why: 'requires manual human action' },
  { re: /please (enter|provide|tap|click|confirm)/i, why: 'requests human to act' },
];

function stripComments(src, ext) {
  let s = src;
  if (ext === 'sh') s = s.split('\n').map(l => l.replace(/(^|\s)#.*$/, '$1')).join('\n');
  else { s = s.replace(/\/\*[\s\S]*?\*\//g, ' ').split('\n').map(l => l.replace(/\/\/.*$/, '')).join('\n'); }
  return s;
}

/** @param {{path:string, content:string}[]} files → violations[] */
export function auditNoHuman(files) {
  const v = [];
  for (const f of files) {
    const ext = f.path.endsWith('.sh') ? 'sh' : 'mjs';
    const code = stripComments(f.content, ext);
    for (const { re, why } of FORBIDDEN) {
      if (re.test(code)) v.push({ path: f.path, why });
    }
  }
  return v;
}
