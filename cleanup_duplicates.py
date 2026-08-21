"""
cleanup_duplicates.py — one-off repair for the duplicates that already exist.

The code fixes stop NEW duplicates from forming; this removes the ones already
sitting in ~/.chenki_akademi and on the VDS, and repairs meta.json files that the
old sync bloated with version payloads.

    python cleanup_duplicates.py                # report only, changes nothing
    python cleanup_duplicates.py --apply        # local repair, with a backup first
    python cleanup_duplicates.py --apply --cloud  # also purge them from the VDS

Duplicate means byte-identical schedule content (ignoring volatile metadata), the
same rule the app and the server use. The copy with the LOWEST version number is
kept, so the numbering you already recognise survives; a folder assignment that only
a discarded copy carried is transferred to the survivor rather than lost.
"""
import argparse
import json
import os
import shutil
import sys
from collections import defaultdict
from datetime import datetime

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import version_store


def backup_everything() -> str:
    base = version_store._base_dir()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(os.path.dirname(base), f"institutions_backup_{stamp}")
    shutil.copytree(base, dest)
    return dest


def scan_institution(slug: str):
    """Groups an institution's versions by content hash.

    Returns (groups, unreadable) where groups maps hash -> [version dicts] sorted so
    the keeper is first.
    """
    groups = defaultdict(list)
    unreadable = []
    for v in version_store.list_versions(slug):
        path = v["filepath"]
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            unreadable.append((v["filename"], str(exc)))
            continue
        groups[version_store.compute_data_hash(data)].append(v)

    for digest in groups:
        # Lowest version number first; that one is kept.
        groups[digest].sort(key=lambda x: (x.get("number", 0), x.get("filename", "")))
    return groups, unreadable


def meta_is_bloated(slug: str) -> int:
    """Bytes of version payload wrongly stored inside meta.json, or 0."""
    meta_path = os.path.join(version_store._base_dir(), slug, "meta.json")
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return 0
    if "versions" not in raw:
        return 0
    try:
        return len(json.dumps(raw["versions"]))
    except Exception:
        return 1


def repair_meta(slug: str) -> bool:
    meta_path = os.path.join(version_store._base_dir(), slug, "meta.json")
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return False
    if "versions" not in raw:
        return False
    raw.pop("versions", None)
    ok = version_store._atomic_write_json(meta_path, raw)
    version_store._invalidate_meta_cache(slug)
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove duplicate schedule versions.")
    parser.add_argument("--apply", action="store_true",
                        help="Actually delete. Without this, nothing is changed.")
    parser.add_argument("--cloud", action="store_true",
                        help="Also delete the duplicates from the VDS (requires --apply).")
    parser.add_argument("--slug", help="Limit to one institution.")
    parser.add_argument("--no-backup", action="store_true",
                        help="Skip the safety copy. Not recommended.")
    args = parser.parse_args()

    base = version_store._base_dir()
    if not os.path.isdir(base):
        print(f"Nothing to do: {base} does not exist.")
        return 0

    institutions = version_store.list_institutions()
    if args.slug:
        institutions = [i for i in institutions if i["slug"] == args.slug]
    if not institutions:
        print("No institutions found.")
        return 0

    plan = []
    total_dupes = 0
    total_bytes = 0
    bloated = []

    for inst in institutions:
        slug = inst["slug"]
        groups, unreadable = scan_institution(slug)
        dupes = []
        for digest, members in groups.items():
            if len(members) < 2:
                continue
            keeper, extras = members[0], members[1:]
            dupes.append((keeper, extras))
            total_dupes += len(extras)
            total_bytes += sum(int(e.get("size_kb", 0) * 1024) for e in extras)

        bloat = meta_is_bloated(slug)
        if bloat:
            bloated.append((slug, bloat))

        if dupes or unreadable or bloat:
            plan.append((inst, dupes, unreadable, bloat))

    print(f"\nScanned {len(institutions)} institution(s) in {base}\n")

    if not plan:
        print("No duplicates, no bloated meta files. Nothing to clean.")
        return 0

    for inst, dupes, unreadable, bloat in plan:
        print(f"── {inst['name']}  ({inst['slug']})")
        if bloat:
            print(f"     meta.json carries {bloat / 1024:.0f} KB of version payload "
                  f"that does not belong there")
        for keeper, extras in dupes:
            print(f"     keep    {keeper.get('label', keeper['filename']):<16}  {keeper['filename']}")
            for e in extras:
                folder = f"  [klasör: {e['folder_name']}]" if e.get("folder_name") else ""
                print(f"     remove  {e.get('label', e['filename']):<16}  {e['filename']}"
                      f"  ({e['size_kb']} KB){folder}")
        for filename, exc in unreadable:
            print(f"     UNREADABLE (left alone): {filename} — {exc}")
        print()

    print(f"Total: {total_dupes} duplicate version(s), about {total_bytes / 1048576:.1f} MB")
    if bloated:
        print(f"       {len(bloated)} meta.json file(s) to repair")

    if not args.apply:
        print("\nThis was a report only. Re-run with --apply to make these changes.")
        return 0

    if not args.no_backup:
        print("\nBacking up first...")
        try:
            dest = backup_everything()
            print(f"  backup: {dest}")
        except Exception as exc:
            print(f"  backup FAILED: {exc}")
            print("  Refusing to delete anything without a backup. Use --no-backup to override.")
            return 1

    removed = 0
    cloud_removed = 0
    for inst, dupes, _unreadable, bloat in plan:
        slug = inst["slug"]
        for keeper, extras in dupes:
            for extra in extras:
                # Don't lose a folder assignment that only the discarded copy had.
                if extra.get("folder_id") and not keeper.get("folder_id"):
                    version_store.assign_version_folder(slug, keeper["filename"], extra["folder_id"])
                    keeper["folder_id"] = extra["folder_id"]

                if args.cloud:
                    try:
                        from api_client import api_client
                        if api_client.delete_version_from_rtdb(slug, extra["filename"]):
                            cloud_removed += 1
                    except Exception as exc:
                        print(f"  cloud delete failed for {extra['filename']}: {exc}")

                try:
                    path = os.path.join(version_store._versions_dir(slug), extra["filename"])
                    if os.path.exists(path):
                        os.remove(path)
                    version_store.invalidate_version_summary(slug, extra["filename"])
                    removed += 1
                except OSError as exc:
                    print(f"  could not remove {extra['filename']}: {exc}")

        if bloat:
            repair_meta(slug)

        # The active version may have been one of the copies just removed.
        active = version_store.get_active_version(slug)
        present = {v["filename"] for v in version_store.list_versions(slug)}
        if active not in present:
            remaining = version_store.list_versions(slug)
            version_store.set_active_version(slug, remaining[0]["filename"] if remaining else None)

    version_store.invalidate_cross_busy_cache()

    print(f"\nRemoved {removed} local duplicate(s).")
    if args.cloud:
        print(f"Removed {cloud_removed} from the VDS.")
        print("Ask the server to collapse anything it still holds:")
        print("  POST /api/maintenance/dedupe   (admin token required)")
    else:
        print("The VDS was not touched. Re-run with --cloud to purge there too,")
        print("or the next sync may pull some of these back.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
