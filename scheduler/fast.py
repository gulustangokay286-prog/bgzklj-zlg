"""scheduler/fast.py — yeni C++ çekirdeği (protokol 3) için köprü.

Girdi artık minik: kartlar, aday saatleri ve kapalı hücre maskeleri. Eski
protokolün kart çifti maliyet tabloları (v188'de 4,5 MB) tamamen kalktı —
çakışma, tablodan okunmak yerine çizelgenin kendisinden hesaplanıyor. Girdi
küçüldüğü için paralel şerit açmak da ucuzladı: her şerit dosyayı baştan
ayrıştırmak zorunda değil.
"""
import concurrent.futures
import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from . import rules as R

_LOCK = threading.Lock()


def binary():
    src = Path(__file__).parent / 'native' / 'chenkron.cpp'
    out = Path(__file__).parent / 'native' / 'chenkron'
    with _LOCK:
        if not out.is_file() or out.stat().st_mtime < src.stat().st_mtime:
            cxx = shutil.which(os.environ.get('CXX', 'clang++')) or shutil.which('g++')
            if not cxx:
                raise RuntimeError('C++ motoru derlenmemiş; clang++ veya g++ gerekiyor.')
            r = subprocess.run([cxx, '-std=c++17', '-O3', '-DNDEBUG', str(src), '-o', str(out)],
                               capture_output=True, text=True, timeout=120)
            if r.returncode:
                raise RuntimeError('C++ motoru derlenemedi: ' + r.stderr[-2000:])
    return out


def encode(world, rule_list, seconds, seed, target):
    """Problemi protokol 3 metnine çevirir."""
    w = world
    N = w.D * w.P
    subject_once = any(r.kind == R.X_SUBJECT_ONCE_DAY and r.is_hard() for r in rule_list)
    teacher_once = any(r.kind == R.X_TEACHER_ONCE_DAY and r.is_hard() for r in rule_list)
    hard_adj = set()
    for r in rule_list:
        if r.kind == R.X_HARD_NOT_ADJACENT and r.is_hard():
            hard_adj |= set(r.subjects)

    out = [f"3 {len(w.cards)} {len(w.classes)} {len(w.teachers)} {len(w.subjects)} "
           f"{w.D} {w.P} {seconds} {seed} {target}"]

    def mask(m):
        return f"{m & ((1 << 64) - 1)} {(m >> 64) & ((1 << 64) - 1)}"

    for m in w.class_closed:
        out.append(mask(m))
    for m in w.teacher_closed:
        out.append(mask(m))
    out.append(f"{int(subject_once)} {int(teacher_once)} {len(hard_adj)} "
               + " ".join(map(str, sorted(hard_adj))))
    for c in w.cards:
        slots = [i for i, _ in c.slots]
        out.append(f"{c.duration} {c.subject} {c.teacher} {c.duration*len(c.classes)} "
                   f"{-1 if c.locked_at is None else c.locked_at} {len(c.classes)} "
                   + " ".join(map(str, c.classes)) + f" {len(slots)} "
                   + " ".join(map(str, slots)))
    return "\n".join(out) + "\n"


def _one(binpath, payload_path, seconds, seed, n):
    with tempfile.TemporaryDirectory(prefix='chenkron-fast-') as tmp:
        op = Path(tmp) / 'out'
        with open(payload_path) as si, op.open('w') as so:
            p = subprocess.Popen([str(binpath), str(seconds), str(seed)],
                                 stdin=si, stdout=so, stderr=subprocess.DEVNULL)
            try:
                p.wait(timeout=seconds + 20)
            except subprocess.TimeoutExpired:
                p.kill(); p.wait()
        best = None
        for line in op.read_text().splitlines():
            v = line.split()
            if len(v) == n + 5 and v[0] in ('P', 'F'):
                best = dict(hours=int(v[1]), steps=int(v[2]), restarts=int(v[3]),
                            soft_cost=int(v[4]), positions=list(map(int, v[5:])))
        return best or dict(hours=0, steps=0, restarts=0, soft_cost=0,
                            positions=[-1] * n)


def solve_fast(world, rule_list, seconds, seed, target, lanes=None):
    """Paralel şeritlerde arar, en iyi sonucu döner.

    Şeritler TEK bir girdi dosyasını paylaşır; tohum komut satırından verilir.
    Girdi küçük olduğu için şerit sayısını çekirdek sayısının üstüne çıkarmak
    ucuzdur ve tohum çeşitliliği kazandırır — bir tohum başaracaksa ilk
    saniyelerde başarır, başaramayacaksa beklemenin faydası yoktur.
    """
    b = binary()
    n = len(world.cards)
    if lanes is None:
        lanes = max(2, (os.cpu_count() or 4) * 2)
    with tempfile.TemporaryDirectory(prefix='chenkron-in-') as tmp:
        payload = Path(tmp) / 'input'
        payload.write_text(encode(world, rule_list, seconds, seed, target))
        best = None
        with concurrent.futures.ThreadPoolExecutor(max_workers=lanes) as pool:
            futs = [pool.submit(_one, b, payload, seconds, seed + k * 7919 + 1, n)
                    for k in range(lanes)]
            for f in concurrent.futures.as_completed(futs):
                rec = f.result()
                if best is None or rec['hours'] > best['hours']:
                    best = rec
        return best
