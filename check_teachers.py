import version_store
slug = 'bogazici_egitim_kurumlari'
active = version_store.get_active_version(slug)
data = version_store.load_version(slug, active)

print("=== ALL TEACHERS ===")
teachers = data.get("ogretmenler", [])
for t in sorted(teachers, key=lambda x: x.get("ad", "")):
    print(f"  {t.get('ad', '?')}")

print(f"\nTotal teachers: {len(teachers)}")

print("\n=== ALL ASSIGNMENTS (teacher field) ===")
atamalar = data.get("atamalar", [])
teacher_set = set()
for a in atamalar:
    t = a.get("teacher", a.get("ogretmen", "")).strip()
    if t:
        teacher_set.add(t)

for t in sorted(teacher_set):
    count = sum(1 for a in atamalar if (a.get("teacher","") or a.get("ogretmen","")).strip() == t)
    print(f"  {t} ({count} assignments)")

print(f"\nTotal assigned teachers: {len(teacher_set)}")

# Find teachers WITHOUT assignments
teacher_names = set(t.get("ad", "").strip() for t in teachers if t.get("ad", "").strip())
unassigned = []
for tn in sorted(teacher_names):
    found = False
    for at in teacher_set:
        if tn.lower() == at.lower() or tn in at or at in tn:
            found = True
            break
    if not found:
        unassigned.append(tn)

print(f"\n=== UNASSIGNED TEACHERS ({len(unassigned)}) ===")
for t in unassigned:
    print(f"  {t}")
