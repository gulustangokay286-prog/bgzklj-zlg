"""Apply to the existing VDS main.py after making a backup."""
from pathlib import Path
import sys


def patch(source):
    if "_desktop_sync_cache" in source:
        raise ValueError("Realtime patch is already applied")
    source = source.replace('import time\n', 'import time\nimport threading\n', 1)
    source = source.replace('@app.get("/api/sync/index")', '''
_desktop_sync_cache = None
_desktop_sync_generation = 0
_desktop_sync_lock = threading.Lock()


def _invalidate_desktop_sync():
    global _desktop_sync_cache, _desktop_sync_generation
    with _desktop_sync_lock:
        _desktop_sync_generation += 1
        _desktop_sync_cache = None


@app.get("/api/sync/index")''', 1)
    source = source.replace('    result = {}\n    dirty = []', '''    global _desktop_sync_cache
    with _desktop_sync_lock:
        generation = _desktop_sync_generation
        cached = _desktop_sync_cache
    if cached and time.monotonic() - cached[0] < 5:
        return cached[1]
    result = {}
    dirty = []''', 1)
    source = source.replace('                "hash": _cached_hash(hashes, key, payload),', '                "sync_revision": (payload.get("_sync_meta") or {}).get("revision", 0),\n                "hash": _cached_hash(hashes, key, payload),', 1)
    source = source.replace('    return result\n\n\n@app.get("/api/user/me")', '''    with _desktop_sync_lock:
        if generation == _desktop_sync_generation:
            _desktop_sync_cache = (time.monotonic(), result)
    return result


@app.get("/api/user/me")''', 1)
    source = source.replace('    async def broadcast(self, slug: str, message: dict):\n', '    async def broadcast(self, slug: str, message: dict):\n        _invalidate_desktop_sync()\n', 1)
    # Each version gets an increasing server revision. Existing clients without
    # a revision remain compatible; revision-aware clients get explicit conflicts.
    source = source.replace('        prev = versions.get(version_key)\n', '''        prev = versions.get(version_key)
        current_revision = int(((prev or {}).get("_sync_meta") or {}).get("revision") or 0)
        supplied_revision = (data.get("_sync_meta") or {}).get("revision")
        if supplied_revision is not None and int(supplied_revision) != current_revision and not force:
            if version_content_hash(prev) != version_content_hash(data):
                raise HTTPException(409, "Version changed on another device")
''', 1)
    source = source.replace('        versions[version_key] = data\n', '''        data["_sync_meta"] = {
            "revision": current_revision + 1, "slug": slug, "key": version_key,
            "server_modified": time.time(),
        }
        versions[version_key] = data
''', 1)
    source = source.replace('        inst = models.Institution(slug=slug, name=slug, meta_data={"versions": {version_key: data}})', '''        data["_sync_meta"] = {"revision": 1, "slug": slug, "key": version_key,
                              "server_modified": time.time()}
        inst = models.Institution(slug=slug, name=slug, meta_data={"versions": {version_key: data}})''', 1)
    source = source.replace('return {"msg": "Version pushed successfully", "stored": True}', 'return {"msg": "Version pushed successfully", "stored": True, "sync_meta": data.get("_sync_meta", {})}', 1)
    # An acknowledged, revision-aware empty save is an intentional edit. Legacy
    # empty uploads still retain their existing destructive-write protection.
    source = source.replace('if not force and _is_destructive_overwrite(prev, data):', 'if not force and supplied_revision is None and _is_destructive_overwrite(prev, data):', 1)
    compile(source, "main.py", "exec")
    return source


if __name__ == "__main__":
    target = Path(sys.argv[1])
    target.write_text(patch(target.read_text()))
