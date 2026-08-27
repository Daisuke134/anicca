// tty-shim.cjs — preloaded into the @nosana/cli poster child via NODE_OPTIONS="--require ...".
// The CLI calls TTY-only stdout APIs (moveCursor/clearLine/cursorTo) even when stdout is a pipe,
// crashing headless posters at the post-display step (observed live twice, 2026-07-25/26).
// No-op them when absent — display niceties die, the p2p definition server lives.
for (const stream of [process.stdout, process.stderr]) {
  if (typeof stream.moveCursor !== "function") stream.moveCursor = () => {};
  if (typeof stream.clearLine !== "function") stream.clearLine = () => {};
  if (typeof stream.cursorTo !== "function") stream.cursorTo = () => {};
}
