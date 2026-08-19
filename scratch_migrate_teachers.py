import os, sys, glob, json

sys.path.insert(0, 'c:/Users/gokay/Desktop/aSc/ChenKi_v2')
import version_store
from version_store import _matches_teacher, rename_teacher_in_data_store, sanitize_atamalar

TEACHER_CANONICAL_MAP = {
    'seyma aker': 'Şeyma Nur Aker',
    'şeyma aker': 'Şeyma Nur Aker',
    'şeyma nur aker': 'Şeyma Nur Aker',
    'seyma nur aker': 'Şeyma Nur Aker',
    'fatih özbiçakçi': 'Fatih Özbıçakçı',
    'fatih özbıçakcı': 'Fatih Özbıçakçı',
    'fatih özbıçakçı': 'Fatih Özbıçakçı',
    'oya erocağı': 'Oya S. Erocağı',
    'oya s.erocağ': 'Oya S. Erocağı',
    'oya s.erocağı': 'Oya S. Erocağı',
    'büşra öksüz': 'Büşra K. Öksüz',
    'büşra k.öksüz': 'Büşra K. Öksüz',
    'büşra k. öksüz': 'Büşra K. Öksüz',
    'yasemin': 'Yasemin Özkaya',
    'yasemin özkaya': 'Yasemin Özkaya',
    'h.barış karataş': 'H. Barış Karataş',
    'h.baris karatas': 'H. Barış Karataş',
    'h. barış karataş': 'H. Barış Karataş',
}

def migrate_dict(data):
    if not isinstance(data, dict): return data
    ogretmenler = data.get('ogretmenler', [])
    for t in ogretmenler:
        raw_ad = t.get('ad', '').strip()
        clean_k = version_store.normalize_teacher_name(raw_ad)
        if clean_k in TEACHER_CANONICAL_MAP:
            t['ad'] = TEACHER_CANONICAL_MAP[clean_k]
            
    # Deduplicate ogretmenler by normalized name
    seen_og = {}
    for t in ogretmenler:
        ad = t.get('ad', '').strip()
        if not ad: continue
        k = version_store.normalize_teacher_name(ad)
        if k not in seen_og:
            seen_og[k] = t
    data['ogretmenler'] = list(seen_og.values())
    
    # Update atamalar, grid_placements, etc.
    active_teachers = [t['ad'] for t in data['ogretmenler']]
    for a in data.get('atamalar', []):
        t_name = a.get('teacher', '').strip()
        if not t_name: continue
        matched = False
        for at in active_teachers:
            if _matches_teacher(t_name, at):
                a['teacher'] = at
                matched = True
                break
        if not matched:
            clean_k = version_store.normalize_teacher_name(t_name)
            if clean_k in TEACHER_CANONICAL_MAP:
                a['teacher'] = TEACHER_CANONICAL_MAP[clean_k]
                
    for p in data.get('grid_placements', []):
        t_name = (p.get('teacher_name') or p.get('teacher') or '').strip()
        if not t_name: continue
        for at in active_teachers:
            if _matches_teacher(t_name, at):
                p['teacher_name'] = at
                p['teacher'] = at
                break
                
    data['atamalar'] = sanitize_atamalar(data.get('atamalar', []))
    return data

# Migrate bgz_database.json
if os.path.exists('c:/Users/gokay/Desktop/aSc/ChenKi_v2/bgz_database.json'):
    with open('c:/Users/gokay/Desktop/aSc/ChenKi_v2/bgz_database.json', 'r', encoding='utf-8', errors='replace') as fp:
        bgz = json.load(fp)
    bgz = migrate_dict(bgz)
    with open('c:/Users/gokay/Desktop/aSc/ChenKi_v2/bgz_database.json', 'w', encoding='utf-8') as fp:
        json.dump(bgz, fp, ensure_ascii=False, indent=2)
    print('Migrated bgz_database.json')

# Migrate all versions
for inst in version_store.list_institutions():
    for v in version_store.list_versions(inst['slug'], source_filter='all'):
        data = version_store.load_version(inst['slug'], v['filename'])
        if data:
            data = migrate_dict(data)
            with open(v['filepath'], 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Migrated {inst['slug']} / {v['filename']}")

print('All migrations completed successfully!')
