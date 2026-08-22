"""
repair_assignments.py — kayıtlı çizelgeyi Ders ve Öğretmen Atama Paneli ile eşitler.

Eski oto planlayıcı, atanan öğretmen meşgulse dersi BAŞKA bir öğretmene yazıyordu ve
aday listesi "o dersi verenler + okuldaki herkes" olduğu için hiç ataması olmayan
öğretmenler bile çizelgeye giriyordu. O hata düzeltildi, ama daha önce KAYDEDİLMİŞ
versiyonlarda bozuk veri duruyor. Bu araç onları onarır.

    python repair_assignments.py                          # aktif versiyonu tara (değiştirmez)
    python repair_assignments.py --all                    # tüm versiyonları tara
    python repair_assignments.py --apply                  # aktif versiyonu onar
    python repair_assignments.py --all --apply            # hepsini onar
    python repair_assignments.py --version v118_...roz --apply

Kurallar:
  * (sınıf, ders) için atanmış öğretmen varsa, yerleşimdeki öğretmen ona düzeltilir.
  * (sınıf, ders) için hiç atama yoksa, o yerleşim çizelgeye ait değildir; kaldırılır
    ve "yerleştirilmeyenler" listesine düşer — silinmez, elle yerleştirilebilir.

--apply verilmeden hiçbir şey değişmez. Değiştirmeden önce .bak kopyası alınır.
"""
import argparse
import json
import os
import shutil
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import version_store


def norm(value) -> str:
    return " ".join(str(value or "").split()).strip().upper()


def build_assignment_map(data: dict) -> dict:
    """(SINIF, DERS) -> [öğretmen adı, ...] — panelde görünen gerçek atamalar."""
    mapping = defaultdict(list)
    for a in data.get("atamalar", []) or []:
        if not isinstance(a, dict):
            continue
        cls = norm(a.get("class") or a.get("sinif") or a.get("class_name"))
        sub = norm(a.get("subject") or a.get("ders"))
        raw = str(a.get("teacher") or a.get("ogretmen") or a.get("teacher_name") or "")
        if not (cls and sub):
            continue
        for part in raw.split(","):
            name = part.strip()
            if name and name not in mapping[(cls, sub)]:
                mapping[(cls, sub)].append(name)
    return mapping


def analyse(data: dict):
    """(düzeltilecekler, kaldırılacaklar) listelerini döndürür."""
    mapping = build_assignment_map(data)
    to_fix, to_drop = [], []

    for placement in data.get("grid_placements", []) or []:
        if not isinstance(placement, dict):
            continue
        cls = norm(placement.get("class_name") or placement.get("class"))
        sub = norm(placement.get("subject_name") or placement.get("subject"))
        tea = norm(placement.get("teacher_name") or placement.get("teacher"))

        assigned = mapping.get((cls, sub))
        if not assigned:
            # Bu sınıfa bu ders hiç atanmamış — çizelgede işi yok.
            to_drop.append(placement)
            continue
        if tea not in {norm(t) for t in assigned}:
            to_fix.append((placement, assigned[0]))

    return to_fix, to_drop


def repair(data: dict) -> dict:
    """Veriyi yerinde onarır ve özet döndürür."""
    to_fix, to_drop = analyse(data)

    for placement, correct_teacher in to_fix:
        placement["teacher_name"] = correct_teacher
        placement["teacher"] = correct_teacher

    if to_drop:
        drop_ids = {id(p) for p in to_drop}
        data["grid_placements"] = [
            p for p in data.get("grid_placements", []) if id(p) not in drop_ids
        ]
        # Silmek yerine yerleştirilmeyenler havuzuna al: kullanıcı isterse elle koyar.
        import uuid

        loose = data.setdefault("loose_unplaced_cards", [])
        seen = set()
        for p in to_drop:
            cls = (p.get("class_name") or p.get("class") or "").strip()
            sub = (p.get("subject_name") or p.get("subject") or "").strip()
            key = (cls.upper(), sub.upper())
            if key in seen:
                continue  # aynı dersin her saati için ayrı kart üretme
            seen.add(key)
            loose.append({
                "id": f"loose_{uuid.uuid4().hex[:8]}",
                "subject_name": sub, "subject": sub,
                "teacher_name": "", "teacher": "",
                "class_name": cls, "class": cls,
                "duration": int(p.get("duration", 1) or 1),
                "color": p.get("color", ""),
                "is_filler": False,
                "needs_assignment": True,
            })

    if "auto_schedule_results" in data:
        data["auto_schedule_results"] = list(data.get("grid_placements", []))

    return {"fixed": len(to_fix), "dropped": len(to_drop)}


def report(slug: str, filename: str, data: dict, verbose: bool):
    to_fix, to_drop = analyse(data)
    mapping = build_assignment_map(data)

    ghosts = defaultdict(int)
    assigned_teachers = {norm(t) for names in mapping.values() for t in names}
    for p in data.get("grid_placements", []) or []:
        tea = norm(p.get("teacher_name") or p.get("teacher"))
        if tea and tea not in assigned_teachers:
            ghosts[tea] += 1

    total = len(data.get("grid_placements", []) or [])
    status = "TEMİZ" if not (to_fix or to_drop) else "BOZUK"
    print(f"  {filename:<44} {total:>4} yerleşim  "
          f"{len(to_fix):>3} yanlış  {len(to_drop):>3} atamasız  [{status}]")

    if verbose and ghosts:
        print("       hiç ataması olmayan öğretmenler çizelgede:")
        for name, count in sorted(ghosts.items(), key=lambda kv: -kv[1]):
            print(f"         {name:<24} {count} saat")

    if verbose and to_fix:
        print("       düzeltilecek (ilk 10):")
        for placement, correct in to_fix[:10]:
            cls = placement.get("class_name") or placement.get("class")
            sub = placement.get("subject_name") or placement.get("subject")
            tea = placement.get("teacher_name") or placement.get("teacher")
            print(f"         {str(cls)[:12]:<12} {str(sub)[:16]:<16} "
                  f"'{tea}' -> '{correct}'")

    return to_fix, to_drop


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Çizelgedeki öğretmenleri atama paneliyle eşitler.")
    parser.add_argument("--slug", default="bogazici_egitim_kurumlari", help="Kurum kodu")
    parser.add_argument("--version", help="Belirli bir versiyon dosyası")
    parser.add_argument("--all", action="store_true", help="Tüm versiyonları işle")
    parser.add_argument("--apply", action="store_true", help="Değişiklikleri kaydet")
    parser.add_argument("--no-push", action="store_true",
                        help="Onarımı buluta gönderme (ÖNERİLMEZ — sonraki senkron geri alır)")
    parser.add_argument("--quiet", action="store_true", help="Detay gösterme")
    args = parser.parse_args()

    slug = args.slug
    if not os.path.isdir(os.path.join(version_store._base_dir(), slug)):
        print(f"'{slug}' kurumu bulunamadı.")
        return 1

    if args.version:
        targets = [args.version]
    elif args.all:
        targets = [v["filename"] for v in version_store.list_versions(slug)]
    else:
        active = version_store.get_active_version(slug)
        if not active:
            print("Aktif versiyon yok.")
            return 1
        targets = [active]

    print(f"\n'{slug}' — {len(targets)} versiyon inceleniyor\n")

    total_fixed = total_dropped = touched = 0
    pushed = []
    for filename in targets:
        data = version_store.load_version(slug, filename)
        if not data:
            print(f"  {filename:<44} okunamadı, atlandı")
            continue

        to_fix, to_drop = report(slug, filename, data, verbose=not args.quiet and len(targets) <= 3)
        if not (to_fix or to_drop):
            continue

        if not args.apply:
            total_fixed += len(to_fix)
            total_dropped += len(to_drop)
            continue

        path = os.path.join(version_store._versions_dir(slug), filename)
        backup = path + ".bak"
        if not os.path.exists(backup):
            shutil.copy2(path, backup)

        result = repair(data)
        meta = data.setdefault("_version_meta", {})
        meta["note"] = (meta.get("note", "") + " | atamalarla eşitlendi").strip(" |")

        version_store._atomic_write_json(path, data)
        version_store.invalidate_version_summary(slug, filename)
        total_fixed += result["fixed"]
        total_dropped += result["dropped"]
        touched += 1
        print(f"       -> onarıldı ({result['fixed']} düzeltildi, "
              f"{result['dropped']} kaldırıldı), yedek: {os.path.basename(backup)}")

        # Onarımı buluta göndermek ŞART. Sunucu doğruluk kaynağı olduğu için, yalnızca
        # yerelde düzeltmek işe yaramaz: bir sonraki senkron eski bozuk sürümü geri
        # indirir ve onarım sessizce geri alınır. (Tam olarak bu yaşandı.)
        if not args.no_push:
            try:
                from cloud_sync import push_version_to_rtdb
                if push_version_to_rtdb(slug, filename, data):
                    pushed.append(filename)
                    print("          buluta gönderildi")
                else:
                    print("          UYARI: buluta gönderilemedi — "
                          "sonraki senkron bu onarımı geri alabilir")
            except Exception as exc:
                print(f"          UYARI: bulut gönderimi hatası: {exc}")

    print()
    if args.apply:
        print(f"{touched} versiyon onarıldı: {total_fixed} öğretmen düzeltildi, "
              f"{total_dropped} atamasız yerleşim kaldırıldı.")
        if args.no_push:
            print("UYARI: buluta gönderilmedi. Sonraki senkron onarımı GERİ ALIR.")
        else:
            print(f"{len(pushed)}/{touched} versiyon buluta gönderildi.")
    else:
        print(f"Ön izleme: {total_fixed} öğretmen düzeltilecek, "
              f"{total_dropped} atamasız yerleşim kaldırılacak.")
        print("Uygulamak için --apply ekleyin.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
