"""Read `codex remote-control start --json` output on stdin, print its status."""
import re
import sys

matches = re.findall(r'"status"\s*:\s*"([a-zA-Z]+)"', sys.stdin.read())
print(matches[0] if matches else "unknown")
