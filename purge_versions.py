"""
purge_versions.py — geri gelmeye devam eden versiyonları kalıcı olarak sil.

Acil kurtarma aracı. Bir versiyon uygulamadan silinip silinip geri geliyorsa bunu
çalıştırın: dosyayı siler, kalıcı bir "tombstone" (silinme kaydı) yazar ve silmeyi
sunucu onaylayana kadar kuyrukta tutar. Tombstone kurum meta'sında saklandığı ve
buluta gönderildiği için diğer cihazlar (Mac dahil) da o dosyayı bir daha yüklemez.

    python purge_versions.py                          # kurumları ve versiyonları listele
    python purge_versions.py --slug <kurum>            # o kurumun versiyonlarını listele
    python purge_versions.py --slug <kurum> --file v082_....roz --apply
    python purge_versions.py --slug <kurum> --numbers 82,83,84 --apply
    python purge_versions.py --flush                   # bekleyen silmeleri sunucuya gönder
    python purge_versions.py --slug <kurum> --list-tombstones
    python purge_versions.py --slug <kurum> --restore v082_....roz   # silmeyi geri al

--apply verilmeden hiçbir şey değişmez.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import version_store


def show_institutions():
    institutions = version_store.list_institutions()
    if not institutions:
        print("Hiç kurum bulunamadı.")
        return
    print(f"\n{len(institutions)} kurum:\n")
    for inst in institutions:
        versions = version_store.list_versions(inst["slug"])
        tombs = version_store.list_tombstones(inst["slug"])
        print(f"  {inst['slug']:<40} {inst['name']}")
        print(f"      {len(versions)} versiyon, {len(tombs)} silinmiş kayıt")
    print("\nDetay için: python purge_versions.py --slug <kurum>")


def show_versions(slug):
    versions = version_store.list_versions(slug)
    if not versions:
        print(f"'{slug}' kurumunda listelenecek versiyon yok.")
        return
    active = version_store.get_active_version(slug)
    print(f"\n'{slug}' — {len(versions)} versiyon:\n")
    for v in versions:
        mark = " (AKTİF)" if v["filename"] == active else ""
        folder = f"  [{v['folder_name']}]" if v.get("folder_name") else "  [Klasörsüz]"
        print(f"  {v.get('label', ''):<16} {v['filename']:<42}"
              f"{v['date_str']} {v['time_str']}{folder}{mark}")

    # Diskte durup listelenmeyenler: tombstone'lu ama dosyası hâlâ duran kayıtlar.
    ver_dir = version_store._versions_dir(slug)
    on_disk = {f for f in os.listdir(ver_dir) if f.endswith(".roz")}
    listed = {v["filename"] for v in versions}
    ghosts = on_disk - listed
    if ghosts:
        print(f"\n  Silinmiş sayılan ama diski hâlâ işgal eden {len(ghosts)} dosya:")
        for g in sorted(ghosts):
            print(f"      {g}")
        print("  Bunları temizlemek için: --apply --enforce")


def show_tombstones(slug):
    tombs = sorted(version_store.list_tombstones(slug))
    if not tombs:
        print(f"'{slug}' kurumunda silinmiş versiyon kaydı yok.")
        return
    print(f"\n'{slug}' — {len(tombs)} silinmiş versiyon:\n")
    for t in tombs:
        print(f"  {t}")
    print("\nBirini geri getirmek için: --restore <dosya adı> --apply")


def resolve_targets(slug, args):
    """--file / --numbers / --all seçeneklerini dosya adlarına çevirir."""
    versions = version_store.list_versions(slug)
    by_name = {v["filename"]: v for v in versions}
    # Zaten silinmiş bir versiyonu "bulunamadı" diye bildirmek, kullanıcıya silme
    # işleminin başarısız olduğunu düşündürüyor. Oysa tam tersi: iş bitmiş demek.
    tombstoned = version_store.list_tombstones(slug)

    def _report_missing(label, matcher):
        already = [t for t in tombstoned if matcher(t)]
        if already:
            print(f"  {label} zaten silinmiş (silme kaydı mevcut): {', '.join(already)}")
        else:
            print(f"  UYARI: {label} bu kurumda bulunamadı, atlanıyor.")

    targets = []
    if args.all:
        active = version_store.get_active_version(slug)
        targets = [v["filename"] for v in versions if v["filename"] != active]
        print(f"  (--all: aktif versiyon '{active}' korunuyor)")

    for name in (args.file or []):
        if name in by_name:
            targets.append(name)
        else:
            _report_missing(f"'{name}'", lambda t, n=name: t == n)

    if args.numbers:
        wanted = set()
        for chunk in args.numbers.split(","):
            chunk = chunk.strip()
            if chunk.isdigit():
                wanted.add(int(chunk))
        for v in versions:
            if v["number"] in wanted:
                targets.append(v["filename"])
        found = {v["number"] for v in versions if v["number"] in wanted}
        for missing in sorted(wanted - found):
            _report_missing(
                f"Versiyon {missing}",
                lambda t, n=missing: t.startswith(f"v{n:03d}_"),
            )

    # Sırayı koruyarak tekrarları at
    seen = set()
    unique = []
    for t in targets:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Geri gelen versiyonları kalıcı olarak sil.")
    parser.add_argument("--slug", help="Kurum kodu")
    parser.add_argument("--file", action="append", help="Silinecek dosya adı (birden fazla verilebilir)")
    parser.add_argument("--numbers", help="Silinecek versiyon numaraları, virgülle: 82,83,84")
    parser.add_argument("--all", action="store_true", help="Aktif hariç TÜM versiyonları sil")
    parser.add_argument("--enforce", action="store_true",
                        help="Silinmiş sayılıp diskte kalan dosyaları temizle")
    parser.add_argument("--list-tombstones", action="store_true", help="Silinmiş kayıtları göster")
    parser.add_argument("--restore", help="Bir silme kaydını geri al")
    parser.add_argument("--flush", action="store_true", help="Bekleyen silmeleri sunucuya gönder")
    parser.add_argument("--apply", action="store_true", help="Değişiklikleri uygula")
    args = parser.parse_args()

    if args.flush:
        pending = version_store.pending_delete_count()
        if not pending:
            print("Bekleyen silme yok.")
            return 0
        print(f"{pending} bekleyen silme sunucuya gönderiliyor...")
        confirmed = version_store.flush_pending_deletes()
        left = version_store.pending_delete_count()
        print(f"  {confirmed} tanesi sunucu tarafından onaylandı, {left} tanesi beklemede.")
        if left:
            print("  Beklemede kalanlar internet bağlantısı geldiğinde otomatik denenecek.")
        return 0

    if not args.slug:
        show_institutions()
        return 0

    slug = args.slug
    if not os.path.isdir(os.path.join(version_store._base_dir(), slug)):
        print(f"'{slug}' adlı kurum bulunamadı.")
        show_institutions()
        return 1

    if args.list_tombstones:
        show_tombstones(slug)
        return 0

    if args.restore:
        if not args.apply:
            print(f"'{args.restore}' geri alınacak. Uygulamak için --apply ekleyin.")
            return 0
        if version_store.remove_tombstone(slug, args.restore):
            print(f"'{args.restore}' silme kaydı kaldırıldı.")
            print("Dosya bir sonraki bulut senkronunda geri inecektir.")
        else:
            print(f"'{args.restore}' için silme kaydı bulunamadı.")
        return 0

    targets = resolve_targets(slug, args)

    if args.enforce and not targets:
        if not args.apply:
            tombs = version_store.list_tombstones(slug)
            ver_dir = version_store._versions_dir(slug)
            stuck = [t for t in tombs if os.path.exists(os.path.join(ver_dir, t))]
            print(f"Diskte kalan {len(stuck)} silinmiş dosya temizlenecek. --apply ekleyin.")
            return 0
        removed = version_store.enforce_tombstones(slug)
        print(f"{removed} artık dosya diskten temizlendi.")
        return 0

    if not targets:
        show_versions(slug)
        print("\nSilmek için: --file <dosya> veya --numbers 82,83 ekleyip --apply verin.")
        return 0

    print(f"\n'{slug}' kurumundan silinecek {len(targets)} versiyon:\n")
    versions = {v["filename"]: v for v in version_store.list_versions(slug)}
    for name in targets:
        v = versions.get(name, {})
        print(f"  {v.get('label', '?'):<16} {name:<42}"
              f"{v.get('date_str', '')} {v.get('time_str', '')}")

    if not args.apply:
        print("\nBu bir ön izlemedir. Silmek için --apply ekleyin.")
        return 0

    print()
    for name in targets:
        version_store.delete_version(slug, name)
        print(f"  silindi: {name}")

    removed = version_store.enforce_tombstones(slug)
    if removed:
        print(f"  {removed} artık dosya daha temizlendi.")

    print("\nSunucuya bildiriliyor...")
    confirmed = version_store.flush_pending_deletes()
    left = version_store.pending_delete_count()
    print(f"  {confirmed} silme sunucu tarafından onaylandı.")
    if left:
        print(f"  {left} tanesi beklemede — bağlantı gelince otomatik gönderilecek.")
        print("  (Bu arada bu cihazda geri gelmezler; silme kaydı kalıcıdır.)")

    print(f"\nKalan versiyon sayısı: {len(version_store.list_versions(slug))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
