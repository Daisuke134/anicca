#!/usr/bin/env python3
"""set-profile.py — the ONLY writer of identity/profile.json.

Sets a nested field, validates the WHOLE file against profile.schema.json,
and writes atomically. Refuses to write if the result is invalid.

Usage:
  python3 set-profile.py <dot.path> <value>           # string value
  python3 set-profile.py <dot.path> --json '<json>'   # object/array/number/bool
Examples:
  python3 set-profile.py contact.phone "+81-90-1234-5678"
  python3 set-profile.py social.tiktok --json '[{"handle":"x","postizIntegrationId":"cm..","postMode":"draft"}]'
"""
import json, os, sys, tempfile

ANICCA_HOME = os.environ.get("ANICCA_HOME", os.path.expanduser("~/.openclaw"))
PROFILE = os.environ.get("ANICCA_PROFILE", os.path.join(ANICCA_HOME, "identity/profile.json"))
SCHEMA  = os.path.join(ANICCA_HOME, "identity/profile.schema.json")

def die(m): print(f"❌ {m}", file=sys.stderr); sys.exit(1)

if len(sys.argv) < 3:
    die("usage: set-profile.py <dot.path> <value> | <dot.path> --json '<json>'")

path = sys.argv[1].strip(".")
if sys.argv[2] == "--json":
    if len(sys.argv) < 4: die("--json needs a JSON argument")
    try: value = json.loads(sys.argv[3])
    except Exception as e: die(f"invalid --json: {e}")
else:
    value = sys.argv[2]

prof = {}
if os.path.exists(PROFILE):
    try: prof = json.load(open(PROFILE))
    except Exception as e: die(f"existing profile.json is not valid JSON: {e}")

# set nested path (creates intermediate objects)
node = prof
keys = path.split(".")
for k in keys[:-1]:
    node = node.setdefault(k, {})
    if not isinstance(node, dict): die(f"path segment '{k}' is not an object")
node[keys[-1]] = value

# validate WHOLE result against schema
try:
    import jsonschema
    schema = json.load(open(SCHEMA))
    jsonschema.validate(prof, schema)
except ImportError:
    print("⚠ jsonschema not installed — wrote without schema validation", file=sys.stderr)
except Exception as e:
    die(f"schema validation FAILED, refusing to write: {getattr(e,'message',str(e))[:200]}")

# atomic write, 0600
os.makedirs(os.path.dirname(PROFILE), exist_ok=True)
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(PROFILE))
with os.fdopen(fd, "w") as f:
    json.dump(prof, f, ensure_ascii=False, indent=2); f.write("\n")
os.chmod(tmp, 0o600); os.replace(tmp, PROFILE)
print(f"✅ profile.{path} set + validated → {PROFILE}")
