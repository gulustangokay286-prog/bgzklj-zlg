# -*- coding: utf-8 -*-
"""session_store.py — where a remembered sign-in actually lives.

The session used to be kept in exactly one file, ~/.chenki_akademi/
bgz_auth_token.json. That is one HOME resolution away from being lost.
An update relaunches through Launcher.exe, and if that relaunch lands in
a different context than the one that signed in — elevated, a service
account, a roaming profile that did not follow the machine — then `~`
resolves somewhere else, the file is not there, and someone who ticked
"beni hatırla" is asked to sign in again. From the outside that looks
exactly like the update forgetting them, which is the reported symptom.

So the session is mirrored: it is written to every location that turns
out to be writable, and read back from whichever copy is newest. Losing
one location no longer loses the session. Nothing here decides *whether*
to remember — that is the checkbox's job, recorded as the "remember" key
inside the payload — this module only makes the answer survive.

The primary path is unchanged and still written first, so an older build
reading only that file sees exactly what it always did.
"""
import json
import os
import sys
import time

FILENAME = "bgz_auth_token.json"
_APP_DIR = "BKPlanner"


def _primary_dir() -> str:
    """~/.chenki_akademi — the path every other module already uses."""
    return os.path.join(os.path.expanduser("~"), ".chenki_akademi")


def _install_state_dir():
    """<ROOT>/State when running from an installed build.

    Derived from sys.executable rather than by importing bk_update, which
    pulls in the whole update engine; this module is imported during
    startup auth, well before any of that is wanted.
    """
    if not getattr(sys, "frozen", False):
        return None
    try:
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        root = os.path.dirname(os.path.dirname(exe_dir))
        if os.path.isdir(os.path.join(root, "State")) and os.path.isdir(os.path.join(root, "Versions")):
            return os.path.join(root, "State")
    except Exception:
        pass
    return None


def candidate_dirs() -> list:
    """Every place worth keeping a copy, most-canonical first."""
    dirs = [_primary_dir()]

    if os.name == "nt":
        for var in ("LOCALAPPDATA", "APPDATA", "PROGRAMDATA"):
            base = os.environ.get(var)
            if base:
                dirs.append(os.path.join(base, _APP_DIR))
    elif sys.platform == "darwin":
        dirs.append(os.path.join(os.path.expanduser("~"), "Library",
                                 "Application Support", _APP_DIR))
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
        dirs.append(os.path.join(base, _APP_DIR))

    state = _install_state_dir()
    if state:
        dirs.append(state)

    seen, out = set(), []
    for d in dirs:
        key = os.path.normcase(os.path.abspath(d))
        if key not in seen:
            seen.add(key)
            out.append(d)
    return out


def primary_path() -> str:
    return os.path.join(_primary_dir(), FILENAME)


def write(data: dict) -> int:
    """Mirrors the session everywhere it will go. Returns how many copies
    landed; 0 means the session will not survive this process, which the
    caller may want to say out loud."""
    if not isinstance(data, dict):
        return 0
    payload = dict(data)
    payload["_saved_at"] = int(time.time())

    written = 0
    for d in candidate_dirs():
        try:
            os.makedirs(d, exist_ok=True)
            tmp = os.path.join(d, FILENAME + ".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            os.replace(tmp, os.path.join(d, FILENAME))
            written += 1
        except Exception:
            continue
    return written


def read():
    """The newest surviving copy, or None. Copies without a timestamp are
    from before this module existed and rank oldest, so a freshly written
    mirror always wins over one of them."""
    best, best_ts = None, -1
    for d in candidate_dirs():
        try:
            with open(os.path.join(d, FILENAME), "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        if not (data.get("access_token") or data.get("email")):
            continue
        ts = data.get("_saved_at")
        ts = int(ts) if isinstance(ts, (int, float)) else 0
        if ts > best_ts:
            best, best_ts = data, ts
    return best


def heal() -> bool:
    """Puts the newest copy back into any location that has lost it. Called
    on a successful restore so one surviving mirror repopulates the rest."""
    data = read()
    if data is None:
        return False
    write(data)
    return True


def clear() -> None:
    for d in candidate_dirs():
        try:
            path = os.path.join(d, FILENAME)
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            continue
