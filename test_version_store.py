"""
test_version_store.py — regression tests for local version storage.

    python test_version_store.py

Runs against a throwaway directory, so it never touches ~/.chenki_akademi. Cloud
pushes are stubbed out: this covers the local half of the duplicate problem only.
"""
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SANDBOX = os.path.join(tempfile.gettempdir(), "chenki_vs_test")
if os.path.exists(SANDBOX):
    shutil.rmtree(SANDBOX, ignore_errors=True)
os.makedirs(SANDBOX, exist_ok=True)

import version_store  # noqa: E402

# Redirect storage into the sandbox and neutralise every background cloud push, so
# the tests exercise disk logic only and never touch the VDS.
version_store._base_dir = lambda: os.path.join(SANDBOX, "institutions")


class _NullCloud:
    def __getattr__(self, _name):
        return lambda *a, **k: True


sys.modules["cloud_sync"] = _NullCloud()
sys.modules["database"] = _NullCloud()

PASSED, FAILED = [], []


def check(name, condition, detail=""):
    if condition:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def schedule(*placements):
    return {
        "dersler": [{"ad": "Matematik"}],
        "siniflar": [{"ad": "9A"}],
        "ogretmenler": [{"ad": "Seher Şanlı"}],
        "atamalar": [{"subject": "Matematik", "teacher": "Seher Şanlı", "class": "9A", "duration": 4}],
        "grid_placements": list(placements),
        "settings": {"periods": 8, "days": ["Pzt", "Sal", "Çar", "Per", "Cum"]},
    }


def placement(day, period, subject="Matematik", teacher="Seher Şanlı", cls="9A"):
    return {"day": day, "period": period, "subject_name": subject,
            "teacher_name": teacher, "class_name": cls, "duration": 1}


def run():
    print("\n[institution setup]")
    inst = version_store.create_institution("Test Okulu")
    slug = inst["slug"]
    check("institution created", bool(slug), str(inst))
    check("starts with exactly one version",
          len(version_store.list_versions(slug)) == 1,
          str(len(version_store.list_versions(slug))))

    print("\n[duplicate suppression]")
    data = schedule(placement(0, 0))
    first = version_store.save_version(slug, data, note="ilk")
    time.sleep(1.05)  # version filenames carry a whole-second timestamp
    second = version_store.save_version(slug, dict(data), note="ayni")
    check("saving identical content reuses the version", first == second,
          f"{first} vs {second}")

    versions = version_store.list_versions(slug)
    hashes = [version_store.compute_data_hash(version_store.load_version(slug, v["filename"]))
              for v in versions]
    check("no two stored versions share content", len(hashes) == len(set(hashes)),
          f"{len(hashes)} versions, {len(set(hashes))} distinct")

    changed = schedule(placement(0, 0), placement(1, 1, subject="Fizik"))
    third = version_store.save_version(slug, changed, note="degisti")
    check("changed content does create a new version", third != first, f"{third} vs {first}")

    print("\n[explicit checkpoint]")
    forced = version_store.save_version(slug, dict(changed), note="kontrol",
                                        allow_duplicate=True)
    check("allow_duplicate still makes a distinct file", forced != third, f"{forced} vs {third}")

    print("\n[folders]")
    folder, created = version_store.create_folder(slug, "Ağustos Planı")
    check("folder created", created and folder.get("id"), str(folder))
    same, created_again = version_store.create_folder(slug, "ağustos planı")
    check("same name (case-insensitive) is not duplicated",
          not created_again and same.get("id") == folder["id"], str(same))

    ok = version_store.assign_version_folder(slug, third, folder["id"])
    check("version assigned to folder", ok)
    listed = {v["filename"]: v for v in version_store.list_versions(slug)}
    check("folder id is reported back", listed[third]["folder_id"] == folder["id"],
          str(listed[third].get("folder_id")))
    check("folder name is resolved", listed[third]["folder_name"] == "Ağustos Planı",
          str(listed[third].get("folder_name")))

    # A folder move must bump last_modified, or the cloud pull's reconciliation
    # decides nothing changed and silently reverts it.
    moved = version_store.load_version(slug, third)
    check("folder move stamps last_modified",
          bool(moved.get("_version_meta", {}).get("last_modified")),
          str(moved.get("_version_meta")))

    version_store.assign_version_folder(slug, third, None)
    listed = {v["filename"]: v for v in version_store.list_versions(slug)}
    check("version can be taken back out of a folder",
          listed[third]["folder_id"] is None, str(listed[third].get("folder_id")))

    print("\n[summary cache correctness]")
    # The cache is keyed on (mtime, size); a rewrite must be picked up, not served
    # stale, or a dragged version would appear to snap back to its old folder.
    version_store.assign_version_folder(slug, third, folder["id"])
    refetched = {v["filename"]: v for v in version_store.list_versions(slug)}
    check("cache reflects a rewrite immediately",
          refetched[third]["folder_id"] == folder["id"],
          str(refetched[third].get("folder_id")))

    print("\n[meta never accumulates version payloads]")
    meta_path = os.path.join(version_store._base_dir(), slug, "meta.json")
    import json
    with open(meta_path, "r", encoding="utf-8") as f:
        raw_meta = json.load(f)
    check("meta.json has no 'versions' key", "versions" not in raw_meta, str(list(raw_meta)))

    # Simulate the damage the old sync caused and confirm reading repairs it.
    raw_meta["versions"] = {"v001_x_roz": {"huge": "x" * 5000}}
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(raw_meta, f)
    version_store._invalidate_meta_cache(slug)
    cleaned = version_store.get_institution_meta(slug)
    check("reading strips an injected version blob", "versions" not in cleaned, str(list(cleaned)))
    with open(meta_path, "r", encoding="utf-8") as f:
        check("and the repair is written back to disk", "versions" not in json.load(f))

    print("\n[meta cache isolation]")
    a = version_store.get_institution_meta(slug)
    a["name"] = "MUTATED"
    a.setdefault("folders", []).append({"id": "junk", "name": "junk"})
    b = version_store.get_institution_meta(slug)
    check("callers cannot mutate the cached meta", b.get("name") != "MUTATED", str(b.get("name")))
    check("nested structures are copied too",
          not any(f.get("id") == "junk" for f in b.get("folders", [])), str(b.get("folders")))

    print("\n[delete]")
    before = len(version_store.list_versions(slug))
    version_store.delete_version(slug, forced)
    after = len(version_store.list_versions(slug))
    check("deleting removes exactly one version", before - after == 1, f"{before} -> {after}")
    check("active version is still valid",
          version_store.get_active_version(slug) in
          {v["filename"] for v in version_store.list_versions(slug)},
          version_store.get_active_version(slug))

    print("\n[folder delete cascades]")
    in_folder = [v["filename"] for v in version_store.list_versions(slug)
                 if v.get("folder_id") == folder["id"]]
    removed = version_store.delete_folder(slug, folder["id"])
    check("delete_folder reports what it removed", removed == len(in_folder),
          f"{removed} vs {len(in_folder)}")
    check("folder is gone",
          not any(f["id"] == folder["id"] for f in version_store.list_folders(slug)))
    remaining = {v["filename"] for v in version_store.list_versions(slug)}
    check("its versions are gone too", not (set(in_folder) & remaining), str(in_folder))

    print("\n[in-place update / write-skip cache]")
    base = schedule(placement(0, 0))
    target = version_store.save_version(slug, base, note="inplace", allow_duplicate=True)

    edited = schedule(placement(0, 0), placement(3, 4, subject="Tarih"))
    check("an edit is written", version_store.update_version_in_place(slug, target, dict(edited)))
    reread = version_store.load_version(slug, target)
    check("the edit is on disk", len(reread.get("grid_placements", [])) == 2,
          str(len(reread.get("grid_placements", []))))

    # Unchanged data must skip the write, which is what stops every idle save from
    # rewriting (and re-uploading) the whole schedule.
    stat_before = os.stat(os.path.join(version_store._versions_dir(slug), target)).st_mtime_ns
    time.sleep(0.02)
    version_store.update_version_in_place(slug, target, dict(edited))
    stat_after = os.stat(os.path.join(version_store._versions_dir(slug), target)).st_mtime_ns
    check("unchanged data does not rewrite the file", stat_before == stat_after)

    # The dangerous case: something else (a cloud pull) rewrites the file. If the
    # remembered hash survived that, the next local save would decide it already
    # matched and silently drop the user's edit.
    path = os.path.join(version_store._versions_dir(slug), target)
    outside = schedule(placement(5, 5, subject="Uzaktan"))
    outside["_version_meta"] = dict(reread.get("_version_meta", {}))
    version_store._atomic_write_json(path, outside)
    version_store.invalidate_version_summary(slug, target)

    version_store.update_version_in_place(slug, target, dict(edited))
    final = version_store.load_version(slug, target)
    subjects = {p.get("subject_name") for p in final.get("grid_placements", [])}
    check("a local save after an outside rewrite is not skipped",
          "Tarih" in subjects, str(subjects))

    print("\n[atomic write]")
    target = os.path.join(SANDBOX, "atomic.json")
    version_store._atomic_write_json(target, {"a": 1})
    check("atomic write produces a readable file", os.path.exists(target))
    leftovers = [f for f in os.listdir(SANDBOX) if f.endswith(".tmp")]
    check("no temp file is left behind", not leftovers, str(leftovers))

    print("\n[cross-institution conflict map]")
    other = version_store.create_institution("Diger Okul")
    version_store.save_version(
        other["slug"], schedule(placement(2, 3, subject="Kimya", cls="10B")), note="c"
    )
    version_store.invalidate_cross_busy_cache()
    busy = version_store.get_cross_institution_teacher_busy_slots(exclude_slug=slug)
    key = (version_store.normalize_teacher_name("Seher Şanlı"), 2, 3)
    check("conflicting slot is found", key in busy, str(list(busy)[:3]))
    if key in busy:
        entry = busy[key]
        # main_window's conflict dialog reads "subject"/"class"; the duplicate
        # definition that used to shadow this function emitted only those, while the
        # cached one emitted only *_name. Both must now be present.
        check("entry exposes 'subject' for the dialog", entry.get("subject") == "Kimya", str(entry))
        check("entry exposes 'class' for the dialog", entry.get("class") == "10B", str(entry))
        check("entry also exposes subject_name", entry.get("subject_name") == "Kimya", str(entry))
        check("entry names the institution",
              entry.get("institution_name") == "Diger Okul", str(entry))

    check("own institution is excluded",
          not any(v.get("institution_slug") == slug for v in busy.values()))

    print("\n[cross-institution cache is actually used]")
    calls = {"n": 0}
    real_load = version_store.load_version

    def counting_load(*a, **k):
        calls["n"] += 1
        return real_load(*a, **k)

    version_store.load_version = counting_load
    try:
        version_store.invalidate_cross_busy_cache()
        version_store.get_cross_institution_teacher_busy_slots(exclude_slug=slug)
        first_calls = calls["n"]
        version_store.get_cross_institution_teacher_busy_slots(exclude_slug=slug)
        check("second call reads nothing from disk", calls["n"] == first_calls,
              f"{first_calls} then {calls['n']}")
        check("first call did read from disk", first_calls > 0, str(first_calls))
    finally:
        version_store.load_version = real_load


if __name__ == "__main__":
    try:
        run()
    finally:
        print("\n" + "=" * 60)
        print(f"passed: {len(PASSED)}   failed: {len(FAILED)}")
        for name, detail in FAILED:
            print(f"  - {name}: {detail}")
        print("=" * 60)
        shutil.rmtree(SANDBOX, ignore_errors=True)
    sys.exit(1 if FAILED else 0)
