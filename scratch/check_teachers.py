import json, os, glob

# Check all .json files in version_store for teacher mismatches
base = os.path.join(os.path.expanduser("~"), ".chenki_akademi", "versions")
json_files = []
if os.path.exists(base):
    for root, dirs, files in os.walk(base):
        for f in files:
            if f.endswith(".json"):
                json_files.append(os.path.join(root, f))

# Also check bgz_database.json
bgz = "bgz_database.json"
if os.path.exists(bgz):
    json_files.insert(0, bgz)

for fp in json_files:
    try:
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        continue
    
    teachers = data.get("ogretmenler", [])
    atamalar = data.get("atamalar", [])
    if not teachers or not atamalar:
        continue
    
    teacher_names = set(t.get("ad", "") for t in teachers if t.get("ad"))
    at_teachers = set(a.get("teacher", "") for a in atamalar if a.get("teacher"))
    
    missing = at_teachers - teacher_names
    if missing:
        print(f"\n=== FILE: {os.path.basename(fp)} ===")
        print(f"  Teachers in list: {len(teacher_names)}")
        print(f"  Teachers in assignments: {len(at_teachers)}")
        print(f"  MISMATCHES ({len(missing)}):")
        for m in sorted(missing):
            # Find closest match
            best = None
            for tn in teacher_names:
                if tn.split()[0] == m.split()[0] if m.split() and tn.split() else False:
                    best = tn
                    break
            if best:
                print(f"    '{m}' -> probable match: '{best}'")
            else:
                print(f"    '{m}' -> NO MATCH FOUND")
    else:
        print(f"\n=== FILE: {os.path.basename(fp)} === OK (no mismatches)")
