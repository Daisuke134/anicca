"""state_io.py — atomic, corruption-resistant STATE I/O for the earn/video slot (FIND-603 / FIND-702).

Every write is atomic (tmp → os.replace, which is atomic on POSIX so a kill mid-write leaves either the
complete old or the complete new file — never a truncated one), and keeps a `.bak` of the prior VALID state.
load_or_init restores from `.bak` if the primary is missing/corrupt, re-initializing to day-0 ONLY as a last
resort — so a transient corruption never silently wipes warmup progress (FIND-702). Pure + file-only (testable).
"""
import json, os, shutil


def _read(p):
    if os.path.exists(p) and os.path.getsize(p) > 0:
        try:
            return json.load(open(p))
        except Exception:
            return None
    return None


def _atomic(path, d):
    # back up the current VALID primary first, so a future corruption can be restored from .bak
    if os.path.exists(path) and os.path.getsize(path) > 0:
        try:
            json.load(open(path))
            shutil.copyfile(path, path + ".bak")
        except Exception:
            pass
    t = path + ".tmp"
    with open(t, "w") as f:
        json.dump(d, f, ensure_ascii=False)
    os.replace(t, path)


def load_or_init(path, handle):
    """Return a valid state dict. Primary → .bak → fresh day-0 init (last resort)."""
    d = _read(path)
    restored = False
    if d is None:
        d = _read(path + ".bak")
        if d is not None:
            restored = True            # primary corrupt/missing but backup good → restore progress
    if d is None:
        d = {"handle": handle, "status": "warming", "warmup_day": 0, "affiliate_set": False}
    if _read(path) is None or restored:
        _atomic(path, d)               # heal the primary on disk
    return d


def update(path, patch):
    """Atomically merge `patch` into the on-disk state and return the new dict."""
    d = _read(path) or {}
    d.update(patch)
    _atomic(path, d)
    return d
